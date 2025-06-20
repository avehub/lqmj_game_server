from c_services.base.base_server import BaseServer
from c_services.const.cs_enum_const import CdmClub
from c_services.cs_club.room import ClubRoom
from common.public.enum_const import StaCode


class ClubServer(BaseServer):
    def __init__(self):
        super().__init__()
        self.add_handlers({
            CdmClub.ENTER_CLUB: self.__enter_club,
            CdmClub.QUIT_CLUB: self.__quit_club,
            CdmClub.ROOM_INFO_CHANGE: self.__room_info_change,
            CdmClub.CLUB_OWNER_DISMISS: self.__club_owner_dismiss,
        })

        self.__rooms = {}

    def get_room(self, cid):
        return self.__rooms.get(cid)

    def create_room(self, cid):
        room = ClubRoom(cid, self)
        self.__rooms[cid] = room
        return room

    def get_or_create_room(self, cid):
        return self.get_room(cid) or self.create_room(cid)

    async def __enter_club(self, uid, data):
        """ 进入 """
        club_id = data.get("club_id")

        # todo: 1.检验club_id 是否有对应茶馆
        # todo: 2.检验当前uid是否是club id下的茶馆成员
        room = self.get_or_create_room(club_id)
        room.player_join_room(uid)
        return await self.cs2ws_by_rmq(CdmClub.ENTER_CLUB, uid)

    async def __quit_club(self, uid, data):
        """ 退出 """
        club_id = data.get("club_id")
        room = self.get_room(club_id)
        if not room:
            return await self.cs2ws_by_rmq(CdmClub.QUIT_CLUB, uid, StaCode.FAIL)
        room.player_quit_room(uid)
        self.log_info(uid, "退出俱乐部", club_id)
        return await self.cs2ws_by_rmq(CdmClub.QUIT_CLUB, uid)

    async def __room_info_change(self, _, data):
        """ 房间改变下发 """
        club_id = data.get("club_id")
        room = self.get_room(club_id)
        if not room:
            return
        await room.inner_broadcast(CdmClub.ROOM_INFO_CHANGE, data)

    async def __club_owner_dismiss(self, uid, data):
        """ 俱乐部主解散房间 """

