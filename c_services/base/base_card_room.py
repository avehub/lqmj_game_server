from nsanic.libs.tool import json_encode
from nsanic.libs import tool_dt
from c_services.base.base_room import BaseRoom
from c_services.const.cs_enum_const import RoomStatus, CmdRoom, CmdWorkers, GameAnnouncement, CmdClub, ClubMsgType
from c_services.cs_mahjong.const import OverType, PlayType, EXTRA_SCORE_MAP, ExtraHuPai, CheckType, PAI_XING_SCORE_MAP, HuType, FlowStatus, \
    JI_PAI_SCORE, CardsType, JiType
from common.proto.py_pb2.ws_base import PbWsBaseRep
from common.proto.py_pb2.ws_leisure import S2CDealCards, s2c_tickets_model, S2CBrokeBroad, \
    s2c_trustee_model, s2c_gold_model, s2c_one_of_model, s2c_recharge_model, S2CGameOverInfo, S2CRoundOverInfo
from common.public.conf import LIVE_SERVER, C_SERVICE_SECRET_KEY
from common.public.enum_const import TaskId, StaCode, ServiceEnum
from common.utils.kit_async import DelayCall
from common.utils.utils import UtilsTool
from lucky_admin.const import WeightEnum
from lucky_game.const import ReasonCostGold, SeasonStatus, GiftType
from lucky_game.model_rc.game_rooms import GameRoomsRC
from lucky_game.model_rc.records_game_room import RecordsGameRoomRC
from lucky_game.model_rc.records_game_segment import RecordsGameSegmentRC
from lucky_game.model_rc.records_game_total import RecordsGameTotalRC


# from lucky_game.model_rc.base_activity import ConfActivityRC


