from typing import List

from c_services.const.base_card import BaseCard
from common.utils.meta_class import NoInstances


class BaseRule(metaclass=NoInstances):
    """
    基类规则
    """

    @staticmethod
    def stat_card_count(cards: list):
        card2count = {}
        for c in cards:
            card2count[c] = card2count.get(c, 0) + 1
        return card2count

    @staticmethod
    def contain(cards: List[BaseCard], play_cards: List[int]):
        for pc in play_cards:
            if pc not in cards:
                return False
        return True

    @staticmethod
    def sort_rule(card: BaseCard):
        return card.val, card.suit
