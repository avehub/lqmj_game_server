from nsanic.libs import tool_dt
from nsanic.orm.db_model import DBModel
from tortoise import fields
from tortoise.fields.base import OnDelete
from lucky_game.config import conf_srv as conf
from common.public.enum_const import Sex, PlayType, Switch, LevelType, RankingDanLevel, MonsterCardType, RegionEnum, \
    UserSource, ChatChannel
from lucky_game.const import QuickChatType, PlatForm, MailSta, PullSta, AchieveType, AwardType, GoodsType, \
    TaskType, PayType, AddType, StoreType, RandType, ActivityType, GotType, MailType, CompleteSta, JumpTarget, \
    ConditionType, ActivitySta, PayMode, DeliverStatus, OrderStatus, CosmeticType, GamePropType, BagSta, PutType, \
    CellType, EventType, LvDefendType, SeasonStatus, AdEventType, FriendshipSta, InteractPropType, PlayTemplate


class Users(DBModel):
    """用户总表"""
    uid = fields.IntField(max_length=28, pk=True, default=500000, description='玩家ID')
    name = fields.CharField(max_length=20, null=True, default='', description='玩家昵称')
    sex = fields.IntEnumField(enum_type=Sex, default=Sex.DEFAULT, description="性别")
    phone = fields.CharField(max_length=18, null=True, index=True, description='手机号码')
    email = fields.CharField(max_length=256, null=True, description='邮箱')
    address = fields.CharField(max_length=256, null=True, default='', description='所在地址')
    id_card = fields.CharField(max_length=20, null=True, default='', description='身份证')
    real_name = fields.CharField(max_length=32, null=True, default='', description='玩家真实姓名')
    pi = fields.CharField(max_length=64, index=True, default='', description='已通过实名认证用户的唯一标识')
    gold = fields.DecimalField(max_digits=65, null=True, decimal_places=2, default=0, description="金币")
    diamond = fields.IntField(max_digits=20, null=True, default=0, description="钻石")
    room_card = fields.IntField(max_digits=20, null=True, default=0, description="房卡")
    yellow_diamond = fields.IntField(max_digits=20, null=True, default=0, description="黄钻")
    vip = fields.IntField(max_digits=2, default=0, null=True, description="VIP等级")
    platform = fields.IntEnumField(enum_type=PlatForm, index=True, description="平台：1网页 2微信公众号 3原生app 4微信小游戏 5支付宝小游戏 6抖音小游戏")
    dev_ident = fields.CharField(max_length=18, null=True, default='', description='设备标识')
    safe_key = fields.CharField(max_length=18, null=True, default='', description='安全密钥')
    valid_key = fields.CharField(max_length=16, null=True, default='', description='验证密钥')
    tst_mark = fields.BooleanField(null=True, default=False, description='测试号标记')
    ip = fields.CharField(max_length=128, null=True, default='', description='登陆IP')
    region = fields.CharField(max_length=20, null=True, default='', description='地区/行政区域')
    country = fields.CharField(max_length=16, null=True, default='CN', description='国家域名')
    openid = fields.CharField(max_length=128, null=True, description='微信小游戏授权用户唯一标识')
    unionid = fields.CharField(max_length=128, null=True, description='微信平台用户授权唯一标识')
    ban_time = fields.BigIntField(null=True, default=0, description='封禁时间：0未封禁 -1永久封禁 大于0为封禁时间')
    updated = fields.BigIntField(null=True, default=0, description='更新时间')

    class Meta:
        unique_together = (("platform", "openid"), ("platform", "unionid"))  # 联合主键


class LogUserBehavior(DBModel):
    """用户行为日志表"""
    id = fields.BigIntField(max_length=10, pk=True, description='主键ID')
    uid = fields.IntField(max_length=28, null=True, default=0, description='玩家ID')
    behavior_type = fields.CharField(max_length=64, null=True, default='', description='行为类型（接口方法）')
    behavior_info = fields.CharField(max_length=256, null=True, default='', description='行为参数（接口参数）')

    class Meta:
        table = "log_user_behavior"


