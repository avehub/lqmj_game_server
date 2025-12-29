import asyncio

from common.public.conf import R_UID_THRESHOLD


class CompetitionRoom:
    def __init__(self, match_room_id, service):
        self.__match_room_id = match_room_id
        self.__service = service
        self.__members = set()
        self.__player_scores = {}
        self.__finish_room_count = 0
        self.__max_player = 0
        self.__max_match_player = 0
        self.__game_room_count = 0
        self.__cs_type = 0
        self.__match_round = 1
        self.__total_match_round = 4
        self.__competition_id = 0
        self.__game_room_info = {}

    @property
    def match_room_id(self):
        return self.__match_room_id

    @property
    def members(self):
        return self.__members

    @property
    def finish_room_count(self):
        return self.__finish_room_count

    @finish_room_count.setter
    def finish_room_count(self, finish_room_count):
        self.__finish_room_count = finish_room_count

    @property
    def max_player(self):
        return self.__max_player

    @max_player.setter
    def max_player(self, max_player):
        self.__max_player = max_player

    @property
    def max_match_player(self):
        return self.__max_match_player

    @max_match_player.setter
    def max_match_player(self, max_match_player):
        self.__max_match_player = max_match_player

    @property
    def game_room_count(self):
        return self.__max_match_player // self.__max_player

    @property
    def cs_type(self):
        return self.__cs_type

    @cs_type.setter
    def cs_type(self, cs_type):
        self.__cs_type = cs_type

    @property
    def match_round(self):
        return self.__match_round

    def add_match_round(self):
        self.__match_round += 1

    @property
    def total_match_round(self):
        return self.__total_match_round

    @total_match_round.setter
    def total_match_round(self, total_match_round):
        self.__total_match_round = total_match_round

    @property
    def competition_id(self):
        return self.__competition_id

    @competition_id.setter
    def competition_id(self, competition_id):
        self.__competition_id = competition_id

    @property
    def game_room_info(self):
        return self.__game_room_info

    def set_game_room_info(self, room_id, info):
        self.__game_room_info[room_id] = info

    def player_join_competition_room(self, uid, score = 0):
        self.__members.add(uid)
        self.__player_scores[uid] = score

    def player_quit_competition_room(self, uid):
        self.__members.discard(uid)
        if uid in self.__player_scores:
            del self.__player_scores[uid]

    def check_player_in_competition(self, uid):
        return uid in self.__members

    def sort_players_by_score(self):
        sorted_players = sorted(self.__members,
                                key=lambda uid: (-self.__player_scores.get(uid, 0), uid))
        return sorted_players

    def get_rank_by_score(self):
        sorted_list = sorted(self.__player_scores.items(),
                             key=lambda x: x[1],
                             reverse=True)

        # 生成带名次的排名列表
        ranked_players = []
        for rank, (uid, score) in enumerate(sorted_list, start=1):
            ranked_players.append((rank, uid, score))
        return ranked_players

    def add_finish_room_count(self):
        self.__finish_room_count += 1

    def update_player_score(self, uid, score):
        self.__player_scores[uid] = score

    def get_player_score(self, uid):
        return self.__player_scores.get(uid, 0)

    def get_players_by_score(self):
        sorted_players = self.sort_players_by_score()
        groups = [sorted_players[i:i + self.__max_player] for i in range(0, len(sorted_players), self.__max_player)]

        return groups

    def clear_competition(self):
        self.__service = 0
        self.__members.clear()
        self.__player_scores.clear()
        self.__finish_room_count = 0
        self.__match_round = 1
        self.__competition_id = 0
        self.__max_player = 0
        self.__max_match_player = 0
        self.__game_room_count = 0
        self.__cs_type = 0
        self.__total_match_round = 4
        self.__game_room_info.clear()

    async def inner_broadcast(self, c_code, data):
        """ 广播消息成员 """
        task_list = []
        for uid in self.__members:
            if uid > R_UID_THRESHOLD:
                task_list.append(self.__service.cs2ws_by_rmq(c_code, uid, msg=data))
        if task_list:
            await asyncio.gather(*task_list)
