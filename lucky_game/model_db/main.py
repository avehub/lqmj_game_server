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


class User(DBModel):
    """用户总表"""
    uid = fields.IntField(max_length=28, pk=True, default=500000, description='玩家ID')
    name = fields.CharField(max_length=20, null=True, default='', description='玩家昵称')
    avatar = fields.CharField(max_length=256, null=True, default='', description='头像地址')
    sex = fields.IntEnumField(enum_type=Sex, default=Sex.DEFAULT, description="性别")
    phone = fields.CharField(max_length=18, null=True, index=True, description='手机号码')
    email = fields.CharField(max_length=256, null=True, description='邮箱')
    address = fields.CharField(max_length=256, null=True, default='', description='所在地址')
    id_card = fields.CharField(max_length=20, null=True, default='', description='身份证')
    real_name = fields.CharField(max_length=32, null=True, default='', description='玩家真实姓名')
    album = fields.CharField(max_length=256, null=True, default='', description='相册')
    pi = fields.CharField(max_length=64, index=True, default='', description='已通过实名认证用户的唯一标识')
    gold = fields.DecimalField(max_digits=65, null=True, decimal_places=2, default=0, description="金币")
    diamond = fields.IntField(max_digits=20, null=True, default=0, description="钻石")
    room_card = fields.IntField(max_digits=20, null=True, default=0, description="房卡")
    yellow_diamond = fields.IntField(max_digits=20, null=True, default=0, description="黄钻")
    vip = fields.SmallIntField(max_length=2, default=0, null=True, description="VIP等级")
    platform = fields.IntEnumField(enum_type=PlatForm, index=True, description="平台：1网页 2微信公众号 3原生app 4微信小游戏 5支付宝小游戏 6抖音小游戏")
    dev_ident = fields.CharField(max_length=18, null=True, default='', description='设备标识')
    safe_key = fields.CharField(max_length=18, null=True, default='', description='安全密钥')
    valid_key = fields.CharField(max_length=16, null=True, default='', description='验证密钥')
    tst_mark = fields.BooleanField(null=True, default=False, description='测试号标记')
    ip = fields.CharField(max_length=128, null=True, default='', description='登陆IP')
    region = fields.CharField(max_length=20, null=True, default='', description='地区/行政区域')
    country = fields.CharField(max_length=16, null=True, default='CN', description='国家域名')
    openid = fields.CharField(max_length=128, null=True, default='', description='微信小游戏授权用户唯一标识')
    unionid = fields.CharField(max_length=128, null=True, default='', description='微信平台用户授权唯一标识')
    apple_id = fields.CharField(max_length=128, null=True, default='', description='苹果平台用户授权唯一标识')
    ban_time = fields.BigIntField(null=True, default=0, description='封禁时间：0未封禁 -1永久封禁 大于0为封禁时间')
    updated = fields.BigIntField(null=True, default=0, description='更新时间')

    class Meta:
        unique_together = (("platform", "openid"), ("platform", "union_id"))  # 联合主键


class UserFollows(DBModel):
    """用户关注关系表"""
    id = fields.BigIntField(max_length=10, pk=True, description='主键ID')
    uid = fields.IntField(max_length=28, index=True, default=0, description='玩家ID')
    follow_uid = fields.CharField(max_length=28, null=True, default='', description='被关注玩家ID')

    class Meta:
        table = "user_follows"


class ExtraUserPraises(DBModel):
    """用户点赞记录表"""
    id = fields.BigIntField(max_length=10, pk=True, description='主键ID')
    uid = fields.IntField(max_length=28, index=True, default=0, description='玩家ID')
    praise_uid = fields.CharField(max_length=28, null=True, default='', description='被点赞玩家ID')

    class Meta:
        table = "extra_user_praises"


class RecordsUserVisits(DBModel):
    """用户访问记录表"""
    id = fields.BigIntField(max_length=10, pk=True, description='主键ID')
    uid = fields.IntField(max_length=28, index=True, default=0, description='玩家ID')
    visit_uid = fields.CharField(max_length=28, null=True, default='', description='被访问玩家ID')

    class Meta:
        table = "records_user_visits"


