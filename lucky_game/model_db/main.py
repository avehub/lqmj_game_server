from nsanic.libs import tool_dt
from nsanic.orm.db_model import DBModel
from tortoise import fields
from tortoise.fields.base import OnDelete
from lucky_game.config import conf_srv as conf
from common.public.enum_const import Sex, Switch, LevelType, RankingDanLevel, MonsterCardType, RegionEnum, \
    UserSource, ChatChannel
from lucky_game.const import QuickChatType, PlatForm, MailSta, PullSta, AchieveType, AwardType, GoodsType, \
    TaskType, PayType, AddType, StoreType, RandType, ActivityType, GotType, MailType, CompleteSta, JumpTarget, \
    ConditionType, ActivitySta, PayMode, DeliverStatus, OrderStatus, CosmeticType, GamePropType, BagSta, PutType, \
    CellType, EventType, LvDefendType, SeasonStatus, AdEventType, FriendshipSta, InteractPropType, PlayTemplate
from c_services.const.cs_enum_const import RoomStatus
from c_services.cs_mahjong.const import PlayType
from lucky_admin.const import AdminStatus, AdminPermission, UserGroup, AnnouncementsStatus, WeightEnum, \
    BackTaskSta


class User(DBModel):
    """用户总表"""
    uid = fields.IntField(max_length=28, pk=True, default=500000, description='玩家ID')
    name = fields.CharField(max_length=32, null=True, default='', description='玩家昵称')
    avatar = fields.CharField(max_length=256, null=True, default='', description='头像地址')
    sex = fields.IntEnumField(enum_type=Sex, default=Sex.DEFAULT, description="性别")
    phone = fields.CharField(max_length=18, null=True, index=True, description='手机号码')
    email = fields.CharField(max_length=256, null=True, description='邮箱')
    address = fields.CharField(max_length=256, null=True, default='', description='所在地址')
    id_card = fields.CharField(max_length=20, null=True, default='', description='身份证')
    real_name = fields.CharField(max_length=32, null=True, default='', description='玩家真实姓名')
    album = fields.CharField(max_length=256, null=True, default='', description='相册')
    pi = fields.CharField(max_length=64, index=True, default='', description='已通过实名认证用户的唯一标识')
    discount = fields.FloatField(max_digits=3, null=True, decimal_places=2, default=1, description="消费折扣")
    gold = fields.DecimalField(max_digits=65, null=True, decimal_places=2, default=0, description="金币")
    diamond = fields.IntField(max_digits=20, null=True, default=0, description="钻石")
    room_card = fields.IntField(max_digits=20, null=True, default=0, description="房卡")
    yellow_diamond = fields.IntField(max_digits=20, null=True, default=0, description="黄钻")
    vip = fields.SmallIntField(max_length=2, default=0, null=True, description="VIP等级")
    platform = fields.IntEnumField(enum_type=PlatForm, index=True,
                                   description="平台：1网页 2微信公众号 3原生app 4微信小游戏 5支付宝小游戏 6抖音小游戏 7安卓app 8ios_app")
    dev_ident = fields.CharField(max_length=32, null=True, default='', description='设备标识')
    safe_key = fields.CharField(max_length=18, null=True, default='', description='安全密钥')
    valid_key = fields.CharField(max_length=16, null=True, default='', description='验证密钥')
    tst_mark = fields.BooleanField(null=True, default=False, description='测试号标记')
    ip = fields.CharField(max_length=128, null=True, default='', description='登陆IP')
    region = fields.CharField(max_length=20, null=True, default='', description='地区/行政区域')
    country = fields.CharField(max_length=16, null=True, default='CN', description='国家域名')
    openid = fields.CharField(max_length=128, null=True, default='', description='用户授权唯一标识')
    unionid = fields.CharField(max_length=128, null=True, default='', description='用户授权唯一标识')
    wechat = fields.SmallIntField(max_length=2, null=True, default=0, description='微信绑定标识：1已绑定 0未绑定')
    apple_id = fields.CharField(max_length=128, index=True, default='', description='苹果平台用户授权唯一标识')
    ban_time = fields.BigIntField(null=True, default=0, description='封禁时间：0未封禁 -1永久封禁 大于0为封禁时间')
    updated = fields.BigIntField(null=True, default=0, description='更新时间')

    class Meta:
        unique_together = (("platform", "openid"),("unionid", "platform"),)  # 联合主键


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
    end_time = fields.BigIntField(null=True, default=None, description='商品有效期')
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
    play_type = fields.IntEnumField(enum_type=PlayType, default=PlayType.AN_LONG_XUE_ZHAN, description="玩法类型")
    room_card = fields.IntField(max_length=20, null=True, default=0, description='茶馆基金（房卡）')
    other = fields.JSONField(null=True, description='其他设置：JSON存储')
    notice = fields.TextField(null=True, description='公告')
    status = fields.SmallIntField(max_length=2, null=True, default=0, description='状态：0正常')
    record_status = fields.SmallIntField(max_length=2, null=True, default=0, description='战绩状态：0隐藏 1显示')
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
    gid = fields.IntField(max_length=10, pk=True, description='分组ID')
    name = fields.CharField(max_length=32, null=True, default=0, description="分组名称")
    club_id = fields.IntField(max_length=6, null=True, description='茶馆ID')
    u_ids = fields.TextField(null=True, description='多个玩家ID')

    class Meta:
        table = "club_groups"


class ExtraClubBehavior(DBModel):
    """茶馆操作行为记录表"""
    id = fields.IntField(max_length=10, pk=True, default=0, description='行为ID')
    club_id = fields.IntField(max_length=6, index=True, description='茶馆ID')
    uid = fields.IntField(max_length=28, index=True, description='玩家ID')
    type = fields.SmallIntField(max_length=2, null=True, default=0,
                                description='类型：1加入茶馆申请 2小黑屋 3隔离 4退出茶馆 5管理员 6玩法')
    status = fields.SmallIntField(max_length=2, null=True, default=0,
                                  description='状态，类型==1：0未审批 1拒绝 2取消 3更新 99通过')
    check_uid = fields.IntField(max_length=28, null=True, default=0, description='审批/操作玩家ID')
    updated = fields.BigIntField(null=True, default=0, description='更新时间')

    class Meta:
        table = "extra_club_behavior"


class ConfGameRoomRules(DBModel):
    """游戏房间规则配置表"""
    id = fields.IntField(max_length=10, pk=True, description='规则ID')
    pip = fields.IntField(max_length=10, index=True, default=0, description='父级ID')
    status = fields.SmallIntField(max_length=2, null=True, default=0, description='状态：0显示 1隐藏')
    rule_type = fields.SmallIntField(max_length=2, null=True, default=0, description='规则类型：1房卡场 2休闲场 3黄钻场')
    play_type = fields.SmallIntField(max_length=2, null=True, default=0, description='玩法类型')
    rule_name = fields.CharField(max_length=20, null=True, description='规则名')
    rule_info = fields.JSONField(null=True, description='规则信息：JSON存储')

    class Meta:
        table = "conf_game_room_rules"


