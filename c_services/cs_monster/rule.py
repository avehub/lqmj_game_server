from .poker import Cards
from ..base.base_rule import BaseRule


class Rule(BaseRule):
    """ 规则类 """
    UNIVERSAL_CARD = Cards.UNIVERSAL_CARD  # 万能牌
    XIAO_YAO = 11  # 小妖
    MID_YAO = 12  # 中妖
    DA_YAO = 13  # 大妖
    SHA_SENG = 3  # 沙僧
    WU_KONG = 5  # 悟空
    BA_JIE = 8  # 八戒
    SHI_FU = 10  # 师傅

    __PRENTICE = (SHA_SENG, WU_KONG, BA_JIE)
    __MONSTER = (XIAO_YAO, MID_YAO, DA_YAO)

    @staticmethod
    def get_card_str(card_value):
        """
        JQK385S
        """
        str_map = {
            3: "3",
            5: "5",
            8: "8",
            10: "S",
            11: "J",
            12: "Q",
            13: "K",
        }
        return str_map.get(card_value) or ""

    @staticmethod
    def is_shi_fu(card: int):
        """ 判断师傅 """
        return card == Rule.SHI_FU

    @staticmethod
    def is_tu_di(card: int):
        """ 判断徒弟 """
        return card in Rule.__PRENTICE

    @staticmethod
    def is_yao_guai(card: int):
        """ 判断妖怪 """
        return card in Rule.__MONSTER

    @staticmethod
    def is_universal_card(card: int):
        """ 判断是否是万能牌 """
        return card == 20

    @staticmethod
    def yao_de_qi(last_cards, hand_cards):
        """判断是否要得起"""
        for c in hand_cards:
            if Rule.compare(c.val, last_cards):
                return True
        return False

    @staticmethod
    def legal_cards(turn_cards, hand_cards):
        """获取全部能出的牌"""
        result = []
        if len(hand_cards) != 0 and len(turn_cards) != 0:
            last_card_val = turn_cards[-1][-1]
            for c in hand_cards:
                if Rule.compare(c.val, last_card_val):
                    result.append(c)
        return result

    @staticmethod
    def compare(attack_card: int, last_card: int):
        """
        要得起
        比较attack_card是否要得起last_card
        params: attack_card玩家手牌其中一张
        params: last_card上一张牌
        return: bool
        """
        # 万能牌都要得起
        if Rule.is_universal_card(attack_card):
            return True
        # 1.上一张为师傅
        if last_card == Rule.SHI_FU:
            if Rule.is_yao_guai(attack_card):
                return True
            return False
        # 2.上一张为妖怪
        if Rule.is_yao_guai(last_card):
            if Rule.is_tu_di(attack_card):
                return True
            if Rule.is_yao_guai(attack_card) and attack_card > last_card:
                return True
            return False
        # 3.上一张为徒弟
        if Rule.is_tu_di(last_card):
            if Rule.is_shi_fu(attack_card):
                return True
            if Rule.is_tu_di(attack_card) and Rule.compare_tu_di(attack_card, last_card):
                return True
            return False
        return False

    @staticmethod
    def compare_tu_di(card1: int, card2: int):
        """
        比较徒弟
        在两张牌都是徒弟的情况下，比较大小
       （徒弟牌5>8>3）
       """
        if card1 == Rule.WU_KONG and card2 != Rule.WU_KONG:
            return True
        if card1 == Rule.BA_JIE and card2 == Rule.SHA_SENG:
            return True
        return False

    @staticmethod
    def cal_score(take_pai_len, di_fen, max_player):
        """ 计算分 """
        # 最后得分：（-捡牌分值*（人数-1）+（总的捡牌数-捡牌分值））* 底分
        # 实时计分：捡牌：（-捡牌分值*（人数-1））*底分 非捡牌：捡牌分值*底分
        mine = (-take_pai_len * (max_player - 1)) * di_fen
        other = take_pai_len * di_fen
        return mine, other

    @staticmethod
    def trans_universal_card_by_last_card(card: int):
        """
        当玩家打出万能牌时，需要根据上家打的牌转换为相应的阵营
        打妖怪分3个阵营：师傅|妖怪|徒弟
        场上为妖怪时，打出的万能牌视作3沙僧
        场上为徒弟时，打出的万能牌视作10唐僧
        场上为师父时，打出的万能牌视作J小妖
        """
        if Rule.is_yao_guai(card):
            return Rule.SHA_SENG
        if Rule.is_tu_di(card):
            return Rule.SHI_FU
        if card == Rule.SHI_FU:
            return Rule.XIAO_YAO
