from c_services.base.base_leisure_player import BaseLeisurePlayer
from c_services.cs_landlords.const import DoubleType
from common.utils import earth_position


class Player(BaseLeisurePlayer):
    def __init__(self, uid, is_robot):
        super().__init__(uid, is_robot)
        self.__play_count = 0
        self.__self_multiple = 1  # 记录玩家自己的倍数
        self.__max_score = 0  # 最大得分
        self.__win_count = 0  # 赢局次数
        self.__bomb_count = 0  # 炸弹次数
        self.__round_bomb_count = 0  # 本局炸弹次数

        self.__is_qiang_guan = -1
        self.__x = earth_position.X_NA  # 玩家经度
        self.__y = earth_position.Y_NA  # 玩家纬度
        self.__bei_guan_count = 0 #被关次数
        self.__fan_guan_other = False  # 本局是否反关其他人
        self.__fan_guan = False  # 本局是否被反关
        self.__quan_guan = False  # 本局是否被全关
        self.__is_header = False  # 是否是头家出牌, 用来记录反关
        self.__dan_guan_count = 0  # 关笼次数
        self.__quan_guan_count = 0  # 全关次数
        self.__fan_guan_count = 0 # 反关次数
        self.__round_guan_count = 0
        self.__is_double = False
        self.__has_double = False # 是否操作了加倍
        self.__bomb_score = 0  # 炸弹得分
        self.__is_all_big = False #玩家是否全大
        self.__is_bao_pei = False # 是否被包赔
        self.__not_play_best = False # 是否没有出最大的牌

    @property
    def is_qiang_guan(self):
        return self.__is_qiang_guan

    @is_qiang_guan.setter
    def is_qiang_guan(self, is_qiang_guan: int):
        self.__is_qiang_guan = is_qiang_guan

    @property
    def is_double(self):
        return self.__is_double

    @is_double.setter
    def is_double(self, value: bool):
        self.__is_double = value

    @property
    def has_double(self):
        return self.__has_double

    @has_double.setter
    def has_double(self, value: bool):
        self.__has_double = value

    @property
    def is_header(self):
        return self.__is_header

    @is_header.setter
    def is_header(self, header):
        # 设置玩家是否头家出牌
        self.__is_header = header

    @property
    def play_count(self):
        return self.__play_count

    @property
    def win_count(self):
        return self.__win_count

    @property
    def max_score(self):
        return self.__max_score

    @max_score.setter
    def max_score(self, score):
        self.__max_score = score

    @property
    def quan_guan(self):
        return self.__quan_guan

    @quan_guan.setter
    def quan_guan(self, value: bool):
        self.__quan_guan = value

    @property
    def bomb_score(self):
        return self.__bomb_score

    @bomb_score.setter
    def bomb_score(self, score):
        self.__bomb_score += score

    @property
    def is_all_big(self):
        return self.__is_all_big

    @is_all_big.setter
    def is_all_big(self, value: bool):
        self.__is_all_big = value

    @property
    def is_bao_pei(self):
        return self.__is_bao_pei

    @is_bao_pei.setter
    def is_bao_pei(self, value: bool):
        self.__is_bao_pei = value

    @property
    def not_play_best(self):
        return self.__not_play_best

    @not_play_best.setter
    def not_play_best(self, value: bool):
        self.__not_play_best = value

    def on_round_over(self, score):
        """ 一局结束结算 """
        self.round_score = score

    def add_bei_guan_count(self, count=1):
        self.__bei_guan_count += count
        if self.__is_header and self.__play_count == 1:
            self.__fan_guan = True

    def add_dan_fan_guan_count(self, count=1, guan=1):
        if guan == 1:
            self.__dan_guan_count += count
        else:
            self.__fan_guan_count += count
            self.__fan_guan_other = True

        self.__round_guan_count += 1
        if self.__round_guan_count == 2:
            self.__quan_guan_count += 1


    def round_over_data(self):
        if self.__max_score < self.round_score:
            self.__max_score = self.round_score
        return {
            "seat_id": self.seat_id,
            "hand_cards": self.cards if not self.is_all_big else [],
            "round_score": self.round_score,
            "total_score": self.total_score,
            "quan_guan": self.__quan_guan,
            "fan_guan": self.__fan_guan,
            "round_bomb_count": self.__round_bomb_count,  # 本局炸弹次数
            "bao_pei": self.__is_bao_pei,
        }

    @property
    def game_over_data(self):
        return {
            "seat_id": self.seat_id,
            "uid": self.uid,
            "total_score": self.total_score,  # 总分
            "max_score": self.__max_score,  # 最大得分
            "win_count": self.__win_count,  # 赢局次数
            "bomb_count": self.__bomb_count,  # 炸弹次数
        }

    def add_bomb_count(self, count=1):
        self.__bomb_count += count
        self.__round_bomb_count += count

    def add_win_count(self, count=1):
        self.__win_count += count

    def player_info(self, contain_cards=True):
        p_info = super().player_info(contain_cards)
        p_info["is_ready"] = self.is_ready
        p_info["total_score"] = self.total_score
        p_info["has_double"] = self.__has_double
        p_info["has_qiang_guan"] = True if self.__is_qiang_guan == 1 else False
        return p_info

    def rm_cards(self, cards: list):
        super().rm_cards(cards)
        self.__play_count += 1

    def on_round_over_clear(self):
        """ 清理回合数据 """
        self.__play_count = 0
        self.__self_multiple = 1
        self.__is_double = False
        self.__quan_guan = False
        self.__fan_guan = False
        self.is_ready = False
        self.__is_qiang_guan = -1
        self.__has_double = False # 是否操作了加倍
        self.__is_header = False
        self.__bomb_score = 0
        self.__is_all_big = False
        self.__round_bomb_count = 0  # 本局炸弹次数
        self.__is_bao_pei = False # 是否被包赔
        self.__play_best_card = False # 是否出最大的牌

    def on_game_start_clear_data(self):
        """ 房间开始前的清理 """
        self.clear_game_data()

    def clear_data_round_over(self):
        super().clear_data_round_over()
        self.on_round_over_clear()

    def clear_game_data(self):
        self.__max_score = 0  # 最大得分
        self.__win_count = 0  # 赢局次数
        self.__bomb_count = 0  # 炸弹次数


    def clear_player(self):
        self.on_round_over_clear()
        self.clear_game_data()
        super().clear_player()
