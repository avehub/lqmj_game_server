from nsanic.libs import tool_dt
from nsanic.libs.mk_random import RngMaker
from nsanic.orm.db_model import DBModel
from tortoise import fields
from tortoise.fields.base import OnDelete
from lucky_game.config import conf_srv as conf
# 下面的导入模型不要删除，导入此处只为了数据迁移
from lucky_admin.model_db.main import (
    Admins, ConfAnnouncements, RecordsAdminOperates, RecordsAdminTimedTask, RecordsAdminMails
)
from common.public.enum_const import Sex, PlayType, Switch, LevelType, RankingDanLevel, MonsterCardType, RegionEnum, \
    UserSource, ChatChannel
from lucky_game.const import QuickChatType, PlatForm, MailSta, PullSta, AchieveType, AwardType, GoodsType, \
    TaskType, PayType, AddType, StoreType, RandType, ActivityType, GotType, MailType, CompleteSta, JumpTarget, \
    ConditionType, ActivitySta, PayMode, DeliverStatus, OrderStatus, CosmeticType, GamePropType, BagSta, PutType, \
    CellType, EventType, LvDefendType, SeasonStatus, AdEventType, FriendshipSta, InteractPropType




class ItemsBase(DBModel):
    """ 基础物品项 """
    goods_id = fields.IntField(max_length=10, pk=True, default=1000, description='基础物品ID')
    goods_name = fields.CharField(max_length=32, null=False, default='', description='物品名称')
    goods_type = fields.IntEnumField(enum_type=GoodsType, null=False, index=True, default=0, description='物品类型')
    level = fields.IntField(max_length=10, null=True, description='物品等级')
    add_type = fields.IntEnumField(enum_type=AddType, default=0, description='累加类型')
    put_type = fields.IntEnumField(enum_type=PutType, default=PutType.U_BAG, description='存放类型')
    jump_target = fields.IntEnumField(enum_type=JumpTarget, default=0, description='跳转目标')
    target_data = fields.JSONField(null=True, description='跳转配置')
    time_limit = fields.IntField(max_length=20, null=True, default=0, description='默认时效 0 永久 单位：秒')
    desc = fields.CharField(max_length=256, null=True, default='', description='物品描述')
    img_url = fields.CharField(max_length=128, null=True, default='', description='图片地址')
    status = fields.SmallIntField(max_length=2, null=True, default=0, description='状态 0关闭 1开启')
    jump_data = fields.JSONField(null=True, description='跳转配置')

    class Meta:
        table = "items_base"


class ItemsProp(DBModel):
    """游戏道具项"""
    goods_id = fields.IntField(max_length=10, pk=True, default=1600, description='游戏道具ID')
    goods_name = fields.CharField(max_length=32, null=False, default='', description='道具名称')
    goods_type = fields.IntEnumField(enum_type=GoodsType, null=False, index=True, default=0, description='物品类型')
    game_prop_type = fields.IntEnumField(enum_type=GamePropType, index=True, default=0, description='游戏道具类型')
    add_type = fields.IntEnumField(enum_type=AddType, default=0, description='累加类型')
    put_type = fields.IntEnumField(enum_type=PutType, default=PutType.U_BAG, description='存放类型')
    prop_level = fields.IntField(max_length=10, index=True, null=True, default=0, description='道具等级')
    jump_target = fields.IntEnumField(enum_type=JumpTarget, default=0, description='跳转目标')
    target_data = fields.JSONField(null=True, description='跳转配置')
    time_limit = fields.IntField(max_length=20, null=True, default=0, description='默认时效 0 永久 单位：秒')
    usage_limit = fields.IntField(max_length=20, null=True, default=0, description='默认使用次数 0 永久 单位：次')
    desc = fields.CharField(max_length=256, null=True, default='', description='物品描述')
    img_url = fields.CharField(max_length=128, null=True, default='', description='图片地址')
    status = fields.SmallIntField(max_length=2, null=True, default=0, description='状态 0关闭 1开启')
    extra_info = fields.JSONField(null=True, description="额外配置信息")
    jump_data = fields.JSONField(null=True, description='跳转配置')

    class Meta:
        table = "items_prop"


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


