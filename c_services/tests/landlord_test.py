import unittest
from c_services.cs_landlords.rule import Rule
from c_services.cs_landlords.poker import Cards, Poker


class RuleTest(unittest.TestCase):
    ALLOW_ACT = {
        "1": 1, "2": 1, "3": 1, "4": 1, "5": 1, "6": 1, "7": 1, "8": 1, "9": 1, "10": 1, "11": 1, "12": 1,
        "13": 1, "14": 1, "15": 0
    }

    def test_moves(self):
        """ 测试动作 """
        cards = [3, 4, 5, 6, 7, 12, 12, 12, 12, 14, 16]
        cards_dict = Rule.get_cards_count_dict(cards)
        res = Rule.gen_moves(cards, cards_dict, RuleTest.ALLOW_ACT)
        # print(res)
        self.assertTrue(res)

    def test_legal_move(self):
        last_action = [[Cards.FK_J, Cards.MH_J, Cards.HX_J, Cards.FK_3]]
        cards = [Cards.FK_3, Cards.FK_4, Cards.FK_5, Cards.FK_6, Cards.FK_7, Cards.FK_Q, Cards.MH_Q, Cards.HX_Q,
                 Cards.FK_A]
        res = Rule.get_legal_card_play_actions(cards, last_action, RuleTest.ALLOW_ACT)
        print(res)
        self.assertTrue(res)

        last_action = [[Cards.HT_10, Cards.MH_10, Cards.HT_J, Cards.MH_J, Cards.FK_J], [], []]
        cards = [Cards.FK_3, Cards.FK_4, Cards.FK_5, Cards.FK_6, Cards.FK_7, Cards.FK_Q, Cards.MH_Q, Cards.HX_Q,
                 Cards.FK_A]
        res = Rule.get_legal_card_play_actions(cards, last_action, RuleTest.ALLOW_ACT)
        print(res)
        self.assertTrue(res)

    def test_get_cards_by_val(self):
        """ 测试通过牌值获取牌 """
        cards = [Cards.FK_A, Cards.MH_A, Cards.FK_3, Cards.HX_3]
        res = Rule.get_cards_by_val_list(cards, [[14, 14, 3], [3, 3, 3]])
        print(res)
        self.assertTrue(res)

    def test_sort(self):
        cards = [Cards.MH_Q, Cards.HX_Q, Cards.HT_8, Cards.HT_Q]
        cards.sort(key=Rule.sort_rule)
        self.assertTrue(cards == [Cards.HT_7, Cards.HT_8, Cards.HT_9, Cards.MH_10, Cards.MH_J])

    def test_one_hand_play_out(self):
        """ 测试最后一手是否能出 """
        cards = [103, 304, 405, 306, 207, 408, 109, 210, 411, 212, 113]
        cards = [Cards.find_member_by_val(c) for c in cards]
        res = Rule.one_hand_play_out(cards, RuleTest.ALLOW_ACT)
        self.assertTrue(res)

    def test_set_cards(self):
        """ 测试设牌 """
        cards = [
            [214, 518, 408, 405, 212, 109, 103, 211, 414, 306, 314, 216, 210, 411, 304, 113, 207],
            [410, 110, 316, 305, 412, 204, 111, 404, 308, 203, 403, 407, 105, 406, 310, 106, 104],
            [107, 213, 114, 209, 313, 307, 303, 112, 520, 108, 416, 413, 116, 208, 206, 309, 205],
            []
        ]
        poker = Poker()
        poker.set_order_cards(cards)
        all_cards = poker.deal_cards(3)
        self.assertTrue(all_cards)


if __name__ == '__main__':
    unittest.main()
