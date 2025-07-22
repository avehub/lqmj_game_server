from common.proto.py_pb2.ws_c2s import ding_que_model
from common.proto.py_pb2.ws_leisure import S2CDingQueInfo
from common.public.enum_const import StaCode
from .const import (FlowStatus, ActionType, CheckType, PlayType, CardsType, JiType)
from .room_bijie import RoomBJ
from ..const.cs_enum_const import CmdRoom


class RoomGY(RoomBJ):
    def __init__(self, tid, service, room_conf):
        room_conf.get("rule_details")["zhan_ji"] = 1

        super().__init__(tid, service, room_conf)
        self.__cha_que = 0
        self.__yuan_que = 0
        if self.play_type in (PlayType.GUI_YANG_2,PlayType.GUI_YANG_3) and self.liang_men_pai == 0:
            self.__cha_que = 1
            self.__yuan_que = 1


    def get_tian_ting_operates(self,p):
        """获取玩家天听操作"""
        operates = []
        if p.seat_id == self.dealer_id:
            can_hu, _ = self.hu_de_qi(p)
            if can_hu:
                operates.append(ActionType.ACTION_TYPE_HU)
            else:
                operates.extend(self.calc_operates_in_tian_ting(p, True))
        else:
            operates.extend(self.calc_operates_in_tian_ting(p))
        return operates

    async def on_player_ding_que(self,player,data):
        ding_que_model.ParseFromString(data)
        que = ding_que_model.que
        if not self.flow_status_is_equal(FlowStatus.T_IN_DING_QUE):
            return StaCode.FLOW_ERR,"不在定缺流程中"
        if self.liang_men_pai == 0 or self.play_type not in (PlayType.GUI_YANG_2,PlayType.GUI_YANG_2):
            return StaCode.RULE_ERR,"当前玩法不存在定缺"
        if player.que!=0:
            return StaCode.ALREADY_DO,"当前玩家已经定缺过了"
        if que not in self.que_list:
            return StaCode.RULE_ERR,"参数错误，不在定缺范围内"

        player.que = que
        data = {
            "que": que,
            "seat_id": player.seat_id,
        }
        data_model = S2CDingQueInfo.pb_model(**data)
        await self.inner_broadcast(CmdRoom.PLAYER_DING_QUE,data_model)
        is_all_ding_que = True
        for p in self.seats:
            if p.que==0:
                is_all_ding_que = False
                break

        if is_all_ding_que:
            self.call_flow(1,self.start_game_after_ding_que)
        return StaCode.Pass,""

    async def start_game_after_ding_que(self):
        if self.__yuan_que:
            for p in self.seats:
                p.set_is_yuan_que() #置玩家原缺状态
        await self.enter_mo_pai_call()


    def kai_pai_check_out(self, accounts: dict):
        """
        3人开牌结算
        统一数据结构
        """
        accounts, zhuo_ji = super().kai_pai_check_out(accounts)
        # 原缺
        self.check_out_yuan_que(accounts)
        # 查缺
        self.check_out_cha_que(accounts)
        #包鸡
        if self.bao_ji:
            self.bao_ji_check(accounts)
        #包杠
        if self.bao_gang:
            self.bao_gang_check(accounts)

        self.check_out_lian_zhuang(accounts)

        return accounts, zhuo_ji


    def check_out_yuan_que(self, accounts: dict):
        """结算原缺：起手≤2门牌的玩家可从非原缺玩家处获得额外积分"""
        if self.__yuan_que != 1:
            return

        self.log_info(self.__tid, "开始结算源缺")
        type_ = CheckType.CHECK_YUAN_QUE
        base_score = self.extra_score_map.get(type_, 2)

        # 预过滤叫牌玩家
        valid_players = [p for p in self.seats if p.jiao_pai > 0]

        # 分离原缺玩家和非原缺玩家
        yuan_que_players = [p for p in valid_players if p.yuan_que]
        non_yuan_que_players = [p for p in valid_players if not p.yuan_que]

        # 无原缺玩家时提前退出
        if not yuan_que_players:
            return

        # 批量处理原缺玩家收益
        for payer in non_yuan_que_players:
            for receiver in yuan_que_players:
                payer_data = self.other_ming_xi_data(type_, receiver.seat_id, -base_score)
                self.update_result_score(accounts, payer.seat_id, 0, payer_data)

        # 批量处理原缺玩家收益
        for receiver in yuan_que_players:
            win_total = base_score * len(non_yuan_que_players)
            win_from = [p.seat_id for p in non_yuan_que_players]
            receiver_data = self.self_ming_xi_data(type_, win_from, win_total)
            self.update_result_score(accounts, receiver.seat_id, 1, receiver_data)


    def check_out_cha_que(self, accounts: dict):
        """
        结算查缺
        每一位玩家的手牌中有自己开局定缺的牌都要向完成缺一门的玩家赔付，每有1张缺牌赔付1分。
        """
        if self.__cha_que != 1:
            return
        self.log_info(self.__tid, "开始结算查缺")
        type_ = CheckType.CHECK_CHA_QUE

        # 预过滤有效玩家
        valid_players = []
        player_que_count = {}
        for p in self.seats:
            if p.jiao_pai <= 0:
                continue
            que_count = p.que_count()
            player_que_count[p.seat_id] = que_count
            valid_players.append(p)

        receivers = [p for p in valid_players if player_que_count[p.seat_id] == 0] #没有缺牌玩家
        payers = [p for p in valid_players if player_que_count[p.seat_id] > 0] #查缺玩家

        if not receivers or not payers:  # 全部缺牌或者没有缺牌玩家提前结束
            return

        payer_scores = {}
        for payer in payers:
            que_count = player_que_count[payer.seat_id]
            payer_scores[payer.seat_id] = que_count
            for receiver in receivers:
                other_data = self.other_ming_xi_data(type_, receiver.seat_id, -que_count)
                self.update_result_score(accounts, payer.seat_id, 0, other_data)

        for receiver in receivers:
            win_total = sum(payer_scores[p_id] for p_id in payer_scores)
            win_from = list(payer_scores.keys())
            self_data = self.self_ming_xi_data(type_, win_from, win_total)
            self.update_result_score(accounts, receiver.seat_id, 1, self_data)


    def get_per_score(self,ji,score,count,default_ji,liu_ju):
        bei_lv = 1
        if not liu_ju:
            if ji in self.__fan_jin_ji_cards:
                bei_lv = 2

        if ji == CardsType.WU_GU_JI and ji not in default_ji:
            per_score = count
        else:
            per_score = self.ji_pai_score.get(ji, 1) * count * bei_lv
        return per_score

    def check_extra_ji(self,ji,score,count):
        if ji == CardsType.WU_GU_JI and ji not in self.default_ji:
            per_score = score + count
        elif self.yin_ji and ji in self.fan_yin_ji_cards:
            # 银鸡处理（只有翻鸡才有，流局无）
            per_score = score + self.ji_pai_score.get(JiType.YIN_JI, 1) * count
        else:
            per_score = score + self.ji_pai_score.get(ji, 1) * count
        return per_score