class ItemsSkin(DBModel):
    """卡牌皮肤项"""
    goods_id = fields.IntField(max_length=10, pk=True, default=5000, description='皮肤ID')
    star_level = fields.IntField(max_length=5, null=False, default=0, description='皮肤星级')
    need_shards = fields.IntField(max_length=10, null=True, default=0, description='需要精魄数量')
    extra_info = fields.JSONField(null=True, escription='额外配置信息')
    status = fields.SmallIntField(max_length=2, null=True, default=0, description='状态 0关闭 1开启')
    skin_public = fields.ForeignKeyField(
        'lucky_game.ItemsSkinPublic', related_name='skin_public', on_delete=OnDelete.CASCADE, null=True)

    class Meta:
        table = "items_skin"


class ItemsSkinPublic(DBModel):
    """卡牌皮肤公有项"""
    public_id = fields.IntField(max_length=10, pk=True, description='皮肤公有项ID')
    goods_name = fields.CharField(max_length=32, null=False, default='', description='皮肤名称')
    goods_type = fields.IntEnumField(enum_type=GoodsType, default=0, description='物品类型')
    add_type = fields.IntEnumField(enum_type=AddType, default=0, description='累加类型')
    put_type = fields.IntEnumField(enum_type=PutType, default=PutType.U_BAG, description='存放类型')
    cs_type = fields.IntField(max_length=10, default=0, description='支持子服务类型')
    match_card = fields.IntEnumField(enum_type=MonsterCardType, index=True, default=0, description='对应卡牌')
    skin_level = fields.IntField(max_length=10, null=False, default=0, description='皮肤等级')
    top_star = fields.IntField(max_length=5, null=False, default=0, description='皮肤星级上限')
    shard_id = fields.IntField(max_length=10, null=True, description='皮肤精魄ID')
    jump_target = fields.IntEnumField(enum_type=JumpTarget, default=0, description='跳转目标')
    target_data = fields.JSONField(null=True, description='跳转配置')
    desc = fields.CharField(max_length=256, null=True, default='', description='物品描述')
    img_url = fields.CharField(max_length=128, null=True, default='', description='图片地址')
    jump_data = fields.JSONField(null=True, description='跳转配置')

    class Meta:
        table = "items_skin_public"


class ItemsLegend(DBModel):
    """英雄角色项"""
    goods_id = fields.IntField(max_length=10, pk=True, default=6000, description='英雄ID')
    goods_name = fields.CharField(max_length=32, null=False, default='', description='英雄名称')
    goods_type = fields.IntEnumField(enum_type=GoodsType, null=False, index=True, default=0, description='物品类型')
    add_type = fields.IntEnumField(enum_type=AddType, default=0, description='累加类型')
    put_type = fields.IntEnumField(enum_type=PutType, default=PutType.U_BAG, description='存放类型')
    legend_level = fields.IntField(max_length=10, index=True, null=False, description='英雄等级')
    price = fields.IntField(null=True, default=0, description='英雄价格')
    jump_target = fields.IntEnumField(enum_type=JumpTarget, default=0, description='跳转目标')
    target_data = fields.JSONField(null=True, description='跳转配置')
    time_limit = fields.IntField(max_length=20, null=True, default=0, description='默认时效 0 永久 单位：秒')
    usage_limit = fields.IntField(max_length=20, null=True, default=0, description='默认使用次数 0 永久 单位：次')
    number = fields.SmallIntField(max_length=6, null=True, default=0, description='物品排序')
    desc = fields.CharField(max_length=256, null=True, default='', description='物品描述')
    img_url = fields.CharField(max_length=128, null=True, default='', description='图片地址')
    status = fields.SmallIntField(max_length=2, null=True, default=0, description='状态 0关闭 1开启')
    extra_info = fields.JSONField(null=True, escription="额外配置信息")
    jump_data = fields.JSONField(null=True, description='跳转配置')

    class Meta:
        table = "items_legend"


