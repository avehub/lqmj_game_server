from nsanic.libs.mk_random import RngMaker
from nsanic.orm.db_model import DBModel
from tortoise import fields
from nsanic.libs import tool_dt
from common.public.enum_const import ServiceEnum
from lucky_game.const import AwardType, EventTracking
from lucky_game.const import OrderStatus, PayType, PayMode, DeliverStatus, PlatForm, AchieveType
from c_services.cs_mahjong.const import PlayType


class RecordsTrade(DBModel):
    """ 交易订单记录（分表版停用） """
    _SPLIT_TYPE = 2

    order_id = fields.CharField(max_length=32, pk=True, description='订单号')
    uid = fields.IntField(max_length=28, null=False, description='玩家ID')
    trade_item = fields.BigIntField(max_length=28, null=False, description='订单项目')
    trade_item_count = fields.IntField(max_length=28, null=True, default=1, description="交易数量")
    status = fields.IntEnumField(enum_type=OrderStatus, default=OrderStatus.WAIT_PAY, description="订单状态")
    deliver_status = fields.IntEnumField(
        enum_type=DeliverStatus, default=DeliverStatus.UNSHIPPED, description="发货状态")
    product_id = fields.CharField(max_length=32, null=True, default='', description='道具ID')
    orig_price = fields.CharField(max_length=12, null=False, description="原价")
    actual_price = fields.CharField(max_length=12, null=False, description="实际价格")
    trade_amount = fields.CharField(max_length=12, null=False, description="交易数额")
    trade_time = fields.BigIntField(max_length=28, null=True, default=0, description="交易时间")
    order_desc = fields.CharField(max_length=128, null=True, description='订单描述')
    finish_time = fields.BigIntField(max_length=28, null=True, default=0, description='完成时间')
    pay_type = fields.IntEnumField(PayType, description="支付类型")
    pay_mode = fields.IntEnumField(PayMode, description="支付方式")
    order_source = fields.IntEnumField(PlatForm, description="订单来源")

    class Meta:
        table = "records_trade"

    @classmethod
    async def gen_insert_data(cls, **kwargs):
        """ 生成插入数据 """
        data = {
            "order_id": await RngMaker.gen_num(str_len=32),
            "uid": kwargs.get("uid"),
            "trade_item": kwargs.get("trade_item"),
            "trade_item_count": kwargs.get("trade_item_count"),
            "status": kwargs.get("status"),
            "deliver_status": kwargs.get("deliver_status"),
            "orig_price": kwargs.get("orig_price") or 0,
            "actual_price": kwargs.get("actual_price") or kwargs.get("trade_amount"),
            "trade_amount": kwargs.get("trade_amount"),
            "trade_time": tool_dt.cur_time(),
            "order_desc": kwargs.get("order_desc"),
            "finish_time": kwargs.get("finish_time"),
            "pay_type": kwargs.get("pay_type"),
            "pay_mode": kwargs.get("pay_mode"),
            "order_source": kwargs.get("order_source"),
            "product_id": kwargs.get("product_id")
        }
        return data

    @classmethod
    async def query_is_first_buy(cls, uid, trade_item, in_shopping=False):
        """ 查询该商品是否首次购买（已发货状态的订单数量 > 0） """
        query_param = {"uid": uid, "deliver_status": DeliverStatus.SHIPPED, "trade_item": trade_item}
        if in_shopping:
            record = await cls.get_by_dict(query_param)
            is_first = False if record and len(record) >= 1 else True
        else:
            record = await cls.get_by_dict(query_param, limit=1)
            is_first = False if record else True
        if is_first:
            return False
        return True

    @classmethod
    async def query_order(cls, order_id) -> bool or dict:
        """ 查询订单是否已支付 """
        order_info = await cls.get_by_pk(order_id)
        if not order_info:
            return False
        return order_info


class RecordsAdOrder(DBModel):
    """ 广告订单记录 """
    _SPLIT_TYPE = 2

    ad_order_id = fields.CharField(max_length=32, pk=True, description='广告订单号')
    uid = fields.IntField(max_length=28, null=False, description='玩家ID')
    ad_slot_id = fields.IntField(max_length=28, null=False, description='广告奖励位ID')
    ad_achieve_type = fields.IntEnumField(enum_type=AchieveType, default=0, description="广告达成类型")
    ad_achieve_value = fields.BigIntField(max_length=28, null=True, default=0, description="达成值")
    status = fields.IntEnumField(enum_type=OrderStatus, default=OrderStatus.WAIT_PAY, description="广告订单状态")
    deliver_status = fields.IntEnumField(
        enum_type=DeliverStatus, default=DeliverStatus.UNSHIPPED, description="奖励发放状态")
    ad_order_desc = fields.CharField(max_length=128, null=True, description='订单描述')
    finish_time = fields.BigIntField(max_length=28, null=True, default=0, description='完成时间')
    order_source = fields.IntEnumField(PlatForm, description="订单来源")

    class Meta:
        table = "records_ad_order"

    @classmethod
    async def gen_insert_data(cls, **kwargs):
        """ 生成插入数据 """
        data = {
            "ad_order_id": await RngMaker.gen_num(str_len=32),
            "uid": kwargs.get("uid"),
            "ad_slot_id": kwargs.get("ad_slot_id"),
            "ad_achieve_type": kwargs.get("ad_achieve_type"),
            "ad_achieve_value": kwargs.get("ad_achieve_value"),
            "deliver_status": kwargs.get("deliver_status"),
            "ad_order_desc": kwargs.get("ad_order_desc"),
            "finish_time": kwargs.get("finish_time"),
            "order_source": kwargs.get("order_source"),
        }
        return data

    @classmethod
    async def query_order(cls, ad_order_id) -> bool or dict:
        """ 查询广告订单是否已完成 """
        ad_order_info = await cls.get_by_pk(ad_order_id)
        if not ad_order_info:
            return False
        return ad_order_info