class UserBags(DBModel):
    """用户背包表"""
    id = fields.BigIntField(max_length=10, pk=True, description='主键ID')
    uid = fields.IntField(max_length=28, index=True, default=0, description='玩家ID')
    good_id = fields.IntField(max_length=28, null=True, default=0, description='商品/道具ID')
    count = fields.IntField(max_length=28, null=True, default=0, description='数量')
    end_time = fields.DatetimeField(null=True, default=None, description='商品有效期')
    updated = fields.BigIntField(null=True, default=0, description='更新时间')

    class Meta:
        table = "user_bags"


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
    cs_type = fields.IntField(max_length=10, default=0, description="子服务类型")
    play_type = fields.IntEnumField(enum_type=PlayType, default=PlayType.CLASSICAL, description="玩法类型")
    room_card = fields.IntField(max_length=20, null=True, default=0, description='茶馆基金（房卡）')
    other = fields.JSONField(null=True, description='其他设置：JSON存储')
    status = fields.SmallIntField(max_length=2, null=True, default=0, description='状态：0正常')
    updated = fields.BigIntField(null=True, default=0, description='更新时间')


class ClubUsers(DBModel):
    """茶馆和用户关系表"""
    id = fields.IntField(max_length=10, pk=True, description='主键ID')
    club_id = fields.IntField(max_length=6, null=True, description='茶馆ID')
    uid = fields.IntField(max_length=28, null=True, description='玩家ID')
    role = fields.SmallIntField(max_length=2, null=True, default=0, description='角色:0普通成员 1管理员 9馆主')
    status = fields.SmallIntField(max_length=2, null=True, default=0, description='成员状态：0正常 1小黑屋')
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
    club_id = fields.IntField(max_length=6, index=True, description='茶馆ID')
    uid = fields.IntField(max_length=28, index=True, description='玩家ID')
    type = fields.SmallIntField(max_length=2, null=True, default=0, description='类型：1加入茶馆申请 2小黑屋 3隔离')
    status = fields.SmallIntField(max_length=2, null=True, default=0, description='状态，类型==1：0未审批 1拒绝 99通过，类型==2/3:99成功')
    check_uid = fields.IntField(max_length=28, null=True, default=0, description='审批/操作玩家ID')
    updated = fields.BigIntField(null=True, default=0, description='更新时间')

    class Meta:
        table = "extra_club_behavior"


class ConfGameRoomRules(DBModel):
    """游戏房间规则配置表"""
    id = fields.IntField(max_length=10, pk=True, description='规则ID')
    pip = fields.IntField(max_length=10, index=True, default=0, description='父级ID')
    rule_type = fields.SmallIntField(max_length=2, null=True, default=0, description='规则类型')
    rule_name = fields.CharField(max_length=20, null=True, description='规则名')
    rule_info = fields.JSONField(null=True, description='规则信息：JSON存储')

    class Meta:
        table = "conf_game_room_rules"


class ClubRoomTemplates(DBModel):
    """茶馆房间模版表"""
    id = fields.IntField(max_length=10, pk=True, default=0, description='房间ID')
    club_id = fields.IntField(max_length=6, index=True, description='茶馆ID')
    platform = fields.SmallIntField(max_length=2, null=True, description='平台: 1微信小游戏 2APP 3H5')
    cs_type = fields.IntField(max_length=10, default=0, description="子服务类型")
    play_type = fields.IntEnumField(enum_type=PlayType, default=PlayType.CLASSICAL, description="玩法类型")
    room_rule = fields.JSONField(null=True, description='房间玩法规则：JSON存储')
    max_players = fields.SmallIntField(max_length=2, null=True, default=0, description='最大人数')
    current_players = fields.SmallIntField(max_length=2, null=True, default=0, description='当前人数')
    updated = fields.BigIntField(null=True, default=0, description='更新时间')

    class Meta:
        table = "club_room_templates"


class GameRooms(DBModel):
    """游戏房间关系表"""
    id = fields.IntField(max_length=10, pk=True, default=0, description='房间ID')
    club_id = fields.IntField(max_length=6, null=True, description='茶馆ID,无茶馆为0')
    uid = fields.IntField(max_length=28, null=True, description='房主ID(玩家ID)')
    platform = fields.SmallIntField(max_length=2, null=True, description='平台: 1微信小游戏 2APP 3H5')
    cs_type = fields.IntField(max_length=10, default=0, description="子服务类型")
    play_type = fields.IntEnumField(enum_type=PlayType, default=PlayType.CLASSICAL, description="玩法类型")
    room_rule = fields.JSONField(null=True, description='房间玩法规则：JSON存储')
    max_players = fields.SmallIntField(max_length=2, null=True, default=0, description='最大人数')
    current_players = fields.SmallIntField(max_length=2, null=True, default=0, description='当前人数')
    status = fields.SmallIntField(max_length=2, null=True, default=0, description='房间状态：0有空 1已满')
    updated = fields.BigIntField(null=True, default=0, description='更新时间')

    class Meta:
        table = "game_rooms"