class ConfQuickChat(DBModel):
    """ 快捷聊天配置（文字/表情/互动） """
    chat_id = fields.IntField(max_length=11, pk=True, description='聊天ID')
    chat_name = fields.CharField(max_length=30, default="", description='名称')
    chat_type = fields.IntEnumField(enum_type=QuickChatType, default=QuickChatType.HU_DONG, description='快捷聊天类型')
    prop_type = fields.IntEnumField(enum_type=InteractPropType, default=InteractPropType.GOOD, description='道具类型')
    free_act_type = fields.IntEnumField(enum_type=ActivityType, default=0, description='可免费使用的活动类型')
    level = fields.SmallIntField(max_length=4, null=True, default=0, description='等级')
    pay_type = fields.IntEnumField(enum_type=PayType, default=PayType.BY_FREE, description='支付类型')
    price = fields.IntField(null=True, default=0, description='商品价格')
    leisure_rate = fields.IntField(null=True, default=0, description='休闲场基础倍率价格')
    cool_down = fields.SmallIntField(max_length=2, null=True, default=0, description='冷却时间，单位秒')
    img_url = fields.CharField(max_length=255, null=True, default='', description='图片地址')
    status = fields.SmallIntField(max_length=2, null=True, default=0, description='状态 0关闭 1开启')

    class Meta:
        table = "conf_quick_chat"


class UserSkin(DBModel):
    """ 玩家皮肤 """
    skin_id = fields.IntField(max_length=10, pk=True, default=0, description='皮肤统计ID')
    uid = fields.IntField(max_length=28, index=True, null=False, description='玩家ID')
    cs_type = fields.IntField(max_length=10, default=0, description='子服务类型')
    skin_item = fields.ForeignKeyField(
        'lucky_game.ItemsSkin', related_name='skin_item', on_delete=OnDelete.CASCADE, null=True)
    skin_public_id = fields.IntField(max_length=10, index=True, default=0, description='皮肤公有项ID')
    got_type = fields.IntEnumField(enum_type=GotType, default=0, description='获得类型')
    exp_time = fields.BigIntField(max_length=28, null=True, default=0, description="过期时间")
    got_time = fields.IntField(max_length=28, null=True, default=0, description='获得时间')

    class Meta:
        table = "user_skin"
        unique_together = (("uid", "skin_public_id", "cs_type"),)

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




class ConfJson(DBModel):
    """简单配置"""
    conf_id = fields.CharField(pk=True, max_length=128, null=False, description='配置名')
    conf_data = fields.JSONField(null=False, description='具体配置')
    desc = fields.CharField(max_length=256, null=True, default='', description='奖励描述')
    update_time = fields.IntField(max_length=28, null=True, default=0, description='更新时间')

    class Meta:
        table = "conf_json"


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


class ConfTask(DBModel):
    """任务配置"""
    task_id = fields.IntField(max_length=20, pk=True, default=1, description='任务ID')
    task_type = fields.IntEnumField(enum_type=TaskType, index=True, default=1, description='任务类型')
    task_name = fields.CharField(max_length=32, null=True, default='', description='任务名称')
    achieve_type = fields.IntEnumField(enum_type=AchieveType, default=0, description='达成条件')
    achieve_value = fields.BigIntField(max_length=20, null=True, description="达成目标值")
    active_score = fields.IntField(max_length=20, null=True, description="附加活跃值")
    start_time = fields.IntField(max_length=28, null=True, default=0, description='任务开始时间')
    end_time = fields.IntField(max_length=28, null=True, default=0, description='任务结束时间')
    platform = fields.IntEnumField(enum_type=PlatForm, index=True, default=PlatForm.DEFAULT, description="平台")
    jump_target = fields.IntEnumField(enum_type=JumpTarget, default=0, description='任务跳转目标')
    target_data = fields.JSONField(null=True, description='任务跳转详细配置')
    number = fields.SmallIntField(max_length=6, null=True, default=0, description='任务排序')
    conf_items = fields.JSONField(null=True, description='可立即获得的物品配置')
    desc = fields.CharField(max_length=128, null=True, default='', description='任务描述')
    status = fields.SmallIntField(max_length=2, null=True, default=0, description='状态 0关闭 1开启')

    class Meta:
        table = "conf_task"