class RecordsGameGrade(DBModel):
    """ 游戏战绩 """
    _SPLIT_TYPE = 2

    uid = fields.IntField(max_length=28, index=True, default=100000, description='玩家ID')
    cs_type = fields.IntEnumField(enum_type=ServiceEnum, index=True, description="子服务类型")
    play_type = fields.IntEnumField(enum_type=PlayType, index=True, description="玩法类型")
    level_desc = fields.CharField(max_length=28, description="场次等级")
    tid = fields.CharField(max_length=28, description="房间id")
    score = fields.BigIntField(null=True, default=0, description="分数")
    rank_score = fields.IntField(default=0, description="段位分")
    is_win = fields.BooleanField(default=False, description='是否赢')

    class Meta:
        table = "records_game_grade"


class RecordsUserLuck(DBModel):
    """运气记录"""
    _SPLIT_TYPE = 3

    uid = fields.IntField(max_length=28, index=True, null=False, description='玩家ID')
    time_node = fields.BigIntField(max_length=28, null=True, default=0, description='运势时间节点')
    award_type = fields.IntEnumField(enum_type=AwardType, description='运气奖励类型')
    luck = fields.SmallIntField(max_length=4, null=True, default=0, description='运势等级')
    luck_desc = fields.CharField(max_length=256, null=True, default='', description='运势描述')

    class Meta:
        table = "records_user_luck"
        unique_together = (("uid", "time_node"),)


class RecordsUserSign(DBModel):
    """ 签到记录 """
    _SPLIT_TYPE = 3

    uid = fields.IntField(max_length=28, index=True, null=False, description='玩家ID')
    time_node = fields.BigIntField(max_length=28, null=True, default=0, description='最新签到时间')
    award_type = fields.IntEnumField(enum_type=AwardType, default=0, description='签到奖励类型')
    sign_in_date = fields.JSONField(null=True, description='已签到的日期')
    sign_in_achieved = fields.JSONField(null=True, description='已领取的累计奖励')

    class Meta:
        table = "records_user_sign"
        unique_together = (("uid", "award_type"),)


class RecordsUserActiveScore(DBModel):
    """活跃值记录"""
    _SPLIT_TYPE = 3

    uid = fields.IntField(max_length=28, index=True, null=False, description='玩家ID')
    time_node = fields.BigIntField(max_length=28, null=True, default=0, description='活跃时间节点')
    active_score = fields.IntField(max_length=10, null=True, default=0, description="活跃值")
    active_achieved = fields.JSONField(null=True, description='已领取的累计奖励')

    class Meta:
        table = "records_user_active_score"
        unique_together = (("uid", "time_node"),)


class RecordsUserAwards(DBModel):
    """奖励记录"""
    _SPLIT_TYPE = 2

    uid = fields.IntField(max_length=28, index=True, null=False, description='玩家ID')
    time_node = fields.BigIntField(max_length=28, null=True, default=0, description='最新领奖时间')
    # TODO 注释掉，后续需要
    # award = fields.ForeignKeyField('lucky_game.ConfAward', related_name='conf_award')
    award_type = fields.IntEnumField(enum_type=AwardType, index=True, default=0, description='奖励类型')
    receive_times = fields.IntField(max_length=10, null=True, default=0, description='领奖次数')

    class Meta:
        table = "records_user_awards"
        unique_together = (("uid", "award_id"),)


class RecordsUserRaffle(DBModel):
    """ 抽奖记录 """
    _SPLIT_TYPE = 2

    uid = fields.IntField(max_length=28, index=True, null=False, description='玩家ID')
    time_node = fields.BigIntField(max_length=28, null=True, default=0, description='最新抽奖时间')
    award_type = fields.IntEnumField(enum_type=AwardType, default=0, description='抽奖奖励类型')
    raffle_in_date = fields.JSONField(null=True, description='已抽奖的日期')
    raffle_in_achieved = fields.JSONField(null=True, description='已抽奖的累计奖励')

    class Meta:
        table = "records_user_raffle"
        unique_together = (("uid", "award_type"),)


class RecordsUserEvent(DBModel):
    """ 用户事件记录 """
    _SPLIT_TYPE = 2

    uid = fields.IntField(max_length=28, index=True, null=False, description='玩家ID')
    event_tracking = fields.IntEnumField(enum_type=EventTracking, index=True, description='事件埋点')
    event_desc = fields.CharField(max_length=128, null=True, description='事件描述')
    event_time = fields.BigIntField(max_length=28, null=True, default=0, description='事件时间')

    class Meta:
        table = "records_user_event"
        unique_together = (("uid", "event_tracking"),)