class ExtraClubEvent(DBModel):
    """茶馆日常事件相关记录表"""
    id = fields.IntField(max_length=10, pk=True, description='事件ID')
    club_id = fields.IntField(max_length=6, index=True, description='茶馆ID')
    type = fields.SmallIntField(max_length=2, index=True, default=0, description='类型：1基金充值 2基金消耗 3入馆审批记录')
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
    round_total = fields.SmallIntField(max_length=2, null=True, default=0, description='总局数')
    round_num = fields.SmallIntField(max_length=2, null=True, default=0, description='当前局数')
    current_players = fields.SmallIntField(max_length=2, null=True, default=0, description='对局人数')
    best_uid = fields.IntField(max_length=28, index=True, description='最佳玩家ID')
    cs_type = fields.IntField(max_length=10, default=0, description="子服务类型")
    play_type = fields.IntEnumField(enum_type=PlayType, default=PlayType.CLASSICAL, description="玩法类型")
    room_rule = fields.JSONField(null=True, description='房间玩法规则：JSON存储')
    result = fields.JSONField(null=True, description='游戏结果：JSON存储')

    class Meta:
        table = "records_games"


class ExtraGameRoom(DBModel):
    """游戏房间记录表"""
    id = fields.IntField(max_length=10, pk=True, description='记录ID')
    club_id = fields.IntField(max_length=6, index=True, description='茶馆ID，玩家无茶馆值为0')
    room_id = fields.IntField(max_length=10, index=True, description='房间ID')
    room_rule = fields.JSONField(null=True, description='房间玩法规则：JSON存储')
    cs_type = fields.IntField(max_length=10, default=0, description="子服务类型")
    play_type = fields.IntEnumField(enum_type=PlayType, default=PlayType.CLASSICAL, description="玩法类型")
    current_players = fields.SmallIntField(max_length=2, null=True, default=0, description='对局人数')
    room_uids = fields.CharField(max_length=64, null=True, description='房间玩家ID（多个ID用英文,分割）')

    class Meta:
        table = "extra_game_room"


class ConfJson(DBModel):
    """简单配置"""
    conf_id = fields.CharField(pk=True, max_length=128, null=False, description='配置名')
    conf_data = fields.JSONField(null=False, description='具体配置')
    desc = fields.CharField(max_length=256, null=True, default='', description='描述')
    update_time = fields.IntField(max_length=28, null=True, default=0, description='更新时间')

    class Meta:
        table = "conf_json"


class ExtraUserResourceChanges(DBModel):
    """用户资源变动记录表"""
    id = fields.IntField(max_length=10, pk=True, description='变动ID')
    uid = fields.IntField(max_length=28, index=True, description='玩家ID')
    status = fields.SmallIntField(max_length=2, null=True, default=0, description='方式：1充值 0消耗')
    currency = fields.SmallIntField(max_length=2, null=True, default=0, description='类型：0无 1金币 2钻石 3房卡 4黄钻 5人民币')
    num = fields.IntField(max_length=10, null=True, default=0, description='变动数量')
    explain = fields.CharField(max_length=256, null=True, default='', description='其他说明')

    class Meta:
        table = "extra_user_resource_changes"


class ExtraUserReports(DBModel):
    """用户举报信息记录表"""
    id = fields.IntField(max_length=10, pk=True, description='举报ID')
    uid = fields.IntField(max_length=28, index=True, description='玩家ID')
    target_type = fields.SmallIntField(max_length=2, null=True, description='举报类型：1玩家 2茶馆')
    target_id = fields.IntField(max_length=28, null=True, description='被举报对象ID')
    reason = fields.CharField(max_length=256, null=True, default='', description='举报原因')
    receiver_id = fields.CharField(max_length=256, null=True, default='', description='服务人员ID')
    status = fields.SmallIntField(max_length=2, null=True, default=0, description='状态：0未处理 99已处理')
    updated = fields.BigIntField(null=True, default=0, description='更新时间')

    class Meta:
        table = "extra_user_reports"


