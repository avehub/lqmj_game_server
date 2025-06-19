

from nsanic.libs.tool import json_encode
from nsanic.libs import tool_dt
from c_services.base.base_room import BaseRoom
from c_services.const.cs_enum_const import RoomStatus, CmdRoom, CmdWorkers, GameAnnouncement
from c_services.cs_mahjong.const import OverType, PlayType, EXTRA_SCORE_MAP, ExtraHuPai, CheckType
from common.proto.py_pb2.ws_leisure import S2CDealCards, s2c_tickets_model, S2CBrokeBroad, \
    s2c_trustee_model, s2c_gold_model, s2c_one_of_model, s2c_recharge_model, S2CGameOverInfo
from common.public.conf import LIVE_SERVER
from common.public.enum_const import TaskId, StaCode
from common.utils.kit_async import DelayCall
from common.utils.utils import UtilsTool
from lucky_admin.const import WeightEnum
from lucky_game.const import ReasonCostGold, SeasonStatus, GiftType
from lucky_game.model_rc.game_rooms import GameRoomsRC


# from lucky_game.model_rc.base_activity import ConfActivityRC


class BaseCardRoom(BaseRoom):


    def __init__(self, tid, service, room_conf, poker,not_include = 0):
        rule_details = room_conf.pop("rule_details")
        room_conf.update(rule_details)
        super().__init__(tid, service, room_conf, poker,not_include)
        self.__rule_details = rule_details
        self.__in_stop = False
        self.__club_id = room_conf.get("club_id") or 0
        self.__owner = room_conf.get("creator") or 0
        self.__create_time = room_conf.get("create_time") or tool_dt.cur_time()
        self.__cur_round  = room_conf.get("cur_round") or 1
        self.__timeout_idle_time = 60 * 60 * 30
        self.__timer_dismiss = None
        self.__round_msg_records = []
        self.__winner_list = []
        self.__agree_dismiss_seats = set()

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
        sta = await super(BaseCardRoom, self).player_join_room(players)
        return sta

    async def player_quit_room(self,player,data):
        if not self.game_began:
            self.seats[player.seat_id - 1] = None
            await self.service.del_player_in_service(player.uid)  # 释放玩家放在下面，因为下面会清理玩家数据
            self.service.release_player(player)
            one_of_model = s2c_one_of_model()
            one_of_model.seat_id = self.curr_seat_id
            await self.inner_broadcast(CmdRoom.QUIT_ROOM,one_of_model)
        await super(BaseCardRoom, self).player_quit_room(player, data)

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


    async def game_over(self,over_type=OverType.DEFAULT):
        if self.room_status_is_equal(RoomStatus.T_DISMISS):
            return
        await self.async_set_room_status(RoomStatus.T_DISMISS)
        result = {"seats": [], "time_stamp": tool_dt.cur_time(), "tid": self.tid}
        for p in self.seats:
            result["seats"].append(p.game_over_data)
        data_model = S2CGameOverInfo.pb_model(**result)
        await self.inner_broadcast(CmdRoom.GAME_OVER, data_model)
        await super().game_over()




    def room_info(self):
        data = super().room_info()
        data["owner"] = self.__owner

        if self.__agree_dismiss_seats:
            data["agree_seats"] = list(self.__agree_dismiss_seats)
            data["req_dismiss_left_sec"] = self.dismiss_left_seconds()
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

    def refresh_room_conf(self, service,room_conf):
        rule_details = room_conf.pop("rule_details")
        room_conf.update(rule_details)
        super().refresh_room_conf(service,room_conf)

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
        if self.play_type in (PlayType.XING_YI_MJ,PlayType.AN_LONG_XUE_ZHAN):
            return map_copy
        elif self.play_type in (PlayType.GUI_YANG_4,PlayType.GUI_YANG_3,PlayType.GUI_YANG_2):
            map_copy.update({
                ExtraHuPai.GANG_SHANG_PAO: 3,  # 杠上炮
                ExtraHuPai.GANG_SHANG_HUA: 3,  # 杠上花(自摸)
                CheckType.CHECK_CHA_QUE: 1,
                CheckType.CHECK_YUAN_QUE: 2,
                # 贵阳麻将房卡场新增
                CheckType.CHECK_LAI_ZI_PENG: 30,
                CheckType.CHECK_LAI_ZI_GNAG: 40,
                CheckType.CHECK_LAI_ZI_JI: 2,
            })
            return map_copy
        else:
            return map_copy

    async def async_set_room_status(self, status: RoomStatus):
        self.set_room_status(status)
        await GameRoomsRC.update_game_room(self.tid, status=status)
