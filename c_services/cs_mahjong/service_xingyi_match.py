from c_services.cs_mahjong.player import Player
from .room_xingyi_match import RoomXyMatch
from .service import MahjongServer
from ..const.cs_enum_const import CmdRoom, RoomStatus


class MahjongServerXyMatch(MahjongServer):
    ROOM = RoomXyMatch
    PLAYER = Player

    def __init__(self):
        super().__init__()
        self.add_handlers({
            CmdRoom.ROBOT_CAL_ACTION.val: self.on_robot_cal_action,
            CmdRoom.ROBOT_CAL_PENG.val: self.on_robot_cal_peng,
            CmdRoom.ROBOT_CAL_GANG.val: self.on_robot_cal_gang,
            CmdRoom.ALL_PLAYER_FINISH.val: self.__all_player_finish,
        })

    async def __all_player_finish(self, _, data):
        self.log_info("所有真人玩家都结束当前轮次了")
        robot_room = data.get("robot_room") or None
        if robot_room:
            for tid in robot_room:
                room = self.get_room(tid)
                if not room:
                    self.log_info(tid, "房间不存在")
                    return None, None
                if room.room_status != RoomStatus.T_PLAYING:
                    room.log_info(tid, "uid", "房间状态不是游戏中")
                    return None, None
                room.robot_fast = True