class ClubRoomTemplates(DBModel):
    """茶馆房间模版表"""
    id = fields.IntField(max_length=10, pk=True, default=0, description='房间ID')
    club_id = fields.IntField(max_length=6, index=True, description='茶馆ID')
    platform = fields.IntEnumField(enum_type=PlatForm, index=True,
                                   description="平台：1网页 2微信公众号 3原生app 4微信小游戏 5支付宝小游戏 6抖音小游戏 7安卓app 8ios_app")
    cs_type = fields.IntField(max_length=10, default=0, description="子服务类型")
    play_type = fields.IntEnumField(enum_type=PlayType, default=PlayType.AN_LONG_XUE_ZHAN, description="玩法类型")
    rule_details = fields.JSONField(null=True, description='房间玩法规则：JSON存储')
    max_player = fields.SmallIntField(max_length=2, null=True, default=0, description='最大人数')
    total_round = fields.SmallIntField(max_length=6, null=True, default=0, description='总局数')
    price = fields.SmallIntField(max_length=6, null=True, default=0, description='费用')
    is_location = fields.SmallIntField(max_length=2, null=True, default=0, description='是否开启定位：0否 1是')
    is_friend = fields.SmallIntField(max_length=2, null=True, default=0, description='是否只允许好友可进：0否 1是')
    updated = fields.BigIntField(null=True, default=0, description='更新时间')

    class Meta:
        table = "club_room_templates"


class GameRooms(DBModel):
    """游戏房间关系表"""
    id = fields.IntField(max_length=10, pk=True, description='主键ID')
    room_id = fields.IntField(max_length=6, unique=True, description='房间ID')
    club_id = fields.IntField(max_length=6, index=True, default=0, description='茶馆ID,无茶馆为0')
    creator = fields.IntField(max_length=28, null=True, description='房主ID(玩家ID)')
    platform = fields.IntEnumField(enum_type=PlatForm, index=True,
                                   description="平台：1网页 2微信公众号 3原生app 4微信小游戏 5支付宝小游戏 6抖音小游戏 7安卓app 8ios_app")
    pay_type = fields.SmallIntField(max_length=2, null=True, default=0,
                                    description='支付方式：0房主 1冠军支付 2茶馆基金 3AA支付')
    price = fields.SmallIntField(max_length=6, null=True, default=0, description='费用')
    cs_type = fields.IntField(max_length=10, default=0, description="子服务类型")
    play_type = fields.IntEnumField(enum_type=PlayType, default=PlayType.AN_LONG_XUE_ZHAN, description="玩法类型")
    total_round = fields.SmallIntField(max_length=6, null=True, default=0, description='总局数')
    round_num = fields.SmallIntField(max_length=6, default=0, description='对局数')
    rule_details = fields.JSONField(null=True, description='房间玩法规则：JSON存储')
    max_player = fields.SmallIntField(max_length=2, null=True, default=0, description='最大人数')
    is_location = fields.SmallIntField(max_length=2, null=True, default=0, description='是否开启定位：0否 1是')
    is_friend = fields.SmallIntField(max_length=2, null=True, default=0, description='是否只允许好友可进：0否 1是')
    room_type = fields.SmallIntField(max_length=2, null=True, default=0,
                                     description='房间类型：1普通房间（通过匹配） 2自建房间')
    status = fields.IntEnumField(enum_type=RoomStatus, default=RoomStatus.T_IDLE, index=True, description='房间状态')
    updated = fields.BigIntField(null=True, default=0, description='更新时间')

    class Meta:
        table = "game_rooms"


class ExtraClubEvent(DBModel):
    """茶馆日常事件相关记录表"""
    id = fields.IntField(max_length=10, pk=True, description='事件ID')
    club_id = fields.IntField(max_length=6, index=True, description='茶馆ID')
    type = fields.SmallIntField(max_length=2, index=True, default=0,
                                description='类型：1基金充值 2基金消耗 3入馆审批记录 4茶馆解散')
    uid = fields.IntField(max_length=28, index=True, description='玩家ID（发起方）')
    explain = fields.CharField(max_length=256, null=True, default='',
                               description='说明:记录XX管理员（ID：xx）通过XX玩家（ID：xx）加入茶馆; XX玩家（ID：xx）消耗XX基金创建了xx玩法（房间号：xx）; XX玩家（ID：xx）为茶馆充值基金xx')

    class Meta:
        table = "extra_club_event"


class RecordsGameRoom(DBModel):
    """战绩表-游戏房间"""
    record_rid = fields.IntField(pk=True, description='战绩ID', )
    club_id = fields.IntField(index=True, description='茶馆ID，玩家无茶馆值为0', )
    room_id = fields.IntField(index=True, description='房间ID', )
    creator = fields.IntField(description='房主ID', )
    total_round = fields.SmallIntField(description='总局数', )
    round_num = fields.SmallIntField(default=0, description='对局数', )
    max_player = fields.SmallIntField(description='对局人数', )
    rule_details = fields.JSONField(null=True, description='房间玩法规则：JSON存储', )
    play_type = fields.SmallIntField(description='玩法类型', )
    cs_type = fields.IntField(description='子服务类型', )
    start_time = fields.BigIntField(default=0, index=True, description='开始时间', )
    end_time = fields.BigIntField(default=0, index=True, description='结束时间', )
    pay_type = fields.SmallIntField(description='支付方式：0房主 1冠军支付 2茶馆基金 3AA支付', )
    price = fields.SmallIntField(description='费用', )
    room_status = fields.SmallIntField(null=True, default=0, description='房间状态：0完局结束、1中途解散（人为操作解散）、2异常解散（非人为解散）', )
    updated = fields.BigIntField(default=0, description='更新时间', )

    class Meta:
        table = "records_game_room"


class RecordsGameTotal(DBModel):
    """战绩表-游戏总局"""
    record_tid = fields.IntField(pk=True, description='战绩总局ID', )
    record_rid = fields.IntField(index=True, description='战绩房间ID', )
    club_id = fields.IntField(index=True, description='茶馆ID，玩家无茶馆值为0', )
    room_id = fields.IntField(index=True, description='房间ID', )
    uid = fields.IntField(index=True, description='玩家ID', )
    cs_type = fields.IntField(description='子服务类型', )
    play_type = fields.SmallIntField(description='玩法类型', )
    price = fields.BigIntField(description='费用', )
    final_status = fields.SmallIntField(description='输赢状态：0输 1赢', )
    final_score = fields.BigIntField(description='最终分数', )
    final_ranking = fields.IntField(description='最终名次', )
    final_grade = fields.SmallIntField(description='最终评价：1全场最佳', )
    final_result = fields.JSONField(null=True, description='详细结果：JSON存储', )

    class Meta:
        table = "records_game_total"


