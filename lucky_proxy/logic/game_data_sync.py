import decimal
from dataclasses import dataclass
from datetime import datetime, timedelta

from nsanic.libs.component import LogMeta
from tortoise.transactions import in_transaction

from common.public.enum_const import DbKey
from common.utils.utils import UtilsTool
from lucky_proxy.config import ConfSrv, conf_srv
from lucky_proxy.const import ProxyLevel
from lucky_proxy.model_db.main import ProxyPromotionRelation, ProxyOrderDividendRecords, ProxyUser, ProxyUserWallet

"""
订单数据
"""


@dataclass
class Level1ProxyDTO:
    # 玩家id
    player_id: int
    # unionid
    unionid: str
    phone: int
    # 昵称
    name: int = None
    # 头像
    avatar: str = None


@dataclass
class PromotionOrderDataDTO:
    order_id: int
    # 订单号
    order_no: str
    player_id: int
    # 订单类型  1:房卡 2:助农收益
    order_type: int
    # 商品数量 没有传1
    goods_number: int
    # 单价 如：18.00 28.00
    price: float
    # 订单总金额
    order_amount: float
    # 代理分成比例 0.6 0.8
    dividend_rate: float
    # 订单时间（创建时间）
    order_time: int


"""
推广新增用户对象
"""


@dataclass
class PromotionAddUserDTO:
    # 玩家 id
    player_id: int
    # 推广码
    promotion_code: str
    # 暂时不用
    promotion_type: int
    # 用户新增时间
    promotion_time: int


"""
订单同步
"""


class GameDataSync(LogMeta):
    conf: ConfSrv = conf_srv

    @classmethod
    async def save_dividend_records(cls, data: PromotionOrderDataDTO
                                    , relation: ProxyPromotionRelation
                                    , proxy_user: ProxyUser):
        proxy_id = relation.get("proxy_id")
        level1_proxy_id = relation.get("level1_proxy_id")
        proxy_level = relation.get("level")
        room_card_rate = proxy_user.get("room_card_rate")
        assistance_program_rate = proxy_user.get("assistance_program_rate")
        order_type = data.order_type
        now = datetime.now()
        proxy_income = (decimal.Decimal(str(data.order_amount)) * decimal.Decimal(str(data.dividend_rate))).quantize(
            decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)
        platform_income = (decimal.Decimal(str(data.order_amount)) - proxy_income).quantize(
            decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)
        level2_proxy_income = decimal.Decimal("0.00")
        level1_proxy_income = decimal.Decimal("0.00")
        level2_dividend_rate = decimal.Decimal("0.00")
        if ProxyLevel.LEVEL_2 == proxy_level:
            if order_type == 1:
                level2_dividend_rate = room_card_rate
                level2_proxy_income = (proxy_income * room_card_rate).quantize(
                    decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)
            elif order_type == 2:
                level2_dividend_rate = assistance_program_rate
                level2_proxy_income = (proxy_income * assistance_program_rate).quantize(
                    decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)
            level1_proxy_income = (proxy_income - level2_proxy_income).quantize(
                decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)
            proxy_income = level2_proxy_income.quantize(
                decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)

        monday_date = now - timedelta(days=now.weekday())
        records = {
            "id": data.order_id,
            "order_id": data.order_id,
            "order_no": data.order_no,
            "price": data.price,
            "order_amount": data.order_amount,
            "dividend_rate": data.dividend_rate,
            "level2_dividend_rate": level2_dividend_rate,
            "proxy_id": proxy_id,
            "promotion_id": relation.get("promotion_id"),
            "player_id": data.player_id,
            "level1_proxy_id": level1_proxy_id,
            "proxy_income": proxy_income,
            "level1_proxy_income": level1_proxy_income,
            "platform_income": platform_income,
            "order_type": data.order_type,
            "level": relation.get("level"),
            "goods_number": data.goods_number,
            "order_year": now.strftime("%Y"),
            "order_month": now.strftime("%Y-%m"),
            "order_day": now.strftime("%Y-%m-%d"),
            "order_week_day": monday_date.strftime("%Y-%m-%d"),
            "order_time": data.order_time
        }
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                await ProxyOrderDividendRecords.add_one(records)
                await cls.update_wallet(proxy_id, proxy_income, level1_proxy_income, data.order_amount, data.order_type)
                # TODO 增加 用户钱包数据
        except Exception as e:
            cls.log_err(f"【重要日志】分销订单入库失败，error：{e},data:{data}")

    @classmethod
    async def update_wallet(cls, proxy_id, proxy_income, level1_proxy_income, order_amount, order_type):
        sql = ""
        if order_type == 1:
            sql = f"""
                 update proxy_user_wallet 
                        set  total_player=total_player+1
                        , total_amount=total_amount+{order_amount}
                        ,  total_income=total_income+{proxy_income}
                        ,  room_amount=room_amount+{order_amount}
                        ,  room_income=room_income+{proxy_income}
                        ,  level1_total_income=level1_total_income+{level1_proxy_income}
                        ,  level1_room_income=level1_room_income+{level1_proxy_income}
                 where id={proxy_id}
                 """
        if order_type == 2:
            sql = f"""
                 update proxy_user_wallet 
                        set  total_player=total_player+1
                        ,  total_amount=total_amount+{order_amount}
                        ,  total_income=total_income+{proxy_income}
                        ,  assistance_program_amount=assistance_program_amount+{order_amount}
                        ,  assistance_program_income=assistance_program_income+{proxy_income}
                        ,  level1_total_income=level1_total_income+{level1_proxy_income}
                        ,  level1_assistance_program_income=level1_assistance_program_income+{level1_proxy_income}
                 where id={proxy_id}
                 """
        return await ProxyUserWallet.exec_sql(sql)

    @classmethod
    async def init_level1_proxy(cls, data: Level1ProxyDTO):
        try:
            add_param = {
                "id": data.player_id,
                "unionid": data.unionid,
                "phone": data.phone,
                "name": data.name,
                "avatar": data.avatar,
                "level": ProxyLevel.LEVEL_1,
                "join_day": datetime.now().strftime("%Y-%m-%d"),
                "promotion_code": UtilsTool.generate_invite_code(10),
            }
            await ProxyUser.add_one(add_param)
            await ProxyUserWallet.add_one({"id": data.player_id, "proxy_level": ProxyLevel.LEVEL_1})
        except Exception as e:
            cls.log_err(f"【重要日志】初始化一级代理失败，error：{e},data:{data}")
            return False, 'ERROR'
        return True, ''
