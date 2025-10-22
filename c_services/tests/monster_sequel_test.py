import unittest
from c_services.cs_monster_sequel.rule import Rule
from c_services.cs_monster_sequel.poker import Cards


class RuleTest(unittest.TestCase):
    def test_contain(self):
        """ 包含 """
        cards = [Cards.FK_A, Cards.FK_A, Cards.FK_2]
        play_cards = [Cards.FK_2, Cards.FK_2]
        res = Rule.contain(cards, play_cards)
        self.assertFalse(res)

    def test_legal_action(self):
        """ 测试合法动作 """
        hand_cards = [Cards.FK_A, Cards.FK_5, Cards.FK_6, Cards.FK_7, Cards.FK_8]
        rival_move = [[1, [Cards.MH_J]]]
        res = Rule.get_legal_card_play_actions(rival_move, hand_cards)
        self.assertTrue(res == [[Cards.FK_5]])

        # 奔波儿霸与霸波儿奔组合接在任意单张牌
        hand_cards = [Cards.FK_A, Cards.FK_3, Cards.FK_5, Cards.FK_7, Cards.FK_8]
        rival_move = [[1, [Cards.MH_J]]]
        res = Rule.get_legal_card_play_actions(rival_move, hand_cards)
        self.assertTrue(res == [[Cards.FK_A, Cards.FK_3], [Cards.FK_5]])

        # 妖怪接师傅
        hand_cards = [Cards.FK_A, Cards.FK_3, Cards.FK_5, Cards.FK_7, Cards.FK_8]
        rival_move = [[1, [Cards.HX_A]]]
        res = Rule.get_legal_card_play_actions(rival_move, hand_cards)
        self.assertTrue(res == [[101, 103], [101], [103], [105], [107], [108]])

        # 师傅/师傅+小白龙 接徒弟
        hand_cards = [Cards.FK_A, Cards.FK_3, Cards.FK_5, Cards.HT_Q, Cards.HX_A]
        rival_move = [[1, [Cards.MH_10]]]
        res = Rule.get_legal_card_play_actions(rival_move, hand_cards)
        self.assertTrue(res == [[101, 103], [301, 412], [301], [412]])

        # 徒弟/妖怪/仙佛牌 接 接妖怪
        hand_cards = [Cards.FK_6, Cards.MH_9, Cards.MH_10, Cards.MH_J, Cards.HT_Q]
        rival_move = [[1, [Cards.FK_5]]]
        res = Rule.get_legal_card_play_actions(rival_move, hand_cards)
        self.assertTrue(res == [[106], [209], [210], [211], [412]])

        # 牛魔王接悟空
        hand_cards = [Cards.FK_5, Cards.MH_9, Cards.MH_10, Cards.MH_J, Cards.HT_A]
        rival_move = [[1, [Cards.MH_J]]]
        res = Rule.get_legal_card_play_actions(rival_move, hand_cards)
        self.assertTrue(res == [[105], [414]])

        # 金角银角 接 任意牌
        hand_cards = [Cards.FK_4, Cards.FK_4, Cards.FK_4, Cards.MH_J, Cards.HT_A]
        rival_move = [[1, [Cards.FK_A, Cards.FK_A, Cards.FK_A]]]
        res = Rule.get_legal_card_play_actions(rival_move, hand_cards)
        self.assertTrue(res == [[104, 104, 104], [414]])

        hand_cards = [Cards.FK_4, Cards.FK_4, Cards.MH_J, Cards.HT_A]
        rival_move = [[1, [Cards.FK_A, Cards.FK_3]]]  # 奔波儿霸 霸波儿奔
        res = Rule.get_legal_card_play_actions(rival_move, hand_cards)
        self.assertTrue(res == [[104], [211], [104, 104], [414]])

        # 上家打铁扇
        hand_cards = [Cards.FK_2, Cards.FK_5, Cards.FK_2, Cards.MH_9, Cards.FK_4]
        rival_move = [[1, [Cards.FK_6]]]  # 铁扇
        res = Rule.get_legal_card_play_actions(rival_move, hand_cards)
        self.assertTrue(res == [[209], [104]])

        # 测试悟空未出，六耳猕猴充当真悟空
        hand_cards = [Cards.FK_2, Cards.FK_5, Cards.FK_2, Cards.MH_9, Cards.FK_4]
        rival_move = [[1, [Cards.FK_5]]]  # 铁扇
        res = Rule.get_legal_card_play_actions(rival_move, hand_cards, False)
        self.assertTrue(res == [[209], [102], [104]])

        # 上家打铁扇
        hand_cards = [Cards.FK_8, Cards.FK_A, Cards.MH_J, Cards.FK_8, Cards.FK_3]
        rival_move = [[1, [Cards.FK_6]]]  # 铁扇
        res = Rule.get_legal_card_play_actions(rival_move, hand_cards)
        self.assertTrue(res == [[101, 103], [108], [211]])

        # 上家打六耳猕猴，但真悟空未出
        hand_cards = [Cards.MH_9, Cards.MH_10, Cards.MH_J, Cards.FK_7, Cards.FK_7]
        rival_move = [[1, [Cards.FK_2]]]  # 铁扇
        res = Rule.get_legal_card_play_actions(rival_move, hand_cards, False)
        self.assertTrue(res == [])

        # 上家唐僧，真悟空未出，六耳猕猴不能接唐僧
        hand_cards = [Cards.MH_9, Cards.MH_10, Cards.MH_J, Cards.FK_2, Cards.FK_7]
        # rival_move = [[1, [Cards.HX_A]]]  # 铁扇
        rival_move = [[1, [Cards.HX_A, Cards.HT_Q]]]  # 铁扇
        res = Rule.get_legal_card_play_actions(rival_move, hand_cards, False)
        self.assertTrue(res == [[107]])

        # 上家出六耳猕猴，真悟空未出，唐僧能接牌
        hand_cards = [Cards.MH_9, Cards.MH_10, Cards.MH_J, Cards.HX_A, Cards.FK_7]
        rival_move = [[1, [Cards.FK_2]]]
        res = Rule.get_legal_card_play_actions(rival_move, hand_cards, False)
        self.assertTrue(res == [[301]])

        # 上家出如来，下家当首出
        hand_cards = [Cards.MH_10, Cards.HT_Q, Cards.HX_A, Cards.FK_4, Cards.FK_6]
        rival_move = [[1, [Cards.HT_A]]]
        res = Rule.get_legal_card_play_actions(rival_move, hand_cards, False)
        self.assertTrue(res == [[301, 412], [210], [301], [104], [106], [412]])

        # 上家出金角，下家也能接金角
        hand_cards = [Cards.MH_10, Cards.HT_Q, Cards.HX_A, Cards.FK_4, Cards.FK_6]
        rival_move = [[1, [Cards.FK_4]]]
        res = Rule.get_legal_card_play_actions(rival_move, hand_cards, False)
        self.assertTrue(res == [[106], [210], [104], [412]])

        # 上家出沙僧，下家接金角
        hand_cards = [Cards.FK_3, Cards.FK_4, Cards.FK_5, Cards.FK_2, Cards.MH_9]
        rival_move = [[1, [Cards.MH_9]]]
        res = Rule.get_legal_card_play_actions(rival_move, hand_cards, )
        self.assertTrue(res == [[104]])

        # 上家出六耳猕猴，真悟空未打出，此时下家可接牛魔王
        hand_cards = [Cards.FK_3, Cards.FK_4, Cards.FK_5, Cards.FK_2, Cards.MH_9]
        rival_move = [[1, [Cards.FK_2]]]
        res = Rule.get_legal_card_play_actions(rival_move, hand_cards, wu_kong_played=False)
        self.assertTrue(res == [[104], [105]])

        # 上家出六耳猕猴，真悟空未打出，此时下家应该可用金角银角接
        hand_cards = [Cards.MH_J, Cards.FK_4, Cards.FK_4, Cards.HX_A, Cards.FK_8]
        rival_move = [[1, [Cards.FK_2, Cards.FK_2]]]
        res = Rule.get_legal_card_play_actions(rival_move, hand_cards, wu_kong_played=False)
        self.assertTrue(res == [[104, 104]])

        # 测试一张压了一对的问题
        hand_cards = [Cards.FK_3, Cards.HT_A, Cards.FK_2, Cards.FK_5, Cards.HT_Q]
        rival_move = [[1, [Cards.MH_9, Cards.MH_9]], [2, [Cards.HT_Q]]]
        res = Rule.get_legal_card_play_actions(rival_move, hand_cards, wu_kong_played=False)
        self.assertTrue(res == [[412], [414]])

        # 出牌顺序：六耳变的悟空—如来—小白龙/观音，提示玩家“收牌”
        hand_cards = [Cards.MH_10, Cards.HX_A, Cards.FK_A, Cards.HX_A, Cards.MH_9]
        rival_move = [[1, [Cards.FK_5, Cards.FK_5]], [2, [Cards.HT_A]], [3, [Cards.HT_K]]]
        res = Rule.get_legal_card_play_actions(rival_move, hand_cards, wu_kong_played=False)
        self.assertTrue(res == [[301, 301], [301], [210], [101], [209]])

        # 徒弟区仅有六耳变的悟空时，玩家无法打出唐僧+白龙马
        hand_cards = [Cards.HT_Q, Cards.HX_A, Cards.FK_5, Cards.FK_3, Cards.FK_A]
        rival_move = [[1, [Cards.FK_2]]]
        res = Rule.get_legal_card_play_actions(rival_move, hand_cards, wu_kong_played=False)
        res = Rule.sort_legal_cards(res)
        self.assertTrue(res == [[301], [105], [301, 412], [101, 103], [412]])

    def test_compare(self):
        # 多张仙佛牌接牌（不允许）
        hand_cards = [Cards.HT_Q, Cards.HT_Q, Cards.HT_Q]
        rival_move = [Cards.FK_A, Cards.FK_A, Cards.FK_A]
        res = Rule.compare(rival_move, hand_cards)
        self.assertFalse(res)

        # 单张仙佛牌接任何牌
        hand_cards = [Cards.HT_Q]
        rival_move = [Cards.FK_A, Cards.FK_A, Cards.FK_A]
        res = Rule.compare(rival_move, hand_cards)
        self.assertTrue(res)

        # 不同数量的大牌接小牌
        hand_cards = [Cards.MH_9, Cards.MH_9]
        rival_move = [Cards.FK_8, Cards.FK_8, Cards.FK_8]
        res = Rule.compare(rival_move, hand_cards)
        self.assertFalse(res)

        hand_cards = [Cards.MH_9, Cards.MH_9, Cards.MH_9]
        rival_move = [Cards.FK_8, Cards.FK_8]
        res = Rule.compare(rival_move, hand_cards)
        self.assertFalse(res)


if __name__ == '__main__':
    unittest.main()
