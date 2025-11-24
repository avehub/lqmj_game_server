import unittest
from c_services.cs_monster.poker import Poker


class PokerTest(unittest.TestCase):
    def test_deal_cards(self):
        """ 测试发牌 """
        poker = Poker()
        res = poker.deal_cards(4, 7)
        self.assertTrue(len(res) == 4)
        all_cards = []
        for cards in res:
            all_cards.extend(cards)
        self.assertTrue(len(all_cards) == 32)


if __name__ == '__main__':
    unittest.main()
