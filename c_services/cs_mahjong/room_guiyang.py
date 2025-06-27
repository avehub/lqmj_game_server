from common.proto.py_pb2.ws_c2s import ding_que_model
from common.proto.py_pb2.ws_leisure import S2CDingQueInfo
from common.public.enum_const import StaCode
from .room_base import Room
from .const import (FlowStatus, ActionType, CheckType, PlayType)
from ..const.cs_enum_const import CmdRoom


class RoomGY(Room):
    def __init__(self, tid, service, room_conf):
        room_conf.get("rule_details")["bao_ting"] = 1
        super().__init__(tid, service, room_conf)
        self.__cha_que = 0
        self.__yuan_que = 0
        self.__lian_zhuang = 0
        if self.play_type in (PlayType.GUI_YANG_2,PlayType.GUI_YANG_3) and self.liang_men_pai == 0:
            self.__cha_que = 1
            self.__yuan_que = 1

        if self.play_type == PlayType.GUI_YANG_4:
            self.__lian_zhuang = int(self.rule_detail.get("lian_zhuang", 0))

        self.__yuan_bao = 0
        if self.play_type in (PlayType.GUI_YANG_4, PlayType.GUI_YANG_3):
            # 起手牌满足听牌条件才能报听。摸第一张牌后不可再报听，庄家除外。
            self.__yuan_bao = self.__rule_details.get("yuan_bao", 0)

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


    def __kai_pai_check_out(self, accounts: dict):
        """
        3人开牌结算
        统一数据结构
        """
        # 翻鸡
        self.__ji_cards, zhuo_ji = self.calc_fan_ji_cards()
        self.log_info(self.tid, "翻到的所有鸡牌", self.__ji_cards, "捉鸡：", zhuo_ji)

        # 1.开牌牌型结算
        self.log_info(self.tid, "开胡信息: ", self.__kai_pai_hu_info)
        for hu_info in self.__kai_pai_hu_info:
            self.check_by_num_3(accounts, hu_info)

        # 原缺
        self.check_out_yuan_que(accounts)
        # 查缺
        self.check_out_cha_que(accounts)

        # 2.结算闷捡
        self.check_men_jian(accounts)

        # 3.结算鸡分
        # 3.1 冲锋鸡
        self.check_chong_feng_ji(accounts)

        # 3.2 责任鸡(责任鸡无金鸡一说，额外算分)
        self.check_ze_ren_ji(accounts)

        # 3.3 翻鸡
        self.check_ji(accounts)

        if self.bao_ji:
            self.bao_ji_check(accounts)

        # 4.结算杠分
        # 4.1 结算正常玩家的杠分
        self.check_gang(accounts)

        # 4.2 结算包杠
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

    def check_out_lian_zhuang(self, accounts: dict):
        """结算连庄（贵阳捉鸡4人专属）：连庄玩家从其他玩家获得（连庄次数-1）分"""
        if self.__lian_zhuang != 1:  # 非连庄模式直接退出
            return

        self.log_info(self.__tid, "结算连庄")
        type_ = CheckType.CHECK_LIAN_ZHUANG

        # 预过滤有效玩家（非空且连庄≥2）
        valid_winners = [w for w in self.__winner_list if w and w.lian_zhuang >= 2]
        if not valid_winners:  # 无有效连庄玩家提前退出
            return

        # 预过滤需付分玩家（非空且非连庄玩家）
        payers = [p for p in self.__seats if p and p not in valid_winners]

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






