import random
from typing import Dict, Set, List

from .const import MatchingMode, ExtensionType
from .player import Player
from nsanic.libs import tool_dt


class Session:
    """ 场次对象（场次等级） """

    def __init__(self, service, cs_type, level, s_conf: dict):
        self.__service = service
        self.__level = level
        self.__cs_type = cs_type
        self.__player_num = s_conf.get("rule_conf", {}).get("max_player", 0)
        self.__play_type = s_conf.get("play_type") or 1  # 玩法类型
        self.__max_expend_times = 2  # 最大扩展次数
        self.__players = set()
        self.__players_ranking_pool: Dict[int, Set] = {}  # 段位等级池 {r_level: [p1,p2...]}
        self.__extension_map = {
            1: ExtensionType.E1,
            2: ExtensionType.E2,
            3: ExtensionType.E3,
        }

    @property
    def level(self):
        return self.__level

    @property
    def cs_type(self):
        return self.__cs_type

    @property
    def player_num(self):
        return self.__player_num

    @property
    def play_type(self):
        return self.__play_type

    @property
    def wait_players(self):
        return self.__players

    @property
    def players_ranking_pool(self):
        return self.__players_ranking_pool

    def log_info(self, *data):
        self.__service.log_info(*data)

    def add_wait_player(self, p: Player, matching_mode: MatchingMode):
        """ 添加等待玩家 """
        if matching_mode in (MatchingMode.COMMON, MatchingMode.RAND_TIME):
            self.__players.add(p)
        else:
            self.__players_ranking_pool.setdefault(p.ranking_level, set()).add(p)

        p.max_wait_time = random.randint(3, 7)
        p.s_key = f"{self.cs_type}_{self.play_type}_{self.level}"
        self.log_info(p.uid, "玩家加入匹配队列", matching_mode, self.cs_type, self.level)

    def rm_wait_player(self, p, matching_mode):
        """ 移除等待玩家 """
        if matching_mode in (MatchingMode.COMMON, MatchingMode.RAND_TIME):
            self.__players.discard(p)
        else:
            self.__players_ranking_pool[p.ranking_level].discard(p)

    def __scan_meet_the_conditions(self):
        max_player = self.__player_num
        all_comb_players = []
        # 1.满足人数条件则收集起来
        if len(self.__players) >= max_player:
            player_list = list(self.__players)
            player_list.sort(key=lambda p: p.enter_time, reverse=True)  # 按匹配时间升序
            # while写到里面避免排序多次
            while len(player_list) >= max_player:
                ing_player_list = [player_list.pop() for _ in range(max_player)]
                self.__players.difference_update(ing_player_list)
                all_comb_players.append(ing_player_list)
        return all_comb_players

    def match_players_rand_time(self) -> List[list]:
        """ 普通匹配玩家 """
        all_comb_players = self.__scan_meet_the_conditions()

        # 2.人数不够时，设定一个匹配最大等待时常，如果时间到了都未凑满则立即匹配
        if self.__players:
            immediate_match = False
            cur_time = tool_dt.cur_time()
            for player in self.__players:
                if cur_time - player.enter_time >= player.max_wait_time:
                    print("player.max_wait_time",player.max_wait_time)
                    immediate_match = True
                    break
            if immediate_match:
                ing_player_list = [p for p in self.__players]
                self.__players.clear()
                all_comb_players.append(ing_player_list)

        return all_comb_players

    def match_players_common(self, max_wait=0) -> List[list]:
        """ 普通匹配玩家 """
        all_comb_players = self.__scan_meet_the_conditions()

        # 2.人数不够时，设定一个匹配最大等待时常，如果时间到了都未凑满则立即匹配
        if self.__players:
            immediate_match = False
            cur_time = tool_dt.cur_time()
            for player in self.__players:
                if cur_time - player.enter_time >= max_wait:
                    immediate_match = True
                    break
            if immediate_match:
                ing_player_list = [p for p in self.__players]
                self.__players.clear()
                all_comb_players.append(ing_player_list)

        return all_comb_players

    def match_players_by_rank(self) -> List[list]:
        """ 匹配玩家（根据修为） """
        max_player = self.__player_num
        all_comb_players = []
        # [(level, {p1, p2, p3})]
        wait_pool = sorted(self.__players_ranking_pool.items(), key=lambda d: d[0])
        # 1. 同段位池子中的玩家满足人数条件优先匹配
        for _, wait_players in wait_pool:
            player_list = list(wait_players)
            player_list.sort(key=lambda p: p.enter_time, reverse=True)  # 降序 enter_time越小的进入越早
            while len(player_list) >= max_player:
                ing_player_list = [player_list.pop() for _ in range(max_player)]
                wait_players.difference_update(ing_player_list)
                all_comb_players.append(ing_player_list)

        # 2.分类满足当前扩展层级时间阈值 玩家
        curr_time = tool_dt.cur_time()
        wait_pool_len = len(wait_pool) - 1
        for i, (r_level, wait_players) in enumerate(wait_pool):
            # 扩展次数
            for times in range(1, self.__max_expend_times + 1):
                mtc_players = []  # 满足条件的玩家 meet the conditions players
                # 扩展层级时间
                interval_time = (self.__service.match_search_extension_time
                                 .get(str(r_level))
                                 .get(self.__extension_map.get(times)))
                for player in wait_players:
                    if curr_time - player.enter_time > interval_time:
                        mtc_players.append((i, player))

                # 扩展层级
                for depth in range(1, times + 1):
                    # search depth +
                    s_depth_add = i + depth
                    if s_depth_add < wait_pool_len and r_level + depth == wait_pool[s_depth_add][0]:
                        for player in wait_pool[s_depth_add][1]:
                            if curr_time - player.enter_time >= interval_time:
                                mtc_players.append((s_depth_add, player))
                    # search depth -
                    s_depth_sub = i - depth
                    if s_depth_sub >= 0 and r_level - depth == wait_pool[s_depth_sub][0]:
                        for player in wait_pool[s_depth_sub][1]:
                            if curr_time - player.enter_time >= interval_time:
                                mtc_players.append((s_depth_sub, player))

                self.deal_match_data(mtc_players, max_player, all_comb_players, wait_pool)

        # 3.将匹配时间>=强制开始时间的凑到一桌（无视段位差距）
        force_players = []
        max_expand = self.__extension_map.get(max(self.__extension_map))
        for i, (r_level, wait_players) in enumerate(wait_pool):
            # 但凡有一人到了强制时间，都要完成匹配
            force_time = self.__service.match_search_extension_time.get(str(r_level)).get(max_expand)
            for player in wait_players:
                if curr_time - player.enter_time >= force_time:
                    force_players.append((i, player))

        self.deal_match_data(force_players, max_player, all_comb_players, wait_pool)

        # 4.如果3不足，则寻找时间最长的玩家与其凑一桌
        if force_players:
            # 先从队列池中移除强制匹配玩家
            self.__rm_player_from_wait_pool(force_players, wait_pool)

            residue_players = []
            for i, (r_level, wait_players) in enumerate(wait_pool):
                for player in wait_players:
                    residue_players.append((i, player))

            residue_players.sort(key=lambda p: p[1].enter_time, reverse=True)  # 降序 enter_time越小的进入越早
            for _ in range(max_player - len(force_players)):
                if not residue_players:
                    break
                force_players.append(residue_players.pop())

            self.deal_match_data(force_players, max_player, all_comb_players, wait_pool)

            # 5.最后仍然不足，则全部返回
            self.deal_match_data(force_players, len(force_players), all_comb_players, wait_pool)

        self.__players_ranking_pool = dict(wait_pool)
        return all_comb_players

    @staticmethod
    def deal_match_data(mtc_players, max_player, comb_players, wait_pool):
        """
        mtc_players: meet the conditions players(满足条件玩家)
        max_player: 最大玩家
        comb_players: 整合玩家列表
        wait_pool: 等待匹配池子
        """
        while mtc_players and len(mtc_players) >= max_player:
            ing_player_list = [mtc_players.pop() for _ in range(max_player)]
            Session.__rm_player_from_wait_pool(ing_player_list, wait_pool)
            ing_player_list = [p[1] for p in ing_player_list]
            comb_players.append(ing_player_list)

    @staticmethod
    def __rm_player_from_wait_pool(ing_player_list, wait_pool):
        for (idx, player) in ing_player_list:
            wait_pool[idx][1].discard(player)
