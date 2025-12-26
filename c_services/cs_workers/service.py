import asyncio
import random
from nsanic.libs import tool_dt
from nsanic.libs.tool import json_encode
from tortoise.transactions import in_transaction
from c_services.base.base_server import JsonBaseServer
from c_services.const.cs_enum_const import CmdWorkers, CmdNotice, RedDotType, CmdWs, GameAnnouncement
from common.model_rc.tournament_cycle_leaderboard import TournamentCycleLeaderboardRC
from common.model_rc.tournament_user_point import TournamentUserPointRC
from common.proto.py_pb2.common import common_pb2
from common.proto.py_pb2.ws_leisure import S2CTopAnnouncements
from common.public.conf import ROBOT_RANK
from common.public.enum_const import DbKey, LEISURE_GAME_LIST, ServiceEnum
from common.utils.kit_async import DelayCall
from common.utils.kit_dt import KitDt
from lucky_admin.const import BackTaskSta, WeightEnum
from lucky_game.model_db.main import RecordsAdminTimedTask
from lucky_admin.model_rc.mails_manage import RecordsAdminMailsRC
from lucky_game.model_rc.active_behaviors import UserBehaviorsRC
from lucky_game.model_rc.base_activity import UserActivityRC
from lucky_game.model_rc.base_bag import UserBagRC
# from lucky_game.model_rc.base_game_task import UserTaskRC, ConfTaskRC
from lucky_game.model_rc.base_interaction import InteractionRC
from lucky_game.model_rc.base_mails import MailsRC
# from lucky_game.model_rc.base_safe_box import UserSafeBoxRC
# from lucky_game.model_rc.base_skin import UserSkinRC, ItemsSkinRC
from lucky_game.model_rc.base_store import StoreRC
from lucky_game.model_rc.base_user import BaseUserRC
# from lucky_game.model_rc.base_cosmetic import UserCosmeticRC, ItemsCosmeticRC
from lucky_game.model_rc.conf_leisure import LeisureConfRC
from lucky_game.model_rc.vip_level import UserVipRC, ConfVipRC
from lucky_game.model_rc.player_game_times import PlayerGameTimesRC
from lucky_game.model_db.extra import RecordsGameGrade, RecordsUserEvent
# from lucky_game.model_rc.base_ranking import UserRankingRC, ConfRankingRC, ConfSeasonRC
from lucky_game.model_db.main import Mails, Orders
from lucky_game.const import ActivityItem, GoodsItem, StoreItem, TaskType, AwardType, MailType, ActivityType, \
    CompleteSta, EventTracking, OrderStatus, GoodsSku
from lucky_game.logic.activity import act_count, Base, Package, FirstCharge, InfinitePlay
from lucky_game.model_rc.base_activity import ConfActivityRC
from lucky_game.model_rc.user_activity import AwardGainsRC
from lucky_game.model_rc.club_users import ClubUsersRC
from lucky_game.model_rc.extra_club_behavior import ExtraClubBehaviorRC
from lucky_game.model_rc.conf_json import ConfJsonRC
from lucky_game.logic.payment import PaymentLogic
from common.utils.utils import UtilsTool
from lucky_game.model_rc.records_game_room import RecordsGameRoomRC
from lucky_game.model_rc.records_game_segment import RecordsGameSegmentRC
from lucky_game.model_rc.records_game_total import RecordsGameTotalRC




