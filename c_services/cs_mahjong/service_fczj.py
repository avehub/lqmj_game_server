from c_services.cs_mahjong.player import Player
from common.proto.py_pb2.ws_c2s import gang_model
from common.public.enum_const import StaCode
from .const import FlowStatus
from .player_fczj import PlayerFCZJ
from .room_fczj import RoomFCZJ
from ..base.base_leisure_service import BaseLeisureService
from ..const.cs_enum_const import CmdRoom, RoomStatus


class MahjongServerFc(BaseLeisureService):
    ROOM = RoomFCZJ
    PLAYER = PlayerFCZJ

    def __init__(self):
        super().__init__()
        self.add_handlers({
            CmdRoom.FAN_JI.val: self.__on_player_fan_ji,
            CmdRoom.ROBOT_CAL_ACTION.val: self.__on_robot_cal_action,
            CmdRoom.ROBOT_CAL_PENG.val: self.__on_robot_cal_peng,
            CmdRoom.ROBOT_CAL_GANG.val: self.__on_robot_cal_gang,
        })

    async def __on_player_fan_ji(self, player, room, data):
        code, msg = await room.on_player_fan_ji(player, data)
        if code != StaCode.PASS:
            return await self.cs2ws_by_rmq(CmdRoom.PLAYER_GANG, player.uid, code, msg, ws_id=player.ws_id)

    async def __on_robot_cal_action(self,uid,data):
        tid = data.get("tid")
        card = data.get("card")
        room, p = self.check_room_and_player(tid,uid)
        if room is None or p is None:
            return

        if p.chu_pai_len() > 0:
            self.log_info(tid,"uid",uid,"玩家已经出牌")

        code, msg = await room.on_player_chu_pai(p,room.serialized_chu_pai_data(card))
        if code != StaCode.PASS:
            self.log_info(tid,"uid",uid,"机器人出牌失败",code,msg)
        await room.enter_chu_pai_call()

    async def __on_robot_cal_peng(self,uid,data):
        card = data.get("card")
        tid = data.get("tid")
        card = data.get("card")
        room, p = self.check_room_and_player(tid,uid)
        if room is None or p is None:
            return
        if not card:
            self.log_info(tid,"uid",uid,"不碰牌")
            code,msg = await room.on_player_pass(p)
            if code != StaCode.PASS:
                self.log_info(tid,"uid",uid,"机器人不碰牌失败",code,msg)
                return
            if room.flow_status in (FlowStatus.T_IN_PUBLIC_OPRATE, FlowStatus.T_IN_ZHUAN_WAN_GANG_PAI_CALL):
               return await room.check_action_end()
        else:
            code,msg = await room.on_player_peng(p)
            if code != StaCode.PASS:
                self.log_info(tid,"uid",uid,"机器人碰牌失败",code,msg)
                return
            return await room.check_action_end()

    async def __on_robot_cal_gang(self,uid,data):
        tid = data.get("tid")
        card = data.get("card")
        room, p = self.check_room_and_player(tid,uid)
        if room is None or p is None:
            return
        if not card:
            if room.flow_status == FlowStatus.T_IN_PUBLIC_OPRATE:
                self.log_info(tid,"uid",uid,"不杠牌,直接过")
                code,msg = await room.on_player_pass(p)
                if code != StaCode.PASS:
                    self.log_info(tid,"uid",uid,"机器人不杠牌失败",code,msg)
                    return
                return await room.check_action_end()
            else:
                self.log_info(tid,"uid",uid,"不杠牌,直接打牌")
                room.check_robot_auto_chu_pai()
        else:
            code,msg = await room.on_player_gang(p,room.serialized_chu_pai_data(card))
            if code != StaCode.PASS:
                self.log_info(tid,"uid",uid,"机器人杠牌失败",code,msg)
                return
            return await room.check_action_end()

    def check_room_and_player(self,tid,uid):
        room = self.get_room(tid)
        if not room:
            self.log_info(tid,"uid",uid,"房间不存在")
            return None,None
        if room.status != RoomStatus.T_PLAYING:
            self.log_info(tid,"uid",uid,"房间状态不是游戏中")
            return None,None
        p = room.get_player(uid)
        if not p:
            self.log_info(tid,"uid",uid,"玩家不存在")
            return None,None
        return room,p