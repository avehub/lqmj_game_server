from copy import deepcopy

from common.proto.py_pb2.ws_leisure import S2CFirstJiMahjong
from common.public.enum_const import StaCode
from .player import Player
from .const import (FlowStatus, ActionType, CheckType, JiType, CardsType, HuType, ExtraHuPai)
from .room_bijie import RoomBJ
from .rule import Rule
from ..const.cs_enum_const import CmdRoom
from ..cs_robot_mahjong.const import OverType


class RoomZY(RoomBJ):
    def __init__(self, tid, service, room_conf):
        room_conf.get("rule_details")["di_long_qi"] = 1
        super().__init__(tid, service, room_conf)
        self.__after_peng_can_bao_ting = self.rule_detail.get("after_peng_can_bao_ting", 0)
        self.__xi_pai_score = self.rule_detail.get("xi_pai_score", 25)
        self.__yi_wan_ji = self.rule_detail.get("yi_wan_ji", 0)
        self.__fan_ji_score = {}
        self.__round_first_yi_tong = 0
        self.__round_first_yi_wan = 0
        self.__cf_yi_tong_seat_id = 0  # 冲锋一筒玩家
        self.__cf_yi_wan_seat_id = 0  # 冲锋一万玩家
        self.__ze_ren_yi_tong_seat_id = 0  # 责任一筒玩家
        self.__ze_ren_yi_tong_win_seat_id = 0

        self.__ze_ren_yi_wan_seat_id = 0  # 责任一万玩家
        self.__ze_ren_yi_wan_win_seat_id = 0
        self.__ying_hu_score = self.extra_score_map.get(ExtraHuPai.YING_HU)

        if self.__yi_wan_ji:
            self.add_default_ji(CardsType.YI_WAN)


    def clear_room_round_start(self):
        super().clear_room_round_start()
        self.__round_first_yi_tong = 0
        self.__round_first_yi_wan = 0
        self.__cf_yi_tong_seat_id = 0  # 冲锋一筒玩家
        self.__cf_yi_wan_seat_id = 0  # 冲锋一万玩家
        self.__ze_ren_yi_tong_seat_id = 0  # 责任一筒玩家
        self.__ze_ren_yi_tong_win_seat_id = 0

        self.__ze_ren_yi_wan_seat_id = 0  # 责任一万玩家
        self.__ze_ren_yi_wan_win_seat_id = 0
        self.__fan_ji_score = {}

    def kai_pai_check_out(self, accounts: dict):
        """
        开牌结算
        统一数据结构
        """
        self.check_out_hu_lai_zi(accounts)

        self.check_out_ying_hu(accounts)

        self.check_chong_xi(accounts)

        accounts, zhuo_ji = super().kai_pai_check_out(accounts)

        self.check_out_lian_zhuang(accounts)

        return accounts, zhuo_ji

    def get_per_score(self, ji, score, count, default_ji, liu_ju):

        bei_lv = 1
        if ji in default_ji and ji in self.fan_jin_ji_cards:  # 金鸡必须是9转1
            bei_lv = 3

        if ji == CardsType.WU_GU_JI and ji not in self.default_ji:
            per_score = count
        else:
            per_score = self.ji_pai_score.get(ji, 1) * count * bei_lv
        return per_score

    def get_hu_type(self, p: Player, dian_pao=False, only_calc_hu=False, lou=False):
        extra_fan = []
        is_zi_mo = self.curr_seat_id == p.seat_id
        table_cards = deepcopy(p.table_cards)
        if only_calc_hu:
            hu_type = Rule.only_can_hu(table_cards, p.cards, self.curr_card, self.lai_zi)
            hu_path = []
        else:
            flag = self.is_must_qing_yi_se(p, table_cards, is_zi_mo)
            hu_type, hu_path = Rule.get_hu_type_by_score(
                table_cards, p.cards, self.curr_card, self.__fan_ji_score, is_zi_mo, lai_zi=self.lai_zi, must_qys=flag,
                pai_xing_score_map=self.pai_xing_score_map, extra_score_map=self.extra_score_map)
            p.jiao_pai = hu_type
            p.hu_path = hu_path or []
        print("hu_type:", hu_type, "p.hu_path", p.hu_path)
        if not hu_type:
            return {}, False, []

        # 地胡：第一轮接庄炮/自摸
        # 杀报(天听玩家未胡之前都可被杀报，只算一次，自己胡过或者被别人杀报过 后续则没有杀报)
        is_sha_bao = False
        bei_sha_bao_seats = []  # 被杀报者需要记录，因为如果是自摸，可能有一个可能有多个
        re_pao_score = 0  # 记录热炮分(杠上炮分后续不好计算，此处算好后面直接用)
        qiang_gang_score = 0  # 记录抢杠分(抢杠分后续不好计算，此处算好后面直接用)
        gang_card = []  # 记录抢杠|杠上炮时的杠，如果是默认鸡后续算分时需要+鸡的分

        if is_zi_mo:
            if len(self.gang_hou_mo_pai) > 0:
                extra_fan.append(ExtraHuPai.GANG_SHANG_HUA)  # 杠上花

            if p.seat_id == self.dealer_id and not p.all_chu_cards and not p.men_cards:
                if p.tian_ting != 1:
                    extra_fan.append(ExtraHuPai.TIAN_HU)  # 天胡(选择报听后则不能算天胡)

            for other_p in self.seats:
                if p.seat_id == other_p.seat_id:
                    continue
                if other_p.tian_ting > 0:
                    is_sha_bao = True  # 杀报
                    bei_sha_bao_seats.append(other_p.seat_id)
        else:
            if self.flow_status_is_equal(FlowStatus.T_IN_ZHUAN_WAN_GANG_PAI_CALL):
                gang = ActionType.ACTION_TYPE_ZHUAN_WAN_GANG
                gang_card = [[gang, self.curr_card]]

                qiang_gang_score += self.cal_score_by_gang_shang_pao(gang)
                extra_fan.append(ExtraHuPai.QIANG_GANG_HU)  # 抢杠胡(烧鸡烧杠)
                if not only_calc_hu:
                    self.shao_ji_gang_seats.add(self.curr_seat_id)

            if len(self.gang_hou_chu_pai) > 0:
                gang_card = self.gang_hou_chu_pai[::]
                for gang in self.gang_hou_chu_pai:
                    re_pao_score += self.cal_score_by_gang_shang_pao(gang[0])

                extra_fan.append(ExtraHuPai.GANG_SHANG_PAO)  # 杠上炮(烧鸡烧杠)
                if not only_calc_hu:
                    self.shao_ji_gang_seats.add(self.curr_seat_id)

            curr_p = self.curr_player()
            if curr_p.tian_ting > 0:
                bei_sha_bao_seats.append(curr_p.seat_id)
                is_sha_bao = True  # 杀报

        if p.tian_ting > 0:
            # 天胡地胡不与报听叠加
            if ExtraHuPai.TIAN_HU not in extra_fan and ExtraHuPai.DI_HU not in extra_fan:
                if p.tian_ting == 1:
                    extra_fan.append(ExtraHuPai.TIAN_TING)
                else:
                    extra_fan.append(ExtraHuPai.COMMON_TIAN_TING)

        if is_sha_bao:
            extra_fan.append(ExtraHuPai.SHA_BAO)

        qing_upgrade_map = {
            HuType.QI_DUI: HuType.QING_QI_DUI,
            HuType.LONG_QI_DUI: HuType.QING_LONG_BEI,
            HuType.DA_DUI_ZI: HuType.QING_DA_DUI,
            HuType.DI_LONG_QI: HuType.QING_DI_LONG,
            HuType.DOUBLE_DI_LONG_QI: HuType.QING_DOUBLE_DI_LONG_QI,
            HuType.THREE_DI_LONG_QI: HuType.QING_THREE_DI_LONG_QI,
            HuType.JIN_GOU_DIAO: HuType.QING_JIN_GOU,
            HuType.DOUBLE_LONG_QI: HuType.QING_DOUBLE_LONG_QI,
            HuType.THREE_LONG_QI: HuType.QING_THREE_LONG_QI,
        }
        is_qing_yi_se = Rule.has_hu_is_qing_yi_se(deepcopy(p.table_cards), deepcopy(p.cards), self.curr_card, self.lai_zi)

        if is_qing_yi_se:
            hu_type = qing_upgrade_map.get(hu_type, HuType.QING_YI_SE)

        result = {
            "card": p.mo_pai,
            "seat_id": p.seat_id,
            "is_zi_mo": is_zi_mo,
            "hu_type": hu_type,
            "extra_hu_type": extra_fan,
        }

        if is_sha_bao:
            result["bei_sha_bao_seats"] = bei_sha_bao_seats
        if not is_zi_mo:
            result["fang_pao_seat_id"] = self.curr_seat_id
            result["re_pao_score"] = re_pao_score
            result["qiang_gang_score"] = qiang_gang_score
            result["card"] = self.curr_card
            result["gang_card"] = gang_card
        return result, True, hu_path

    def is_must_qing_yi_se(self, p: Player, table_cards, is_zi_mo) -> bool:
        """ 是否是清一色 """
        hu_type = Rule.only_can_hu(table_cards, p.cards, self.curr_card, self.lai_zi)
        if hu_type != HuType.PING_HU:
            return False
        hu_info = {"hu_type": hu_type, "is_zi_mo": is_zi_mo}
        can_hu, hu_type, _ = self.check_can_hu(p, True, hu_info)
        if not can_hu:
            is_qing_yi_se = Rule.has_hu_is_qing_yi_se(
                deepcopy(p.table_cards), deepcopy(p.cards), self.curr_card, self.lai_zi)
            if is_qing_yi_se:
                return True
        return False

    def deal_fan_ji(self):
        self.ji_cards, self.zhuo_ji_card = self.calc_fan_ji_cards()
        # 该map主要用于胡牌类型的选取
        ji_score = {
            CardsType.YAO_JI: self.ji_pai_score.get(CardsType.YAO_JI),
            CardsType.WU_GU_JI: self.ji_pai_score.get(CardsType.WU_GU_JI),
        }
        if self.__yi_wan_ji:
            ji_score[CardsType.YI_WAN] = self.ji_pai_score.get(CardsType.YI_WAN)

        for ji in self.ji_cards:
            if ji == CardsType.YAO_JI:
                ji_score[CardsType.YAO_JI] = self.ji_pai_score.get(JiType.JIN_JI)
            elif ji == CardsType.WU_GU_JI:
                ji_score[CardsType.WU_GU_JI] = self.ji_pai_score.get(JiType.WU_GU_JIN_JI)
            elif ji == CardsType.YI_TONG:
                ji_score[CardsType.YI_TONG] = self.ji_pai_score.get(CardsType.YI_TONG)
            elif self.__yi_wan_ji and ji == CardsType.YI_WAN:
                ji_score[CardsType.YI_WAN] = self.ji_pai_score.get(JiType.JIN_YI_WAN)
            else:
                ji_score[ji] = 1
        self.__fan_ji_score = ji_score

    def get_operates_after_peng(self, p: Player):
        can_an_gang, gang_card_list = p.can_an_gang(Rule)
        can_zwg, gang_card = p.can_zhuan_wan_gang(Rule)
        can_ting = False
        if self.__after_peng_can_bao_ting:
            if not p.chu_cards and p.mo_pai == 0:
                can_ting = self.check_tian_ting_after_peng(p)
                self.log_info(p.uid, "玩家碰后是否能听：", can_ting, p.cards)
        operates = []
        if can_zwg:
            operates.append(ActionType.ACTION_TYPE_ZHUAN_WAN_GANG)
        if can_an_gang:
            operates.append(ActionType.ACTION_TYPE_AN_GANG)
        if can_ting:
            operates.append(ActionType.ACTION_TYPE_TIAN_TING)
        return operates, gang_card_list

    def check_tian_ting_after_peng(self, p: Player):
        """是否符合碰后听牌"""
        if len(p.table_cards) != 1 or p.table_cards[0][0] != ActionType.ACTION_TYPE_PENG:  # 最多有一个杠或者碰
            return False
        if len(p.cards) != 11:
            return False
        if p.chu_pai_len() == 0 and p.can_tian_ting >= 0:
            if Rule.r_can_tian_ting(p.table_cards, p.cards, p.que, is_zy=True, lai_zi=self.lai_zi):
                return True
        return False

    async def on_player_pass(self, p: Player):
        code, msg = await super().on_player_pass(p)
        if code == StaCode.PASS:
            if p.is_action_in_operates(ActionType.ACTION_TYPE_HU) and self.curr_seat_id != p.seat_id:
                p.dian_pao_no_hu = 1
        return code, msg

    async def hu_da_notify(self, hu_list):
        self.deal_fan_ji()
        await super().hu_da_notify(hu_list)

    async def deal_first_ji(self, curr_p: Player):
        await super().deal_first_ji(curr_p)
        if self.curr_card == self.lai_zi and self.__round_first_yi_tong == 0:
            self.__round_first_yi_tong = 1
            self.__cf_yi_tong_seat_id = self.curr_seat_id
            curr_p.chong_feng_yi_tong = 1
            await self.send_first_ji_info("癞子冲锋鸡玩家成功")

        elif self.__yi_wan_ji and self.curr_card == CardsType.YI_WAN and self.__round_first_yi_wan == 0:
            self.__round_first_yi_wan = 1
            self.__cf_yi_wan_seat_id = self.curr_seat_id
            curr_p.chong_feng_yi_wan = 1
            await self.send_first_ji_info("一万冲锋鸡玩家成功")

    def check_chong_feng_ji(self, accounts, liu_ju=False, is_bao=False):
        super().check_chong_feng_ji(accounts, liu_ju, is_bao)
        if self.__cf_yi_tong_seat_id != 0:
            ji_card = CardsType.YI_TONG
            key = JiType.CF_YI_TONG
            if ji_card in self.fan_jin_ji_cards:  # 翻到为金鸡
                key = JiType.JIN_CF_YI_TONG
            score = self.ji_pai_score.get(key, 0)
            self.concreteness_check_chong_feng_ji(accounts, score, ji_card, self.__cf_yi_tong_seat_id, liu_ju, is_bao)

        if self.__cf_yi_wan_seat_id != 0:
            ji_card = CardsType.YI_WAN
            key = JiType.CF_YI_WAN
            if ji_card in self.fan_jin_ji_cards:  # 翻到为金鸡
                key = JiType.JIN_CF_YI_WAN
            score = self.ji_pai_score.get(key, 0)
            self.concreteness_check_chong_feng_ji(accounts, score, ji_card, self.__cf_yi_wan_seat_id, liu_ju, is_bao)

    def check_ji(self, accounts, is_bao=True, liu_ju=False):
        if liu_ju and self.play_type > 2:
            return
        type_ = CheckType.CHECK_JI
        # 外循环为未叫牌/炸胡玩家
        fan_bird_list = self.ji_cards.copy()
        if self.lai_zi in fan_bird_list:
            fan_bird_list.remove(self.lai_zi)
        for p in self.seats:
            if p.jiao_pai <= 0 or p.is_zha_hu:
                continue
            if p.seat_id in self.shao_ji_gang_seats:
                continue
            p.calc_all_ji_pai(self.default_ji, fan_bird_list, self.man_tang_ji, include_hand_card = False)  # 计算玩家有几个鸡牌
            p_ji_cards = p.ji_pai[:]  # list
            is_winner = p in self.winner_list
            p_hand_ji = p.calc_hand_ji_by_lai_zi(
                self.default_ji, self.ji_cards, self.__fan_ji_score, self.lai_zi, is_winner)
            # 冲锋鸡之前算过 -1
            self.remove_player_ji_card(p_ji_cards, p)

            hand_ji_card_count = self.cal_card_count(p_hand_ji)
            hand_lai_zi_count = hand_ji_card_count.get(self.lai_zi, 0)  # 手里的癞子数量
            # 一筒在手里必须翻到才算
            for ji, count in hand_ji_card_count.items():
                p_ji_cards.extend([ji] * count)
            if not p_ji_cards:
                continue

            ji_card_count = self.cal_card_count(p_ji_cards)
            bearer, get_bearer = self.zha_hu_bear_no_zha_hu(p)

            for ji, count in ji_card_count.items():
                score = 0
                if ji in self.default_ji or ji == self.lai_zi:
                    # 金鸡 x2
                    if ji in self.fan_jin_ji_cards:
                        bei_lv = 3
                        if ji == self.lai_zi:
                            hand_lai_zi_score = 10 * hand_lai_zi_count
                            # 剩下的算打出的金鸡
                            # 2024/5/10打出去的冲锋幺筒20，其余的15
                            out_lai_zi_score = self.ji_pai_score.get(ji) * (count - hand_lai_zi_count) * bei_lv
                            score = score + hand_lai_zi_score + out_lai_zi_score
                        else:
                            score += self.ji_pai_score.get(ji, 1) * count * bei_lv  # 金鸡 x 2
                        count = 0
                    else:
                        # 一筒在手里必须翻到才算鸡
                        if ji == self.lai_zi:
                            count -= hand_lai_zi_count
                if bearer:
                    # x2是炸胡者承担2份
                    if ji == CardsType.WU_GU_JI and ji not in self.default_ji:
                        score = (score + count) * 2
                    else:
                        score = (score + self.ji_pai_score.get(ji, 1) * count) * 2
                    self.update_score(type_, p.seat_id, bearer.seat_id, -score, ji, accounts, get_bearer.seat_id)
                else:
                    win_total = 0
                    win_from = []
                    if ji == CardsType.WU_GU_JI and ji not in self.default_ji:
                        per_score = score + count
                    else:
                        per_score = score + self.ji_pai_score.get(ji, 1) * count
                    for other_p in self.seats:
                        if not other_p:
                            continue
                        if p.seat_id == other_p.seat_id:
                            continue
                        other_data = self.other_ming_xi_data(type_, p.seat_id, -per_score, ji)
                        self.update_result_score(accounts, other_p.seat_id, 0, other_data)
                        win_total += per_score
                        win_from.append(other_p.seat_id)

                    self_data = self.self_ming_xi_data(type_, win_from, win_total, ji)
                    self.update_result_score(accounts, p.seat_id, 1, self_data)
        self.check_out_lai_zi_ji(accounts)

    def remove_player_ji_card(self, p_ji_cards, p: Player):
        super().remove_player_ji_card(p_ji_cards, p)
        if self.__cf_yi_wan_seat_id != 0 and self.__cf_yi_wan_seat_id == p.seat_id:
            p_ji_cards.remove(CardsType.YI_WAN)

    def check_out_lai_zi_ji(self, accounts: dict):
        """
        结算赖子鸡：打出去打一筒（包括碰杠的）
        注意：这里把如果玩家未叫牌，则算负分（相当于包鸡）
        """
        if not self.lai_zi:
            return
        self.log_info(self.tid, "结算赖子鸡", self.lai_zi, self.ji_cards)
        type_ = CheckType.CHECK_LAI_ZI_JI
        score = self.ji_pai_score.get(CardsType.YI_TONG, 0)
        if self.lai_zi in self.ji_cards:
            # 没翻到赖子鸡时，打出一筒的赖子叫牌时算为10分/个，握在手里不计分，打出未叫牌-10/个。
            score = self.ji_pai_score.get(JiType.JIN_YI_TONG, 0)

        for p in self.seats:
            if p.jiao_pai > 0 and p.seat_id in self.shao_ji_gang_seats:
                self.log_info(p.uid, "结算碰杠+打出去的癞子鸡, 玩家叫牌但被烧鸡烧杠")
                continue
            played_count = p.lai_zi_in_played(self.lai_zi)
            if self.__cf_yi_tong_seat_id == p.seat_id:
                played_count -= 1
                self.log_info(p.uid, "结算癞子鸡，冲锋赖子鸡玩家-1", played_count)
            if played_count <= 0:
                continue
            per_score = score * played_count
            if p.jiao_pai <= 0:
                per_score *= -1
            self.log_info(p.uid, p.seat_id, "结算打出的赖子鸡", played_count)
            win_total = 0
            win_from = []
            for other_p in self.seats:
                if other_p.seat_id == p.seat_id:
                    continue
                if per_score < 0 and other_p.jiao_pai <= 0:
                    # 包赖子时只包给叫牌的人
                    continue
                win_total += per_score
                win_from.append(other_p.seat_id)
                other_data = self.other_ming_xi_data(type_, p.seat_id, -per_score, self.lai_zi)
                self.update_result_score(accounts, other_p.seat_id, 0, other_data)

            self_data = self.self_ming_xi_data(type_, win_from, win_total, self.lai_zi)
            self.update_result_score(accounts, p.seat_id, 1, self_data)

    def bao_ji_check(self, accounts, liu_ju=False):
        type_ = CheckType.CHECK_JI

        default_ji = self.default_ji.copy()

        # 外循环为未叫牌/炸胡玩家
        for p in self.seats:
            # 叫牌且未炸胡玩家不存在包杠
            if p.jiao_pai > 0 and not p.is_zha_hu:
                continue
            p.get_bao_ji(default_ji)  # 计算玩家有几个鸡牌
            p_ji_cards = p.ji_pai[:]  # list
            # 冲锋鸡之前算过 -1
            self.remove_player_ji_card(p_ji_cards, p)

            if not p_ji_cards:
                continue
            ji_card_count = self.cal_card_count(p_ji_cards)
            bearer, get_bearer = self.zha_hu_bear_no_zha_hu(p)
            bearer_seat_id = p.seat_id
            get_bearer_seat = -1
            if not p.is_zha_hu and bearer:
                bearer_seat_id = bearer.seat_id
                get_bearer_seat = p.seat_id

            for ji, count in ji_card_count.items():
                # 流局包鸡没有金鸡一说
                win_total = 0
                win_from = []
                per_score = self.get_per_score(ji, 0, count, default_ji, liu_ju)

                for other_p in self.seats:
                    if other_p.seat_id == p.seat_id:
                        continue
                    if other_p.seat_id == bearer_seat_id:
                        continue
                    if other_p.is_zha_hu or other_p.jiao_pai <= 0:
                        continue
                    if other_p.seat_id in self.shao_ji_gang_seats:
                        self.log_info(other_p.uid, "__bao_ji_check", "被烧鸡不能收别人包鸡赔付")
                        continue
                    other_data = self.other_ming_xi_data(type_, bearer_seat_id, per_score, ji)
                    self.update_result_score(accounts, other_p.seat_id, 0, other_data)
                    win_total += per_score
                    win_from.append(other_p.seat_id)
                    # todo: 包鸡者未炸胡，但有人炸胡，炸胡者承担

                self_data = self.self_ming_xi_data(type_, win_from, -win_total, ji, get_bearer=get_bearer_seat)
                self.update_result_score(accounts, bearer_seat_id, 1, self_data)

    def check_out_hu_lai_zi(self, accounts: dict):
        """ 胡1筒算分 """
        if self.curr_card != self.lai_zi:
            return
        self.log_info("胡一筒算分")
        for hu_info in self.kai_pai_hu_info:
            if hu_info.get("is_zi_mo"):
                continue
            seat_id = hu_info.get("seat_id")
            if self.__round_first_yi_tong == 0:
                score = self.ji_pai_score.get(JiType.CF_YI_TONG)
            else:
                score = self.ji_pai_score.get(CardsType.YI_TONG)
            pei_seat = hu_info.get("fang_pao_seat_id")
            self.update_score(CheckType.CHECK_ZE_REN_JI, seat_id, pei_seat, -score, self.lai_zi, accounts)

    def check_out_ying_hu(self, accounts: dict):
        """
        结算硬胡(只在胡牌是结算)
        仅胡牌玩家有硬胡
        幺筒不为赖子，直接作为幺筒，也是硬胡
        """
        if not self.lai_zi:
            return
        ying_hu_score = self.__ying_hu_score
        for hu_info in self.kai_pai_hu_info:
            is_zi_mo = hu_info.get("is_zi_mo")
            seat_id = hu_info.get("seat_id")
            winner = self.get_player_by_seat_id(seat_id)
            di_long_qi_peng_card = self.is_lai_zi_di_long_qi(winner)
            if not Rule.is_ying_hu_by_hu_path(winner.cards, winner.hu_path, self.lai_zi, di_long_qi_peng_card):
                continue
            self.log_info("结算硬胡", ying_hu_score, winner.cards, winner.hu_path)
            if is_zi_mo:
                self.inner_check(ying_hu_score, seat_id, accounts,CheckType.CHECK_YING_HU)
            else:
                pei_seat = hu_info.get("fang_pao_seat_id")
                other_data = self.other_ming_xi_data(
                    CheckType.CHECK_YING_HU, seat_id, -ying_hu_score, self.lai_zi)
                self.update_result_score(accounts, pei_seat, 0, other_data)
                self_data = self.self_ming_xi_data(
                    CheckType.CHECK_YING_HU, [pei_seat], ying_hu_score, self.lai_zi)
                self.update_result_score(accounts, seat_id, 1, self_data)

    @staticmethod
    def is_lai_zi_di_long_qi(winner: Player) -> 0:
        """ 判断是否是癞子的地龙七 """
        if winner.hu_type not in (HuType.DI_LONG_QI, HuType.DOUBLE_DI_LONG_QI, HuType.THREE_DI_LONG_QI):
            return 0
        if winner.table_cards:
            return winner.table_cards[0][1]
        return 0

    def check_chong_xi(self, accounts: dict):
        """
        结算冲喜
        手里有4个一筒，已听牌情况下，冲喜25分（有4张就算冲喜）
        杠再加5(杠原本就是5？)
        """

        for p in self.seats:
            if p.jiao_pai <= 0:
                continue
            hand_lz_count = p.cards.count(self.lai_zi)
            out_lz_count = p.chu_cards.count(self.lai_zi)
            # 2024/6/12
            if hand_lz_count + out_lz_count == 4:
                cx_score = self.__xi_pai_score
                self.log_info(p.uid, "结算冲喜，手里 + 打出去", cx_score, hand_lz_count, out_lz_count)
                self.inner_check(cx_score, p.seat_id, accounts,CheckType.CHECK_LAI_ZI_CHONG_XI)
                break
            elif hand_lz_count == 1 or out_lz_count == 1:
                for table_card in p.table_cards:
                    if table_card[0] == ActionType.ACTION_TYPE_PENG and table_card[1] == self.lai_zi:
                        cx_score = self.__xi_pai_score
                        self.log_info(p.uid, "结算冲喜，碰", hand_lz_count, out_lz_count, cx_score)
                        self.inner_check(cx_score, p.seat_id, accounts,CheckType.CHECK_LAI_ZI_CHONG_XI)
                        break
            elif hand_lz_count == 0:
                for table_card in p.table_cards:
                    if table_card[0] != ActionType.ACTION_TYPE_PENG and table_card[1] == self.lai_zi:
                        cx_score = self.__xi_pai_score
                        self.log_info(p.uid, "结算冲喜，杠", cx_score)
                        self.inner_check(cx_score, p.seat_id, accounts,CheckType.CHECK_LAI_ZI_CHONG_XI)
                        break

    def inner_check(self, score, seat_id, accounts,c_type):
        win_total = 0
        win_from = []
        for other_p in self.seats:
            if other_p.seat_id == seat_id:
                continue
            win_total += score
            win_from.append(other_p.seat_id)
            other_data = self.other_ming_xi_data(
                c_type, seat_id, -score, self.lai_zi)
            self.update_result_score(accounts, other_p.seat_id, 0, other_data)

        self_data = self.self_ming_xi_data(c_type, win_from, win_total, self.lai_zi)
        self.update_result_score(accounts, seat_id, 1, self_data)

    def get_player_jiao_pai(self):
        """玩家叫牌牌型获取"""
        for p in self.seats:
            if p.seat_id in self.win_seat_list:
                p.lian_zhuang += 1
            else:
                p.lian_zhuang = 0

            p.jiao_pai = Rule.get_round_over_jiao_pai_by_zun_yi(
                p.table_cards, p.cards,0, self.lai_zi, self.__fan_ji_score,self.pai_xing_score_map,self.extra_score_map)


    def check_ze_ren_ji(self, accounts, liu_ju=False, is_bao=False):
        """ 结算责任鸡 """
        if not self.ze_ren_ji:
            return
        super().check_ze_ren_ji(accounts,liu_ju,is_bao)

        if self.__ze_ren_yi_tong_seat_id != 0 and self.__ze_ren_yi_tong_win_seat_id != 0:
            ji_card = CardsType.YI_TONG
            key = JiType.CF_YI_TONG
            if ji_card in self.fan_jin_ji_cards:  # 翻到为金鸡
                key = JiType.JIN_CF_YI_TONG
            score = self.ji_pai_score.get(key, 0)
            self.concreteness_check_ze_ren_ji(
                accounts, self.__ze_ren_yi_tong_win_seat_id, self.__ze_ren_yi_tong_seat_id, ji_card, score, liu_ju,is_bao)

        if self.__ze_ren_yi_wan_seat_id != 0 and self.__ze_ren_yi_wan_win_seat_id != 0:
            ji_card = CardsType.YI_WAN
            key = JiType.CF_YI_WAN
            if ji_card in self.fan_jin_ji_cards:  # 翻到为金鸡
                key = JiType.JIN_CF_YI_WAN
            score = self.ji_pai_score.get(key, 0)
            self.concreteness_check_ze_ren_ji(
                accounts, self.__ze_ren_yi_wan_win_seat_id, self.__ze_ren_yi_wan_seat_id, ji_card, score, liu_ju,is_bao)


    def deal_ze_ren_ji(self, p):
        """
        处理责任鸡handle
        """
        super().deal_ze_ren_ji(p)
        if self.curr_card == CardsType.YI_TONG and self.__round_first_yi_tong == 0:
            self.__ze_ren_yi_tong_seat_id = self.curr_seat_id
            self.__ze_ren_yi_tong_win_seat_id = p.seat_id
            if self.__cf_yi_tong_seat_id > 0:
                cf_yi_tong_player = self.get_player_by_seat_id(self.__cf_yi_tong_seat_id)
                cf_yi_tong_player.chong_feng_yi_tong = 0
                self.__cf_yi_tong_seat_id = 0

            curr_p = self.curr_player()
            curr_p.ze_ren_yi_tong = 1
            self.__round_first_yi_tong = 1
            return 1,self.__ze_ren_yi_tong_seat_id

        if self.__yi_wan_ji and self.curr_card == CardsType.YI_WAN and self.__round_first_yi_wan == 0:
            self.__ze_ren_yi_wan_seat_id = self.curr_seat_id
            self.__ze_ren_yi_wan_win_seat_id = p.seat_id
            if self.__cf_yi_wan_seat_id > 0:
                cf_yi_tong_player = self.get_player_by_seat_id(self.__cf_yi_wan_seat_id)
                cf_yi_tong_player.chong_feng_yi_wan = 0
                self.__cf_yi_wan_seat_id = 0
            curr_p = self.curr_player()
            curr_p.ze_ren_yi_wan = 1
            self.__round_first_yi_wan = 1
            return 1,self.__ze_ren_yi_wan_seat_id
        return 0,0



