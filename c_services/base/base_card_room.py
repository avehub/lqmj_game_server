import asyncio
import random

from nsanic.libs.tool import json_encode
from nsanic.libs import tool_dt
from c_services.base.base_room import BaseRoom
from c_services.const.cs_enum_const import RoomStatus, CmdRoom, CmdWorkers, GameAnnouncement
from c_services.cs_mahjong.const import OverType
from common.proto.py_pb2.ws_leisure import S2CDealCards, s2c_tickets_model, S2CBrokeBroad, \
    s2c_trustee_model, s2c_gold_model, s2c_one_of_model, s2c_recharge_model
from common.public.conf import LIVE_SERVER
from common.public.enum_const import TaskId, StaCode
from common.utils.utils import UtilsTool
from lucky_admin.const import WeightEnum
from lucky_game.const import ReasonCostGold, SeasonStatus, GiftType
# from lucky_game.model_rc.base_activity import ConfActivityRC


class BaseCardRoom(BaseRoom):


    def __init__(self, tid, service, room_conf, poker):
        rule_details = room_conf.pop("rule_details")
        room_conf.update(rule_details)
        super().__init__(tid, service, room_conf, poker)
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

    async def player_join_room(self, players: list):
        return await super(BaseCardRoom, self).player_join_room(players)

    async def player_quit_room(self,player,data):
        await super(BaseCardRoom, self).player_quit_room(player, data)
        if not self.game_began:
            self.seats[player.seat_id - 1] = None
            await self.service.del_player_in_service(player.uid)  # 释放玩家放在下面，因为下面会清理玩家数据
            self.service.release_player(player)

    def agree_dismiss_count(self):
        return len(self.__agree_dismiss_seats)

    def add_agree_dismiss(self, seat_id):
        self.__agree_dismiss_seats.add(seat_id)

    def clear_agree_dismiss(self):
        self.cancel_timer_dismiss()
        return self.__agree_dismiss_seats.clear()


    def cancel_timer_dismiss(self):
        if self.__timer_dismiss:
            self.__timer_dismiss.cancel()
            self.__timer_dismiss = None

    def game_began(self):
        return self.round_idx != 1 or self.room_status != RoomStatus.T_IDLE

    async def round_start(self):
        self.clear_room_round_start()
        await super().round_start()

    def start_next_round(self):
        """ 开始下一局 """
        self.incr_round_count()
        self.set_room_status(RoomStatus.T_IDLE)
        self.try_round_start()

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
        pass

    async def try_round_over(self):
        """ 尝试解散房间 """
        for player in self.seats:
            if player.is_robot:
                continue
            if not (player.is_out and player.offline):
                return  # 但凡有真实玩家 没有 破产和离线则不解散房间
        self.log_info("房间内已经没有真人玩家，enter force_dismiss")
        await self.delay_func(0.5, self.force_dismiss)


    async def do_deal_cards(self, all_cards, set_dealer_card=None, extra_data=None):
        send_list = []
        for i, player in enumerate(self.seats):
            player.cards = all_cards[i]
            if set_dealer_card and set_dealer_card in player.cards:
                self.dealer_id = player.seat_id
                self.log_info("设置庄为：", self.dealer_id, player.uid)

            self.log_info(player.uid, player.seat_id, "玩家发牌：", player.cards)
            if player.is_robot:
                continue
            data = {"cards": player.cards, "seat_id": player.seat_id}
            if extra_data:
                data.update(extra_data)
            data_model = S2CDealCards.pb_model(**data)
            send_list.append(self.inner_send(player, CmdRoom.DEALER_CARDS, data_model))
        await asyncio.gather(*send_list)

    async def play_card_by_rand(self, player):
        """ 随机出牌 """


    async def game_over(self,over_type=OverType.DEFAULT):
        if self.room_status_is_equal(RoomStatus.T_DISMISS):
            return
        self.set_room_status(RoomStatus.T_DISMISS)
        result = {"seats": [], "time_stamp": tool_dt.cur_time(), "tid": self.tid}
        for p in self.seats:
            result["seats"].append(p.game_over_data)

        await self.inner_broadcast(CmdRoom.GAME_OVER, result)

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