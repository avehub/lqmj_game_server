# -*- coding: utf-8 -*-

import numpy as np

from collections import Counter

from c_services.cs_robot_mahjong import const
from c_services.cs_robot_mahjong.const import ActionType
from c_services.cs_robot_mahjong.card import MahjongCard as Card


def new_make_cards():
    """
    制作卡牌编码字典
    """
    # 卡牌编码成字典
    card_encoding_dict = {}
    # 卡牌索引
    num = 0
    # 所有卡牌编码
    for card in const.ALL_CARDS:
        card_encoding_dict[card] = num
        num += 1
    else:
        # 癞子牌
        card_encoding_dict[const.LAI_ZI] = num
        num += 1
    # 玩家
    card_encoding_dict[ActionType.G_PASS] = num  # 28 过
    card_encoding_dict[ActionType.TIAN_TING] = num + 1  # 29 天听
    card_encoding_dict[ActionType.PONG] = num + 2  # 30 碰
    card_encoding_dict[ActionType.MING_GONG] = num + 3  # 31 明杠
    card_encoding_dict[ActionType.SUO_GONG] = num + 4  # 32 索杠(转弯杠)
    card_encoding_dict[ActionType.AN_GONG] = num + 5  # 33 暗杠
    card_encoding_dict[ActionType.GS_PAO] = num + 6  # 34 杠上炮
    card_encoding_dict[ActionType.QG_HU] = num + 7  # 35 抢杠胡
    card_encoding_dict[ActionType.PICK_HU] = num + 8  # 36 捡胡
    card_encoding_dict[ActionType.MI_HU] = num + 9  # 37 # 密胡
    card_encoding_dict[ActionType.KAI_HU] = num + 10  # 38 # 胡开(游戏结束)

    return card_encoding_dict

# 构建动作编码字典
new_card_encoding_dict = new_make_cards()
card_decoding_dict = {new_card_encoding_dict[key]: key for key in new_card_encoding_dict.keys()}

def init_deck():
    """
    麻将卡牌(108)
    """
    # 牌盒
    deck = []
    index_num = 0
    for card_rank in const.ALL_CARDS:
        card_type = const.CARD_TYPES[card_rank // 10]
        card = Card(card_type, card_rank)
        card.set_index_num(index_num)
        index_num = index_num + 1
        deck.append(card)
    deck = deck * 4

    return deck

def lai_zi_deck():
    """
    万能牌(3)
    """
    lz_deck = []
    index_num = 27
    card_type = const.CARD_TYPES[const.LAI_ZI // 10]
    card = Card(card_type, const.LAI_ZI)
    card.set_index_num(index_num)
    lz_deck.append(card)
    lz_deck = lz_deck * 3

    return lz_deck

def compare2cards_obj(card1, card2):
    """
    排序卡牌对象
    """
    key = []
    for card in [card1, card2]:
        key.append(const.CARD_VALUE.index(str(card)))
    if key[0] > key[1]:
        return 1
    if key[0] < key[1]:
        return -1
    return 0

# TODO: 卡牌编码(new)
def encode_cards(cards):
    """
    手牌编码方式-1
    注意: 考虑其他动作
    """
    matrix = np.zeros((28, 4), dtype=np.float32)
    for card in list(set(cards)):
        index = new_card_encoding_dict[card]  # 获取卡牌索引
        num = cards.count(card)  # 统计卡牌数量
        matrix[index][:num] = 1  # 根据卡牌数量，编码为1
    return matrix.flatten('F')

def encode_legal_actions(legal_actions):
    """
    编码合法动作
    """
    matrix = np.zeros((39, 4), dtype=np.float32)
    for card in list(set(legal_actions)):
        index = new_card_encoding_dict[card]  # 获取卡牌索引
        num = legal_actions.count(card)  # 统计卡牌数量
        matrix[index][:num] = 1  # 根据卡牌数量，编码为1
    return matrix.flatten('F')

def encode_last_action(last_action):
    """
    编码上一个动作
    """
    if not last_action:
        return np.zeros(39, dtype=np.float32)
    matrix = np.zeros(39, dtype=np.float32)
    index = new_card_encoding_dict[last_action[-1]]
    matrix[index] = 1

    return matrix

def pile2list(piles):
    """
    计算玩家碰、杠牌
    """
    cards_list = []
    for p in piles.keys():
        for pile in piles[p]:
            cards_list.extend(pile[1])

    return cards_list

def action_seq_history(action_seqs):
    """
    TODO: 玩家打牌动作序列
    只对玩家动作序列的后四个进行编码
    以四个动作为滑动窗口进行移动编码
    """
    if len(action_seqs) == 0:
        return np.zeros(156, dtype=np.int8)
    matrix = np.zeros([4, 39], dtype=np.int8)
    counter = Counter(action_seqs[-4:])
    for card, nums in counter.items():
        matrix[:, const.Card2Column[card]] = const.NumOnes2Array[nums]
    return matrix.flatten('A')

def encode_nums(hand_card_nums):
    """
    手牌数量编码
    """
    matrix = np.zeros([3, 14], dtype=np.float32)
    for idx, nums in enumerate(hand_card_nums):
        matrix[idx][nums - 1] = 1
    return matrix.flatten('A')
