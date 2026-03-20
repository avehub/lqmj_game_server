from c_services.const.cs_enum_const import CmdRoom, RoomStatus
from common.public.enum_const import StaCode
from .const import FlowStatus
from ..base.base_service import BaseService


class MahjongServerRobotAct(BaseService):

    async def on_robot_cal_action(self, uid, data):
        tid = data.get("tid")
        card = data.get("card")
        room, p = self.check_room_and_player(tid, uid)
        if room is None or p is None:
            return
        if room.room_status != RoomStatus.T_PLAYING:
            room.log_info(tid, "uid", uid, "房间状态不是游戏中")
            return

        code, msg = await room.on_player_chu_pai(p, room.serialized_chu_pai_data(card))
        if code != StaCode.PASS:
            room.log_info(tid, "uid", uid, "cs_robot_mahjong出牌失败", code, msg)
            return
        room.log_info(tid, "uid", uid, "cs_robot_mahjong出牌消息", data)
        room.call_flow(0.5, room.enter_chu_pai_call)

    async def on_robot_cal_peng(self, uid, data):
        tid = data.get("tid")
        card = data.get("card")
        room, p = self.check_room_and_player(tid, uid)
        if room is None or p is None:
            return
        if room.room_status != RoomStatus.T_PLAYING:
            room.log_info(tid, "uid", uid, "房间状态不是游戏中")
            return
        if not card:
            room.log_info(tid, "uid", uid, "cs_robot_mahjong不碰牌")
            if room.flow_status_is_equal(FlowStatus.T_IN_CHECK_OUT):
                room.log_info(tid, "uid", uid, "桌子已结算，不再碰的后续")
                return
            code, msg = await room.on_player_pass(p)
            if code != StaCode.PASS:
                room.log_info(tid, "uid", uid, "cs_robot_mahjong不碰牌失败", code, msg)
                return
            if room.flow_status in (FlowStatus.T_IN_PUBLIC_OPRATE, FlowStatus.T_IN_ZHUAN_WAN_GANG_PAI_CALL):
                await room.check_action_end()
        else:
            code, msg = await room.on_player_peng(p)
            if code != StaCode.PASS:
                room.log_info(tid, "uid", uid, "cs_robot_mahjong碰牌失败", code, msg)
                return
            room.log_info(tid, "uid", uid, "cs_robot_mahjong碰牌消息", data)
            await room.check_action_end()

    async def on_robot_cal_gang(self, uid, data):
        tid = data.get("tid")
        card = data.get("card")
        room, p = self.check_room_and_player(tid, uid)
        if room is None or p is None:
            return
        if room.room_status != RoomStatus.T_PLAYING:
            room.log_info(tid, "uid", uid, "房间状态不是游戏中")
            return
        if not card:
            if room.flow_status == FlowStatus.T_IN_PUBLIC_OPRATE:
                room.log_info(tid, "uid", uid, "cs_robot_mahjong不杠牌,直接过")
                if room.flow_status_is_equal(FlowStatus.T_IN_CHECK_OUT):
                    room.log_info(tid, "uid", uid, "桌子已结算，不再杠的后续")
                    return
                code, msg = await room.on_player_pass(p)
                if code != StaCode.PASS:
                    room.log_info(tid, "uid", uid, "cs_robot_mahjong不杠牌失败", code, msg)
                    return
                return await room.check_action_end()
            else:
                room.log_info(tid, "uid", uid, "cs_robot_mahjong不杠牌,直接打牌")
                await room.check_robot_auto_chu_pai()
        else:
            code, msg = await room.on_player_gang(p, room.serialized_chu_pai_data(card))
            if code != StaCode.PASS:
                room.log_info(tid, "uid", uid, "cs_robot_mahjong杠牌失败", code, msg)
                return
            room.log_info(tid, "uid", uid, "cs_robot_mahjong杠牌消息", data)
            return await room.check_action_end()

    def check_room_and_player(self, tid, uid):
        room = self.get_room(tid)
        if not room:
            self.log_info(tid, "uid", uid, "房间不存在")
            return None, None
        if room.room_status != RoomStatus.T_PLAYING:
            room.log_info(tid, "uid", uid, "房间状态不是游戏中")
            return None, None
        p = self.get_player(uid)
        if not p:
            room.log_info(tid, "uid", uid, "玩家不存在")
            return None, None
        return room, p
