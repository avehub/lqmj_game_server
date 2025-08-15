from common.proto.py_pb2.ws_c2s import ding_que_model
from common.proto.py_pb2.ws_leisure import S2CDingQueInfo, s2c_one_of_model
from common.public.enum_const import StaCode
from .player import Player
from .room_base import Room
from .const import (FlowStatus, ActionType, CheckType, PlayType, JiType, CardsType, HuType)
from .rule import Rule
from ..const.cs_enum_const import CmdRoom, RoomStatus


class RoomBJ(Room):
    def __init__(self, tid, service, room_conf):
        room_conf.get("rule_details")["bao_ting"] = 1
        room_conf.get("rule_details")["ze_ren_ji"] = 1
        room_conf.get("rule_details")["chong_feng_ji"] = 1
        room_conf.get("rule_details")["zi_mo_jia_bei"] = 1
        super().__init__(tid, service, room_conf)
        self.__shu_zi_ji = self.rule_detail.get("shu_zi_ji", 0)  # 数字鸡

    def check_extra_ji(self, ji, score, count):
        if self.yin_ji and ji in self.fan_yin_ji_cards:
            # 银鸡处理（只有翻鸡才有，流局无）
            per_score = score + self.ji_pai_score.get(JiType.YIN_JI, 1) * count
            self.log_info(self.tid, "银鸡算分", ji, per_score)
        else:
            if self.__shu_zi_ji and ji != CardsType.YAO_JI:
                per_score = score + (ji % 10) * count  # 数字鸡
            else:
                per_score = score + self.ji_pai_score.get(ji, 1) * count
        return per_score

    def get_tian_ting_operates(self, p):
        """获取玩家天听操作"""
        operates = []
        if p.seat_id == self.dealer_id:
            flag, gang_card_list = p.can_an_gang(Rule)
            if flag:
                operates.append(ActionType.ACTION_TYPE_AN_GANG)
            can_hu, _ = self.hu_de_qi(p)
            if can_hu:
                operates.append(ActionType.ACTION_TYPE_HU)
            else:
                operates.extend(self.calc_operates_in_tian_ting(p, True))
        else:
            operates.extend(self.calc_operates_in_tian_ting(p))
        p.operates = operates
        return operates

    def check_hu_and_ting(self, p: Player, result, can_gang_list):
        can_hu, hu_info = self.hu_de_qi(p)
        if can_hu:
            if p.seat_id != self.dealer or p.all_chu_cards:
                result.append(ActionType.ACTION_TYPE_HU)

        if not self.yuan_bao and not p.all_chu_cards and p.can_tian_ting > -1:
            if self.can_select_tian_ting(p, self.deal_cards_count + 1):
                result.append(ActionType.ACTION_TYPE_TIAN_TING)

    def check_hu_by_chu_pai(self, p, result):
        can_hu, hu_info = self.hu_de_qi(p)
        if can_hu:
            result.append(ActionType.ACTION_TYPE_HU)
        return result

    def kai_pai_check_out(self, accounts: dict):
        """
        开牌结算
        统一数据结构
        """
        accounts, zhuo_ji = super().kai_pai_check_out(accounts)

        if self.bao_ji:
            self.bao_ji_check(accounts)

        # 4.2 结算包杠
        if self.bao_gang:
            self.bao_gang_check(accounts)

        self.check_out_lian_zhuang(accounts)

        return accounts, zhuo_ji

    def get_per_score(self, ji, score, count, default_ji, liu_ju):

        bei_lv = 1
        if not liu_ju:
            if ji in self.fan_jin_ji_cards:
                bei_lv = 10

        if self.yin_ji and ji == CardsType.YI_TONG:
            per_score = self.ji_pai_score.get(ji, 1) * count  # 翻到银鸡才有5分
        else:
            if self.__shu_zi_ji and ji != CardsType.YAO_JI:
                per_score = (ji % 10) * count  # 数字鸡
            else:
                per_score = self.ji_pai_score.get(ji, 1) * count * bei_lv
        return per_score

    async def on_player_pass(self, p: Player):
        if not self.room_status_is_equal(RoomStatus.T_PLAYING):
            return StaCode.FLOW_ERR, "桌子状态不在游戏中"
        if self.flow_status not in (FlowStatus.T_IN_PUBLIC_OPRATE, FlowStatus.T_IN_MO_PAI_CALL,
                                    FlowStatus.T_IN_MING_GANG_PAI_CALL, FlowStatus.T_IN_FOUR_BAO_TING,
                                    FlowStatus.T_IN_ZHUAN_WAN_GANG_PAI_CALL,
                                    FlowStatus.T_IN_TIAN_HU, FlowStatus.T_IN_TIAN_TING):
            return StaCode.FLOW_ERR, "游戏流程不在可过流程"

        if self.has_do_by_action(p, ActionType.ACTION_TYPE_PASS):  # 不允许再次操作
            return StaCode.RULE_ERR, "已经操作过了"
        if p.can_tian_ting == 0 and self.flow_status == FlowStatus.T_IN_TIAN_TING:
            p.can_tian_ting = -1

        self.save_player_action(p, ActionType.ACTION_TYPE_PASS)
        p.operates = []
        one_of_model = s2c_one_of_model()
        one_of_model.seat_id = self.curr_seat_id
        await self.inner_send(p, CmdRoom.PLAYER_PASS, one_of_model)
        return StaCode.PASS, ""

    def check_out_lian_zhuang(self, accounts: dict):
        """结算连庄：连庄玩家从其他玩家获得（连庄次数-1）分"""
        if self.lian_zhuang != 1:  # 非连庄模式直接退出
            return
        self.log_info("结算连庄")
        type_ = CheckType.CHECK_LIAN_ZHUANG

        # 预过滤有效玩家（非空且连庄≥2）
        valid_winners = [w for w in self.winner_list if w and w.lian_zhuang >= 2]
        if not valid_winners:  # 无有效连庄玩家提前退出
            return

        # 预过滤需付分玩家（非空且非连庄玩家）
        payers = [p for p in self.seats if p and p not in valid_winners]

        # 批量处理连庄玩家
        for winner in valid_winners:
            score_per_payer = winner.lian_zhuang - 1  # 单玩家应付分数
            win_total = score_per_payer * len(payers)  # 总收益
            win_from = [p.seat_id for p in payers]  # 付分玩家列表

            # 批量扣除玩家分数
            for payer in payers:
                other_data = self.other_ming_xi_data(type_, winner.seat_id, -score_per_payer)
                self.update_result_score(accounts, payer.seat_id, 0, other_data)

            # 连庄玩家加分
            self_data = self.self_ming_xi_data(type_, win_from, win_total)
            self.update_result_score(accounts, winner.seat_id, 1, self_data)
