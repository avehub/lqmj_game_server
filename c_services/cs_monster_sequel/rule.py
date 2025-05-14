from typing import List
from c_services.base.base_rule import BaseRule
from .poker import Cards
from c_services.const.base_card import BaseCard, CardsSuit


class Rule(BaseRule):
    """ 打妖怪下篇规则类 """
    # 妖怪阵营
    __CAMP_MONSTER = (Cards.FK_A, Cards.FK_2, Cards.FK_3, Cards.FK_4, Cards.FK_5, Cards.FK_6, Cards.FK_7, Cards.FK_8)
    __CAMP_MONSTER_EXCLUDE_FAKE_WU_KONG = (
        Cards.FK_A, Cards.FK_3, Cards.FK_4, Cards.FK_5, Cards.FK_6, Cards.FK_7, Cards.FK_8)
    # 徒弟阵营
    __CAMP_PRENTICE = (Cards.MH_9, Cards.MH_10, Cards.MH_J)
    # 仙佛阵营
    CAMP_DIVINE = (Cards.HT_Q, Cards.HT_K, Cards.HT_A)

    @staticmethod
    def rm_from_end(lst, val):
        # 从后向前遍历，找到并移除第一个匹配的元素
        for i in range(len(lst) - 1, -1, -1):
            if lst[i] == val:
                del lst[i]
                break

    @staticmethod
    def contain(cards: List[BaseCard], play_cards: List[int]):
        """ 出牌是否满足手牌包含 """
        hand_card2count = Rule.stat_card_count(cards)
        play_card2count = Rule.stat_card_count(play_cards)
        for pc, count in play_card2count.items():
            if count > hand_card2count.get(pc, 0):
                return False
        return True

    @staticmethod
    def is_master_with_dragon(cards: List[BaseCard]):
        """ 是否是唐僧+小白龙 """
        return cards[0] == Cards.HX_A and cards[1] == Cards.HT_Q or cards[0] == Cards.HT_Q and cards[1] == Cards.HX_A

    @staticmethod
    def have_master_with_dragon(cards_dict: dict):
        """ cards 白龙马和唐僧 """
        return cards_dict.get(Cards.HX_A) and cards_dict.get(Cards.HT_Q)

    @staticmethod
    def is_ben_bo_er_ba_and_ba_bo_er_ben(cards: List[BaseCard]):
        """ 是否是: 奔波儿霸和霸波儿奔 """
        return cards[0] == Cards.FK_A and cards[1] == Cards.FK_3 or cards[0] == Cards.FK_3 and cards[1] == Cards.FK_A

    @staticmethod
    def have_ben_bo_er_ba_and_ba_bo_er_ben(cards_dict: dict):
        """ cards是否有 奔波儿霸 和 霸波儿奔 """
        return cards_dict.get(Cards.FK_A) and cards_dict.get(Cards.FK_3)

    @staticmethod
    def have_divine_cards(cards_dict: dict):
        """ 是否有神仙牌 """
        return cards_dict.get(Cards.HT_Q) or cards_dict.get(Cards.HT_K) or cards_dict.get(Cards.HT_A)

    @staticmethod
    def get_move_type(rival_move):
        """ 获取动作类型 """

    @staticmethod
    def compare_same_camp(rival_move, rival_len, cards_dict):
        """ 相同阵营的比较 """
        actions = []
        for card, count in cards_dict.items():
            if card.suit == rival_move.suit and card.val > rival_move.val and count >= rival_len:
                actions.append([card] * rival_len)
        return actions

    @staticmethod
    def compare_by_len(cards_dict, rival_len, camp: tuple, is_gte=False):
        """
        通过阵营比较
        is_gte: 数量大于等于
        """
        actions = []
        if is_gte:
            for p in camp:
                _rival_len = rival_len
                camp_len = cards_dict.get(p, 0)
                while camp_len >= _rival_len:
                    actions.append([p] * _rival_len)  # 主要计算妖怪抓唐僧的场景
                    _rival_len += 1
        else:
            for p in camp:
                if cards_dict.get(p, 0) >= rival_len:
                    actions.append([p] * rival_len)
        return actions

    @staticmethod
    def sort_legal_cards(legal_cards: List[List[Cards]]):
        """
        排序合法动作
        多张>单张>组合；
        大点数>小点数；
        其它牌>神佛牌
        """
        divine_cards = []
        comb_cards = []
        other_cards = []
        for act in legal_cards:
            if len(act) == 1 and act[0] in Rule.CAMP_DIVINE:
                divine_cards.append(act)
            elif len(act) == 2 and (Rule.is_ben_bo_er_ba_and_ba_bo_er_ben(act) or Rule.is_master_with_dragon(act)):
                comb_cards.append(act)
            else:
                other_cards.append(act)
        other_cards.sort(key=lambda cards: (len(cards), cards[0]), reverse=True)
        comb_cards.sort(key=lambda cards: cards[0], reverse=True)
        divine_cards.sort(key=lambda cards: cards[0], reverse=True)
        return other_cards + comb_cards + divine_cards

    @staticmethod
    def get_legal_card_play_actions(turn_cards: List[list], hand_cards, wu_kong_played=True):
        """
        获取所有合法动作
        rival_move: 上家出牌
            注意：这里传进来的需要是根据游戏进程情况变化的牌，比如奔波儿霸与霸波儿奔如果被观音、如来减少出牌数时，下家只能视为1张数字3
        """
        rival_move = Rule.get_last_action(turn_cards)

        if not rival_move:
            return Rule.gen_moves(hand_cards)

        cards_dict = Rule.stat_card_count(hand_cards)

        rival_len = len(rival_move)
        moves = []
        if rival_len == 1:
            # 奔波儿霸与霸波儿奔组合接在任意单张牌或一对
            if Rule.have_ben_bo_er_ba_and_ba_bo_er_ben(cards_dict):
                moves.append([Cards.FK_A, Cards.FK_3])

        elif rival_len == 2:
            # 组合牌：奔波儿霸与霸波儿奔、唐僧与小白龙
            # 奔波儿霸与霸波儿奔组合接在任意单张牌或一对 todo: 是否能接奔波儿霸与霸波儿奔
            if Rule.have_ben_bo_er_ba_and_ba_bo_er_ben(cards_dict):
                moves.append([Cards.FK_A, Cards.FK_3])

            if Rule.is_ben_bo_er_ba_and_ba_bo_er_ben(rival_move):
                # 用大于3的单张或一对来接
                # 妖怪阵营：同阵营更大的 + 徒弟阵营 单张或一对
                # 这里包含了金角银角大王
                moves.extend(Rule.compare_same_camp(Cards.FK_3, 1, cards_dict))
                moves.extend(Rule.compare_by_len(cards_dict, 1, Rule.__CAMP_PRENTICE))

                moves.extend(Rule.compare_same_camp(Cards.FK_3, 2, cards_dict))
                moves.extend(Rule.compare_by_len(cards_dict, 2, Rule.__CAMP_PRENTICE))

                if not wu_kong_played:  # 真悟空未出，六耳猕猴充当真悟空
                    moves.extend(Rule.compare_by_len(cards_dict, 1, (Cards.FK_2,)))
                    moves.extend(Rule.compare_by_len(cards_dict, 2, (Cards.FK_2,)))

            if Rule.is_master_with_dragon(rival_move):
                # 如果是唐僧 + 小白龙：下家只需当作接唐僧牌
                # 妖怪阵营也包含了金角银角大王（下面注意不要计算重复）
                camp_cards = Rule.__CAMP_MONSTER
                if not wu_kong_played:
                    camp_cards = Rule.__CAMP_MONSTER_EXCLUDE_FAKE_WU_KONG
                moves.extend(Rule.compare_by_len(cards_dict, 1, camp_cards, is_gte=True))

        rival2count = Rule.stat_card_count(rival_move)
        if len(rival2count) == 1:  # 上家出的都是相同牌
            rival_card = rival_move[0]
            rival_camp = rival_card.suit  # 阵营
            if rival_camp == CardsSuit.DIAMONDS:
                # 1.妖怪阵营 < 同阵营更大的 + 徒弟阵营
                if wu_kong_played or rival_card != Cards.FK_2:
                    moves.extend(Rule.compare_same_camp(rival_card, rival_len, cards_dict))
                    moves.extend(Rule.compare_by_len(cards_dict, rival_len, Rule.__CAMP_PRENTICE))

                if not wu_kong_played:
                    if rival_card != Cards.FK_2:
                        moves.extend(Rule.compare_by_len(cards_dict, rival_len, (Cards.FK_2,)))
                    else:
                        # 真悟空未出，六耳猕猴充当真悟空
                        moves.extend(Rule.compare_by_len(cards_dict, rival_len, (Cards.HX_A, Cards.FK_4, Cards.FK_5)))
                        if rival_len == 1 and Rule.have_master_with_dragon(cards_dict):
                            moves.append([Cards.HX_A, Cards.HT_Q])

            elif rival_camp == CardsSuit.CLUBS:
                # 2.徒弟阵营 < 同阵营更大的 + 师傅阵营
                if rival_len == 1 and Rule.have_master_with_dragon(cards_dict):
                    moves.append([Cards.HX_A, Cards.HT_Q])
                moves.extend(Rule.compare_by_len(cards_dict, rival_len, (Cards.HX_A,)))
                if rival_card == Cards.MH_J:  # 牛魔王可以接悟空
                    moves.extend(Rule.compare_by_len(cards_dict, rival_len, (Cards.FK_5,)))

                if not wu_kong_played:  # 真悟空未出，六耳猕猴充当真悟空
                    moves.extend(Rule.compare_by_len(cards_dict, rival_len, (Cards.FK_2,)))
                moves.extend(Rule.compare_same_camp(rival_card, rival_len, cards_dict))

            elif rival_camp == CardsSuit.HEARTS:
                # 3.师傅阵营 < 妖怪阵营
                camp_cards = Rule.__CAMP_MONSTER
                if not wu_kong_played:
                    camp_cards = Rule.__CAMP_MONSTER_EXCLUDE_FAKE_WU_KONG
                moves.extend(Rule.compare_by_len(cards_dict, rival_len, camp_cards, is_gte=True))

            # 此处是为了过滤，因为上面`1处`计算可能已经把金角银角算进去了
            # 如果是徒弟阵营 或者 是妖怪阵营并且大于金角银角
            if rival_camp == CardsSuit.CLUBS or (rival_camp == CardsSuit.DIAMONDS and rival_card >= Cards.FK_4):
                if cards_dict.get(Cards.FK_4, 0) >= rival_len:
                    moves.append([Cards.FK_4] * rival_len)

        # .仙佛牌都能接
        if cards_dict.get(Cards.HT_Q):
            moves.append([Cards.HT_Q])
        if cards_dict.get(Cards.HT_K):
            moves.append([Cards.HT_K])
        if cards_dict.get(Cards.HT_A):
            moves.append([Cards.HT_A])

        return moves

    @staticmethod
    def get_last_action(turn_cards):
        """ 获取上一个动作 """
        turn_cards_len = len(turn_cards)
        if turn_cards_len > 0:
            last_act = turn_cards[-1][-1]
            if len(last_act) == 1:  # 此处主要判断仙佛牌
                last_card = last_act[0]
                if turn_cards_len == 1:  # 首出仙佛牌，下家任意出
                    if last_card in Rule.CAMP_DIVINE:
                        return []
                if last_card == Cards.HT_A:  # 上家打如来，下家任意出
                    return []
                if last_card == Cards.HT_Q or last_card == Cards.HT_K:  # 上家打小白龙和观音
                    idx = 2
                    while turn_cards_len >= idx:
                        c = turn_cards[-idx][-1]
                        if c[0] == Cards.HT_A:
                            return []
                        if c[0] not in (Cards.HT_Q, Cards.HT_K):
                            return c
                        idx += 1
                    return []
            return last_act
        return []

    @staticmethod
    def compare(last_cards: list, attack_cards: list) -> bool:
        """
        比较attack_card是否大过last_card
        """
        attack_len = len(attack_cards)
        attack_cards_dict = Rule.stat_card_count(attack_cards)
        # 1.仙牌都可接
        if attack_len == 1 and Rule.have_divine_cards(attack_cards_dict):
            return True
        # last_cards_dict = Rule.stat_card_count(last_cards)
        last_cards_len = len(last_cards)
        if last_cards_len == 2:
            # 组合牌
            # 奔波儿霸 && 霸波儿奔
            if Rule.is_ben_bo_er_ba_and_ba_bo_er_ben(last_cards):
                if len(attack_cards_dict) == 1 and attack_cards[0].val > 3:
                    return True
            # 唐僧 && 小白龙
            if Rule.is_master_with_dragon(last_cards):
                if attack_len == 1 and attack_cards[0].suit == CardsSuit.DIAMONDS:
                    return True

        if len(attack_cards_dict) != 1:  # 不是相同的牌则不让出
            return False
        last_card = last_cards[0]
        last_camp = last_card.suit  # 阵营
        # if attack_len != last_cards_len:  # 除了仙佛牌以及组合牌 接牌数量必须一致
        if last_camp != CardsSuit.HEARTS and attack_len != last_cards_len:  # 除了仙佛牌以及组合牌 接牌数量必须一致
            return False

        attack_card = attack_cards[0]
        if last_camp == CardsSuit.DIAMONDS:
            # 1.妖怪阵营 < 同阵营更大的 + 徒弟阵营
            if attack_card.suit == CardsSuit.CLUBS or (attack_card.suit == last_camp and attack_card > last_card):
                return True
        elif last_camp == CardsSuit.CLUBS:
            # 2.徒弟阵营 < 同阵营更大的 + 师傅阵营
            if attack_card.suit == CardsSuit.HEARTS or (attack_card.suit == last_camp and attack_card > last_card):
                return True
            # 2.1 牛魔王可以接孙悟空
            if last_card == Cards.MH_J and attack_card == Cards.FK_5:
                return True
        elif last_camp == CardsSuit.HEARTS:
            # 3.师傅阵营 < 妖怪阵营(大于等于相同数量)
            if attack_card.suit == CardsSuit.DIAMONDS and attack_len >= last_cards_len:
                return True
        if attack_card == Cards.FK_4:  # 金角银角都可以接
            return True

        return False

    @staticmethod
    def gen_first_play_moves(cards_dict: dict):
        """
        首出moves
        组合＞多张＞单张；
        大点数>小点数；其它牌＞神佛牌
        """
        moves = []

        # 奔波儿霸 & 霸波儿奔
        if Rule.have_ben_bo_er_ba_and_ba_bo_er_ben(cards_dict):
            moves.append([Cards.FK_A, Cards.FK_3])

        # 唐僧 & 小白龙
        if Rule.have_master_with_dragon(cards_dict):
            moves.append([Cards.HX_A, Cards.HT_Q])

        divine_cards = []
        c = cards_dict.pop(Cards.HT_Q, None)
        if c:
            divine_cards.append([Cards.HT_Q])
        c = cards_dict.pop(Cards.HT_K, None)
        if c:
            divine_cards.append([Cards.HT_K])
        c = cards_dict.pop(Cards.HT_A, None)
        if c:
            divine_cards.append([Cards.HT_A])

        for k, v in sorted(cards_dict.items(), key=lambda x: x[1], reverse=True):
            if v >= 6:
                moves.append([k, k, k, k, k, k])
            if v >= 5:
                moves.append([k, k, k, k, k])
            if v >= 4:
                moves.append([k, k, k, k])
            if v >= 3:
                moves.append([k, k, k])
            if v >= 2:
                moves.append([k, k])
            moves.append([k])

        if divine_cards:
            moves.extend(divine_cards)
        return moves

    @staticmethod
    def gen_moves(cards):
        """ 首出动作 """
        moves = []
        cards_dict = Rule.stat_card_count(cards)
        moves.extend(Rule.gen_first_play_moves(cards_dict))
        return moves
