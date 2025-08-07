import random
from copy import deepcopy
from functools import reduce

from common.utils.meta_class import NoInstances
from common.utils.utils import UtilsTool
from .const import *
from .poker import Poker


class Rule(metaclass=NoInstances):
    @staticmethod
    def random_dice(count):
        """ 掷骰子 """
        return [random.randint(1, 6) for _ in range(count)]

    @staticmethod
    def get_value(card):
        return (card or 0) % 10

    @staticmethod
    def get_suit(card):
        return (card or 0) // 10

    @staticmethod
    def is_card(card):
        if not card or not isinstance(card, int):
            return False
        if card < 10 or card > 80:
            return False
        return card in ALL_CARDS_WITHOUT_ZI_HUA

    @staticmethod
    def group_by_suit(cards):
        """ 麻将分组,只有无花色 """
        group = {}
        for card in cards:
            suit = Rule.get_suit(card)
            value = Rule.get_value(card)
            group.setdefault(suit, []).append(value)
        return group

    @staticmethod
    def search_count(cards, need_count, is_gte=False):
        """搜索可组成对子牌的列表"""
        card_to_count = Rule.get_card_to_count(cards)
        result = []
        if is_gte:
            for card, count in card_to_count.items():
                if count >= need_count:
                    result.append(card)
        else:
            for card, count in card_to_count.items():
                if count == need_count:
                    result.append(card)
        result.sort()
        return result

    @staticmethod
    def search_cards_by_count(cards, count1, count2, count3, count4=None):
        """
        搜索满足指定count的牌,用于替代 search_count，一次遍历搜索即可
        """
        card_to_count = Rule.get_card_to_count(cards)
        cards_1 = []
        cards_2 = []
        cards_3 = []
        cards_4 = []
        for card, count in card_to_count.items():
            if count == count1:
                cards_1.append(card)
            elif count == count2:
                cards_2.append(card)
            elif count == count3:
                cards_3.append(card)
            elif count == count4:
                cards_4.append(card)
        return cards_1, cards_2, cards_3, cards_4, card_to_count

    @staticmethod
    def calc_ke_zi_list_and_must_list(cards):
        """计算刻子列表，以及必须被满足的牌列表"""
        count_list = Rule.get_card_to_count(cards)
        ke_zi_list = []
        must_list = []  # 除刻子外多余的牌
        for value, count in count_list.items():
            if count == 1:
                must_list.append(value)
            elif count == 2:
                must_list.append(value)
                must_list.append(value)
            elif count == 3:
                ke_zi_list.append(value)
            elif count == 4:
                must_list.append(value)
                ke_zi_list.append(value)

        return ke_zi_list, must_list

    @staticmethod
    def is_jin_gou_diao(cards, lai_zi):
        """
        是否是金钩钓
        （只在二三丁拐下有）
        """
        if len(cards) != 2:
            return False, []
        cards_copy = list(cards)
        lai_zi_count = Rule.remove_by_value(cards_copy, lai_zi, -1)
        if cards[0] == cards[1]:
            return HuType.JIN_GOU_DIAO, [cards]
        if lai_zi_count == 1:
            hu_type = HuType.JIN_GOU_DIAO
            if cards[0] == lai_zi:
                return hu_type, [[cards[1], cards[1]]]
            return hu_type, [[cards[0], cards[0]]]
        return False, []

    @staticmethod
    def is_seven_pairs(cards, lai_zi):
        """判断是否7小对 只需考虑1个癞子内的情况  """
        if not cards or len(cards) != 14:
            return False, []
        cards = list(cards)
        lai_zi_count = Rule.remove_by_value(cards, lai_zi, -1)
        singles, threes, fours, _, card_to_count = Rule.search_cards_by_count(cards, 1, 3, 4)
        singles_len = len(singles)
        threes_len = len(threes)
        if lai_zi_count == 0:
            if threes_len == 0 and singles_len == 0:
                result = HuType.QI_DUI
                if len(fours) > 0:
                    result = HuType.LONG_QI_DUI
                return result, [[card] * count for card, count in card_to_count.items()]
        elif lai_zi_count > 0 and singles_len + threes_len <= lai_zi_count:  # 8对 + 癞子  一刻子 + 6对 + 1单牌 +癞子

            singles_path = []
            singles_path.extend([[card] * count for card, count in card_to_count.items() if count == 2 or count == 4])
            singles_path.extend([[card] * 4 for card, count in card_to_count.items() if count == 3])
            singles_path.extend([[card] * 2 for card, count in card_to_count.items() if count == 1])

            result = HuType.QI_DUI
            if len(fours) > 0 or threes_len > 0:
                result = HuType.LONG_QI_DUI
            # singles_path.append([lai_zi]*lai_zi_count)
            return result, singles_path

        return False, []

    @staticmethod
    def is_da_dui_zi(cards, lai_zi):
        """ 判断是否是大对子 """
        if not cards or len(cards) % 3 != 2:
            return False, []
        cards = list(cards)
        lai_zi_count = Rule.remove_by_value(cards, lai_zi, -1)
        singles, two, threes, fours, card_to_count = Rule.search_cards_by_count(cards, 1, 2, 3, 4)
        if lai_zi_count == 0:
            if not singles and not fours and len(two) == 1:
                return HuType.DA_DUI_ZI, [[card] * count for card, count in card_to_count.items()]
        elif lai_zi_count > 0 and not fours:
            singles_path = []
            first_pair = True
            if two:
                # 单张需要两张赖子，对子需要一张赖子，当有对子时，留出一对可减少一张赖子
                if len(singles) * 2 + (len(two) - 1) <= lai_zi_count:
                    for card, count in card_to_count.items():
                        if count == 1:
                            singles_path.append([card] * 3)
                        elif count == 2:
                            if first_pair:
                                singles_path.append([card] * 2)
                                first_pair = False
                            else:
                                singles_path.append([card] * 3)
                        elif count == 3:
                            singles_path.append([card] * 3)

                    return HuType.DA_DUI_ZI, singles_path
            else:
                if len(singles) * 2 - 1 <= lai_zi_count:
                    for card, count in card_to_count.items():
                        if count == 1:
                            if first_pair:
                                first_pair = False
                                singles_path.append([card] * 2)
                            else:
                                singles_path.append([card] * 3)
                        elif count == 3:
                            singles_path.append([card] * 3)
                    return HuType.DA_DUI_ZI, singles_path
        return False, []

    @staticmethod
    def is_di_long_qi(table_cards, cards, lai_zi, is_gy=False, cal_ting_pai=False):
        """
        有一组碰牌+手上5个对子，胡碰的那组牌
        判断是否是地龙七
        双地龙：主要是贵阳麻将中有
        is_gy: 是否是贵阳麻将
        """
        # 必须先有一个碰牌  这个在外部直接PASS  必须有一个碰牌+摸或接炮同一张牌才继续内部判断 这里只需要判断剩下的是5对即可
        if len(table_cards) != 1 or table_cards[0][0] != ActionType.ACTION_TYPE_PENG:  # 最多有一个杠或者碰
            return False, []
        if not cards or len(cards) != 11:  # 地龙七手上必须有11张
            return False, []

        cards = list(cards)
        cards.extend(table_cards[0][1:-1])
        lai_zi_count = Rule.remove_by_value(cards, lai_zi, -1)
        if cal_ting_pai:
            if lai_zi_count > 0:
                cards.append(table_cards[0][1])
                lai_zi_count -= 1

        singles, _, threes, fours, count_list = Rule.search_cards_by_count(cards, 1, 2, 3, 4)
        singles_len = len(singles)
        threes_len = len(threes)
        fours_len = len(fours)
        if lai_zi_count == 0:
            if threes_len == 0 and singles_len == 0:
                result = HuType.DI_LONG_QI
                if is_gy:
                    if fours_len == 2:
                        result = HuType.DOUBLE_DI_LONG_QI  # 双地龙七
                    elif fours_len == 3:
                        result = HuType.THREE_DI_LONG_QI  # 三地龙七

                return result, [[card] * count for card, count in count_list.items()]

        # 8对 + 癞子  一刻子 + 6对 + 1单牌 +癞子
        elif lai_zi_count > 0 and singles_len + threes_len == lai_zi_count:
            singles_path = []
            singles_path.extend([[card] * count for card, count in count_list.items() if count == 2 or count == 4])
            singles_path.extend([[card] * 4 for card, count in count_list.items() if count == 3])
            singles_path.extend([[card] * 2 for card, count in count_list.items() if count == 1])
            result = HuType.DI_LONG_QI
            if is_gy:
                if fours_len == 3 or threes_len == 3:
                    result = HuType.THREE_DI_LONG_QI  # 三龙
                elif fours_len == 1 and threes_len == 2:
                    result = HuType.THREE_DI_LONG_QI  # 三龙
                elif fours_len == 2 and threes_len == 1:
                    result = HuType.THREE_DI_LONG_QI  # 三龙
                elif fours_len == 2:
                    result = HuType.DOUBLE_DI_LONG_QI  # 双龙
                    if lai_zi_count >= 2:
                        result = HuType.THREE_DI_LONG_QI  # 三龙
                elif threes_len == 2:
                    result = HuType.DOUBLE_DI_LONG_QI  # 双龙
                    if lai_zi_count == 4:
                        result = HuType.THREE_DI_LONG_QI  # 三龙
                elif fours_len == 1 and threes_len == 1 and lai_zi_count >= 3:
                    result = HuType.THREE_DI_LONG_QI  # 三龙
                elif fours_len == 1:
                    if lai_zi_count == 2:
                        result = HuType.DOUBLE_DI_LONG_QI  # 双龙
                    elif lai_zi_count == 4:
                        result = HuType.THREE_DI_LONG_QI  # 三龙
                elif threes_len == 1:
                    if lai_zi_count > 2:
                        result = HuType.DOUBLE_DI_LONG_QI  # 双龙
                elif fours_len == 0 and threes_len == 0 and lai_zi_count == 4:
                    result = HuType.DOUBLE_DI_LONG_QI  # 双龙

            return result, singles_path
        return False, []

    @staticmethod
    def is_group_match_rule(cards):
        """判断牌值的分组是否符合麻将的顺子、刻子的规则"""
        cards_len = len(cards)
        hu_path = []
        if cards_len == 0:
            return True, hu_path
        # 1.是否都是顺子
        cards.sort()
        is_shun_zi, shun_zi_path = Rule.is_shun_zi(cards)
        if is_shun_zi:
            hu_path.extend(shun_zi_path)
            return True, hu_path

        if cards_len == 3:
            if Rule.is_value_ke_zi(cards):
                hu_path.append(cards)
                return True, hu_path
            return False, []

        # 是否都是刻子
        ke_zi_list, must_list = Rule.calc_ke_zi_list_and_must_list(cards)
        if len(must_list) == 0:
            return True, list(map(lambda value: [value] * 3, ke_zi_list))

        # 以下都是判断是否为：顺子 + 刻子
        # 判断除刻子外的牌能否组成顺子
        must_list.sort()
        is_shun_zi, shun_zi_path = Rule.is_shun_zi(must_list)
        if is_shun_zi:
            hu_path = list(map(lambda value: [value] * 3, ke_zi_list))
            hu_path.extend(shun_zi_path)
            return True, hu_path

        # 检测将刻子与剩余的牌 组合 是否能成为顺子
        ke_zi_list.sort()
        for v in ke_zi_list:
            tmp_value = list(must_list)
            tmp_value.extend([v] * 3)
            tmp_value.sort()
            is_shun_zi, shun_zi_path = Rule.is_shun_zi(tmp_value)
            if is_shun_zi:
                ke_zi_list.remove(v)
                hu_path = list(map(lambda value: [value] * 3, ke_zi_list))
                hu_path.extend(shun_zi_path)
                return True, hu_path

        # 检测将刻子从cards中移除后能否组成顺子
        for v in ke_zi_list:
            ke_zi_list_new = [v]
            tmp_value = list(cards)
            tmp_value.remove(v)
            tmp_value.remove(v)
            tmp_value.remove(v)
            tmp_value.sort()
            is_shun_zi, shun_zi_path = Rule.is_shun_zi(tmp_value)
            if is_shun_zi:
                hu_path = list(map(lambda value: [value] * 3, ke_zi_list_new))
                hu_path.extend(shun_zi_path)
                return True, hu_path
        return False, []

    @staticmethod
    def can_hu_by_jiang(cards, card):
        """
        判断能否以此为将牌胡牌
        card: 将牌
        """
        cards = list(cards)
        remove_jiang_count = 2
        Rule.remove_by_value(cards, card, remove_jiang_count)
        group = Rule.group_by_suit(cards)
        hu_path = []
        for k, v in group.items():
            if len(v) % 3 != 0:
                return False, []
            flag, unit_hu_path = Rule.is_group_match_rule(list(v))
            if not flag:
                return False, []
            for path in unit_hu_path:
                hu_path.append(list(map(lambda value: k * 10 + value, path)))

        hu_path.append([card] * remove_jiang_count)
        return True, hu_path

    @staticmethod
    def __can_hu_with_pairs_and_jiang(cards, lai_zi_count, remove_jiang, lai_zi=CardsType.LAI_ZI):
        # one_list, two_list, three_list, four_list, _ = Rule.search_cards_by_count(cards, 1, 2, 3, 4)
        # for jiang in two_list + three_list + four_list + one_list:
        for jiang in set(cards):
            flag, hu_path = Rule.can_hu_with_lai_zi_and_jiang(cards, jiang, lai_zi_count, remove_jiang, lai_zi)
            if flag:
                return True, hu_path
        return False, []

    @staticmethod
    def can_hu_without_lai_zi(cards, _):
        """ 不带赖子判断胡牌 """
        pair_list = Rule.search_count(cards, 2, is_gte=True)
        for card in pair_list:
            flag, path = Rule.can_hu_by_jiang(cards, card)
            if flag:
                return True, path
        return False, []

    @staticmethod
    def can_hu_with_one_lai_zi(cards, lai_zi):
        """
        一个癞子判断胡牌
        手里有将，则先尝试用将牌组合，判断能否胡
        如果没有将，则直接尝试红中补将
        """
        Rule.remove_by_value(cards, lai_zi, -1)
        return Rule.__can_hu_with_pairs_and_jiang(cards, 1, 2, lai_zi)

    @staticmethod
    def can_hu_with_two_lai_zi(cards, lai_zi):
        """
        两个癞子判断能否胡牌
        2个红中：
        一对作将 -> 不补，直接按现有方式处理
        先找将牌，有的话先遍历一下，看能不能直接用手中的将胡牌
        如果不行，再直接遍历全部手牌拼将，看能不能胡
        """
        flag, hu_path = Rule.can_hu_by_jiang(cards, lai_zi)
        if flag:
            return True, hu_path

        Rule.remove_by_value(cards, lai_zi, -1)
        return Rule.__can_hu_with_pairs_and_jiang(cards, 2, 2, lai_zi)

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
        flag, hu_path = Rule.can_hu_without_lai_zi(cards, lai_zi)
        if flag:
            hu_path.append([lai_zi, lai_zi, lai_zi])
            return True, hu_path

        flag, hu_path = Rule.can_hu_with_lai_zi_and_jiang(cards, lai_zi, 1, 0, lai_zi)
        if flag:
            hu_path.append([lai_zi, lai_zi])
            return True, hu_path

        return Rule.__can_hu_with_pairs_and_jiang(cards, 3, 2, lai_zi)

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

        flag, hu_path = Rule.can_hu_with_lai_zi_and_jiang(cards, lai_zi, 2, 0, lai_zi)
        if flag:
            hu_path.append([lai_zi, lai_zi])
            return True, hu_path

        return Rule.__can_hu_with_pairs_and_jiang(cards, 4, 2, lai_zi)

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
        return Rule.__can_hu_with_pairs_and_jiang(cards, 5, 2, lai_zi)

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
            2: Rule.can_hu_with_two_lai_zi,
            3: Rule.can_hu_with_three_lai_zi,
            4: Rule.can_hu_with_four_lai_zi,
            5: Rule.can_hu_with_five_lai_zi,
        }
        hz_count = Rule.calc_value_count(cards, lai_zi)
        if method_map.get(hz_count):
            flag, hu_path = method_map.get(hz_count)(cards, lai_zi)
            if flag:
                hu_path = list(filter(lambda v: v != [], hu_path))
            return flag, hu_path
        return False, []

    @staticmethod
    def get_hu_path(suit, step_data, lai_zi):
        step_data = deepcopy(step_data)
        hu_path = []
        user_cards = []
        for step in reversed(step_data):
            for already_user_card in user_cards:
                if already_user_card in step[3]:
                    step[3].remove(already_user_card)
            user_cards.extend(step[3])
            cards = list(map(lambda v: suit * 10 + v, step[3]))
            hz_cards = list(map(lambda v: suit * 10 + v, step[4]))
            unit_path = (cards + hz_cards)
            unit_path.sort()
            for value in step[4]:
                index = unit_path.index(suit * 10 + value)
                unit_path[index] = lai_zi

            hu_path.append(unit_path)

        return hu_path

    @staticmethod
    def can_hu_with_lai_zi_and_jiang(cards, jiang, lai_zi_count, remove_jiang_count, lai_zi=CardsType.LAI_ZI):
        cards = list(cards)
        Rule.remove_by_value(cards, jiang, remove_jiang_count)

        group = Rule.group_by_suit(cards).items()
        group = sorted(group, key=lambda value: len(value[1]), reverse=True)
        hu_path = []
        for suit, card_list in group:
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
    def check_value_is_valid_with_lai_zi(cards, step_data, index, hz_count):
        """
        :param cards:
        :param step_data:
        :param index:
        :param hz_count:
        :return: 是否组成顺子或刻子, 当前牌, 红中数量，红中所变的牌
        """
        calc_cards = list(cards)
        value = cards[0]
        hz_change_value = []
        if not step_data[index][1]:
            # 检测刻子
            step_data[index][1] = True
            count = Rule.calc_value_count(cards, value)
            if 3 <= count:
                Rule.remove_by_value(cards, value, 3)
                return True, cards, hz_count, hz_change_value

            if hz_count > 0 and hz_count >= 3 - count:
                Rule.remove_by_value(cards, value, 3)
                hz_count -= (3 - count)
                hz_change_value.extend([value] * (3 - count))
                return True, cards, hz_count, hz_change_value
        if not step_data[index][0]:
            # 检测顺子
            step_data[index][0] = True
            if value + 1 in cards and value + 2 in cards:
                Rule.remove_by_value(cards, value)
                Rule.remove_by_value(cards, value + 1)
                Rule.remove_by_value(cards, value + 2)
                return True, cards, hz_count, hz_change_value

            used_hz = 0  # 记录红中使用数  # todo: value + 1 > 9???
            if value + 1 not in cards:
                used_hz += 1
                hz_change_value.append(value + 1)

            if value + 2 not in cards:
                used_hz += 1
                if value + 2 <= 9:
                    hz_change_value.append(value + 2)
                else:
                    hz_change_value.append(value - 1)

            if hz_count >= used_hz > 0:
                hz_count -= used_hz
                Rule.remove_by_value(cards, value)
                Rule.remove_by_value(cards, value + 1)
                if value + 2 <= 9:
                    Rule.remove_by_value(cards, value + 2)
                else:
                    Rule.remove_by_value(cards, value - 2)
                return True, cards, hz_count, hz_change_value
            else:
                hz_change_value = []

        return False, calc_cards, hz_count, hz_change_value

    @staticmethod
    def check_value_match_rule_with_lai_zi_count(cards, index, step_data, hz_count, is_back):
        """
        检测某花色是否符合游戏规则（带红中检测）
        从最左边的牌往右依次来检测，当成顺或成刻时，此路通
        当即不成顺又不成刻时，此路不通
        当此路通时，往下循环，到达终点时则是成功
        当此路不通时，往上回退一步，如果上一步已经检测了顺和刻，则再回退一步，
        直到可以选择下一步或者回到了起点。
        step_data：[是否检测刻子, 是否检测顺子，癞子数量, 原始手牌，拆牌后的新手牌] 递归实现
        """
        if len(cards) == 0:
            return True, hz_count, step_data

        cards.sort()
        if index >= len(step_data):
            step_data.append([False, False, 0, {}, []])

        if not is_back:
            step_data[index][2] = hz_count
            step_data[index][3] = deepcopy(cards)

        flag, new_list, new_hz_count, new_hz_change_value = Rule.check_value_is_valid_with_lai_zi(
            cards, step_data, index, hz_count)

        step_data[index][4] = new_hz_change_value
        if flag:
            return Rule.check_value_match_rule_with_lai_zi_count(
                new_list, index + 1, step_data, new_hz_count, False)
        # 往回退一步
        if index > 0:
            step_data = step_data[0:index]
            old_hz_count, old_list = deepcopy(step_data[index - 1][2]), deepcopy(step_data[index - 1][3])

            return Rule.check_value_match_rule_with_lai_zi_count(
                old_list, index - 1, step_data, old_hz_count, True)

        if index == 0:
            return False, hz_count, step_data

        return False, hz_count, step_data

    @staticmethod
    def can_hu(table_cards, cards, card=0, allow_hu_map: dict = None, lai_zi=CardsType.LAI_ZI, is_gy=False, is_wu_dui=False):
        """
        暴露给桌子对象的判胡接口
        return: hu_type, hu_path
        """
        allow_hu_map = allow_hu_map or {}
        if Rule.is_card(card) and len(cards) % 3 != 2:
            cards.append(card)

        def lai_zi_2_hong_zhong(value):
            if value == lai_zi:
                return CardsType.LAI_ZI
            return value

        def hong_zhong_2_lai_zi(value):
            if value == CardsType.LAI_ZI:
                return lai_zi
            return value

        if lai_zi != CardsType.LAI_ZI:
            cards = list(map(lai_zi_2_hong_zhong, cards))

        cards = list(cards)
        if allow_hu_map.get(HuType.JIN_GOU_DIAO):
            flag, path = Rule.is_jin_gou_diao(cards, CardsType.LAI_ZI)
            if flag == HuType.JIN_GOU_DIAO:
                return flag, list(map(lambda v: list(map(hong_zhong_2_lai_zi, v)), path))
        if allow_hu_map.get(HuType.QI_DUI):
            flag, path = Rule.is_seven_pairs(cards, lai_zi)
            if flag:
                return flag, list(map(lambda v: list(map(hong_zhong_2_lai_zi, v)), path))  # 有癞子替换为癞子
        if allow_hu_map.get(HuType.DI_LONG_QI):
            flag, path = Rule.is_di_long_qi(table_cards, cards, CardsType.LAI_ZI, is_gy, cal_ting_pai=True)
            if flag:
                if table_cards[0][1] == card:  # 必须摸的是碰的那张
                    return flag, list(map(lambda v: list(map(hong_zhong_2_lai_zi, v)), path))
        if is_wu_dui:
            flag, path = Rule.is_wu_dui(cards, lai_zi=CardsType.LAI_ZI)
            if flag:
                return flag, list(map(lambda v: list(map(hong_zhong_2_lai_zi, v)), path))

        flag, path = Rule.is_da_dui_zi(cards, lai_zi)
        if flag:
            return flag, list(map(lambda v: list(map(hong_zhong_2_lai_zi, v)), path))

        is_hu, path = Rule.can_common_hu(cards, lai_zi)
        if is_hu:
            return HuType.PING_HU, list(map(lambda v: list(map(hong_zhong_2_lai_zi, v)), path))
        return 0, []


    @staticmethod
    def only_can_hu(table_cards, cards, card, lai_zi=CardsType.LAI_ZI):
        cards = list(cards)
        cards_len = len(cards)
        if Rule.is_card(card) and cards_len % 3 != 2:
            cards.append(card)

        flag, _ = Rule.is_jin_gou_diao(cards, lai_zi)
        if flag:
            return flag

        if cards_len == 11 and len(table_cards) == 1 and table_cards[0][0] == ActionType.ACTION_TYPE_PENG:
            # 2.地龙七
            flag, _ = Rule.is_di_long_qi_new(table_cards, cards, card, lai_zi)
            if flag:
                return flag
        cards_copy = cards[:]
        lai_zi_count = Rule.remove_by_value(cards_copy, lai_zi, -1)
        singles, two, threes, fours, _ = Rule.search_cards_by_count(cards_copy, 1, 2, 3, 4)
        if cards_len == 14:
            # 3.七对
            flag, _ = Rule.is_qi_dui(lai_zi, lai_zi_count, singles, two, threes, fours)
            if flag:
                return flag
            # 4.龙七对
            flag, _ = Rule.is_long_qi_dui(lai_zi, lai_zi_count, singles, two, threes, fours)
            if flag:
                return flag
        # 5.大对子
        flag, _ = Rule.is_da_dui_zi_new(cards, lai_zi, lai_zi_count, singles, two, threes, fours)
        if flag:
            return flag
        # 6.平胡
        flag, _ = Rule.can_common_hu(cards, lai_zi)
        if flag:
            return HuType.PING_HU
        return False


    @staticmethod
    def can_tian_ting(table_cards, cards: list, que=0, allow_hu_map: dict = None):
        """
        table_cards: 碰杠的牌
        cards：手牌
        que：选缺的牌
        """
        if Rule.is_has_que(cards, que):
            return False
        hand_cards_len = len(cards)
        if hand_cards_len % 3 == 2:
            for card in set(cards):
                tian_ting_hand_cards = deepcopy(cards)
                tian_ting_hand_cards.remove(card)
                can_hu, hu_path = Rule.can_ting_pai(table_cards, tian_ting_hand_cards, allow_hu_map)
                if can_hu:
                    return True
        else:
            can_hu, hu_path = Rule.can_ting_pai(table_cards, cards, allow_hu_map)
            if can_hu:
                return True
        return False


    @staticmethod
    def which_cards_to_play_can_tian_ting(table_cards, cards, allow_hu_map: dict = None):
        """
        打出哪些牌能天听
        """
        tian_ting_cards = []
        if len(cards) == 13:
            can_hu, path = Rule.can_ting_pai(table_cards, cards, allow_hu_map)
            if can_hu:
                return True, tian_ting_cards

        for card in set(cards):
            temp_cards = deepcopy(cards)
            temp_cards.remove(card)
            # 打出一张之后能听牌
            can_hu, path = Rule.can_ting_pai(table_cards, temp_cards, allow_hu_map)
            if can_hu:
                tian_ting_cards.append(card)

        if len(tian_ting_cards) > 0:
            return True, tian_ting_cards

        return False, tian_ting_cards

    @staticmethod
    def get_tian_ting_cards(table_cards, cards, que=0, lai_zi=CardsType.LAI_ZI):
        """
        打出哪些牌后能保证天听  此接口必须在桌子里先判断没出过牌
        返回打出哪些牌后剩余牌保持叫牌的 牌列表
        """
        tian_ting_cards = []
        cards_copy = deepcopy(cards)
        cards_copy.sort()
        if que > 0:
            que_cards = []
            for c in cards_copy:
                if Rule.get_suit(c) == que:
                    que_cards.append(c)

            if que_cards:
                return True, que_cards

        if len(cards) == 13:
            can_hu = Rule.only_can_hu(table_cards, cards_copy, card=lai_zi, lai_zi=lai_zi)
            if can_hu:
                return True, tian_ting_cards
        c = 0
        for card in cards_copy:
            if c == card:
                continue
            c = card
            if card in tian_ting_cards:
                tian_ting_cards.append(card)
                continue
            tian_ting_hand_cards = deepcopy(cards)
            tian_ting_hand_cards.remove(card)
            can_hu = Rule.only_can_hu(table_cards, tian_ting_hand_cards, card=lai_zi, lai_zi=lai_zi)
            if can_hu:
                tian_ting_cards.append(card)

        if len(tian_ting_cards) > 0:
            return True, tian_ting_cards

        return False, []


    @staticmethod
    def can_ting_pai(table_cards, hand_cards, allow_hu_map: dict, lai_zi=CardsType.LAI_ZI, is_gy=False, is_wu_dui=False):
        """
        计算是否是听牌状态
        加个癞子能胡就听牌了
        """
        cards = deepcopy(hand_cards)
        cards.append(lai_zi)  # 加入一张癞子牌
        return Rule.can_hu(table_cards, cards, allow_hu_map=allow_hu_map, lai_zi=lai_zi, is_gy=is_gy, is_wu_dui=is_wu_dui)


    @staticmethod
    def can_ting_pai_by_zun_yi(table_cards, hand_cards, card=0, ji_to_score=None, lai_zi=CardsType.LAI_ZI,
                               pai_xing_score_map=PAI_XING_SCORE_MAP, extra_score_map=EXTRA_SCORE_MAP):
        cards = deepcopy(hand_cards)
        if len(cards) % 3 < 2:
            cards.append(lai_zi)
            card = lai_zi
        return Rule.get_hu_type_by_score(table_cards, cards, card, ji_to_score, lai_zi=lai_zi,
                                         pai_xing_score_map=pai_xing_score_map, extra_score_map=extra_score_map)


    @staticmethod
    def get_ting_hu_list(table_cards, cards: list, allow_hu_map: dict, lai_zi=CardsType.LAI_ZI):
        """ 获取叫哪些牌 """
        all_cards = list(ALL_CARDS_WITHOUT_ZI_HUA)
        hu_card = []
        count_gt_4 = Rule.search_count(cards, 4)
        for c in count_gt_4 or []:
            all_cards.remove(c)

        suits_to_count = {}
        for c in cards:
            c_suit = Rule.get_suit(c)
            suits_to_count[c_suit] = suits_to_count.get(c_suit, 0) + 1

        valid_cards = []
        for card in all_cards:
            if suits_to_count.get(Rule.get_suit(card)):
                valid_cards.append(card)

        for card in valid_cards:
            temp_cards = list(cards)
            temp_cards.append(card)
            flag, hu_path = Rule.can_hu(table_cards, temp_cards, allow_hu_map=allow_hu_map, lai_zi=lai_zi)
            if flag:
                hu_card.append(card)
        return hu_card


    @staticmethod
    def has_hu_is_qing_yi_se(table_cards, cards, card, lai_zi=CardsType.LAI_ZI):
        """清一色"""
        if card > 0:
            cards.append(card)
        lai_zi_count = Rule.calc_value_count(cards, lai_zi)
        cards = reduce(lambda result, v: result + v[1:-1], table_cards, cards)
        Rule.remove_by_value(cards, lai_zi, lai_zi_count)
        hua_se = set(map(lambda value: value // 10, cards))
        return len(hua_se) == 1


    @staticmethod
    def can_ming_gang(cards: list, card, lai_zi=CardsType.LAI_ZI):
        """ 判断是否能明杠 """
        if card == lai_zi:
            return False, 0
        if Rule.calc_value_count(cards, card) >= 3:
            return True, card
        return False, 0


    @staticmethod
    def can_zhuan_wan_gang(cards: list, table_cards: list, card=0):
        """ 判断是否能转弯杠（梭杠） """
        peng_cards = {group[1] for group in table_cards
                      if group[0] == ActionType.ACTION_TYPE_PENG}

        check_cards = [card] if card != 0 else cards

        card = next((c for c in check_cards if c in peng_cards), None)
        return (True, card) if card else (False, 0)


    @staticmethod
    def can_an_gang(cards: list, card=0):
        """ 判断是否能暗杠 """
        card_to_count = Rule.get_card_to_count(cards)
        if card > 0:
            if card_to_count.get(card, 0) >= 4:
                return True, [card]
        can_gang_list = []
        for card, count in card_to_count.items():
            if count >= 4:
                can_gang_list.append(card)
        if can_gang_list:
            return True, can_gang_list
        return False, can_gang_list


    @staticmethod
    def can_peng(cards: list, card, lai_zi=CardsType.LAI_ZI):
        """ 判断是否能碰 """
        if card == lai_zi:
            return False
        return Rule.calc_value_count(cards, card) >= 2


    @staticmethod
    def is_shun_zi(cards):
        """
        -- 判断牌值是否全部由顺子构成，注意这里不能直接传牌过来，只能传牌值，不能带花色
        -- 所有会改变原参数的值的方法，都应该在开始的时候直接复制list
        """
        cards = list(cards)
        path = []
        for i in range(0, len(cards) - 1, 3):
            v = cards[0]
            if v in cards and v + 1 in cards and v + 2 in cards:
                cards.remove(v)
                cards.remove(v + 1)
                cards.remove(v + 2)
                path.append([v, v + 1, v + 2])
            else:
                return False, []
        return True, path


    @staticmethod
    def is_value_ke_zi(cards):
        """ 判断牌值是否刻子，注意这里不能直接传牌过来，只能传牌值，不能带花色 """
        return len(cards) == 3 and cards[0] == cards[1] == cards[2]


    @staticmethod
    def calc_value_count(cards, value):
        """计算给定值在列表中出现的次数"""
        return cards.count(value)


    @staticmethod
    def remove_by_value(card_data, value, remove_count=1):
        return UtilsTool.remove_by_value(card_data, value, remove_count)


    @staticmethod
    def __split_list_by_straight(l: list) -> list:
        """
        将列表按值是否连续来断开，比如 [5, 7, 9, 10, 12] -> [[5], [7], [9, 10], [12]]
        :param l:
        :return:
        """
        result = []
        l.sort()
        cursor = 0
        for i in range(len(l)):
            if i == len(l) - 1:
                result.append(l[cursor:])
                continue
            if l[i] + 1 != l[i + 1]:
                result.append(l[cursor:i + 1])
                cursor = i + 1
                continue
        return result


    @staticmethod
    def get_card_to_count(cards):
        """统计整组牌张数量"""
        count_list = {}
        for v in cards:
            count_list[v] = count_list.get(v, 0) + 1
        return count_list


    @staticmethod
    def is_has_que(cards, que):
        """ 判断是否缺门是否打完 """
        if que < 0:
            return False
        for card in cards:
            if Rule.get_suit(card) == que:
                return True
        return False


    @staticmethod
    def r_can_tian_ting(table_cards, hand_cards, que=0, allow_hu_map: dict = None, is_zy=False, lai_zi=CardsType.LAI_ZI):
        """通用天听检测方法（支持13/14张牌）"""
        for combo in table_cards:
            if combo[0] != ActionType.ACTION_TYPE_AN_GANG:
                return False

        cards = deepcopy(hand_cards)
        cards_len = len(cards)
        is_14_mode = len(cards) == 14 or (is_zy and cards_len == 11)  # 是否14张牌
        cards.sort()

        if que > 0:
            suit_count = Poker.cal_card_suit_count(cards)
            que_count = suit_count.get(que, 0)

            # 14张牌允许1张缺门牌，13张牌禁止任何缺门牌
            max_allowed = 1 if is_14_mode else 0
            if que_count > max_allowed:
                return False

        def check_ting(cards_to_check):
            if not is_zy:
                return Rule.can_ting_pai(table_cards, cards_to_check, allow_hu_map)[0]
            else:
                return Rule.only_can_hu(table_cards, cards_to_check, lai_zi, lai_zi)

        if is_14_mode:
            for idx in range(len(cards)):
                # 移除索引为idx的牌（仅一张）
                modified_hand = cards[:idx] + cards[idx + 1:]
                if check_ting(modified_hand):
                    return True
            return False
        else:
            # 13张牌：直接检测当前牌组
            return check_ting(cards)


    @staticmethod
    def get_round_over_jiao_pai(table_cards, hand_cards, allow_hu_map: dict, curr_card=0, is_gy=False, lai_zi=0, is_wu_dui=False):
        """
        此接口处理玩家叫牌类型，外部不再处理
        """
        lai_zi = lai_zi or CardsType.LAI_ZI
        cards = deepcopy(hand_cards)
        # 如果有14张 打出一张之后 算听牌
        if len(hand_cards) % 3 == 2:
            cards_list = list(cards)
            cards_list.sort()
            curr_c = 0
            for card in cards_list:
                if curr_c == card:
                    continue
                curr_c = card
                tian_ting_hand_cards = deepcopy(hand_cards)
                tian_ting_hand_cards.remove(curr_c)
                # 打出一张之后能听牌
                can_hu, hu_path = Rule.can_ting_pai(
                    table_cards, tian_ting_hand_cards, allow_hu_map, lai_zi, is_gy, is_wu_dui
                )
                if can_hu:
                    return Rule.get_jiao_type(table_cards, can_hu, hu_path, cards, curr_card)
        else:
            can_hu, hu_path = Rule.can_ting_pai(
                table_cards, cards, allow_hu_map, lai_zi, is_gy, is_wu_dui)
            if can_hu:
                return Rule.get_jiao_type(table_cards, can_hu, hu_path, cards, curr_card)
        return 0


    @staticmethod
    def get_round_over_jiao_pai_by_zun_yi(table_cards, hand_cards, curr_card=0, lai_zi=0, ji_to_score=None,
                                          pai_xing_score_map=PAI_XING_SCORE_MAP, extra_score_map=EXTRA_SCORE_MAP):
        """
        此接口处理玩家叫牌类型，外部不再处理
        """
        lai_zi = lai_zi or CardsType.LAI_ZI
        cards = deepcopy(hand_cards)
        # 如果有14张 打出一张之后 算听牌
        if len(hand_cards) % 3 == 2:
            cards_list = list(cards)
            cards_list.sort()
            curr_c = 0
            for card in cards_list:
                if curr_c == card:
                    continue
                curr_c = card
                tian_ting_hand_cards = deepcopy(hand_cards)
                tian_ting_hand_cards.remove(curr_c)
                # 打出一张之后能听牌
                can_hu, hu_path = Rule.can_ting_pai_by_zun_yi(table_cards, tian_ting_hand_cards, 0, ji_to_score,
                                                              lai_zi, pai_xing_score_map, extra_score_map)
                if can_hu:
                    return Rule.get_jiao_type(table_cards, can_hu, hu_path, cards, curr_card)
        else:
            can_hu, hu_path = Rule.can_ting_pai_by_zun_yi(table_cards, cards, 0, ji_to_score, lai_zi, pai_xing_score_map, extra_score_map)
            if can_hu:
                return Rule.get_jiao_type(table_cards, can_hu, hu_path, cards, curr_card)
        return 0


    @staticmethod
    def get_jiao_type(table_cards, can_hu, hu_path, cards, curr_card):
        """ 在叫牌的基础上判断叫牌类型 """
        jiao_pai = can_hu

        if can_hu == HuType.QI_DUI:
            # 检查是否存在三张相同牌（龙七对）
            if Rule.get_card_list_by_count(cards, 3, True):
                jiao_pai = HuType.LONG_QI_DUI

        # 检测大对子
        elif can_hu not in (HuType.DI_LONG_QI, HuType.JIN_GOU_DIAO, HuType.RUAN_WU_DUI, HuType.YING_WU_DUI):
            if Rule.is_peng_peng_hu(hu_path.copy()):
                jiao_pai = HuType.DA_DUI_ZI

        # 清一色检测
        if not Rule.has_hu_is_qing_yi_se(table_cards.copy(), cards, curr_card):
            return jiao_pai

        qing_map = {
            HuType.QI_DUI: HuType.QING_QI_DUI,
            HuType.LONG_QI_DUI: HuType.QING_LONG_BEI,
            HuType.DA_DUI_ZI: HuType.QING_DA_DUI,
            HuType.DI_LONG_QI: HuType.QING_DI_LONG,
            HuType.JIN_GOU_DIAO: HuType.QING_JIN_GOU,
            HuType.RUAN_WU_DUI: HuType.QYS_RUAN_WU_DUI,
            HuType.YING_WU_DUI: HuType.QYS_YING_WU_DUI,
        }
        return qing_map.get(jiao_pai, HuType.QING_YI_SE)


    @staticmethod
    def get_card_list_by_count(cards: list, count, with_more=False):
        same_value_list = Poker.get_same_value_cards(cards)
        temp_list = []
        for i in same_value_list:
            if len(same_value_list[i]) == count:
                temp_list.append(same_value_list[i])
            if with_more and len(same_value_list[i]) > count:
                temp_list.append(same_value_list[i])
        return temp_list


    @staticmethod
    def is_peng_peng_hu(hu_path):
        """碰碰胡"""
        for combo in hu_path:
            if len(combo) > 1:
                combo_set = set(combo)
                if len(combo_set) > 2:
                    return False
                if len(combo_set) == 2 and CardsType.LAI_ZI not in combo_set:
                    return False
        return True


    @staticmethod
    def is_wu_dui(cards, card=0, lai_zi=CardsType.LAI_ZI):
        """
        毕节玩法：判断是否是软/硬5对
        """
        if not cards or len(cards) != 11:
            return False, []
        cards = list(cards)
        lai_zi_count = Rule.remove_by_value(cards, lai_zi, -1)
        singles, two, threes, fours,_= Rule.search_cards_by_count(cards, 1, 2, 3, 4)
        singles_len = len(singles)
        threes_len = len(threes)
        fours_len = len(fours)
        if lai_zi_count == 0:
            if singles_len == 0:
                if threes_len == 1:
                    if threes[0] == card:
                        hu_type = HuType.YING_WU_DUI
                    else:
                        hu_type = HuType.RUAN_WU_DUI
                    return hu_type, [threes * 3] + [[t] * 2 for t in two]
                if threes_len == 3:
                    return HuType.RUAN_WU_DUI, [[t] * 3 for t in threes] + [[t] * 2 for t in two]
        else:
            if fours_len == 0:
                res_lai_zi_count = lai_zi_count - singles_len
                if threes_len == 0:
                    if res_lai_zi_count == 0:
                        return HuType.YING_WU_DUI, []
                    if res_lai_zi_count >= 3:
                        return HuType.RUAN_WU_DUI, []
                else:
                    if res_lai_zi_count >= 0:
                        return HuType.RUAN_WU_DUI, []
        return False, []


    @staticmethod
    def is_qi_dui(lai_zi, lai_zi_count, *args):
        """
        新七对判胡算法：针对遵义麻将
        """
        singles, two, threes, fours = args
        if not lai_zi_count:
            if two and (not singles and not threes and not fours):
                return HuType.QI_DUI, [[[t] * 2 for t in two]]
            return False, []
        singles_len = len(singles)
        if not threes and not fours:
            if lai_zi_count == singles_len:
                return HuType.QI_DUI, [[[t] * 2 for t in two] + [[s, lai_zi] for s in singles]]
            elif (lai_zi_count - singles_len) == 2:
                return HuType.QI_DUI, [
                    [[t] * 2 for t in two] +
                    [[s, lai_zi] for s in singles] +
                    [[lai_zi] * 2]
                ]
            # 有四个癞子时的七对可以是双龙七
        return False, []


    @staticmethod
    def is_long_qi_dui(lai_zi, lai_zi_count, *args):
        """
        龙七对判胡算法（遵义麻将）
        """
        singles, two, threes, fours = args
        fours_len = len(fours)
        singles_len = len(singles)
        threes_len = len(threes)
        two_len = len(two)

        # 1. 无赖子情况优先处理
        if not lai_zi_count:
            if not singles and not threes and fours_len > 0:
                dragon_type = HuType.LONG_QI_DUI
                if fours_len == 2:
                    dragon_type = HuType.DOUBLE_LONG_QI
                elif fours_len == 3:
                    dragon_type = HuType.THREE_LONG_QI
                path = [[f] * 4 for f in fours] + [[t] * 2 for t in two]
                return dragon_type, [path]
            return False, []

        # 2. 赖子不足直接返回
        if lai_zi_count < singles_len + threes_len:
            return False, []

        if not fours and not threes:
            if lai_zi_count < 2 or lai_zi_count == singles_len:
                return False, []

        # 3. 核心处理流程
        base_groups = [[f] * 4 for f in fours]  # 四张牌组
        remaining_lai_zi = lai_zi_count - threes_len  # 处理三张牌后剩余赖子

        # 处理三张牌组（每个三张需1赖子组成刻子）
        for t in threes:
            base_groups.append([t, t, t, lai_zi])

        # 处理单张牌（每个单张需1赖子组成对子）
        remaining_lai_zi -= singles_len
        if remaining_lai_zi < 0 or remaining_lai_zi % 2 != 0:
            return False, []
        dragon_count = len(base_groups)
        all_paths = []
        # 场景1：无剩余赖子
        if remaining_lai_zi == 0:
            path = base_groups[:]
            path.extend([[t] * 2 for t in two])
            path.extend([[s, lai_zi] for s in singles])
            all_paths.append(path)

        # 场景2：剩余2赖子
        elif remaining_lai_zi == 2:
            # 子场景2.1：无单张和对子
            if not singles and not two:
                path = base_groups[:]
                path.append([lai_zi, lai_zi])
                all_paths.append(path)
            else:
                dragon_count += 1
                # 处理对子+赖子组合
                for t_val in two:
                    path = base_groups[:]
                    path.append([t_val, t_val, lai_zi, lai_zi])
                    path.extend([[t] * 2 for t in two if t != t_val])
                    path.extend([[s, lai_zi] for s in singles])
                    all_paths.append(path)
                # 处理单张+赖子组合
                for s_val in singles:
                    path = base_groups[:]
                    path.append([s_val, lai_zi, lai_zi, lai_zi])
                    path.extend([[t] * 2 for t in two])
                    path.extend([[s, lai_zi] for s in singles if s != s_val])
                    all_paths.append(path)

        # 场景3：剩余4赖子
        elif remaining_lai_zi == 4:
            dragon_count += 2
            # 无单张/三张且仅1对子
            if not singles and not threes and two_len == 1:
                path = base_groups[:]
                path.append([lai_zi] * 4)
                path.append([two[0]] * 2)
                all_paths.append(path)
            else:
                # 生成对子组合（避免itertools）
                for i in range(two_len):
                    for j in range(i + 1, two_len):
                        path = base_groups[:]
                        path.append([two[i], two[i], lai_zi, lai_zi])
                        path.append([two[j], two[j], lai_zi, lai_zi])
                        # 添加剩余对子
                        for idx, t_val in enumerate(two):
                            if idx not in (i, j):
                                path.append([t_val] * 2)
                        all_paths.append(path)

        # 4. 确定龙类型
        dragon_type = HuType.LONG_QI_DUI
        if dragon_count == 2:
            dragon_type = HuType.DOUBLE_LONG_QI
        elif dragon_count == 3:
            dragon_type = HuType.THREE_LONG_QI

        return dragon_type, all_paths


    @staticmethod
    def get_max_score_hu_path_by_fan_ji(
            path_list: list,
            ji_to_score: dict,
            lai_zi: int,
            qing_yi_se=0,
            must_qys=False,
            is_zi_mo=False,
            cards=None,
            ying_hu_score=10,
            pai_xing_score_map=PAI_XING_SCORE_MAP
    ):
        """ 计算癞子作为鸡时的得分 """
        cards = cards or []
        max_score = 0
        max_score_path = []
        has_path = False
        for path in path_list:
            per_path_score = 0
            for idx, comb in enumerate(path, 0):
                if lai_zi not in comb:
                    for c in comb:
                        per_path_score += ji_to_score.get(c, 0)
                    continue
                all_comb_list = Rule.let_lai_zi_to_card_by_comb(lai_zi, comb)
                max_per_comb_score = 0
                has_comb = False
                for c_list in all_comb_list:  # 有癞子的所有可能组合
                    per_comb_score = 0
                    if Rule.is_shun_zi(c_list)[0]:
                        for c in c_list:
                            per_comb_score += ji_to_score.get(c, 0)  # 顺子时必须翻到金幺筒幺筒才算分
                    else:
                        # 不是顺子就是全部一样的牌
                        c_list_len = len(c_list)
                        c_list_val_1 = c_list[0]
                        if c_list_val_1 == lai_zi:  # 是癞子时可以作为分值最大的鸡
                            if must_qys:
                                # 必须是清一色
                                ji_list = list(ji_to_score.keys())
                                ji_list.sort(key=ji_to_score.get, reverse=True)
                                for ji in ji_list:
                                    if qing_yi_se == Rule.get_suit(ji):
                                        max_ji_card = ji
                                        break
                                else:
                                    max_ji_card = qing_yi_se * 10 + 1  # todo: 目前采用同花色的第一张牌
                            else:
                                # if qing_yi_se == 2:
                                #     max_ji_card = CardsType.YAO_JI
                                if qing_yi_se in (0, 3):
                                    max_ji_card = ji_to_score and max(ji_to_score, key=ji_to_score.get) or lai_zi
                                else:
                                    # 看癞子作为鸡大还是作为清一色大
                                    qing_yi_se_score = pai_xing_score_map.get(HuType.QING_YI_SE) - 5
                                    max_ji_score = max(ji_to_score.values()) * c_list_len * 3
                                    max_ji = ji_to_score and max(ji_to_score, key=ji_to_score.get)
                                    ying_hu = max_ji == lai_zi and Rule.is_ying_hu_by_hu_path(cards, path, lai_zi)
                                    if ying_hu:
                                        if is_zi_mo:
                                            ying_hu_score *= 3
                                        max_ji_score += ying_hu_score

                                    if is_zi_mo:
                                        qing_yi_se_score *= 3

                                    if qing_yi_se_score >= max_ji_score:
                                        ji_list = list(ji_to_score.keys())
                                        ji_list.sort(key=ji_to_score.get, reverse=True)
                                        for ji in ji_list:
                                            if qing_yi_se == Rule.get_suit(ji):
                                                max_ji_card = ji
                                                break
                                        else:
                                            max_ji_card = qing_yi_se * 10 + 1  # todo: 目前采用同花色的第一张牌
                                    else:
                                        max_ji_card = ji_to_score and max(ji_to_score, key=ji_to_score.get) or lai_zi

                            per_comb_score += (ji_to_score.get(max_ji_card, 0) * c_list_len)
                            c_list = [max_ji_card] * c_list_len
                        else:
                            per_comb_score += (ji_to_score.get(c_list_val_1, 0) * c_list_len)

                    if not has_comb or per_comb_score > max_per_comb_score:
                        max_per_comb_score = per_comb_score
                        path[idx] = c_list
                        has_comb = True

                per_path_score += max_per_comb_score

            if Rule.is_ying_hu_by_hu_path(cards, path, lai_zi):
                per_path_score += ying_hu_score

            if not has_path or per_path_score > max_score:
                max_score = per_path_score
                max_score_path = path
                has_path = True
        return max_score, max_score_path


    @staticmethod
    def get_hu_type_by_score(
            table_cards, cards, card, ji_to_score=None, is_zi_mo=False, lai_zi=CardsType.LAI_ZI,
            must_qys=False, pai_xing_score_map=PAI_XING_SCORE_MAP, extra_score_map=EXTRA_SCORE_MAP):
        """根据分数选取最大的得分胡牌类型 """
        ying_hu_score = extra_score_map.get(ExtraHuPai.YING_HU) or 10
        cards = list(cards)
        ji_to_score = ji_to_score or {}
        if Rule.is_card(card) and len(cards) % 3 != 2:
            cards.append(card)

        flag, path = Rule.is_jin_gou_diao(cards, lai_zi)
        if flag == HuType.JIN_GOU_DIAO:
            return flag, path

        cards_not_lai_zi = cards[:]
        lai_zi_count = Rule.remove_by_value(cards_not_lai_zi, lai_zi, -1)
        hua_se = {c // 10 for c in cards_not_lai_zi}
        qing_yi_se = hua_se.pop() if len(hua_se) == 1 else 0
        cards_len = len(cards)

        # 地龙七对
        if (cards_len == 11 and len(table_cards) == 1
                and table_cards[0][0] == ActionType.ACTION_TYPE_PENG):
            flag, path_list = Rule.is_di_long_qi_new(table_cards, cards, card, lai_zi)
            if flag:
                if table_cards[0][1] == lai_zi and card == lai_zi:
                    return flag, path_list[0]
                _, best_path = Rule.get_max_score_hu_path_by_fan_ji(
                    path_list, ji_to_score, lai_zi, qing_yi_se, must_qys, is_zi_mo, cards, ying_hu_score, pai_xing_score_map)
                return flag, best_path
        singles, two, threes, fours, _ = Rule.search_cards_by_count(cards_not_lai_zi, 1, 2, 3, 4)

        if cards_len == 14:
            # 七对
            flag1, path1_list = Rule.is_qi_dui(lai_zi, lai_zi_count, singles, two, threes, fours)
            # 龙七对
            flag2, path2_list = Rule.is_long_qi_dui(lai_zi, lai_zi_count, singles, two, threes, fours)

            if flag1 and flag2:
                score1, best_path1 = Rule.get_max_score_hu_path_by_fan_ji(
                    path1_list, ji_to_score, lai_zi, qing_yi_se, must_qys, is_zi_mo, cards, ying_hu_score, pai_xing_score_map)
                score2, best_path2 = Rule.get_max_score_hu_path_by_fan_ji(
                    path2_list, ji_to_score, lai_zi, qing_yi_se, must_qys, is_zi_mo, cards, ying_hu_score, pai_xing_score_map)
                pai_xing_score_1 = pai_xing_score_map.get(flag1, 0)
                pai_xing_score_2 = pai_xing_score_map.get(flag2, 0)
                if Rule.is_ying_hu_by_hu_path(cards, best_path1, lai_zi):
                    pai_xing_score_1 += extra_score_map.get(ExtraHuPai.YING_HU)
                if Rule.is_ying_hu_by_hu_path(cards, best_path2, lai_zi):
                    pai_xing_score_2 += extra_score_map.get(ExtraHuPai.YING_HU)
                ji_score_1 = score1 * 3
                ji_score_2 = score2 * 3
                if is_zi_mo:
                    pai_xing_score_1 *= 3
                    pai_xing_score_2 *= 3
                all_score1 = pai_xing_score_1 + ji_score_1
                all_score2 = pai_xing_score_2 + ji_score_2

                if all_score2 >= all_score1:
                    return flag2, best_path2
                return flag1, best_path1
            elif flag1:
                score1, best_path1 = Rule.get_max_score_hu_path_by_fan_ji(
                    path1_list, ji_to_score, lai_zi, qing_yi_se, must_qys, is_zi_mo, cards, ying_hu_score, pai_xing_score_map)
                return flag1, best_path1
            elif flag2:
                score2, best_path2 = Rule.get_max_score_hu_path_by_fan_ji(
                    path2_list, ji_to_score, lai_zi, qing_yi_se, must_qys, is_zi_mo, cards, ying_hu_score, pai_xing_score_map)
                # todo: 当可以是单龙和双龙时，需要看自摸以及翻鸡来决定
                if not is_zi_mo and ji_to_score.get(lai_zi, 0) > 0 and cards.count(lai_zi) >= 2:
                    # 处理双龙、三龙的情况
                    x = 0
                    if flag2 == HuType.DOUBLE_LONG_QI:
                        x = 1
                    elif flag2 == HuType.THREE_LONG_QI:
                        x = 2
                    if x > 0:
                        res, path = Rule.is_x_long(lai_zi, lai_zi_count, singles, two, threes, fours, x=x)
                        if res:
                            px_score1 = pai_xing_score_map.get(flag2, 0)
                            ji_score, path1 = Rule.get_max_score_hu_path_by_fan_ji(
                                path, ji_to_score, lai_zi, qing_yi_se, must_qys, is_zi_mo, cards, ying_hu_score, pai_xing_score_map)
                            px_score2 = pai_xing_score_map.get(res, 0)
                            if ji_score * 3 + px_score2 > score2 * 3 + px_score1:
                                return res, path1

                return flag2, best_path2

            # 大对子
        flag, path_list = Rule.is_da_dui_zi_new(cards, lai_zi, lai_zi_count, singles, two, threes, fours)
        if flag:
            if cards.count(lai_zi) == 0:
                return flag, path_list[0]
            score, best_path = Rule.get_max_score_hu_path_by_fan_ji(
                path_list, ji_to_score, lai_zi, qing_yi_se, must_qys, is_zi_mo, cards, ying_hu_score, pai_xing_score_map)
            return flag, best_path

        # 平胡
        flag, path_list = Rule.can_common_hu(cards, lai_zi)
        if flag:
            if cards.count(lai_zi) == 0:
                return HuType.PING_HU, path_list
            score, best_path = Rule.let_lai_zi_make_ji_by_ping_hu(
                cards, path_list, ji_to_score, lai_zi, qing_yi_se, must_qys, is_zi_mo)
            return HuType.PING_HU, best_path
        return False, []


    @staticmethod
    def let_lai_zi_to_card_by_comb(lai_zi, comb: list) -> list:
        """
        在胡牌的基础上检查癞子替代的牌
        替代本身返回自己，替代其它牌返回其他牌
        """
        comb_len = len(comb)
        val_1 = comb[0]
        if comb_len in (2, 4):
            if val_1 != lai_zi:
                return [[val_1] * comb_len]
            return [[lai_zi] * comb_len]
        # 31 31 31 | 31 32 33
        if Rule.is_value_ke_zi(comb):
            return [[val_1, val_1, val_1]]
        if comb_len == 3:
            # X 31, 31
            comb_copy = comb[:]
            comb_copy.sort()
            no_lz_val = comb_copy[0]
            if no_lz_val == lai_zi:
                no_lz_val = comb_copy[-1]

            if comb.count(lai_zi) == 2:
                comb_1_val = Rule.get_value(no_lz_val)
                pub_pro = [[no_lz_val, no_lz_val, no_lz_val]]
                if 2 < comb_1_val <= 7:
                    pub_pro.extend([
                        [no_lz_val - 2, no_lz_val - 1, no_lz_val],
                        [no_lz_val - 1, no_lz_val, no_lz_val + 1],
                        [no_lz_val, no_lz_val + 1, no_lz_val + 2]
                    ])
                elif comb_1_val == 1:
                    pub_pro.extend([
                        [no_lz_val, no_lz_val + 1, no_lz_val + 2],
                    ])
                elif comb_1_val == 2:
                    pub_pro.extend([
                        [no_lz_val - 1, no_lz_val, no_lz_val + 1],
                        [no_lz_val, no_lz_val + 1, no_lz_val + 2]
                    ])
                elif comb_1_val == 8:
                    pub_pro.extend([
                        [no_lz_val - 2, no_lz_val - 1, no_lz_val],
                        [no_lz_val - 1, no_lz_val, no_lz_val + 1]
                    ])
                elif comb_1_val == 9:
                    pub_pro.extend([
                        [no_lz_val - 2, no_lz_val - 1, no_lz_val]
                    ])
                return pub_pro
            # AA 癞子
            if comb.count(no_lz_val) == 2:
                return [[no_lz_val, no_lz_val, no_lz_val]]

            lz_index = comb.index(lai_zi)
            if lz_index == 1:  # 卡张
                return [[val_1, val_1 + 1, comb[-1]]]
            elif lz_index == 0:
                if Rule.get_value(comb[2]) == 9:
                    return [[comb[1] - 1, comb[1], comb[2]]]
                return [
                    [comb[1] - 1, comb[1], comb[2]],
                    [comb[1], comb[2], comb[2] + 1]
                ]
            elif lz_index == 2:
                if Rule.get_value(val_1) == 1:
                    return [[val_1, comb[1], comb[1] + 1]]
                return [
                    [val_1 - 1, val_1, comb[1]],
                    [val_1, comb[1], comb[1] + 1]
                ]
        return []


    @staticmethod
    def is_ying_hu_by_hu_path(cards: list, path: list, lai_zi: int, di_long_qi_peng_card=0):
        """
        手里有幺筒，但是胡牌时幺筒不为赖子，直接作为幺筒，也是硬胡
        di_long_qi_peng_card: 当胡牌为地龙七时 碰的那张牌（因为在算地龙七时将碰牌算进了hu path）
        """
        if not cards:
            return False
        card_to_count1 = {}
        for c in cards:
            card_to_count1[c] = card_to_count1.get(c, 0) + 1

        if not card_to_count1.get(lai_zi):
            return True

        path_cards = []
        if di_long_qi_peng_card:
            for comb in path:
                if comb[0] == di_long_qi_peng_card and len(comb) == 4:
                    path_cards.extend([di_long_qi_peng_card])  # 因为在算地龙七时将碰牌算进了hu path
                else:
                    path_cards.extend(comb)
        else:
            for comb in path:
                path_cards.extend(comb)
        card_to_count2 = {}
        for c in path_cards:
            card_to_count2[c] = card_to_count2.get(c, 0) + 1

        for c, count in card_to_count1.items():
            if card_to_count2.get(c, 0) != count:
                return False
        return True


    @staticmethod
    def is_di_long_qi_new(table_cards, cards, card, lai_zi):
        """
        地龙七
        双地龙
        三地龙
        针对遵义麻将
        """
        # 必须胡当前碰的那张牌/癞子牌
        zhuo_card = table_cards[0][1]
        if card != lai_zi:
            if card != zhuo_card:
                return False, []
        if not Rule.check_is_satisfy_di_long_qi(zhuo_card, cards, card, lai_zi):
            return False, []

        cards = list(cards)
        # 碰的癞子不能再作为任意牌
        if zhuo_card != lai_zi:
            cards.extend(table_cards[0][1:-1])
            lai_zi_count = Rule.remove_by_value(cards, lai_zi, -1)
            singles, two, threes, fours, _ = Rule.search_cards_by_count(cards, 1, 2, 3, 4)
            flag, path = Rule.is_long_qi_dui(lai_zi, lai_zi_count, singles, two, threes, fours)
            if flag == HuType.LONG_QI_DUI:
                return HuType.DI_LONG_QI, path
            elif flag == HuType.DOUBLE_LONG_QI:
                return HuType.DOUBLE_DI_LONG_QI, path
            elif flag == HuType.THREE_LONG_QI:
                return HuType.THREE_DI_LONG_QI, path
            return flag, path
        else:
            # 碰的是幺筒，地龙就只能胡幺筒
            if card != lai_zi:
                return False, []
            try:
                remove_curr_card_cards = cards[:]
                remove_curr_card_cards.remove(card)
                singles, two, threes, fours, _ = Rule.search_cards_by_count(remove_curr_card_cards, 1, 2, 3, 4)
                if singles or threes:
                    return False, []
            except Exception:
                pass
            # 碰了癞子，手里最多有1张癞子
            singles, two, threes, fours, _ = Rule.search_cards_by_count(cards, 1, 2, 3, 4)
            singles_len = len(singles)
            if singles_len == 1 and not threes:
                fours_len = len(fours)
                path = [[[f] * 4 for f in fours] + [[singles[0]] + table_cards[0][1:-1]] + [[t] * 2 for t in two]]
                if fours_len == 0:
                    return HuType.DI_LONG_QI, path
                elif fours_len == 1:
                    return HuType.DOUBLE_DI_LONG_QI, path
                elif fours_len == 2:
                    return HuType.THREE_DI_LONG_QI, path
            if singles_len == 2 and lai_zi in singles and len(threes) == 1:
                t_val = threes[0]
                path = [
                    [[f] * 4 for f in fours] + \
                    [[t_val, t_val, t_val, lai_zi]] + \
                    [[singles[0]] + table_cards[0][1:-1]] + \
                    [[t] * 2 for t in two]
                ]
                fours_len = len(fours)
                if fours_len == 0:
                    return HuType.DOUBLE_DI_LONG_QI, path
                elif fours_len == 1:
                    return HuType.THREE_DI_LONG_QI, path

            return False, []


    @staticmethod
    def check_is_satisfy_di_long_qi(zhuo_card, cards, card, lai_zi) -> bool:
        """ 检查是否满足是地龙七 """
        # 主要针对当前牌为癞子的情况
        if zhuo_card != card and card == lai_zi:
            try:
                cards = cards[:]
                cards.remove(lai_zi)
            except ValueError:
                return False

            lai_zi_count = Rule.remove_by_value(cards, lai_zi, -1)
            singles, two, threes, fours, _ = Rule.search_cards_by_count(cards, 1, 2, 3, 4)
            if not lai_zi_count:
                if not singles and not threes:
                    return True
            if lai_zi_count >= len(singles) + len(threes):
                return True
            return False

        return True


    @staticmethod
    def is_x_long(lai_zi, lai_zi_count, *args, x=1):
        """
        在已经是龙七对且有癞子的情况下查看是否时单龙
        """
        singles, two, threes, fours = args
        fours_len = len(fours)
        threes_len = len(threes)
        if fours_len + threes_len > x:
            return False, []
        singles_len = len(singles)
        threes_len = len(threes)
        res_lz_count = lai_zi_count - (singles_len + threes_len)
        if res_lz_count % 2 == 0:
            path = [
                [[t] * 4 for t in fours] +
                [[t, t, t, lai_zi] for t in threes] +
                [[t] * 2 for t in two] +
                [[s, lai_zi] for s in singles] +
                [[lai_zi] * lai_zi_count]
            ]
            # 癞子只做必要的搭，三张和单张
            if x == 1:
                hu_type = HuType.LONG_QI_DUI
            else:
                hu_type = HuType.DOUBLE_LONG_QI
            return hu_type, path
        return False, []


    @staticmethod
    def is_da_dui_zi_new(cards, lai_zi, lai_zi_count, *args):
        """ 判断是否是大对子 """
        if not cards or len(cards) % 3 != 2:
            return False, []
        singles, two, threes, fours = args
        if lai_zi_count == 0:
            if not singles and not fours and len(two) == 1:
                return HuType.DA_DUI_ZI, [[[t] * 3 for t in threes] + [[t] * 2 for t in two]]
        elif lai_zi_count > 0:
            if two and ((len(singles) + len(fours)) * 2 + (len(two) - 1) <= lai_zi_count) or \
                    ((len(singles) + len(fours)) * 2 - 1 + len(two) <= lai_zi_count):
                path = []
                pub_path = []
                all_path = []
                lz_count = lai_zi_count
                for f in fours:
                    pub_path.append([f] * 3)
                    singles.append(f)
                for t in threes:
                    pub_path.append([t] * 3)
                for s in singles:
                    path.append([s] * 2)
                    lz_count -= 1
                    for es in singles:
                        if s == es:
                            continue
                        path.append([es] * 3)
                        lz_count -= 2
                    for t in two:
                        path.append([t] * 3)
                        lz_count -= 1

                    if lz_count > 0:
                        path.append([lai_zi] * lz_count)
                    path.extend(pub_path)
                    all_path.append(path)
                    path = []
                    lz_count = lai_zi_count

                for t in two:
                    path.append([t] * 2)
                    for et in two:
                        if t == et:
                            continue
                        path.append([et] * 3)
                        lz_count -= 1
                    for s in singles:
                        path.append([s] * 3)
                        lz_count -= 2

                    if lz_count > 0:
                        path.append([lai_zi] * lz_count)
                    path.extend(pub_path)
                    all_path.append(path)
                    path = []
                    lz_count = lai_zi_count

                if lz_count >=2 and not all_path:
                    path.extend(pub_path)
                    all_path.append(path)

                return HuType.DA_DUI_ZI, all_path

        return False, []


    @staticmethod
    def let_lai_zi_make_ji_by_ping_hu(
            cards, hu_path, ji_to_score, lai_zi, qing_yi_se=0, must_qys=False, is_zi_mo=False):
        """
        在平胡的基础上优化癞子作为鸡牌的得分计算
        """
        # 1. 预先计算基础得分和鸡牌列表
        base_score, base_path = Rule.get_max_score_hu_path_by_fan_ji(
            [hu_path], ji_to_score, lai_zi, qing_yi_se, must_qys, is_zi_mo, cards)

        # 按分值降序排序鸡牌列表
        ji_list = sorted(ji_to_score, key=ji_to_score.get, reverse=True)

        # 2. 统计癞子数量
        total_lai_zi = cards.count(lai_zi)

        # 3. 初始化最佳得分和路径
        best_score = base_score
        best_path = base_path

        # 4. 内部函数：尝试替换并计算得分
        def try_replace(replace_cards, remove_cnt):
            """尝试替换癞子并计算新得分"""
            # 创建新牌列表：移除指定数量的癞子，添加替换牌
            new_cards = [c for c in cards if c != lai_zi]  # 移除所有癞子
            new_cards = new_cards[:len(cards) - remove_cnt]  # 保留正确数量
            new_cards.extend(replace_cards)  # 添加替换牌

            # 检查新牌型是否能胡
            flag_rep, new_hu_path = Rule.can_common_hu(new_cards, lai_zi)
            if not flag_rep:
                return None, None

            # 计算新胡牌路径的最大得分
            score_rep, path_rep = Rule.get_max_score_hu_path_by_fan_ji(
                [new_hu_path], ji_to_score, lai_zi, qing_yi_se, must_qys, is_zi_mo, new_cards)
            return score_rep, path_rep

        # 5. 处理硬胡情况（不使用癞子替换）
        if total_lai_zi > 0:
            # 尝试不使用癞子直接胡牌（硬胡）
            flag, ying_hu_path = Rule.can_common_hu(cards)
            if flag:
                # 获取硬胡得分（假设EXTRA_SCORE_MAP已定义）
                ying_score = EXTRA_SCORE_MAP.get(ExtraHuPai.YING_HU, 0)
                if ying_score > best_score:
                    best_score = ying_score
                    best_path = ying_hu_path

        # 6. 根据癞子数量执行不同优化策略

        # 6.1 单个癞子替换策略
        if total_lai_zi == 1:
            # 尝试用每个鸡牌替换单个癞子
            for ji in ji_list:
                score, path = try_replace([ji], 1)
                if score is not None and score > best_score:
                    best_score = score
                    best_path = path

        # 6.2 多个癞子替换策略
        elif total_lai_zi >= 2:
            # 生成所有可能的替换方案
            replace_options = []

            # 方案1: 替换两个不同的鸡牌
            for i in range(len(ji_list)):
                for j in range(i + 1, len(ji_list)):
                    replace_options.append((ji_list[i], ji_list[j]))

            # 方案2: 替换两个相同的鸡牌
            for ji in ji_list:
                replace_options.append((ji, ji))

            # 方案3: 只替换一个癞子（保留一个癞子）
            for ji in ji_list:
                replace_options.append((ji,))

            # 尝试所有替换方案
            for option in replace_options:
                # 根据替换牌数量确定移除的癞子数量
                remove_count = len(option)
                score, path = try_replace(option, remove_count)

                if score is not None and score > best_score:
                    best_score = score
                    best_path = path

        # 7. 后备方案：当所有优化尝试都不优于基础得分时
        if best_score <= base_score:
            # 拆解原胡牌路径重新组合
            hu_path_list = Rule.dismantle_hu_path(hu_path, lai_zi)
            if hu_path_list:
                s, p = Rule.get_max_score_hu_path_by_fan_ji(
                    hu_path_list, ji_to_score, lai_zi, qing_yi_se, must_qys, is_zi_mo, cards)
                if s > best_score:
                    return s, p
            else:
                # 如果后备方案也失败，返回原始结果
                return base_score, base_path

        return best_score, best_path


    @staticmethod
    def dismantle_hu_path(hu_path, lai_zi):
        """
        拆解hu path
        主要解决：[33, 34, 35, 36, 31, 32] -> [32, 33, 34, 34, 35, 36]
        """
        all_hu_path = [hu_path]
        for i, path in enumerate(hu_path):
            one_path = path[:]
            lz_count = Rule.remove_by_value(one_path, lai_zi, -1)
            if lz_count == 0:
                continue
            if len(one_path) == 1:
                continue
            one_path.sort()
            if one_path[0] + 1 == one_path[1]:
                le1_card = one_path[0] - 1
                for i1 in [i - 1, i + 1]:
                    if 0 <= i1 < len(hu_path) and le1_card in hu_path[i1]:
                        hu_path_copy = deepcopy(hu_path)
                        one_path.insert(0, le1_card)  # 顺里面最小的牌
                        hu_path_copy[i] = one_path

                        le1_card_1 = hu_path_copy[i1][0] - 1
                        le1_idx = hu_path_copy[i1].index(le1_card)
                        hu_path_copy[i1][le1_idx] = lai_zi
                        all_hu_path.append(hu_path_copy)

                        # 再进一步判断
                        i2 = i1 + 1
                        if 0 <= i2 < len(hu_path) and le1_card_1 in hu_path_copy[i2]:
                            # 把i1的癞子替换为card
                            hu_path_copy1 = deepcopy(hu_path_copy)
                            hu_path_copy1[i1][le1_idx] = le1_card_1

                            # 把i2的card替换成癞子
                            le1_idx = hu_path_copy1[i2].index(le1_card_1)
                            hu_path_copy1[i2][le1_idx] = lai_zi
                            all_hu_path.append(hu_path_copy1)

        return all_hu_path