class BaseCardRoom(BaseRoom):

    def __init__(self, tid, service, room_conf, poker, not_include=0):
        rule_details = room_conf.pop("rule_details")
        print("rule_details", rule_details)
        room_conf.update(rule_details)
        super().__init__(tid, service, room_conf, poker, not_include)
        self.__rule_details = rule_details
        self.__in_stop = False
        self.__club_id = room_conf.get("club_id") or 0
        self.__owner = room_conf.get("creator") or 0
        self.__create_time = room_conf.get("create_time") or tool_dt.cur_time()
        self.__cur_round = room_conf.get("cur_round") or 1
        self.__timeout_idle_time = 60 * 60 * 30
        self.__timer_dismiss = None
        self.__round_msg_records = []
        self.__winner_list = []
        self.__agree_dismiss_seats = set()
        self.__extra_score_map = self.get_extra_score_map()
        self.__pai_xing_score_map = self.get_pai_xing_score_map()
        self.__record_id = 1
        self.__last_round_result = {}
        self.__not_playing_room_status = RoomStatus.T_IDLE
        self.__not_playing_dismiss = False
        self.__deal_cards_count = 13
        if self.play_type == PlayType.BI_JIE_MJ:
            self.__deal_cards_count = 10
        else:
            self.__deal_cards_count = 13

    @property
    def extra_score_map(self):
        return self.__extra_score_map

    @property
    def pai_xing_score_map(self):
        return self.__pai_xing_score_map

    @property
    def record_id(self):
        return self.__record_id

    @property
    def not_playing_room_status(self):
        return self.__not_playing_room_status

    @property
    def not_playing_dismiss(self):
        return self.__not_playing_dismiss

    @property
    def deal_cards_count(self):
        return self.__deal_cards_count

    def set_not_playing_dismiss(self, status, value):
        self.__not_playing_room_status = status
        self.__not_playing_dismiss = value

    def back_room_status(self):
        print("返回房间状态", self.__not_playing_dismiss, self.__not_playing_room_status)
        if self.__not_playing_dismiss:
            self.async_set_room_status(self.__not_playing_room_status)
            self.__not_playing_dismiss = False
            self.__not_playing_room_status = RoomStatus.T_IDLE

    async def close_room_time_out(self):
        if self.game_began:
            return
        if tool_dt.cur_time() - self.__create_time < self.__timeout_idle_time:
            return
        if self.in_room_count > 0:
            self.__timeout_idle_time += 300
            return
        await self.force_dismiss()

    @property
    def timer_dismiss(self):
        return self.__timer_dismiss

    def call_dismiss(self, seconds, func, *params, **kwargs):
        self.cancel_timer_dismiss()
        self.__timer_dismiss = DelayCall(seconds, func, *params, **kwargs)
        self.__timer_dismiss.start()
        self.log_info("启动倒计时解散房间", seconds)

    def cancel_timer_dismiss(self):
        if self.__timer_dismiss:
            self.__timer_dismiss.cancel()
            self.__timer_dismiss = None

    @property
    def agree_dismiss_seats(self):
        return self.__agree_dismiss_seats

    def agree_dismiss_count(self):
        return len(self.__agree_dismiss_seats)

    def add_agree_dismiss(self, seat_id):
        self.__agree_dismiss_seats.add(seat_id)

    def clear_agree_dismiss(self):
        self.cancel_timer_dismiss()
        return self.__agree_dismiss_seats.clear()

    async def player_join_room(self, players: list):
        await super(BaseCardRoom, self).player_join_room(players)
        if self.club_id > 0:
            print("玩家进入房间，通知茶馆创建房间")
            await self.cs2club_by_rmq(CmdClub.ROOM_INFO_CHANGE, self.club_room_info(ClubMsgType.ENTER_ROOM))  # 通知茶馆创建房间

    async def player_quit_room(self, player, data):
        self.log_info("请求退出房间:uid", player.uid, "game_began:", self.game_began(), "owner:", self.owner, "tid:", self.tid)
        if not self.game_began():
            if self.owner == player.uid:
                if self.in_room_count == 1:
                    self.__not_playing_dismiss = True
                    return await self.force_dismiss()
                await self.inner_send(player, CmdRoom.QUIT_ROOM, None, StaCode.FAIL, "房主不能退出")
                return
            one_of_model = s2c_one_of_model()
            one_of_model.seat_id = player.seat_id
            await self.inner_broadcast(CmdRoom.QUIT_ROOM, one_of_model)
            await GameRoomsRC.leave_room(self.tid, player.uid)
            self.seats[player.seat_id - 1] = None
            await self.service.del_player_in_service(player.uid)  # 释放玩家放在下面，因为下面会清理玩家数据
            self.service.release_player(player)
            if self.club_id > 0:
                await self.cs2club_by_rmq(CmdClub.ROOM_INFO_CHANGE, self.club_room_info(ClubMsgType.QUIT_ROOM))  # 通知茶馆创建房间
        super(BaseCardRoom, self).player_quit_room(player, data)

    def game_began(self):
        return self.round_idx != 1 or self.room_status != RoomStatus.T_IDLE

    async def round_start(self):
        self.clear_room_round_start()
        await super().round_start()

    async def start_next_round(self):
        """ 开始下一局 """
        self.incr_round_count()
        await self.async_set_room_status(RoomStatus.T_IDLE)

    def clear_room_round_start(self):
        """ 小局开始清理 """
        self.__round_msg_records = []
        self.__add_room_info_msg()
        self.__add_player_info_msg()

    def __add_pack_msg_records(self, cmd, data, code=StaCode.PASS, hint=''):
        cmd = UtilsTool.packet_command(self.service.service_type, cmd)
        data_msg = PbWsBaseRep.encode(code, hint, data)
        message = UtilsTool.pack_msg_by_bytes(self.service.service_type, cmd, data_msg)
        self.__round_msg_records.append(message)

    def __add_round_log(self, cmd, data, code, hint):
        """ 对局日志 """
        # 首局并且空闲不记录
        if not self.game_began:
            return
        if isinstance(data, dict):
            data.pop("legal_actions", None)
        self.__add_pack_msg_records(cmd, data, code, hint)

    def __add_room_info_msg(self):
        """ 获取房间信息 """
        self.__add_pack_msg_records(CmdRoom.ROOM_INFO, self.serialize_room_info())

    def __add_player_info_msg(self):
        """ 获取玩家信息 """
        self.__add_pack_msg_records(CmdRoom.PLAYER_INFO, self.serialize_player_info(self.room_player_info()))

    async def inner_send(self, p, c_code, data=None, code: StaCode = StaCode.PASS, hint='', req_id="", record_round_log=True):
        await super().inner_send(p, c_code, data, code, hint, req_id)
        if record_round_log:
            self.__add_round_log(c_code, data, code, hint)

    async def inner_broadcast(self, c_code, data=None, code: StaCode = StaCode.PASS, hint='', exclude_uid=0, record_round_log=True):
        await super().inner_broadcast(c_code, data, code, hint, exclude_uid)
        if record_round_log:
            self.__add_round_log(c_code, data, code, hint)

    @property
    def rule_detail(self):
        return self.__rule_details

    @property
    def ready_player_count(self):  # 统计当前已准备的玩家数
        count = 0
        for p in self.seats:
            if p and p.is_ready:
                count += 1
        return count

    @property
    def get_owner_is_ready(self):
        is_ready = False
        for p in self.seats:
            if p and p.uid == self.__owner and p.is_ready:
                is_ready = True
                break
        return is_ready

    @property
    def owner(self):
        return self.__owner

    @property
    def club_id(self):
        return self.__club_id

    async def do_trustee(self, player):
        is_trustee = False if player.trustee else True
        player.trustee = is_trustee
        tm = s2c_trustee_model(player.seat_id, is_trustee)
        await self.inner_broadcast(CmdRoom.TRUSTEE, tm)

    async def try_round_start(self):
        pass

    @staticmethod
    def get_player_info(player):
        """ 子类实现 """

    async def play_card_by_rand(self, player):
        """ 随机出牌 """

    async def round_over(self, over_type, **kwargs):
        print("进入round_over")
        self.set_flow_status(FlowStatus.T_IN_CHECK_OUT)
        await self.async_set_room_status(RoomStatus.T_CHECK_OUT)
        account = kwargs.pop("account")
        data = kwargs

        new_data = []
        is_round_over = True if over_type != OverType.FORCE else False
        score_rank_map = self.get_player_ranking(account, is_round_over)
        for p in self.seats:
            if not p:
                continue
            record_data = {
                "record_rid": self.__record_id,
                "record_tid": 0,
                "cs_type": self.service.service_type,
                "round_num": self.round_idx,
                "replay_msg": self.__round_msg_records,
            }
            player_account = account.get(p.seat_id, {})
            score = player_account.get("total_score", 0)
            p.on_round_over(score)
            over_data = p.round_over_data()
            over_data["account"] = player_account if player_account else None
            data["seats"].append(over_data)
            record_data["uid"] = p.uid
            record_data["round_status"] = 1 if score >= 0 else 0
            record_data["round_score"] = score
            record_data["round_ranking"] = score_rank_map[p.round_score] if score_rank_map else 0
            record_data["round_result"] = over_data
            new_data.append(record_data)
            p.clear_data_round_over()

        self.log_info( "round_index:", self.round_idx, "结算：", data)
        if over_type != OverType.FORCE:
            result_data = await RecordsGameSegmentRC.bulk_create_record_game_segment(new_data)
            self.log_info("一轮结束战绩插入", result_data)
            data_model = S2CRoundOverInfo.pb_model(**data)
            await self.inner_broadcast(CmdRoom.ROUND_OVER, data_model)

        if not self.has_next_round() or over_type == OverType.FORCE:
            return await self.game_over(over_type)
        else:
            await self.next_round_ready()

    async def next_round_ready(self):
        await self.start_next_round()
        for p in self.seats:
            p.is_ready = False
        await self.try_start_game()

    async def try_start_game(self):
        if await self.check_game_start():
            return
        return await self.check_round_start()

    async def check_round_start(self):
        """ 检查下一局是否要开始了 """
        print("进入check_round_start")
        if not self.room_status_is_equal(RoomStatus.T_CHECK_OUT):
            return False
        if self.in_room_count != self.max_player_count:
            return False
        if self.ready_player_count != self.max_player_count:
            return False
        await self.async_set_room_status(RoomStatus.T_PLAYING)
        await self.round_start()
        return True

    async def check_game_start(self, force=False):
        if not self.room_status_is_equal(RoomStatus.T_IDLE):
            return False
        if force:
            if 2 > self.in_room_count:  # 手动开始人数未满2人
                return False
        if self.max_player_count > self.in_room_count:
            return False
        if not self.get_owner_is_ready:  # 满人后其余玩家准备了，房主没准备，通知房主
            if self.ready_player_count == self.max_player_count - 1:
                room_data = {"club_id": self.club_id, "secret": C_SERVICE_SECRET_KEY}
                await self.cs2cs_by_rmq(ServiceEnum.C_CLUB, CmdClub.PLAYER_READY_EXCEPT_OWNER, room_data, self.owner)
                self.log_info("玩家都准备了,除了房主", self.owner)

        if self.max_player_count != self.ready_player_count:
            return False
        await self.async_set_room_status(RoomStatus.T_READY)
        await self.game_start()
        return True

    async def game_start(self):
        if not self.room_status_is_equal(RoomStatus.T_READY):
            return
        await self.async_set_room_status(RoomStatus.T_PLAYING)
        await self.inner_broadcast(CmdRoom.GAME_START)
        if self.round_idx == 1:
            record_info = await RecordsGameRoomRC.create_record_game_room(self.tid, tool_dt.cur_time())
            self.__record_id = record_info[0].record_rid
        self.call_flow(2, self.round_start)

    async def game_over(self, over_type=OverType.DEFAULT):
        if self.room_status_is_equal(RoomStatus.T_DISMISS):
            return
        await self.async_set_room_status(RoomStatus.T_DISMISS)
        result = {"seats": [], "time_stamp": tool_dt.cur_time(), "tid": self.tid}

        score_rank_map = self.get_player_ranking()

        for idx, p in enumerate(self.seats):
            if not p:
                continue
            num = 1 if idx == 0 else 0
            result["seats"].append(p.game_over_data)
            final_ranking = score_rank_map[p.total_score]
            final_grade = 1 if final_ranking == 1 else 0
            over_record = await RecordsGameTotalRC.create_record_game_total(self.__record_id, p.uid, p.total_score >= 0, p.total_score
                                                                            , final_ranking, final_grade, p.game_over_data, num)
            self.log_info("总结算战绩插入", over_record)

        data_model = S2CGameOverInfo.pb_model(**result)
        await self.inner_broadcast(CmdRoom.GAME_OVER, data_model)
        if self.club_id > 0:
            await self.cs2club_by_rmq(CmdClub.ROOM_INFO_CHANGE, self.club_room_info(ClubMsgType.DISMISS_ROOM))
        for p in self.seats:
            p.on_game_start_clear_data()
        await super().game_over()

    def get_player_ranking(self, account=None, is_round_over=False):
        if account:
            all_scores = [account.get(p.seat_id, {}).get("total_score", 0) for p in self.seats if p]
        elif is_round_over:
            all_scores = [0 for p in self.seats if p]
        else:
            all_scores = [p.total_score for p in self.seats if p]
        sorted_scores = sorted(all_scores, reverse=True)
        score_rank_map = {}

        for idx, score in enumerate(sorted_scores):
            score_rank_map[score] = idx + 1
        return score_rank_map

    def room_info(self):
        data = super().room_info()
        data["owner"] = self.__owner
        data["cs_type"] = self.service.service_type
        data["price"] = self.room_conf.get("price") or 0
        data["is_location"] = self.room_conf.get("is_location") or 0
        data["is_friend"] = self.room_conf.get("is_friend") or 0
        data["club_id"] = self.room_conf.get("club_id") or 0
        data["pay_type"] = self.room_conf.get("pay_type") or 0

        data["rule_details"] = self.__rule_details
        if self.__agree_dismiss_seats:
            data["dismiss_info"] = {
                "agree_seats": list(self.__agree_dismiss_seats),
                "req_dismiss_left_sec": self.dismiss_left_seconds()
            }
        return data

    def dismiss_left_seconds(self) -> int:
        """ 解散剩余时间 """
        return self.__timer_dismiss and self.__timer_dismiss.left_seconds() or 0

    def clear_room(self):
        """ 房间回收清理 """
        self.__round_msg_records = []  # 每局消息记录
        self.__timer_dismiss = None
        self.__agree_dismiss_seats = set()
        self.__timeout_idle_time = 60 * 60 * 30
        super().clear_room()

    def refresh_room_conf(self, service, room_conf):
        rule_details = room_conf.pop("rule_details")
        print("刷新房间配置", rule_details)
        room_conf.update(rule_details)
        super().refresh_room_conf(service, room_conf)

        self.__rule_details = rule_details
        self.__club_id = room_conf.get("club_id") or 0
        self.__owner = room_conf.get("creator") or 0  # 所有者
        self.__create_time = room_conf.get("created") or tool_dt.cur_time()
        self.__cur_round = room_conf.get("cur_round") or 1

        self.__round_msg_records = []  # 每局消息记录
        self.__timer_dismiss = None
        self.__agree_dismiss_seats = set()

    def get_extra_score_map(self) -> dict:
        map_copy = EXTRA_SCORE_MAP.copy()
        if self.play_type in (PlayType.GUI_YANG_4, PlayType.GUI_YANG_3, PlayType.GUI_YANG_2):
            map_copy.update({
                ExtraHuPai.GANG_SHANG_PAO: 3,
                ExtraHuPai.GANG_SHANG_HUA: 3,
                CheckType.CHECK_CHA_QUE: 1,
                CheckType.CHECK_YUAN_QUE: 2,
                # 贵阳麻将房卡场新增
                CheckType.CHECK_LAI_ZI_PENG: 30,
                CheckType.CHECK_LAI_ZI_GNAG: 40,
                CheckType.CHECK_LAI_ZI_JI: 2,
            })
            return map_copy
        elif self.play_type == PlayType.BI_JIE_MJ:
            map_copy.update({
                ExtraHuPai.GANG_SHANG_PAO: 10,
                ExtraHuPai.GANG_SHANG_HUA: 3,
                ExtraHuPai.QIANG_GANG_HU: 15,
                ExtraHuPai.TIAN_TING: 20,
                ExtraHuPai.DI_HU: 40,
                ExtraHuPai.TIAN_HU: 60,
                ExtraHuPai.SHA_BAO: 20,
            })
            return map_copy
        elif self.play_type == PlayType.ZUN_YI_LAI_ZI:
            map_copy.update({
                ExtraHuPai.GANG_SHANG_PAO: 10,
                ExtraHuPai.GANG_SHANG_HUA: 10,
                ExtraHuPai.QIANG_GANG_HU: 10,
                ExtraHuPai.TIAN_TING: 40,
                ExtraHuPai.DI_HU: 40,
                ExtraHuPai.TIAN_HU: 40,
                ExtraHuPai.SHA_BAO: 40,
                ExtraHuPai.YING_HU: 10,
                ExtraHuPai.XI_PAI: 25,
                ExtraHuPai.COMMON_TIAN_TING: 20,
                ExtraHuPai.COMMON_SHA_BAO: 20,

                CheckType.CHECK_CHA_QUE: 1,
                CheckType.CHECK_YUAN_QUE: 2,

                CheckType.CHECK_LAI_ZI_JI: 2,
                CheckType.CHECK_LAI_ZI_CHONG_XI: 25,
            })
            return map_copy
        else:
            return map_copy

    def get_pai_xing_score_map(self) -> dict:
        map_copy = PAI_XING_SCORE_MAP.copy()
        if self.play_type in (PlayType.GUI_YANG_4, PlayType.GUI_YANG_3, PlayType.GUI_YANG_2):
            qing_yi_se = 10
            if self.play_type == PlayType.GUI_YANG_3:
                qys_score = self.__rule_details.get("qing_yi_se_extra_add", 0)
                if qys_score:
                    qing_yi_se = 10 + 5

            map_copy.update({
                HuType.DI_LONG_QI: 20,
                HuType.DOUBLE_DI_LONG_QI: 30,
                HuType.QING_DOUBLE_DI_LONG_QI: 40,
                HuType.THREE_DI_LONG_QI: 40,
                HuType.QING_THREE_DI_LONG_QI: 50,
                HuType.QING_YI_SE: qing_yi_se
            })
            return map_copy
        elif self.play_type == PlayType.BI_JIE_MJ:
            map_copy.update({
                HuType.PING_HU: 6,
                HuType.DA_DUI_ZI: 12,
                HuType.QI_DUI: 10,
                HuType.DI_LONG_QI: 20,
                HuType.QING_YI_SE: 20,
                HuType.QING_DA_DUI: 40,
                HuType.QING_QI_DUI: 20,
                HuType.QING_DI_LONG: 30,
                HuType.QING_LONG_BEI: 30,
                HuType.DOUBLE_DI_LONG_QI: 30,
                HuType.QING_DOUBLE_DI_LONG_QI: 40,
                HuType.THREE_DI_LONG_QI: 40,
                HuType.QING_THREE_DI_LONG_QI: 50,
                HuType.JIN_GOU_DIAO: 52,
                HuType.QING_JIN_GOU: 52,
                HuType.YIN_GOU_DIAO: 32,  # 银钩钓
                HuType.RUAN_WU_DUI: 12,  # 软五对
                HuType.YING_WU_DUI: 12,  # 硬五对
                HuType.QYS_RUAN_WU_DUI: 40,  # 清硬五对
                HuType.QYS_YING_WU_DUI: 40,  # 清硬五对
            })
            return map_copy
        elif self.play_type == PlayType.ZUN_YI_LAI_ZI:
            base_score = 5
            map_copy.update({
                HuType.PING_HU: base_score,
                HuType.DA_DUI_ZI: base_score + 10,
                HuType.QI_DUI: base_score + 20,
                HuType.LONG_QI_DUI: base_score + 40,
                HuType.DOUBLE_LONG_QI: base_score + 80,
                HuType.THREE_LONG_QI: base_score + 120,
                HuType.DI_LONG_QI: base_score + 40,
                HuType.DOUBLE_DI_LONG_QI: base_score + 80,
                HuType.THREE_DI_LONG_QI: base_score + 120,
                HuType.JIN_GOU_DIAO: base_score + 20,
                HuType.QING_YI_SE: base_score + 20,
                HuType.QING_DA_DUI: base_score + 30,
                HuType.QING_QI_DUI: base_score + 40,
                HuType.QING_DI_LONG: base_score + 60,
                HuType.QING_DOUBLE_DI_LONG_QI: base_score + 100,
                HuType.QING_THREE_DI_LONG_QI: base_score + 140,
                HuType.QING_LONG_BEI: base_score + 60,
                HuType.QING_DOUBLE_LONG_QI: base_score + 100,
                HuType.QING_THREE_LONG_QI: base_score + 140,
                HuType.QING_JIN_GOU: base_score + 40
            })
            return map_copy
        else:
            return map_copy

    def get_ji_pai_score_map(self) -> dict:
        map_copy = JI_PAI_SCORE.copy()
        if self.play_type == PlayType.BI_JIE_MJ:
            map_copy.update({
                CardsType.YI_TONG: 5,
                JiType.CHONG_FENG_JI: 2,
                JiType.CHONG_FENG_JIN_JI: 2 * 10,
                JiType.JIN_JI: 10,
                JiType.YIN_JI: 5,
                JiType.ZE_REN_JI: 1,
            })
            return map_copy
        if self.play_type == PlayType.ZUN_YI_LAI_ZI:
            wgj_score = self.__rule_details.get("wu_gu_ji_score", 2)
            default_score = 1 if wgj_score == 3 else 2
            map_copy.update({
                CardsType.YAO_JI: 2,
                CardsType.YI_WAN: 1,
                CardsType.YI_TONG: 15,
                JiType.DEFAULT: default_score,
                JiType.CHONG_FENG_JI: 4,
                JiType.CHONG_FENG_JIN_JI: 4 * 3,  # 3倍数
                JiType.ZE_REN_JI: 4,
                JiType.JIN_JI: 2 * 3,
                JiType.WU_GU_JI: wgj_score,
                JiType.WU_GU_CFJ: wgj_score * 2,
                JiType.WU_GU_ZRJ: wgj_score * 2,
                JiType.WU_GU_JIN_JI: wgj_score * 3,
                JiType.WU_GU_CF_JIN_JI: wgj_score * 6,  # 3倍
                JiType.CF_YI_WAN: 4,  # 一万冲锋鸡
                JiType.YI_WAN_ZRJ: 4,  # 一万责任鸡
                JiType.JIN_YI_WAN: 2 * 3,  # 金一万 3倍
                JiType.JIN_CF_YI_WAN: 4 * 3,  # 金冲锋一万 3倍
                JiType.JIN_YI_TONG: 15 * 3,
                JiType.CF_YI_TONG: 20,
                JiType.JIN_CF_YI_TONG: 20 * 3,
                JiType.AN_GANG: 5,
                JiType.MING_GANG: 5,
                JiType.ZHUAN_WAN_GANG: 5,
            })
            return map_copy
        else:
            return map_copy

    async def async_set_room_status(self, status: RoomStatus):
        self.set_room_status(status)
        await GameRoomsRC.update_game_room(self.tid, status=status)

    async def cs2club_by_rmq(self, cmd, data):
        await self.cs2cs_by_rmq(ServiceEnum.C_CLUB, cmd, data)

    def club_room_info(self, msg_type):
        return {
            "club_id": self.__club_id,
            "created": self.__create_time,
            "creator": self.owner,
            "cs_type": self.service.service_type,
            "id": self.room_conf.get("id") or 0,
            "is_friend": self.room_conf.get("is_location") or 0,
            "is_location": self.room_conf.get("is_friend") or 0,
            "max_player": self.max_player_count,
            "pay_type": self.room_conf.get("pay_type"),
            "platform": self.room_conf.get("platform"),
            "play_type": self.play_type,
            "price": self.room_conf.get("price"),
            "room_id": self.tid,
            "room_type": self.room_type,
            "rule_details": self.__rule_details,
            "seats": [p.uid for p in self.seats if p],
            "status": self.room_status,
            "total_round": self.room_conf.get("total_round"),
            "round_idx": self.round_idx,
            "updated": self.__create_time,
            "msg_type": msg_type,
            "secret": C_SERVICE_SECRET_KEY,
        }