class Stores(DBModel):
    """商店信息表"""
    sid = fields.IntField(max_length=10, pk=True, description='商店ID')
    platform = fields.IntEnumField(enum_type=PlatForm, index=True, description="平台：1网页 2微信公众号 3原生app 4微信小游戏 5支付宝小游戏 6抖音小游戏")
    type = fields.SmallIntField(max_length=2, null=True, default=0, description='类型：1首充 2金币 3钻石 4房卡 5黄钻 6VIP 7周卡 8月卡 9终身卡')
    label = fields.CharField(max_length=64, unique=True, default=0, description="唯一标识")
    original = fields.DecimalField(max_digits=65, null=True, decimal_places=2, default=0, description="原价")
    price = fields.DecimalField(max_digits=65, null=True, decimal_places=2, default=0, description="售价")
    currency = fields.SmallIntField(max_length=2, null=True, default=0, description="货币类型：0无 1金币 2钻石 3房卡 4黄钻 5人民币")
    rank = fields.IntField(max_length=10, null=True, default=0, description="排序：越大越靠前")
    total = fields.IntField(max_length=10, null=True, default=0, description="总量：-1无限")
    purchase_limit = fields.CharField(max_length=256, null=True, default='', description='限购条件')
    name = fields.CharField(max_length=64, null=True, default=0, description="名称")
    img = fields.CharField(max_length=256, null=True, default='', description='图片')
    desc = fields.CharField(max_length=256, null=True, default='', description='描述')
    content = fields.JSONField(null=True, description='商品内容：JSON存储')
    status = fields.SmallIntField(max_length=2, null=True, description='状态：0下架 1上架')
    up_time = fields.DatetimeField(null=True, default=None, description='上架时间')
    down_time = fields.DatetimeField(null=True, default=None, description='下架时间')
    start_time = fields.DatetimeField(null=True, default=None, description='有效期开始时间')
    end_time = fields.DatetimeField(null=True, default=None, description='有效期结束时间')
    updated = fields.BigIntField(null=True, default=0, description='更新时间')


class Goods(DBModel):
    """商品(道具)表"""
    id = fields.IntField(max_length=10, pk=True, description='商品ID')
    sid = fields.IntField(max_length=10, index=True, default=0, description='商城ID')
    kind = fields.SmallIntField(max_length=2, null=True, description='特性：0虚拟 1实物')
    type = fields.SmallIntField(max_length=2, null=True, default=0, description='类型：1首充 2金币 3钻石 4房卡 5黄钻 6VIP 7周卡 8月卡 9终身卡')
    sku = fields.CharField(max_length=64, unique=True, default=0, description="商品唯一标识")
    total = fields.IntField(max_length=10, null=True, default=0, description="总量：-1无限")
    name = fields.CharField(max_length=64, null=True, default=0, description="商品名称")
    img = fields.CharField(max_length=256, null=True, default='', description='商品图片')
    desc = fields.CharField(max_length=256, null=True, default='', description='商品描述')
    content = fields.JSONField(null=True, description='商品内容：JSON存储')
    status = fields.SmallIntField(max_length=2, null=True, description='状态：0下架 1上架')
    start_time = fields.DatetimeField(null=True, default=None, description='商品有效期开始时间')
    end_time = fields.DatetimeField(null=True, default=None, description='商品有效期结束时间')
    bag_type = fields.SmallIntField(max_length=2, null=True, default=0, description='背包类型：0常规 1延时')
    updated = fields.BigIntField(null=True, default=0, description='更新时间')


class Orders(DBModel):
    """用户订单表"""
    id = fields.IntField(max_length=10, pk=True, description='变动ID')
    uid = fields.IntField(max_length=28, index=True, description='玩家ID')
    sid = fields.IntField(max_length=28, index=True, description='购买商店ID')
    platform = fields.IntEnumField(enum_type=PlatForm, index=True, description="平台：1网页 2微信公众号 3原生app 4微信小游戏 5支付宝小游戏 6抖音小游戏")
    amount = fields.DecimalField(max_digits=65, null=True, decimal_places=2, default=0, description="支付金额")
    currency = fields.SmallIntField(max_length=2, null=True, default=0, description="购买资源支付类型：0无 1金币 2钻石 3房卡 4黄钻 5人民币")
    pay_mode = fields.IntEnumField(enum_type=PayMode, null=True, default=PayMode.NO_MODE, description="支付方式")
    num = fields.IntField(max_length=10, null=True, default=0, description="购买数量")
    order_no = fields.CharField(max_length=32, null=True, default=0, description="订单编号")
    out_order_no = fields.IntField(max_length=10, null=True, default=0, description="外部订单编号")
    prepay_id = fields.CharField(max_length=64, null=True, default='', description="外部支付标识")
    status = fields.SmallIntField(max_length=2, null=True, description='订单状态：0待支付 1支付失败 2订单关闭 99支付成功')
    explain = fields.CharField(max_length=256, null=True, default='', description='其他说明')
    updated = fields.BigIntField(null=True, default=0, description='更新时间')


