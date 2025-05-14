import asyncio
import random
from nsanic.libs import tool_dt
from nsanic.libs.tool import json_encode
from tortoise.transactions import in_transaction
from c_services.base.base_server import JsonBaseServer
from c_services.const.cs_enum_const import CmdWorkers, CmdNotice, RedDotType, CmdWs, GameAnnouncement
from common.proto.py_pb2.common import common_pb2
from common.proto.py_pb2.ws_leisure import S2CTopAnnouncements
from common.public.conf import ROBOT_RANK
from common.public.enum_const import TaskId, DbKey, LEISURE_GAME_LIST
from common.utils.kit_async import DelayCall
from common.utils.kit_dt import KitDt
from lucky_admin.const import BackTaskSta, WeightEnum
from lucky_admin.model_db.main import RecordsAdminTimedTask
from lucky_admin.model_rc.mails_manage import RecordsAdminMailsRC
from lucky_game.model_rc.active_behaviors import UserBehaviorsRC
from lucky_game.model_rc.base_activity import UserActivityRC
from lucky_game.model_rc.base_bag import UserBagRC
from lucky_game.model_rc.base_game_task import UserTaskRC, ConfTaskRC
from lucky_game.model_rc.base_goods import ItemsBaseRC
from lucky_game.model_rc.base_interaction import InteractionRC
from lucky_game.model_rc.base_mails import MailsRC
from lucky_game.model_rc.base_prop import ItemsPropRC
from lucky_game.model_rc.base_safe_box import UserSafeBoxRC
from lucky_game.model_rc.base_skin import UserSkinRC, ItemsSkinRC
from lucky_game.model_rc.base_store import ConfStoreRC
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.model_rc.conf_json import ConfJsonRC
from lucky_game.model_rc.base_cosmetic import UserCosmeticRC, ItemsCosmeticRC
from lucky_game.model_rc.conf_leisure import LeisureConfRC
from lucky_game.model_rc.goods_manager import GoodsManagerRC
from lucky_game.model_rc.vip_level import UserVipRC, ConfVipRC
from lucky_game.model_rc.player_game_times import PlayerGameTimesRC
from lucky_game.model_db.extra import RecordsGameGrade, RecordsUserEvent
from lucky_game.model_db.log import RecordsGoldStatement, RecordsDiamondStatement
from lucky_game.model_rc.base_ranking import UserRankingRC, ConfRankingRC, ConfSeasonRC
from lucky_game.model_db.main import Mails, RecordsUserRankingHistory, RecordsTradeOrder
from lucky_game.const import ActivityItem, GoodsItem, StoreItem, TaskType, AwardType, MailType, \
    CompleteSta, EventTracking, OrderStatus


