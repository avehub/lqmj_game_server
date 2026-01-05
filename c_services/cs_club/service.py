import asyncio

from c_services.base.base_server import BaseServer
from c_services.const.cs_enum_const import CmdClub, CallCheck, ClubMsgType, CmdRoom, CmdFanOut
from c_services.cs_club.room import ClubRoom
from common.proto.py_pb2.ws_c2s import leave_club_model, club_room_set_model
from common.proto.py_pb2.ws_leisure import S2CClubRoomInfo, S2CClubNotice, S2CClubRoomSetInfo, S2CCheckInGame, one_of_model
from common.public.conf import C_SERVICE_SECRET_KEY
from common.public.enum_const import StaCode, ServiceEnum, CacheKey, Channel
from lucky_game.model_rc.base_clubs import BaseClubRC


class ClubServer(BaseServer):

    # SUBSCRIBE_FANOUT = Channel.C_SERVICES_COMMON

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
            CmdClub.UPDATE_ROOM_SET:self.__update_room_set,
            CmdClub.CHECK_GAME_STATUS:self.__check_game_status,
            CmdClub.JOIN_NEW_GAME:self.__join_new_game,
            CmdClub.JOIN_NEW_GAME_SUC:self.__join_new_game_suc,
            CmdFanOut.LOST_CONNECT:self.__lost_connect,
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
        self.log_info("进入茶馆信息",uid,data)
        club_id = data.get("club_id")
        owner = data.get("club_uid")
        # todo: 1.检验club_id 是否有对应茶馆
        if club_id <= 0:
            return await self.cs2ws_by_rmq(CmdClub.ENTER_CLUB, uid, StaCode.FAIL, "茶馆id有误")
        room = self.get_or_create_room(club_id, owner)
        if uid in room.members:
            return await self.cs2ws_by_rmq(CmdClub.ENTER_CLUB, uid, StaCode.FAIL, "玩家已在茶馆")
        # todo: 2.检验当前uid是否是club id下的茶馆成员
        if uid <= 0:
            return await self.cs2ws_by_rmq(CmdClub.ENTER_CLUB, uid, StaCode.FAIL, "玩家uid有误")
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

    async def __update_room_set(self,uid,data):

        club_room_set_model.ParseFromString(data)
        club_id = club_room_set_model.club_id or 0
        rank_members_only = club_room_set_model.rank_members_only or 0
        self.log_info("收到房间设置更新",uid,club_id,rank_members_only)
        room = await self.check_in_room(CmdClub.LEAVE_CLUB, uid, club_id)
        if room:
            await BaseClubRC.update_club(club_id, record_status=rank_members_only)
            set_data = {"rank_members_only":rank_members_only}
            data_model = S2CClubRoomSetInfo.pb_model(**set_data)
            await room.inner_broadcast(CmdClub.UPDATE_ROOM_SET, data_model)

    async def __check_game_status(self,uid,data):
        one_of_model.ParseFromString(data)
        req_id = one_of_model.req_id
        info = await self.get_play_in_game(uid)
        game_status = info.get("game_status", 0) if info else 0
        is_owner = info and info.get("owner") == uid if info else False
        room_id = info.get("room_id", 0) if info else 0
        data = {
            "game_status": game_status,
            "room_id": room_id,
            "is_owner": is_owner
        }
        data_model = S2CCheckInGame.pb_model(**data)
        await self.cs2ws_by_rmq(CmdClub.CHECK_GAME_STATUS, uid,msg=data_model,req_id = req_id)

    async def get_play_in_game(self, uid):
        try:
            info = await self.conf.rds.get_hash(CacheKey.PLAYER_GAME_STA, uid, jsparse=True)
        except Exception as e:
            info = {}
        return info

    async def __join_new_game(self,uid,data):
        one_of_model.ParseFromString(data)
        req_id = one_of_model.req_id
        info = await self.get_play_in_game(uid)
        if info:
            creator = info.get("owner")
            cs_type = info.get("cs_type")
            info["secret"] = C_SERVICE_SECRET_KEY
            info["uid"] = uid
            info["req_id"] = req_id
            info["from_club"] = True
            c_enum = ServiceEnum.find_member_by_val(cs_type)
            if creator != uid:
                await self.cs2cs_by_rmq(c_enum, CmdRoom.CLUB_QUIT_ROOM,info , uid )
            else:
                await self.cs2cs_by_rmq(c_enum, CmdRoom.CLUB_OWNER_DISMISS, info)

    async def __join_new_game_suc(self,uid,data):
        req_id = data.get("req_id")
        await self.cs2ws_by_rmq(CmdClub.JOIN_NEW_GAME, uid ,req_id = req_id)

    async def __lost_connect(self,uid,_):
        self.log_info("玩家掉线",uid)
        for club_id, room in self.__rooms.items():
            if room.check_player_in_club(uid):
                room.player_quit_club_room(uid)
                self.log_info("club_id", club_id, "玩家离开茶馆", uid)
                return await self.cs2ws_by_rmq(CmdClub.LEAVE_CLUB, uid)

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
        self.log_info("club_id", club_id, "uid",uid,"俱乐部主解散房间")

    async def __player_ready_except_owner(self,uid,data):
        club_id = data.get("club_id")
        room = await self.check_in_room(CmdClub.PLAYER_READY_EXCEPT_OWNER, uid, club_id)
        if not room:
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
        if not c_enum:
            c_enum = CmdFanOut.find_member_by_val(cmd)
        check_inner = c_enum.desc == CallCheck.INNER
        if check_inner:
            data = self.check_inner_call(data)
            if not data:
                return
            data.pop("secret")
            return await func(uid, data) if asyncio.iscoroutinefunction(func) else func(uid, data)
        return await func(uid, data) if asyncio.iscoroutinefunction(func) else func(uid, data)