class RecordsGameSegment(DBModel):
    """战绩表-游戏子局"""
    record_sid = fields.IntField(pk=True, description='战绩子ID', )
    record_tid = fields.IntField(index=True, description='战绩总局ID', )
    record_rid = fields.IntField(index=True, description='战绩房间ID', )
    uid = fields.IntField(index=True, description='玩家ID', )
    round_num = fields.SmallIntField(description='当前局数', )
    round_status = fields.SmallIntField(description='当局状态：0输 1赢', )
    round_score = fields.BigIntField(description='当局分数', )
    round_ranking = fields.IntField(description='当局名次', )
    round_result = fields.JSONField(null=True, description='详细结果：JSON存储', )
    replay_label = fields.CharField(unique=True, default=None, max_length=32, description='回放标签', )
    replay_msg = fields.TextField(null=True, description='回放数据', )
    cs_type = fields.IntField(description='子服务类型', )

    class Meta:
        table = "records_game_segment"


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
    reason = fields.SmallIntField(max_length=2, null=True, default=0, description='变更原因：查看ReasonCostGold常量类')
    currency = fields.SmallIntField(max_length=2, null=True, default=0,
                                    description='类型：0无 1金币 2钻石 3房卡 4黄钻 5人民币')
    num = fields.DecimalField(max_digits=65, null=True, decimal_places=2, default=0, description="变动数量")
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
    platform = fields.CharField(max_length=32, null=True,
                                description="平台：1网页 2微信公众号 3原生app 4微信小游戏 5支付宝小游戏 6抖音小游戏 7安卓app 8ios_app")
    type = fields.SmallIntField(max_length=2, null=True, default=0,
                                description='类型：1首充 2金币 3钻石 4房卡 5黄钻 6VIP 7周卡 8月卡 9终身卡 10金币补足 11复仇礼包 12返还礼包 13赛事-代金券 14赛事-晋级资格 15赛事-农产品')
    currency = fields.SmallIntField(max_length=2, null=True, default=0,
                                    description="货币类型：0无 1金币 2钻石 3房卡 4黄钻 5人民币")
    rank = fields.IntField(max_length=10, null=True, default=0, description="排序：越大越靠前")
    purchase_limit = fields.CharField(max_length=256, null=True, default='', description='限购条件')
    name = fields.CharField(max_length=64, null=True, default='', description="名称")
    img = fields.CharField(max_length=256, null=True, default='', description='图片')
    desc = fields.CharField(max_length=256, null=True, default='', description='描述')
    status = fields.SmallIntField(max_length=2, null=True, description='状态：0隐藏 1显示')
    start_time = fields.BigIntField(null=True, default=None, description='有效期开始时间')
    end_time = fields.BigIntField(null=True, default=None, description='有效期结束时间')
    updated = fields.BigIntField(null=True, default=0, description='更新时间')


class Goods(DBModel):
    """商品(道具)表"""
    good_id = fields.IntField(max_length=10, pk=True, description='商品ID')
    sid = fields.IntField(max_length=10, index=True, default=0, description='商城ID')
    kind = fields.SmallIntField(max_length=2, null=True, description='特性：0虚拟 1实物')
    type = fields.SmallIntField(max_length=2, null=True, default=0,
                                description='类型：1首充 2金币 3钻石 4房卡 5黄钻 6VIP 7周卡 8月卡 9终身卡 10金币补足 11复仇礼包 12返还礼包 13赛事-代金券 14赛事-晋级资格 15赛事-农产品')
    currency = fields.SmallIntField(max_length=2, null=True, default=0,
                                    description="货币类型：0无 1金币 2钻石 3房卡 4黄钻 5人民币")
    sku = fields.CharField(max_length=64, unique=True, default=0, description="商品唯一标识")
    purchase_limit = fields.CharField(max_length=256, null=True, default='', description='限购条件')
    original = fields.DecimalField(max_digits=65, null=True, decimal_places=2, default=0, description="原价")
    price = fields.DecimalField(max_digits=65, null=True, decimal_places=2, default=0, description="售价")
    total = fields.IntField(max_length=10, null=True, default=0, description="总量：-1无限")
    name = fields.CharField(max_length=64, null=True, default='', description="商品名称")
    img = fields.CharField(max_length=256, null=True, default='', description='商品图片')
    desc = fields.CharField(max_length=256, null=True, default='', description='商品描述')
    content = fields.JSONField(null=True, description='商品内容：JSON存储')
    status = fields.SmallIntField(max_length=2, null=True, description='状态：0下架 1上架')
    up_time = fields.BigIntField(null=True, default=None, description='上架时间')
    down_time = fields.BigIntField(null=True, default=None, description='下架时间')
    rank = fields.IntField(max_length=10, null=True, default=0, description="排序：越大越靠前")
    bag_type = fields.SmallIntField(max_length=2, null=True, default=0, description='背包类型：0常规 1延时')
    updated = fields.BigIntField(null=True, default=0, description='更新时间')


class Orders(DBModel):
    """用户订单表"""
    id = fields.IntField(max_length=10, pk=True, description='变动ID')
    uid = fields.IntField(max_length=28, index=True, description='玩家ID')
    purchase_uid = fields.IntField(max_length=28, index=True, description='采购人ID')
    good_id = fields.IntField(max_length=28, index=True, description='商品ID')
    sku = fields.CharField(max_length=64, index=True, default=0, description="商品唯一标识")
    platform = fields.IntEnumField(enum_type=PlatForm, index=True,
                                   description="平台：1网页 2微信公众号 3原生app 4微信小游戏 5支付宝小游戏 6抖音小游戏 7安卓app 8ios_app")
    amount = fields.DecimalField(max_digits=65, null=True, decimal_places=2, default=0, description="支付金额")
    currency = fields.SmallIntField(max_length=2, null=True, default=0,
                                    description="购买资源支付类型：0无 1金币 2钻石 3房卡 4黄钻 5人民币")
    pay_mode = fields.IntEnumField(enum_type=PayMode, null=True, default=PayMode.DEFAULT_MODE, description="支付方式")
    num = fields.IntField(max_length=10, null=True, default=0, description="购买数量")
    order_no = fields.CharField(max_length=32, index=True, default='', description="订单编号")
    out_order_no = fields.CharField(max_length=64, index=True, default='', description="外部订单编号")
    prepay_id = fields.CharField(max_length=64, null=True, default='', description="外部支付标识")
    status = fields.SmallIntField(max_length=2, null=True,
                                  description='订单状态：0待支付 1支付失败 2订单关闭 99支付成功')
    gain_status = fields.SmallIntField(max_length=2, null=True, description='领取状态：0未发放 1已发放 99已领取')
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
    award_id = fields.IntField(max_length=10, pk=True, description='奖励ID')
    type = fields.SmallIntField(max_length=2, index=True, description='奖励类型：1系统 2牌友会 3活动 3任务 4赛事-线上 5赛事-线下')
    level = fields.SmallIntField(max_length=2, index=True, description='奖励等级')
    name = fields.CharField(max_length=20, null=True, description='奖励名称')
    content = fields.JSONField(null=True, description='奖励内容：JSON存储')
    updated = fields.BigIntField(null=True, default=0, description='更新时间')