class Clubs(DBModel):
    """茶馆信息表"""
    id = fields.IntField(max_length=6, pk=True, default=100000, description='茶馆ID')
    uid = fields.IntField(max_length=28, index=True, description='馆主ID(玩家ID)')
    num = fields.IntField(max_length=6, null=True, default=1, description='茶馆人数')
    name = fields.CharField(max_length=20, null=True, description='茶馆名称')
    play_template = fields.IntEnumField(enum_type=PlayTemplate, null=True, default=PlayTemplate.MJ_XTMJ, description='常玩玩法')
    room_card = fields.IntField(max_length=20, null=True, default=0, description='茶馆基金（房卡）')
    other = fields.JSONField(null=True, default=None, description='其他设置：JSON存储')
    status = fields.IntField(max_length=2, null=True, default=0, description='状态：0正常')
    updated = fields.BigIntField(null=True, default=0, description='更新时间')


class ClubUsers(DBModel):
    """茶馆和用户关系表"""
    id = fields.IntField(max_length=10, pk=True, description='主键ID')
    club_id = fields.IntField(max_length=6, null=True, description='茶馆ID')
    uid = fields.IntField(max_length=28, null=True, description='馆主ID(玩家ID)')
    role = fields.IntField(max_length=2, null=True, default=0, description='角色:0普通成员 1管理员 9馆主')
    status = fields.IntField(max_length=2, null=True, default=0, description='成员状态：0正常 1小黑屋')
    updated = fields.BigIntField(null=True, default=0, description='更新时间')

    class Meta:
        unique_together = (("club_id", "uid"),)  # 联合主键
        table = "club_users"


class ClubGroups(DBModel):
    """茶馆隔离组表"""
    id = fields.IntField(max_length=10, pk=True, description='分组ID')
    club_id = fields.IntField(max_length=6, null=True, description='茶馆ID')
    uid = fields.IntField(max_length=28, null=True, description='玩家ID')

    class Meta:
        unique_together = (("club_id", "uid"),)  # 联合主键
        table = "club_groups"


class ExtraClubBehavior(DBModel):
    """茶馆操作行为记录表"""
    id = fields.IntField(max_length=10, pk=True, default=0, description='行为ID')
    club_id = fields.IntField(max_length=6, null=True, description='茶馆ID')
    uid = fields.IntField(max_length=28, null=True, description='玩家ID')
    type = fields.IntField(max_length=2, null=True, default=0, description='类型：1加入茶馆申请 2小黑屋 3隔离')
    status = fields.IntField(max_length=2, null=True, default=0, description='状态，类型==1：0未审批 1拒绝 99通过，类型==2/3:99成功')
    check_uid = fields.IntField(max_length=28, null=True, description='审批/操作玩家ID')
    updated = fields.BigIntField(null=True, default=0, description='更新时间')

    class Meta:
        table = "extra_club_behavior"


class GameRooms(DBModel):
    """游戏房间关系表"""
    id = fields.IntField(max_length=10, pk=True, default=0, description='房间ID')
    club_id = fields.IntField(max_length=6, null=True, description='茶馆ID,无茶馆为0')
    uid = fields.IntField(max_length=28, null=True, description='房主ID(玩家ID)')
    platform = fields.IntField(max_length=2, null=True, description='平台: 1微信小游戏 2APP 3H5')
    is_template = fields.IntField(max_length=2, null=True, default=0, description='是否为模板（茶馆玩法列表）:0否 1是')
    room_rule = fields.JSONField(null=True, default=None, description='房间玩法规则：JSON存储')
    max_players = fields.IntField(max_length=2, null=True, default=0, description='最大人数')
    current_players = fields.IntField(max_length=2, null=True, default=0, description='当前人数')
    status = fields.IntField(max_length=2, null=True, default=0, description='房间状态：0有空 1已满')
    updated = fields.BigIntField(null=True, default=0, description='更新时间')

    class Meta:
        table = "game_rooms"


