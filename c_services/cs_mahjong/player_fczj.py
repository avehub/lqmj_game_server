from copy import deepcopy

from c_services.cs_mahjong.player import Player


class PlayerFCZJ(Player):
    def __init__(self, uid, is_robot):
        super().__init__(uid, is_robot)
        self.__first_down = 0  # 第一次金币下到15倍
        self.__quan_count = 0  # 记录打了几圈
        self.__lucky_quan = 0
        self.__lian_sheng = 0  # 正为胜 负为败
        self.__record_account = []
        self.__fan_ji = 0
        self.is_lock = False
        self.__hua_zhu = 0
        self.__max_hu_type = 0
        self.__max_multiple = 0
        self.__hu_type_score = 0

    @property
    def first_down(self):
        return self.__first_down

    def add_first_down(self):
        self.__first_down += 1

    @property
    def quan_count(self):
        return self.__quan_count

    def add_quan_count(self):
        self.__quan_count += 1

    @property
    def lucky_quan(self):
        return self.__lucky_quan

    @lucky_quan.setter
    def lucky_quan(self, lucky_quan):
        self.__lucky_quan = lucky_quan

    @property
    def lian_sheng(self):
        return self.__lian_sheng

    @lian_sheng.setter
    def lian_sheng(self, lian_sheng):
        self.__lian_sheng = lian_sheng

    @property
    def fan_ji(self):
        return self.__fan_ji

    @fan_ji.setter
    def fan_ji(self, fan_ji):
        self.__fan_ji = fan_ji

    @property
    def hua_zhu(self):
        return self.__hua_zhu

    @hua_zhu.setter
    def hua_zhu(self, hua_zhu):
        self.__hua_zhu = hua_zhu

    @property
    def max_hu_type(self):
        return self.__max_hu_type

    @max_hu_type.setter
    def max_hu_type(self, max_hu_type):
        self.__max_hu_type = max_hu_type

    @property
    def max_multiple(self):
        return self.__max_multiple

    @max_multiple.setter
    def max_multiple(self, max_multiple):
        self.__max_multiple = max_multiple

    @property
    def hu_type_score(self):
        return self.__hu_type_score

    @hu_type_score.setter
    def hu_type_score(self, hu_type_score):
        self.__hu_type_score = hu_type_score

    def record_account(self, data, is_copy=True):
        """
        玩家记账
        [上家 下家 两家 三家]，最多三家
        """
        if is_copy:
            data = deepcopy(data)
        self.__record_account.append(data)

    def round_account(self):
        return self.__record_account

    def clear_account(self):
        self.__record_account = []

    def round_over_info(self):
        data = super().round_over_info()
        result = {
            "hand_cards": self.cards,
            "table_cards": self.get_table_cards(),
            "jiao_pai": self.jiao_pai,
            "fang_pao": self.fang_pao,
            "hu_type": self.hu_type,
            "ji_pai": self.ji_pai,
            "max_hu_type": self.__max_hu_type,
            "max_multiple": self.__max_multiple
        }
        data.update(result)
        return data

    @property
    def game_over_data(self):
        data = super().game_over_data
        result = {
            "max_hu_type": self.__max_hu_type,
            "max_multiple": self.__max_multiple
        }
        data.update(result)
        return data

    def player_info(self, contain_cards=True):
        p_info = super().player_info(contain_cards)
        p_info["is_out"] = self.is_out
        p_info["total_score"] = 0
        return p_info

    def clear_player(self):
        self.__first_down = 0
        self.__quan_count = 0
        self.__record_account = []
        self.__fan_ji = 0
        self.__hua_zhu = 0
        super().clear_player()
