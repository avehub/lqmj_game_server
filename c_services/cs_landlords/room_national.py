import random
from common.proto.py_pb2.ws_leisure import do_redouble_model, s2c_one_of_model
from common.public.enum_const import StaCode
from .room_base import Room
from .const import FlowStatus
from ..const.cs_enum_const import CmdRoom


class NationalRoom(Room):
    """ 通用玩法房间设计 """

    def __init__(self, tid, service, room_conf):
        super().__init__(tid, service, room_conf)

    async def start_redouble(self):
        """ 开始加倍（每个玩家都能加倍） """
        await self.confirm_dealer()

        self.set_flow_status(FlowStatus.F_IN_REDOUBLE)
        seconds = 5
        one_of_model = s2c_one_of_model()
        one_of_model.seconds = seconds
        await self.inner_broadcast(CmdRoom.START_REDOUBLE, one_of_model)

        rand_time = [1, 2, 3, 4]
        for player in self.seats:
            delay_rs = random.choice(rand_time)
            if player.is_robot:
                player.call_flow(delay_rs, self.robot_auto_chan, player)

        self.call_flow(seconds, self.time_out_redouble, trustee=True)

    def all_has_doubled(self):
        """ 是否都加倍 """
        for player in self.seats:
            if not player.has_doubled:
                return False
        return True

    async def time_out_redouble(self, *args, trustee=False):
        """ 超时加倍 """
        if not self.flow_status_is_equal(FlowStatus.F_IN_REDOUBLE):
            return StaCode.FORBID, "非加倍中"
        for player in self.seats:
            if not player.has_doubled:
                not trustee and await self.do_trustee(player, True)
                await self.player_redouble(player, 0)
        await self.delay_func(1, self.turn_start)

    async def player_redouble(self, player, score, **kwargs):
        """ 通用版加倍 """
        if not self.flow_status_is_equal(FlowStatus.F_IN_REDOUBLE):
            return StaCode.FORBID, "非加倍中"
        if player.has_doubled:
            return StaCode.FORBID, "已选择加倍"
        if score > 0:
            player.do_double()

        player.has_doubled = True
        self.info_log(player.uid, "do 加倍", score)

        do_redouble_model.seat_id = player.seat_id
        do_redouble_model.score = score
        do_redouble_model.multiple = player.self_multiple
        await self.inner_broadcast(CmdRoom.DO_REDOUBLE, do_redouble_model)

        if self.all_has_doubled():
            await self.delay_func(1, self.turn_start, flow=FlowStatus.F_IN_REDOUBLE)
        return StaCode.PASS, ""

    def get_player_info(self, player):
        info = super().get_player_info(player)
        info["double_type"] = player.double_type
        return info