class WorkersServer(JsonBaseServer):
    """
    工人服务：专门用于不停地消费异步任务调度，如游戏内的数据库操作等可以发往该服务进行消费
    该服务可开启多个实例：rmq内部会负载均衡
    """
    ONCE_OPERATION_LIMIT = 1000  # 单次操作上限
    TASK_DATE_KEY = 'task_date'
    delay_fail = 2
    SUBSCRIBE_FANOUT = None

    def __init__(self):
        super().__init__()
        self.__timed_server = None
        self.add_handlers({
            CmdWorkers.MANAGER_SEND_MAILS: self.__manager_send_mails,
            CmdWorkers.GET_RED_DOT_LIST: self.__get_red_dot_by_list,
            CmdWorkers.UPDATE_USER_VIP_LEVEL: self.__update_user_vip_level,
            CmdWorkers.UPDATE_ITEM_ORDER_COUNT: self.__update_item_order_count,
            CmdWorkers.BAN_PLAYER: self.__ban_player,
            CmdWorkers.NOTIFY_ANNOUNCEMENT: self.__notify_announcement,
            CmdWorkers.INSERT_GAME_GRADE: self.__insert_game_grade,
            CmdWorkers.UPDATE_GAME_RECORD_TIMES: self.__update_game_record_times,
            CmdWorkers.INSERT_GAME_RECORD_TOTAL: self.__insert_game_record_total,
            CmdWorkers.UPDATE_CYCLE_POINT_LEADERBOARD: self.__update_tournament_cycle_leaderboard,
            CmdWorkers.UPDATE_COMPETITION_RESULT: self.__update_competition_result,
        })
        self.__user_query_red_dot_func_map = {}  # 记录用户查询红点任务

        # DelayCall(1, self.__get_date_task_exec).start()
        # DelayCall(1, self.__rand_loop_game_announcement).start()

    async def __rand_loop_game_announcement(self):
        while 1:
            await asyncio.sleep(random.randint(60, 90))
            await self.__loop_game_announcement()

    @classmethod
    def red_dot_log(cls, *data):
        cls.log_info("红点任务：", *data)

    async def __update_game_times(self, uid, data):
        """ 更新游戏次数 """
        data.update({"uid": uid})
        res = await PlayerGameTimesRC.update_game_times(data)
        self.log_info(uid, "更新玩家次数", res)



    async def __update_user_vip_level(self, uid, data):
        """ 更新VIP经验值 """
        self.log_info(uid, "更新VIP经验值", data)
        _, up_flag = await UserVipRC.update_user_vip_level(uid, amount=data.get("amount"))
        if up_flag:
            await self.__notice_by_vip(uid, up_flag)
            # await self.__process_safe_box(uid, _)
            await self.__user_event_tracking(uid, {'event_tracking': EventTracking.AFTER_FIRST_PAY.val})




    async def __new_user_give_gift(self, uid, data):
        """ 新用户赠送礼物 """
        self.log_info(uid, "新用户赠送礼物", data)

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
        self.log_info(uid, "批量获取红点>>>", rd_type_list)
        get_red_dots = self.__get_red_dot_tasks(uid, rd_type_list)
        get_red_dots and await asyncio.gather(*get_red_dots)

    def __get_red_dot_tasks(self, uid, rd_type_list):
        """根据红点类型生成任务列表"""
        map_func = {
            # 每日免费抽奖签到
            RedDotType.RD_SIGN_IN_RF.val: self.__login_sign_in,
            # 每月累计签到奖励
            RedDotType.RD_SIGN_IN.val: self.__notice_by_sign_in_by_month,
            # 每日商店免费金币
            RedDotType.RD_STORE.val: self.__notice_by_store,
            # 未读邮件
            RedDotType.RD_MAILS.val: self.__notice_by_mails,
            # 首次充值
            RedDotType.RD_FIRST_CHARGE.val: self.__notice_by_first_charge,
            # 救济金
            RedDotType.RD_RELIEF.val: self.__notice_by_relief,
            # 分享
            RedDotType.RD_SHARE.val: self.__notice_by_share,
            # 限时登录
            RedDotType.RD_LIMIT_LOGIN.val: self.__notice_by_limit_login,
            # 茶馆申请、审批
            RedDotType.RD_CLUB_APPLY.val: self.__notice_by_club_apply,
            # 茶馆用户变动
            RedDotType.RD_CLUB_USER_LIST.val: self.__notice_by_club_user_list,
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


    async def __notice_by_sign_in_by_month(self, uid):
        """每月累计签到奖励红点"""
        u_info = await BaseUserRC.cache_by_uid(uid)
        act, _ = await ConfActivityRC.get_activity_by_once(act_type=ActivityType.LUCK_SIGN_IN, platform=u_info.get("platform"))
        start, end = await self.get_time_range(period="month")
        sta, gains = await AwardGainsRC.get_award_gains(uid, act_id=act.get("act_id", 0), status=0, start_time=start, end_time=end, count=True)
        self.red_dot_log(uid, "每月累计签到奖励红点查询", sta and gains > 0)
        if sta and gains > 0:
            await self.__notify_red_dot(uid, RedDotType.RD_SIGN_IN)

    async def __notice_by_sign_in_by_week(self, uid):
        """每周七日签到红点"""
        sta = await UserBehaviorsRC.get_sign_in_unclaimed(uid, AwardType.SIGN_IN_WK)
        self.red_dot_log(uid, "每周七日签到红点查询", sta)
        if sta:
            await self.__notify_red_dot(uid, RedDotType.RD_SIGN_IN_WK)

    async def __notice_by_store(self, uid):
        """游戏商店红点"""
        count = await PaymentLogic().buy_count(uid, GoodsSku.SKU_FREE, period="day")
        self.red_dot_log(uid, "游戏商店红点查询", not count)
        if not count:
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

#     async def __notice_by_week_card(self, uid):
        """周卡红点"""
        w_cards = (ActivityItem.WEEK_CARD_2.val, ActivityItem.WEEK_CARD_1.val)
        sta = await UserActivityRC.get_activity_unclaimed(uid, w_cards)
        self.red_dot_log(uid, "周卡红点查询", sta)
        if sta:
            await self.__notify_red_dot(uid, RedDotType.RD_WEEK_CARD)

    async def __notice_by_first_charge(self, uid):
        """首充红点"""
        total = await FirstCharge().pay_count(uid)
        self.red_dot_log(uid, "首充红点查询", not total)
        if not total:
            await self.__notify_red_dot(uid, RedDotType.RD_FIRST_CHARGE)

    async def __notice_by_relief(self, uid):
        """救济红点"""
        u_info = await BaseUserRC.cache_by_uid(uid)
        conf_data = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_RELIEF)
        if u_info.get("gold", 0) < conf_data.get("min_gold"):
            act, _ = await ConfActivityRC.get_activity_by_once(act_type=ActivityType.INFINITE_PLAY)
            sta, msg, progress, _ = await Base().act_progress(act, u_info)
            status = -1
            if sta:
                result = await InfinitePlay().progress_data(act, progress, u_info)
                status = result.get("gains")[0].get("status")
            result = status == 0
            self.red_dot_log(uid, "救济金红点查询", result)
            if result:
                await self.__notify_red_dot(uid, RedDotType.RD_RELIEF)

    async def __notice_by_share(self, uid):
        """分享红点"""
        act, _ = await ConfActivityRC.get_activity_by_once(act_type=ActivityType.SHARE)
        sta, count = await act_count(uid, act.get("act_id", 0), "day")
        if count > 0:
            self.log_info(uid, "今天已完成分享")
            return
        else:
            await self.__notify_red_dot(uid, RedDotType.RD_SHARE)

    async def __notice_by_limit_login(self, uid):
        """ 限时登录红点 """
        package = Package()
        u_info = await BaseUserRC.cache_by_uid(uid)
        platform = u_info.get("platform")
        act, _ = await ConfActivityRC.get_activity_by_once(act_type=ActivityType.PACKAGE, platform=platform)
        now_award_id = await package.now_award_id(platform)
        if now_award_id:
            progress = await package.get_progress(now_award_id, uid, act)
            sta = progress["status"] == 0
            self.log_info(uid, "限时登录红点查询", sta)
            if sta:
                await self.__notify_red_dot(uid, RedDotType.RD_LIMIT_LOGIN)

    async def __notice_by_club_user_list(self, uid):
        """ 茶馆用户变动红点 """
        pass

    async def __notice_by_club_apply(self, uid):
        """ 茶馆申请变动红点 """
        club_ids, e = await ClubUsersRC.get_club_user_by_uid_club_ids(uid, in_role=[1, 9])
        if club_ids:
            data, e = await ExtraClubBehaviorRC.get_behavior_by_filter(
                type=ExtraClubBehaviorRC.BEHAVIOR_APPLY_INDEX,
                club_id=club_ids,
                status=ExtraClubBehaviorRC.BEHAVIOR_STATUS_DEFAULT
            )
            if data:
                await self.__notify_red_dot(uid, RedDotType.RD_CLUB_APPLY)

    async def __notice_by_bag(self, uid):
        """背包红点"""
        sta = await BaseUserRC.deal_user_update_goods(uid, key_name=UserBagRC.KEY_NEWLY)
        self.red_dot_log(uid, "背包红点查询", sta)
        if sta:
            await self.__notify_red_dot(uid, RedDotType.RD_BAG)



    async def __update_item_order_count(self, uid, data):
        """ 更新玩家完成订单数 """
        res = await UserBehaviorsRC.update_user_order_count(uid, data)
        self.log_info(uid, "更新玩家完成订单数", True if res else False)

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
        self.log_info(uid, "更新背包物品", data)

    async def __check_limited_goods(self, uid, data):
        """检查限时物品"""
        # 法相
        # sta = await UserSkinRC.deal_expire_skin(uid, data.get('cs_type'))
        self.log_info(uid, "检查限时物品")

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
        self.log_info("群发邮件及通知")
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


    async def __ban_player(self, _, data):
        """ 封禁玩家 """
        uid = data.get("uid")
        ban_time = data.get("ban_time")
        if not isinstance(ban_time, int):
            return
        u_info = await BaseUserRC.cache_by_uid(uid)
        if not u_info:
            self.log_info("封禁玩家失败，没有玩家信息", uid)
            return
        await BaseUserRC.update_info(u_info, {"ban_time": ban_time})
        if ban_time == 0:
            self.log_info("解禁玩家完成：", uid)
            return
        self.log_info("封禁玩家：", uid)
        await self.inner_cs2ws(ServiceEnum.WS_HALL, CmdWs.BAN_PLAYER, 1, data)

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

    async def __insert_game_grade(self, uid, data):
        replay_msg_data = data.get("replay_msg_data")
        tid = data.get("tid")
        for replay_msg in replay_msg_data:
            msg = replay_msg.get("replay_msg")
            for i, m in enumerate(msg):
                msg[i] = UtilsTool.base64_to_bytes(m,log_fun = self.log_info)
        result_data = await RecordsGameSegmentRC.bulk_create_record_game_segment(replay_msg_data)
        self.log_info(tid,"游戏结束一轮结束战绩插入", result_data)



    async def __update_game_record_times(self, uid, data):
        """ 更新游戏战绩次数 """
        tid = data.get("tid")
        await self.conf.locker.locked(tid,self.update_record_times,(uid,data))

    async def update_record_times(self,uid,data):
        round_idx = data.get("round_idx")
        record_id = data.get("record_id")
        tid = data.get("tid")
        is_all = data.get("is_all")
        if not is_all:
            round_msg_records = data.get("round_msg_records")
            for i, m in enumerate(round_msg_records):
                round_msg_records[i] = UtilsTool.base64_to_bytes(m, log_fun=self.log_info)
            up_segment_sta, e = await RecordsGameSegmentRC.update_record_game_segment(record_id, uid, replay_msg=round_msg_records,
                                                                  round_num=round_idx)
            self.log_info(tid, "玩家", uid, "战绩更新结果", e)

        else:
            is_dismiss = data.get("is_dismiss")
            record_data_list =data.get("record_data_list")
            for record_data in record_data_list:
                final_grade = record_data.get("final_grade")
                final_ranking = record_data.get("final_ranking")
                num = record_data.get("num")
                room_status = record_data.get("room_status") or None
                total_score = record_data.get("total_score")
                game_over_data = record_data.get("game_over_data")
                tid = record_data.get("tid")
                uid = record_data.get("uid")
                up_result = await RecordsGameTotalRC.create_record_game_total(record_id, uid, total_score >= 0, total_score
                                                                              , final_ranking, final_grade, game_over_data, num,
                                                                              room_status)
                self.log_info(tid, "插入游戏战绩总分结果", up_result)
            if is_dismiss:
                up_room_sta, up_result = await RecordsGameRoomRC.update_record_game_room(record_id, round_num=round_idx)
                self.log_info(tid, "玩家", uid, "战绩更新结果", data)
                self.log_info(tid,"更新所有战绩结果", up_result)

    async def __insert_game_record_total(self,uid,data):
        """ 插入游戏战绩总分 """
        record_id = data.get("record_id")
        final_grade = data.get("final_grade")
        final_ranking = data.get("final_ranking")
        num = data.get("num")
        room_status = data.get("room_status") or None
        total_score = data.get("total_score")
        game_over_data = data.get("game_over_data")
        tid = data.get("tid")
        up_result = await RecordsGameTotalRC.create_record_game_total(record_id, uid, total_score >= 0, total_score
                                                                        , final_ranking, final_grade, game_over_data, num, room_status)
        self.log_info(tid,"插入游戏战绩总分结果", up_result)

    async def __login_sign_in(self, uid):
        """登陆签到"""
        # 1.检查是否完成签到
        u_info = await BaseUserRC.cache_by_uid(uid)
        act, _ = await ConfActivityRC.get_activity_by_once(act_type=ActivityType.LUCK_SIGN_IN, platform=u_info.get("platform"))
        sta, count = await act_count(uid, act.get("act_id", 0), "day")
        if count > 0:
            self.log_info(uid, "今天的签到已完成")
            return
        else:
            await self.__notify_red_dot(uid, RedDotType.RD_SIGN_IN_RF)


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
        self.log_info("后台新增定时任务", cmd)
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

