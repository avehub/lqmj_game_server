from copy import deepcopy

from c_services.base.base_leisure_player import BaseLeisurePlayer
from c_services.cs_mahjong.const import ActionType
from c_services.cs_mahjong.poker import Poker
from common.utils import earth_position
from common.utils.utils import UtilsTool


class Player(BaseLeisurePlayer):
    def __init__(self, uid, is_robot):
        super().__init__(uid, is_robot)
        self.__que = 0
        self.__yuan_que = 0
        self.__is_lock = False
        self.__tian_ting =0
        self.__tian_hu = 0
        self.__mo_pai = 0
        self.__jiao_pai = 0
        self.__men_cards = []  #闷、捡牌都在里面
        self.__zi_mo_cards = [] #玩家闷的牌
        self.__has_shang_ga = False
        self.__can_tian_ting = 0
        self.__operates = [] #玩家能做的操作
        self.__shang_ga_score = 0
        self.__table_cards = []  # 玩家桌牌
        self.__all_chu_cards = []  # 所有出牌记录
        self.__chu_cards = []
        self.__shao_tong_xing_zheng = 0  # 烧通行证
        self.__tui_zhang_ke_kai = 0
        self.__ting_list = []
        self.__lock_cards = []
        self.__dian_pao_count = 0  # 点炮次数
        self.__jie_pao_count = 0  # 接炮次数
        self.__dian_gang_count = 0  # 点杠次数
        self.__ming_gang_count = 0  # 明杠次数
        self.__an_gang_count = 0  # 暗杠次数
        self.__zhuan_wan_gang_count = 0
        self.__zi_mo_count = 0  # 自摸次数
        self.__lian_zhuang = 0
        self.__jian_next_player_card = 0  # 一圈内是否捡过下家牌 轮到自己重置为0 1为捡过
        self.__zha_hu = 0
        self.__fang_pao = 0
        self.__hu_type = 0
        self.__ji_pai = []
        self.__chong_feng_ji = 0
        self.__chong_feng_wgj = 0
        self.__ze_ren_ji = 0
        self.__ze_ren_wgj = 0
        self.__han_bao_dou_an_gang_count = 0
        self.__han_bao_dou_zhuan_wan_gang_count = 0
        self.__han_dou_cards = set()
        self.__is_ready = False
        self.__hu_info = {}  # 胡开信息
        self.__shao_tong_xing_zheng = 0  # 烧通行证

        self.__x = earth_position.X_NA  # 玩家经度
        self.__y = earth_position.Y_NA  # 玩家纬度

    @property
    def has_shang_ga(self):
        return self.__has_shang_ga

    @has_shang_ga.setter
    def has_shang_ga(self, shang_ga):
        if not shang_ga:
            return
        self.__has_shang_ga = shang_ga

    @property
    def shang_ga_score(self):
        return self.__shang_ga_score

    @shang_ga_score.setter
    def shang_ga_score(self, shang_ga_score):
        self.__shang_ga_score = shang_ga_score

    @property
    def que(self):
        return self.__que

    @que.setter
    def que(self,que:int):
        self.__que = que

    @property
    def yuan_que(self):
        return self.__yuan_que

    @property
    def is_lock(self):
        return self.__is_lock

    @is_lock.setter
    def is_lock(self,is_lock:bool):
        self.__is_lock = is_lock

    @property
    def tian_ting(self):
        return self.__tian_ting

    @tian_ting.setter
    def tian_ting(self,tian_ting:int):
        self.__tian_ting = tian_ting

    @property
    def tian_hu(self):
        return self.__tian_hu

    @tian_hu.setter
    def tian_hu(self, tian_hu):
        self.__tian_hu = tian_hu

    @property
    def all_chu_cards(self):
        return self.__all_chu_cards

    @all_chu_cards.setter
    def all_chu_cards(self, cards):
        self.__all_chu_cards = cards

    @property
    def chu_cards(self):
        return self.__chu_cards

    @chu_cards.setter
    def chu_cards(self, cards):
        self.__chu_cards = cards

    @property
    def can_tian_ting(self):
        return self.__can_tian_ting

    def chu_pai_len(self):
        return len(self.__chu_cards)

    def pop_chu_pai(self):
        return self.__chu_cards.pop()

    @can_tian_ting.setter
    def can_tian_ting(self, can_tian_ting):
        self.__can_tian_ting = can_tian_ting

    @property
    def operates(self):
        return deepcopy(self.__operates)

    @operates.setter
    def operates(self, opts):
        self.__operates.clear()
        self.__operates.extend(opts)

    def can_operates(self):
        return len(self.__operates) > 0

    def remove_operates(self, opt):
        self.__operates.remove(opt)

    def add_operates(self, opt):
        self.__operates.append(opt)


    @property
    def mo_pai(self):
        return self.__mo_pai

    @mo_pai.setter
    def mo_pai(self,mo_pai:int):
        self.__mo_pai = mo_pai

    @property
    def jiao_pai(self):
        return self.__jiao_pai

    @jiao_pai.setter
    def jiao_pai(self,jiao_pai:int):
        self.__jiao_pai = jiao_pai

    @property
    def men_cards(self):
        return self.__men_cards

    @property
    def table_cards(self):
        return deepcopy(self.__table_cards)

    def table_cards_len(self):
        return len(self.__table_cards)

    def add_table_cards(self, card_type, cards, from_seat_id):
        cards = deepcopy(cards)
        cards.insert(0, card_type)
        cards.append(from_seat_id)
        self.__table_cards.append(cards)

    def add_men_cards(self,data, is_zha=False):
        self.__men_cards.append(data)
        card = data["card"]
        self.__zi_mo_cards.append(card)
        self.rm_cards([card])
        if not is_zha:
            self.__zi_mo_count += 1

    def rm_cards(self, cards,chu_pai=False):
        super().rm_cards(cards)
        chu_pai and self.__chu_cards.extend(cards)
        self.__all_chu_cards.extend(cards)


    @property
    def zi_mo_cards(self):
        return deepcopy(self.__zi_mo_cards)

    def gang_in_operates(self):
        if ActionType.ACTION_TYPE_AN_GANG in self.__operates:
            return ActionType.ACTION_TYPE_AN_GANG
        elif ActionType.ACTION_TYPE_MING_GANG in self.__operates:
            return ActionType.ACTION_TYPE_MING_GANG
        elif ActionType.ACTION_TYPE_ZHUAN_WAN_GANG in self.__operates:
            return ActionType.ACTION_TYPE_ZHUAN_WAN_GANG
        else:
            return None

    def is_action_in_operates(self,action):
        return action in self.__operates

    def can_hu_men_jian(self):
        """是否包含至少一个(闷，捡，胡)"""
        operates_map = set(self.__operates)
        target_actions = {
            ActionType.ACTION_TYPE_MEN,
            ActionType.ACTION_TYPE_JIAN,
            ActionType.ACTION_TYPE_HU
        }
        return not target_actions.isdisjoint(operates_map)

    def set_shao_txz(self, flag: int = 1):
        """ 设置烧通行证 """
        print(self.__uid, "玩家被烧通行证")
        self.__shao_tong_xing_zheng = flag

    @property
    def shao_tong_xing_zheng(self):
        return self.__shao_tong_xing_zheng


    def on_round_over_clear(self):
        self.is_lock = False
        self.__has_shang_ga = False
        self.__shang_ga_score = 0
        self.__operates.clear()
        self.__ting_list = []
        self.__fang_pao = 0
        self.__hu_type = 0
        self.__ji_pai = []
        self.__que = 0
        self.__yuan_que = 0
        self.__men_cards = []
        self.__chong_feng_ji = 0
        self.__chong_feng_wgj = 0
        self.__ze_ren_ji = 0
        self.__ze_ren_wgj = 0
        self.__jiao_pai = 0
        self.__tian_ting = 0
        self.__can_tian_ting = 0
        self.__han_bao_dou_an_gang_count = 0
        self.__han_bao_dou_zhuan_wan_gang_count = 0
        self.__lock_cards = []
        self.__zha_hu = 0
        self.__tian_hu = 0
        self.__hu_info = {}
        self.__han_dou_cards = set()
        self.__shao_tong_xing_zheng = 0
        self.__tui_zhang_ke_kai = 0
        self.__jian_next_player_card = 0
        self.__is_ready = False

        self.__chu_cards.clear()
        self.__all_chu_cards.clear()
        self.__table_cards.clear()
        self.__zi_mo_cards.clear()

    def clear_data_round_over(self):
        super().clear_data_round_over()
        self.on_round_over_clear()


    def mo_pai_can_operates(self):
        """两个集合有交集返回True,即至少有其中一个操作"""
        operates_map = set(self.__operates)
        target_actions = {
            ActionType.ACTION_TYPE_PENG,
            ActionType.ACTION_TYPE_MING_GANG,
            ActionType.ACTION_TYPE_AN_GANG,
            ActionType.ACTION_TYPE_ZHUAN_WAN_GANG,
            ActionType.ACTION_TYPE_MEN,
            ActionType.ACTION_TYPE_JIAN,
            ActionType.ACTION_TYPE_HU
        }
        return not target_actions.isdisjoint(operates_map)

    def exchange_cards_seat(self, index_list, cards):
        for i, idx in enumerate(index_list, 1):
            self.ex_cards(cards[-i],idx)

    def can_an_gang(self, rule, card=0):
        if self.__que > 0:
            if (card or 0) // 10 == self.__que:
                return False, 0
        return rule.can_an_gang(self.cards, card)

    @property
    def tui_zhang_ke_kai(self):
        return self.__tui_zhang_ke_kai

    @tui_zhang_ke_kai.setter
    def tui_zhang_ke_kai(self, flag):
        self.__tui_zhang_ke_kai = flag

    def can_zhuan_wan_gang(self, rule, card=0):
        if self.__que > 0:
            if (card or 0) // 10 == self.__que:
                return False, 0
        return rule.can_zhuan_wan_gang(self.cards, self.__table_cards, card)

    def zhuan_wan_gang(self, card):

        for table_card in self.__table_cards:
            card_type, first_card, *_ = table_card
            if card_type == ActionType.ACTION_TYPE_PENG and first_card == card:
                self.__table_cards.remove(table_card)
                self.__add_table_cards(ActionType.ACTION_TYPE_ZHUAN_WAN_GANG, [card] * 4, self.seat_id)
                if card in self.cards:
                    self.rm_cards([card])
                self.__zhuan_wan_gang_count += 1
                return True

        return False

    def can_ming_gang(self, rule, card):
        if self.__que > 0:
            if (card or 0) // 10 == self.__que:
                return False, 0
        return rule.can_ming_gang(self.cards,card)

    def can_peng(self, card, rule):
        """ 1. 手牌有两张相同 2. 碰牌之后还要有牌可以打出 """
        if self.__tian_ting:
            return False
        if self.is_lock:
            return False
        if self.__que > 0:
            if card // 10 == self.__que:
                return False
        return rule.can_peng(self.cards, card)


    @property
    def ting_list(self):
        return self.__ting_list

    @ting_list.setter
    def ting_list(self, ting_list):
        self.__ting_list = ting_list

    @property
    def lock_cards(self):
        return self.__lock_cards

    @lock_cards.setter
    def lock_cards(self, lock_cards):
        self.__lock_cards = lock_cards

    def get_out_not_lock_card(self):
        lock_set = set(self.__lock_cards)
        print("lock_set",lock_set)
        result = [card for card in self.cards if card not in lock_set]
        if not result:
            return [self.__mo_pai]
        return [card for card in self.cards if card not in lock_set]

    def set_lock_cards(self, lock_cards):
        """ 锁牌，锁住除lock_cards的牌 """
        self.__lock_cards = []
        temp_cards = deepcopy(self.cards)
        for card in lock_cards:
            temp_cards.remove(card)
        self.__lock_cards = temp_cards

    def set_position(self, x, y):
        if x is None or y is None:
            return
        self.__x = UtilsTool.check_float(x)
        self.__y = UtilsTool.check_float(y)

    @property
    def position(self):
        return self.__x, self.__y

    def card_is_lock(self):
        return self.tian_ting or len(self.men_cards) > 0

    def chu_pai(self,card,chu_pai=True):
        self.rm_cards([card], chu_pai)

    def jie_pao_count(self):
        self.__jie_pao_count += 1

    def dian_pao_count(self):
        self.__dian_pao_count += 1

    def add_dian_gang_count(self):
        self.__dian_gang_count += 1

    def zi_mo_count(self):
        self.__zi_mo_count += 1

    @property
    def lian_zhuang(self):
        return self.__lian_zhuang

    @lian_zhuang.setter
    def lian_zhuang(self, lian_zhuang):
        self.__lian_zhuang = lian_zhuang

    def __add_table_cards(self, card_type, cards, from_seat_id):
        cards = deepcopy(cards)
        cards.insert(0, card_type)
        cards.append(from_seat_id)
        self.__table_cards.append(cards)

    def ming_gang(self, card, from_seat_id=0):
        if 3 != self.cards.count(card):
            return False
        cards = [card, card, card, card]
        self.rm_cards([card] * 3)
        self.__add_table_cards(ActionType.ACTION_TYPE_MING_GANG, cards, from_seat_id)
        self.__ming_gang_count += 1
        return True

    def an_gang(self, card):  # 暗杠
        if self.cards.count(card) < 4:
            return False
        cards = [card, card, card, card]
        self.rm_cards([card] * 4)
        self.__add_table_cards(ActionType.ACTION_TYPE_AN_GANG, cards, self.seat_id)
        self.__an_gang_count += 1
        return True

    def check_zhuan_wan_gang(self, card) -> bool:
        """ 仅检测当前牌能否转弯杠 """
        return any(
            card_type == ActionType.ACTION_TYPE_PENG and first_card == card
            for card_type, first_card,*_ in self.__table_cards
        )

    def check_an_gang(self, card) -> bool:
        """ 仅检测当前牌能否暗杠 """
        if self.cards.count(card) < 4:
            return False
        return True

    def add_jian_cards(self, data, is_zha=False):
        self.__men_cards.append(data)
        if not is_zha:
            self.__jie_pao_count += 1

    @property
    def jian_next_player_card(self):
        return self.__jian_next_player_card

    @jian_next_player_card.setter
    def jian_next_player_card(self,value):
        self.__jian_next_player_card = value

    @property
    def is_zha_hu(self):
        return self.__zha_hu

    @is_zha_hu.setter
    def is_zha_hu(self, zha_hu):
        self.__zha_hu = zha_hu

    @property
    def fang_pao(self):
        return self.__fang_pao

    @fang_pao.setter
    def fang_pao(self, fang_pao):
        self.__fang_pao = fang_pao

    @property
    def hu_type(self):
        return self.__hu_type

    @hu_type.setter
    def hu_type(self, hu_type):
        self.__hu_type = hu_type

    @property
    def ji_pai(self):
        return self.__ji_pai

    @property
    def chong_feng_ji(self):
        return self.__chong_feng_ji

    @chong_feng_ji.setter
    def chong_feng_ji(self, chong_feng_ji):
        self.__chong_feng_ji = chong_feng_ji

    @property
    def chong_feng_wgj(self):
        return self.__chong_feng_wgj

    @chong_feng_wgj.setter
    def chong_feng_wgj(self, chong_feng_ji):
        self.__chong_feng_wgj = chong_feng_ji

    @property
    def ze_ren_ji(self):
        return self.__ze_ren_ji

    @ze_ren_ji.setter
    def ze_ren_ji(self, ze_ren_ji):
        self.__ze_ren_ji = ze_ren_ji

    @property
    def ze_ren_wgj(self):
        return self.__ze_ren_wgj

    @ze_ren_wgj.setter
    def ze_ren_wgj(self, ze_ren_ji):
        self.__ze_ren_wgj = ze_ren_ji


    def on_game_start_clear_data(self):
        """ 房间开始前的清理 """
        self.__clear_game_data()

    def __clear_game_data(self):
        self.__ming_gang_count = 0
        self.__dian_gang_count = 0
        self.__an_gang_count = 0
        self.__zhuan_wan_gang_count = 0
        self.__lian_zhuang = 0
        self.__zi_mo_count = 0
        self.__tian_ting = 0
        self.__can_tian_ting = 0
        self.__shang_ga_score = 0


    def calc_all_ji_pai(self, default_ji, fan_ji_list=None, with_out=False, exclude_last_card=None):
        """
        计算玩家自己所有鸡牌
        fan_ji_list: 桌子中所有鸡牌的集合(默认鸡 + 翻鸡 + 乌骨鸡，后两种可选)
        default_ji: 默认鸡
        with_out: 满堂鸡包含打出的鸡
        exclude_last_card: 打出的牌不算最后一张（点炮那张）
        """
        fan_ji_list = fan_ji_list or set()

        all_bird = default_ji | fan_ji_list  # 并集

        # 手牌
        for card in self.cards:
            if card in all_bird:
                self.__ji_pai.append(card)

        # 闷捡的牌
        for men_data in self.__men_cards:
            card = men_data["card"]
            if card in all_bird:
                self.__ji_pai.append(card)
        # 碰杠的牌
        for combo in self.__table_cards:
            for card in combo[1:-1]:
                if card in all_bird:
                    self.__ji_pai.append(card)
        # 默认鸡
        for card in self.__chu_cards[:exclude_last_card]:
            if card in default_ji:
                self.__ji_pai.append(card)

        # 出过的牌（满堂鸡）
        if with_out:
            for card in self.__chu_cards:
                if card in default_ji:  # 打出的默认鸡已经算过一遍
                    continue
                if card in fan_ji_list:
                    self.__ji_pai.append(card)

    def calc_stand_ji(self, default_ji) -> list:
        """
        计算站鸡，站鸡仅限默认鸡，冲锋鸡是打出去的鸡没有站鸡
        在手牌中的、自摸的、捡胡的、暗杠的幺鸡和乌骨鸡分数翻倍（可与金鸡相乘）
        """
        # 手牌
        stand_ji = []
        for card in self.cards:
            if card in default_ji:
                stand_ji.append(card)

        # 闷捡的牌
        for men_data in self.__men_cards:
            card = men_data["card"]
            if card in default_ji:
                stand_ji.append(card)

        # 暗杠的
        for combo in self.__table_cards:
            if combo[0] != ActionType.ACTION_TYPE_AN_GANG:
                continue
            for card in combo[1:-1]:
                if card in default_ji:
                    stand_ji.append(card)
        return stand_ji

    def calc_peng_gang_ji(self, default_ji):
        """ 计算碰杠的鸡(除暗杠) """
        peng_gang_ji = []
        for combo in self.__table_cards:
            if combo[0] == ActionType.ACTION_TYPE_AN_GANG:
                continue
            for card in combo[1:-1]:
                if card in default_ji:
                    peng_gang_ji.append(card)
        return peng_gang_ji

    def get_bao_ji(self, default_ji):
        """
        不叫牌的玩家碰杠的默认鸡和打出的默认鸡要按相
        同分数倒给进行包鸡。
        """
        # 打出的默认鸡
        for card in self.__chu_cards:
            if card in default_ji:
                self.__ji_pai.append(card)

        # 碰杠的默认鸡
        for combo in self.__table_cards:
            # 暗杠属于手上的鸡
            if combo[0] == ActionType.ACTION_TYPE_AN_GANG:
                continue
            for card in combo[1:-1]:
                if card in default_ji:
                    self.__ji_pai.append(card)

    @property
    def is_ready(self):
        return self.__is_ready

    @is_ready.setter
    def is_ready(self,is_ready:bool):
        self.__is_ready = is_ready

    def player_info(self,contain_cards = True):
        public_men_cards = []
        for men_cards in self.__men_cards:
            data = deepcopy(men_cards)
            if data.get("is_zi_mo"):
                data["card"] = 0
            public_men_cards.append(data)

        p_info = super().player_info(contain_cards)
        p_info["is_ready"] = self.__is_ready
        p_info["shang_ga"] = self.__has_shang_ga
        p_info["shang_ga_score"] = self.__shang_ga_score
        p_info["is_bao_ting"] = self.__tian_ting == 1
        p_info["mo_pai"] = self.__mo_pai
        p_info["first_ji"] = self.__chong_feng_ji
        p_info["first_wu_gu_ji"] = self.__chong_feng_wgj
        p_info["ze_ren_ji"] = self.__ze_ren_ji
        p_info["ze_ren_wu_gu_ji"] = self.__ze_ren_wgj
        p_info["is_lock_cards"] = self.__tian_ting or bool(public_men_cards)
        p_info["table_cards"] = self.get_table_cards()
        p_info["out_cards"] = deepcopy(self.__chu_cards)
        p_info["lock_cards"] = self.__lock_cards
        p_info["operates"] = self.operates[:]
        p_info["men_cards"] = self.__men_cards
        return p_info

    def round_over_data(self):
        return {
            "seat_id": self.seat_id,
            "hand_cards": self.cards,
            "table_cards": self.get_table_cards(),
            "round_score": self.round_score,
            "total_score": self.total_score,
            "jiao_pai": self.__jiao_pai,
            "fang_pao": self.__fang_pao,
            "hu_type": self.__hu_type,
            "ji_pai": self.__ji_pai,
            "men_cards": self.__men_cards,
            "is_zha_hu": self.__zha_hu,
        }

    @property
    def game_over_data(self):
        return {
            "seat_id": self.seat_id,
            "uid": self.__uid,
            "total_score": self.total_score,  # 总分
            "dian_pao_count": self.__dian_pao_count,  # 点炮次数
            "jie_pao_count": self.__jie_pao_count,  # 接炮次数
            "zi_mo_count": self.__zi_mo_count,  # 自摸次数
            "ming_gang_count": self.__ming_gang_count,  # 明杠次数
            "dian_gang_count": self.__dian_gang_count,  # 点杠次数
            "an_gang_count": self.__an_gang_count,  # 暗杠次数
            "zhuan_wan_gang_count": self.__zhuan_wan_gang_count,  # 转弯杠次数
        }

    def get_table_cards(self):
        data = self.get_public_pai()
        result = []
        for table_cards in data:
            act_type = table_cards[0]

            if act_type == ActionType.ACTION_TYPE_CHI:
                result.append({
                    "act_type": act_type,
                    "cards": table_cards[1:-1],
                    "from_seat_id": table_cards[-1]
                })
            else:
                item = {
                    "act_type": act_type,
                    "card": table_cards[1],
                    "from_seat_id": table_cards[-1]
                }
                result.append(item)
        return result

    def get_public_pai(self):
        return [deepcopy(item) for item in self.__table_cards]



    def on_round_over(self, score):
        """ 一局结束结算 """
        self.round_score = score

    def set_hu_info(self, info: dict):
        self.__hu_info = info

    def check_has_permit(self):
        """ 检测是否有通行证(杠牌) """
        for combo in self.__table_cards:
            if combo[0] in (ActionType.ACTION_TYPE_AN_GANG, ActionType.ACTION_TYPE_MING_GANG,
                            ActionType.ACTION_TYPE_ZHUAN_WAN_GANG):
                return True
        return False

    def que_count(self):
        """
        检查玩家是否完成缺
        return: 0 表示已经完成，> 0表示还有缺牌
        """
        suit_count = Poker.cal_card_suit_count(self.cards)
        return suit_count.get(self.__que, 0)

    def set_is_yuan_que(self):
        """ 判断起手是不是原缺(手牌只有一种或两种花色且不是缺牌花色) """
        if self.__que == 0:
            return False
        cards_to_count = Poker.cal_card_suit_count(self.cards)
        if len(cards_to_count) <= 2:
            # 手中没有缺的牌才算源缺
            if not cards_to_count.get(self.__que):
                self.__yuan_que = self.__que
                return True
        return False

    @property
    def han_bao_dou_an_gang_count(self):
        return self.__han_bao_dou_an_gang_count

    def add_han_bao_dou_an_gang_count(self, card):
        self.__han_bao_dou_an_gang_count += 1
        self.__han_dou_cards.add(card)

    @property
    def han_bao_dou_zhuan_wan_gang_count(self):
        return self.__han_bao_dou_zhuan_wan_gang_count

    def add_han_bao_dou_zhuan_wan_gang_count(self, card):
        self.__han_bao_dou_zhuan_wan_gang_count += 1
        self.__han_dou_cards.add(card)

    @property
    def han_dou_cards(self):
        return self.__han_dou_cards

    def player_peng(self, card, from_seat_id):
        if self.cards.count(card) < 2:
            return False
        cards = [card, card, card]
        self.rm_cards([card] * 2)
        self.__add_table_cards(ActionType.ACTION_TYPE_PENG, cards, from_seat_id)
        return True


    def on_game_over(self):
        self.on_round_over_clear()
        self.__clear_game_data()