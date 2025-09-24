from enum import IntEnum

from common.public.base_enum import BaseEnum


class CardsSuit(BaseEnum):
    """ 牌花色 """
    DIAMONDS = 1, "方块"
    CLUBS = 2, "梅花"
    HEARTS = 3, "红心"
    SPADES = 4, "黑桃"


class BaseCard(IntEnum):
    def __new__(cls, card, suit, val):
        obj = int.__new__(cls, card)
        obj._value_ = card
        obj.suit = suit  # 花色
        obj.val = val  # 牌值
        return obj

    @classmethod
    def find_member_by_val(cls, value):
        """是否包含指定值"""
        return cls._value2member_map_.get(value)

    @classmethod
    def all_cards(cls,extra_count = 0):
        raise NotImplementedError

    @staticmethod
    def extra_cards():
        return []

    def __repr__(self):
        return f'{self.value}'
