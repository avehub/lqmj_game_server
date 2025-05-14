from c_services.base.base_leisure_player import BaseLeisurePlayer
from c_services.cs_landlords.const import DoubleType


class Player(BaseLeisurePlayer):
    def __init__(self, uid, is_robot):
        super().__init__(uid, is_robot)
        self.__bid_score = -1
        self.__play_count = 0
        self.__self_multiple = 1  # 记录玩家自己的倍数
        self.__has_doubled: bool = False

    @property
    def bid_score(self):
        return self.__bid_score

    @bid_score.setter
    def bid_score(self, bs: int):
        self.__bid_score = bs

    @property
    def play_count(self):
        return self.__play_count

    @property
    def self_multiple(self):
        return self.__self_multiple

    def do_double(self):
        """ 加倍 """
        self.__self_multiple *= 2

    @property
    def has_doubled(self):
        return self.__has_doubled

    @has_doubled.setter
    def has_doubled(self, is_do: bool):
        self.__has_doubled = is_do

    @property
    def double_type(self):
        """ 加倍类型 """
        if not self.__has_doubled:
            return DoubleType.DOUBLE_DFT
        if self.__self_multiple == 1:
            return DoubleType.DONE_NO_DOUBLE
        return DoubleType.DONE_REDOUBLE

    def rm_cards(self, cards: list):
        super().rm_cards(cards)
        self.__play_count += 1

    def clear_round_data(self):
        """ 清理回合数据 """
        self.__play_count = 0