#     async def __cancel_background_scheduled_task(self, _, data):
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
            self.log_err(f"取消后台定时任务 事务执行失败，原因：{e}")

        self.log_info("取消后台定时任务！")

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
        self.log_info("用户事件追踪:", uid, data)
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
                self.log_info(f"用户 {uid} 属于老用户暂不统计")
                return
        # 首次对局判断
        if event_tracking == EventTracking.AFTER_FIRST_GAME.val:
            game_record = await RecordsGameGrade.get_by_dict({"uid": uid}, limit=1)
            if game_record:
                self.log_info(f"用户 {uid} 非首次对局")
                return
        # 首次付费判断
        elif event_tracking == EventTracking.AFTER_FIRST_PAY.val:
            pay_record = await Orders.get_by_dict(
                {"uid": uid, "order_status": OrderStatus.PAID.val}, limit=1)
            if pay_record:
                self.log_info(f"用户 {uid} 非首次付费")
                return

        async with in_transaction(connection_name=DbKey.DEFAULT):
            # 插入当前事件
            await RecordsUserEvent.split_add_one({
                "uid": uid,
                "event_tracking": event_tracking,
                "event_desc": et_enum.phrase,
                "event_time": tool_dt.cur_time()
            })


    async def __update_tournament_cycle_leaderboard(self, uid, data):
        total_points = data.get("total_points")
        uid = data.get("uid")
        cycle_id = data.get("cycle_id")
        has, leaderboard_data = await TournamentCycleLeaderboardRC.get_uid_leaderboard(cycle_id, uid)
        if not has:
            sta, _ = await TournamentCycleLeaderboardRC.add_leaderboard(cycle_id, uid, total_points)
        else:
            up_data = {
                "total_points": total_points + leaderboard_data.get("total_points"),
                "participated_rounds": 1 + leaderboard_data.get("participated_rounds"),
            }
            sta, _ = await TournamentCycleLeaderboardRC.update_leaderboard(leaderboard_data.get("id"), up_data)
        self.log_info(f"赛季单场次结束排行榜更新：{sta}")

    async def __update_competition_result(self,uid,data):
        cycle_id = data.get("cycle_id")
        up_data = data.get("up_data")
        sta,result = await TournamentUserPointRC.up_user_point(cycle_id, uid, up_data)
        self.log_info(f"更新比赛结果：{sta} 玩家{uid}")
