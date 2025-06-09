import random
from copy import deepcopy
from functools import reduce
from common.utils.utils import UtilsTool
from . import const
from .const import *
from common.utils.meta_class import NoInstances
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

        singles, _, threes, fours,count_list = Rule.search_cards_by_count(cards, 1, 2, 3, 4)
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
    def can_hu(table_cards, cards, card=0, allow_hu_map: dict = None,lai_zi=CardsType.LAI_ZI,is_gy=False,is_wu_dui=False):
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
            flag, path = Rule.is_di_long_qi(table_cards, cards, CardsType.LAI_ZI,is_gy,cal_ting_pai=True)
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
    def can_ting_pai(table_cards, hand_cards, allow_hu_map: dict, lai_zi=CardsType.LAI_ZI,is_gy=False,is_wu_dui=False):
        """
        计算是否是听牌状态
        加个癞子能胡就听牌了
        """
        cards = deepcopy(hand_cards)
        cards.append(lai_zi)  # 加入一张癞子牌
        return Rule.can_hu(table_cards, cards, allow_hu_map=allow_hu_map, lai_zi=lai_zi, is_gy = is_gy,is_wu_dui = is_wu_dui)

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
    def r_can_tian_ting(table_cards, hand_cards, mo_card=0, que=0):
        """通用天听检测方法（支持13/14张牌）"""
        for combo in table_cards:
            if combo[0] != ActionType.ACTION_TYPE_AN_GANG:
                return False

        cards = deepcopy(hand_cards)
        is_14_mode = mo_card != 0  # 是否14张牌
        if is_14_mode:
            cards.append(mo_card)
        cards.sort()

        if que > 0:
            suit_count = Poker.cal_card_suit_count(cards)
            que_count = suit_count.get(que, 0)

            # 14张牌允许1张缺门牌，13张牌禁止任何缺门牌
            max_allowed = 1 if is_14_mode else 0
            if que_count > max_allowed:
                return False
        allow_hu_map = {HuType.QI_DUI: True}
        def check_ting(cards_to_check):
            return Rule.can_ting_pai(table_cards, cards_to_check, allow_hu_map)[0]

        if is_14_mode:
            # 14张牌遍历移除每张唯一牌后检测
            seen = set()
            for card in cards:
                if card not in seen:
                    seen.add(card)
                    modified_hand = [c for c in cards if c != card]
                    if check_ting(modified_hand):
                        return True
            return False
        else:
            # 13张牌：直接检测当前牌组
            return check_ting(cards)

    @staticmethod
    def get_round_over_jiao_pai(table_cards, hand_cards,allow_hu_map: dict, curr_card=0, is_gy=False,lai_zi=0, is_wu_dui=False
    ):
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
                    table_cards, tian_ting_hand_cards, allow_hu_map,lai_zi,is_gy,is_wu_dui
                )
                if can_hu:
                    return Rule.get_jiao_type(table_cards, can_hu, hu_path, cards, curr_card)
        else:
            can_hu, hu_path = Rule.can_ting_pai(
                table_cards, cards, allow_hu_map, lai_zi,is_gy,is_wu_dui)
            if can_hu:
                return Rule.get_jiao_type(table_cards, can_hu, hu_path, cards, curr_card)
        return 0

    @staticmethod
    def get_jiao_type(table_cards, can_hu, hu_path, cards, curr_card):
        """ 在叫牌的基础上判断叫牌类型 """
        jiao_pai = HuType.PING_HU
        is_seven_pair = 0  # 七对
        is_hh_seven_pairs = 0  # 龙七对
        is_peng_peng_hu = 0  # 大对子
        is_di_long_qi = 0  # 地龙七
        is_jin_gou_diao = 0  # 金钩吊
        if can_hu == HuType.QI_DUI:
            is_seven_pair = 1
            jiao_pai = HuType.QI_DUI
            list_3 = Rule.get_card_list_by_count(cards, 3, True)
            if len(list_3) > 0:
                is_hh_seven_pairs = 1
                jiao_pai = HuType.LONG_QI_DUI
        if can_hu == HuType.DI_LONG_QI:
            is_di_long_qi = 1
            jiao_pai = HuType.DI_LONG_QI
        if can_hu == HuType.JIN_GOU_DIAO:
            is_jin_gou_diao = 1
            jiao_pai = HuType.JIN_GOU_DIAO
        if can_hu == HuType.RUAN_WU_DUI:
            jiao_pai = can_hu
        elif can_hu == HuType.YING_WU_DUI:
            jiao_pai = can_hu
        elif is_seven_pair == 0 and is_di_long_qi == 0 and is_jin_gou_diao == 0:  # 满足不是七对和地龙七才能检测是否是大对子
            is_peng_peng_hu = Rule.is_peng_peng_hu(deepcopy(hu_path))
            if is_peng_peng_hu:
                jiao_pai = HuType.DA_DUI_ZI
        is_qing_yi_se = Rule.has_hu_is_qing_yi_se(deepcopy(table_cards), cards, curr_card)

        if is_qing_yi_se:
            if is_seven_pair:
                jiao_pai = HuType.QING_QI_DUI
            elif is_hh_seven_pairs:
                jiao_pai = HuType.QING_LONG_BEI
            elif is_peng_peng_hu:
                jiao_pai = HuType.QING_DA_DUI
            elif is_di_long_qi:
                jiao_pai = HuType.QING_DI_LONG
            elif is_jin_gou_diao:
                jiao_pai = HuType.QING_JIN_GOU
            else:
                jiao_pai = HuType.QING_YI_SE
        return jiao_pai

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
        count_list, singles, two, threes, fours = Rule.search_cards_by_count(cards, 1, 2, 3, 4)
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
