import asyncio
from c_services.const.cs_enum_const import RoomStatus, RoomType, CmdRoom
from common.proto.py_pb2.ws_base import PbWsBaseRep
from common.proto.py_pb2.ws_c2s import set_cards_model
from common.public.conf import LIVE_SERVER
from common.public.enum_const import StaCode, BaseEnum, ServiceEnum
from lucky_game.model_rc.game_rooms import GameRoomsRC
from .base_player import BasePlayer
from .base_service import BaseService
from typing import List, Optional
from common.utils.kit_async import DelayCall, delay_func
from abc import ABCMeta, abstractmethod


class BaseRoom(metaclass=ABCMeta):
    """ 基础玩法类 """

    def __init__(self, tid, service: BaseService, room_conf, poker,not_include =0,extra_count =0):
        self.__tid = tid
        self.__service = service
        self.__room_status = RoomStatus.T_IDLE
        self.__flow_status = 0
        self.__room_conf = room_conf
        self.__room_type = room_conf.get("room_type") or RoomType.COMMON
        self.__play_type = room_conf.get("play_type") or 1
        self.__level = room_conf.get("level") or ''
        self.__level_desc = room_conf.get("level_desc") or ''
        self.__base_score = room_conf.get("base_score") or 1  # 底分

        self.__max_player_count = room_conf.get("max_player") or room_conf.get("rule_conf", {}).get("max_player") or 4
        self.__total_round = room_conf.get("total_round") or room_conf.get("rule_conf", {}).get(
            "total_round") or 1  # 总局数

        self.__curr_seat_id = 0
        self.__dealer = 0
        self.__round_idx = 1  # 局数
        self.__seats: List[Optional[BasePlayer]] = self.__init_seats()

        self.__poker = poker(not_include,extra_count)
        self.__timer = None
        self.__timer_trustee = None  # 托管timer
        self.__timer_robot = None  # 托管timer

    @property
    def tid(self):
        return self.__tid

    def set_tid(self, tid):
        """ 房间号累加 """
        if self.room_status == RoomStatus.T_IDLE or self.room_status == RoomStatus.T_CLOSED:
            self.__tid = tid

    @property
    def service(self):
        return self.__service

    @property
    def room_conf(self):
        return self.__room_conf

    @property
    def room_type(self):
        return self.__room_type

    @property
    def play_type(self):
        return self.__play_type

    @property
    def level(self):
        return self.__level

    @property
    def level_desc(self):
        return self.__level_desc

    @property
    def base_score(self):
        return self.__base_score

    @base_score.setter
    def base_score(self, score):
        self.__base_score = score

    @property
    def room_status(self):
        return self.__room_status

    @property
    def flow_status(self):
        return self.__flow_status

    @property
    def max_player_count(self):
        return self.__max_player_count

    @property
    def curr_seat_id(self):
        return self.__curr_seat_id

    @curr_seat_id.setter
    def curr_seat_id(self, seat_id: int):
        self.__curr_seat_id = seat_id

    @property
    def dealer_id(self):
        return self.__dealer

    @dealer_id.setter
    def dealer_id(self, seat):
        self.__dealer = seat

    @property
    def seats(self):
        return self.__seats

    @property
    def round_idx(self):
        return self.__round_idx

    @property
    def poker(self):
        return self.__poker

    def __init_seats(self):
        return [] if self.room_type == RoomType.COMMON else [None] * self.max_player_count

    def incr_round_count(self):
        self.__round_idx += 1

    def __cancel_timer(self):
        if self.__timer:
            self.__timer.cancel()
            self.__timer = None

    def __cancel_timer_robot(self):
        if self.__timer_robot:
            self.__timer_robot.cancel()
            self.__timer_robot = None

    def __cancel_timer_trustee(self):
        if self.__timer_trustee:
            self.__timer_trustee.cancel()
            self.__timer_trustee = None

    def call_flow(self, seconds, func, *params, **kwargs):
        """ 正常延时 """
        self.__cancel_timer()
        self.__timer = DelayCall(seconds, func, *params, **kwargs, log_handler=self.err_log)
        self.__timer.start()

    def call_flow_robot(self, seconds, func, *params, **kwargs):
        """ 机器人正常延时 """
        self.__cancel_timer_robot()
        self.__timer_robot = DelayCall(seconds, func, *params, **kwargs, log_handler=self.err_log)
        self.__timer_robot.start()

    def call_flow_trustee(self, seconds, func, *params, **kwargs):
        """ 托管延时 """
        if params:
            player = params[0]
            if isinstance(player, BasePlayer):
                if not player.trustee:
                    return
        self.__cancel_timer_trustee()
        self.__timer_trustee = DelayCall(seconds, func, *params, **kwargs, log_handler=self.err_log)
        self.__timer_trustee.start()

    def cancel_timer(self):
        self.__cancel_timer()

    def cancel_timer_trustee(self):
        self.__cancel_timer_trustee()

    def cancel_all_timer(self):
        """ 取消所有延时 """
        self.__cancel_timer()
        self.__cancel_timer_robot()
        self.__cancel_timer_trustee()

    @staticmethod
    async def delay_func(seconds, func, *args, **kwargs):
        return await delay_func(seconds, func, *args, **kwargs)

    def left_seconds(self) -> int:
        return (self.__timer and self.__timer.left_seconds() or
                self.__timer_robot and self.__timer_robot.left_seconds() or 0)

    def log_info(self, *data):
        self.__service.log_info(self.__tid, *data)

    def err_log(self, *data):
        self.__service.log_err(self.__tid, *data)

    def set_room_status(self, status: RoomStatus):
        self.__room_status = status
        self.log_info("房间状态变动：", status, status.phrase)

    def set_flow_status(self, flow_status: BaseEnum):
        self.__flow_status = flow_status
        if not LIVE_SERVER:
            self.log_info("流程变动：", flow_status, flow_status.phrase)

    def room_status_is_equal(self, room_status: RoomStatus):
        if self.__room_status == room_status:
            return True
        self.log_info("当前房间状态：", self.__room_status, room_status)
        return False

    def flow_status_is_equal(self, flow_status: BaseEnum):
        if self.__flow_status == flow_status:
            return True
        self.log_info("当前流程状态：", self.__flow_status, flow_status)
        return False

    def in_flow_status(self, *status):
        """ 当前流程是否在指定流程中 """
        return self.__flow_status in status

    @property
    def in_room_count(self):
        count = 0
        for p in self.__seats:
            # if p and not p.is_out:
            if p:
                count += 1
        return count

    @property
    def no_give_up_count(self):
        count = 0
        for p in self.__seats:
            if p and not p.is_out:
                count += 1
        return count

    def search_leisure_seat(self) -> int:
        """ 寻找空闲位置 """
        # todo: 如果是自建房需要走注释逻辑
        if self.__room_type == RoomType.COMMON:
            return len(self.__seats)
        for seat, p in enumerate(self.__seats):
            if not p:
                return seat
        return -1

    def sit_down(self, player, seat):
        player.tid = self.__tid
        player.seat_id = seat
        if self.room_type == RoomType.COMMON:
            self.__seats.append(player)
        else:
            self.__seats[seat] = player

    def dealer(self):
        return self.get_player_by_seat_id(self.__dealer)

    def curr_player(self):
        return self.get_player_by_seat_id(self.__curr_seat_id)

    def get_player_by_seat_id(self, seat_id: int) -> BasePlayer or None:
        seat_id -= 1
        if 0 <= seat_id < len(self.__seats):
            return self.__seats[seat_id]

    def next_player_reverse(self, seat_id, with_cards=True):
        """ 反序下一个人 """
        for i in range(seat_id - 2, -1, -1):  # -1是当前玩家，再-1是上一个玩家
            p = self.seats[i]
            if p:
                if p.is_out:
                    continue
                if with_cards and not p.cards:
                    continue
                return p
        for i in range(self.max_player_count - 1, seat_id - 1, -1):  # -1是当前玩家，不能包含当前玩家
            p = self.seats[i]
            if p:
                if p.is_out:
                    continue
                if with_cards and not p.cards:
                    continue
                return p
        return

    def next_player(self, seat_id: int, with_cards=True) -> BasePlayer or None:
        """
        下一个玩家
        注意：由于玩家seat id被 + 1过，这里闯进来的seat id视为seats中的下一个索引
        """
        for i in range(seat_id, self.__max_player_count):
            p = self.__seats[i]
            if p:
                if p.is_out:
                    continue
                if with_cards and not p.cards:
                    continue
                return p
        for i in range(seat_id - 1):  # seat_id-1后不包，不到自己
            p = self.__seats[i]
            if p:
                if p.is_out:
                    continue
                if with_cards and not p.cards:
                    continue
                return p
        return None

    def has_next_round(self):
        """ 判断是否还有下一局 """
        return self.__round_idx < self.__total_round

    async def player_join_room(self, players):
        """ 玩家加入房间 """
        task_list = []
        for player in players:
            # todo: 进入房间则设置玩家所在游戏类型
            if not player.is_robot:
                task_list.append(self.service.sava_player_in_service(player.uid, self.tid))
                task_list.append(self.service.init_player(player))
                task_list.append(self.service.set_player_ws_id(player))
            seat = self.search_leisure_seat()
            self.sit_down(player, seat)
        task_list and await asyncio.gather(*task_list)

    def player_quit_room(self, player, _):
        """ 玩家离开房间 """
        player.offline = True
        self.log_info(player.uid, "玩家离开房间", player.is_out)

    def set_cards_in_debug(self, data):
        """ 设牌调试 """
        if LIVE_SERVER:
            return StaCode.FAIL, "不允许设牌"
        set_cards_model.ParseFromString(data)
        dealer_id = set_cards_model.dealer_id or 0
        cards = set_cards_model.cards
        if len(cards) != self.max_player_count + 1:
            return StaCode.FAIL, "设牌数据结构错误"

        all_cards = []
        cards_data = []
        for c in cards:
            data = []
            if len(c.values) > 0:
                all_cards.extend(c.values)
                data.extend(c.values)
                cards_data.append(data)
            else:
                cards_data.append([])
        card2count = {}
        for c in all_cards:
            count = card2count.get(c, 0) + 1
            card2count[c] = count
            if count > self.__poker.CARDS_NUM:
                return StaCode.FAIL, "设牌多于牌该有的数量"
            card = self.__poker.CARDS_ENUM.find_member_by_val(c)
            if not card:
                return StaCode.FAIL, "设牌错误"

        if dealer_id > 0:
            pass  # todo 设置庄家
        self.__poker.set_order_cards(cards_data)  # 具体设置牌
        return StaCode.PASS, ""

    async def round_start(self):
        """ 子类实现 """

    async def inner_send(self, p, c_code, data=None, code: StaCode = StaCode.PASS, hint="", req_id=""):
        """ 单发，注意：机器人不要调该接口！！！ """
        if p.is_robot:
            return
        if p.offline:
            return
        if p.tid != self.__tid:
            return
        await self.__service.cs2ws_by_rmq(c_code, p.uid, code, hint, data, req_id, ws_id=p.ws_id)

    async def inner_broadcast(self, c_code, data=None, code: StaCode = StaCode.PASS, hint="ok", exclude_uid=0):
        """ 房间内广播 """
        task_list = []
        send_player_list = []
        for p in self.__seats:
            if not p:
                continue
            if p.offline:
                continue
            if p.is_robot:
                continue
            if p.tid != self.__tid:
                continue
            if p.uid == exclude_uid:
                continue
            send_player_list.append(p)

        if send_player_list:
            # data只序列化一次
            hint = hint or code.msg
            pb_data = PbWsBaseRep.encode(code, hint, data)
            for player in send_player_list:
                task_list.append(self.__service.cs2ws_by_rmq_in_room(c_code, player.uid, pb_data, ws_id=player.ws_id))

        if task_list:
            await asyncio.gather(*task_list)

    async def cs2cs_by_rmq(self, cs_type: ServiceEnum, c_code, msg=None, uid=1):
        """ 推送到子服务 """
        await self.__service.cs2cs_by_rmq(cs_type, c_code, msg, uid)

    async def send_task_to_worker(self, cmd, data, uid=1):
        """ 发送任务到worker消费 """
        await self.__service.push_task2worker(cmd, data, uid)

    # async def broadcast_to_cs(self,cmd,uid=1,data = None):
    #     if not self.__service:
    #         return
    #     await self.__service.publish_to_fanout(cmd, uid,data)


    @staticmethod
    @abstractmethod
    def get_player_info(player):
        """ 抽象接口，子类必须实现 """

    @abstractmethod
    def try_round_start(self):
        """ 抽象接口，子类必须实现 """

    @staticmethod
    def serialize_room_info():
        """ 子类实现 """
        raise NotImplementedError

    @staticmethod
    def serialize_player_info(room_player_info):
        """ 子类实现 """
        raise NotImplementedError

    async def notify_player_enter_room(self, player, reenter=False):
        # 房间信息
        await self.notify_room_info(player)
        # 发送房间内所有玩家信息给当前玩家
        await self.notify_player_info(player, reenter)

    async def notify_room_info(self, player=None):
        data = self.serialize_room_info()
        if not data:
            return
        if player:
            await self.inner_send(player, CmdRoom.ROOM_INFO, data)
        else:
            await self.inner_broadcast(CmdRoom.ROOM_INFO, data)

    async def notify_player_info(self, curr_player=None, reenter=False):
        """ 通知玩家信息 """
        if curr_player:
            # 断线重进房间
            room_player_info = self.room_player_info(curr_player)
            data = self.serialize_player_info(room_player_info)
            await self.inner_send(curr_player, CmdRoom.PLAYER_INFO, data)
            if not reenter:
                curr_p_info = curr_player.player_info(contain_cards=False)
                data = self.serialize_player_info([curr_p_info])
                await self.inner_broadcast(CmdRoom.PLAYER_INFO, data, exclude_uid=curr_player.uid)
            return

        task_list = []
        for player in self.seats:
            if player.is_robot:
                continue
            room_player_info = self.room_player_info(player)
            data = self.serialize_player_info(room_player_info)
            task_list.append(self.inner_send(player, CmdRoom.PLAYER_INFO, data))
        if task_list:
            await asyncio.gather(*task_list)

    def room_player_info(self, curr_player=None):
        result = []
        for player in self.seats:
            if player:
                contain_cards = curr_player and player.seat_id == curr_player.seat_id or False
                info = player.player_info(contain_cards)
                result.append(info)
        return result

    def room_info(self):
        """ 房间信息：子类必须实现该方法 """
        data = {
            "tid": self.__tid,
            "play_type": self.play_type,
            "curr_seat_id": self.__curr_seat_id,
            "dealer_id": self.__dealer,
            "room_status": self.__room_status,
            "flow_status": self.__flow_status,
            "seconds": self.left_seconds(),
            "room_conf": self.room_conf,
            "round_idx": self.__round_idx,
        }
        return data

    @classmethod
    def new(cls, tid, service, room_conf, *args, **kwargs):
        return cls(tid, service, room_conf, *args, **kwargs)

    async def round_over(self, *args, **kwargs):
        raise NotImplemented

    async def force_dismiss(self):
        self.log_info("强制解散：", self.room_status, self.flow_status)
        if self.room_status in (RoomStatus.T_CHECK_OUT, RoomStatus.T_CLOSED):
            return
        # 该条判断主要为了避免重复回收房间
        if self.service.get_room(self.__tid):
            return await self.round_over(is_force=True)

    async def game_over(self):
        """ 游戏结束 """
        task_list = []
        for p in self.__seats:
            if p:
                uid = p.uid
                if not p.is_robot and p.tid != 0:  # 玩家可能在上一桌破产离开，仅仅只是将tid置为0
                    if self.__room_type == RoomType.SELF_BUILD:
                        await self.service.del_player_in_game(uid)
                        # tid = p.tid
                        # task_list.append(GameRoomsRC.leave_room(tid, uid))
                        # self.log_info("游戏结束离开房间:", leave_result, "房间状态:", self.__room_status)
                if not p.is_robot:
                    task_list.append(GameRoomsRC.leave_room(self.tid, uid))
                    task_list.append(self.service.del_player_in_service(uid))
                self.service.release_player(p)
        self.__room_status = RoomStatus.T_CLOSED
        if task_list:
           result = await asyncio.gather(*task_list)
           self.log_info("调用离开房间结果",result)
        self.service.release_room(self)


    def clear_room(self):
        """ 清理房间 """
        self.__service = None
        self.__room_status = RoomStatus.T_CLOSED
        self.__flow_status = 0
        self.__curr_seat_id = 0
        self.__dealer = 0
        self.__round_idx = 1  # 局数
        self.__seats: List[Optional[BasePlayer]] = self.__init_seats()
        self.__room_conf = {}
        self.__poker = None
        self.cancel_all_timer()
        if hasattr(self, '_timeout_task') and self._timeout_task:
            self._timeout_task.cancel()  # 关键！

    def refresh_room_conf(self, service, room_conf):
        """ 刷新房间配置 """
        self.__service = service
        self.__room_conf = room_conf
        self.__room_type = room_conf.get("room_type") or RoomType.COMMON
        self.__play_type = room_conf.get("play_type") or 1
        self.__level = room_conf.get("level") or 1
        self.__level_desc = room_conf.get("desc") or ''
        self.__base_score = room_conf.get("base_score") or 1  # 底分
        self.__max_player_count = room_conf.get("max_player") or room_conf.get("rule_conf", {}).get("max_player") or 4
        self.__total_round = room_conf.get("total_round") or room_conf.get("rule_conf", {}).get(
            "total_round") or 1  # 总局数

        self.__seats: List[Optional[BasePlayer]] = self.__init_seats()
        self.__room_status = RoomStatus.T_IDLE
