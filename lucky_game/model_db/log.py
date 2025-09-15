from tortoise import fields
from nsanic.orm.db_model import DBModel
from common.public.enum_const import DbKey, LoginWay, ServiceEnum, BanType
from c_services.cs_mahjong.const import PlayType
from lucky_game.const import PlatForm


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

class RecordsAdEvent(DBModel):
    """广告事件记录"""
    campaign_type = fields.SmallIntField(description='参与类型：1活动 2游戏', )
    id = fields.IntField(pk=True, )
    ip = fields.CharField(max_length=32, null=True, description='IP地址', )
    os = fields.CharField(max_length=32, null=True, description='操作系统平台', )
    platform = fields.IntEnumField(enum_type=PlatForm, index=True,
                                   description="平台：1网页 2微信公众号 3原生app 4微信小游戏 5支付宝小游戏 6抖音小游戏")
    status = fields.SmallIntField(description='广告播放状态：成功99 失败1', )
    type_id = fields.IntField(description='类型ID', )
    uid = fields.IntField(description='玩家ID', )

    class Meta:
        table = "records_ad_event"

