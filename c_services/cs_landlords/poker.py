from c_services.base.base_poker import BasePoker
from c_services.const.base_card import BaseCard


class Cards(BaseCard):
    """ 牌对象 """
    # 方块
    FK_3 = 103, 1, 3
    FK_4 = 104, 1, 4
    FK_5 = 105, 1, 5
    FK_6 = 106, 1, 6
    FK_7 = 107, 1, 7
    FK_8 = 108, 1, 8
    FK_9 = 109, 1, 9
    FK_10 = 110, 1, 10
    FK_J = 111, 1, 11
    FK_Q = 112, 1, 12
    FK_K = 113, 1, 13
    FK_A = 114, 1, 14
    FK_2 = 116, 1, 16

    # 梅花
    MH_3 = 203, 2, 3
    MH_4 = 204, 2, 4
    MH_5 = 205, 2, 5
    MH_6 = 206, 2, 6
    MH_7 = 207, 2, 7
    MH_8 = 208, 2, 8
    MH_9 = 209, 2, 9
    MH_10 = 210, 2, 10
    MH_J = 211, 2, 11
    MH_Q = 212, 2, 12
    MH_K = 213, 2, 13
    MH_A = 214, 2, 14
    MH_2 = 216, 2, 16

    # 红心
    HX_3 = 303, 3, 3
    HX_4 = 304, 3, 4
    HX_5 = 305, 3, 5
    HX_6 = 306, 3, 6
    HX_7 = 307, 3, 7
    HX_8 = 308, 3, 8
    HX_9 = 309, 3, 9
    HX_10 = 310, 3, 10
    HX_J = 311, 3, 11
    HX_Q = 312, 3, 12
    HX_K = 313, 3, 13
    HX_A = 314, 3, 14
    HX_2 = 316, 3, 16

    # 黑桃
    HT_3 = 403, 4, 3
    HT_4 = 404, 4, 4
    HT_5 = 405, 4, 5
    HT_6 = 406, 4, 6
    HT_7 = 407, 4, 7
    HT_8 = 408, 4, 8
    HT_9 = 409, 4, 9
    HT_10 = 410, 4, 10
    HT_J = 411, 4, 11
    HT_Q = 412, 4, 12
    HT_K = 413, 4, 13
    HT_A = 414, 4, 14
    HT_2 = 416, 4, 16

    # 大小王
    S_KING = 518, 5, 18
    B_KING = 520, 5, 20

    @classmethod
    def all_cards(cls):
        all_member = list(cls._member_map_.values())
        return all_member


class Poker(BasePoker):
    CARDS_ENUM = Cards

    def __init__(self):
        super().__init__()

    def deal_cards(self, player_count: int = 3, card_count: int = 17, extra_count=0):
        """
        子类需要实现发牌算法
        发牌总接口
        params: player_count 人数
        params: card_count 牌数
        params: extra_count 额外牌数
        """
        return super().deal_cards(player_count, card_count, extra_count)
