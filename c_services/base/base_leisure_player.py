from common.utils.kit_async import DelayCall
from common.utils.utils import UtilsTool
from .base_player import BasePlayer
from c_services.cs_matching.player import Player


class BaseLeisurePlayer(BasePlayer, Player):
    """ 休闲玩法玩家 """

    def __init__(self, uid, is_robot):
        BasePlayer.__init__(self, uid, is_robot)
        Player.__init__(self, uid)
        self.__is_out: bool = False
        self.__gold = 0
        self.__diamond = 0
        self.__timer = None
        self.__ranking_score = 0  # 段位分
        self.__check_info_ranking = {}

        self.__skin_addition_num = 0  # 皮肤加成数量(金币)
        self.__multiple_card_addition_num = 0  # 多倍卡加成数量(金币)
        self.__free_loss_num = 0  # 免输数量（护盾卡）(金币)
        self.__ranking_score_free_num = 0  # 修为免输数量（固元丹）

        self.__actual_score = 0  # 实际赢分，非加成
        self.__is_win = 0  # 是输还是赢

    def __cancel_timer(self):
        if self.__timer:
            self.__timer.cancel()
            self.__timer = None

    @property
    def gold(self):
        return self.__gold

    @gold.setter
    def gold(self, gold):
        self.__gold = gold

    @property
    def diamond(self):
        return self.__diamond

    @property
    def ranking_score(self):
        return self.__ranking_score

    @ranking_score.setter
    def ranking_score(self, score):
        self.__ranking_score = score

    def call_flow(self, seconds, func, *params, **kwargs):
        self.__cancel_timer()
        self.__timer = DelayCall(seconds, func, *params, **kwargs)
        self.__timer.start()

    def cancel_timer(self):
        self.__cancel_timer()

    @property
    def is_out(self):
        return self.__is_out

    @is_out.setter
    def is_out(self, out: bool):
        self.__is_out = out

    @property
    def skin_addition_num(self):
        return self.__skin_addition_num

    @property
    def multiple_card_addition_num(self):
        return self.__multiple_card_addition_num

    @property
    def free_loss_num(self):
        return self.__free_loss_num

    @property
    def actual_score(self):
        return self.__actual_score

    def add_actual_score(self, score):
        self.__actual_score += score

    @property
    def is_win(self):
        return self.__is_win

    @is_win.setter
    def is_win(self, flag: int):
        self.__is_win = flag

    def init_player(self, u_info: dict):
        self.__gold = int(u_info.get("gold")) if u_info.get("gold") is not None else 0
        self.__diamond = u_info.get("diamond") or 0

    def update_gold(self, score: int, accumulate=True):
        """
        更新玩家金币
        accumulate: 是否累计在得分上
        """
        res_count = self.__gold + score
        if res_count < 0:
            score = -self.__gold
            self.__gold = 0
        else:
            self.__gold = res_count

        if accumulate:
            self.add_round_score(score)

    def update_diamond(self, score):
        res_count = self.__diamond + score
        if res_count < 0:
            self.__diamond = 0
        else:
            self.__diamond = res_count

    def round_over_info(self):
        return {
            "seat_id": self.seat_id,
            "win_gold": self.round_score,
            "res_gold": self.__gold,
            "is_win": self.__is_win
        }

    def check_info_ranking(self):
        ranking_info = {
            'r_score': self.__ranking_score,
            'win_streak_count': self.win_streak,
            **self.__check_info_ranking,
            'r_score_free_num': self.__ranking_score_free_num,
        }
        return ranking_info

    def set_check_info_ranking(self, session_addition, win_streak_addition, skin_addition=0):
        """ 排位结算信息 """
        self.__check_info_ranking = {
            "prop_card": UtilsTool.get_percent(self.ranking_addition * 100),
            "session": UtilsTool.get_percent(session_addition * 100),
            "win_streak": win_streak_addition,
            "vip": UtilsTool.get_percent(self.ranking_addition_vip * 100),
            "lifetime_card": UtilsTool.get_percent(self.ranking_addition_lifetime_card * 100),
            "skin": UtilsTool.get_percent(skin_addition * 100)
        }

    def add_skin_addition_num(self, num: int):
        self.__skin_addition_num += num
        self.update_gold(num)

    def add_multiple_card_addition_num(self, num: int):
        self.__multiple_card_addition_num += num

    def add_free_loss_num(self, num: int):
        self.__free_loss_num += num

    def add_ranking_score_free_num(self, num: int):
        self.__ranking_score_free_num += num

    def player_info(self,contain_cards = True):
        """ 玩家信息：子类必须实现 """
        data = super().player_info(contain_cards)
        data["gold"] = self.__gold
        return data

    def clear_player(self):
        """ 清理玩家 """
        self.__is_out: bool = False
        self.__gold = 0
        self.__timer = None
        self.__ranking_score = 0
        self.__check_info_ranking = {}

        self.__skin_addition_num = 0
        self.__multiple_card_addition_num = 0
        self.__free_loss_num = 0
        self.__ranking_score_free_num = 0

        self.__actual_score = 0
        self.__is_win = 0
        BasePlayer.clear_player(self)
        Player.clear_player(self)
