"""
基础休闲场玩家类
"""


class BasePlayer():
    """ 休闲场基础玩家 """

    def __init__(self, uid, is_robot=False):
        self.__uid = uid
        self.__is_robot = is_robot
        self.__trustee: bool = False  # 是否为托管者
        self.__cards = []
        self.__seat_id = -1  # 座位号
        self.__offline = False
        self.__tid = 0
        self.__ws_id = 0  # 玩家连接上的ws进程id
        self.__round_score = 0  # 每小局得分
        self.__total_score = 0  # 目前为止总得分
        self.__operand = 0  # 记录玩家操作数

    @property
    def uid(self):
        return self.__uid

    @property
    def is_robot(self):
        return self.__is_robot

    @property
    def trustee(self):
        return self.__trustee

    @trustee.setter
    def trustee(self, flag: bool):
        self.__trustee = flag

    @property
    def seat_id(self):
        return self.__seat_id

    @seat_id.setter
    def seat_id(self, seat_id):
        self.__seat_id = seat_id + 1

    @property
    def offline(self):
        return self.__offline

    @offline.setter
    def offline(self, flag: bool):
        self.__offline = flag

    @property
    def tid(self):
        return self.__tid

    @tid.setter
    def tid(self, tid):
        self.__tid = tid

    @property
    def ws_id(self):
        return self.__ws_id

    @ws_id.setter
    def ws_id(self, _id):
        self.__ws_id = int(_id or 0)

    @property
    def round_score(self):
        return self.__round_score

    @property
    def total_score(self):
        return self.__total_score

    @round_score.setter
    def round_score(self, score):
        self.__round_score = score
        self.__total_score += score

    def add_round_score(self, score):
        """ 增加每局得分 """
        self.__round_score += score
        self.__total_score += score

    @property
    def cards(self):
        return self.__cards

    @cards.setter
    def cards(self, cards):
        self.__cards = cards

    @property
    def operand(self):
        return self.__operand

    def add_operand(self):
        self.__operand += 1

    def clear_operand(self):
        self.__operand = 0

    def rev_card(self, card):
        self.__cards.append(card)

    def rm_cards(self, cards: list):
        for c in cards:
            self.__cards.remove(c)

    def ex_cards(self,card,idx):
        self.__cards[idx] = card

    def sort_cards(self):
        self.__cards.sort()

    @property
    def cards_len(self):
        return len(self.__cards)

    def player_info(self,contain_cards = True):
        """ 玩家信息：子类必须实现 """
        data = {
            "uid": self.__uid,
            "seat_id": self.__seat_id,
            "is_trustee": self.__trustee,
            "offline": self.__offline,
            # "cards": self.__cards,
            "round_score": self.__round_score,
            "cards_len": self.cards_len,
            # "gold": self.__gold,
        }
        if contain_cards:
            data["cards"] = self.__cards
        return data

    def clear_data_round_over(self):
        """ 小局清理 """
        self.__trustee: bool = False  # 是否为托管者
        self.__offline = False
        self.__cards = []

    def clear_player(self):
        """ 清理玩家 """
        self.__uid = 0
        self.__is_robot = False
        self.__trustee: bool = False  # 是否为托管者
        self.__cards.clear()
        self.__seat_id = -1  # 座位号
        self.__offline = False
        self.__tid = 0
        self.__ws_id = 0  # 玩家连接上的ws进程id
        self.__round_score = 0  # 每小局得分
        self.__total_score = 0  # 目前为止总得分
        self.__operand = 0  # 操作数

    def refresh_player(self, uid, is_robot):
        """ 刷新玩家 """
        self.__uid = uid
        self.__is_robot = is_robot