class WorkersServer(JsonBaseServer):
    """
    工人服务：专门用于不停地消费异步任务调度，如游戏内的数据库操作等可以发往该服务进行消费
    该服务可开启多个实例：rmq内部会负载均衡
    """
    ONCE_OPERATION_LIMIT = 1000  # 单次操作上限
    TASK_DATE_KEY = 'task_date'
    delay_fail = 2

    def __init__(self):
        super().__init__()
        self.__timed_server = None
        self.add_handlers({
            CmdWorkers.UPDATE_GAME_TIMES: self.__update_game_times,
            CmdWorkers.INSERT_GAME_GRADE: self.__insert_game_grade,
            CmdWorkers.UPDATE_GAME_TASK: self.__update_game_task,
            CmdWorkers.INSERT_GOLD_STATEMENT: self.__insert_gold_statement,
            CmdWorkers.INSERT_DIAMOND_STATEMENT: self.__insert_diamond_statement,
            CmdWorkers.MANAGER_SEND_MAILS: self.__manager_send_mails,
            CmdWorkers.NEW_USER_GIVE_GIFT: self.__new_user_give_gift,
            CmdWorkers.GET_RED_DOT_LIST: self.__get_red_dot_by_list,
            CmdWorkers.UPDATE_USER_VIP_LEVEL: self.__update_user_vip_level,
            CmdWorkers.UPDATE_ITEM_ORDER_COUNT: self.__update_item_order_count,
            CmdWorkers.UPDATE_BAG_PROP: self.__update_bag_prop,
            CmdWorkers.BAN_PLAYER: self.__ban_player,
            CmdWorkers.SET_NEW_SEASON: self.__set_new_season,
            CmdWorkers.CHECK_LIMITED_GOODS: self.__check_limited_goods,
            CmdWorkers.NOTIFY_ANNOUNCEMENT: self.__notify_announcement,
            CmdWorkers.LOGIN_SIGN_IN: self.__login_sign_in,
            CmdWorkers.BACKGROUND_SCHEDULED_TASK: self.__background_scheduled_task,
            CmdWorkers.CANCEL_BACKGROUND_SCHEDULED_TASK: self.__cancel_background_scheduled_task,
            CmdWorkers.FETCH_ACTIVE_MAILS: self.__fetch_active_mails,
            CmdWorkers.USER_EVENT_TRACKING: self.__user_event_tracking,
            # CmdWorkers.PROCESS_SAFE_BOX: self.__process_safe_box,
        })

        self.register_rc_model(
            GoodsManagerRC, PlayerGameTimesRC, ConfTaskRC, UserTaskRC, UserBehaviorsRC, ConfStoreRC, UserVipRC,
            BaseUserRC, UserActivityRC, ConfVipRC, ConfJsonRC, UserSafeBoxRC, UserCosmeticRC, ItemsCosmeticRC,
            UserBagRC, UserSkinRC, ItemsSkinRC, UserRankingRC, ConfRankingRC, MailsRC, ItemsPropRC,
            ItemsBaseRC, ConfSeasonRC, RecordsAdminMailsRC, LeisureConfRC
        )

        self.__user_query_red_dot_func_map = {}  # 记录用户查询红点任务

        DelayCall(1, self.__get_date_task_exec).start()
        DelayCall(1, self.__rand_loop_game_announcement).start()

    async def __rand_loop_game_announcement(self):
        while 1:
            await asyncio.sleep(random.randint(60, 90))
            await self.__loop_game_announcement()

    @classmethod
    def red_dot_log(cls, *data):
        cls.info_log("红点任务：", *data)

    async def __update_game_times(self, uid, data):
        """ 更新游戏次数 """
        data.update({"uid": uid})
        res = await PlayerGameTimesRC.update_game_times(data)
        self.info_log(uid, "更新玩家次数", res)

    async def __insert_game_grade(self, _, data):
        """ 插入游戏战绩 """
        up_rank = data.pop('up_rank', False)
        grade_data = data.get('data')
        self.info_log("插入玩家战绩", data, up_rank)
        if up_rank:
            for one_data in grade_data:
                rank_score = one_data.get("rank_score")
                uid = one_data.get("uid")
                rank_score = await UserRankingRC.update_user_ranking_score(uid, rank_score, 1)
                one_data["rank_score"] = rank_score

                await self.__user_event_tracking(uid, {'event_tracking': EventTracking.AFTER_FIRST_GAME.val})
        await RecordsGameGrade.split_bulk_insert(grade_data)

    async def __update_game_task(self, uid, data):
        """ 更新游戏任务 """
        self.info_log(uid, "更新游戏任务", data)
        finish_flag, old_task = await UserTaskRC.update_user_task_records(uid, data)
        if finish_flag:
            await self.__send_notice_to_task(uid, old_task.get("task_type"))

    async def __update_user_vip_level(self, uid, data):
        """ 更新VIP经验值 """
        self.info_log(uid, "更新VIP经验值", data)
        _, up_flag = await UserVipRC.update_user_vip_level(uid, amount=data.get("amount"))
        if up_flag:
            await self.__notice_by_vip(uid, up_flag)
            # await self.__process_safe_box(uid, _)
            await self.__user_event_tracking(uid, {'event_tracking': EventTracking.AFTER_FIRST_PAY.val})

    async def __insert_gold_statement(self, uid, data):
        """ 插入灵石流水 """
        self.info_log(uid, "插入灵石流水", data)
        await RecordsGoldStatement.insert_one(uid, **data)

    async def __insert_diamond_statement(self, uid, data):
        """ 插入仙玉流水 """
        self.info_log(uid, "插入仙玉流水", data)
        await RecordsDiamondStatement.insert_one(uid, **data)

    async def __new_user_give_gift(self, uid, data):
        """ 新用户赠送礼物 """
        self.info_log(uid, "新用户赠送礼物", data)

    async def __await_get_ws_id(self, uid, time_limit=60):
        re_time = tool_dt.cur_time()
        while tool_dt.cur_time() - re_time < time_limit:
            await asyncio.sleep(self.delay_fail)
            ws_id = await self.get_player_ws_id(uid)
            if ws_id:
                return ws_id
        return 0

    async def __get_red_dot_by_list(self, uid, data):
        """
        根据红点列表获取红点
        不传时获取所有红点
        在规定时间内重复调用则取消之前未完成的调用
        """
        red_dot_task = self.__user_query_red_dot_func_map.get(uid)
        if red_dot_task and not red_dot_task.done():
            red_dot_task.cancel()
        # 创建并启动新任务
        new_red_dot_task = asyncio.create_task(self.__batch_get_red_dot(uid, data))
        self.__user_query_red_dot_func_map[uid] = new_red_dot_task

        def remove_task(task):
            if not task.cancelled() and task.done():
                self.__user_query_red_dot_func_map.pop(uid)

        new_red_dot_task.add_done_callback(remove_task)

    async def __batch_get_red_dot(self, uid, data):
        """批量获取红点"""
        ws_id = await self.__await_get_ws_id(uid)
        if not ws_id:
            self.red_dot_log(uid, f"玩家{uid}ws未连上，无法获取红点")
            return
        rd_type_list = data.get("rd_type_list") or RedDotType.all_values()
        self.red_dot_log(uid, "批量获取红点>>>", rd_type_list)
        get_red_dots = self.__get_red_dot_tasks(uid, rd_type_list)
        get_red_dots and await asyncio.gather(*get_red_dots)

    def __get_red_dot_tasks(self, uid, rd_type_list):
        """根据红点类型生成任务列表"""
        map_func = {
            RedDotType.RD_SIGN_IN_RF.val: self.__notice_by_sign_in_by_raffle,
            RedDotType.RD_SIGN_IN.val: self.__notice_by_sign_in_by_seven,
            RedDotType.RD_SIGN_IN_WK.val: self.__notice_by_sign_in_by_week,
            RedDotType.RD_STORE.val: self.__notice_by_store,
            RedDotType.RD_TASK.val: self.__notice_by_task,
            RedDotType.RD_MAILS.val: self.__notice_by_mails,
            RedDotType.RD_VIP.val: self.__notice_by_vip,
            RedDotType.RD_FIRST_CHARGE.val: self.__notice_by_first_charge,
            RedDotType.RD_WEEK_CARD.val: self.__notice_by_week_card,
            RedDotType.RD_LIFETIME_CARD.val: self.__notice_by_lifetime_card,
            RedDotType.RD_PERSONAL.val: self.__notice_by_personal,
            # RedDotType.RD_RELIEF.val: self.__notice_by_relief,
            RedDotType.RD_BAG.val: self.__notice_by_bag,
            RedDotType.RD_SKIN.val: self.__notice_by_skin,
            RedDotType.RD_MONOPOLY.val: self.__notice_by_monopoly,
            RedDotType.RD_MONOPOLY_FREE_DICE.val: self.__notice_by_monopoly_store,
            RedDotType.RD_MONOPOLY_TASK.val: self.__notice_by_monopoly_task,
            RedDotType.RD_RANKING_AWARDS.val: self.__notice_by_ranking_awards,
            RedDotType.RD_DOUYIN_REVISIT.val: self.__notice_by_douyin_revisit
        }
        # 按RedDotType分组
        get_tasks = []
        for rd_type in rd_type_list:
            pt_enum = RedDotType.find_member_by_val(rd_type)
            if not isinstance(pt_enum, RedDotType):
                self.red_dot_log('RedDotType 不存在', pt_enum)
                continue
            add_func = map_func.get(rd_type)
            if add_func and callable(add_func):
                get_tasks.append(add_func(uid))

        return get_tasks

    async def __notify_red_dot(self, uid, rd_type):
        """ 红点消息 """
        model = common_pb2.S2COneFieldWeb()
        model.red_dot = rd_type
        await self.notice_ws_by_rmq(CmdNotice.RED_DOT, uid=uid, msg=model)

    async def __notice_by_sign_in_by_raffle(self, uid):
        """抽奖签到红点"""
        sta = await UserBehaviorsRC.get_sign_in_unclaimed(uid, AwardType.SIGN_IN_RF)
        self.red_dot_log(uid, "抽奖签到红点查询", sta)
        if sta:
            await self.__notify_red_dot(uid, RedDotType.RD_SIGN_IN_RF)

    async def __notice_by_sign_in_by_seven(self, uid):
        """七日签到红点"""
        sta = await UserBehaviorsRC.get_sign_in_unclaimed(uid, AwardType.SIGN_IN)
        self.red_dot_log(uid, "七日签到红点查询", sta)
        if sta:
            await self.__notify_red_dot(uid, RedDotType.RD_SIGN_IN)

    async def __notice_by_sign_in_by_week(self, uid):
        """每周七日签到红点"""
        sta = await UserBehaviorsRC.get_sign_in_unclaimed(uid, AwardType.SIGN_IN_WK)
        self.red_dot_log(uid, "每周七日签到红点查询", sta)
        if sta:
            await self.__notify_red_dot(uid, RedDotType.RD_SIGN_IN_WK)

    async def __notice_by_store(self, uid):
        """游戏商店红点"""
        sta = await ConfStoreRC.get_store_free_chance(uid, StoreItem.FREE_GOLD)
        self.red_dot_log(uid, "游戏商店红点查询", sta)
        if sta:
            await self.__notify_red_dot(uid, RedDotType.RD_STORE)

    async def __notice_by_mails(self, uid):
        """邮件红点"""
        sta = await MailsRC.get_unread_mails(uid)
        self.red_dot_log(uid, "邮件红点查询", sta)
        if sta:
            await self.__notify_red_dot(uid, RedDotType.RD_MAILS)

    async def __send_notice_to_task(self, uid, task_type=TaskType.DAILY_TASK):
        """任务红点推送"""
        rd_type = RedDotType.RD_TASK if task_type == TaskType.DAILY_TASK else RedDotType.RD_MONOPOLY_TASK
        self.red_dot_log(uid, "任务红点推送")
        await self.__notify_red_dot(uid, rd_type)

    async def __notice_by_task(self, uid):
        """任务红点"""
        sta = await UserTaskRC.get_task_unclaimed(uid, TaskType.DAILY_TASK)
        self.red_dot_log(uid, "任务红点查询", sta)
        if sta:
            await self.__send_notice_to_task(uid, TaskType.DAILY_TASK)

    async def __notice_by_vip(self, uid, sta=None):
        """VIP红点查询"""
        if not sta:
            sta = await UserVipRC.get_vip_unclaimed(uid)
        self.red_dot_log(uid, "VIP红点查询", sta)
        if sta:
            await self.__notify_red_dot(uid, RedDotType.RD_VIP)

    async def __notice_by_lifetime_card(self, uid):
        """终生卡红点"""
        l_cards = (ActivityItem.LIFETIME_CARD_2.val, ActivityItem.LIFETIME_CARD_1.val)
        sta = await UserActivityRC.get_activity_unclaimed(uid, l_cards)
        self.red_dot_log(uid, "终生卡红点查询", sta)
        if sta:
            await self.__notify_red_dot(uid, RedDotType.RD_LIFETIME_CARD)

    async def __notice_by_week_card(self, uid):
        """周卡红点"""
        w_cards = (ActivityItem.WEEK_CARD_2.val, ActivityItem.WEEK_CARD_1.val)
        sta = await UserActivityRC.get_activity_unclaimed(uid, w_cards)
        self.red_dot_log(uid, "周卡红点查询", sta)
        if sta:
            await self.__notify_red_dot(uid, RedDotType.RD_WEEK_CARD)

    async def __notice_by_first_charge(self, uid):
        """首充红点"""
        sta = await UserActivityRC.get_first_charge_chance(uid, ActivityItem.FIRST_CHARGE.val)
        self.red_dot_log(uid, "首充红点查询", sta)
        if sta:
            await self.__notify_red_dot(uid, RedDotType.RD_FIRST_CHARGE)

    async def __notice_by_relief(self, uid):
        """救济红点"""
        sta = await InteractionRC.get_relief_chance(uid)
        self.red_dot_log(uid, "救济红点查询", sta)
        if sta:
            await self.__notify_red_dot(uid, RedDotType.RD_RELIEF)

    async def __notice_by_personal(self, uid):
        """个人中心红点"""
        sta = await BaseUserRC.deal_user_update_goods(uid, key_name=UserCosmeticRC.KEY_NEWLY)
        self.red_dot_log(uid, "个人中心红点查询", sta)
        if sta:
            await self.__notify_red_dot(uid, RedDotType.RD_PERSONAL)

    async def __notice_by_bag(self, uid):
        """背包红点"""
        sta = await BaseUserRC.deal_user_update_goods(uid, key_name=UserBagRC.KEY_NEWLY)
        self.red_dot_log(uid, "背包红点查询", sta)
        if sta:
            await self.__notify_red_dot(uid, RedDotType.RD_BAG)

    async def __notice_by_skin(self, uid):
        """皮肤红点"""
        new_sta = await BaseUserRC.deal_user_update_goods(uid, key_name=UserSkinRC.KEY_NEWLY)
        self.red_dot_log(uid, "新皮肤红点查询", new_sta)
        if new_sta:
            return await self.__notify_red_dot(uid, RedDotType.RD_SKIN)

        up_sta = await UserSkinRC.deal_upgradable_skin(uid)
        self.red_dot_log(uid, "可升级皮肤查询", up_sta)
        if up_sta:
            return await self.__notify_red_dot(uid, RedDotType.RD_SKIN)

    async def __notice_by_monopoly(self, uid):
        """大富翁有骰子红点"""
        data = await UserBagRC.get_user_bag_by_id(uid, goods_id=GoodsItem.DICE.val)
        dice_count = data.get("goods_count") or 0
        self.red_dot_log(uid, "大富翁红点查询", dice_count)
        if dice_count >= 1:
            await self.__notify_red_dot(uid, RedDotType.RD_MONOPOLY)

    async def __notice_by_monopoly_store(self, uid):
        """ 大富翁商店可领取红点 """
        sta = await ConfStoreRC.get_store_free_chance(uid, StoreItem.FREE_DICE)
        self.red_dot_log(uid, "大富翁商店红点查询", sta)
        if sta:
            await self.__notify_red_dot(uid, RedDotType.RD_MONOPOLY_FREE_DICE)

    async def __notice_by_monopoly_task(self, uid):
        """ 大富翁是任务可领取红点 """
        sta = await UserTaskRC.get_task_unclaimed(uid, TaskType.MONOPOLY_TASK)
        self.red_dot_log(uid, "大富翁任务红点查询", sta)
        if sta:
            await self.__send_notice_to_task(uid, TaskType.MONOPOLY_TASK)

    async def __notice_by_ranking_awards(self, uid):
        """ 境界奖励未领取红点 """
        sta = await UserRankingRC.get_ranking_unclaimed(uid)
        self.red_dot_log(uid, "排位境界红点查询", sta)
        if sta:
            await self.__notify_red_dot(uid, RedDotType.RD_RANKING_AWARDS)

    async def __notice_by_douyin_revisit(self, uid):
        """ 抖音侧边栏未领取红点 """
        sta = await UserTaskRC.get_douyin_revisit_chance(uid)
        self.red_dot_log(uid, "抖音侧边栏红点查询", sta)
        if sta:
            await self.__notify_red_dot(uid, RedDotType.RD_DOUYIN_REVISIT)

    async def __process_safe_box(self, uid, _):
        """激活/升级/扩容保险箱"""
        top_conf = await UserActivityRC.check_top_lifetime_card(uid)
        self.info_log(uid, "激活/升级/扩容保险箱", top_conf)
        if top_conf:
            vip_conf = await UserVipRC.get_vip_conf_by_uid(uid)
            await UserSafeBoxRC.process_safe_box(
                uid, top_conf.get("space", 0), top_conf.get("draw_add_times", 0), vip_conf.get("increase_space", 0))

    async def __update_item_order_count(self, uid, data):
        """ 更新玩家完成订单数 """
        res = await UserBehaviorsRC.update_user_order_count(uid, data)
        self.info_log(uid, "更新玩家完成订单数", True if res else False)

    async def __update_bag_prop(self, uid, data):
        """ 更新背包物品 """
        data = data.get("prop") or []
        if not data:
            return
        await UserBagRC.update_user_bag(uid, data)
        goods_id_list = []
        for d in data:
            goods_id_list.append(d.get('goods_id'))
        await UserBagRC.batch_deal_new_props(uid, goods_id_list)
        self.info_log(uid, "更新背包物品", data)

    async def __check_limited_goods(self, uid, data):
        """检查限时物品"""
        # 法相
        # sta = await UserSkinRC.deal_expire_skin(uid, data.get('cs_type'))
        self.info_log(uid, "检查限时物品")

    async def __manager_send_mails(self, _, data):
        """管理员发邮件"""
        receiver = data.pop("receiver")
        if not receiver:
            return
        broad = False
        appoint_uid_list = None
        if receiver.get('type') == "group":
            uid_list = receiver.get('uid_list')
            appoint_uid_list = uid_list
            uid_list = await BaseUserRC.get_receiver_by_uid_list(uid_list)

            data["receivers"] = uid_list
            await self.__bulk_send_mails(_, data)
        else:
            # todo: 分批插入
            batch_size = 1000
            start_uid = 0
            while 1:
                uid_list = await BaseUserRC.fetch_uid_by_batch_size(batch_size, start_uid)
                if not uid_list:
                    break
                data["receivers"] = uid_list
                await self.__bulk_send_mails(_, data)
                start_uid = uid_list[-1]
                await asyncio.sleep(0.0001)
            broad = True

        # 分离在线用户和离线用户
        online_uid = await BaseUserRC.get_online_uid(uid_list=appoint_uid_list)
        online_list = list(online_uid)

        # 通知在线用户或全员通知
        if broad:
            await self.__notify_red_dot(1, RedDotType.RD_MAILS)
        else:
            for uid in online_list:
                await self.__notify_red_dot(uid, RedDotType.RD_MAILS)

    async def __bulk_send_mails(self, _, data):
        """
        群发邮件及通知
        receivers：群发名单
        mails：邮件内容 （内容相同，则复制给所有收件人 / 内容各异，则正常发送）
        """
        self.info_log("群发邮件及通知")
        receivers = data.get('receivers') or []
        mails = data.get('mails') or []

        if not receivers or not mails:
            return

        # 1.内容相同，复制给所有收件人
        if len(mails) == 1:
            single_mail = mails[0]
            mails = [{**single_mail, 'receiver': p} for p in receivers]

        # 2.创建邮件实例并插入数据库
        mails_tasks = []
        cur_time = tool_dt.cur_time()
        expired_sec = 30 * 86400  # 有效期
        for one_em in mails:
            new_mail = one_em.copy()
            new_mail['receiver'] = one_em['receiver']
            new_mail['receive_time'] = cur_time
            new_mail['exp_time'] = cur_time + expired_sec
            mails_tasks.append(Mails(**new_mail))

        await Mails.bulk_create(mails_tasks, batch_size=self.ONCE_OPERATION_LIMIT)

    async def season_settle_mails(self, _, data):
        """ 赛季结算奖励邮件  """
        cur_season_id = data.get("season_id")
        # 1.查询符合条件的玩家
        receive_users = await RecordsUserRankingHistory.filter(
            season=cur_season_id,
            season_achieved=False,
            game_count__gte=data.get("condition", 30)).all()

        # 2.获取每个玩家的赛季奖励
        _, ranking_data = await ConfRankingRC.get_season_awards_items(cur_season_id)
        if not ranking_data:
            return

        # 3.构建邮件数据
        mails = []
        rev_uid_list = []
        for u in receive_users:
            # 4.根据最高分来检查奖励
            top_score = u.top_score
            cur_ranking_data = ConfRankingRC.get_ranking_data_by_score(ranking_data, top_score)
            if cur_ranking_data:  # 检查是否有奖励，无奖不发
                ranking_name = cur_ranking_data.get('ranking_name', "")
                mail_data = {
                    'receiver': u.uid,
                    'mail_type': MailType.SEASON_SETTLE,
                    'title': f'S{cur_season_id}赛季结算奖励',
                    'content': f'恭喜你在S{cur_season_id}赛季中修为达到{ranking_name}境界，获得以下奖励：',
                    'attachment': cur_ranking_data.get('season_awards'),
                    'sender': "system"
                }
                mails.append(mail_data)
                rev_uid_list.append(u.uid)

        # 5.发送邮件并通知
        receiver = {'type': 'group', 'uid_list': rev_uid_list}
        await self.__manager_send_mails(_, {'receiver': receiver, 'mails': mails})

        # 6.更新历史表中当前赛季奖励状态为True
        await RecordsUserRankingHistory.filter(season_id=cur_season_id).update(season_achieved=True)

    async def __set_new_season(self, _, data):
        """ 设置新赛季 """
        season_desc = data.get("season_desc")
        off_season_time = data.get("off_season_time")
        condition = data.get("condition") or 30
        if not season_desc or not off_season_time:
            self.info_log("新赛季名称或休赛期时长不能为空！")
            return
        if not isinstance(off_season_time, int) or not isinstance(condition, int):
            self.info_log("场数限制或休赛期时长必须为整数！")
            return
        flag, msg = await ConfSeasonRC.add_season(**data)
        if not flag:
            return self.info_log(f"赛季添加失败：{msg}")
        self.info_log(f"赛季添加成功：{season_desc}")

    async def __ban_player(self, _, data):
        """ 封禁玩家 """
        uid = data.get("uid")
        ban_time = data.get("ban_time")
        if not isinstance(ban_time, int):
            return
        u_info = await BaseUserRC.cache_by_uid(uid)
        if not u_info:
            self.info_log("封禁玩家失败，没有玩家信息", uid)
            return
        await BaseUserRC.update_info(u_info, {"ban_time": ban_time})
        if ban_time == 0:
            self.info_log("解禁玩家完成：", uid)
            return
        self.info_log("封禁玩家：", uid)
        await self.inner_cs2ws(CmdWs.BAN_PLAYER, 1, data)

    async def __loop_game_announcement(self):
        """ 循环调用局内公告 """
        cs_type = random.choice(LEISURE_GAME_LIST)
        data_list = await LeisureConfRC.cache_all_by_cs_type(cs_type)
        data = random.choice(data_list)
        uid = random.randint(ROBOT_RANK[0], ROBOT_RANK[1])
        t1 = data.get("threshold_multiple") * data.get("base_score")
        t2 = t1 * 1.5
        total_score = random.randint(t1, t2)
        content = {
            "sentence_pattern": GameAnnouncement.rand_choice_member(),
            "uid": uid,
            "cs_type": cs_type,
            "level_desc": data.get("desc"),
            "win_gold": total_score
        }
        data = {
            "weight": WeightEnum.W1,
            "content": json_encode(content)
        }
        print("发送局内公告", tool_dt.cur_dt())
        data = {"ann_list": [data]}
        await self.__notify_announcement(1, data)

    async def __notify_announcement(self, uid, data):
        """ 通知公告 """
        ann_list = data.get("ann_list") or []
        if not ann_list:
            return
        pb_data = S2CTopAnnouncements.pb_model(ann_list)
        await self.notice_ws_by_rmq(CmdNotice.TOP_ANNOUNCEMENT, uid, msg=pb_data)

    async def __login_sign_in(self, uid, _):
        """登陆签到"""
        award_type = AwardType.SIGN_IN
        today_time_node = KitDt.timestamp_today()

        # 1.检查是否完成签到
        task_info = await UserTaskRC.cache_task_record_by_id(uid, TaskId.ROOKIE_SEVEN_SIGN_IN.val)
        if task_info.get('task_sta') == CompleteSta.COMPLETED and task_info.get('cur_value', 0) >= 7:
            self.info_log(uid, "七日签到已完成")
            return

        # 2.检查今天签到情况
        query_params = {"uid": uid, "award_type": award_type}
        sign_info = await UserBehaviorsRC.get_sign_in_records(uid, award_type) or {}
        sign_in_date, sign_in_achieved = UserBehaviorsRC.parse_sign_in_info(sign_info)

        if len(sign_in_achieved) >= 7:
            self.info_log(uid, f"七日签到奖励已领完 {sign_in_achieved}")
            return
        if today_time_node in sign_in_date:
            self.info_log(uid, f"今天的签到已完成 {today_time_node}")
            return

        # 3.签到
        sign_in_date.append(today_time_node)
        new_sign_info = {
            "uid": uid,
            "time_node": today_time_node,
            "award_type": award_type,
            "sign_in_date": json_encode(sign_in_date) if sign_in_date else '[]'
        }
        self.info_log(uid, f"进行登陆签到 {today_time_node}")
        await UserBehaviorsRC.update_user_sign_in_records(query_params, new_sign_info, sign_info)

    @staticmethod
    def task_h_key(uid, start_time):
        return f'{uid}_{start_time}'

    async def save_date_task(self, uid, start_time, data):
        """ 保存data task """
        h_key = self.task_h_key(uid, start_time)
        start_time = data.get('start_time')
        ex_time = start_time - tool_dt.cur_time()
        if ex_time > 0:
            await self.conf.rds.set_hash(self.TASK_DATE_KEY, h_key, data)

    async def __get_date_task_exec(self):
        """ 获取所有date task并执行 """
        all_hash = await self.conf.rds.get_hash_all(self.TASK_DATE_KEY, jsparse=True)
        if not all_hash:
            return
        cur_time = tool_dt.cur_time()
        for h_key, data in all_hash.items():
            uid, start_time = h_key.split('_')
            uid, start_time = int(uid) if uid.isdigit() else uid, int(start_time)
            if start_time > cur_time:
                await self.__background_scheduled_task(uid, data)
            else:
                await self.conf.rds.drop_hash(self.TASK_DATE_KEY, h_key)

    async def __background_scheduled_task(self, _, data):
        cmd = data.get('cmd', None)
        func = self.cmd2func.get(cmd)
        self.info_log("后台新增定时任务", cmd)
        if not func:
            return
        kwargs = {
            "cmd": cmd,
            "start_time": data.get('start_time') or 0,
            "name": data['task_name'],
        }
        job_id = await self.__timed_server.add_appointed_time_job(func, args=(_, data), kwargs=kwargs)
        if job_id and cmd == CmdWorkers.MANAGER_SEND_MAILS:
            await RecordsAdminMailsRC.update_info(data.get("m_id"), {"job_id": job_id})

    async def __cancel_background_scheduled_task(self, _, data):
        """ 取消后台定时任务 """
        start_time = data.get("start_time")
        job_id = data.get("job_id")
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                await RecordsAdminTimedTask.update_by_pk(job_id, {"status": BackTaskSta.CANCELED.val})
                await RecordsAdminMailsRC.cancel_mail(job_id)

            self.__timed_server.scheduler.rm_job(job_id)
            h_key = self.task_h_key(_, start_time)
            await self.conf.rds.drop_hash(self.TASK_DATE_KEY, h_key)
        except Exception as e:
            self.error_log(f"取消后台定时任务 事务执行失败，原因：{e}")

        self.info_log("取消后台定时任务！")

    async def __fetch_active_mails(self, uid, _):
        mails_list = await RecordsAdminMailsRC.get_active_mails()
        for mail in mails_list:
            mails_data = {
                "mails": [
                    {
                        'mail_type': mail.get("mail_type"),
                        'title': mail.get("title"),
                        'content': mail.get("content"),
                        'attachment': mail.get("attachment"),
                        'sender': mail.get("sender"),
                    }
                ],
                "receiver": {"type": "group", "uid_list": [uid]},
            }
            await self.__manager_send_mails(uid, mails_data)
            await asyncio.sleep(0.01)

    async def start_server(self):
        """ 重写启动服务 """
        if self.server_id == 1:
            print("启动定时服务>>>")
            from .timed_service import TimedService
            self.__timed_server = TimedService(self.conf, self)
            try:
                self.__timed_server.start()
                await super().start_server()
            except asyncio.CancelledError:
                pass
            finally:
                self.__timed_server.close()  # 关闭scheduler
            return
        await super().start_server()

    async def __user_event_tracking(self, uid, data):
        """ 用户事件追踪 """
        self.info_log("用户事件追踪:", uid, data)
        event_tracking = data.get('event_tracking')
        et_enum = EventTracking.find_member_by_val(event_tracking)
        if not isinstance(et_enum, EventTracking):
            return

        # 检查注册记录是否存在
        if event_tracking != EventTracking.AFTER_REGISTER.val:
            reg_record = await RecordsUserEvent.get_by_dict(
                {"uid": uid, "event_tracking": EventTracking.AFTER_REGISTER.val}, limit=1
            )
            if not reg_record:
                self.info_log(f"用户 {uid} 属于老用户暂不统计")
                return
        # 首次对局判断
        if event_tracking == EventTracking.AFTER_FIRST_GAME.val:
            game_record = await RecordsGameGrade.get_by_dict({"uid": uid}, limit=1)
            if game_record:
                self.info_log(f"用户 {uid} 非首次对局")
                return
        # 首次付费判断
        elif event_tracking == EventTracking.AFTER_FIRST_PAY.val:
            pay_record = await RecordsTradeOrder.get_by_dict(
                {"uid": uid, "order_status": OrderStatus.PAID.val}, limit=1)
            if pay_record:
                self.info_log(f"用户 {uid} 非首次付费")
                return

        async with in_transaction(connection_name=DbKey.DEFAULT):
            # 插入当前事件
            await RecordsUserEvent.split_add_one({
                "uid": uid,
                "event_tracking": event_tracking,
                "event_desc": et_enum.phrase,
                "event_time": tool_dt.cur_time()
            })

            # 检查并补充注册记录
            # reg_record = await RecordsUserEvent.get_by_dict(
            #     {"uid": uid, "event_tracking": EventTracking.AFTER_REGISTER.val}, limit=1)
            # if not reg_record:
            #     u_info = await BaseUserRC.cache_by_uid(uid)
            #     if u_info:
            #         await RecordsUserEvent.split_add_one({
            #             "uid": uid,
            #             "event_tracking": EventTracking.AFTER_REGISTER.val,
            #             "event_desc": EventTracking.AFTER_REGISTER.phrase,
            #             "event_time": u_info.get('created')
            #         })
            #         self.info_log(f"为用户 {uid} 补充注册记录")
            #     else:
            #         self.error_log(f"用户 {uid} 未注册，且未找到user表记录")
