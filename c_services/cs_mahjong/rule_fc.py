import random
from copy import deepcopy
from functools import reduce

from common.utils.meta_class import NoInstances
from common.utils.utils import UtilsTool
from .const import *
from .poker import Poker
from .rule import Rule


class RuleFc(Rule):

    @staticmethod
    def can_hu_with_lai_zi_and_jiang(cards, jiang, lai_zi_count, remove_jiang_count, lai_zi=CardsType.LAI_ZI):
        cards = list(cards)
        Rule.remove_by_value(cards, jiang, remove_jiang_count)

        group = Rule.group_by_suit(cards).items()
        group = sorted(group, key=lambda value: len(value[1]), reverse=True)
        hu_path = []

        def process_check_result(result_cards,result_lz_count,count,card,kz_cards):
            """统一处理检查结果"""
            """优先判断是否有三节高"""
            nonlocal flag
            nonlocal lai_zi_count
            kz_cards_copy = deepcopy(kz_cards)
            card_list_copy = deepcopy(result_cards)
            card_list_copy.extend([card] * count)
            kz_cards_copy.append(card)
            for kz in kz_cards_copy:
                Rule.remove_by_value(card_list_copy, kz, 3)
            result_lz_count -= count

            result_flag, result_lai_zi_count_temp, result_step_data = Rule.check_value_match_rule_with_lai_zi_count(
                list(card_list_copy), 0, list(), result_lz_count, False)
            if result_flag:
                flag = result_flag
                l = len(result_step_data)
                if l>=0:
                    for kz in kz_cards_copy:
                        result_step_data.append([False, False, 0, {}, []])
                        result_step_data[l][0] = False
                        result_step_data[l][1] = True
                        result_step_data[l][2] = result_lai_zi_count_temp
                        result_step_data[l][3] = deepcopy([kz] * 3)
                        l+=1
                hu_path.extend(Rule.get_hu_path(suit, result_step_data, lai_zi))
                lai_zi_count = result_lai_zi_count_temp

        for suit, card_list in group:
            flag = False
            three = []
            two = []
            single = []
            for i in card_list:
                card_count = Rule.calc_value_count(card_list, i)
                if card_count == 3 and i not in three:
                    three.append(i)
                elif card_count == 2 and i not in two:
                    two.append(i)
                elif card_count == 1:
                    single.append(i)
            if len(three) == 2:
                three.sort()
                if three[0] + 1 == three[1]:
                    lz_count = lai_zi_count
                    if lai_zi_count >= 2 :
                        if three[0] - 1 in single:
                            process_check_result(list(card_list),lz_count,2,three[0] - 1,three)
                            if flag:
                                continue
                        if three[1] + 1 in single:
                            process_check_result(list(card_list),lz_count,2,three[1] + 1,three)
                            if flag:
                                continue
                        if three[0] - 1 in two:
                            process_check_result(list(card_list),lz_count,1,three[0] - 1,three)
                            if flag:
                                continue
                        if three[1] + 1 in two:
                            process_check_result(list(card_list),lz_count,1,three[1] + 1,three)
                            if flag:
                                continue
                    if lai_zi_count ==1 and two:
                        if three[0] - 1 in two:
                            process_check_result(list(card_list),lz_count,1,three[0] - 1,three)
                            if flag:
                                continue
                        if three[1] + 1 in two:
                            process_check_result(list(card_list),lz_count,1,three[1] + 1,three)
                            if flag:
                                continue



            if not flag:
                flag, lai_zi_count_temp, step_data = Rule.check_value_match_rule_with_lai_zi_count(
                    list(card_list), 0, list(), lai_zi_count, False)
                if not flag:
                    return False, []
                else:
                    hu_path.extend(Rule.get_hu_path(suit, step_data, lai_zi))
                lai_zi_count = lai_zi_count_temp

        if remove_jiang_count > 0:
            hu_path.append([jiang] * remove_jiang_count)
        for value in hu_path:
            if len(value) == 1:
                value.append(lai_zi)

        return True, hu_path

    @staticmethod
    def find_best_sequence(hand):
        """
        检测三节高、四节高
        """
        # 1. 按花色分组统计牌值
        suits = {}
        for tile in hand:
            suit = tile // 10  # 十位：花色
            val = tile % 10  # 个位：牌值
            if suit not in suits:
                suits[suit] = {}
            suits[suit][val] = suits[suit].get(val, 0) + 1

        # 2. 检测连续刻子链（三节高/四节高）
        best_sequence = []  # 存储最长连续序列

        for suit, counts in suits.items():
            sorted_vals = sorted(counts.keys())
            sequences = []  # 存储当前花色所有可能连续链

            # 生成所有可能的连续序列
            for i in range(len(sorted_vals)):
                chain = [sorted_vals[i]]
                current_val = sorted_vals[i]
                for j in range(i + 1, len(sorted_vals)):
                    next_val = sorted_vals[j]
                    if next_val == current_val + 1:
                        chain.append(next_val)
                        current_val = next_val
                    else:
                        break
                sequences.append(chain)

            # 筛选有效连续刻子链（每个牌值数量≥3）
            valid_chains = [
                chain for chain in sequences
                if len(chain) >= 3 and all(counts[val] >= 3 for val in chain)
            ]

            # 选择最长连续链
            if valid_chains:
                max_chain = max(valid_chains, key=len)
                # 更新全局最优序列
                if len(max_chain) > len(best_sequence):
                    best_sequence = max_chain

        return best_sequence

    @staticmethod
    def is_12_jin_chai(table_cards, cards):
        """判断是否是十二金钗"""
        # 必须先有3个杠
        if not cards:
            return False, []
        if len(table_cards) < 3:
            return False, []
        else:
            gang_count = 0
            for zp in table_cards:
                if zp[0] != ActionType.ACTION_TYPE_PENG:
                    gang_count += 1
            if gang_count < 3:  # 无3杠直接排除
                return False, []

        return HuType.SHI_ER_JIN_CHAI, []

    @staticmethod
    def is_an_ke(table_cards, hu_path, lai_zi, min_len=3):
        """ 3暗刻或4暗刻 """
        hu_path = list(hu_path)
        table_cards = list(table_cards)
        an_ke_count = 0

        if table_cards:
            for zp in table_cards:
                if zp[0] == ActionType.ACTION_TYPE_AN_GANG:
                    an_ke_count += 1  # 暗杠算暗刻

        for path in hu_path:
            path_len = len(path)
            if path_len < 3:
                continue
            path_lz_count = path.count(lai_zi)
            if path_lz_count == 0:
                if path[0] == path[1] == path[2]:
                    an_ke_count += 1
            elif path_lz_count == path_len:
                an_ke_count += 1
            else:
                path_copy = path[:]
                for _ in range(path_lz_count):
                    path_copy.remove(lai_zi)
                if len(path_copy) == 1 or path_copy[0] == path_copy[1]:
                    an_ke_count += 1

        if an_ke_count == 4:
            return HuType.SI_AN_KE, hu_path
        if an_ke_count == min_len:
            return HuType.SAN_AN_KE, hu_path
        return False, []

    @staticmethod
    def is_18_luo_han(table_cards, cards, lai_zi):
        """判断是否是十八罗汉"""
        # 必须先有4个杠
        if not cards:
            return False, []
        if len(table_cards) < 4:  # 无4杠直接排除
            return False, []
        else:
            for zp in table_cards:
                if zp[0] == ActionType.ACTION_TYPE_PENG:
                    return False, []
        flag, path = Rule.is_jin_gou_diao(cards, lai_zi)
        if flag:
            return HuType.SHI_BA_LUO_HAN, path
        else:
            return flag, path

    @staticmethod
    def can_hu(table_cards, cards, card=0, allow_hu_map: dict = None, lai_zi=CardsType.LAI_ZI, is_gy=False, is_wu_dui=False):
        """
        暴露给桌子对象的判胡接口
        return: hu_type, hu_path
        根据分数选取最大的得分胡牌类型
        """
        cards = list(cards)
        if Rule.is_card(card) and len(cards) % 3 != 2:
            cards.append(card)

        flag, path = Rule.is_jin_gou_diao(cards, lai_zi)
        if flag == HuType.JIN_GOU_DIAO:
            return flag,path

        cards_not_lai_zi = cards[:]
        lai_zi_count = Rule.remove_by_value(cards_not_lai_zi, lai_zi, -1)
        hua_se = {c // 10 for c in cards_not_lai_zi}
        qing_yi_se = hua_se.pop() if len(hua_se) == 1 else 0
        cards_len = len(cards)

        singles, two, threes, fours, _ = Rule.search_cards_by_count(cards_not_lai_zi, 1, 2, 3, 4)

        if cards_len == 11 and len(table_cards) == 1 and table_cards[0][0] == ActionType.ACTION_TYPE_PENG:
            # 2.地龙七
            flag, path = Rule.is_di_long_qi_new(table_cards, cards, card, lai_zi)
            if flag:
                if qing_yi_se:
                    return HuType.QING_LONG_BEI,path
                return flag,path

        if cards_len == 14:

            # 龙七对
            flag, path = Rule.is_long_qi_dui(lai_zi, lai_zi_count, singles, two, threes, fours)
            if flag:
                if qing_yi_se:
                    return HuType.QING_LONG_BEI,path
                return flag,path

            # 七对
            flag, path = Rule.is_qi_dui(lai_zi, lai_zi_count, singles, two, threes, fours)
            if flag:
                if qing_yi_se:
                    return HuType.QING_QI_DUI,path
                return flag,path

            # 大对子
        flag, path_list = Rule.is_da_dui_zi_new(cards, lai_zi, lai_zi_count, singles, two, threes, fours)
        if flag:
            if cards.count(lai_zi) == 0:
                return flag, path_list[0]
            flag, path = RuleFc.is_18_luo_han(table_cards, cards, lai_zi)
            if flag:
                return flag, path
            for path in path_list:
                flat_list = []  # 创建空列表

                # 遍历每个子列表，将其元素添加到主列表
                for sublist in path:
                    flat_list.extend(sublist)
                for table_card in table_cards:
                    flat_list.extend(list(table_card)[1:-1])
                result = RuleFc.find_best_sequence(flat_list)
                an_ke, an_ke_path = RuleFc.is_an_ke(table_cards,path,lai_zi)
                if len(result) == 4:
                    return HuType.SI_JIE_GAO, path
                if an_ke == HuType.SI_AN_KE:
                    return an_ke,an_ke_path
                if qing_yi_se:
                    return HuType.QING_DA_DUI,path
                flag, _ = RuleFc.is_12_jin_chai(table_cards, cards)
                if flag:
                    return flag, path

                if len(result) == 3:
                    return HuType.SAN_JIE_GAO,path
                if an_ke == HuType.SAN_AN_KE:
                    return an_ke,an_ke_path

            flag, path = Rule.is_jin_gou_diao(cards, lai_zi)
            if flag == HuType.JIN_GOU_DIAO:
                return flag, path

        # 平胡
        flag, path_list = RuleFc.can_common_hu(cards, lai_zi)
        if flag:
            if cards.count(lai_zi) == 0:
                return HuType.PING_HU, path_list
        return False, []


    @staticmethod
    def can_common_hu(cards, lai_zi=CardsType.LAI_ZI):
        """
        判断胡牌(平胡)的总循环
        该接口主要判断1个对子 + 顺子|刻子的情况
        """
        if len(cards) % 3 != 2:
            return False, []
        cards = list(cards)
        method_map = {
            0: Rule.can_hu_without_lai_zi,
            1: Rule.can_hu_with_one_lai_zi,
            2: RuleFc.can_hu_with_two_lai_zi,
            3: RuleFc.can_hu_with_three_lai_zi,
            4: RuleFc.can_hu_with_four_lai_zi,
            5: RuleFc.can_hu_with_five_lai_zi,
        }
        hz_count = Rule.calc_value_count(cards, lai_zi)
        if method_map.get(hz_count):
            flag, hu_path = method_map.get(hz_count)(cards, lai_zi)
            if flag:
                hu_path = list(filter(lambda v: v != [], hu_path))
            return flag, hu_path
        return False, []


    @staticmethod
    def can_hu_with_two_lai_zi(cards, lai_zi):
        """
        两个癞子判断能否胡牌
        2个红中：
        一对作将 -> 不补，直接按现有方式处理
        先找将牌，有的话先遍历一下，看能不能直接用手中的将胡牌
        如果不行，再直接遍历全部手牌拼将，看能不能胡
        """
        # flag, hu_path = Rule.can_hu_by_jiang(cards, lai_zi)
        # if flag:
        #     return True, hu_path

        Rule.remove_by_value(cards, lai_zi, -1)
        return RuleFc.__can_hu_with_pairs_and_jiang(cards, 2, 2, lai_zi)

    @staticmethod
    def can_hu_with_three_lai_zi(cards, lai_zi):
        """
        三个癞子判断能否胡牌
        3个红中：
        3张+0补
        直接按现有算法处理

        一对将+1补
        红中作将，其它的牌按1补的方式来处理

        三张全补
        手牌有将，则先遍历将牌
        手牌无将，则先补一将，三张牌必须全部补下去
        """
        Rule.remove_by_value(cards, lai_zi, -1)
        # flag, hu_path = Rule.can_hu_without_lai_zi(cards, lai_zi)
        # if flag:
        #     hu_path.append([lai_zi, lai_zi, lai_zi])
        #     return True, hu_path

        flag, hu_path = RuleFc.can_hu_with_lai_zi_and_jiang(cards, lai_zi, 1, 0, lai_zi)
        if flag:
            hu_path.append([lai_zi, lai_zi])
            return True, hu_path

        return RuleFc.__can_hu_with_pairs_and_jiang(cards, 3, 2, lai_zi)

    @staticmethod
    def can_hu_with_four_lai_zi(cards, lai_zi):
        """
        四个癞子判断能否胡牌
        4个红中：
        3张+1补
        红中不能做将，直接按1个红中的情况处理

        一对将+2补
        红中作将，剩下的两张按2个红中补两张的方式来处理

        四张全补
        红中不能作将（但可以补将），四张牌必须全部补下去
        """
        Rule.remove_by_value(cards, lai_zi, -1)
        flag, hu_path = Rule.can_hu_with_one_lai_zi(cards, lai_zi)
        if flag:
            hu_path.append([lai_zi, lai_zi, lai_zi])
            return True, hu_path

        flag, hu_path = RuleFc.can_hu_with_lai_zi_and_jiang(cards, lai_zi, 2, 0, lai_zi)
        if flag:
            hu_path.append([lai_zi, lai_zi])
            return True, hu_path

        return RuleFc.__can_hu_with_pairs_and_jiang(cards, 4, 2, lai_zi)

    @staticmethod
    def can_hu_with_five_lai_zi(cards, lai_zi):
        """ 5癞子（未测试） """
        Rule.remove_by_value(cards, lai_zi, -1)
        # # 按2个癞子的情况处理
        flag, hu_path = Rule.can_hu_with_two_lai_zi(cards, lai_zi)
        if flag:
            hu_path.append([lai_zi, lai_zi, lai_zi])
            return True, hu_path
        # 癞子作将，剩下的两张癞子按将补两张的方式来处理
        flag, hu_path = Rule.can_hu_with_lai_zi_and_jiang(cards, lai_zi, 3, 0, lai_zi)
        if flag:
            hu_path.append([lai_zi, lai_zi])
            return True, hu_path
        return RuleFc.__can_hu_with_pairs_and_jiang(cards, 5, 2, lai_zi)

    @staticmethod
    def __can_hu_with_pairs_and_jiang(cards, lai_zi_count, remove_jiang, lai_zi=CardsType.LAI_ZI):

        one_list, two_list, three_list, four_list = Rule.search_cards_by_count(cards, 1, 2, 3, 4)
        for jiang in two_list:
            flag, hu_path = RuleFc.can_hu_with_lai_zi_and_jiang(cards, jiang, lai_zi_count, remove_jiang, lai_zi)
            if flag:
                return True, hu_path
        for jiang in one_list:
            flag, hu_path = RuleFc.can_hu_with_lai_zi_and_jiang(cards, jiang, lai_zi_count, remove_jiang, lai_zi)
            if flag:
                return True, hu_path
        for jiang in three_list:
            flag, hu_path = RuleFc.can_hu_with_lai_zi_and_jiang(cards, jiang, lai_zi_count, remove_jiang, lai_zi)
            if flag:
                return True, hu_path
        for jiang in four_list:
            flag, hu_path = RuleFc.can_hu_with_lai_zi_and_jiang(cards, jiang, lai_zi_count, remove_jiang, lai_zi)
            if flag:
                return True, hu_path

        for jiang in set(cards):
            flag, hu_path = RuleFc.can_hu_with_lai_zi_and_jiang(cards, jiang, lai_zi_count, remove_jiang, lai_zi)
            if flag:
                return True, hu_path
        return False, []