class StatsItemOrderCount(DBModel):
    """玩家完成订单数统计"""
    uid = fields.IntField(max_length=28, null=False, description='玩家ID')
    trade_item = fields.BigIntField(max_length=28, null=False, description='订单项目')
    order_count = fields.IntField(max_length=28, null=True, default=1, description="完成订单数量")
    order_id = fields.CharField(max_length=32, null=False, description='最新订单号')

    class Meta:
        table = "stats_item_order_count"
        unique_together = (("uid", "trade_item"),)


class ConfSeason(DBModel):
    """排位赛季记录"""
    season_id = fields.IntField(max_length=10, pk=True, default=1, description='赛季ID')
    season_desc = fields.CharField(max_length=32, null=False, description='赛季描述')
    start_time = fields.IntField(max_length=28, null=False, default=0, description='赛季开赛时间')
    end_time = fields.IntField(max_length=28, null=False, default=0, description='赛季结算时间')
    off_season_time = fields.IntField(max_length=16, null=False, default=0, description='休赛时间段：秒')
    condition = fields.SmallIntField(default=0, description="奖励条件: 游戏局数")
    status = fields.IntEnumField(enum_type=SeasonStatus, index=True, default=0, description="赛季状态")
    img_url = fields.CharField(max_length=128, null=True, default='', description='图片地址')

    class Meta:
        table = "conf_season"


class ConfRanking(DBModel):
    """ 排位配置 """
    level = fields.IntField(max_length=10, default=1, description='排位等级ID')
    season = fields.ForeignKeyField('lucky_game.ConfSeason', index=True, related_name='s_ranking')
    ranking_name = fields.CharField(max_length=32, null=False, default='', description='排位等级名称')
    major_level = fields.IntEnumField(
        enum_type=RankingDanLevel, index=True, default=RankingDanLevel.DAN_LEVEL_1, description='大段等级')
    minor_level = fields.IntField(max_length=10, index=True, null=False, description='小段等级')
    min_score = fields.IntField(max_length=20, default=0, description="最低分")
    max_score = fields.IntField(max_length=20, default=0, description="最高分")
    win_gain_score = fields.SmallIntField(default=0, description="胜利获取修为（上篇）")
    lose_deduct_score = fields.SmallIntField(default=0, description="失败扣除修为（上篇）")

    win_gain_score_seq = fields.SmallIntField(default=0, description="胜利获取修为（下篇）")
    lose_deduct_score_seq = fields.SmallIntField(default=0, description="失败扣除修为（下篇）")

    lv_defend = fields.IntEnumField(enum_type=LvDefendType, default=0, description="段位保护类型")
    ranking_match_time = fields.ForeignKeyField(
        'lucky_game.ConfRankingMatchTime', related_name="ranking", null=True, on_delete=OnDelete.SET_NULL)

    level_awards = fields.JSONField(null=True, description='段位等级奖（突破奖励）')
    season_awards = fields.JSONField(null=True, description='赛季奖（赛季结算奖励）')
    display_awards = fields.JSONField(null=True, description='展示奖励（段位奖励中的一部分，用于展示）')

    class Meta:
        table = "conf_ranking"
        unique_together = (("level", "season_id"),)


class ConfRankingMatchTime(DBModel):
    """ 排位赛匹配时间 """
    first_expend_time = fields.SmallIntField(default=0, description="首次扩充时间")
    second_expend_time = fields.SmallIntField(default=0, description="第二次扩充时间")
    force_start_time = fields.SmallIntField(default=0, description="第三扩充时间")

    # todo: 搜索深度？
    class Meta:
        table = "conf_ranking_match_time"


class UserRanking(DBModel):
    """ 用户排位 """
    # uid = fields.IntField(max_length=28, default=100000, description='玩家ID')
    user = fields.OneToOneField('lucky_game.User', related_name='ur', on_delete=OnDelete.CASCADE)
    ranking = fields.ForeignKeyField('lucky_game.ConfRanking', related_name='u_ranking', default=None)
    # season = fields.ForeignKeyField('lucky_game.ConfSeason', related_name='u_season', default=None)
    cur_score = fields.IntField(max_length=20, index=True, description='当前排位分')
    top_score = fields.IntField(max_length=20, description='历史最高段位分')  # 主要用于首次获取突破奖励
    season_achieved = fields.BooleanField(default=False, description='赛季奖是否获得')
    level_achieved = fields.JSONField(null=True, description='记录玩家奖励是否')
    region = fields.IntEnumField(enum_type=RegionEnum, default=RegionEnum.DEFAULT, description="行政区域（省份）")
    game_count = fields.IntField(max_length=16, default=0, description='游戏次数')
    updated = fields.BigIntField(null=True, default=0, description='更新时间')

    class Meta:
        table = "user_ranking"
        # unique_together = (("user", "season_id"),)
        indexes = (("region", "cur_score"),)  # 联合索引


