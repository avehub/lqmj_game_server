import collections
import itertools
from typing import List, Dict

from .const import ActionType
from .poker import Cards
from ..base.base_rule import BaseRule

MIN_SINGLE_CARDS = 5  # 最小连续数
MIN_PAIRS = 3  # 最小连对数
MIN_TRIPLES = 2  # 最小飞机数
S_KING = 18
B_KING = 20


class Rule(BaseRule):
    """
    斗地主规则算法
    """

    @staticmethod
    def get_val2cards(cards: List[Cards]):
        val2cards = {}
        for c in cards:
            val2cards.setdefault(c.val, []).append(c)
        return val2cards

    @staticmethod
    def get_cards_by_val(val2cards: Dict[int, list], cards_val: List[int]):
        """
        根据 牌值 获取 cards
        注意：cards 中需要一定有足够数量的 cards val
        :param val2cards: 手牌
        :param cards_val: 牌值
        :return:
        """
        val2count = {}
        for val in cards_val:
            val2count[val] = val2count.get(val, 0) + 1

        move = []
        for val, count in val2count.items():
            card_list = val2cards.get(val)
            move.extend(card_list[:count])
        return move

    @staticmethod
    def get_cards_by_val_list(cards: List[Cards], cards_val: List[list[int]]):
        if len(cards_val) == 1 and not cards_val[0]:
            return []
        val2cards = Rule.get_val2cards(cards)
        moves = []
        for one_cards_val in cards_val:
            move = Rule.get_cards_by_val(val2cards, one_cards_val)
            moves.append(move)
        return moves

    @staticmethod
    def select(cards, num):
        return [list(i) for i in itertools.combinations(cards, num)]

    @staticmethod
    def _gen_serial_moves(cards, min_serial, repeat=1, repeat_num=0):
        """
        repeat_num: 最大连数
        """
        if repeat_num < min_serial:  # at least repeat_num is min_serial
            repeat_num = 0

        single_cards = sorted(list(set(cards)))
        seq_records = []
        moves = []

        start = i = 0
        longest = 1
        while i < len(single_cards):
            if i + 1 < len(single_cards) and single_cards[i + 1] - single_cards[i] == 1:
                longest += 1
                i += 1
            else:
                seq_records.append((start, longest))
                i += 1
                start = i
                longest = 1

        for seq in seq_records:
            if seq[1] < min_serial:
                continue
            start, longest = seq[0], seq[1]
            longest_list = single_cards[start: start + longest]

            if repeat_num == 0:  # No limitation on how many sequences
                steps = min_serial
                while steps <= longest:
                    index = 0
                    while steps + index <= longest:
                        target_moves = sorted(longest_list[index: index + steps] * repeat)
                        moves.append(target_moves)
                        index += 1
                    steps += 1

            else:  # repeat_num > 0
                if longest < repeat_num:
                    continue
                index = 0
                while index + repeat_num <= longest:
                    target_moves = sorted(longest_list[index: index + repeat_num] * repeat)
                    moves.append(target_moves)
                    index += 1

        return moves

    @staticmethod
    def gen_type_1_single(cards: list[int]):
        """ 单张 """
        single_card_moves = []
        for i in set(cards):
            single_card_moves.append([i])
        return single_card_moves

    @staticmethod
    def gen_type_2_pair(cards_dict: dict):
        """ 对子 """
        pair_moves = []
        for k, v in cards_dict.items():
            if v >= 2:
                pair_moves.append([k, k])
        return pair_moves

    @staticmethod
    def gen_type_3_triple(cards_dict: dict):
        """ 3不带 """
        triple_cards_moves = []
        for k, v in cards_dict.items():
            if v >= 3:
                triple_cards_moves.append([k, k, k])
        return triple_cards_moves

    @staticmethod
    def gen_type_4_bomb(cards_dict: dict):
        """ 4张炸弹 """
        bomb_moves = []
        for k, v in cards_dict.items():
            if v == 4:
                bomb_moves.append([k, k, k, k])
        return bomb_moves

    # @staticmethod
    # def gen_type_5_king_bomb(cards: list[int]):
    #     """ 王炸 """
    #     final_bomb_moves = []
    #     if S_KING in cards and B_KING in cards:
    #         final_bomb_moves.append([S_KING, B_KING])
    #     return final_bomb_moves

    @staticmethod
    def gen_type_5_king_bomb(cards_dict: dict):
        """ 王炸 """
        final_bomb_moves = []
        if cards_dict.get(S_KING) and cards_dict.get(B_KING):
            final_bomb_moves.append([S_KING, B_KING])
        return final_bomb_moves

    @staticmethod
    def gen_type_6_3_1(cards: list[int], cards_dict: dict):
        """ 3带1 """
        result = []
        single_card_moves = Rule.gen_type_1_single(cards)
        triple_cards_moves = Rule.gen_type_3_triple(cards_dict)
        for t in single_card_moves:
            for i in triple_cards_moves:
                if t[0] != i[0]:
                    result.append(t + i)
        return result

    @staticmethod
    def gen_type_7_3_2(cards_dict: dict):
        """ 3带2 """
        result = []
        pair_moves = Rule.gen_type_2_pair(cards_dict)
        triple_cards_moves = Rule.gen_type_3_triple(cards_dict)
        for t in pair_moves:
            for i in triple_cards_moves:
                if t[0] != i[0]:
                    result.append(t + i)
        return result

    @staticmethod
    def gen_type_8_serial_single(cards: list[int], repeat_num=0):
        """ 单连牌：最少5张 """
        return Rule._gen_serial_moves(cards, MIN_SINGLE_CARDS, repeat=1, repeat_num=repeat_num)

    @staticmethod
    def gen_type_9_serial_pair(cards_dict: dict, repeat_num=0):
        """ 双连牌：最少3对 """
        single_pairs = []
        for k, v in cards_dict.items():
            if v >= 2:
                single_pairs.append(k)

        return Rule._gen_serial_moves(single_pairs, MIN_PAIRS, repeat=2, repeat_num=repeat_num)

    @staticmethod
    def gen_type_10_serial_triple(cards_dict: dict, min_serial=MIN_TRIPLES, repeat_num=0):
        """ 飞机不带 """
        single_triples = []
        for k, v in cards_dict.items():
            if v >= 3:
                single_triples.append(k)

        return Rule._gen_serial_moves(single_triples, min_serial, repeat=3, repeat_num=repeat_num)

    @staticmethod
    def gen_type_11_serial_3_1(cards: list[int], cards_dict: dict, repeat_num=0):
        """ 飞机带单 """
        serial_3_moves = Rule.gen_type_10_serial_triple(cards_dict, repeat_num=repeat_num)
        serial_3_1_moves = []

        for s3 in serial_3_moves:  # s3 is like [3,3,3,4,4,4]
            s3_set = set(s3)
            new_cards = [i for i in cards if i not in s3_set]

            # Get any s3_len items from cards
            sub_cards = Rule.select(new_cards, len(s3_set))

            for i in sub_cards:
                serial_3_1_moves.append(s3 + i)

        return list(k for k, _ in itertools.groupby(serial_3_1_moves))

    @staticmethod
    def gen_type_12_serial_3_2(cards_dict: dict, repeat_num=0):
        """ 飞机带双 """
        serial_3_moves = Rule.gen_type_10_serial_triple(cards_dict, repeat_num=repeat_num)
        serial_3_2_moves = []
        pair_set = sorted([k for k, v in cards_dict.items() if v >= 2])

        for s3 in serial_3_moves:
            s3_set = set(s3)
            pair_candidates = [i for i in pair_set if i not in s3_set]

            # Get any s3_len items from cards
            subcards = Rule.select(pair_candidates, len(s3_set))
            for i in subcards:
                serial_3_2_moves.append(sorted(s3 + i * 2))

        return serial_3_2_moves

    @staticmethod
    def gen_type_13_4_2(cards: list[int], cards_dict):
        """ 4带2 """
        four_cards = []
        for k, v in cards_dict.items():
            if v == 4:
                four_cards.append(k)

        result = []
        for fc in four_cards:
            cards_list = [k for k in cards if k != fc]
            subcards = Rule.select(cards_list, 2)
            for i in subcards:
                result.append([fc] * 4 + i)
        return list(k for k, _ in itertools.groupby(result))

    @staticmethod
    def gen_type_14_4_22(cards_dict):
        """ 4带2对 """
        four_cards = []
        for k, v in cards_dict.items():
            if v == 4:
                four_cards.append(k)

        result = []
        for fc in four_cards:
            cards_list = [k for k, v in cards_dict.items() if k != fc and v >= 2]
            subcards = Rule.select(cards_list, 2)
            for i in subcards:
                result.append([fc] * 4 + [i[0], i[0], i[1], i[1]])
        return result

    @staticmethod
    def gen_type_15_serial_bomb(cards_dict, min_num=2):
        """
        寻找滚炸(新加)
        min_num: 最小连数
        """
        four_cards = []
        for k, v in cards_dict.items():
            if v == 4:
                four_cards.append(k)
        return Rule._gen_serial_moves(four_cards, min_num, repeat=4)

    @staticmethod
    def __split_list_by_straight(l: list, min_num) -> list:
        """
        将列表按值是否连续来断开，比如 [5, 7, 9, 10, 12] -> [[5], [7], [9, 10], [12]]
        :param l:
        :return:
        """
        l.sort()
        result, cursor, l_len = [], 0, len(l)
        for i in range(l_len):
            if i == l_len - 1:
                cards = l[cursor:]
                if len(cards) >= min_num:
                    result.append(l[cursor:])
                continue
            if l[i] + 1 != l[i + 1]:
                cards = l[cursor:i + 1]
                if len(cards) >= min_num:
                    result.append(cards)
                cursor = i + 1
                continue
        return result

    @staticmethod
    def get_shun_zi(cards, min_num=2):
        """ 获取不重复的最大连牌 """
        if not cards:
            return []
        return Rule.__split_list_by_straight(cards, min_num)

    @staticmethod
    def get_cards_count_dict(cards: list[int]):
        cards_dict = {}
        for c in cards:
            cards_dict[c] = cards_dict.get(c, 0) + 1
        return cards_dict

    @staticmethod
    def is_continuous_seq(move):
        """ 是否连续 """
        i = 0
        while i < len(move) - 1:
            if move[i + 1] - move[i] != 1:
                return False
            i += 1
        return True

    @staticmethod
    def get_move_type(move,drift = False):
        """ 获取动作类型 """
        """drift 是否甩尾"""
        move_size = len(move)
        move_dict = collections.Counter(move)

        if move_size == 0:
            return {"type": ActionType.TYPE_0_PASS}

        if move_size == 1:
            return {'type': ActionType.TYPE_1_SINGLE, 'rank': move[0]}

        if move_size == 2:
            if move[0] == move[1]:
                return {'type': ActionType.TYPE_2_PAIR, 'rank': move[0]}
            elif set(move) == {S_KING, B_KING}:  # Kings
                return {'type': ActionType.TYPE_5_KING_BOMB}
            else:
                return {'type': ActionType.TYPE_16_WRONG}

        if move_size == 3:
            if len(move_dict) == 1:
                return {'type': ActionType.TYPE_3_TRIPLE, 'rank': move[0]}
            else:
                return {'type': ActionType.TYPE_16_WRONG}

        if move_size == 4:
            if len(move_dict) == 1:
                return {'type': ActionType.TYPE_4_BOMB, 'rank': move[0]}
            elif len(move_dict) == 2:
                if move[0] == move[1] == move[2] or move[1] == move[2] == move[3]:
                    return {'type': ActionType.TYPE_6_3_1, 'rank': move[1]}
                else:
                    return {'type': ActionType.TYPE_16_WRONG}
            else:
                return {'type': ActionType.TYPE_16_WRONG}

        if Rule.is_continuous_seq(move):
            return {'type': ActionType.TYPE_8_SERIAL_SINGLE, 'rank': move[0], 'len': len(move)}

        if move_size % 4 == 0:
            card_count = {}
            for c in move:
                card_count[c] = card_count.get(c, 0) + 1
            for card, count in card_count.items():
                if count < 4:
                    break  # 这里如果跳出不会走else
            else:
                # 连炸
                bomb_serial = list(set(move))
                if Rule.is_continuous_seq(bomb_serial):
                    return {'type': ActionType.TYPE_15_SERIAL_BOMB, 'rank': move[0], 'len': len(bomb_serial)}

        count_dict = collections.defaultdict(int)
        for c, n in move_dict.items():
            count_dict[n] += 1

        # if move_size == 5:
        if move_size == 5 and count_dict.get(4, 0) == 0:  # 不这样处理炸弹 + 单牌会识别为3带2
            if len(move_dict) == 2:
                return {'type': ActionType.TYPE_7_3_2, 'rank': move[2]}
            else:
                return {'type': ActionType.TYPE_16_WRONG}

        if move_size == 6:
            if (len(move_dict) == 2 or len(move_dict) == 3) and count_dict.get(4) == 1 and \
                    (count_dict.get(2) == 1 or count_dict.get(1) == 2):
                return {'type': ActionType.TYPE_13_4_2, 'rank': move[2]}

        if move_size == 8 and (((len(move_dict) == 3 or len(move_dict) == 2) and
                                (count_dict.get(4) == 1 and count_dict.get(2) == 2)) or count_dict.get(4) == 2):
            return {'type': ActionType.TYPE_14_4_22, 'rank': max([c for c, n in move_dict.items() if n == 4])}

        md_keys = sorted(move_dict.keys())  # count_dict.get(2) 2张一样的数量
        if len(move_dict) == count_dict.get(2) and Rule.is_continuous_seq(md_keys):
            return {'type': ActionType.TYPE_9_SERIAL_PAIR, 'rank': md_keys[0], 'len': len(md_keys)}

        if len(move_dict) == count_dict.get(3) and Rule.is_continuous_seq(md_keys):
            return {'type': ActionType.TYPE_10_SERIAL_TRIPLE, 'rank': md_keys[0], 'len': len(md_keys)}

        # Check Type 11 (serial 3+1) and Type 12 (serial 3+2)
        if count_dict.get(3, 0) >= MIN_TRIPLES:
            serial_3 = []
            single = []
            pair = []

            for k, v in move_dict.items():
                if v == 3:
                    serial_3.append(k)
                elif v == 1:
                    single.append(k)
                elif v == 2:
                    pair.append(k)
                else:  # no other possibilities
                    return {'type': ActionType.TYPE_16_WRONG}

            serial_3.sort()
            if Rule.is_continuous_seq(serial_3):
                if len(serial_3) == len(single) + len(pair) * 2:
                    return {'type': ActionType.TYPE_11_SERIAL_3_1, 'rank': serial_3[0], 'len': len(serial_3)}
                if len(serial_3) == len(pair) and len(move_dict) == len(serial_3) * 2:
                    return {'type': ActionType.TYPE_12_SERIAL_3_2, 'rank': serial_3[0], 'len': len(serial_3)}
                if drift and len(serial_3) > len(single) + len(pair) * 2:
                    return {'type': ActionType.TYPE_19_SERIAL_3_2_DRIFT, 'rank': serial_3[0], 'len': len(serial_3)}

            if len(serial_3) == 4:
                if Rule.is_continuous_seq(serial_3[1:]):
                    return {'type': ActionType.TYPE_11_SERIAL_3_1, 'rank': serial_3[1], 'len': len(serial_3) - 1}
                if Rule.is_continuous_seq(serial_3[:-1]):
                    return {'type': ActionType.TYPE_11_SERIAL_3_1, 'rank': serial_3[0], 'len': len(serial_3) - 1}

        return {'type': ActionType.TYPE_16_WRONG}

    @staticmethod
    def filter_common(moves, rival_move):
        """ 筛选普通 """
        new_moves = []
        for move in moves:
            if move[0] > rival_move[0]:
                new_moves.append(move)
        return new_moves

    @staticmethod
    def handle_by_bu_xi_pai(moves, rival_move):
        new_moves = []
        for move in moves:
            if move[0] > rival_move[0] or len(move) > len(rival_move):
                new_moves.append(move)
        return new_moves

    @staticmethod
    def filter_type_6_3_1(moves, rival_move):
        """ 筛选三带1 """
        rival_rank = rival_move[1]
        new_moves = []
        for move in moves:
            # move.sort()
            my_rank = move[1]
            if my_rank > rival_rank:
                new_moves.append(move)
        return new_moves

    @staticmethod
    def filter_type_7_3_2(moves, rival_move):
        """ 筛选三带2 """
        rival_rank = rival_move[2]
        new_moves = []
        for move in moves:
            # move.sort()
            my_rank = move[2]
            if my_rank > rival_rank:
                new_moves.append(move)
        return new_moves

    @staticmethod
    def filter_type_11_serial_3_1(moves, rival_move):
        """ 筛选飞机带单 """
        rival = Rule.get_cards_count_dict(rival_move)
        rival_rank = max([k for k, v in rival.items() if v == 3])
        new_moves = []
        for move in moves:
            my_move = Rule.get_cards_count_dict(move)
            my_rank = max([k for k, v in my_move.items() if v == 3])
            if my_rank > rival_rank:
                new_moves.append(move)

        return new_moves

    @staticmethod
    def filter_type_12_serial_3_2(moves, rival_move):
        """ 筛选飞机带双 """
        return Rule.filter_type_11_serial_3_1(moves, rival_move)

    @staticmethod
    def filter_type_13_4_2(moves, rival_move):
        """ 筛选4带2 """
        rival_rank = rival_move[2]
        new_moves = []
        for move in moves:
            # move.sort()
            my_rank = move[2]
            if my_rank > rival_rank:
                new_moves.append(move)
        return new_moves

    @staticmethod
    def filter_type_14_4_22(moves, rival_move):
        """ 筛选4带2对 """
        rival = Rule.get_cards_count_dict(rival_move)
        rival_rank = my_rank = 0
        for k, v in rival.items():
            if v == 4:
                rival_rank = k
        new_moves = []
        for move in moves:
            my_move = collections.Counter(move)
            for k, v in my_move.items():
                if v == 4:
                    my_rank = k
            if my_rank > rival_rank:
                new_moves.append(move)
        return new_moves

    @staticmethod
    def filter_type_15_serial_bomb(moves, rival_move):
        """
        moves: 所有类似的动作
        rival_move：上一个玩家出的动作
        """
        if not moves:
            return moves
        return Rule.handle_by_bu_xi_pai(moves, rival_move)

    @staticmethod
    def get_last_action(turn_cards):
        """ 获取上一个动作 """
        if len(turn_cards) == 0:
            return []
        if len(turn_cards[-1]) == 0:
            last_action = turn_cards[-2]
        else:
            last_action = turn_cards[-1]
            # last_action and last_action.sort()
        return last_action

    @staticmethod
    def one_hand_play_out(cards: List[Cards], allow_actions: dict):
        """ 一手出完 """
        cards = [c.val for c in cards]
        cards.sort()
        rival_type = Rule.get_move_type(cards)
        cards_type = rival_type['type']
        if not allow_actions.get(cards_type.desc):
            return False
        if cards_type == ActionType.TYPE_16_WRONG:
            return False
        card2count = collections.Counter(cards)
        # 有炸弹能一手出，但出出来不是炸弹则不能自动帮出
        if max(card2count.values()) == 4 and cards_type != ActionType.TYPE_4_BOMB:
            return False
        return True

    @staticmethod
    def is_legal_action(action: List[Cards], rival_move: List[Cards], allow_actions: dict):
        """ 是否为合法动作 """
        action = [c.val for c in action]
        rival_move = [c.val for c in rival_move]

        curr_rival_type = Rule.get_move_type(action)
        curr_rival_move_type = curr_rival_type['type']
        # 先判断当前动作是否合法
        if curr_rival_move_type == ActionType.TYPE_16_WRONG:
            return False, None

        if not allow_actions.get(curr_rival_move_type.desc):
            return False, None

        rival_type = Rule.get_move_type(rival_move)
        rival_move_type = rival_type['type']
        if rival_move_type == ActionType.TYPE_0_PASS:
            return True, curr_rival_type

        if curr_rival_move_type != rival_move_type:
            if curr_rival_move_type in (ActionType.TYPE_5_KING_BOMB, ActionType.TYPE_4_BOMB):
                return True, curr_rival_type
            return False, None

        moves = []
        action.sort()
        all_moves = [action]
        if rival_move_type == ActionType.TYPE_1_SINGLE:
            moves = Rule.filter_common(all_moves, rival_move)

        elif rival_move_type == ActionType.TYPE_2_PAIR:
            moves = Rule.filter_common(all_moves, rival_move)

        elif rival_move_type == ActionType.TYPE_3_TRIPLE:
            moves = Rule.filter_common(all_moves, rival_move)

        elif rival_move_type == ActionType.TYPE_4_BOMB:
            moves = Rule.filter_common(all_moves, rival_move)

        elif rival_move_type == ActionType.TYPE_5_KING_BOMB:
            if allow_actions.get(ActionType.TYPE_15_SERIAL_BOMB.desc):
                if curr_rival_move_type == ActionType.TYPE_15_SERIAL_BOMB:
                    moves = all_moves
            else:
                moves = []

        elif rival_move_type == ActionType.TYPE_6_3_1:
            moves = Rule.filter_type_6_3_1(all_moves, rival_move)

        elif rival_move_type == ActionType.TYPE_7_3_2:
            moves = Rule.filter_type_7_3_2(all_moves, rival_move)

        elif rival_move_type == ActionType.TYPE_8_SERIAL_SINGLE:
            moves = Rule.filter_common(all_moves, rival_move)

        elif rival_move_type == ActionType.TYPE_9_SERIAL_PAIR:
            moves = Rule.filter_common(all_moves, rival_move)

        elif rival_move_type == ActionType.TYPE_10_SERIAL_TRIPLE:
            moves = Rule.filter_common(all_moves, rival_move)

        elif rival_move_type == ActionType.TYPE_11_SERIAL_3_1:
            moves = Rule.filter_type_11_serial_3_1(all_moves, rival_move)

        elif rival_move_type == ActionType.TYPE_12_SERIAL_3_2:
            moves = Rule.filter_type_12_serial_3_2(all_moves, rival_move)

        elif rival_move_type == ActionType.TYPE_13_4_2:
            moves = Rule.filter_type_13_4_2(all_moves, rival_move)

        elif rival_move_type == ActionType.TYPE_14_4_22:
            moves = Rule.filter_type_14_4_22(all_moves, rival_move)

        elif rival_move_type == ActionType.TYPE_15_SERIAL_BOMB:
            moves = Rule.filter_type_15_serial_bomb(all_moves, rival_move)

        if moves:
            return True, curr_rival_type

        return False, None

    @staticmethod
    def get_legal_card_play_actions(cards: List[Cards], action_sequence, allow_actions: dict):
        """ 获取当前合法动作 """
        cards = [c.val for c in cards]
        cards_dict = Rule.get_cards_count_dict(cards)

        rival_move = Rule.get_last_action(action_sequence)
        rival_move = [c.val for c in rival_move]

        rival_type = Rule.get_move_type(rival_move)
        rival_move_type = rival_type['type']
        rival_move_len = rival_type.get('len', 1)
        moves = []

        if rival_move_type == ActionType.TYPE_0_PASS:
            moves = Rule.gen_moves(cards, cards_dict, allow_actions)  # 获取包含连炸move

        elif rival_move_type == ActionType.TYPE_1_SINGLE:
            all_moves = Rule.gen_type_1_single(cards)
            moves = Rule.filter_common(all_moves, rival_move)

        elif rival_move_type == ActionType.TYPE_2_PAIR:
            all_moves = Rule.gen_type_2_pair(cards_dict)
            moves = Rule.filter_common(all_moves, rival_move)

        elif rival_move_type == ActionType.TYPE_3_TRIPLE:
            all_moves = Rule.gen_type_3_triple(cards_dict)
            moves = Rule.filter_common(all_moves, rival_move)

        elif rival_move_type == ActionType.TYPE_4_BOMB:
            all_moves = Rule.gen_type_4_bomb(cards_dict) + Rule.gen_type_5_king_bomb(cards_dict)
            moves = Rule.filter_common(all_moves, rival_move)

        elif rival_move_type == ActionType.TYPE_5_KING_BOMB:
            moves = []

        elif rival_move_type == ActionType.TYPE_6_3_1:
            all_moves = Rule.gen_type_6_3_1(cards, cards_dict)
            moves = Rule.filter_type_6_3_1(all_moves, rival_move)

        elif rival_move_type == ActionType.TYPE_7_3_2:
            all_moves = Rule.gen_type_7_3_2(cards_dict)
            moves = Rule.filter_type_7_3_2(all_moves, rival_move)

        elif rival_move_type == ActionType.TYPE_8_SERIAL_SINGLE:
            all_moves = Rule.gen_type_8_serial_single(cards, repeat_num=rival_move_len)
            moves = Rule.filter_common(all_moves, rival_move)

        elif rival_move_type == ActionType.TYPE_9_SERIAL_PAIR:
            all_moves = Rule.gen_type_9_serial_pair(cards_dict, repeat_num=rival_move_len)
            moves = Rule.filter_common(all_moves, rival_move)

        elif rival_move_type == ActionType.TYPE_10_SERIAL_TRIPLE:
            all_moves = Rule.gen_type_10_serial_triple(cards_dict, repeat_num=rival_move_len)
            moves = Rule.filter_common(all_moves, rival_move)

        elif rival_move_type == ActionType.TYPE_11_SERIAL_3_1:
            all_moves = Rule.gen_type_11_serial_3_1(cards, cards_dict, repeat_num=rival_move_len)
            moves = Rule.filter_type_11_serial_3_1(all_moves, rival_move)

        elif rival_move_type == ActionType.TYPE_12_SERIAL_3_2:
            all_moves = Rule.gen_type_12_serial_3_2(cards_dict, repeat_num=rival_move_len)
            moves = Rule.filter_type_12_serial_3_2(all_moves, rival_move)

        elif rival_move_type == ActionType.TYPE_13_4_2:
            all_moves = Rule.gen_type_13_4_2(cards, cards_dict)
            moves = Rule.filter_type_13_4_2(all_moves, rival_move)

        elif rival_move_type == ActionType.TYPE_14_4_22:
            all_moves = Rule.gen_type_14_4_22(cards_dict)
            moves = Rule.filter_type_14_4_22(all_moves, rival_move)

        elif rival_move_type == ActionType.TYPE_15_SERIAL_BOMB:
            all_moves = Rule.gen_type_15_serial_bomb(cards_dict, min_num=rival_move_len)
            moves = Rule.filter_type_15_serial_bomb(all_moves, rival_move)

        if rival_move_type not in [ActionType.TYPE_0_PASS, ActionType.TYPE_4_BOMB,
                                   ActionType.TYPE_5_KING_BOMB, ActionType.TYPE_15_SERIAL_BOMB]:
            moves = moves + Rule.gen_type_4_bomb(cards_dict) + Rule.gen_type_5_king_bomb(cards_dict)

        # 炸弹<王炸<二连炸<三连炸<四连炸<五连炸(连炸最大)
        if rival_move_type != ActionType.TYPE_15_SERIAL_BOMB and allow_actions.get(ActionType.TYPE_15_SERIAL_BOMB.desc):
            all_moves = Rule.gen_type_15_serial_bomb(cards_dict)
            moves += all_moves

        if len(rival_move) != 0:  # rival_move is not 'pass'
            moves = moves + [[]]

        # for m in moves:
        #     m.sort()
        return moves

    @staticmethod
    def gen_moves(cards, cards_dict: dict, allow_actions: dict):
        """ generate all possible moves from given cards """
        moves = []
        moves.extend(Rule.gen_type_1_single(cards))
        moves.extend(Rule.gen_type_2_pair(cards_dict))
        moves.extend(Rule.gen_type_3_triple(cards_dict))  # 允许3不带（新增）
        moves.extend(Rule.gen_type_4_bomb(cards_dict))
        moves.extend(Rule.gen_type_5_king_bomb(cards_dict))
        moves.extend(Rule.gen_type_6_3_1(cards, cards_dict))
        moves.extend(Rule.gen_type_7_3_2(cards_dict))  # 取消3带2（新增）
        moves.extend(Rule.gen_type_8_serial_single(cards))
        moves.extend(Rule.gen_type_9_serial_pair(cards_dict))
        moves.extend(Rule.gen_type_10_serial_triple(cards_dict))
        moves.extend(Rule.gen_type_11_serial_3_1(cards, cards_dict))
        moves.extend(Rule.gen_type_12_serial_3_2(cards_dict))  # 飞机带对（新增）
        moves.extend(Rule.gen_type_13_4_2(cards, cards_dict))  # 后面允许4带2（新增）
        # moves.extend(self.gen_type_14_4_22()) # 取消4带2对
        if allow_actions.get(ActionType.TYPE_15_SERIAL_BOMB.desc):
            moves.extend(Rule.gen_type_15_serial_bomb(cards_dict))
        return moves
