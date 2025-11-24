import itertools
import unittest
from c_services.cs_water_fish.poker import Poker
from c_services.cs_water_fish.rule import Rule


class RuleTest(unittest.TestCase):
    def test_sort(self):
        """ 测试排序 """
        all_cards = Poker().cards
        all_comb = [list(comb) for comb in itertools.combinations(all_cards, 2)]
        Rule.merge_sort(all_comb, 0, len(all_comb) - 1)
        print("123", all_comb)


if __name__ == '__main__':
    unittest.main()