class AwardGains(DBModel):
    """ 奖励领取记录表 """
    id = fields.IntField(max_length=10, pk=True, description='领取ID')
    reward_type = fields.SmallIntField(max_length=2, index=True, description='奖励类型:0活动 1福利码 2任务 3邮件附件')
    type_id = fields.IntField(max_length=10, index=True, description='奖励类型ID')
    act_id = fields.IntField(max_length=10, index=True, description='活动ID')
    uid = fields.IntField(max_length=28, index=True, description='玩家ID')
    status = fields.SmallIntField(max_length=2, null=True, description='领取状态：0未领取 99已领取')
    remark = fields.CharField(max_length=255, null=True, description='备注')
    updated = fields.BigIntField(null=True, default=0, description='更新时间')

    class Meta:
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
        app = "lucky_game"


class ConfServerAddr(DBModel):
    """服务器配置"""
    sid = fields.IntField(max_length=10, null=True, default=0, description="服务ID")
    addr = fields.CharField(max_length=32, null=True, default='', description='地址')
    path = fields.CharField(max_length=32, null=True, default='', description='路径')
    status = fields.SmallIntField(max_length=2, null=True, default=0, description='状态 0关闭 1开启')

    class Meta:
        table = "conf_server_addr"


class ConfRule(DBModel):
    """ 游戏规则配置(主要关于游戏、房间规则相关) """
    conf_leisure: fields.ReverseRelation["ConfLeisure"]
    conf = fields.JSONField(null=True, description="配置")
    desc = fields.CharField(max_length=28, null=True, default=0, description='配置描述')

    class Meta:
        table = "conf_rule"


class ConfLeisure(DBModel):
    """ 休闲场配置 """
    cs_type = fields.IntField(max_length=10, default=0, description="子服务类型")
    play_type = fields.IntEnumField(enum_type=PlayType, default=PlayType.AN_LONG_XUE_ZHAN, description="玩法类型")
    level = fields.IntField(max_length=10, null=True, default=0, description="级别")
    base_score = fields.BigIntField(null=True, default=0, description="底分")
    price = fields.BigIntField(null=True, default=0, description="门票")
    min_take = fields.BigIntField(null=True, default=0, description="最低携带")
    max_take = fields.BigIntField(null=True, default=0, description="最高携带")
    status = fields.SmallIntField(max_length=2, null=True, default=0, description='状态 0关闭 1开启')
    desc = fields.CharField(max_length=28, null=True, default=0, description='配置描述')
    level_desc = fields.CharField(max_length=28, null=True, default=0, description='场次描述')
    ranking_addition = fields.FloatField(default=0, description="修为加成")
    gift_conf = fields.JSONField(null=True, description="礼包配置")
    # 表示在 RuleConf 模型中可以通过 conf_leisure 属性访问所有相关的 LeisureConf 实例（这里好像用不到）
    rule_conf = fields.ForeignKeyField("lucky_game.ConfRule", related_name="conf_leisure")
    threshold_multiple = fields.SmallIntField(max_length=2, null=True, default=0, description='大赢公告倍率')

    class Meta:
        table = "conf_leisure"


class StatsPlayerGameTimes(DBModel):
    """ 玩家游戏次数统计 """
    uid = fields.IntField(max_length=28, index=True, default=100000, description='玩家ID')
    cs_type = fields.IntField(max_length=10, default=0, description="子服务类型")
    play_type = fields.IntEnumField(enum_type=PlayType, default=PlayType.AN_LONG_XUE_ZHAN, description="玩法类型")
    win_count = fields.BigIntField(null=True, default=0, description="赢的次数")
    curr_win_streak = fields.IntField(null=True, default=0, description="当前连胜")
    max_win_streak = fields.IntField(null=True, default=0, description="最大连胜")
    total_count = fields.BigIntField(null=True, default=0, description="总次数")
    max_multiple = fields.BigIntField(null=True, default=0, description="最大倍数")
    max_win_score = fields.BigIntField(null=True, default=0, description="最大赢分")
    max_cards = fields.CharField(max_length=64, null=True, default="", description="最大牌型")
    extra_info = fields.JSONField(null=True, description="额外信息")

    class Meta:
        unique_together = (("uid", "cs_type", "play_type"),)
        table = "stats_player_game_times"


class Robot(DBModel):
    """ 机器人总表 """
    uid = fields.IntField(max_length=28, pk=True, default=100000, description='玩家ID')
    name = fields.CharField(max_length=32, null=True, default='', description='玩家昵称')
    sex = fields.IntEnumField(enum_type=Sex, default=Sex.DEFAULT, description="性别")
    avatar = fields.CharField(max_length=128, null=True, default='', description='头像地址')
    address = fields.CharField(max_length=256, null=True, default='', description='所在地址')
    region = fields.CharField(max_length=20, null=True, default='', description='地区/行政区域')

    class Meta:
        indexes = ("region",)  # 联合索引


class ConfRobot(DBModel):
    """ 机器人简单配置 """
    leisure = fields.ForeignKeyField("lucky_game.ConfLeisure", related_name="conf_robot", on_delete=fields.CASCADE)
    cs_type = fields.IntField(max_length=10, default=0, description="子服务类型")
    avatar_frame = fields.JSONField(null=True, description="头像框配置")
    chat_bubble = fields.JSONField(null=True, description="聊天气泡配置")
    card_skin = fields.JSONField(null=True, description="卡牌皮肤配置")
    skin_count = fields.JSONField(null=True, description="卡牌皮肤数量配置")
    status = fields.SmallIntField(max_length=2, null=True, default=0, description='状态 0关闭 1开启')

    class Meta:
        table = "conf_robot"


