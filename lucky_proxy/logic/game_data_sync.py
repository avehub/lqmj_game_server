import decimal
import time
from dataclasses import dataclass
from datetime import datetime, timedelta

from nsanic.libs.component import LogMeta
from tortoise.transactions import in_transaction

from common.public.enum_const import DbKey
from common.utils.utils import UtilsTool
from lucky_proxy.config import ConfSrv, conf_srv
from lucky_proxy.const import ProxyLevel, ChargeOrderType
from lucky_proxy.model_db.main import ProxyPromotionRelation, ProxyOrderDividendRecords, ProxyUser, ProxyUserWallet

# 房卡固定分佣金额0.05 一张

ROOM_FIXED_COMMISSION_AMOUNT = decimal.Decimal("0.05")

"""
订单数据
"""


@dataclass
class Level1ProxyDTO:
    # 玩家id
    player_id: int
    # unionid
    unionid: str
    phone: str
    # VIP等级1（月卡会员）、2（季卡会员）、3（年卡会员）、999（永久会员）
    vip_level: int
    # 过期时间转换为秒
    vip_expire_time: int
    # 昵称
    name: int = None
    # 头像
    avatar: str = None


@dataclass
class UpgradeProxyDTO:
    # 二级代理id
    player_id: int
    # 操作用户id
    opt_user_id: int


