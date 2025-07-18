from tortoise import fields
from nsanic.orm.db_model import DBModel
from common.public.enum_const import DbKey, LoginWay, ServiceEnum, BanType
from c_services.cs_mahjong.const import PlayType


class RecordsGameUserLogin(DBModel):
    """登录记录"""
    _SPLIT_TYPE = 2

    uid = fields.IntField(max_length=28, index=True, null=True, default=0, description='玩家ID')
    login_way = fields.IntEnumField(enum_type=LoginWay, index=True, null=True, description='登录方式')
    dev_id = fields.CharField(max_length=32, index=True, null=True, default='', description='设备ID')
    dev_name = fields.CharField(max_length=20, index=True, null=True, default='H5', description='设备名')
    platform = fields.CharField(max_length=20, index=True, null=True, default=0, description='登陆平台')
    login_ip = fields.CharField(max_length=128, null=True, default='', description='登录IP')

    class Meta:
        table = "records_game_user_login"


class RecordsGoldStatement(DBModel):
    """ 金币流水记录 """
    _SPLIT_TYPE = 2

    uid = fields.IntField(max_length=28, index=True, null=True, default=0, description='玩家ID')
    count = fields.DecimalField(max_digits=65, decimal_places=0, default=0, description="当前数量")
    res_count = fields.DecimalField(max_digits=65, decimal_places=0, default=0, description="剩余数量")
    g_type = fields.SmallIntField(default=1, description="金币类型：默认1")
    reason_id = fields.IntField(max_length=11, default=0, description='原因id')
    reason_desc = fields.CharField(max_length=28, default='', description='原因描述')

    class Meta:
        table = "records_gold_statement"

    @classmethod
    async def insert_one(cls, uid, **kwargs):
        insert_data = {
            "uid": uid,
            "count": kwargs.get("count") or 0,
            "res_count": kwargs.get("res_count") or 0,
            "g_type": kwargs.get("g_type") or 1,
            "reason_id": kwargs.get("reason_id") or 0,
            "reason_desc": kwargs.get("reason_desc") or "",
        }
        await cls.split_add_one(insert_data, db_key=DbKey.LOG)


class RecordsDiamondStatement(DBModel):
    """ 钻石流水记录 """
    _SPLIT_TYPE = 2

    uid = fields.IntField(max_length=28, index=True, null=True, default=0, description='玩家ID')
    count = fields.IntField(max_length=32, default=0, description="当前数量")
    res_count = fields.IntField(max_length=64, default=0, description="剩余数量")
    d_type = fields.SmallIntField(default=1, description="钻石类型：默认1")
    reason_id = fields.IntField(max_length=11, default=0, description='原因id')
    reason_desc = fields.CharField(max_length=28, default='', description='原因描述')

    class Meta:
        table = "records_diamond_statement"

    @classmethod
    async def insert_one(cls, uid, **kwargs):
        insert_data = {
            "uid": uid,
            "count": kwargs.get("count") or 0,
            "res_count": kwargs.get("res_count") or 0,
            "d_type": kwargs.get("d_type") or 1,
            "reason_id": kwargs.get("reason_id") or 0,
            "reason_desc": kwargs.get("reason_desc") or "",
        }
        await cls.split_add_one(insert_data, db_key=DbKey.LOG)


class RecordsRoomCardsStatement(DBModel):
    """ 房卡流水记录 """
    _SPLIT_TYPE = 2

    uid = fields.IntField(max_length=28, index=True, null=True, default=0, description='玩家ID')
    count = fields.IntField(max_length=12, default=0, description="当前数量")
    res_count = fields.IntField(max_digits=32, default=0, description="剩余数量")
    r_type = fields.SmallIntField(default=1, description="房卡类型：默认1")
    reason_id = fields.IntField(max_length=11, default=0, description='原因id')
    reason_desc = fields.CharField(max_length=28, default='', description='原因描述')

    class Meta:
        table = "records_room_cards_statement"


class RecordsUserGame(DBModel):
    """ 用户游戏记录 """
    _SPLIT_TYPE = 2

    uid = fields.IntField(max_length=28, index=True, null=True, default=0, description='玩家ID')
    cs_type = fields.IntEnumField(enum_type=ServiceEnum, index=True, null=True, description='子服务')
    play_type = fields.IntEnumField(enum_type=PlayType, index=True, null=True, description='玩法类型')
    level = fields.IntField(max_length=12, index=True, null=True, default=0, description='游戏场次')
    extra_info = fields.JSONField(null=True, description="额外信息（可记录对局信息）")

    class Meta:
        table = "records_user_game"


class RecordsUserBan(DBModel):
    """ 封禁记录 """
    _SPLIT_TYPE = 2

    operator = fields.CharField(max_length=28, default='', description='操作员')
    uid = fields.IntField(max_length=28, index=True, null=True, default=0, description='玩家ID')
    reason = fields.CharField(max_length=28, default='', description='原因描述（为何封禁）')
    ban_type = fields.IntEnumField(enum_type=BanType, index=True, default=BanType.DEFAULT.val, description='封禁类型')
    ban_time = fields.BigIntField(null=True, index=True, default=0,
                                  description='封禁时间：0未封禁 -1永久封禁 大于0为封禁时间')

    class Meta:
        table = "records_user_ban"