class RecordsChatHistory(DBModel):
    """ 聊天历史记录 """
    from_uid = fields.IntField(max_length=28, null=False, index=True, description='发送玩家UID')
    to_uid = fields.IntField(max_length=28, null=False, index=True, description='接收玩家UID')
    chat_channel = fields.IntEnumField(enum_type=ChatChannel, index=True, default=ChatChannel.WORLD,
                                       description='聊天频道')
    content = fields.CharField(max_length=255, default='', description='消息内容')

    class Meta:
        table = "records_chat_history"


class UserFriendship(DBModel):
    """好友关系表"""
    from_uid = fields.IntField(max_length=28, null=False, index=True, description='发起申请玩家UID')
    to_uid = fields.IntField(max_length=28, null=False, index=True, description='被申请玩家UID')
    status = fields.IntEnumField(enum_type=FriendshipSta, default=FriendshipSta.PENDING.val, description='友情状态')
    prev_status = fields.IntField(null=True, description='屏蔽前的友情状态')
    updated = fields.BigIntField(null=True, default=0, description='更新时间')

    class Meta:
        unique_together = (("from_uid", "to_uid"),)
        table = "user_friendship"


class StatsUserDataAnalysis(DBModel):
    """ 用户数据分析 """
    time_node = fields.BigIntField(max_length=28, index=True, null=False, default=0, description="时间节点：天")
    active_user_count = fields.IntField(max_length=32, default=0, description="活跃用户总数")
    new_user_count = fields.IntField(max_length=32, default=0, description="新增用户总数")
    pay_user_count = fields.IntField(max_length=32, default=0, description="付费用户总数")
    pay_amount = fields.BigIntField(max_length=28, null=True, default=0, description="付费金额")
    first_pay_times = fields.IntField(max_length=28, null=True, default=0, description="首次付费人数")
    avg_pay_amount = fields.FloatField(null=True, default=0, description="人均付费金额")

    class Meta:
        table = "stats_user_data_analysis"


class ConfAward(DBModel):
    """奖励配置"""
    award_id = fields.IntField(max_length=10, pk=True, default=4000, description='奖励ID')
    award_type = fields.IntEnumField(enum_type=AwardType, index=True, default=0, description='获奖类型')
    award_name = fields.CharField(max_length=32, null=True, default='', description='奖励名称')
    award_level = fields.IntField(max_length=10, null=True, default=0, description='奖励级别 0无等级')
    weight = fields.SmallIntField(null=True, default=0, description='奖励权重')
    achieve_type = fields.IntEnumField(enum_type=AchieveType, default=0, description='获奖条件')
    achieve_value = fields.BigIntField(max_length=20, null=True, description="获奖目标值")
    receive_limit = fields.IntField(max_length=10, null=True, default=0, description='领奖次数限制')
    conf_items = fields.JSONField(null=True, description='可立即获得的物品配置')
    img_url = fields.CharField(max_length=128, null=True, default='', description='图片地址')
    desc = fields.CharField(max_length=256, null=True, default='', description='奖励描述')
    status = fields.SmallIntField(max_length=2, null=True, default=0, description='状态 0关闭 1开启')

    class Meta:
        table = "conf_award"


class StatsWatchAdTimes(DBModel):
    """玩家看广告统计"""
    uid = fields.IntField(max_length=28, index=True, null=False, description='玩家ID')
    time_node = fields.BigIntField(max_length=28, null=True, default=0, description='时间节点：天')
    t_raffle_luck = fields.IntField(max_length=10, null=True, default=0, description='免费抽奖次数')
    t_award = fields.IntField(max_length=10, null=True, default=0, description='免费领奖次数')
    t_relief = fields.IntField(max_length=10, null=True, default=0, description='救济翻倍次数')
    t_dice = fields.IntField(max_length=10, null=True, default=0, description='免费骰子次数')
    t_gold_not_enough_first = fields.IntField(max_length=10, null=True, default=0,
                                              description='看广告领取金币不足礼包（上篇）')
    t_gold_not_enough_second = fields.IntField(max_length=10, null=True, default=0,
                                               description='看广告领取金币不足礼包（下篇）')
    t_sign_in_wk = fields.IntField(max_length=10, null=True, default=0, description='看广告每周七日签到')

    class Meta:
        table = "stats_watch_ad_times"
        unique_together = (("uid", "time_node"),)


class ConfActivity(DBModel):
    """活动配置"""
    act_id = fields.IntField(max_length=10, pk=True, default=3000, description='充值活动ID')
    act_type = fields.IntEnumField(enum_type=ActivityType, index=True, default=0, description='活动类型')
    platform = fields.CharField(max_length=32, null=True,
                                description="平台：1网页 2微信公众号 3原生app 4微信小游戏 5支付宝小游戏 6抖音小游戏 7安卓app 8ios_app")
    act_name = fields.CharField(max_length=32, null=True, default='', description='活动名称')
    act_level = fields.SmallIntField(max_length=4, null=True, default=0, description='活动级别')
    repetition = fields.SmallIntField(max_length=2, null=True, default=0, description='重复类型：0否 1是')
    pay_type = fields.IntEnumField(enum_type=PayType, default=PayType.BY_FREE, description='支付类型')
    price = fields.IntField(null=True, default=0, description='活动价格')
    discount_price = fields.IntField(null=True, default=0, description='折扣价格')
    product_id = fields.CharField(max_length=32, null=True, description='微信道具ID')
    condition_type = fields.IntEnumField(enum_type=ConditionType, default=0, description='参与条件')
    join_limit_day = fields.IntField(max_length=10, null=True, default=0, description='每日可参与次数：-1为不限制')
    join_limit_total = fields.IntField(max_length=10, null=True, default=0, description='总共可参与次数:  -1为不限制')
    desc = fields.CharField(max_length=1500, null=True, default='', description='活动描述')
    start_time = fields.IntField(max_length=28, null=True, default=0, description='活动开始时间')
    end_time = fields.IntField(max_length=28, null=True, default=0, description='活动结束时间')
    once_awards = fields.JSONField(null=True, description='可立即获得的物品配置')
    condition_awards = fields.JSONField(null=True, description='按活动规则获取的奖励')
    sale_limit = fields.JSONField(null=True, description='商品特价配置')
    rand_type = fields.IntEnumField(enum_type=RandType, default=0, description='返利类型')
    img_url = fields.CharField(max_length=128, null=True, default='', description='图片地址')
    status = fields.SmallIntField(max_length=2, null=True, default=0, description='状态 0关闭 1开启')

    class Meta:
        table = "conf_activity"


