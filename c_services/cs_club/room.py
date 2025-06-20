import asyncio


class ClubRoom():
    def __init__(self, club_id, service):
        self.__club_id = club_id
        self.__service = service
        self.__members = set()

    @property
    def club_id(self):
        return self.__club_id

    @property
    def members(self):
        return self.__members

    def player_join_room(self, uid):
        self.__members.add(uid)

    def player_quit_room(self, uid):
        self.__members.discard(uid)

    async def inner_broadcast(self, c_code, data):
        """ 广播消息成员 """
        task_list = []
        for uid in self.__members:
            task_list.append(self.__service.cs2ws_by_rmq(c_code, uid, msg=data))
        if task_list:
            await asyncio.gather(*task_list)