@dataclass
class PromotionOrderDataDTO:
    order_id: int
    # 订单号
    order_no: str
    player_id: int
    # 订单类型  1:房卡 2:助农收益
    order_type: int
    # 商品数量 没有传1（房卡时传精确的房卡份数）
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

        proxy_income = decimal.Decimal("0.00")
        platform_income = decimal.Decimal("0.00")
        # 原一级收入
        original_level1_proxy_income= decimal.Decimal("0.00")
        # 一级代理邀请的用户升级为一级代理后产生订单 如果是房卡则按照0.05一张给原一级分佣 否则不进行分佣
        if relation.get("upgrade_flag") == 1 and ProxyLevel.LEVEL_1 == proxy_level:
            if order_type == ChargeOrderType.TYPE_1 and ROOM_FIXED_COMMISSION_AMOUNT > decimal.Decimal(str(data.price)):
                cls.log_info(f"固定房卡分成比例时固定金额={ROOM_FIXED_COMMISSION_AMOUNT}大于订单单价={data.price},不进行分佣")
                return 1
            if order_type == ChargeOrderType.TYPE_1:
                original_level1_proxy_income = (decimal.Decimal(str(data.goods_number)) * ROOM_FIXED_COMMISSION_AMOUNT).quantize(
                    decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)
                proxy_income=original_level1_proxy_income
                platform_income = (decimal.Decimal(str(data.order_amount)) - original_level1_proxy_income).quantize(
                    decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)
            if order_type == ChargeOrderType.TYPE_2:
                cls.log_info(
                    f"player_id={data.player_id}已经升级为一级代理,该玩家充值的订单非房卡订单不再给原代理产生分佣，data={data}")
                return 1
        else:
            proxy_income = (
                    decimal.Decimal(str(data.order_amount)) * decimal.Decimal(str(data.dividend_rate))).quantize(
                decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)
            platform_income = (decimal.Decimal(str(data.order_amount)) - proxy_income).quantize(
                decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)

        level2_proxy_income = decimal.Decimal("0.00")
        level1_proxy_income = decimal.Decimal("0.00")
        level2_dividend_rate = decimal.Decimal("0.00")

        if ProxyLevel.LEVEL_2 == proxy_level:
            if order_type == ChargeOrderType.TYPE_1:
                level2_dividend_rate = room_card_rate
                level2_proxy_income = (proxy_income * room_card_rate).quantize(
                    decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)
            elif order_type == ChargeOrderType.TYPE_2:
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
                if relation.get("upgrade_flag") == 1 and ProxyLevel.LEVEL_1 == proxy_level:
                    await cls.update_wallet(proxy_id, original_level1_proxy_income, decimal.Decimal("0.00"),
                                            data.order_amount, ChargeOrderType.TYPE_1)
                else:
                    await cls.update_wallet(proxy_id, proxy_income, level1_proxy_income, data.order_amount,
                                        data.order_type)
                await ProxyPromotionRelation.exec_sql(f" update proxy_promotion_relation  "
                                                      f"set total_amount=total_amount+{str(data.order_amount)} where player_id={data.player_id}")
        except Exception as e:
            e.with_traceback()
            cls.log_err(f"【重要日志】分销订单入库失败，error：{e},data:{data}")
            return 0
        return 1

    @classmethod
    async def update_wallet(cls, proxy_id, proxy_income, level1_proxy_income, order_amount,
                            order_type):
        sql = ""
        if order_type == 1:
            sql = f"""
                 update proxy_user_wallet 
                        set total_amount=total_amount+{str(order_amount)}
                        ,  total_income=total_income+{str(proxy_income)}
                        ,  room_amount=room_amount+{str(order_amount)}
                        ,  room_income=room_income+{str(proxy_income)}
                        ,  level1_total_income=level1_total_income+{str(level1_proxy_income)}
                        ,  level1_room_income=level1_room_income+{str(level1_proxy_income)}
                 where id={proxy_id}
                 """
        if order_type == 2:
            sql = f"""
                 update proxy_user_wallet 
                         set total_amount=total_amount+{str(order_amount)}
                        ,  total_income=total_income+{str(proxy_income)}
                        ,  assistance_program_amount=assistance_program_amount+{str(order_amount)}
                        ,  assistance_program_income=assistance_program_income+{str(proxy_income)}
                        ,  level1_total_income=level1_total_income+{str(level1_proxy_income)}
                        ,  level1_assistance_program_income=level1_assistance_program_income+{str(level1_proxy_income)}
                 where id={proxy_id}
                 """
        return await ProxyUserWallet.exec_sql(sql)

    @classmethod
    async def init_level1_proxy(cls, data: Level1ProxyDTO):
        add_param = {
            "id": data.player_id,
            "unionid": data.unionid,
            "phone": data.phone,
            "name": data.name,
            "avatar": data.avatar,
            "level": ProxyLevel.LEVEL_1,
            "join_day": datetime.now().strftime("%Y-%m-%d"),
            "promotion_code": UtilsTool.generate_invite_code(10),
            "vip_level": data.vip_level,
            "vip_expire_time": data.vip_expire_time if data.vip_expire_time else 0
        }
        try:
            query_relation = {
                "player_id": data.player_id
            }
            relation: ProxyPromotionRelation = await ProxyPromotionRelation.get_by_dict(query_relation, limit=1)
            proxy_id = relation.get("proxy_id")
            proxy_level = relation.get("level")
            """
              若存在邀请关系
              1、如果是二级用户邀请的用户则直接成为1级，则该用户的充值原上级还能正常享受分佣，但该用户成为代理后邀请的用户和原来的上级代理脱离关系()
              2、若是二级用户升级一级代理 则原来的一级代理只享受0.05一张房卡的收益提成
            """
            level1_proxy_id = None
            if relation and proxy_level == ProxyLevel.LEVEL_1:
                level1_proxy_id = proxy_id
                add_param.update({"level1_proxy_id": level1_proxy_id})

            async with in_transaction(connection_name=DbKey.DEFAULT):
                await ProxyUser.add_one(add_param)
                await ProxyUserWallet.add_one(
                    {"id": data.player_id, "proxy_level": ProxyLevel.LEVEL_1, "level1_proxy_id": level1_proxy_id})
                if relation and relation.get("level") == ProxyLevel.LEVEL_1:
                    await ProxyPromotionRelation.update_by_pk(pk_val=relation.get("id"), param={"upgrade_flag", 1})
        except Exception as e:
            cls.log_err(f"【重要日志】初始化一级代理失败，error：{e},data:{data}")
            return False, 'ERROR'
        return True, ''

    """
    二级代理用户升级为一级代理用户
    """

    @classmethod
    async def upgrade_level1_proxy(cls, data: UpgradeProxyDTO):
        update_data = {
            "opt_user_id": data.opt_user_id,
            "proxy_level": ProxyLevel.LEVEL_1,
            "upgrade_time": time.time()
        }
        """
                   若存在邀请关系
                   1、如果是二级用户邀请的用户则直接成为1级，则该用户的充值原上级还能正常享受分佣，但该用户成为代理后邀请的用户和原来的上级代理脱离关系()
                   2、若是二级用户升级一级代理 则原来的一级代理只享受0.05一张房卡的收益提成
        """
        try:
            relation: ProxyPromotionRelation = await ProxyPromotionRelation.get_by_dict({"player_id": data.player_id},
                                                                                        field=["id"], limit=1)
            async with in_transaction(connection_name=DbKey.DEFAULT):
                await ProxyUser.update_by_pk(data.player_id, update_data)
                await ProxyUserWallet.update_by_pk(data.player_id,
                                                   param={"proxy_level": ProxyLevel.LEVEL_1, "upgrade_flag": 1})
                if relation and relation.get("level") == ProxyLevel.LEVEL_1:
                    await ProxyPromotionRelation.update_by_pk(pk_val=relation.get("id"), param={"upgrade_flag": 1})
                cls.log_info(f"升级一级代理结束,data={data}")

        except Exception as e:
            cls.log_err(f"【重要日志】升级代理等级失败，error：{e},data:{data}")
            return False, 'ERROR'
        return True, ''
