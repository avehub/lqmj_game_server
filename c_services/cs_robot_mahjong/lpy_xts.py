# -*- coding: utf-8 -*-

import random
import itertools

from enum import IntEnum
from copy import deepcopy
from collections import defaultdict, Counter
from typing import Iterable

from c_services.cs_robot_mahjong.const import ACTION_TYPE_MING_GANG, FcHuPaiType, FcPileType, ACTION_TYPE_ZHUAN_WAN_GANG
from common.utils.utils import UtilsTool

LOG_PRINT = False


class TypeScore(IntEnum):
    """
    卡牌类型分数
    """
    PAIR = 35  # 对子
    KE_ZI = 115  # 刻子
    SHUN_ZI = 100  # 三顺
    GAP_CARD = 20  # 坎张
    EDGE_CARD = 19  # 边张
    XIAO_SHUN = 40  # 二顺


class Card2Type(IntEnum):
    """
    拆牌之后的最小组合
    """
    PAIR = 3  # 对子
    KE_ZI = 6  # 刻子
    SHUN_ZI = 5  # 顺子
    GAP_CARD = 2  # 坎张
    EDGE_CARD = 1  # 边张
    XIAO_SHUN = 4  # 两面(小顺)
    SINGLE_ONE = 0  # 单张


# todo: 牌组合能减少向听数的多少
# 组合能减少的向听数map,卡张|一对|小顺 减少1向听，顺子|刻子减少 2向听
# 不同组合卡牌，能减去有效向听的数量
COMB_REMOVE_XTS = {
    Card2Type.GAP_CARD: 1,  # 减去向听1
    Card2Type.EDGE_CARD: 1,  # 减去向听1
    Card2Type.PAIR: 1,  # 减去向听1
    Card2Type.XIAO_SHUN: 1,  # 减去向听1
    Card2Type.SHUN_ZI: 2,  # 减去向听(三连顺)2
    Card2Type.KE_ZI: 2,  # 减去向听(刻子)2
}


