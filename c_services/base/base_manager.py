from c_services.base.base_player import BasePlayer
from typing import Optional, Deque
from collections import deque

from c_services.const.cs_enum_const import RoomType


class SessionManager:
    """ 游戏玩家、房间 会话管理 """
    conf = None

    def __init__(self, use_pool=False):
        self.__rooms = {}
        self.__players = {}
        self.__use_pool = use_pool
        self.__room_pool = Optional[Deque]
        self.__player_pool = Optional[Deque]
        if use_pool:
            room_num = 300
            self.__room_pool = deque(maxlen=room_num)  # 房间对象池
            self.__player_pool = deque(maxlen=room_num * 4)  # 玩家对象池

    async def new_match(self, *args, **kwargs):
        """ 接收新匹配 """

    def get_room(self, tid):
        """ 获取房间 """
        return self.__rooms.get(tid)

    def __create_room(self, room, room_conf, **kwargs):
        if not hasattr(room, "new"):
            raise AttributeError(f"type object {room.__name__} has no attribute 'new'")
        while 1:
            tid = self.conf.rng.mk_num(length=7)
            if not self.__rooms.get(tid):
                return room.new(tid, self, room_conf, **kwargs)

    def create_room(self, room, room_conf, **kwargs):
        room_type = room_conf.get("room_type")
        tid = kwargs.pop("tid") if room_type == RoomType.SELF_BUILD else 0
        if self.__room_pool:
            room_obj = self.__room_pool.popleft()
            if tid!=0:
                room_obj.set_tid(tid)
            room_obj.refresh_room_conf(self, room_conf, **kwargs)
            if room_type != RoomType.SELF_BUILD:
                tid = room_obj.tid + 1
                while self.__rooms.get(tid):
                    tid += 1
                room_obj.set_tid(tid)
        else:
            if room_type == RoomType.SELF_BUILD:
                room_obj = room.new(tid,self, room_conf, **kwargs)
            else:
                room_obj = self.__create_room(room, room_conf, **kwargs)
        self.__rooms[room_obj.tid] = room_obj
        return room_obj

    def release_room(self, room):
        """ 释放房间 """
        self.__del_room(room.tid)
        room.clear_room()
        if self.__use_pool:
            self.__room_pool.append(room)

    def __del_room(self, tid):
        """ 删除房间 """
        self.__rooms.pop(tid, None)
        self.log_info(f"回收房间：{tid}, 当前游戏房间：{self.__rooms.keys()}")

    def create_player(self, c_player, uid, is_robot) -> BasePlayer or None:
        """ 创建玩家 """
        if self.__player_pool:
            player = self.__player_pool.popleft()
            player.refresh_player(uid, is_robot)
        else:
            player = c_player(uid, is_robot)

        self.__players[player.uid] = player
        return player

    def get_player(self, uid) -> BasePlayer or None:
        return self.__players.get(uid)

    def release_player(self, p):
        """ 释放玩家 """
        self.__del_player(p)
        p.clear_player()  # 此处顺序不能调整！！！
        if self.__use_pool:
            self.__player_pool.append(p)  # 回收玩家对象到对象池

    def __del_player(self, p: BasePlayer):
        """ 回收玩家 """
        del_p = self.__players.get(p.uid)
        if del_p and del_p.tid == p.tid:  # 玩家破产退出时的tid与新进房间tid不一样
            self.__players.pop(p.uid, None)
