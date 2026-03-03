
from c_services.cs_mahjong.room_robot import RoomRobot



class RoomXyMatch(RoomRobot):
    def __init__(self, tid, service, room_conf):
        super().__init__(tid, service, room_conf)