class RecordsUserRankingHistory(DBModel):
    """ 记录玩家历史排位 """
    uid = fields.IntField(max_length=28, index=True, default=100000, description='玩家ID')
    ranking = fields.ForeignKeyField('lucky_game.ConfRanking', related_name='r_ranking', default=None)
    season = fields.ForeignKeyField('lucky_game.ConfSeason', index=True, related_name='r_season', default=None)
    cur_score = fields.IntField(max_length=20, description='当前排位分')
    top_score = fields.IntField(max_length=20, description='历史最高段位分')  # 主要用于首次获取突破奖励
    season_achieved = fields.BooleanField(default=False, description='赛季奖是否获得')
    level_achieved = fields.JSONField(null=True, description='记录玩家奖励是否')
    region = fields.IntEnumField(enum_type=RegionEnum, default=RegionEnum.DEFAULT, description="行政区域（省份）")
    game_count = fields.IntField(max_length=16, default=0, description='游戏次数')

    class Meta:
        table = "records_user_ranking_history"
        unique_together = (("uid", "season_id"),)
        indexes = (("season_id", "season_achieved", "game_count"),)


# class UserLeague(DBModel):
#     """ 降妖结盟 """
#     user = fields.OneToOneField('lucky_game.User', related_name='ul', on_delete=OnDelete.CASCADE)
#     contribution_val = fields.IntField(max_length=16, default=0, description='贡献值')
#     region = fields.IntEnumField(enum_type=RegionEnum, default=RegionEnum.DEFAULT, description="行政区域（省份）")
#     join_time = fields.BigIntField(null=True, default=0, description='加入时间，退出时置为0，主要用于发奖判断')
#     personal_achieved = fields.BooleanField(default=False, description='个人奖励奖是否获得')
#     area_achieved = fields.BooleanField(default=False, description='地区奖励是否达成')
#     updated = fields.BigIntField(null=True, default=0, description='更新时间')
#
#     class Meta:
#         table = "user_league"


class RecordsUserTask(DBModel):
    """任务记录"""
    uid = fields.IntField(max_length=28, index=True, null=False, description='玩家ID')
    time_node = fields.BigIntField(max_length=28, index=True, null=True, default=0, description='时间节点：天')
    task = fields.ForeignKeyField('lucky_game.ConfTask', related_name='conf_task')
    task_type = fields.IntEnumField(enum_type=TaskType, index=True, default=1, description='任务类型')
    task_sta = fields.IntEnumField(enum_type=CompleteSta, index=True, default=1, description="任务完成状态")
    cur_value = fields.BigIntField(max_length=4, null=False, default=0, description='任务完成情况')
    finish_time = fields.BigIntField(max_length=28, null=True, default=0, description='完成时间')

    class Meta:
        table = "records_user_task"
        unique_together = (("uid", "task_id"),)


# class ConfWinStreakAddition(DBModel):
#     """ 连胜加成表 """
#     a_type = fields.IntEnumField(enum_type=AdditionType, description="加成类型: 修为|金币|...等")
#     win_streak = fields.SmallIntField(null=True, default=0, description='连胜场数')
#     percentage = fields.IntField(max_length=28, default=0, description='占比')
#     cs_type = fields.IntField(max_length=10, default=0, description="子服务类型")
#
#     class Meta:
#         table = "conf_win_streak_addition"


class UserMonopoly(DBModel):
    """ 玩家大富翁记录 """
    uid = fields.IntField(max_length=28, pk=True, default=100000, description='玩家ID')
    map = fields.JSONField(null=True, description='随机奖励映射')
    position = fields.SmallIntField(null=True, default=0, description='当前玩家所在位置')
    updated = fields.BigIntField(null=True, default=0, description='更新时间')

    class Meta:
        table = "user_monopoly"


