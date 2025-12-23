from c_services.cs_mahjong.player import Player
from common.proto.py_pb2.ws_c2s import gang_model
from common.public.enum_const import StaCode
from .const import FlowStatus
from .player_fczj import PlayerFCZJ
from .room_fczj import RoomFCZJ
from .service_robot_act import MahjongServerRobotAct
from ..base.base_leisure_service import BaseLeisureService
from ..const.cs_enum_const import CmdRoom, RoomStatus


class MahjongServerFc(BaseLeisureService,MahjongServerRobotAct):
    ROOM = RoomFCZJ
    PLAYER = PlayerFCZJ

    def __init__(self):
        super().__init__()
        self.add_handlers({
            CmdRoom.FAN_JI.val: self.__on_player_fan_ji,
            CmdRoom.ROBOT_CAL_ACTION.val: self.on_robot_cal_action,
            CmdRoom.ROBOT_CAL_PENG.val: self.on_robot_cal_peng,
            CmdRoom.ROBOT_CAL_GANG.val: self.on_robot_cal_gang,
            CmdRoom.PLAYER_DING_QUE.val: self.__on_player_ding_que,
            CmdRoom.PLAYER_MEN.val: self.__on_player_men,
            CmdRoom.PLAYER_JIAN.val: self.__on_player_jian,
            CmdRoom.PLAY_CARDS.val: self.__on_player_chu_pai,
            CmdRoom.PLAYER_PASS.val: self.__on_player_pass,
            CmdRoom.PLAYER_PENG.val: self.__on_player_peng,
            CmdRoom.PLAYER_GANG.val: self.__on_player_gang,
        })

    async def __on_player_fan_ji(self, player, room, data):
        code, msg = await room.on_player_fan_ji(player, data)
        if code != StaCode.PASS:
            return await self.cs2ws_by_rmq(CmdRoom.PLAYER_GANG, player.uid, code, msg, ws_id=player.ws_id)

    async def __on_player_ding_que(self, player, room ,data):
        code, msg = await room.on_player_ding_que(player,data)
        if code != StaCode.PASS:
            return await self.cs2ws_by_rmq(CmdRoom.PLAYER_DING_QUE, player.uid, code, msg, ws_id=player.ws_id)

    async def __on_player_pass(self, player, room, _):
        code, msg = await room.on_player_pass(player)
        if code != StaCode.PASS:
            return await self.cs2ws_by_rmq(CmdRoom.PLAYER_PASS, player.uid, code, msg, ws_id=player.ws_id)

        return await room.check_action_end()

    async def __on_player_gang(self, player, room, data):
        code, msg = await room.on_player_gang(player, data)
        if code != StaCode.PASS:
            return await self.cs2ws_by_rmq(CmdRoom.PLAYER_GANG, player.uid, code, msg, ws_id=player.ws_id)
        await room.check_action_end()

    async def __on_player_peng(self, player, room, _):
        code, msg = await room.on_player_peng(player)
        if code != StaCode.PASS:
            return await self.cs2ws_by_rmq(CmdRoom.PLAYER_PENG, player.uid, code, msg, ws_id=player.ws_id)
        await room.check_action_end()

    async def __on_player_men(self, player, room, _):
        code, msg = await room.on_player_men(player)
        if code != StaCode.PASS:
            return await self.cs2ws_by_rmq(CmdRoom.PLAYER_MEN, player.uid, code, msg, ws_id=player.ws_id)
        await room.check_action_end()

    async def __on_player_jian(self, player, room, _):
        code, msg = await room.on_player_jian(player)
        if code != StaCode.PASS:
            return await self.cs2ws_by_rmq(CmdRoom.PLAYER_JIAN, player.uid, code, msg, ws_id=player.ws_id)
        await room.check_action_end()

    async def __on_player_chu_pai(self, player, room, data):
        code, msg = await room.on_player_chu_pai(player, data)
        if code != StaCode.PASS:
            return await self.cs2ws_by_rmq(CmdRoom.PLAY_CARDS, player.uid, code, msg, ws_id=player.ws_id)
        await room.enter_chu_pai_call()