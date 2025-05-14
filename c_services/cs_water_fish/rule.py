from .poker import Cards
from .const import CardsType
from typing import List
from ..base.base_rule import BaseRule


class Rule(BaseRule):
    """ 规则类：不能用实例化 """
    @staticmethod
    def is_different_cards(cards1: List[int], cards2: List[Cards]):
        # cards2 = [card.value for card in cards2]
        return set(cards1).difference(cards2)

    @staticmethod
    def cards_type(cards: list[Cards]) -> int:
        val_to_count = Rule.get_val_to_count_by_cards(cards)
        val_count_len = len(val_to_count)
        if val_count_len == 1:
            return CardsType.SHUI_YU_TX.val
        elif val_count_len == 2:
            return CardsType.SHUI_YU.val
        elif val_count_len == 3:
            return CardsType.PAIR.val
        return CardsType.SAN_PAI.val

    @staticmethod
    def get_val_to_count_by_cards(cards: list[Cards]):
        """ 获取牌值count """
        val_to_count = {}
        for c in cards:
            val_to_count[c.val] = val_to_count.get(c.val, 0) + 1
        return val_to_count

    @staticmethod
    def extract_cards_val(cards: list[Cards]):
        """ 提取牌值 """
        c_val = []
        for c in cards:
            val = c.val
            if c.val > 10:
                val = val % 10 / 10
            c_val.append(val)
        return c_val

    @staticmethod
    def compare_one(cards1: list[Cards], cards2: list[Cards]) -> bool:
        """
        只比较一铺, 储存Card对象的list切片不会再拷贝Card对象
        进行比较的单铺
        """
        cards1.sort(key=Rule.sort_rule)
        cards2.sort(key=Rule.sort_rule)
        c1_pair = cards1[0] == cards1[1]
        c2_pair = cards2[0] == cards2[1]
        # 对子的情况
        if c1_pair and not c2_pair:
            return True
        if not c1_pair and c2_pair:
            return False
        if c1_pair and c2_pair:
            # A对最大
            if cards1[-1].val == 1 and cards2[-1].val != 1:
                return True
            if cards1[-1].val != 1 and cards2[-1].val == 1:
                return False
            if cards1[-1] > cards2[-1]:
                return True
            return False
        return Rule.compare_by_san_pai(cards1, cards2)

    @staticmethod
    def compare_by_san_pai(cards1: list[Cards], cards2: list[Cards]) -> bool:
        """
        比较散牌
        cards1: 其中的某一铺牌（大铺/小铺）
        """
        c1_val = Rule.extract_cards_val(cards1)
        c2_val = Rule.extract_cards_val(cards2)
        c1_val = sum(c1_val) % 10
        c2_val = sum(c2_val) % 10
        # 1.单铺 加和值相同
        if c1_val == c2_val:
            # 单牌不同，比大的张
            if cards1[-1].val > cards2[-1].val:
                return True
            if cards1[-1].val < cards2[-1].val:
                return False
            # 单牌相同，比花色
            suit_idx = 1
            if cards1[0].val == 1:
                suit_idx = 0
            if cards1[suit_idx] > cards2[suit_idx]:
                return True
            return False

        # 2.单铺 加和值不同
        if int(c1_val) == int(c2_val) and (cards1[0].val == 1 or cards2[0].val == 1):
            # 18 => 9Q 、QK => 19、1Q => 1K
            # 2.1 两铺都带A
            if cards1[0].val == 1 and cards2[0].val == 1:
                if cards1[0] > cards2[0]:
                    return True
            if cards1[0].val == 1:
                return True
            return False

        elif c1_val > c2_val:
            return True
        return False

    @staticmethod
    def compare(c1: list[Cards], c2: list[Cards], compare_num) -> bool:
        """
        比较牌大小, 走/信的算平局不走该接口
        c1: 玩家A撒扑后的牌
        c1_t: 玩家A撒扑后的牌的类型
        compare_num: 比几铺
        return: bool c1 比较 c2的结果
        """
        c1_t: int = Rule.cards_type(c1)
        c2_t: int = Rule.cards_type(c2)
        if c1_t > c2_t >= CardsType.SHUI_YU.val:
            return True
        if c2_t > c1_t >= CardsType.SHUI_YU.val:
            return False

        assert 0 < compare_num <= 2
        if c1_t == c2_t == CardsType.SHUI_YU.val:
            compare_num = 1  # 水鱼各大一铺
        # 只有牌类型一样的才做比较
        bigger_compare_res = Rule.compare_one(c1[:2], c2[:2])
        small_compare_res = Rule.compare_one(c1[2:], c2[2:])

        if compare_num == 1:
            if bigger_compare_res or small_compare_res:
                return True
            return False
        if bigger_compare_res and small_compare_res:
            return True
        return False

    @staticmethod
    def sort_sa_pu(cards: List[int]):
        """ 撒扑后排序 """
        cards = [Cards.find_member_by_val(card) for card in cards]
        one = cards[:2]
        two = cards[2:]
        res = Rule.compare_one(one, two)
        one.sort(key=Rule.sort_rule, reverse=True)
        two.sort(key=Rule.sort_rule, reverse=True)
        if res:
            return one + two
        return two + one

    @staticmethod
    def merge(li, low, mid, high):
        """
        :param low: 首位元素
        :param mid:  将列表分割为两段有序的索引
        :param high: 列表长度-1
        :return:
        """
        i = low
        j = mid + 1
        ltmp = []
        while i <= mid and j <= high:
            if not Rule.compare_one(li[i], li[j]):
                ltmp.append(li[i])
                i += 1
            else:
                ltmp.append(li[j])
                j += 1
        # 当while执行完毕，两段中必定有一段没有数了
        while i <= mid:
            ltmp.append(li[i])
            i += 1
        while j <= high:
            ltmp.append(li[j])
            j += 1
        li[low:high + 1] = ltmp  # 写回到原来列表中

    @staticmethod
    def merge_sort(li, low, high):
        """ 归并排序 """
        if low < high:  # 至少有两个元素， 递归
            mid = (low + high) // 2
            Rule.merge_sort(li, low, mid)  # 将左边排好序
            Rule.merge_sort(li, mid + 1, high)  # 将右边排好序
            Rule.merge(li, low, mid, high)  # 归并