class ConfMonopolyMap(DBModel):
    """大富翁地图配置"""
    cell_id = fields.SmallIntField(pk=True, default=1, description='格子ID')
    cell_name = fields.CharField(max_length=32, null=True, default='', description='格子名称')
    cell_type = fields.IntEnumField(enum_type=CellType, index=True, default=0, description='格子类型')
    conf_items = fields.JSONField(null=True, description='固定奖励配置')
    event_id = fields.SmallIntField(max_length=10, null=True, description='事件ID')
    desc = fields.CharField(max_length=256, null=True, default='', description='格子描述')
    status = fields.SmallIntField(max_length=2, null=True, default=0, description='状态 0关闭 1开启')

    class Meta:
        table = "conf_monopoly_map"


class ConfMonopolyEvent(DBModel):
    """大富翁事件配置"""
    event_id = fields.SmallIntField(max_length=20, pk=True, default=1, description='事件ID')
    event_name = fields.CharField(max_length=32, null=False, default='', description='事件名称')
    event_type = fields.IntEnumField(enum_type=EventType, index=True, default=0, description='事件类型')
    weight = fields.SmallIntField(null=True, default=0, description='事件权重')
    ending_odds = fields.JSONField(null=True, description='结局概率')
    conf_items = fields.JSONField(null=True, description='结局奖励配置')
    conf_ending = fields.JSONField(null=True, description='结局类型配置')
    conf_execute = fields.JSONField(null=True, description='结局执行配置')
    conf_desc = fields.JSONField(null=True, description='结局描述配置')
    desc = fields.CharField(max_length=256, null=True, default='', description='事件描述')
    status = fields.SmallIntField(max_length=2, null=True, default=0, description='状态 0关闭 1开启')

    class Meta:
        table = "conf_monopoly_event"


class ConfMonopolyStore(DBModel):
    """ 大富翁商店配置 """
    store_id = fields.IntField(max_length=10, pk=True, default=2100, description='商品ID')
    store_type = fields.IntEnumField(enum_type=StoreType, index=True, default=0, description='商品类型')
    store_name = fields.CharField(max_length=32, null=True, default='', description='商品名称')
    store_count = fields.IntField(max_length=10, null=True, default=0, description='商品数量')
    pay_type = fields.IntEnumField(enum_type=PayType, default=PayType.BY_FREE, description='支付类型')
    price = fields.IntField(null=True, default=0, description='商品价格')
    product_id = fields.CharField(max_length=32, null=True, description='微信道具ID')
    discount = fields.FloatField(null=True, default=0, description='商品折扣')
    discount_price = fields.IntField(null=True, default=0, description='折扣价格')
    sub_label = fields.JSONField(null=True, description='子标签')
    time_limit = fields.IntField(max_length=20, null=True, default=0, description='商品购买时效 0 永久 单位：秒')
    buy_limit = fields.JSONField(null=True, description='商品限购配置')
    rand_type = fields.IntEnumField(enum_type=RandType, default=0, description='返利类型')
    number = fields.SmallIntField(max_length=6, null=True, default=0, description='商品排序')
    desc = fields.CharField(max_length=256, null=True, default='', description='商品描述')
    conf_items = fields.JSONField(null=True, description='商品配置')
    img_url = fields.CharField(max_length=128, null=True, default='', description='图片地址')
    start_sale_time = fields.IntField(max_length=20, null=True, default=0, description='商品开售时间')
    end_sale_time = fields.IntField(max_length=20, null=True, default=0, description='商品止售时间')
    status = fields.SmallIntField(max_length=2, null=True, default=0, description='状态 0关闭 1开启')

    class Meta:
        table = "conf_monopoly_store"


