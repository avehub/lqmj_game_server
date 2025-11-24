import asyncio


class ClubRoom:
    def __init__(self, club_id, owner, service):
        self.__club_id = club_id
        self.__service = service
        self.__members = set()
        self.__owner = owner

    @property
    def club_id(self):
        return self.__club_id

    @property
    def members(self):
        return self.__members

    @property
    def owner(self):
        return self.__owner

    def player_join_club_room(self, uid):
        self.__members.add(uid)

    def player_quit_club_room(self, uid):
        self.__members.discard(uid)

    def check_player_in_club(self, uid):
        return uid in self.__members

    def clear_club(self):
        self.__club_id = 0
        self.__service = 0
        self.__members.clear()
        self.__owner = 0

    async def inner_broadcast(self, c_code, data):
        """ 广播消息成员 """
        task_list = []
        for uid in self.__members:
            task_list.append(self.__service.cs2ws_by_rmq(c_code, uid, msg=data))
        if task_list:
            await asyncio.gather(*task_list)
