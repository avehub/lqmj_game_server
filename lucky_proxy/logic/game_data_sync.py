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
    # 直接传入的代理分成金额，优先用于计算，不再使用比例
    dividend_income: float = 0.0


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
        proxy_level = proxy_user.get("proxy_level")
        room_card_rate = proxy_user.get("room_card_rate")
        assistance_program_rate = proxy_user.get("assistance_program_rate")
        order_type = data.order_type
        now = datetime.now()
        level1_proxy_id = 0
        ch_id = 0
        # 有从二级升级成一级的情况  所以 若代理已经是一级 则 不取level1_proxy_id
        cls.log_info(f"当前订data={data}的代理等级={proxy_level}")
        if proxy_level != ProxyLevel.LEVEL_1:
            level1_proxy_id = relation.get("level1_proxy_id")

        proxy_income = decimal.Decimal("0.00")
        platform_income = decimal.Decimal("0.00")
        channel_proxy_income = decimal.Decimal("0.00")
        
        # 原一级收入
        original_level1_proxy_income = decimal.Decimal("0.00")
        # 一级代理邀请的用户升级为一级代理后产生订单 如果是房卡则按照0.05一张给原一级分佣 否则不进行分佣
        if relation.get("upgrade_flag") == 1:
            if order_type == ChargeOrderType.TYPE_1 and ROOM_FIXED_COMMISSION_AMOUNT > decimal.Decimal(str(data.price)):
                cls.log_info(
                    f"固定房卡分成比例时固定金额={ROOM_FIXED_COMMISSION_AMOUNT}大于订单单价={data.price},不进行分佣")
                return 1
            if order_type == ChargeOrderType.TYPE_1:
                original_level1_proxy_income = (
                        decimal.Decimal(str(data.goods_number)) * ROOM_FIXED_COMMISSION_AMOUNT).quantize(
                    decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)
                proxy_income = original_level1_proxy_income
                platform_income = (decimal.Decimal(str(data.order_amount)) - original_level1_proxy_income).quantize(
                    decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)
                cls.log_info(f"原一级固定分成 proxy_income={proxy_income}, platform_income={platform_income}, goods={data.goods_number}, price={data.price}")
                 # 渠道分成：玩家是一级代理，且其渠道代理是渠道时，房卡订单每张固定0.05从平台分成给渠道  改成从关系表拿渠道ID
                player_proxy = await ProxyUser.get_by_pk(data.player_id, ["proxy_level", "channel_proxy_id", "is_channel"])
                if player_proxy and player_proxy.get("proxy_level") == ProxyLevel.LEVEL_1 and data.order_type == ChargeOrderType.TYPE_1:
                    ch_id = player_proxy.get("channel_proxy_id") or 0
                    ch_id = relation.get("channel_proxy_id") or 0
                    if ch_id:
                        ch_user = await ProxyUser.get_by_pk(ch_id, ["is_channel"])
                        if ch_user and ch_user.get("is_channel") == 1:
                            need = (decimal.Decimal(str(data.goods_number)) * ROOM_FIXED_COMMISSION_AMOUNT).quantize(
                                decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)
                            if platform_income >= need:
                                channel_proxy_income = need
                                platform_income = (platform_income - channel_proxy_income).quantize(
                                    decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)
                                cls.log_info(f"渠道分成 proxy_id={proxy_id} channel_id={ch_id} income={channel_proxy_income} goods={data.goods_number}")
                            else:
                                cls.log_info(f"渠道分成不足 platform_income={platform_income} need={need} proxy_id={proxy_id} channel_id={ch_id}")
        
            if order_type == ChargeOrderType.TYPE_2:
                cls.log_info(
                    f"player_id={data.player_id}已经升级为一级代理,该玩家充值的订单非房卡订单 给原代理 按比例产生分佣 之前为不分，data={data}")

                proxy_income = (
                        decimal.Decimal(str(data.order_amount)) * decimal.Decimal(str(data.dividend_rate))).quantize(
                    decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)
                platform_income = (decimal.Decimal(str(data.order_amount)) - proxy_income).quantize(
                    decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)
        else:
            if data.dividend_income and float(data.dividend_income) > 0:
                incoming = decimal.Decimal(str(data.dividend_income)).quantize(decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)
                amount = decimal.Decimal(str(data.order_amount)).quantize(decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)
                if incoming > amount:
                    cls.log_info(f"分成跳过：传入金额超额 incoming={incoming} > order_amount={amount}, order_id={data.order_id}, player_id={data.player_id}, proxy_id={proxy_id}, dividend_rate={data.dividend_rate}, goods={data.goods_number}, order_type={data.order_type}")
                    return 1
                proxy_income = incoming
                cls.log_info(f"按传入金额分成 proxy_income={proxy_income}, order_amount={data.order_amount}")
            else:
                proxy_income = (
                    decimal.Decimal(str(data.order_amount)) * decimal.Decimal(str(data.dividend_rate))
                ).quantize(decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)
                cls.log_info(f"按比例分成 proxy_income={proxy_income}, order_amount={data.order_amount}, dividend_rate={data.dividend_rate}")
            platform_income = (decimal.Decimal(str(data.order_amount)) - proxy_income).quantize(
                decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)
            cls.log_info(f"计算平台收入 platform_income={platform_income}, order_amount={data.order_amount}, proxy_income={proxy_income}")

        level2_proxy_income = decimal.Decimal("0.00")
        level1_proxy_income = decimal.Decimal("0.00")
        level2_dividend_rate = decimal.Decimal("0.00") 

        if ProxyLevel.LEVEL_2 == proxy_level:
            if order_type == ChargeOrderType.TYPE_1:
                level2_dividend_rate = room_card_rate
                level2_proxy_income = (proxy_income * room_card_rate).quantize(
                    decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)
                cls.log_info(f"二级房卡分成 level2_proxy_income={level2_proxy_income}, room_card_rate={room_card_rate}, proxy_income基数={proxy_income}")
            elif order_type == ChargeOrderType.TYPE_2:
                level2_dividend_rate = assistance_program_rate
                level2_proxy_income = (proxy_income * assistance_program_rate).quantize(
                    decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)
                cls.log_info(f"二级助农分成 level2_proxy_income={level2_proxy_income}, assistance_program_rate={assistance_program_rate}, proxy_income基数={proxy_income}")

            level1_proxy_income = (proxy_income - level2_proxy_income).quantize(
                decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)
            proxy_income = level2_proxy_income.quantize(
                decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)
            cls.log_info(f"分成拆分后 level1_proxy_income={level1_proxy_income}, level2_proxy_income={proxy_income}")

       
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
            "channel_proxy_income": channel_proxy_income,
            "channel_proxy_id": ch_id,
            "order_type": data.order_type,
            #必须
            "level": proxy_user.get("proxy_level"),
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
                if channel_proxy_income > decimal.Decimal("0.00") and ch_id:
                    await ProxyUserWallet.exec_sql(
                        f"update proxy_user_wallet "
                        f"set total_income=total_income+{str(channel_proxy_income)}, "
                        f"room_income=room_income+{str(channel_proxy_income)} "
                        f"where id={ch_id}"
                    )
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
            "status": 1,
            "vip_expire_time": data.vip_expire_time if data.vip_expire_time else 0
        }
        try:
            cls.log_info(f"新增一级代理开始 uid={data.player_id}")
            query_relation = {
                "player_id": data.player_id
            }
            relation: ProxyPromotionRelation = await ProxyPromotionRelation.get_by_dict(query_relation, limit=1)
            cls.log_info(f"relation={relation}")
            level1_proxy_id = None
            channel_proxy_id = 0
            if relation:
                proxy_id = relation.get("proxy_id")
                proxy_level = relation.get("level")
                """
                  若存在邀请关系
                  1、如果是二级用户邀请的用户则直接成为1级，则该用户的充值原上级还能正常享受分佣，但该用户成为代理后邀请的用户和原来的上级代理脱离关系()
                  2、若是二级用户升级一级代理 则原来的一级代理只享受0.05一张房卡的收益提成
                """

                if relation:
                    level1_proxy_id = proxy_id
                    add_param.update({"level1_proxy_id": level1_proxy_id})
                    parent = await ProxyUser.get_by_pk(level1_proxy_id, field=["level1_proxy_id"])
                    grand_id = parent.get("level1_proxy_id") if parent else 0
                    channel_proxy_id = grand_id or 0
                    cls.log_info(f"parent={parent}, grand_id={grand_id}, channel_proxy_id={channel_proxy_id}")

            async with in_transaction(connection_name=DbKey.DEFAULT):
                await ProxyUser.add_one({**add_param, "channel_proxy_id": channel_proxy_id})
                cls.log_info(f"写入代理表完成 uid={data.player_id}, channel_proxy_id={channel_proxy_id}")
                await ProxyUserWallet.add_one(
                    {"id": data.player_id, "proxy_level": ProxyLevel.LEVEL_1, "level1_proxy_id": level1_proxy_id})
                if relation:
                    up = {"upgrade_flag": 1}
                    if channel_proxy_id:
                        up["channel_proxy_id"] = channel_proxy_id
                    await ProxyPromotionRelation.update_by_pk(pk_val=relation.get("id"), param=up)
                    cls.log_info(f"更新关系表完成 relation_id={relation.get('id')}, channel_proxy_id={channel_proxy_id}")
                else:
                    await ProxyPromotionRelation.exec_sql(f"UPDATE proxy_promotion_relation SET upgrade_flag=1 WHERE player_id={data.player_id}")
                    cls.log_info(f"兜底关系表更新完成 player_id={data.player_id}")
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
            cls.log_info(f"升级一级代理开始 uid={data.player_id}, opt_user_id={data.opt_user_id}")
            relation: ProxyPromotionRelation = await ProxyPromotionRelation.get_by_dict({"player_id": data.player_id},
                                                                                        field=["id", "level",
                                                                                               "proxy_id"], limit=1)
            cls.log_info(f"relation={relation}")
            level_proxy_id = relation.get("proxy_id")
            cls.log_info(f"level_proxy_id={level_proxy_id}")
            channel_proxy_id = 0
            if level_proxy_id:
                parent = await ProxyUser.get_by_pk(level_proxy_id, field=["level1_proxy_id"])
                grand_id = parent.get("level1_proxy_id") if parent else 0
                cls.log_info(f"parent={parent}, grand_id={grand_id}")
                channel_proxy_id = grand_id
                cls.log_info(f"grand={locals().get('grand', None)}, channel_proxy_id={channel_proxy_id}")
            else:
                cls.log_info("未找到上级代理，跳过渠道判定")
            async with in_transaction(connection_name=DbKey.DEFAULT):
                await ProxyUser.update_by_pk(data.player_id, {**update_data, "channel_proxy_id": channel_proxy_id})
                cls.log_info(f"更新代理渠道ID完成 uid={data.player_id}, channel_proxy_id={channel_proxy_id}")

                await ProxyUserWallet.exec_sql(
                    f"update proxy_user_wallet  set proxy_level=1"
                    f",upgrade_flag=1"
                    f",level2_total_player=level2_total_player-1 "
                    f" where id={level_proxy_id}")
                cls.log_info(f"更新钱包完成 level_proxy_id={level_proxy_id}")
                if relation:
                    up = {"upgrade_flag": 1}
                    if channel_proxy_id:
                        up["channel_proxy_id"] = channel_proxy_id
                    await ProxyPromotionRelation.update_by_pk(pk_val=relation.get("id"), param=up)
                    cls.log_info(f"更新关系表完成 relation_id={relation.get('id')}, channel_proxy_id={channel_proxy_id}")
                else:
                    await ProxyPromotionRelation.exec_sql(f"UPDATE proxy_promotion_relation SET upgrade_flag=1 WHERE player_id={data.player_id}")
                    cls.log_info(f"兜底关系表更新完成 player_id={data.player_id}")
                cls.log_info(f"升级一级代理结束,data={data}")

        except Exception as e:
            cls.log_err(f"【重要日志】升级代理等级失败，error：{e},data:{data}")
            return False, 'ERROR'
        return True, ''