class ConfVip(DBModel):
    """ VIP配置 """
    level = fields.IntEnumField(enum_type=LevelType, description="等级")
    need_exp = fields.IntField(max_length=20, description='需要经验')
    text = fields.CharField(max_length=64, default='', description='当前文案')
    ranking_addition = fields.FloatField(default=0, description="修为加成")
    relief_add_times = fields.SmallIntField(default=0, description='救济增加次数')
    relief_addition = fields.FloatField(default=0, description='救济金加成')
    level_awards = fields.JSONField(null=True, description='VIP等级奖')
    daily_awards = fields.JSONField(null=True, description='VIP日奖')
    increase_space = fields.DecimalField(max_digits=65, decimal_places=0, default=0, description="保险箱扩容量")

    class Meta:
        table = "conf_vip"


class UserVip(DBModel):
    """ VIP玩家记录 """
    uid = fields.IntField(max_length=28, pk=True, default=100000, description='玩家ID')
    cur_exp = fields.IntField(max_length=20, description='当前经验')
    vip = fields.ForeignKeyField('lucky_game.ConfVip', related_name='conf_vip', default=None)
    recharge_amount = fields.DecimalField(max_digits=65, decimal_places=2, default=0, description="充值金额")
    level_achieved = fields.JSONField(null=True, description='已领取的等级奖励')
    time_node = fields.BigIntField(max_length=28, null=True, default=0, description='日奖最新发奖时间')
    daily_achieved = fields.JSONField(null=True, description='已领取的每日奖励')
    updated = fields.BigIntField(null=True, default=0, description='更新时间')

    class Meta:
        table = "user_vip"


class UserSafeBox(DBModel):
    """ 玩家保险箱 """
    uid = fields.IntField(max_length=28, pk=True, default=100000, description='玩家ID')
    amount = fields.DecimalField(max_digits=65, decimal_places=0, default=0, description="当前已存入的总量")
    complement_sta = fields.IntEnumField(enum_type=Switch, default=Switch.CLOSE, description="自动补足开启状态")
    complement_count = fields.DecimalField(max_digits=65, decimal_places=0, default=0, description="自动补足数量")
    space = fields.DecimalField(max_digits=65, decimal_places=0, default=0, description="容量")
    got_time = fields.BigIntField(null=True, default=0, description='激活时间')
    times_limit = fields.IntField(max_length=11, default=0, description="每日限制次数")
    exp_time = fields.BigIntField(max_length=28, null=True, default=0, description="过期时间")

    class Meta:
        table = "user_safe_box"


class ItemsCosmetic(DBModel):
    """游戏装扮项"""
    goods_id = fields.IntField(max_length=10, pk=True, default=1300, description='游戏装扮ID')
    goods_name = fields.CharField(max_length=32, null=False, default='', description='装扮名称')
    goods_type = fields.IntEnumField(enum_type=GoodsType, null=False, index=True, default=0, description='物品类型')
    cosmetic_type = fields.IntEnumField(enum_type=CosmeticType, index=True, default=0, description='装扮类型')
    add_type = fields.IntEnumField(enum_type=AddType, default=0, description='累加类型')
    put_type = fields.IntEnumField(enum_type=PutType, default=PutType.U_BAG, description='存放类型')
    price = fields.IntField(null=True, default=0, description='装扮价格')
    jump_target = fields.IntEnumField(enum_type=JumpTarget, default=0, description='跳转目标')
    target_data = fields.JSONField(null=True, description='跳转配置')
    number = fields.SmallIntField(max_length=6, null=True, default=0, description='物品排序')
    desc = fields.CharField(max_length=256, null=True, default='', description='物品描述')
    img_url = fields.CharField(max_length=128, null=True, default='', description='图片地址')
    status = fields.SmallIntField(max_length=2, null=True, default=0, description='状态 0关闭 1开启')
    extra_info = fields.JSONField(null=True, description="额外配置信息")
    jump_data = fields.JSONField(null=True, description='跳转配置')

    class Meta:
        table = "items_cosmetic"


class UserCosmetic(DBModel):
    """玩家装扮"""
    cos_id = fields.IntField(max_length=10, pk=True, default=1, description='装扮统计ID')
    cosmetic_type = fields.IntEnumField(enum_type=CosmeticType, index=True, default=0, description='装扮类型')
    cosmetic_item = fields.ForeignKeyField('lucky_game.ItemsCosmetic', related_name='cosmetic_item',
                                           on_delete=OnDelete.CASCADE, null=True)
    uid = fields.IntField(max_length=28, index=True, null=False, description='玩家ID')
    got_type = fields.IntEnumField(enum_type=GotType, default=0, description='获得类型')
    exp_time = fields.BigIntField(null=True, default=0, description="过期时间")
    got_time = fields.IntField(null=True, default=0, description='获得时间')

    class Meta:
        table = "user_cosmetic"
        unique_together = (("uid", "cosmetic_item"),)


class UserActivityProgress(DBModel):
    """ 用户参与活动进度表 """
    progress_id = fields.IntField(max_length=28, pk=True, description='进度ID', )
    act_id = fields.IntField(max_length=28, index=True, description='活动ID', )
    current_value = fields.SmallIntField(max_length=6, description='当前进度值：如完成数量，积分等', )
    deadline = fields.BigIntField(default=0, description='截止时间', )
    join_time = fields.BigIntField(default=0, description='参与时间', )
    status = fields.SmallIntField(max_length=2, description='奖励发放状态: 0未发放 1部分发放 99全部发放', )
    time_node = fields.BigIntField(default=0, description='发奖时间', )
    uid = fields.IntField(max_length=28, index=True, description='玩家ID', )

    class Meta:
        table = "user_activity_progress"
        unique_together = (("uid", "act_id"),)


class LogUserActivity(DBModel):
    """ 用户参与活动记录表 """
    act_id = fields.IntField(max_length=28, index=True, description='活动ID', )
    join_time = fields.BigIntField(index=True, default=0, description='参与时间', )
    uid = fields.IntField(max_length=28, index=True, description='玩家ID', )
    pay_type = fields.IntEnumField(enum_type=PayType, default=PayType.BY_FREE, description='支付类型')
    award_type = fields.IntEnumField(enum_type=AwardType, default=AwardType.DEFAULT, description='奖励类型')

    class Meta:
        table = "log_user_activity"