class RecordsTradeOrder(DBModel):
    """ 交易订单记录 """
    order_id = fields.CharField(max_length=32, pk=True, description='订单号')
    uid = fields.IntField(max_length=28, null=False, description='玩家ID')
    trade_item = fields.BigIntField(max_length=28, null=False, description='订单项目')
    trade_item_count = fields.IntField(max_length=28, null=True, default=1, description="交易项目数")
    order_status = fields.IntEnumField(enum_type=OrderStatus, default=OrderStatus.WAIT_PAY, description="订单状态")
    deliver_status = fields.IntEnumField(
        enum_type=DeliverStatus, default=DeliverStatus.UNSHIPPED, description="发货状态")
    orig_price = fields.IntField(null=False, default=0, description="原价")
    actual_price = fields.IntField(null=False, default=0, description="实际价格")
    trade_amount = fields.IntField(null=False, default=0, description="交易数额")
    trade_time = fields.BigIntField(max_length=28, null=True, default=0, description="交易时间")
    finish_time = fields.BigIntField(max_length=28, null=True, default=0, description='完成时间')
    pay_type = fields.IntEnumField(PayType, description="支付类型")
    pay_mode = fields.IntEnumField(PayMode, description="支付方式")
    order_source = fields.IntEnumField(PlatForm, description="订单来源")
    order_desc = fields.CharField(max_length=128, null=True, description='订单描述')
    extra_info = fields.JSONField(null=True, escription="额外信息")  # 例如：道具ID

    class Meta:
        table = "records_trade_order"

    @classmethod
    async def gen_insert_data(cls, **kwargs):
        """ 生成插入数据 """
        data = {
            "order_id": await RngMaker.gen_num(str_len=32),
            "uid": kwargs.get("uid"),
            "trade_item": kwargs.get("trade_item"),
            "trade_item_count": kwargs.get("trade_item_count"),
            "order_status": kwargs.get("order_status"),
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
            "extra_info": kwargs.get("extra_info")
        }
        return data

    @classmethod
    async def query_trade_order(cls, order_id) -> bool or dict:
        """ 查询订单是否已支付 """
        order_info = await cls.get_by_pk(order_id)
        if not order_info:
            return False
        return order_info


class RecordsAdsEvent(DBModel):
    """ 广告事件记录 """
    user_source = fields.IntEnumField(enum_type=UserSource, index=True, default=UserSource.Own, description="用户来源")
    click_id = fields.CharField(max_length=256, index=True, null=False, description="点击ID")
    promotion_id = fields.CharField(max_length=32, null=False, description="广告ID")
    request_id = fields.CharField(max_length=68, null=True, description='请求ID')
    os = fields.CharField(max_length=10, null=True, description='操作系统平台')
    uid = fields.IntField(max_length=28, null=True, description='玩家ID')
    event_type = fields.IntEnumField(
        enum_type=AdEventType, index=True, default=AdEventType.AD_ACTIVE, description='点击事件类型')

    class Meta:
        table = "records_ads_event"


class RecordsAdsUser(DBModel):
    """ 广告用户记录 """
    id = fields.IntField(max_length=10, pk=True)
    user_source = fields.IntEnumField(enum_type=UserSource, index=True, default=UserSource.Own, description="用户来源")
    openid = fields.CharField(max_length=128, index=True, description="授权用户唯一标识")
    promotion_id = fields.CharField(max_length=32, index=True, description="广告ID")
    first_active_time = fields.BigIntField(max_length=28, null=True, default=0, description="首次激活时间")
    first_open_time = fields.BigIntField(max_length=28, null=True, default=0, description="首次打开广告时间")
    total_cost = fields.FloatField(null=True, default=0, description="总广告消耗（单位十万分之一元）")
    max_cost = fields.FloatField(null=True, default=0, description="最大单次消耗（单位十万分之一元）")
    ad_open_count = fields.IntField(max_length=10, null=True, default=0, description="广告打开次数")
    cost_open_count = fields.IntField(max_length=10, null=True, default=0, description="有消耗打开次数")
    avg_ecpm = fields.FloatField(null=True, default=0, description="平均ECPM")
    user_type = fields.IntField(null=True, default=0, description="用户类型（0新/1老）")
    is_active = fields.IntField(null=True, default=0, description="是否激活")
    pay_amount = fields.IntField(max_length=10, null=True, default=0, description="交易数额")

    class Meta:
        table = "records_ads_user"
        unique_together = (("openid", "promotion_id"),)