class Guilds(DBModel):
    """ 牌友会表 """
    id = fields.IntField(max_length=10, pk=True, description='公会ID')
    name = fields.CharField(max_length=20, null=True, description='公会名称')
    logo = fields.CharField(max_length=256, null=True, description='公会logo')
    desc = fields.CharField(max_length=256, null=True, description='公会描述')
    updated = fields.DatetimeField(null=True, default=0, description='更新时间')


class GuildUsers(DBModel):
    """ 牌友会成员关系表 """
    id = fields.IntField(max_length=10, pk=True, description='关系ID')
    guild_id = fields.IntField(max_length=10, index=True, description='公会ID')
    uid = fields.IntField(max_length=28, index=True, description='玩家ID')
    week_glory = fields.IntField(max_length=10, null=True, default=0, description='本周荣耀值')
    last_week_glory = fields.IntField(max_length=10, null=True, default=0, description='上周荣耀值')
    updated = fields.DatetimeField(null=True, default=0, description='更新时间')

    class Meta:
        unique_together = (("guild_id", "uid"),)  # 联合主键
        table = "guild_users"


class Awards(DBModel):
    """ 奖励信息表 """
    id = fields.IntField(max_length=10, pk=True, description='奖励ID')
    type = fields.SmallIntField(max_length=2, index=True, description='奖励类型：1系统 2牌友会 2活动 3任务 ')
    level = fields.SmallIntField(max_length=2, index=True, description='奖励等级')
    name = fields.CharField(max_length=20, null=True, description='奖励名称')
    content = fields.JSONField(null=True, description='奖励内容：JSON存储')
    updated = fields.DatetimeField(null=True, default=0, description='更新时间')


class AwardGains(DBModel):
    """ 奖励领取记录表 """
    id = fields.IntField(max_length=10, pk=True, description='领取ID')
    award_id = fields.IntField(max_length=10, index=True, description='奖励ID')
    uid = fields.IntField(max_length=28, index=True, description='玩家ID')
    status = fields.SmallIntField(max_length=2, null=True, description='领取状态：0未领取 99已领取')
    updated = fields.DatetimeField(null=True, default=0, description='更新时间')

    class Meta:
        unique_together = (("award_id", "uid"),)  # 联合主键
        table = "award_gains"


class Mails(DBModel):
    """ 邮件总表 """
    mail_id = fields.IntField(max_length=20, pk=True, default=1, description='邮件ID')
    mail_type = fields.IntEnumField(enum_type=MailType, index=True, default=MailType.SYS, description='邮件类型')
    title = fields.CharField(max_length=64, default='', description="主题/标题")
    content = fields.CharField(max_length=255, default='', description="邮件内容")
    attachment = fields.JSONField(null=True, description="附件信息：如奖励ID和数量等")
    sender = fields.CharField(max_length=28, default='', description="发送者")
    receiver = fields.IntField(max_length=28, index=True, null=False, description='接收者：玩家ID')
    mail_sta = fields.IntEnumField(enum_type=MailSta, index=True, default=MailSta.UNREAD, description="邮件状态")
    attachment_sta = fields.IntEnumField(enum_type=PullSta, index=True, default=PullSta.UN_PULL, description="附件状态")
    receive_time = fields.BigIntField(max_length=28, null=True, default=0, description="接收时间")
    exp_time = fields.BigIntField(max_length=28, null=True, default=0, description="过期时间")

    class Meta:
        table = "mails"
        indexes = (("receiver", "mail_sta", "exp_time"),)


class ConfServerAddr(DBModel):
    """服务器配置"""
    sid = fields.IntField(max_length=10, null=True, default=0, description="服务ID")
    addr = fields.CharField(max_length=32, null=True, default='', description='地址')
    path = fields.CharField(max_length=32, null=True, default='', description='路径')
    status = fields.SmallIntField(max_length=2, null=True, default=0, description='状态 0关闭 1开启')

    class Meta:
        table = "conf_server_addr"