class LpyMoveGenerator:
    """
    根据拆牌后，胡牌类型计算牌面估值做出决策
    """
    __slots__ = (
        "__hand_cards",
        "__magic_card",
        "__hand_cards_len",
        "__cards_to_count",
        "__qys_flag_len",
        "__xqd_flag_len",
        "__ddz_flag_len",
        "__modify_flag",
        "__fc_hu_types",
        "__piles",
        "__others_cards_and_piles",
        "__all_hu_cards",
        "__all_played_cards",
        "__left_count",
        "__most_hand_cards_len",
        "__res_cards_to_count",
        "__others_hand_cards",
        "__the_worst_xts_by_hu_type",
        
        "__played_card2count",
        "__is_fczj",
    )

    def __init__(self):
        """
        初始化手牌参数
        """
        self.__piles = []  # 碰杠牌
        self.__others_cards_and_piles = []  # 其它玩家碰杠牌
        self.__hand_cards = []
        self.__left_count = 0
        self.__magic_card = None
        self.__hand_cards_len = 0
        self.__others_hand_cards = []
        self.__res_cards_to_count = {}

        self.__all_hu_cards = {}
        self.__all_played_cards = {}

        self.__cards_to_count = {}
        self.__the_worst_xts_by_hu_type = ...
        
        self.__played_card2count: dict = {}
        self.__is_fczj = False  # 是否是发财捉鸡

        self.__modify_flag = 7
        self.__ddz_flag_len = 2
        self.__xqd_flag_len = 3
        self.__qys_flag_len = 10
        self.__most_hand_cards_len = 14
        self.__fc_hu_types = ["lqd", "dlq", "ddz", "xqd", "jgg", "sxz", "sjg3", "byzc", "sxc", "sjg4", "zxhy"]

    @property
    def hand_cards(self):
        return self.__hand_cards

    @hand_cards.setter
    def hand_cards(self, cards):
        self.__hand_cards = cards

    @property
    def magic_card(self):
        return self.__magic_card

    @magic_card.setter
    def magic_card(self, card):
        self.__magic_card = card

    @property
    def hand_cards_len(self):
        return self.__hand_cards_len

    @hand_cards_len.setter
    def hand_cards_len(self, length):
        self.__hand_cards_len = length

    @property
    def cards_to_count(self):
        return self.__cards_to_count

    @cards_to_count.setter
    def cards_to_count(self, count):
        self.__cards_to_count = count

    @property
    def piles(self):
        return self.__piles

    @piles.setter
    def piles(self, piles):
        self.__piles = piles

    @property
    def left_count(self):
        return self.__left_count

    @left_count.setter
    def left_count(self, count):
        self.__left_count = count

    @property
    def ddz_flag_len(self):
        return self.__ddz_flag_len

    @ddz_flag_len.setter
    def ddz_flag_len(self, length):
        self.__ddz_flag_len = length

    @property
    def xqd_flag_len(self):
        return self.__xqd_flag_len

    @xqd_flag_len.setter
    def xqd_flag_len(self, length):
        self.__xqd_flag_len = length

    @property
    def qys_flag_len(self):
        return self.__qys_flag_len

    @qys_flag_len.setter
    def qys_flag_len(self, length):
        self.__qys_flag_len = length

    @property
    def most_hand_cards_len(self):
        return self.__most_hand_cards_len

    @most_hand_cards_len.setter
    def most_hand_cards_len(self, length):
        self.__most_hand_cards_len = length

    @property
    def res_cards_to_count(self):
        return self.__res_cards_to_count

    @res_cards_to_count.setter
    def res_cards_to_count(self, count):
        self.__res_cards_to_count = count

    @property
    def others_hand_cards(self):
        return self.__others_hand_cards

    @others_hand_cards.setter
    def others_hand_cards(self, cards):
        self.__others_hand_cards = cards

    @property
    def the_worst_xts_by_hu_type(self):
        return self.__the_worst_xts_by_hu_type

    @the_worst_xts_by_hu_type.setter
    def the_worst_xts_by_hu_type(self, worst_hu_types):
        self.__the_worst_xts_by_hu_type = worst_hu_types

    @property
    def fc_hu_types(self):
        return self.__fc_hu_types

    @fc_hu_types.setter
    def fc_hu_types(self, hu_types):
        self.__fc_hu_types = hu_types

    @property
    def is_fczj(self):
        return self.__is_fczj

    @is_fczj.setter
    def is_fczj(self, is_fczj: bool):
        self.__is_fczj = is_fczj



    def calc_can_xqd_pong(self, card):
        """
        处理小七对是否碰/正常牌型碰
        """
        if self.count_xqd_nums():
            return False
        return self.after_pong_xts_less(card)

    def count_xqd_nums(self):
        """
        统计小七对的数量，判断是否合适杠
        """
        if self.hand_cards_len != 13:
            return False
        count = 0
        hand_dict = self.cards_to_count_dict(self.hand_cards)
        for cards, nums in hand_dict.items():
            if nums > 1:
                count += 1
        return count if count > 3 else False

    def after_pong_xts_less(self, card) -> bool:
        """
        判断通过碰操作后向听数是否减
        """
        card_num = 2
        cards_to_count = self.count_cards_dict_res()
        if cards_to_count.get(card, 0) < card_num:
            return False
        args = self.split_cards_dict_res()
        forward_xts, _ = self.cal_xts_ping_hu(*args)
        hand_cards_copy = self.hand_cards[:]
        for _ in range(card_num):
            hand_cards_copy.remove(card)

        one_list, two_list, three_list, four_list = args
        if card_num == 2:
            if card in two_list:
                two_list.remove(card)

        self.hand_cards = hand_cards_copy
        self.the_worst_xts_by_hu_type[FcHuPaiType.PING_HU] -= 2
        need_mz = len(hand_cards_copy) // 3
        after_xts, _ = self.cal_xts_ping_hu(one_list, two_list, three_list, four_list, need_mz=need_mz)
        LOG_PRINT and print("输出碰牌之前向听数为: {}, 碰牌之后向听数为: {}".format(forward_xts, after_xts))
        if after_xts <= 0 or after_xts <= forward_xts:
            return card
        return False

    def calc_can_gang(self, card, gang_type):
        """
        计算是否杠 -> 暗杠|明杠|转弯杠
        """
        return self.after_gang_xts_less(card, gang_type)

    def after_gang_xts_less(self, card, gang_type) -> bool:
        """
        判断碰杠以后向听数是否减少
        """
        cards_to_count = self.count_cards_dict_res()
        args = self.split_cards_dict_res()
        # todo: 暗杠
        if gang_type != ACTION_TYPE_MING_GANG and (not card or isinstance(card, list)):
            can_gang = []
            if isinstance(card, list):
                can_gang = card
            else:
                for card, count in cards_to_count.items():
                    if count > 3:
                        can_gang.append(card)
            if not can_gang:
                return False
            card_num = 4
            xts_ = self.the_worst_xts_by_hu_type[FcHuPaiType.PING_HU]
            for card in can_gang:
                self.the_worst_xts_by_hu_type[FcHuPaiType.PING_HU] = xts_
                args_tup = deepcopy(args)
                forward_xts, _ = self.cal_xts_ping_hu(*args_tup)
                hand_cards_copy = self.hand_cards[:]
                for _ in range(card_num):
                    hand_cards_copy.remove(card)
                one_list, two_list, three_list, four_list = args_tup
                if card_num == 4:
                    if card in four_list:
                        four_list.remove(card)

                self.hand_cards = hand_cards_copy
                self.the_worst_xts_by_hu_type[FcHuPaiType.PING_HU] -= 2
                need_mz = len(hand_cards_copy) // 3
                after_xts, _ = self.cal_xts_ping_hu(one_list, two_list, three_list, four_list, need_mz=need_mz)
                LOG_PRINT and print("输出杠牌之前向听数为: {}, 杠牌之后向听数为: {}".format(forward_xts, after_xts))
                return card
                # if after_xts <= 0 or after_xts <= forward_xts:
                #     return card
                # return False
        # todo: 明杠/转弯杠
        else:
            card_num = 3
            if gang_type != ACTION_TYPE_MING_GANG:
                card_num = 4
                if gang_type == ACTION_TYPE_ZHUAN_WAN_GANG:
                    card_num = 1  # 转弯杠手牌仅为1张
            if cards_to_count.get(card, 0) < card_num:
                return False
            forward_xts, _ = self.cal_xts_ping_hu(*args)
            hand_cards_copy = self.hand_cards[:]
            for _ in range(card_num):
                hand_cards_copy.remove(card)

            one_list, two_list, three_list, four_list = args
            if card_num == 1:
                one_list.remove(card)
            if card_num == 3:
                three_list.remove(card)
            if card_num == 4:
                four_list.remove(card)
            self.hand_cards = hand_cards_copy
            if card_num != 1:
                self.the_worst_xts_by_hu_type[FcHuPaiType.PING_HU] -= 2
            need_mz = len(hand_cards_copy) // 3
            after_xts, _ = self.cal_xts_ping_hu(one_list, two_list, three_list, four_list, need_mz=need_mz)
            LOG_PRINT and print("输出杠牌之前向听数为: {}, 杠牌之后向听数为: {}".format(forward_xts, after_xts))
            return card
            # if after_xts <= 0 or after_xts <= forward_xts:
            #     return card
            # return False

    @staticmethod
    def judge_cards_type(cards: list):
        """
        判断卡牌组合类型
        """
        cards_len = len(cards)

        # todo: 单张(长度为1)
        if cards_len == 1:
            return Card2Type.SINGLE_ONE

        # todo: 两张[对子/边张/二顺/坎张](长度为2)
        if cards_len == 2:
            if cards[0] == cards[1]:
                return Card2Type.PAIR
            elif cards[0] + 1 == cards[1]:
                if cards[0] == 1 or cards[0] == 8:
                    return Card2Type.EDGE_CARD
                return Card2Type.XIAO_SHUN
            elif cards[0] + 2 == cards[1]:
                return Card2Type.GAP_CARD

        # todo: 三张[顺子/刻子](长度为3)
        elif cards_len == 3:
            if cards[0] == cards[1] == cards[2]:
                return Card2Type.SHUN_ZI
            elif cards[0] + 1 == cards[1] and cards[1] + 1 == cards[2]:
                return Card2Type.KE_ZI

    @staticmethod
    def calc_remain_cards(curr_hand_cards, remain_cards: dict):
        """
        统计剩余卡牌
        """
        # 出牌、碰牌、杠牌已经减去，此处不再计算
        if not remain_cards:
            return {suit * 10 + num: 4 for suit in range(1, 4) for num in range(1, 10)}
        remain_cards = {int(key): value for key, value in remain_cards.items()}
        return remain_cards

    def update_attr(
            self,
            hand_cards,
            piles=None,
            others_cards_and_piles=None,
            left_count=0,
            others_hand_cards=None,
            remain_cards=None,
            magic_card=None,
            all_hu_cards: dict = None,
            all_played_cards: dict = None,
    ):
        """
        更新参数，根据手牌数量，判断玩家胡牌类型
        """
        self.piles = piles or []
        self.__others_cards_and_piles = others_cards_and_piles or []

        self.hand_cards = hand_cards
        self.left_count = left_count or 0
        self.magic_card = magic_card or None
        self.hand_cards_len = len(self.hand_cards)
        self.others_hand_cards = others_hand_cards or []
        self.res_cards_to_count = self.calc_remain_cards(hand_cards, remain_cards)

        hu_cards_set = set()
        try:
            for value in all_hu_cards.values():
                if isinstance(value, list):
                    for item in value:
                        hu_cards_set.add(item)
                else:
                    hu_cards_set.add(value)
        except Exception as e:
            print(f"Error : {str(e)}")
        self.__all_hu_cards = hu_cards_set
        # self.__all_hu_cards = set(all_hu_cards.values())
        self.__all_played_cards = all_played_cards or {}
        self.__played_card2count = self.cards_to_count_dict(itertools.chain.from_iterable(self.__all_played_cards.values()))

        # todo: 碰杠数量(计算碰杠数)
        pong_gang_num = 4 - self.hand_cards_len // 3

        # todo: 胡牌类型 -> 平胡，大队子
        self.the_worst_xts_by_hu_type = {
            FcHuPaiType.PING_HU: (self.most_hand_cards_len - 5 - 1) - pong_gang_num * 2,
            FcHuPaiType.DA_DUI_ZI: (self.most_hand_cards_len - 5 - 1) - pong_gang_num * 2,
        }

        # todo: 胡牌类型 -> 七对，龙七对
        if self.hand_cards_len == self.most_hand_cards_len:
            self.the_worst_xts_by_hu_type[FcHuPaiType.QI_DUI] = (self.most_hand_cards_len // 2) - 1
            self.the_worst_xts_by_hu_type[FcHuPaiType.LONG_QI_DUI] = (self.most_hand_cards_len // 2) - 1

    def match_ping_hu(self, *args):
        """
        平胡/金钩钓(手牌只剩余1张)
        """
        return self.cal_xts_ping_hu(*args)

    def match_da_dui_zi(self, *args):
        """
        大对子/清大对/三星照/三节高/四节高/八音坐唱/四喜财/知行和一
        """
        if not self.magic_card:
            return self.cal_xts_da_dui_zi_normal(*args)
        return self.calc_xts_da_dui_zi_lai_zi(*args)

    def match_qi_dui(self, *args):
        """
        七对/清七对
        """
        if not self.magic_card:
            return self.cal_xts_by_qi_dui_normal(*args)
        return self.cal_xts_by_qi_dui_lai_zi(*args)

    def match_long_qi_dui(self, *args):
        """
        龙七对/清龙七对
        """
        if not self.magic_card:
            return self.cal_xts_by_long_qi_dui_normal(*args)
        return self.calc_xts_by_long_qi_dui_lai_zi(*args)

    def split_piles(self):
        """
        切割碰/杠卡牌
        """
        res = []
        for cards in self.piles:
            res.extend(list(set(cards[1:-1])))
        return res

    def count_piles_gang_res(self, gang_type):
        """
        碰/杠(明杠，转弯杠，暗杠)
        """
        gang_res = {
            FcPileType.PILE_PENG: 0,
            FcPileType.PILE_MING_GANG: 0,
            FcPileType.PILE_ZHUAN_WAN_GANG: 0,
            FcPileType.PILE_AN_GANG: 0
        }
        for cards in self.piles:
            if not gang_res.get(cards[0], 0):
                continue
            gang_res[cards[0]] += 1
        return gang_res.get(gang_type, 0)

    @staticmethod
    def is_continuous(cards):
        """
        判断传入的值是否连续
        """
        cards = sorted(cards)
        for i in range(len(cards) - 1):
            if cards[i + 1] - cards[i] != 1:
                return False
        return True

    def calc_normal_build_types(self):
        """
        计算卡牌组成类型及向听数
        """
        all_best_cards, all_xts_cards = [], []
        # args = [[单张], [对子], [刻子], [四张]]
        args = self.split_cards_dict_res()
        LOG_PRINT and print("卡牌及张数: ", sorted(self.hand_cards), self.hand_cards_len)
        LOG_PRINT and print()

        # todo: 1.平胡向听数及最佳出牌
        xts1, ping_hu_best_cards = self.match_ping_hu(*args)
        all_best_cards.extend(ping_hu_best_cards)
        all_xts_cards.append(("ph", xts1, ping_hu_best_cards))
        LOG_PRINT and print(f"平胡向听数: {xts1}, 最优出牌: {ping_hu_best_cards}")
        LOG_PRINT and print()

        # todo: 2.大对子/三星照/三节高/四节高/八音坐唱/四喜财/知行和一向听数及最佳出牌
        # 2.1 计算大对子向听数及最优出牌
        ddz_case = [
            len(args[1] + args[2]) + len(self.split_piles()) > self.xqd_flag_len,
            len(args[1]) + len(self.split_piles()) > self.ddz_flag_len,
            len(args[2]) + len(self.split_piles()) > self.ddz_flag_len,
            len(args[1] + args[2]) > self.ddz_flag_len
        ]
        if any(ddz_case):
            xts2, best_cards2 = self.match_da_dui_zi(*args)
            all_best_cards.extend(best_cards2)
            all_xts_cards.append(("ddz", xts2, best_cards2))
            LOG_PRINT and print(f"大对子向听数: {xts2}, 最优出牌: {best_cards2}")
            LOG_PRINT and print()

        # 2.2 计算三星照向听数及最佳出牌
        sxz_case = [
            len(args[2]) == self.ddz_flag_len,
            self.count_piles_gang_res(FcPileType.PILE_AN_GANG) == self.ddz_flag_len
        ]
        if any(sxz_case):
            xts3, best_cards3 = self.match_da_dui_zi(*args)
            all_best_cards.extend(best_cards3)
            all_xts_cards.append(("sxz", xts3, best_cards3))
            LOG_PRINT and print(f"三星照向听数: {xts3}, 最优出牌: {best_cards3}")
            LOG_PRINT and print()

        # 2.3 计算四喜财向听数及最佳出牌
        sxc_case = [
            len(args[2]) == self.xqd_flag_len,
            self.count_piles_gang_res(FcPileType.PILE_AN_GANG) == self.xqd_flag_len
        ]
        if any(sxc_case):
            xts4, best_cards4 = self.match_da_dui_zi(*args)
            all_best_cards.extend(best_cards4)
            all_xts_cards.append(("sxc", xts4, best_cards4))
            LOG_PRINT and print(f"四喜财向听数: {xts4}, 最优出牌: {best_cards4}")
            LOG_PRINT and print()

        # 2.4 计算八音坐唱向听数及最佳出牌
        mg_count = self.count_piles_gang_res(FcPileType.PILE_MING_GANG)
        zw_count = self.count_piles_gang_res(FcPileType.PILE_ZHUAN_WAN_GANG)
        ag_count = self.count_piles_gang_res(FcPileType.PILE_AN_GANG)
        if mg_count + zw_count + ag_count > self.ddz_flag_len:
            xts5, best_cards5 = self.match_da_dui_zi(*args)
            all_best_cards.extend(best_cards5)
            all_xts_cards.append(("byzc", xts5, best_cards5))
            LOG_PRINT and print(f"八音坐唱向听数: {xts5}, 最优出牌: {best_cards5}")
            LOG_PRINT and print()

        # 2.5 计算知行合一向听数及最佳出牌
        if mg_count + zw_count + ag_count == self.xqd_flag_len:
            xts6, best_cards6 = self.match_da_dui_zi(*args)
            all_best_cards.extend(best_cards6)
            all_xts_cards.append(("zxhy", xts6, best_cards6))
            LOG_PRINT and print(f"知行合一向听数: {xts6}, 最优出牌: {best_cards6}")
            LOG_PRINT and print()

        # 2.6 计算三节高向听数及最佳出牌
        sjg_case = args[2] + self.split_piles()
        if len(sjg_case) > self.ddz_flag_len - 1:
            if self.is_continuous(sjg_case) and self.calc_qing_yi_se(sjg_case):
                xts7, best_cards7 = self.match_da_dui_zi(*args)
                all_best_cards.extend(best_cards7)
                all_xts_cards.append(("sjg3", xts7, best_cards7))
                LOG_PRINT and print(f"三节高向听数: {xts7}, 最优出牌: {best_cards7}")
                LOG_PRINT and print()

        # 2.7 计算四节高向听数及最佳出牌
        if len(sjg_case) > self.xqd_flag_len - 1:
            if self.is_continuous(sjg_case) and self.calc_qing_yi_se(sjg_case):
                xts8, best_cards8 = self.match_da_dui_zi(*args)
                all_best_cards.extend(best_cards8)
                all_xts_cards.append(("sjg4", xts8, best_cards8))
                LOG_PRINT and print(f"四节高向听数: {xts8}, 最优出牌: {best_cards8}")
                LOG_PRINT and print()

        # todo: 3七对/龙七对
        if self.hand_cards_len == 14:
            # 3.1 计算七对向听数及最佳出牌
            if len(args[1]) > self.ddz_flag_len:
                xts9, best_cards9 = self.match_qi_dui(*args)
                all_best_cards.extend(best_cards9)
                all_xts_cards.append(("xqd", xts9, best_cards9))
                if LOG_PRINT:
                    print(f"小七对向听数: {xts9}, 最优出牌: {best_cards9}")
                    print()

            # 3.2 计算龙七对向听数及最佳出牌
            if len(args[1]) > self.ddz_flag_len and len(args[2]) == 1:
                xts10, best_cards10 = self.calc_xts_by_long_qi_dui_lai_zi(*args)
                all_best_cards.extend(best_cards10)
                all_xts_cards.append(("lqd", xts10, best_cards10))
                if LOG_PRINT:
                    print(f"龙七对向听数: {xts10}, 最优出牌: {best_cards10}")
                    print()

        return all_best_cards, all_xts_cards, ping_hu_best_cards

    def calc_qing_yi_se_build_types(self):
        """
        计算清一色卡牌组成类型及向听数
        """
        all_best_cards, all_xts_cards = [], []
        # args = [[单张], [对子], [刻子], [四张]]
        args = self.split_cards_dict_res()
        LOG_PRINT and print("卡牌及张数: ", self.hand_cards, self.hand_cards_len)

        # todo: 1.清一色 -> 平胡
        xts1, best_cards1 = self.match_ping_hu(*args)
        all_best_cards.extend(best_cards1)
        all_xts_cards.append(("ph", xts1, best_cards1))
        LOG_PRINT and print(f"清一色 -> 平胡向听数: {xts1}, 最优出牌: {best_cards1}")
        LOG_PRINT and print()

        # todo: 2.清一色 -> 大对子/三星照/三节高/四节高/八音坐唱/四喜财/知行和一向听数及最佳出牌
        # 2.1 计算大对子向听数及最优出牌
        ddz_case = [
            len(args[1] + args[2]) + len(self.split_piles()) > self.xqd_flag_len,
            len(args[1]) + len(self.split_piles()) > self.ddz_flag_len,
            len(args[2]) + len(self.split_piles()) > self.ddz_flag_len,
            len(args[1] + args[2]) > self.ddz_flag_len
        ]
        if any(ddz_case):
            xts2, best_cards2 = self.match_da_dui_zi(*args)
            all_best_cards.extend(best_cards2)
            all_xts_cards.append(("ddz", xts2, best_cards2))
            LOG_PRINT and print(f"清一色 -> 大对子向听数: {xts2}, 最优出牌: {best_cards2}")
            LOG_PRINT and print()

        # 2.2 计算三星照向听数及最佳出牌
        sxz_case = [
            len(args[2]) == self.ddz_flag_len,
            self.count_piles_gang_res(FcPileType.PILE_AN_GANG) == self.ddz_flag_len
        ]
        if any(sxz_case):
            xts3, best_cards3 = self.match_da_dui_zi(*args)
            all_best_cards.extend(best_cards3)
            all_xts_cards.append(("sxz", xts3, best_cards3))
            LOG_PRINT and print(f"清一色 -> 三星照向听数: {xts3}, 最优出牌: {best_cards3}")
            LOG_PRINT and print()

        # 2.3 计算四喜财向听数及最佳出牌
        sxc_case = [
            len(args[2]) == self.xqd_flag_len,
            self.count_piles_gang_res(FcPileType.PILE_AN_GANG) == self.xqd_flag_len
        ]
        if any(sxc_case):
            xts4, best_cards4 = self.match_da_dui_zi(*args)
            all_best_cards.extend(best_cards4)
            all_xts_cards.append(("sxc", xts4, best_cards4))
            LOG_PRINT and print(f"清一色 -> 四喜财向听数: {xts4}, 最优出牌: {best_cards4}")
            LOG_PRINT and print()

        # 2.4 计算八音坐唱向听数及最佳出牌
        mg_count = self.count_piles_gang_res(FcPileType.PILE_MING_GANG)
        zw_count = self.count_piles_gang_res(FcPileType.PILE_ZHUAN_WAN_GANG)
        ag_count = self.count_piles_gang_res(FcPileType.PILE_AN_GANG)
        if mg_count + zw_count + ag_count == self.ddz_flag_len:
            xts5, best_cards5 = self.match_da_dui_zi(*args)
            all_best_cards.extend(best_cards5)
            all_xts_cards.append(("byzc", xts5, best_cards5))
            LOG_PRINT and print(f"清一色 -> 八音坐唱向听数: {xts5}, 最优出牌: {best_cards5}")
            LOG_PRINT and print()

        # 2.5 计算知行合一向听数及最佳出牌
        if mg_count + zw_count + ag_count == self.xqd_flag_len:
            xts6, best_cards6 = self.match_da_dui_zi(*args)
            all_best_cards.extend(best_cards6)
            all_xts_cards.append(("zxhy", xts6, best_cards6))
            LOG_PRINT and print(f"清一色 -> 知行合一向听数: {xts6}, 最优出牌: {best_cards6}")
            LOG_PRINT and print()

        # 2.6 计算三节高向听数及最佳出牌
        sjg_case = args[2] + self.split_piles()
        if len(sjg_case) > self.ddz_flag_len - 1:
            if self.is_continuous(sjg_case) and self.calc_qing_yi_se(sjg_case):
                xts7, best_cards7 = self.match_da_dui_zi(*args)
                all_best_cards.extend(best_cards7)
                all_xts_cards.append(("sjg3", xts7, best_cards7))
                LOG_PRINT and print(f"清一色 -> 三节高向听数: {xts7}, 最优出牌: {best_cards7}")
                LOG_PRINT and print()

        # 2.7 计算四节高向听数及最佳出牌
        if len(sjg_case) > self.xqd_flag_len - 1:
            if self.is_continuous(sjg_case) and self.calc_qing_yi_se(sjg_case):
                xts8, best_cards8 = self.match_da_dui_zi(*args)
                all_best_cards.extend(best_cards8)
                all_xts_cards.append(("sjg4", xts8, best_cards8))
                LOG_PRINT and print(f"清一色 -> 四节高向听数: {xts8}, 最优出牌: {best_cards8}")
                LOG_PRINT and print()

        # todo: 3七对/龙七对
        if self.hand_cards_len == 14:
            # 3.1 计算七对向听数及最佳出牌
            if len(args[1]) > self.ddz_flag_len:
                xts9, best_cards9 = self.match_qi_dui(*args)
                all_best_cards.extend(best_cards9)
                all_xts_cards.append(("xqd", xts9, best_cards9))
                LOG_PRINT and print(f"清一色 -> 小七对向听数: {xts9}, 最优出牌: {best_cards9}")
                LOG_PRINT and print()

            # 3.2 计算龙七对向听数及最佳出牌
            if len(args[1]) > self.ddz_flag_len and len(args[2]) == 1:
                xts10, best_cards10 = self.calc_xts_by_long_qi_dui_lai_zi(*args)
                all_best_cards.extend(best_cards10)
                all_xts_cards.append(("lqd", xts10, best_cards10))
                LOG_PRINT and print(f"清一色 -> 龙七对向听数: {xts10}, 最优出牌: {best_cards10}")
                LOG_PRINT and print()

        return all_best_cards, all_xts_cards, best_cards1

    def exclude_history_hu_cards_and_lai_zi(self, cards: list):
        ori_cards = cards[:]
        for c in self.__all_hu_cards:
            if c in cards:
                cards.remove(c)
        for c in cards:
            if c == self.magic_card:
                cards.remove(c)
        cards = cards or ori_cards

        played_cards = []
        for c in cards:
            if c in self.__played_card2count:
                played_cards.append(c)
        if played_cards:
            played_cards.sort(key=self.__played_card2count.get)
            return played_cards[-1]
        if not cards:
            return cards
        return cards[-1]

    def calc_xts_by_max_hu_type(self):
        """
        todo: 根据向听数构建大牌胡牌类型，清一色 or 非清一色
            1.清一色胡牌类型
            2.非清一色胡牌类型
            3.清一色: 同一花色数量 > 9
            4.七对: 对子数量 > 4
            5.大对: 对子数量 + 刻子数量 > 3
        """
        # 判断清一色牌型是否符合条件，清一色牌型分为玩家未进行过碰、杠或进行过碰、杠
        other_cards_and_piles = self.__others_cards_and_piles or []
        curr_cards_res, qing_yi_se_res = self.decide_qing_yi_se_by_res(other_cards_and_piles)

        # todo: 1.计算清一色牌型所有出牌，有效牌
        if len(curr_cards_res.keys()) == 1 and qing_yi_se_res:
            all_best_cards, all_xts_cards, ping_hu_best_cards = self.calc_qing_yi_se_build_types()
            if not all_best_cards:
                # todo: 处理万能牌
                tmp_hand_cards = self.hand_cards[:]
                return self.exclude_history_hu_cards_and_lai_zi(tmp_hand_cards)
            if len(all_xts_cards) == 1:
                return self.exclude_history_hu_cards_and_lai_zi(all_best_cards)
            if len(all_xts_cards) > 1:
                return self.calc_best_play_card(all_xts_cards, ping_hu_best_cards)
            return self.calc_xts_by_normal_best_cards()

        # todo: 2.根据当前玩家持有花色手牌结果，决定是否做清一色牌型
        if qing_yi_se_res:
            qys_res = self.make_qing_yi_se_type(curr_cards_res)
            if qys_res:
                return qys_res
        # todo: 3.上面条件不满足(不是清一色，也不能做清一色牌型)，则选择最佳胡牌牌型
        return self.calc_xts_by_normal_best_cards()

    def decide_qing_yi_se_by_res(self, other_cards_and_piles):
        """
        判断其他玩家当前卡牌所有清一色情况，当前清一色牌型是否被影响
        """
        # 判断当前玩家清一色牌型条件是否符合
        curr_qing_yi_se_type = False
        curr_qing_yi_se_res = self.calc_qing_yi_se(self.hand_cards)
        for curr_type, curr_cards in curr_qing_yi_se_res.items():
            if len(curr_cards) > self.qys_flag_len - 1:
                curr_qing_yi_se_type = curr_type
                break
            curr_pong_gong_res = self.decide_pong_gang_type_res(curr_type)
            if curr_pong_gong_res:
                if len(curr_pong_gong_res) + len(curr_cards) > self.qys_flag_len:
                    curr_qing_yi_se_type = curr_type
                    break
        # 判断比较当前玩家清一色牌型与其他两位玩家牌型，存在同一种花色，则不做清一色牌型
        if len(curr_qing_yi_se_res.keys()) == 1 or curr_qing_yi_se_type:
            compare_infos, compare_res = self.compare_qing_yi_se_res(other_cards_and_piles, curr_qing_yi_se_type)
            if not compare_infos and not compare_res:
                if curr_qing_yi_se_type or len(list(curr_qing_yi_se_res.keys())) == 1:
                    return curr_qing_yi_se_res, curr_qing_yi_se_type
        return {}, False

    def compare_qing_yi_se_res(self, other_cards_and_piles, curr_qing_yi_se_type):
        """
        当前玩家满足清一色牌型，开始与其他两位玩家比较牌型花色
        """
        # 其他玩家持有手牌与碰杠卡牌
        for other_infos in other_cards_and_piles:
            other_pong_gong_cards = sum([pile[1:-1] for pile in other_infos[-1]], [])
            other_pong_gong_cards_res = self.calc_qing_yi_se(other_pong_gong_cards)
            other_hand_cards_res = self.calc_qing_yi_se(other_infos[0])
            # 判断当前玩家花色，与另外一位玩家牌型花色
            other_hand_cards = other_hand_cards_res[curr_qing_yi_se_type]
            # 判断另外一位玩家碰/杠加上手牌时形成的花色与当前玩家进行比较
            # 存在与当前玩家的同一花色，并且进行了碰/杠操作
            if other_hand_cards and other_pong_gong_cards:
                other_case_res = [
                    len(other_pong_gong_cards_res.keys()) == 1,
                    list(other_pong_gong_cards_res.keys())[0] == curr_qing_yi_se_type
                ]
                if all(other_case_res):
                    if len(other_pong_gong_cards) + len(other_hand_cards) > self.qys_flag_len + 1:
                        return other_hand_cards_res, False
            # 判断另外一位玩家手牌形成的花色与当前玩家进行比较，无碰杠
            for hd_type, hd_cards in other_hand_cards_res.items():
                if hd_type == curr_qing_yi_se_type and len(hd_cards) > self.qys_flag_len:
                    return other_hand_cards_res, False
        return None, False

    def make_qing_yi_se_type(self, curr_cards_res):
        """
        构建清一色牌型
        """
        # 判断当前清一色是否进行过碰/杠
        if self.left_count > self.__modify_flag:
            tmp_hand_cards = self.hand_cards[:]
            # todo: 处理做清一色牌型时，
            for lai_zi in self.hand_cards:
                if self.magic_card == lai_zi:
                    tmp_hand_cards.remove(self.magic_card)
            for curr_type, curr_cards in curr_cards_res.items():
                if self.piles:
                    pong_gang_cards = self.decide_pong_gang_type_res(curr_type)
                    if len(pong_gang_cards) + len(curr_cards) > self.qys_flag_len:
                        LOG_PRINT and print("构建清一色牌型: ", self.hand_cards, self.hand_cards_len)
                        LOG_PRINT and print("同一花色色牌型: ", curr_cards, len(curr_cards))
                        choose_card = list(set(tmp_hand_cards).difference(set(curr_cards)))
                        if not self.is_fczj:
                            copy_choose_card = choose_card[:]
                            for card in copy_choose_card:
                                if card in self.__all_hu_cards:
                                    choose_card.remove(card)
                        if not choose_card:
                            return None
                        return random.choice(choose_card)
                if len(curr_cards) > self.qys_flag_len:
                    LOG_PRINT and print("构建清一色牌型: ", self.hand_cards, self.hand_cards_len)
                    LOG_PRINT and print("同一花色色牌型: ", curr_cards, len(curr_cards))
                    choose_card = list(set(tmp_hand_cards).difference(set(curr_cards)))
                    if not self.is_fczj:
                        copy_choose_card = choose_card[:]
                        for card in copy_choose_card:
                            if card in self.__all_hu_cards:
                                choose_card.remove(card)
                    if not choose_card:
                        return None
                    return random.choice(choose_card)
        return None

    def calc_qing_yi_se(self, cards):
        """
        检查手牌是否都是同一颜色
        """
        tmp_hand_cards = cards[:]
        cards_type = defaultdict(list)
        for card in tmp_hand_cards:
            if card == self.magic_card:
                continue
            card_type = card // 10
            cards_type[card_type].append(card)
        return cards_type

    @staticmethod
    def control_play_card(best_cards, xts_yxp_cards):
        """
        通过概率分布来控制最佳出牌
        """
        best_card = random.choice(best_cards)
        other_cards = random.choice(xts_yxp_cards)
        return int(UtilsTool.random_choice_num([best_card, other_cards], [0.01, 0.99]))

    def decide_pong_gang_type_res(self, curr_type):
        """
        判断当前卡牌与碰杠卡牌是否为同一花色
        """
        pong_gong_cards = sum([pile[1:-1] for pile in self.piles], [])
        count_type_res = list(self.calc_qing_yi_se(pong_gong_cards).keys())
        if len(count_type_res) == 1 and count_type_res[0] == curr_type:
            return pong_gong_cards
        return []

    def calc_best_play_card(self, all_xts_cards, ping_hu_best_cards):
        """
        判断是否选择大牌做牌类型及出牌
        """
        min_xts = sorted(all_xts_cards, key=lambda x: x[1])
        xts_yxp_cards = sum([xts_yxp[2] for xts_yxp in all_xts_cards], [])
        # 判断剩余卡牌是否还满足做大牌条件
        if self.left_count < (self.__modify_flag * 2) - 2:
            eq_cards = [x for x in xts_yxp_cards if xts_yxp_cards.count(x) > 1]
            eq_cards_copy = eq_cards[:]
            for card in eq_cards_copy:
                if card in self.__all_hu_cards:
                    eq_cards.remove(card)
            if eq_cards:
                return self.exclude_history_hu_cards_and_lai_zi(eq_cards)
            if min_xts[0][2]:
                return self.exclude_history_hu_cards_and_lai_zi(min_xts[0][2])
            if xts_yxp_cards:
                return self.exclude_history_hu_cards_and_lai_zi(xts_yxp_cards)

            tmp_hand_cards = self.hand_cards[:]
            return self.exclude_history_hu_cards_and_lai_zi(tmp_hand_cards)

        # todo: 开始构建较大牌型组合并选择最优出牌
        for yxp_infos in min_xts:
            if yxp_infos[1] < 0:
                if len(min_xts) == 1 and yxp_infos[0] == "ph":
                    return self.exclude_history_hu_cards_and_lai_zi(yxp_infos[2])
                elif len(min_xts) > 1 and yxp_infos[0] != "ph":
                    return self.exclude_history_hu_cards_and_lai_zi(yxp_infos[2])
            if yxp_infos[1] < self.xqd_flag_len and yxp_infos[0] != "ph":
                if yxp_infos[0] in self.fc_hu_types:
                    eq_card = list(set(ping_hu_best_cards) & set(yxp_infos[2]))
                    best_cards = [x for x in xts_yxp_cards if xts_yxp_cards.count(x) > 1]
                    if eq_card:
                        return self.exclude_history_hu_cards_and_lai_zi(eq_card)
                    if yxp_infos[2]:
                        return self.exclude_history_hu_cards_and_lai_zi(yxp_infos[2])
                    if not ping_hu_best_cards and not xts_yxp_cards:
                        # todo: 万能牌不能出，直接删除
                        tmp_hand_cards = self.hand_cards[:]
                        return self.exclude_history_hu_cards_and_lai_zi(tmp_hand_cards)
                    if not best_cards or not xts_yxp_cards:
                        return self.exclude_history_hu_cards_and_lai_zi(best_cards + xts_yxp_cards)

                    # 看一下哪张牌打得最多打哪张
                    return self.exclude_history_hu_cards_and_lai_zi(xts_yxp_cards)

        # todo: 按最小数组合选择最优出牌
        if min_xts[0][2]:
            return self.exclude_history_hu_cards_and_lai_zi(min_xts[0][2])
        if xts_yxp_cards:
            return self.exclude_history_hu_cards_and_lai_zi(xts_yxp_cards)
        # todo: 万能牌不能出，直接删除
        tmp_hand_cards = self.hand_cards[:]
        return self.exclude_history_hu_cards_and_lai_zi(tmp_hand_cards)

    def calc_xts_by_normal_best_cards(self):
        """
        根据向听数大小，牌型优先级别为: 清一色、龙七对、大对子、小七对
        """
        all_best_cards, all_xts_cards, ping_hu_best_cards = self.calc_normal_build_types()
        # 仅存在一张胡牌牌型
        if len(all_xts_cards) == 1:
            if all_xts_cards[0][1] < 0:
                return random.choice(ping_hu_best_cards or all_best_cards)
            all_cards_by_xts = all_xts_cards[0][-1]
            all_cards_by_xts.sort(key=lambda x: self.__played_card2count.get(x, 0))
            # 看一下哪张牌打得最多打哪张
            return all_cards_by_xts[-1]

        # 存在多种胡牌牌型
        if len(all_xts_cards) > 1:
            return self.calc_best_play_card(all_xts_cards, ping_hu_best_cards)

    def cal_xts_ping_hu(self, *args, need_mz=None):
        """
        计算平胡向听数判断平胡
        """
        # 胡牌类型(平胡)
        # 参数解析(单张、两张、三张、四张)
        one_list, two_list, three_list, four_list = args

        # 面子(顺子、刻子)
        # 平胡: 1个对子 + 4个面子 -> (2 + 3 x 4) = 14
        need_mz = need_mz or self.hand_cards_len // 3
        need_heap = need_mz if need_mz > 0 else 0  # 需要多少堆
        optimal_path = []

        record_lowest_xts = 8  # 最小的向听数（仅平胡）用于全局记录最低的向听数
        the_worst_xts = self.the_worst_xts_by_hu_type.get(FcHuPaiType.PING_HU)  # 当前牌的最坏向听数（减去了碰杠）
        jiang_list = two_list + three_list + four_list  # 不添单张(计算大于两张的卡牌)

        # if not two_list:
        # 先统计将牌
        jiang_list += one_list
        for pair in jiang_list:  # 列表相加得到新实例
            new_hand_cards = self.hand_cards[:]
            # 当做将的对子不是从刻子中取的，则先拆刻子
            self.remove_by_value(new_hand_cards, pair, 2)  # 减去对子（平胡只能有一个将）
            # 将牌数量为单/双
            if pair in one_list:
                split_path = [[pair]]
            else:
                split_path = [[pair] * 2]

            # print(f"对子(将牌): {pair}, 所需搭子数: {need_heap}")

            def optimal_split_cards(hand_cards):
                """
                todo: 最优拆牌
                params: new_hand_cards  去掉对子/刻子的手牌
                params: optimal_path 最优路径
                params: all_split_cards 所有组合
                params: need_heap  需要堆数
                """
                nonlocal self
                nonlocal optimal_path
                nonlocal record_lowest_xts
                nonlocal need_heap
                nonlocal split_path

                # 减去 对子/刻子 后的所有搭子
                # todo: 遍历找出顺子
                all_split_cards = []
                hand_cards_copy = hand_cards[:]
                count = 0
                extra_shun = []
                while hand_cards_copy:
                    # 此操作为了找出所有的顺子（包含小顺）
                    single_cards = sorted(list(set(hand_cards_copy)))
                    for sc in single_cards:
                        hand_cards_copy.remove(sc)

                    # 计算所有顺子(三连顺，二连顺，咔张)
                    all_shun = self.gen_serial_moves(single_cards)
                    if count > 0:
                        # all_shun = [shun for shun in all_shun if len(shun) == 3]
                        extra_shun.extend(all_shun)
                    if not all_shun:
                        break
                    all_split_cards.extend(all_shun)
                    count += 1

                # 计算每一张手牌对应的数量(统计当前卡牌数量)
                new_cards_to_count = self.count_cards_dict_res(hand_cards)
                # 当前卡牌是否被切割重组
                if not all_split_cards:
                    if record_lowest_xts < the_worst_xts:
                        return
                    record_lowest_xts = the_worst_xts
                    res_split_cards = split_path[:]
                    for card, count in new_cards_to_count.items():
                        count > 0 and res_split_cards.append([card] * count)
                    optimal_path.append((record_lowest_xts, res_split_cards))
                # 当前卡牌已被切割重组
                else:
                    all_can_comb_shun_cards = []
                    for shun in all_split_cards:
                        all_can_comb_shun_cards.extend(shun)
                    # 去掉已经组合后产生重复的卡牌
                    all_can_comb_shun_cards = list(set(all_can_comb_shun_cards))
                    if extra_shun:
                        es_shun_cards = []
                        for es in extra_shun:
                            es_shun_cards.extend(es)
                        all_can_comb_shun_cards.extend(list(set(es_shun_cards)))

                    new_cards_to_count_copy = new_cards_to_count.copy()
                    # 移除已经使用过的卡牌
                    for s in all_can_comb_shun_cards:
                        if s in new_cards_to_count:
                            new_cards_to_count_copy[s] -= 1
                    extra_comb = []

                    # 计算刻子
                    for card, count in new_cards_to_count_copy.items():
                        if count > 0:
                            # 刻子统一在下面添加，此处可能原本刻子被拆了
                            if count == 3 and card in three_list:
                                continue
                            extra_comb.append([card] * count)

                    # 计算额外的对子
                    extra_pair = []
                    for two in two_list:
                        if two == pair:
                            continue
                        two_val = LpyMoveGenerator.get_value(two)
                        if two_val == 1:
                            if new_cards_to_count_copy.get(two + 1) or new_cards_to_count_copy.get(two + 2):
                                extra_pair.append([two] * 2)
                        elif two_val == 2:
                            if new_cards_to_count_copy.get(two - 1) or new_cards_to_count_copy.get(
                                    two + 1) or new_cards_to_count_copy.get(two + 2):
                                extra_pair.append([two] * 2)
                        elif two_val == 8:
                            if new_cards_to_count_copy.get(two + 1) or new_cards_to_count_copy.get(
                                    two - 1) or new_cards_to_count_copy.get(two - 2):
                                extra_pair.append([two] * 2)
                        elif two_val == 9:
                            if new_cards_to_count_copy.get(two - 1) or new_cards_to_count_copy.get(two - 2):
                                extra_pair.append([two] * 2)
                        else:
                            if new_cards_to_count_copy.get(two - 1) or new_cards_to_count_copy.get(two - 2) or \
                                    new_cards_to_count_copy.get(two + 1) or new_cards_to_count_copy.get(two + 2):
                                extra_pair.append([two] * 2)

                    # 添加重组后的额外对子、刻子、连顺
                    all_split_cards.extend(extra_pair)
                    ke_zi = [[card] * 3 for card in three_list + four_list if card != pair]  # 刻子也添加进去
                    all_split_cards.extend(ke_zi)
                    all_split_cards.extend(extra_comb)

                    # 先拆顺子
                    # todo: 再计算搭子(二连顺、间隔顺)
                    curr_heap_idx = 0  # 当前堆的索引
                    record_comb = ...
                    all_comb = itertools.combinations(range(len(all_split_cards)), need_heap)
                    # all_comb_list = list(all_comb)
                    # print("所有组合长度: ", len(all_comb_list), all_comb_list)
                    for comb in all_comb:
                        if comb[:curr_heap_idx + 1] == record_comb:
                            continue
                        # 统计每一张手牌数量
                        cards_to_count_copy = new_cards_to_count.copy()
                        comb_list = []
                        curr_heap_idx = 0
                        record_comb = ...
                        flag = True
                        # 根据所需的搭子数，计算搭子
                        for i in range(need_heap):
                            curr_heap_idx = i
                            one_comb = all_split_cards[comb[i]]
                            for oc in one_comb:
                                if cards_to_count_copy.get(oc, 0) <= 0:
                                    flag = False
                                    record_comb = comb[:i + 1]
                                    break
                                cards_to_count_copy[oc] -= 1
                            if not flag:
                                comb_list.clear()
                                break
                            comb_list.append(one_comb)

                        if comb_list:
                            res_split_cards = []
                            res_split_cards.extend(split_path)
                            res_split_cards.extend(comb_list)

                            # 平胡拆牌后，计算向听数
                            # 注意: res_split_cards就是根据需要堆数的组合，所以不用考虑多个对子的向听数问题
                            xts = the_worst_xts
                            # 根据对应的切割卡牌组合，减去对应的向听数
                            for sc in res_split_cards:
                                comb_type = LpyMoveGenerator.judge_cards_type(sc)
                                comb_xts = COMB_REMOVE_XTS.get(comb_type, 0)
                                # 不同组合类型卡牌，减去相对应的向听数
                                xts -= comb_xts

                            for card, count in cards_to_count_copy.items():
                                count > 0 and res_split_cards.append([card] * count)

                            # 判断当前向听数是否减少，并添加切割卡牌至最优组合中
                            if xts < record_lowest_xts:
                                optimal_path.clear()
                                # 添加已组合的牌组
                                optimal_path.append((xts, res_split_cards))
                                # 当向听数小于上次记录的向听数时
                                # 则更新上次记录的向听数
                                record_lowest_xts = xts
                            if xts == record_lowest_xts and xts==0: # 向听数为0时，添加多个最优组合
                                optimal_path.append((xts, res_split_cards))

            optimal_split_cards(new_hand_cards)

        deduplicate = []
        xts_flag = 8
        # todo: 计算老牌友麻将(非癞子/癞子)
        # 不存在癞子牌
        if not self.magic_card:
            for op in optimal_path:
                if op[1] in deduplicate:
                    continue
                deduplicate.append(op[1])
            return record_lowest_xts, self.calc_lpy_by_ping_hu_normal(
                optimal_path=deduplicate,
                yx_heap=need_heap,
                xts=record_lowest_xts
            )
        # 存在癞子牌
        else:
            for op in optimal_path:
                if op[1] in deduplicate:
                    continue
                if op[0] >= xts_flag:
                    continue
                xts_flag = op[0]
                deduplicate.extend(op[1])

            best_cards = self.calc_lpy_by_ping_hu_lai_zi(deduplicate, record_lowest_xts)
            # 无最佳出牌时，则从一张和两张中选择最佳出牌
            if not best_cards:
                min_count = 112
                best_cards = []
                tmp_best_cards = one_list + two_list
                for c in tmp_best_cards:
                    count = self.res_cards_to_count.get(c, 0)
                    if count <= min_count:
                        best_cards.append(c)
            if not best_cards:
                best_cards = self.hand_cards

            if self.magic_card in best_cards:
                for lai_zi in best_cards:
                    if lai_zi == self.magic_card:
                        best_cards.remove(self.magic_card)
            record_lowest_xts -= 1
            if record_lowest_xts < 0:
                LOG_PRINT and print(f"平胡成牌组合: {deduplicate} + 癞子形成胡牌: {self.magic_card}")
            LOG_PRINT and print(f"平胡最优组合: {deduplicate}, 癞子为: {self.magic_card}")
            return record_lowest_xts, best_cards

    def calc_lpy_by_ping_hu_lai_zi(self, deduplicate, record_lowest_xts):
        """
        添加癞子后，根据不同的组合路径计算向听数和最佳出牌
        """
        min_count = 112
        all_best_cards = set()
        for i, path in enumerate(deduplicate):
            cards_len = len(path)
            if cards_len == 3:
                continue
            path.append(self.magic_card)
            best_cards, yxp_count = self.calc_lai_zi_by_xts_cards(deduplicate, record_lowest_xts)
            path.remove(self.magic_card)
            if yxp_count <= min_count:
                for card in best_cards:
                    if card == self.magic_card:
                        continue
                    if card in all_best_cards:
                        continue
                    all_best_cards.add(card)
                min_count = yxp_count
        # todo: 处理形成胡牌时，处理异常并选择最佳出牌
        if not all_best_cards:
            tmp_cards = []
            for cards in deduplicate:
                if len(cards) == 3:
                    continue
                tmp_cards.extend(cards)
            min_count = 0
            for card in tmp_cards:
                count = self.res_cards_to_count.get(card, 0)
                if count >= min_count:
                    min_count = count
                    continue
                # 将数量较小的剩余卡牌移除
                tmp_cards.remove(card)
            return tmp_cards
        return list(all_best_cards)

    def calc_lpy_by_ping_hu_normal(self, optimal_path, yx_heap, xts):
        """
        计算老牌友麻将正常卡牌
        根据胡牌类型计算有效牌
            1.平胡
            2.小七对
            3.大队子
            4.龙七对
            [11, 12, 15, 16] -> 有效牌组: [10, 13, 14, 17]
            :params optimal_path 最优路径 -> [[], [], []]
            :params the_worst_xts 仅根据牌数计算出的当前牌的向听数
            :params xts 向听数
            :params yx_heap 有效堆（需要堆数）
        """
        # 平胡形成了胡牌时，选择平胡最佳出牌
        if xts < 0:
            LOG_PRINT and print("检测手牌是否形成平胡胡牌，重新选择最优出牌!")
            count = 0
            best_cards = []
            remain_cards_by_deck = self.calc_remain_cards_by_deck()
            for card in self.hand_cards:
                tmp_count = 0
                tmp_count += remain_cards_by_deck.get(card, 0)
                if tmp_count > count:
                    best_cards.clear()
                    count = tmp_count
                    best_cards.append(card)
            # 找不到条件符合的卡牌时，从当前手牌中，随机选择一张
            if not best_cards:
                return self.hand_cards
            return list(set(best_cards))

        # 胡牌类型组的有效卡牌
        record_chu_pai = {}
        for i, path in enumerate(optimal_path):
            yxp_cards = set()
            # 先算算有效堆的有效牌
            for j, cards in enumerate(path[:yx_heap + 1]):
                # 不计算面子有效牌
                cards_len = len(cards)
                if cards_len == 3:
                    continue
                # 计算单张卡牌有效牌(i-1, i, i+1)
                if cards_len == 1:
                    card = cards[0]
                    yxp_cards.add(card)
                    card_val = LpyMoveGenerator.get_value(card)
                    if xts != 0:
                        # 计算有效牌(先处理边界，再处理中间)
                        if card_val == 1:
                            yxp_cards.add(card + 1)
                            yxp_cards.add(card + 2)
                        elif card_val == 9:
                            yxp_cards.add(card - 1)
                            yxp_cards.add(card - 2)  # 坎张
                        else:
                            yxp_cards.add(card - 1)
                            if card_val > 2:
                                yxp_cards.add(card - 2)
                            yxp_cards.add(card + 1)
                            if card_val < 8:
                                yxp_cards.add(card + 2)
                elif cards_len == 2:
                    card1 = cards[0]
                    card2 = cards[1]
                    # 计算将牌情况(将牌对数大于1时，再计算)
                    if (j != 0 or xts > 0) and card1 == card2:
                        yxp_cards.add(card1)
                    # 计算二连顺(只处理边界)
                    elif card2 - card1 == 1:
                        card1_val = LpyMoveGenerator.get_value(card1)
                        card2_val = LpyMoveGenerator.get_value(card2)
                        if card1_val != 1:
                            yxp_cards.add(card1 - 1)
                        if card2_val != 9:
                            yxp_cards.add(card2 + 1)
                    # 计算间隔顺(只处理中间)
                    elif card2 - card1 == 2:
                        yxp_cards.add(card2 - 1)

            # 在算无效堆的有效牌
            invalid_heap_cards = []
            for cards in path[yx_heap + 1:]:
                invalid_heap_cards.extend(cards)
            invalid_heap_cards = list(set(invalid_heap_cards))
            for card in invalid_heap_cards:
                record_chu_pai.setdefault(card, set()).update(yxp_cards)

        return self.get_best_card_normal(record_chu_pai, ping_hu=True)

    def calc_lai_zi_by_xts_cards(self, optimal_path, xts):
        """
        计算老牌友麻将癞子卡牌
        根据胡牌类型计算有效牌
            1.平胡
            2.小七对
            3.大队子
            4.龙七对
            [11, 12, 15, 16] -> 有效牌组: [10, 13, 14, 17]
            :params optimal_path 最优路径 -> [[], [], []]
            :params the_worst_xts 仅根据牌数计算出的当前牌的向听数
            :params xts 向听数
            :params yx_heap 有效堆（需要堆数）
        """
        # 平胡形成了胡牌时，选择平胡最佳出牌
        yxp_cards = set()
        record_chu_pai = {}
        for idx, cards in enumerate(optimal_path):
            cards_len = len(cards)
            if cards_len == 3:
                continue
            for card in optimal_path[idx]:
                # 判断癞子是否存在，组合成2张合法卡牌
                if self.magic_card in cards:
                    if card != self.magic_card:
                        card1_val = LpyMoveGenerator.get_value(card)
                        if card1_val != 1:
                            yxp_cards.add(card - 1)
                        if card1_val != 9:
                            yxp_cards.add(card + 1)
                else:
                    yxp_cards.add(card)
                    card_val = LpyMoveGenerator.get_value(card)
                    # 计算有效牌(先处理边界，再处理中间)
                    if card_val == 1:
                        yxp_cards.add(card + 1)
                        yxp_cards.add(card + 2)
                    elif card_val == 9:
                        yxp_cards.add(card - 1)
                        yxp_cards.add(card - 2)  # 坎张
                    else:
                        yxp_cards.add(card - 1)
                        yxp_cards.add(card + 1)
                        if card_val > 2:
                            yxp_cards.add(card - 2)
                        if card_val < 8:
                            yxp_cards.add(card + 2)
                # 在算无效堆的有效牌
                if not yxp_cards:
                    continue
                record_chu_pai.setdefault(card, set()).update(yxp_cards)
                yxp_cards = set()
        return self.get_best_card_lai_zi(record_chu_pai)

    def cal_xts_da_dui_zi_normal(self, *args):
        """
        计算未持有癞子时，大队子牌型向听数
        """
        the_worst_xts = self.the_worst_xts_by_hu_type.get(FcHuPaiType.DA_DUI_ZI, 8)
        one_list, two_list, three_list, four_list = args
        need_heap = self.hand_cards_len // 3 + 1  # 刻子数 + 一对
        two_len = len(two_list)
        real_xts = the_worst_xts - two_len if two_len <= need_heap else the_worst_xts - need_heap
        real_xts -= len(three_list + four_list) * 2

        extra_one = []
        optimal_split_cards = []
        for four in four_list:
            optimal_split_cards.append([four] * 3)
            extra_one.append(four)
        for three in three_list:
            optimal_split_cards.append([three] * 3)
        for two in two_list:
            optimal_split_cards.append([two] * 2)

        yxp_cards = set()
        two_list_len = len(two_list)
        for path in optimal_split_cards:
            if len(path) == 3:
                continue
            if two_list_len != 1:
                yxp_cards.add(path[0])

        extra_one.extend(one_list)
        record_chu_pai = {}
        if extra_one:
            optimal_split_cards.extend([[one] for one in extra_one])
            for c in extra_one:
                yxp_copy = yxp_cards.copy()
                yxp_copy.update(set(extra_one))
                yxp_copy.remove(c)
                record_chu_pai[c] = yxp_copy
        else:
            if len(two_list) > 1:
                for c in yxp_cards:
                    yxp_copy = yxp_cards.copy()
                    yxp_copy.remove(c)
                    record_chu_pai[c] = yxp_copy

        best_cards = self.get_best_card_normal(record_chu_pai)
        LOG_PRINT and print(f"大对子最优组合：{optimal_split_cards}")

        return real_xts, best_cards

    def calc_xts_da_dui_zi_lai_zi(self, *args):
        """
        计算持有癞子时，大队子牌型向听数
        """
        the_worst_xts = self.the_worst_xts_by_hu_type.get(FcHuPaiType.DA_DUI_ZI, 8)
        one_list, two_list, three_list, four_list = args
        need_heap = self.hand_cards_len // 3 + 1  # 刻子数 + 一对
        two_len = len(two_list)
        real_xts = the_worst_xts - two_len if two_len <= need_heap else the_worst_xts - need_heap
        real_xts -= len(three_list + four_list) * 2

        # 拆分大对子牌型
        optimal_split_cards = []
        for four in four_list:
            optimal_split_cards.append([four] * 3)
        for three in three_list:
            optimal_split_cards.append([three] * 3)
        for two in two_list:
            optimal_split_cards.append([two] * 2)

        yxp_cards = set()
        two_list_len = len(two_list)
        for path in optimal_split_cards:
            if len(path) == 3:
                continue
            if two_list_len != 1:
                yxp_cards.add(path[0])
        if one_list:
            optimal_split_cards.extend([[one] for one in one_list])
        # 大对子牌型时，存在单张卡牌，优先选择单张卡牌为最优出牌
        min_count = 0
        best_cards = []
        # 存在单张时，择优选择单张为最佳出牌
        if one_list:
            min_count = self.res_cards_to_count.get(one_list[0], 0)
            for c in one_list:
                count = self.res_cards_to_count.get(c, 0)
                if count < min_count:
                    best_cards.clear()
                    best_cards.append(c)
                    min_count = count
                elif count == min_count:
                    best_cards.append(c)
                    min_count = count

        # 不存在单张时，则从对子中选择最佳出牌
        elif yxp_cards:
            min_count = self.res_cards_to_count.get(next(iter(yxp_cards)), 0)
            for c in yxp_cards:
                count = self.res_cards_to_count.get(c, 0)
                if count < min_count:
                    best_cards.clear()
                    best_cards.append(c)
                    min_count = count
                elif count == min_count:
                    best_cards.append(c)
                    min_count = count
        # 找不到最优出牌，说明单张，对子中不存在，则随机打一张
        else:
            if self.magic_card in self.hand_cards:
                self.remove_by_value(self.hand_cards, self.magic_card, -1)
            # if self.magic_card in self.hand_cards:
            #     self.hand_cards.remove(self.magic_card)
            min_count = self.res_cards_to_count.get(self.hand_cards[0], 0)
            for c in self.hand_cards:
                count = self.res_cards_to_count.get(c, 0)
                if count < min_count:
                    best_cards.clear()
                    best_cards.append(c)
                    min_count = count
                elif count == min_count:
                    best_cards.append(c)
                    min_count = count
        if not best_cards:
            return real_xts, self.hand_cards
        real_xts -= 1
        if real_xts < 0:
            LOG_PRINT and print(f"大对子成牌组合: {optimal_split_cards} + 癞子形成胡牌: {self.magic_card}")
        LOG_PRINT and print(f"大对子最优组合：{optimal_split_cards}, 癞子为: {self.magic_card}")
        if best_cards and len(best_cards) > 1:
            if self.magic_card in best_cards:
                best_cards.remove(self.magic_card)

        return real_xts, best_cards

    def cal_xts_by_qi_dui_normal(self, *args):
        """
        计算未持有癞子时，七对牌型向听数
        """
        the_worst_xts = self.the_worst_xts_by_hu_type.get(FcHuPaiType.QI_DUI, 8)  # 最坏向听数
        one_list, two_list, three_list, four_list = args  # self.split_cards_dict_res()
        reduce_one_xts = len(two_list + three_list)
        reduce_two_xts = len(four_list) * 2
        real_xts = the_worst_xts - reduce_one_xts - reduce_two_xts  # 真实向听数
        extra_one = []
        optimal_split_cards = []
        for four in four_list:
            optimal_split_cards.append([four] * 4)
        for three in three_list:
            optimal_split_cards.append([three] * 2)
            extra_one.append(three)
        for two in two_list:
            optimal_split_cards.append([two] * 2)

        extra_one.extend(one_list)  # 单牌
        optimal_split_cards.extend([[one] for one in extra_one])
        record_chu_pai = {}
        for c in extra_one:
            yxp_cards = set(extra_one)
            yxp_cards.remove(c)
            record_chu_pai[c] = yxp_cards

        best_cards = self.get_best_card_normal(record_chu_pai)
        LOG_PRINT and print(f"七对最优组合：{optimal_split_cards}")

        return real_xts, best_cards

    def cal_xts_by_qi_dui_lai_zi(self, *args):
        """
        计算持有癞子时，七对牌型向听数
        """
        the_worst_xts = self.the_worst_xts_by_hu_type.get(FcHuPaiType.QI_DUI, 8)  # 最坏向听数
        one_list, two_list, three_list, four_list = args  # self.split_cards_dict_res()
        reduce_one_xts = len(two_list + three_list)
        reduce_two_xts = len(four_list) * 2
        real_xts = the_worst_xts - reduce_one_xts - reduce_two_xts  # 真实向听数
        extra_one = []
        optimal_split_cards = []
        for four in four_list:
            optimal_split_cards.append([four] * 4)
        for three in three_list:
            optimal_split_cards.append([three] * 2)
            extra_one.append(three)
        for two in two_list:
            optimal_split_cards.append([two] * 2)

        if one_list:
            optimal_split_cards.extend([[one] for one in extra_one])
            extra_one.extend(one_list)
        yxp_cards = set()
        two_list_len = len(two_list)
        for path in optimal_split_cards:
            if len(path) == 3:
                continue
            if two_list_len != 1:
                yxp_cards.add(path[0])

        # todo: 小七对牌型时，存在单张卡牌，优先选择单张卡牌为最优出牌
        min_count = 0
        best_cards = []
        # 存在单张时，优先选择单张为最佳出牌
        if one_list:
            min_count = self.res_cards_to_count.get(one_list[0], 0)
            for c in one_list:
                count = self.res_cards_to_count.get(c, 0)
                if count < min_count:
                    best_cards.clear()
                    best_cards.append(c)
                    min_count = count
                elif count == min_count:
                    best_cards.append(c)
                    min_count = count
        elif yxp_cards:
            min_count = self.res_cards_to_count.get(next(iter(yxp_cards)), 0)
            for c in yxp_cards:
                count = self.res_cards_to_count.get(c, 0)
                if count < min_count:
                    best_cards.clear()
                    best_cards.append(c)
                    min_count = count
                elif count == min_count:
                    best_cards.append(c)
                    min_count = count
        # 找不到最优出牌时，说明单张、对子没有拆牌
        else:
            if self.magic_card in self.hand_cards:
                self.remove_by_value(self.hand_cards, self.magic_card, -1)
            # if self.magic_card in self.hand_cards:
            #     self.hand_cards.remove(self.magic_card)
            min_count = self.res_cards_to_count.get(self.hand_cards[0], 0)
            for c in self.hand_cards:
                count = self.res_cards_to_count.get(c, 0)
                if count < min_count:
                    best_cards.clear()
                    best_cards.append(c)
                    min_count = count
                elif count == min_count:
                    best_cards.append(c)
                    min_count = count
        if not best_cards:
            return real_xts, self.hand_cards
        real_xts -= 1
        if real_xts < 0:
            LOG_PRINT and print(f"小七对成牌组合: {optimal_split_cards} + 癞子形成胡牌: {self.magic_card}")
        LOG_PRINT and print(f"小七对最优组合：{optimal_split_cards}, 癞子为: {self.magic_card}")
        return real_xts, best_cards

    def cal_xts_by_long_qi_dui_normal(self, *args):
        """
        未持有癞子，龙七对
        """
        the_worst_xts = self.the_worst_xts_by_hu_type.get(FcHuPaiType.LONG_QI_DUI, 8)  # 最坏向听数
        one_list, two_list, three_list, four_list = args  # self.split_cards_dict_res()
        reduce_one_xts = len(two_list + three_list)
        reduce_two_xts = len(four_list) * 2
        real_xts = the_worst_xts - reduce_one_xts - reduce_two_xts  # 真实向听数
        extra_one = []
        optimal_split_cards = []
        for four in four_list:
            optimal_split_cards.append([four] * 4)
        for three in three_list:
            optimal_split_cards.append([three] * 3)
        for two in two_list:
            optimal_split_cards.append([two] * 2)

        extra_one.extend(one_list)  # 单牌
        optimal_split_cards.extend([[one] for one in extra_one])
        record_chu_pai = {}
        for c in extra_one:
            yxp_cards = set(extra_one)
            yxp_cards.remove(c)
            record_chu_pai[c] = yxp_cards

        best_cards = self.get_best_card_normal(record_chu_pai)
        LOG_PRINT and print(f"龙七对最优组合：{optimal_split_cards}")

        return real_xts, best_cards

    def calc_xts_by_long_qi_dui_lai_zi(self, *args):
        """
        持有癞子时，计算龙七对牌型向听数
        """
        the_worst_xts = self.the_worst_xts_by_hu_type.get(FcHuPaiType.LONG_QI_DUI, 8)  # 最坏向听数
        one_list, two_list, three_list, four_list = args  # self.split_cards_dict_res()
        reduce_one_xts = len(two_list + three_list)
        reduce_two_xts = len(four_list) * 2
        real_xts = the_worst_xts - reduce_one_xts - reduce_two_xts  # 真实向听数
        extra_one = []
        optimal_split_cards = []
        for four in four_list:
            optimal_split_cards.append([four] * 4)
        for three in three_list:
            optimal_split_cards.append([three] * 3)
        for two in two_list:
            optimal_split_cards.append([two] * 2)

        if one_list:
            optimal_split_cards.extend([[one] for one in extra_one])
            extra_one.extend(one_list)
        yxp_cards = set()
        two_list_len = len(two_list)
        for path in optimal_split_cards:
            if len(path) == 3:
                continue
            if two_list_len != 1:
                yxp_cards.add(path[0])

        # todo: 小七对牌型时，存在单张卡牌，优先选择单张卡牌为最优出牌
        min_count = 0
        best_cards = []
        # 存在单张时，优先选择单张为最佳出牌
        if one_list:
            min_count = self.res_cards_to_count.get(one_list[0], 0)
            for c in one_list:
                count = self.res_cards_to_count.get(c, 0)
                if count < min_count:
                    best_cards.clear()
                    best_cards.append(c)
                    min_count = count
                elif count == min_count:
                    best_cards.append(c)
                    min_count = count
        elif yxp_cards:
            min_count = self.res_cards_to_count.get(next(iter(yxp_cards)), 0)
            for c in yxp_cards:
                count = self.res_cards_to_count.get(c, 0)
                if count < min_count:
                    best_cards.clear()
                    best_cards.append(c)
                    min_count = count
                elif count == min_count:
                    best_cards.append(c)
                    min_count = count
        # 找不到最优出牌时，说明单张、对子没有拆牌
        else:
            if self.magic_card in self.hand_cards:
                self.remove_by_value(self.hand_cards, self.magic_card, -1)
            # if self.magic_card in self.hand_cards:
            #     self.hand_cards.remove(self.magic_card)
            min_count = self.res_cards_to_count.get(self.hand_cards[0], 0)
            for c in self.hand_cards:
                count = self.res_cards_to_count.get(c, 0)
                if count > min_count:
                    best_cards.clear()
                    best_cards.append(c)
                    min_count = count
                elif count == min_count:
                    best_cards.append(c)
                    min_count = count
        if not best_cards:
            return real_xts, self.hand_cards
        real_xts -= 1
        if real_xts < 0:
            LOG_PRINT and print(f"龙七对成牌组合: {optimal_split_cards} + 癞子形成胡牌: {self.magic_card}")
        LOG_PRINT and print(f"龙七对最优组合：{optimal_split_cards}, 癞子为: {self.magic_card}")
        return real_xts, best_cards

    def get_best_card_normal(self, record_chu_pai: dict, ping_hu=False):
        """
        此接口计算不包含万能牌时，选择最佳出牌
        """
        yxp_count = 0
        best_cards = []
        for card, yxp in record_chu_pai.items():
            count = 0
            for c in yxp:
                count += self.res_cards_to_count.get(c, 0)
            if best_cards:
                for c in self.__all_hu_cards:
                    if c in best_cards:
                        best_cards.remove(c)
                        yxp_count = 0
            if count > yxp_count:
                best_cards.clear()
                yxp_count = count
                best_cards.append(card)
            elif count == yxp_count:
                best_cards.append(card)
        if ping_hu:
            final_cards = []
            for c in best_cards:
                c_v = self.get_value(c)
                if c_v == 1 or c_v == 9:
                    final_cards.append(c)
            return final_cards if final_cards else best_cards
        return best_cards

    def get_best_card_lai_zi(self, record_chu_pai):
        """
        此接口计算包含万能牌时，选择最佳出牌
        """
        yxp_count = 112
        best_cards = []
        all_best_cards = []
        for card, yxp in record_chu_pai.items():
            count = 0
            for c in yxp:
                count += self.res_cards_to_count.get(c, 0)
            if count < yxp_count:
                best_cards.clear()
                yxp_count = count
                best_cards.append(card)
            all_best_cards.append(card)
        if not best_cards:
            if not all_best_cards:
                return self.hand_cards, yxp_count
            return all_best_cards, yxp_count
        return best_cards, yxp_count

    def calc_remain_cards_by_deck(self):
        """
        计算牌堆里剩余的卡牌
        """
        # 统计卡牌数量
        remain_cards_dict = self.count_cards_dict_res(self.others_hand_cards)
        remain_cards_by_deck = {int(key): value for key, value in self.res_cards_to_count.items()}
        for card, nums in remain_cards_dict.items():
            if remain_cards_by_deck.get(card, 0):
                remain_cards_by_deck[card] -= nums
        return remain_cards_by_deck

    def count_cards_dict_res(self, cards=None) -> dict:
        """
        计算出手牌每张牌的数量
        已经去除癞子
        cards: 如果不传则就计算手牌
        """
        if not cards:
            if not cards:
                cards = self.hand_cards[:]
            if not self.cards_to_count:
                # 删除万能牌，然后计算向听数
                self.remove_by_value(cards, self.magic_card, -1)
            self.cards_to_count = self.cards_to_count_dict(cards)
            return self.cards_to_count
        else:
            self.remove_by_value(cards, self.magic_card, -1)
            return self.cards_to_count_dict(cards)

    def split_cards_dict_res(self):
        """ 计算不同数量的cards """
        one_list = []  # 单张卡牌
        two_list = []  # 对子
        three_list = []  # 刻子
        four_list = []  # 四张
        cards_to_count = self.count_cards_dict_res()
        for card, count in cards_to_count.items():
            res = {
                1: one_list,
                2: two_list,
                3: three_list,
                4: four_list
            }.get(count, 1)
            res.append(card)
        return one_list, two_list, three_list, four_list

    @staticmethod
    def remove_by_value(data, value, remove_count=1):
        """
        删除列表data中的value
        :param data: list
        :param value:
        :param remove_count: 为-1的时候表示删除全部, 默认为1
        :return: already_remove_count: int
        """
        data_len = len(data)
        count = remove_count == -1 and data_len or remove_count

        already_remove_count = 0

        for i in range(0, count):
            if value in data:
                data.remove(value)
                already_remove_count += 1
            else:
                break

        return already_remove_count

    @staticmethod
    def gen_serial_moves(single_cards, min_serial=2, max_serial=3, repeat=1, solid_num=0):
        """
        减去 对子/刻子 后的所有搭子（两面，坎张，顺子）
        params: cards 输入牌
        params: min_serial  最小连数
        params: max_serial  最大连数
        params: repeat  重复牌数
        params: solid_num  固定连数
        拆牌：坎张|两面|
        """
        seq_records = list()
        result = list()

        cards_len = len(single_cards)

        # 至少重复数是最小序列
        if solid_num < min_serial:
            solid_num = 0

        # 顺子（最少2张）
        start = i = 0
        longest = 1
        while i < cards_len:
            # 判断连续两张牌
            if i + 1 < cards_len and single_cards[i + 1] - single_cards[i] == 1:
                longest += 1
                i += 1
            else:
                # 记录索引
                seq_records.append((start, longest))
                i += 1
                start = i
                longest = 1

        for seq in seq_records:
            if seq[1] < min_serial:
                continue
            start, longest = seq[0], seq[1]
            longest_list = single_cards[start: start + longest]

            if solid_num == 0:  # No limitation on how many sequences
                steps = min_serial  # 最小连数
                while steps <= longest:
                    index = 0
                    while steps + index <= longest:
                        target_moves = sorted(longest_list[index: index + steps] * repeat)
                        result.append(target_moves)
                        index += 1
                    steps += 1  # 递增
                    if steps > max_serial:
                        break
            else:
                if longest < solid_num:
                    continue
                index = 0
                while index + solid_num <= longest:
                    target_moves = sorted(longest_list[index: index + solid_num] * repeat)
                    result.append(target_moves)
                    index += 1
        # 坎张
        i = 0
        while i < cards_len:
            # 连续的两张坎张
            start_val = single_cards[i] % 10
            if start_val > 7:
                i += 1
                continue
            if i + 1 < cards_len and single_cards[i] + 2 == single_cards[i + 1]:
                result.append(single_cards[i: i + min_serial])
            # 间隔的两张坎张
            if i + 2 < cards_len and single_cards[i] + 2 == single_cards[i + 2]:
                result.append([single_cards[i], single_cards[i + 2]])
            i += 1

        return result

    @staticmethod
    def cards_to_count_dict(cards: Iterable):
        """
        统计卡牌数量(dict)
        """
        card_to_count = {}
        for c in cards:
            card_to_count[c] = card_to_count.get(c, 0) + 1
        return card_to_count

    @staticmethod
    def get_value(card):
        return card % 10
