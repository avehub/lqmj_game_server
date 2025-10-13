import asyncio

from c_services.base.base_server import BaseServer
from c_services.const.cs_enum_const import CmdClub, CallCheck
from c_services.cs_club.room import ClubRoom
from common.proto.py_pb2.ws_c2s import leave_club_model
from common.proto.py_pb2.ws_leisure import S2CClubRoomInfo, S2CClubNotice
from common.public.enum_const import StaCode


class ClubServer(BaseServer):

    SUBSCRIBE_FANOUT = None

    def __init__(self):
        super().__init__()
        self.add_handlers({
            CmdClub.ENTER_CLUB: self.__enter_club,
            CmdClub.QUIT_CLUB: self.__quit_club,
            CmdClub.ROOM_INFO_CHANGE: self.__room_info_change,
            CmdClub.CLUB_OWNER_DISMISS: self.__club_owner_dismiss,
            CmdClub.PLAYER_READY_EXCEPT_OWNER: self.__player_ready_except_owner,
            CmdClub.LEAVE_CLUB: self.__leave_club,
            CmdClub.CLUB_NOTICE: self.__club_notice,
        })

        self.__rooms = {}

    def get_room(self, cid):
        return self.__rooms.get(cid)

    def create_room(self, cid, owner):
        room = ClubRoom(cid, owner, self)
        self.__rooms[cid] = room
        self.log_info("创建茶馆房间",cid,owner)
        return room

    def remove_room(self, cid):
        if cid in self.__rooms:
            self.__rooms.pop(cid)

    def get_or_create_room(self, cid, owner):
        return self.get_room(cid) or self.create_room(cid, owner)

    async def __enter_club(self, uid, data):
        """ 进入 """
        self.log_info("玩家进入茶馆",uid,data)
        club_id = data.get("club_id")
        # todo: 1.检验club_id 是否有对应茶馆
        if club_id <= 0:
            return await self.cs2ws_by_rmq(CmdClub.ENTER_CLUB, uid, StaCode.FAIL, "茶馆id有误")
        room = self.get_or_create_room(club_id, uid)
        # todo: 2.检验当前uid是否是club id下的茶馆成员
        if uid <= 0:
            return await self.cs2ws_by_rmq(CmdClub.ENTER_CLUB, uid, StaCode.FAIL, "玩家uid有误")
        self.log_info("club_id",club_id,"玩家进入茶馆", uid,room, room.members)
        room.player_join_club_room(uid)
        return await self.cs2ws_by_rmq(CmdClub.ENTER_CLUB, uid)

    async def __quit_club(self, uid, data):
        """ 退出 """
        club_id = data.get("club_id")
        room = self.get_room(club_id)
        if not room:
            return await self.cs2ws_by_rmq(CmdClub.QUIT_CLUB, uid, StaCode.FAIL)
        room.player_quit_club_room(uid)
        self.log_info("club_id", club_id, "玩家退出茶馆", uid)
        return await self.cs2ws_by_rmq(CmdClub.QUIT_CLUB, uid)

    async def __leave_club(self, uid, data):
        leave_club_model.ParseFromString(data)
        club_id = leave_club_model.club_id or 0
        self.log_info("离开茶馆信息",uid,club_id)
        room = await self.check_in_room(CmdClub.LEAVE_CLUB, uid, club_id)
        if room:
            room.player_quit_club_room(uid)
            self.log_info("club_id", club_id, "玩家离开茶馆", uid)
            return await self.cs2ws_by_rmq(CmdClub.LEAVE_CLUB, uid)

    async def __club_notice(self,uid,data):
        notice = data.get("notice")
        club_id = data.get("id")
        room = await self.check_in_room(CmdClub.CLUB_NOTICE, uid, club_id)
        if room:
            data = {"notice":notice}
            data_model = S2CClubNotice.pb_model(**data)
            await room.inner_broadcast(CmdClub.CLUB_NOTICE, data_model)

    async def __room_info_change(self, _, data):
        """ 房间改变下发 """
        self.log_info("房间改变下发数据",data)
        club_id = data.get("club_id")
        room = self.get_room(club_id)
        if not room:
            return
        data_model = S2CClubRoomInfo.pb_mode(**data)
        await room.inner_broadcast(CmdClub.ROOM_INFO_CHANGE, data_model)
        self.log_info("club_id",club_id,"茶馆房间改变",data.get("msg_type"))

    async def __club_owner_dismiss(self, uid, data):
        """ 俱乐部主解散房间 """
        club_id = data.get("club_id")
        room = self.get_room(club_id)
        if not room:
            return
        if uid != room.owner:
            print("该玩家不是茶馆主",uid,room.owner)
            return
        room.clear_club()
        self.remove_room(club_id)
        self.log_info("club_id", club_id, "俱乐部主解散房间")

    async def __player_ready_except_owner(self,uid,data):
        club_id = data.get("club_id")
        room = await self.check_in_room(CmdClub.PLAYER_READY_EXCEPT_OWNER, uid, club_id)
        if not room:
            return
        if not room.check_player_in_club(uid):
            return

        return await self.cs2ws_by_rmq(CmdClub.PLAYER_READY_EXCEPT_OWNER, uid)

    async def check_in_room(self,cmd, uid, club_id):
        room = self.get_room(club_id)
        if not room:
            await self.cs2ws_by_rmq(cmd, uid, StaCode.FAIL, hint='茶馆不存在')
        elif not room.check_player_in_club(uid):
            await self.cs2ws_by_rmq(cmd, uid, StaCode.FAIL, hint='玩家未在茶馆服務')
            return None
        return room


    async def call_handler(self, cmd, uid, data):
        """
        uid: uid or ws
        注意顺序
        """
        func = self.cmd2func.get(cmd)
        if not func or not callable(func):
            return
        c_enum = CmdClub.find_member_by_val(cmd)
        check_inner = c_enum.desc == CallCheck.INNER
        if check_inner:
            data = self.check_inner_call(data)
            if not data:
                return
            data.pop("secret")
            return await func(uid, data) if asyncio.iscoroutinefunction(func) else func(uid, data)
        return await func(uid, data) if asyncio.iscoroutinefunction(func) else func(uid, data)


