import random
from collections import Counter, defaultdict

from c_services.const.base_card import BaseCard
from common.utils.utils import UtilsTool


class BasePoker:
    CARDS_ENUM: BaseCard

    def __init__(self,not_include=0,lai_zi_count =0):
        self.__cursor = 0
        card_list = self.CARDS_ENUM.all_cards(lai_zi_count)
        if not_include!= 0:
            card_list = [card for card in card_list if card.suit != not_include]
        self.__cards = card_list
        self.__cards_count = len(self.__cards)
        self.__set_cards_list = []
        self.__not_set_cards = []

    @property
    def cards(self):
        return self.__cards

    @property
    def cards_count(self):
        return self.__cards_count + len(self.CARDS_ENUM.extra_cards())

    @property
    def all_cards(self):
        return self.__cards + self.CARDS_ENUM.extra_cards()

    @classmethod
    def get_card_by_key(cls, card: int):
        """ 根据key获取牌对象 """
        card = cls.CARDS_ENUM.find_member_by_val(card)
        if not card:
            raise TypeError(f"card error: {card} is {type(card)}")
        return card

    def shuffle_cards(self, card_count):
        """ 洗牌 """
        self.__cursor = 0
        self.__not_set_cards = []
        if self.__set_cards_list:
            self.__set_cards_ordered(card_count)
        else:
            random.shuffle(self.__cards)
            half_idx = self.__cards_count // 2
            self.swap_card(0, half_idx)
            self.swap_card(half_idx, self.__cards_count - 1)
            random.shuffle(self.__cards)

    def swap_card(self, start_idx: int, end_idx: int):
        """ 交换牌位置 """
        while 1:
            self.__cards[start_idx], self.__cards[end_idx] = self.__cards[end_idx], self.__cards[start_idx]
            start_idx += 1
            end_idx -= 1
            if start_idx >= end_idx:
                break

    # def pop(self):
    #     """ 发一张牌 """
    #     if self.__cursor >= self.__cards_count:
    #         return 0
    #     c = self.__cards[self.__cursor]
    #     self.__cursor += 1
    #     return c

    def pop(self, card=None):
        """弹出指定牌（若未指定则按原规则顺序发牌）"""
        # 情况1：指定目标牌
        if card is not None:
            try:
                # 查找目标牌位置（从当前游标开始搜索）
                idx = self.__cards.index(card, self.__cursor)

                if self.__cursor >= self.__cards_count:
                    return 0

                # 交换目标牌与其后一位（多重赋值实现交换）
                self.__cards[idx], self.__cards[self.__cursor] = self.__cards[self.__cursor], self.__cards[idx]
                c = self.__cards[self.__cursor]
                self.__cursor += 1
                return c
            except ValueError:  # 目标牌不存在
                return 0

        # 情况2：未指定牌时按原顺序发牌
        if self.__cursor >= self.__cards_count:
            return 0
        c = self.__cards[self.__cursor]
        self.__cursor += 1
        return c

    def deal_cards(self, player_count: int = 2, card_count: int = 4, extra_count=0):
        """
        发牌总接口
        params: player_count 人数
        params: card_count 牌数
        params: extra_count 额外牌数
        """
        # 先发
        all_cards = [[] for _ in range(player_count)]
        self.shuffle_cards(card_count)
        for _ in range(card_count):
            for i in range(player_count):
                all_cards[i].append(self.pop())
        if extra_count > 0:
            extra_list = []
            for _ in range(extra_count):
                extra_list.append(self.pop())
            all_cards.append(extra_list)
        return all_cards

    def deal_good_cards(self,player_count: int = 4):

        cards_pool = self.CARDS_ENUM.all_cards().copy()
        result_dict = dict(Counter(cards_pool)).copy()

        players_hands = [[] for _ in range(player_count + 1)]
        for player_id in range(player_count):
            hands = [51]
            combo_count = 0
            dui_zi_index = 0
            count = int(UtilsTool.random_choice_num([5, 4], [0.2, 0.8]))
            suit_list = random.sample(range(1, 4), 2)  # 控制花色为两种
            kz_ctrl = int(UtilsTool.random_choice_num([1, 2], [0.4, 0.6]))  # 控制刻子数量
            kz_index = random.randrange(0, 2)  # 控制刻子是否连续 0不连续
            if kz_index != 0:
                kz_index = random.randrange(1, 8)  # 连续的起点
            if kz_ctrl == 1:
                kz_index = random.randrange(2, 7)
            if count == 5:
                dui_zi_index = random.randrange(1, 5)
            while combo_count < count:
                combo = self.get_better_cards_combo(result_dict,combo_count,1,dui_zi_index,kz_ctrl,kz_index,suit_list)
                if self.has_cards(combo,result_dict):
                    for card in combo:
                        if result_dict.get(card, 0):
                            result_dict[card] -= 1
                    hands.extend(combo)
                combo_count += 1
            valid_items = [key for key, value in result_dict.items() if value > 0]
            random.shuffle(valid_items)
            for i in range(13 - len(hands)):
                if valid_items:  # 确保非空
                    card = valid_items.pop()
                    hands.append(card)
                    result_dict[card] -= 1
            players_hands[player_id] = hands
        # players_hands[0] = [51,51,12,12,13,13,24,24,25,25,26,26,27]
        print("players_hands",players_hands)
        self.__set_cards_list = players_hands
        return players_hands



    @property
    def left_count(self):
        """ 剩余多少牌 """
        return max(self.__cards_count - self.__cursor, 0)

    @property
    def remain_cards(self):
        """ 剩余牌：未使用的牌 """
        return self.__cards[self.__cursor:]

    def set_order_cards(self, cards):
        print("设牌信息",cards)
        self.__set_cards_list = cards
        return True

    # def __set_cards_ordered(self, card_count):
    #     """
    #     根据设牌使self.__cards发牌有序
    #     :params card_count: 多少人
    #     :params per_count: 每人多少张
    #     """
    #     # 设置手牌
    #     all_set_cards = []
    #     player_count = len(self.__set_cards_list) - 1  # 在这里计算人数表示 只发设置人数
    #     for cards in self.__set_cards_list[:-1]:
    #         all_set_cards.extend(cards)
    #
    #     # 设置摸牌
    #     set_mo_cards = self.__set_cards_list[-1]
    #
    #     # 其余牌
    #     remain_cards = list(set(self.all_cards).difference(all_set_cards).difference(set_mo_cards))
    #
    #     order_cards = []
    #     for i in range(card_count):
    #         for j in range(player_count):
    #             per_cards = self.__set_cards_list[j]
    #             if i < len(per_cards):
    #                 order_cards.append(per_cards[i])
    #             else:
    #                 # 未设置的牌用剩余牌填充
    #                 order_cards.append(remain_cards.pop())
    #
    #     # 设置摸牌
    #     order_cards.extend(set_mo_cards)
    #     order_cards.extend(remain_cards)
    #     order_cards = [self.get_card_by_key(c) for c in order_cards]
    #
    #     self.__cards = order_cards
    #     self.__set_cards_list.clear()  # 清除当前设牌

    def __set_cards_ordered(self, card_count):
        """
        根据设牌使self.__cards发牌有序
        :params card_count: 多少人
        :params per_count: 每人多少张
        """
        # 设置手牌
        all_set_cards = []
        set_cards = []
        player_count = len(self.__set_cards_list) - 1  # 在这里计算人数表示 只发设置人数
        for cards in self.__set_cards_list[:-1]:
            all_set_cards.extend(cards[:card_count]) #根据传入牌数切片处理防止设牌数量大于发牌数量,导致总的牌数量有误
            set_cards.extend(cards[card_count:])
        print("set_cards",set_cards)
        self.__not_set_cards = self.__set_cards_list[:-1]
        # 设置摸牌
        set_mo_cards = self.__set_cards_list[-1]

        all_cards_map = {}
        for c in self.all_cards:
            all_cards_map[c] = all_cards_map.get(c, 0) + 1
        all_set_cards_map = {}

        for c in all_set_cards + set_mo_cards:
            all_set_cards_map[c] = all_set_cards_map.get(c, 0) + 1

        for card, count in all_cards_map.items():
            all_cards_map[card] = count - all_set_cards_map.get(card, 0)

        # 其余牌
        print("all_cards_map", all_cards_map)
        remain_cards = []
        for card, count in all_cards_map.items():
            remain_cards.extend([card] * count)

        random.shuffle(remain_cards)
        for card in set_cards:
            remain_cards.remove(card)
        order_cards = []
        for i in range(card_count):
            for j in range(player_count):
                per_cards = self.__set_cards_list[j]
                if i < len(per_cards):
                    order_cards.append(per_cards[i])
                else:
                    # 未设置的牌用剩余牌填充
                    remain_cards and order_cards.append(remain_cards.pop())


        # 设置摸牌
        # order_cards.extend(set_mo_cards)
        remain_cards.extend(set_cards)
        random.shuffle(remain_cards)
        order_cards.extend(remain_cards)
        print("order_cards",order_cards)
        order_cards = [self.get_card_by_key(c) for c in order_cards]

        self.__cards = order_cards
        self.__set_cards_list.clear()  # 清除当前设牌

    def not_set_cards_ordered(self,seats,card_count,bu_card_count,is_clear = True):
        not_set_cards = []
        not_set_cards_list = []
        for i ,cards in enumerate(self.__not_set_cards):
            if i+1 in seats:
                not_set_cards.extend(cards[card_count:])
                not_set_cards_list.append(cards[card_count:])

        count_no = Counter(not_set_cards)
        count_remain = Counter(self.__cards[self.__cursor:])

        # 检查 remain_cards 是否包含足够元素
        for item, req_count in count_no.items():
            if count_remain.get(item, 0) < req_count:
                raise ValueError(f"元素 {item} 数量不足（需要 {req_count} 个，实际 {count_remain.get(item, 0)} 个）")

        temp = []  # 存储非匹配元素
        count = count_no.copy()  # 动态计数器

        for card in self.__cards[self.__cursor:]:
            if card in count and count[card] > 0:
                count[card] -= 1  # 标记已匹配
            else:
                temp.append(card)  # 保留非匹配元素
        print("remain_cards",self.__cards[self.__cursor:])
        new_remain = []
        remain_set_cards = []
        for cards in not_set_cards_list:
            if not cards:
                new_remain = new_remain + temp[:bu_card_count]
                temp = temp[bu_card_count:]
            else:
                new_remain = new_remain + cards[:bu_card_count]
                remain_set_cards.extend(cards[bu_card_count:])
        new_remain = new_remain + temp + remain_set_cards
        self.__cards[self.__cursor:] = new_remain  # 同步修改原列表
        if is_clear:
            self.__not_set_cards = []
        print("new_remain",self.__cards[self.__cursor:])



    @staticmethod
    def get_better_cards_combo(cards, count=0, suit_start=1, dui_zi = 0, kz_ctl=2, kz_index =0, suit_list=None):
        """ 手牌发较好的牌 """
        if suit_list is None:
            suit_list = []
        kz_cards = []
        dz_cards = []
        for card, card_count  in cards.items():
            if card_count>=3:
                kz_cards.append(card)
            elif card_count>=2:
                dz_cards.append(card)
        result = []
        san_zhang = 1 if count == 3 else kz_ctl
        if count <= san_zhang:
            combo_type =  1
        else:
            if kz_ctl == 1:
                combo_type = 5
            else:
                combo_type = int(UtilsTool.random_choice_num([2, 3, 5], [0.3, 0.3,0.4]))
        if dui_zi!=0:
            combo_type = 5
        # 顺子
        if combo_type == 0:
            sz_combo = [[1, 2, 3], [2, 3, 4], [3, 4, 5], [4, 5, 6], [5, 6, 7], [6, 7, 8], [7, 8, 9]]
            sz_index = random.randrange(0, len(sz_combo))
            combo = sz_combo[sz_index]
            # 获取花色
            combo_suit = random.randrange(suit_start, suit_start+2)
            for card in combo:
                result.append(combo_suit * 10 + card)
        # 刻子
        elif combo_type == 1:
            # 特殊处理好牌发刻子
            combo_suit = int(UtilsTool.random_choice_num([suit_list[0], suit_list[1]], [0.85, 0.15]))
            if kz_index != 0 or kz_ctl==1:
                combo_suit = suit_list[0]
            if kz_index ==0:
                valid_cards = [num for num in kz_cards if (num // 10) % 10 == combo_suit]
                first_match = random.choice(valid_cards) if valid_cards else None
            else:
                first_match = next((num for num in kz_cards if (num // 10) % 10 == combo_suit and num % 10 >= kz_index), None)
                if first_match is None:
                    allowed = [i for i in range(1, 4) if i != combo_suit]
                    for suit in allowed:
                        first_match = next((num for num in kz_cards if (num // 10) % 10 == suit and num % 10 >= kz_index), None)
                        if first_match is not None:
                            break

            result.extend([first_match] * 3)

        # 两张
        elif combo_type == 2:
            combo = random.randrange(1, 9)
            combo_suit = random.randrange(suit_start, suit_start+2)
            c_suit = combo_suit * 10
            result.append(c_suit + combo)
            result.append(c_suit + (combo + 1))
        # 隔张
        elif combo_type == 3:
            combo = random.randrange(1, 6)
            combo_suit = random.randrange(suit_start, suit_start+2)
            c_suit = combo_suit * 10
            result.append(c_suit + combo)
            result.append(c_suit + (combo + 4))
        else:
            result = []
            rate1 = 0.1
            rate2 = 0.9
            if kz_ctl ==1 :
                rate1 = 0.9
                rate2 = 0.1
                if kz_index != 0:
                    dui_zi = kz_index-1
            combo_suit = int(UtilsTool.random_choice_num([suit_list[0], suit_list[1]], [rate1, rate2]))
            # 特殊处理好牌发连续的对子
            if dui_zi!=0:
                combo_suit = suit_list[0]
            first_match = None
            if len(kz_cards)!=0:
                first_match = next((num for num in kz_cards if (num // 10) % 10 == combo_suit and num % 10 >=dui_zi), None)
            if first_match is None:
                first_match = next((num for num in dz_cards if (num // 10) % 10 == combo_suit and num % 10 >= dui_zi), None)
            result.extend([first_match]*2)
        # print("result",result)
        return result

    @staticmethod
    def has_cards(cards, result_dict):
        if cards[0] == cards[1]:
            return result_dict.get(cards[0], 0) >= len(cards)
        for card in cards:
            if result_dict.get(card, 0) == 0:
                return False

        return True


