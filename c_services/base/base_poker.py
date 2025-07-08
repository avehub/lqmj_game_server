import random
from collections import Counter

from c_services.const.base_card import BaseCard


class BasePoker:
    CARDS_ENUM: BaseCard

    def __init__(self,not_include=0):
        self.__cursor = 0
        card_list = self.CARDS_ENUM.all_cards()
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
        if self.__set_cards_list:
            self.__set_cards_ordered(card_count)
        else:
            print("self.__cards",len(self.__cards))
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

    def pop(self):
        """ 发一张牌 """
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

    @property
    def left_count(self):
        """ 剩余多少牌 """
        return max(self.__cards_count - self.__cursor, 0)

    @property
    def remain_cards(self):
        """ 剩余牌：未使用的牌 """
        return self.__cards[self.__cursor:]

    def set_order_cards(self, cards):
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
        player_count = len(self.__set_cards_list) - 1  # 在这里计算人数表示 只发设置人数
        for cards in self.__set_cards_list[:-1]:
            all_set_cards.extend(cards[:card_count]) #根据传入牌数切片处理防止设牌数量大于发牌数量,导致总的牌数量有误

        self.__not_set_cards = self.__set_cards_list[:-1]
        # 设置摸牌
        set_mo_cards = [24]

        all_cards_map = {}
        for c in self.all_cards:
            all_cards_map[c] = all_cards_map.get(c, 0) + 1

        all_set_cards_map = {}
        for c in all_set_cards + set_mo_cards:
            all_set_cards_map[c] = all_set_cards_map.get(c, 0) + 1

        for card, count in all_cards_map.items():
            all_cards_map[card] = count - all_set_cards_map.get(card, 0)

        # 其余牌
        remain_cards = []
        for card, count in all_cards_map.items():
            remain_cards.extend([card] * count)

        random.shuffle(remain_cards)
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
        order_cards.extend(set_mo_cards)
        order_cards.extend(remain_cards)
        order_cards = [self.get_card_by_key(c) for c in order_cards]

        self.__cards = order_cards
        self.__set_cards_list.clear()  # 清除当前设牌

    def not_set_cards_ordered(self,seats,card_count):
        not_set_cards = []
        for i ,cards in enumerate(self.__not_set_cards):
            if i+1 in seats:
                not_set_cards.extend(cards[card_count:])

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

        new_remain = not_set_cards + temp  # 前 N 位 = no_set_cards，后续 = 剩余元素
        self.__cards[self.__cursor:] = new_remain  # 同步修改原列表
        self.__not_set_cards = []
        print("new_remain",self.__cards[self.__cursor:])