class AppVersions(DBModel):
    """ 应用版本信息 """
    app_id = fields.CharField(index=True, max_length=50, description='应用标识', )
    build_number = fields.CharField(max_length=20, null=True, description='构建号', )
    created_by = fields.IntField(description='创建人ID', )
    download_url = fields.CharField(max_length=500, description='下载链接', )
    file_hash = fields.CharField(max_length=64, null=True, description='文件校验值', )
    file_size = fields.BigIntField(default=0, description='文件大小（字节）', )
    force_update_version = fields.BooleanField(null=True, description='强制更新版本', )
    id = fields.BigIntField(pk=True, description='主键ID', )
    min_support_version = fields.CharField(max_length=20, null=True, description='最低支持版本', )
    platform = fields.IntEnumField(enum_type=PlatForm, index=True,
                                   description="平台：1网页 2微信公众号 3原生app 4微信小游戏 5支付宝小游戏 6抖音小游戏 7安卓app 8ios_app")
    release_notes = fields.TextField(null=True, description='版本更新说明', )
    release_time = fields.BigIntField(index=True, description='发布时间', )
    status = fields.SmallIntField(null=True, default=1, max_length=2, description='状态：0-下线，1-正常，2-灰度', )
    updated = fields.BigIntField(null=True, auto_now=True, description='更新时间', )
    updated_by = fields.IntField(description='更新人ID', )
    version_code = fields.CharField(index=True, max_length=20, description='版本号（如：1.2.3）', )

    class Meta:
        table = "app_versions"
        unique_together = (("app_id", "version_code", "platform"), ("platform", "status"),)


class ClubUserGroups(DBModel):
    """茶馆用户禁止同桌表"""
    gid = fields.IntField(max_length=10, pk=True, description='分组ID')
    club_id = fields.IntField(max_length=10, null=True, description='茶馆ID')
    uid = fields.IntField(max_length=28, null=True, description='玩家ID')
    u_ids = fields.TextField(null=True, description='多个玩家ID')
    status = fields.SmallIntField(null=True, default=1, description='状态：0失效 1生效')

    class Meta:
        table = "club_user_groups"


class DistributionSettleConf(DBModel):
    """ 渠道结算分润配置表 """
    id = fields.IntField(primary_key=True, description='分润结算ID')
    level = fields.IntField(default=0, description='档位')
    type = fields.SmallIntField(default=0, description='类型：1房卡 2赛事农产品')
    range_min = fields.IntField(default=0, description='最小取值范围')
    range_max = fields.IntField(default=0, description='最大取值范围')
    profit_condition = fields.CharField(max_length=32, default="", description='分润条件')
    profit_ratio = fields.FloatField(null=True, default=1.0000, description='分润比例')
    desc = fields.CharField(max_length=256, null=True, default="", description='描述')
    updated = fields.BigIntField(default=0, description='更新时间')

    class Meta:
        table = "distribution_settle_conf"


class TournamentTemplate(DBModel):
    """ 赛事模板表 (支持多赛事并行) """
    cycle_type = fields.BooleanField(description='周期类型:1-自然月,2-自然季')
    final_round_offline = fields.BooleanField(default=True, description='总决赛是否线下:1-是,0-否')
    id = fields.BigIntField(primary_key=True, description='模板ID')
    online_rounds = fields.BooleanField(description='线上场次数:月赛为3')
    qualifier_count = fields.IntField(description='晋级总决赛人数:10')
    rounds_per_cycle = fields.BooleanField(description='每周期场次:月赛为4')
    status = fields.BooleanField(default=True, description='模板状态:1-启用,0-停用')
    template_name = fields.CharField(max_length=100, description='模板名称:月赛/季赛等')
    template_type = fields.BooleanField(description='赛事类型:1-月赛,2-季赛,预留扩展')
    updated = fields.BigIntField(default=0)

    class Meta:
        indexes = (("template_type", "status"),)  # 联合索引
        table = "tournament_template"

class TournamentCycle(DBModel):
    """赛事周期表 (月度赛事实例)"""
    cycle_end_date = fields.DateField(description='周期结束日期')
    cycle_month = fields.IntField(description='月份:1-12')
    cycle_name = fields.CharField(max_length=100, description='周期名称:2026年1月月赛')
    cycle_start_date = fields.DateField(description='周期开始日期')
    cycle_year = fields.IntField(null=True, description='年份:2026')
    id = fields.BigIntField(primary_key=True, description='周期ID')
    status = fields.IntField(default=False, description='状态:0-未开始,1-进行中,2-已结束,3-已归档')
    template_id = fields.BigIntField(index=True, description='关联模板ID')
    reward_id = fields.BigIntField(null=True, description='关联奖励ID')
    updated = fields.BigIntField(default=0)

    class Meta:
        indexes = (("cycle_start_date", "cycle_end_date"),)  # 联合索引
        table = "tournament_cycle"


class TournamentRules(DBModel):
    """赛事规则表"""
    id = fields.BigIntField(primary_key=True, description='规则ID')
    template_id = fields.BigIntField(description='关联模板ID')
    rule_content = fields.JSONField(description='规则内容JSON')
    # 默认规则示例: {"range_time": "时间范围", "game_platform": "比赛平台", "game_play": "游戏玩法", "join_type": "参与方式", "game_rule": "开赛规则"}
    rule_type = fields.IntField(default=1, description='规则类型:1-默认规则')
    updated = fields.BigIntField(default=0)

    class Meta:
        unique_together = (("template_id", "rule_type"),)  # 唯一索引
        table = "tournament_rules"

class TournamentRewards(DBModel):
    """奖励配置表"""
    id = fields.BigIntField(primary_key=True, description='奖励ID')
    rank_end = fields.IntField(description='奖励范围排名结束，默认10')
    rank_start = fields.IntField(description='奖励范围排名起始值，默认1')
    reward_content = fields.JSONField(null=True, description='奖励内容')
    reward_description = fields.CharField(max_length=255, null=True, description='奖励描述')
    round_type = fields.BooleanField(index=True, description='场次类型:1-线上周赛,2-线下总决赛')
    updated = fields.BigIntField(default=0)

    class Meta:
        table = "tournament_rewards"

class TournamentUserPoints(DBModel):
    """用户赛事积分表"""
    id = fields.BigIntField(primary_key=True, description='积分ID')
    cycle_id = fields.BigIntField(index=True, description='关联赛事周期ID')
    score = fields.IntField(default=0, description='得分')
    uid = fields.BigIntField(index=True, description='用户ID')
    ticket = fields.IntField(index=True, description='门票')
    updated = fields.BigIntField(default=0)

    class Meta:
        unique_together = (("cycle_id", "uid"),)  # 唯一索引
        indexes = (("uid", "cycle_id"),)  # 联合索引
        table = "tournament_user_points"

