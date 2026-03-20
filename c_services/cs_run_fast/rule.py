import collections
import itertools
from typing import List, Dict

from .poker import Cards
from ..cs_landlords.const import ActionType
from ..cs_landlords.rule import Rule

MIN_SINGLE_CARDS = 5  # 最小连续数
MIN_PAIRS = 2  # 最小连对数
MIN_TRIPLES = 2  # 最小飞机数
S_KING = 18
B_KING = 20


class RunFastRule(Rule):
    """
    跑得快规则算法
    """

    @staticmethod
    def gen_type_9_serial_pair(cards_dict: dict, repeat_num=0):
        """ 双连牌：最少3对 """
        single_pairs = []
        for k, v in cards_dict.items():
            if v >= 2:
                single_pairs.append(k)

        return RunFastRule._gen_serial_moves(single_pairs, MIN_PAIRS, repeat=2, repeat_num=repeat_num)

    @staticmethod
    def check_card_in_hand_is_bigger(cards: list, card_val: int):
        """ 检查手牌中是否有比 card_val 大的牌 """
        val_list = [c.val for c in cards]
        val_list.sort()
        if val_list[-1] > card_val:
            return True
        return False

    @staticmethod
    def get_move_type_run_fast(move, allow_4_3, drift):
        result = Rule.get_move_type(move, drift, True)
        if result['type'] == ActionType.TYPE_16_WRONG:
            move_size = len(move)
            move_dict = collections.Counter(move)
            count_dict = collections.defaultdict(int)
            for c, n in move_dict.items():
                count_dict[n] += 1
            if allow_4_3 and move_size == 7:
                if count_dict.get(4) == 1:
                    return {'type': ActionType.TYPE_18_4_3, 'rank': move[3]}
            md_keys = sorted(move_dict.keys())  # count_dict.get(2) 2张一样的数量
            if len(move_dict) == count_dict.get(2) and Rule.is_continuous_seq(md_keys):
                return {'type': ActionType.TYPE_9_SERIAL_PAIR, 'rank': md_keys[0], 'len': len(md_keys)}
            else:
                return result
        else:
            return result

    @staticmethod
    def is_legal_action_run_fast(action: List[Cards], rival_move: List[Cards], allow_actions: dict, drift: bool, is_last_hand: bool):
        sta, rival_type = Rule.is_legal_action(action, rival_move, allow_actions)
        if sta:
            return sta, rival_type
        else:
            action_cards = [c.val for c in action]
            rival_move = [c.val for c in rival_move]
            allow_4_3 = allow_actions.get(ActionType.TYPE_18_4_3.desc)
            curr_rival_type = RunFastRule.get_move_type_run_fast(action_cards, allow_4_3, drift)
            if allow_actions.get(ActionType.TYPE_17_THREE_A_IS_BOMB.desc) and curr_rival_type['type'] == ActionType.TYPE_3_TRIPLE and \
                    action_cards[0] == 14:
                curr_rival_type['type'] = ActionType.TYPE_17_THREE_A_IS_BOMB
            curr_rival_move_type = curr_rival_type['type']

            rival_type = RunFastRule.get_move_type_run_fast(rival_move, allow_4_3, drift)
            rival_move_type = rival_type['type']

            action_cards.sort()
            all_moves = [action_cards]
            moves = []
            if drift:
                if curr_rival_move_type in [ActionType.TYPE_3_TRIPLE, ActionType.TYPE_6_3_1]:
                    curr_rival_move_type = ActionType.TYPE_20_3_2_DRIFT
            # 先判断当前动作是否合法
            if curr_rival_move_type == ActionType.TYPE_16_WRONG:
                if drift and is_last_hand:
                    move_size = len(action_cards)
                    move_dict = collections.Counter(action_cards)
                    count_dict = collections.defaultdict(int)
                    for c, n in move_dict.items():
                        count_dict[n] += 1
                    if rival_move_type == ActionType.TYPE_13_4_2 and count_dict.get(4) == 1 and move_size == 5:
                        return True, {'type': ActionType.TYPE_21_4_2_DRIFT, 'rank': action_cards[2]}
                    elif allow_4_3 and rival_move_type == ActionType.TYPE_18_4_3 and count_dict.get(4) == 1 and move_size <= 6:
                        return True, {'type': ActionType.TYPE_22_4_3_DRIFT, 'rank': action_cards[2]}

                return False, None

            if not allow_actions.get(curr_rival_move_type.desc):
                return False, None

            if curr_rival_move_type == ActionType.TYPE_17_THREE_A_IS_BOMB:
                return True, curr_rival_type
            if rival_move_type == ActionType.TYPE_0_PASS:
                if curr_rival_move_type in [ActionType.TYPE_19_SERIAL_3_2_DRIFT, ActionType.TYPE_20_3_2_DRIFT, ActionType.TYPE_21_4_2_DRIFT,
                                            ActionType.TYPE_22_4_3_DRIFT]:
                    if not drift:
                        return False, None
                    if drift and not is_last_hand:
                        return False, None
                return True, curr_rival_type
            if curr_rival_move_type != rival_move_type:
                if rival_move_type != ActionType.TYPE_17_THREE_A_IS_BOMB:
                    if curr_rival_move_type == ActionType.TYPE_4_BOMB:
                        return True, curr_rival_type
                    if rival_move_type == ActionType.TYPE_7_3_2 and drift and is_last_hand:
                        moves = Rule.filter_type_7_3_2(all_moves, rival_move)
                    elif rival_move_type == ActionType.TYPE_12_SERIAL_3_2 and drift and is_last_hand:
                        if curr_rival_move_type == ActionType.TYPE_19_SERIAL_3_2_DRIFT:
                            moves = Rule.filter_type_12_serial_3_2(all_moves, rival_move)
                        else:
                            return False, None
                    elif rival_move_type == ActionType.TYPE_22_4_3_DRIFT and drift and is_last_hand:
                        moves = RunFastRule.filter_type_13_4_3(all_moves, rival_move)
                    elif rival_move_type == ActionType.TYPE_19_SERIAL_3_2_DRIFT and drift and is_last_hand:
                        moves = Rule.filter_type_12_serial_3_2(all_moves, rival_move)

            elif rival_move_type == ActionType.TYPE_7_3_2:
                moves = Rule.filter_type_7_3_2(all_moves, rival_move)
            elif rival_move_type == ActionType.TYPE_9_SERIAL_PAIR:
                moves = Rule.filter_common(all_moves, rival_move)
            elif rival_move_type == ActionType.TYPE_12_SERIAL_3_2:
                moves = Rule.filter_type_12_serial_3_2(all_moves, rival_move)

            if moves:
                return True, curr_rival_type

            return False, None

    @staticmethod
    def get_legal_card_play_actions_run_fast(cards: List[Cards], action_sequence, allow_actions: dict, drift: bool, max_player=3):
        """ 获取当前牌型可以打的牌型 """
        moves = Rule.get_legal_card_play_actions(cards, action_sequence, allow_actions, drift, max_player, True)

        cards = [c.val for c in cards]
        cards_dict = Rule.get_cards_count_dict(cards)

        rival_move = Rule.get_last_action(action_sequence, max_player)
        rival_move = [c.val for c in rival_move]
        allow_4_3 = allow_actions.get(ActionType.TYPE_18_4_3.desc)
        rival_type = RunFastRule.get_move_type_run_fast(rival_move, allow_4_3, drift)
        rival_move_type = rival_type['type']
        rival_move_len = rival_type.get('len', 1)
        if len(rival_move) != 0:
            moves.pop()
        if allow_actions.get(ActionType.TYPE_18_4_3.desc):
            if rival_move_type == ActionType.TYPE_18_4_3:
                all_moves = RunFastRule.gen_type_13_4_3(cards, cards_dict)
                moves = Rule.filter_type_13_4_2(all_moves, rival_move)

        if rival_move_type in [ActionType.TYPE_7_3_2, ActionType.TYPE_12_SERIAL_3_2] and not moves:
            if drift:
                moves = RunFastRule.get_drift_cards(cards, cards_dict, rival_move_type, rival_move_len)
        elif rival_move_type in [ActionType.TYPE_13_4_2, ActionType.TYPE_18_4_3]:
            if drift:
                moves = RunFastRule.get_drift_cards(cards, cards_dict, rival_move_type, rival_move_len)
        elif not moves and rival_move_type == ActionType.TYPE_9_SERIAL_PAIR:
            all_moves = RunFastRule.gen_type_9_serial_pair(cards_dict, repeat_num=rival_move_len)
            moves = Rule.filter_common(all_moves, rival_move)

        if allow_actions.get(ActionType.TYPE_17_THREE_A_IS_BOMB.desc):  # 三A是炸弹
            if rival_move_type not in [ActionType.TYPE_0_PASS, ActionType.TYPE_15_SERIAL_BOMB]:
                moves = moves + RunFastRule.gen_type_3_three_a_bomb(cards_dict)
            if rival_move_type == ActionType.TYPE_17_THREE_A_IS_BOMB:
                moves = []

        if len(rival_move) != 0:  # rival_move is not 'pass'
            moves = moves + [[]]

        return moves

    @staticmethod
    def gen_type_3_three_a_bomb(cards_dict: dict):
        """ 三A炸 """
        bomb_moves = []
        for k, v in cards_dict.items():
            if v == 3 and k == 14:
                bomb_moves.append([k, k, k])
        return bomb_moves

    @staticmethod
    def gen_type_13_4_3(cards: list[int], cards_dict):
        """ 4带3 """
        four_cards = []
        for k, v in cards_dict.items():
            if v == 4:
                four_cards.append(k)

        result = []
        for fc in four_cards:
            cards_list = [k for k in cards if k != fc]
            subcards = Rule.select(cards_list, 3)
            for i in subcards:
                result.append([fc] * 4 + i)
        return list(k for k, _ in itertools.groupby(result))

    @staticmethod
    def get_drift_cards(cards: list[int], cards_dict, rival_move_type, repeat_num=0):
        """获取合法甩尾牌"""
        if rival_move_type == ActionType.TYPE_7_3_2:
            return RunFastRule.get_drift_three_or_four(cards, cards_dict, 3, 5)
        elif rival_move_type == ActionType.TYPE_12_SERIAL_3_2:
            serial_3_moves = Rule.gen_type_10_serial_triple(cards_dict, repeat_num=repeat_num)
            if len(serial_3_moves) == 1 and len(cards) < repeat_num * 3 + repeat_num * 2:
                return [cards]
            else:
                return []
        elif rival_move_type == ActionType.TYPE_13_4_2:
            return RunFastRule.get_drift_three_or_four(cards, cards_dict, 4, 6)
        elif rival_move_type == ActionType.TYPE_18_4_3:
            return RunFastRule.get_drift_three_or_four(cards, cards_dict, 4, 7)

    @staticmethod
    def get_drift_three_or_four(cards: list[int], cards_dict, drift_cards_len, max_len):
        drift_cards = []
        for k, v in cards_dict.items():
            if v == drift_cards_len:
                drift_cards.append(k)
        if len(drift_cards) == 1 and len(cards) < max_len:
            return [cards]
        else:
            return []

    @staticmethod
    def filter_type_13_4_3(moves, rival_move):
        """ 筛选4带3 """
        rival_rank = rival_move[3]
        new_moves = []
        for move in moves:
            # move.sort()
            my_rank = move[3]
            if my_rank > rival_rank:
                new_moves.append(move)
        return new_moves

    @staticmethod
    def one_hand_play_out_run_fast(cards: List[Cards], allow_actions: dict, drift: bool):
        """ 一手出完 """
        cards = [c.val for c in cards]
        cards.sort()
        allow_4_3 = allow_actions.get(ActionType.TYPE_18_4_3.desc)
        rival_type = RunFastRule.get_move_type_run_fast(cards, allow_4_3, drift)
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
