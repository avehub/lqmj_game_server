from c_services.base.base_poker import BasePoker
from c_services.const.base_card import BaseCard


class Cards(BaseCard):
    """ 牌对象 """
    # 万
    WAN_1 = 11, 1, 1
    WAN_2 = 12, 1, 2
    WAN_3 = 13, 1, 3
    WAN_4 = 14, 1, 4
    WAN_5 = 15, 1, 5
    WAN_6 = 16, 1, 6
    WAN_7 = 17, 1, 7
    WAN_8 = 18, 1, 8
    WAN_9 = 19, 1, 9

    # 条
    TIAO_1 = 21, 2, 1
    TIAO_2 = 22, 2, 2
    TIAO_3 = 23, 2, 3
    TIAO_4 = 24, 2, 4
    TIAO_5 = 25, 2, 5
    TIAO_6 = 26, 2, 6
    TIAO_7 = 27, 2, 7
    TIAO_8 = 28, 2, 8
    TIAO_9 = 29, 2, 9

    # 筒
    TONG_1 = 31, 3, 1
    TONG_2 = 32, 3, 2
    TONG_3 = 33, 3, 3
    TONG_4 = 34, 3, 4
    TONG_5 = 35, 3, 5
    TONG_6 = 36, 3, 6
    TONG_7 = 37, 3, 7
    TONG_8 = 38, 3, 8
    TONG_9 = 39, 3, 9

    @classmethod
    def all_cards(cls):
        all_member = list()
        for c in cls._member_map_.values():
            all_member.extend([c] * 4)
        return all_member


class Poker(BasePoker):
    CARDS_ENUM = Cards
    CARDS_NUM = 4

    def __init__(self,not_include=0):
        super().__init__(not_include)

    def deal_cards(self, player_count: int = 4, card_count: int = 13, extra_count=0):
        """
        子类需要实现发牌算法
        发牌总接口
        params: player_count 人数
        params: card_count 牌数
        params: extra_count 额外牌数
        """
        return super().deal_cards(player_count, card_count, extra_count)

    @staticmethod
    def cal_card_suit_count(cards):
        """ 计算同种花色出现的次数 """
        suits_to_count = {}
        for c in cards:
            c_suit = Poker.get_suit(c)
            suits_to_count[c_suit] = suits_to_count.get(c_suit, 0) + 1
        return suits_to_count

    @staticmethod
    def get_suit(card):
        return (card or 0) // 10

    @staticmethod
    def get_same_value_cards(cards: list):
        same_list = {}
        for card in cards:
            same_list.setdefault(card, []).append(card)
        return same_list