class ExtraClubEvent(DBModel):
    """茶馆日常事件相关记录表"""
    id = fields.IntField(max_length=10, pk=True, description='事件ID')
    club_id = fields.IntField(max_length=6, index=True, description='茶馆ID')
    type = fields.IntField(max_length=2, index=True, default=0, description='类型：1基金充值 2基金消耗 3入馆审批记录')
    uid = fields.IntField(max_length=28, index=True, description='玩家ID（发起方）')
    explain = fields.CharField(max_length=256, null=True, default='', description='说明:记录XX管理员（ID：xx）通过XX玩家（ID：xx）加入茶馆; XX玩家（ID：xx）消耗XX基金创建了xx玩法（房间号：xx）; XX玩家（ID：xx）为茶馆充值基金xx')

    class Meta:
        table = "extra_club_event"


class RecordsGames(DBModel):
    """游戏战绩记录表"""
    id = fields.IntField(max_length=10, pk=True, description='战绩ID')
    club_id = fields.IntField(max_length=6, index=True, default=0, description='茶馆ID，玩家无茶馆值为0')
    uid = fields.IntField(max_length=28, index=True, description='玩家ID')
    room_id = fields.IntField(max_length=10, index=True, description='房间ID')
    round_total = fields.IntField(max_length=2, null=True, default=0, description='总局数')
    round_num = fields.IntField(max_length=2, null=True, default=0, description='当前局数')
    current_players = fields.IntField(max_length=2, null=True, default=0, description='对局人数')
    best_uid = fields.IntField(max_length=28, index=True, description='最佳玩家ID')
    play_template = fields.IntEnumField(enum_type=PlayTemplate, null=True, default=PlayTemplate.MJ_XTMJ, description='常玩玩法')
    room_rule = fields.JSONField(null=True, default=None, description='房间玩法规则：JSON存储')
    result = fields.JSONField(null=True, default=None, description='游戏结果：JSON存储')

    class Meta:
        table = "records_games"


class Configs(DBModel):
    """配置信息表"""
    id = fields.IntField(max_length=10, pk=True, description='配置ID')
    type = fields.IntField(max_length=2, null=True, default=0, description='配置类型：0公共（含1、2、3） 1微信小游戏 2H5 3APP 9管理后台')
    name = fields.CharField(max_length=20, null=True, description='配置名称')
    label = fields.CharField(max_length=20, unique=True, description='唯一标识')
    content = fields.JSONField(null=True, default=None, description='配置内容：JSON存储')
    updated = fields.BigIntField(null=True, default=0, description='更新时间')


class ExtraUserResourceChanges(DBModel):
    """用户资源变动记录表"""
    id = fields.IntField(max_length=10, pk=True, description='变动ID')
    uid = fields.IntField(max_length=28, index=True, description='玩家ID')
    status = fields.IntField(max_length=2, null=True, default=0, description='方式：1充值 0消耗')
    currency = fields.IntField(max_length=2, null=True, default=0, description='类型：0无 1金币 2钻石 3房卡 4黄钻 5人民币')
    num = fields.IntField(max_length=10, null=True, default=0, description='变动数量')
    explain = fields.CharField(max_length=256, null=True, default='', description='其他说明')

    class Meta:
        table = "extra_user_resource_changes"


class ExtraUserReports(DBModel):
    """用户举报信息记录表"""
    id = fields.IntField(max_length=10, pk=True, description='举报ID')
    uid = fields.IntField(max_length=28, index=True, description='玩家ID')
    target_type = fields.IntField(max_length=2, null=True, description='举报类型：1玩家 2茶馆')
    target_id = fields.IntField(max_length=28, null=True, description='被举报对象ID')
    reason = fields.CharField(max_length=256, null=True, default='', description='举报原因')
    receiver_id = fields.CharField(max_length=256, null=True, default='', description='服务人员ID')
    status = fields.IntField(max_length=2, null=True, default=0, description='状态：0未处理 99已处理')
    updated = fields.BigIntField(null=True, default=0, description='更新时间')

    class Meta:
        table = "extra_user_reports"


