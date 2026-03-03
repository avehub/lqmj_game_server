from c_services.base.base_poker import BasePoker
from c_services.const.base_card import BaseCard


class Cards(BaseCard):
    """ 对象 """
    # 方块
    FK_3 = 103, 1, 3
    FK_5 = 105, 1, 5
    FK_8 = 108, 1, 8
    FK_10 = 110, 1, 10
    FK_J = 111, 1, 11
    FK_Q = 112, 1, 12
    FK_K = 113, 1, 13
    # 梅花
    MH_3 = 203, 2, 3
    MH_5 = 205, 2, 5
    MH_8 = 208, 2, 8
    MH_10 = 210, 2, 10
    MH_J = 211, 2, 11
    MH_Q = 212, 2, 12
    MH_K = 213, 2, 13
    # 红心
    HX_3 = 303, 3, 3
    HX_5 = 305, 3, 5
    HX_8 = 308, 3, 8
    HX_10 = 310, 3, 10
    HX_J = 311, 3, 11
    HX_Q = 312, 3, 12
    HX_K = 313, 3, 13
    # 黑桃
    HT_3 = 403, 4, 3
    HT_5 = 405, 4, 5
    HT_8 = 408, 4, 8
    HT_10 = 410, 4, 10
    HT_J = 411, 4, 11
    HT_Q = 412, 4, 12
    HT_K = 413, 4, 13
    # 万能牌
    UNIVERSAL_CARD = 520, 5, 20

    @classmethod
    def all_cards(cls):
        all_member = list(cls._member_map_.values())
        all_member.pop()
        return all_member

    @staticmethod
    def extra_cards():
        # return [Cards.UNIVERSAL_CARD for _ in range(4)]
        return []


class Poker(BasePoker):
    CARDS_ENUM = Cards

    def __init__(self):
        super().__init__()

    def deal_cards(self, player_count: int = 2, card_count: int = 8, extra_count=0):
        """
        子类需要实现发牌算法
        发牌总接口
        params: player_count 人数
        params: card_count 牌数
        params: extra_count 额外牌数
        """
        # 先发
        all_cards = super().deal_cards(player_count, card_count, extra_count)
        extra_cards = self.CARDS_ENUM.extra_cards()
        if extra_cards:
            for _ in range(1):
                for i, c in enumerate(extra_cards):
                    all_cards[i].append(c)
        return all_cards