class RecordsAdsParams(DBModel):
    """
    记录广告参数
    advertiser_id > project_id > promotion_id
    """
    promotion_id = fields.CharField(max_length=32, index=True, description="广告ID")
    project_id = fields.CharField(max_length=32, index=True, description="项目ID")
    advertiser_id = fields.CharField(max_length=32, index=True, description="广告主id")

    class Meta:
        table = "records_ads_params"
        unique_together = (("promotion_id", "project_id", "advertiser_id"),)


class StatsAdsEvent(DBModel):
    """ 统计广告事件 """
    stats_id = fields.IntField(max_length=10, pk=True, description="统计ID")
    user_source = fields.IntEnumField(enum_type=UserSource, index=True, default=UserSource.Own, description="用户来源")
    time_node = fields.BigIntField(max_length=28, index=True, null=False, default=0, description="时间节点：天")
    promotion_id = fields.CharField(max_length=32, index=True, null=False, description="广告ID")
    active_times = fields.IntField(max_length=28, null=True, default=0, description="激活次数")
    register_times = fields.IntField(max_length=28, null=True, default=0, description="注册次数")
    ads_times = fields.IntField(max_length=28, null=True, default=0, description="看广告次数")
    first_pay_times = fields.IntField(max_length=28, null=True, default=0, description="首次付费次数")
    pay_times = fields.IntField(max_length=28, null=True, default=0, description="付费次数")
    pay_amount = fields.BigIntField(max_length=28, null=True, default=0, description="交易数额")

    class Meta:
        table = "stats_ads_event"
        unique_together = (("promotion_id", "time_node", "user_source"),)


class StatsGameTimes(DBModel):
    """ 统计游戏总量 """
    time_node = fields.BigIntField(max_length=28, index=True, null=False, default=0, description="时间节点：天")
    cs_type = fields.IntField(max_length=10, default=0, description="子服务类型")
    play_type = fields.IntEnumField(enum_type=PlayType, default=PlayType.CLASSICAL, description="玩法类型")
    game_times = fields.IntField(max_length=28, null=True, default=0, description="总游戏局数")
    avg_game_times = fields.IntField(max_length=28, null=True, default=0, description="平均游戏局数")

    class Meta:
        table = "stats_game_times"
        unique_together = (("time_node", "cs_type"),)


class StatsRetentionAdsUser(DBModel):
    """ 统计广告用户留存 """
    time_node = fields.BigIntField(max_length=28, index=True, null=False, default=0, description="时间节点：天")
    old_user_count = fields.IntField(max_length=32, default=0, description="老用户总数")
    new_user_count = fields.IntField(max_length=32, default=0, description="新增用户总数")
    pay_user_count = fields.IntField(max_length=32, default=0, description="付费用户总数")
    user_source = fields.IntEnumField(enum_type=UserSource, index=True, default=UserSource.Own, description="用户来源")

    class Meta:
        table = "stats_retention_ads_user"


class StatsRetentionOwnUser(DBModel):
    """ 统计全部用户留存 """
    id = fields.IntField(max_length=10, pk=True)
    time_node = fields.BigIntField(max_length=28, index=True, null=False, default=0, description="时间节点：天")
    day_1_count = fields.IntField(max_length=10, default=0, description="次日留存数")
    day_1_retention = fields.FloatField(max_length=10, default=0.0, description="次日留存率")
    day_3_count = fields.IntField(max_length=10, default=0, description="三日留存数")
    day_3_retention = fields.FloatField(max_length=10, default=0.0, description="三日留存率")
    day_7_count = fields.IntField(max_length=10, default=0, description="七日留存数")
    day_7_retention = fields.FloatField(max_length=10, default=0.0, description="七日留存率")
    day_14_count = fields.IntField(max_length=10, default=0, description="十四日留存数")
    day_14_retention = fields.FloatField(max_length=10, default=0.0, description="十四日留存率")
    day_30_count = fields.IntField(max_length=10, default=0, description="三十日留存数")
    day_30_retention = fields.FloatField(max_length=10, default=0.0, description="三十日留存率")

    class Meta:
        table = "stats_retention_own_user"






