import unittest
from c_services.cs_mahjong.rule import Rule


class RuleTest(unittest.TestCase):
    def test_can_hu(self):
        cards = [12, 13, 13, 14, 14, 14, 15, 15, 16, 28, 28]
        res, hu_path = Rule.can_hu_without_lai_zi(cards, 0)
        self.assertTrue(res)

        cards = [12, 13, 13, 14, 14, 15, 15, 16, 19, 28, 28]
        res, hu_path = Rule.can_hu_without_lai_zi(cards, 0)
        self.assertFalse(res)

        flag, new_list, new_hz_count, new_hz_change_value = Rule.check_value_is_valid_with_lai_zi(
            [3, 9], [[False, False, 0, {}, []]], 0, 2,
        )

        # 5癞子
        cards = [31, 31, 31, 31, 32, 33, 34, 35, 36, 37, 37, 38, 39, 31]
        res = Rule.can_hu_with_five_lai_zi(cards, 31)
        self.assertTrue(res)

    def test_ting_hu_list(self):
        """ 测试手牌胡牌叫哪些牌 """
        cards = [11, 11, 11, 12, 13, 14, 15, 16, 17, 18, 19, 19, 19]
        res = Rule.get_ting_hu_list([], cards, {})
        self.assertTrue(res)


if __name__ == '__main__':
    unittest.main()
