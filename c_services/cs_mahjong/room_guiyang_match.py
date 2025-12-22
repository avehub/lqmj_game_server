from c_services.cs_mahjong.const import ActionType, FlowStatus, TimerDelay
from c_services.cs_mahjong.room_bijie import RoomBJ
from c_services.cs_mahjong.room_robot import RoomRobot
from common.public.enum_const import StaCode
from common.utils.utils import UtilsTool


class RoomGyMatch(RoomBJ, RoomRobot):
    def __init__(self, tid, service, room_conf):
        super().__init__(tid, service, room_conf)
