from c_services.base.base_poker import BasePoker
from c_services.const.base_card import BaseCard
from common.public.base_enum import BaseEnum
from enum import unique

from common.utils.meta_class import with_meta


@unique
class Cards(BaseCard):
    """ 对象 """
    # 方块（妖怪牌）
    FK_A = 101, 1, 1  # 奔波儿霸
    FK_2 = 102, 1, 2  # 六耳猕猴
    FK_3 = 103, 1, 3  # 霸波儿奔
    FK_4 = 104, 1, 4  # 金角银角
    FK_5 = 105, 1, 5  # 牛魔王
    FK_6 = 106, 1, 6  # 铁扇公主
    FK_7 = 107, 1, 7  # 红孩儿
    FK_8 = 108, 1, 8  # 金翅大鹏

    # 梅花（徒弟牌）
    MH_9 = 209, 2, 9  # 沙僧
    MH_10 = 210, 2, 10  # 八戒
    MH_J = 211, 2, 11  # 悟空

    # 红心（师傅牌）
    HX_A = 301, 3, 1  # 师傅

    # 黑桃（神仙牌）
    HT_Q = 412, 4, 12  # 白龙马
    HT_K = 413, 4, 13  # 观音
    HT_A = 414, 4, 14  # 如来

    @classmethod
    def all_cards(cls):
        cards = []
        for c in cls:
            c_num = CardsNum.find_member_by_val(c.value)
            cards.extend([c] * c_num.phrase)
        return cards


class CardsNum(BaseEnum):
    """ 牌数量控制 """
    # 方块（妖怪牌）
    FK_A = 101, 6
    FK_2 = 102, 6
    FK_3 = 103, 6
    FK_4 = 104, 6
    FK_5 = 105, 6
    FK_6 = 106, 6
    FK_7 = 107, 6
    FK_8 = 108, 6

    # 梅花（徒弟牌）
    MH_9 = 209, 6
    MH_10 = 210, 6
    MH_J = 211, 6

    # 红心（师傅牌）
    HX_3 = 301, 6

    # 黑桃（神仙牌）
    HT_Q = 412, 4
    HT_K = 413, 3
    HT_A = 414, 2


Poker = with_meta(type, BasePoker)
Poker.CARDS_ENUM = Cards

if __name__ == '__main__':
    poker = Poker()
    cards = poker.deal_cards(3, 5)
    print(cards)
    for i in range(68):
        print(poker.pop())