class TournamentRegistration(DBModel):
    """用户报名表"""
    created = fields.BigIntField(default=0)
    id = fields.BigIntField(primary_key=True, description='报名ID')
    pid = fields.BigIntField(description='邀请用户ID')
    register_status = fields.SmallIntField(default=1, description='报名状态:1-已报名,2-已取消,3-已确认参赛')
    register_time = fields.DatetimeField(description='报名时间')
    register_type = fields.SmallIntField(description='报名类型:1-主动报名,2-邀请报名')
    cycle_id = fields.BigIntField(index=True, description='关联赛事周期ID')
    uid = fields.BigIntField(index=True, description='用户ID')
    updated = fields.BigIntField(default=0)

    class Meta:
        unique_together = (("cycle_id", "uid"),)  # 唯一索引
        indexes = (("uid", "register_status"),("cycle_id", "register_status"),)  # 联合索引
        table = "tournament_registration"


class TournamentCycleLeaderboard(DBModel):
    """周期排行榜表"""
    cycle_id = fields.BigIntField(index=True, description='关联周期ID')
    id = fields.BigIntField(primary_key=True, description='排行榜ID')
    participated_rounds = fields.IntField(null=True, default=False, description='参与场次数')
    total_points = fields.IntField(default=0, description='总积分')
    uid = fields.BigIntField(index=True, description='用户ID')
    updated = fields.BigIntField(default=0)

    class Meta:
        unique_together = (("cycle_id", "uid"),)  # 唯一索引
        indexes = (("cycle_id", "total_points"),("cycle_id", "uid"),)  # 联合索引
        table = "tournament_cycle_leaderboard"


class UserGoodExchange(DBModel):
    """用户兑换记录表"""
    id = fields.BigIntField(primary_key=True, description='兑换ID')
    uid = fields.BigIntField(index=True, description='用户ID')
    good_id = fields.BigIntField(index=True, description='商品（道具）ID')
    good_type = fields.SmallIntField(description='商品（道具）类型：1首充 2金币 3钻石 4房卡 5黄钻 6VIP 7周卡 8月卡 9终身卡 10道具 11实物')
    platform = fields.SmallIntField(description='平台：1网页 2微信公众号 3原生app 4微信小游戏 5支付宝小游戏 6抖音小游戏')
    num = fields.IntField(default=1, description='兑换数量:默认=1')
    phone = fields.CharField(max_length=18, null=True, index=True, description='手机号码')
    real_name = fields.CharField(max_length=32, null=True, default='', description='玩家真实姓名')
    region = fields.CharField(max_length=20, null=True, default="", description='地区/行政区域')
    address = fields.CharField(max_length=256, null=True, default="", description='所在详细地址')
    check_status = fields.SmallIntField(default=0, description='审核状态：0未审批 1拒绝 99通过')
    exchange_no = fields.CharField(max_length=32, default="", description='兑换唯一编号')
    express_id = fields.SmallIntField(description='快递平台：0无需发货 1顺丰 2京东 3圆通 4韵达 5中通 6申通 7极兔 8百世 9EMS 10德邦')
    express_no = fields.CharField(max_length=64, null=True, default=0, description='快递单号')
    status = fields.SmallIntField(index=True,default=0, description='领取状态：0未发放 1已发放 99已领取')
    updated = fields.BigIntField(default=0)

    class Meta:
        table = "user_good_exchange"

class ConfCompetition(DBModel):
    """赛事玩法配置表"""
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=32, description='赛事名称')
    cs_type = fields.IntField(index=True, default=0, description='子服务类型')
    competition_type = fields.SmallIntField(default=0, description='赛事类型')
    rule_detail = fields.JSONField(null=True, description='规则详情')
    max_player = fields.IntField(description='最大玩家数')
    price = fields.IntField(default=0, description='门票价格')
    price_type = fields.SmallIntField(default=3, description='支付类型')
    status = fields.SmallIntField(default=2, description='赛事状态')
    start_time = fields.BigIntField(default=0, description='开始时间')
    end_time = fields.BigIntField(default=0, description='结束时间')
    total_round = fields.SmallIntField(default=1, description='总局数')
    play_type = fields.SmallIntField(default=3, description='玩法类型')
    max_match_player = fields.SmallIntField(default=0, description='最大开局人数')
    daily_start_time = fields.CharField(max_length=32, description='每日开始时间')
    daily_end_time = fields.CharField(max_length=32, description='每日结束时间')
    total_match_round = fields.SmallIntField(default=1, description='比赛总轮次')

    class Meta:
        table = "conf_competition"

class Admins(DBModel):
    """ 后台管理员 """
    username = fields.CharField(max_length=20, unique=True, default='', description='玩家昵称')
    password = fields.CharField(max_length=64, default='', description='密码')
    updated = fields.BigIntField(null=True, default=0, description='更新时间')
    safe_key = fields.CharField(max_length=18, null=True, default='', description='安全密钥（不能泄密）')
    valid_key = fields.CharField(max_length=16, null=True, default='', description='验证密钥')
    status = fields.IntEnumField(
        enum_type=AdminStatus, defualt=AdminStatus.PENDING, description='表示管理员账户的状态，如启用、禁用、待审核等。')
    permission = fields.IntEnumField(
        enum_type=AdminPermission, defualt=AdminPermission.P1, description='管理员权限')


class RecordsAdminOperates(DBModel):
    """ 后台操作记录 """
    # _SPLIT_TYPE = 2
    username = fields.CharField(max_length=20, index=True, default='', description='操作者')
    route = fields.CharField(max_length=32, index=True, default='', description='路由')
    op_name = fields.CharField(max_length=16, default='', description='操作名（描述）')
    method = fields.CharField(max_length=8, default='', description='请求方法')
    params = fields.JSONField(null=True, default='', description='请求参数')
    status = fields.SmallIntField(description='状态码')
    hint = fields.CharField(max_length=32, default='', description='提示')

    class Meta:
        table = "records_admin_operates"

    @classmethod
    async def insert_one(cls, username, route, op_name, method, params, status, hint=''):
        data = {
            "username": username,
            "route": route,
            "op_name": op_name,
            "method": method,
            "params": params,
            "status": status,
            "hint": hint,
        }
        return await cls.add_one(data)


class RecordsAdminTimedTask(DBModel):
    """ 后台定时任务记录 """
    job_id = fields.CharField(max_length=32, pk=True, default='', description='任务id')
    cmd = fields.SmallIntField(description='命令号')
    name = fields.CharField(max_length=16, default='', description='任务名')
    start_time = fields.BigIntField(null=True, default=0, description='开始时间')
    params = fields.JSONField(null=True, default='', description='任务参数')
    status = fields.IntEnumField(enum_type=BackTaskSta, description='状态: 0已取消 1待执行 2已执行')

    class Meta:
        table = "records_admin_timed_task"

    @classmethod
    async def insert_one(cls, job_id, cmd, name, start_time, params, status):
        data = {
            "job_id": job_id,
            "cmd": cmd,
            "name": name,
            "start_time": start_time,
            "params": params,
            "status": status,
        }
        return await cls.add_one(data)