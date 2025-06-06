import random
from common.proto.py_pb2.ws_leisure import bet_model, do_bet_model, s2c_operate_model, S2CRoundOver, sa_pu_model, \
    S2CRoomInfo03WaterFish, S2CPlayerInfo04WaterFish
from common.public.enum_const import StaCode
from .poker import Poker
from .const import FlowStatus, OperateType, CompareRes, OPERATE_RATE
from .rule import Rule
from c_services.const.cs_enum_const import CmdRoom, RoomStatus
from c_services.base.base_leisure_room import BaseLeisureRoom
from lucky_game.const import ReasonCostGold


class Room(BaseLeisureRoom):
    """
    游戏流程都差不多，基类实现基本游戏流程，规则不同的子类重实现
    """

    def __init__(self, tid, service, room_conf):
        super().__init__(tid, service, room_conf)
        self.__min_player_count = room_conf.get("min_player_count", 2)
        self.__bet_list: list = room_conf.get("bet_list") or [-1, 50, 100, 150]
        self.__card_count = 4
        self.__real_count = 0  # 真实人数，游戏开始再算
        self.__records_dealer_op: dict = {}  # 记录庄家的操作
        self.__records_farmer_op: dict = {}  # 记录闲家的操作
        self.__operate_num: int = 0  # 双方都操作完计数1次
        self.__poker = Poker()

    async def deal_cards(self):
        """ 发牌 """
        if not self.flow_status_is_equal(FlowStatus.FLOW_IN_READY):
            self.info_log("发牌错误，桌子未就绪")
            return
        self.set_flow_status(FlowStatus.FLOW_IN_DEAL_CARDS)
        all_cards = self.__poker.deal_cards(self.__real_count, self.__card_count)
        await super().do_deal_cards(all_cards)

        self.start_sa_pu()

    async def start_bet(self):
        """ 开始下注 """
        self.set_flow_status(FlowStatus.FLOW_IN_BET)
        wait_sec = 10
        bet_model.bet_list.extend(self.__bet_list)
        bet_model.seconds = wait_sec
        await self.inner_broadcast(CmdRoom.START_BET)
        bet_model.bet_list[:] = []  # 清空列表

        # todo：机器人下注
        for player in self.seats:
            if player.is_robot:
                await self.robot_bet(player)

        self.call_flow(wait_sec, self.time_out_bet)
        self.call_flow_trustee(0, self.trustee_bet)

    async def robot_bet(self, player):
        """ 机器人下注 """
        await self.player_bet(player, 50)

    @property
    def is_all_bet(self):
        """ 是否都下注 """
        for player in self.seats:
            if player.bet == 0:
                return False
        return True

    async def time_out_bet(self):
        """ 超时下注 """
        if not self.flow_status_is_equal(FlowStatus.FLOW_IN_BET):
            return
        for player in self.seats:
            if player.seat_id == self.dealer_id:
                continue
            if player.bet == 0:
                bet = self.__bet_list[1]  # 默认50倍
                await self.do_trustee(player, True)
                await self.player_bet(player, bet)

        await self.deal_cards()

    async def trustee_bet(self):
        """ 托管下注 """
        if not self.flow_status_is_equal(FlowStatus.FLOW_IN_BET):
            return
        for player in self.seats:
            if not player.trustee:
                continue
            if player.seat_id == self.dealer_id:
                continue
            if player.bet == 0:
                bet = self.__bet_list[1]  # 默认50倍
                await self.player_bet(player, bet)
        await self.deal_cards()

    async def start_confirm_dealer(self):
        """ 开始定庄 """
        seats = []
        for p in self.seats:
            if not p.is_out:
                seats.append(p.seat_id)
        data = {}
        await self.inner_broadcast(CmdRoom.CONFIRM_DEALER, data)
        self.dealer_id = random.choice(seats)

        await self.delay_func(2, self.start_bet)

    def start_sa_pu(self):
        """ 开始撒扑 """
        if not self.flow_status_is_equal(FlowStatus.FLOW_IN_DEAL_CARDS):
            self.info_log("流程错误，撒扑前应该是发牌")
            return
        self.set_flow_status(FlowStatus.FLOW_IN_SA_PU)
        self.info_log("开始撒扑")
        self.robot_auto_sa_pu()

    def robot_auto_sa_pu(self):
        """ 机器人自动撒扑 """
        for p in self.seats:
            if not p:
                continue
            if not p.is_robot:
                continue
            self.player_sa_pu(p, p.cards, OperateType.FARMER_LP)

    async def start_operates(self):
        """ 开始操作：走/杀/开/信/反 """
        if not self.flow_status_is_equal(FlowStatus.FLOW_IN_SA_PU_END):
            self.info_log("流程错误，必须撒扑完才开始庄操作")
            return
        self.info_log("开始庄喊话")
        self.set_flow_status(FlowStatus.FLOW_IN_OPERATE)
        dealer = self.dealer()
        await self.continue_dealer_operate(dealer)

    async def robot_dealer_operate(self, dealer, seat_id):
        """ 机器人庄操作 """
        player = self.get_player_by_seat_id(seat_id)
        if player.sp_status == OperateType.FARMER_LP:
            operate = OperateType.LANDLORD_SHA
        else:
            operate = OperateType.LANDLORD_KAI
        await self.player_dealer_operate(dealer, operate, seat_id)

    async def continue_dealer_operate(self, dealer):
        """ 继续庄操作 """
        while 1:
            if self.curr_seat_id == self.dealer_id:
                self.info_log("庄家操作完")
                return
            next_player = self.next_player(self.curr_seat_id)
            self.curr_seat_id = next_player.seat_id
            if next_player.sp_status != OperateType.FARMER_QG:
                break

        wait_sec = 15
        data = {"seat_id": self.curr_seat_id, "sp_status": next_player.sp_status, "seconds": wait_sec}
        await self.inner_broadcast(CmdRoom.DEALER_OPERATE, data)
        if dealer.is_robot:
            # todo: 机器人操作
            await self.robot_dealer_operate(dealer, self.curr_seat_id)

        if dealer.trustee:
            wait_sec = 0
        self.call_flow(wait_sec, self.time_out_dealer_operate, dealer, self.curr_seat_id)

    async def robot_auto_farmer_operate(self, seat_id: int):
        """ 机器人闲自动操作 """
        # todo: 后续实现
        p = self.get_player_by_seat_id(seat_id)
        await self.player_farmer_operate(p, OperateType.FARMER_SHA_FAN.val)  # 杀反

    async def player_bet(self, player, bet: int):
        """ 玩家下注 """
        if not self.flow_status_is_equal(FlowStatus.FLOW_IN_BET):
            return StaCode.FORBID, "桌子状态非游戏中"
        if player.bet != 0:
            return StaCode.FORBID, "已下注过"
        if bet not in self.__bet_list:
            return StaCode.FORBID, "下注倍数有误"

        player.bet = bet
        do_bet_model.seat_id = player.seat_id
        do_bet_model.bet = player.bet
        await self.inner_broadcast(CmdRoom.DO_BET, do_bet_model)

        if self.is_all_bet:
            self.call_flow(1, self.deal_cards)
        return StaCode.PASS, ""

    async def player_sa_pu(self, player, cards, sp_status: int):
        """ 玩家撒扑 """
        if len(cards) != self.__card_count:
            self.info_log(player.uid, "撒扑有误，撒扑的牌必须满足该有数量，", len(cards))
            return StaCode.FORBID, "牌数不对"
        if player.seat_id == self.dealer_id:
            player.sp_status = OperateType.FARMER_MI
        else:
            dealer = self.dealer()
            if dealer.sp_status == 0:
                self.info_log(player.uid, "操作有误，闲家撒扑前需要等庄家撒扑")  # 主要为了防止闲强攻后直接进入round_over
                return StaCode.FORBID, "庄家还未撒扑"
            player.sp_status = sp_status
            if sp_status == OperateType.FARMER_QG:
                self.__operate_num += 1

        if Rule.is_different_cards(cards, player.cards):
            return StaCode.FORBID, "撒扑的牌不合法"

        player.cards = Rule.sort_sa_pu(cards)  # 大小铺分扑
        self.info_log(player.uid, "玩家撒扑: ", player.cards, sp_status)

        sa_pu_model.seat_id = player.seat_id
        sa_pu_model.sp_status = player.sp_status
        await self.inner_broadcast(CmdRoom.SA_PU, sa_pu_model)

        sa_pu_model.cards.extend(player.cards)
        sa_pu_model.cards[:] = []  # 清空列表
        await self.inner_send(player, CmdRoom.SA_PU, sa_pu_model)

        if self.is_sa_pu_over:
            self.set_flow_status(FlowStatus.FLOW_IN_SA_PU_END)
            return self.start_operates()

    async def player_dealer_operate(self, dealer, operate, seat_id):
        """ 庄操作接口 """
        if dealer.seat_id != self.dealer_id:
            return StaCode.FORBID, "必须是庄才能调用该接口"
        if seat_id != self.curr_seat_id:
            return StaCode.NOT_YOUR_TURN, "未轮到当前玩家"

        farmer = self.curr_player()
        sa_pu_status = farmer.sp_status
        if sa_pu_status == OperateType.FARMER_QG:
            return StaCode.RULE_ERR, "强攻必比"
        if sa_pu_status == OperateType.FARMER_LP:
            if operate not in (OperateType.LANDLORD_SHA, OperateType.LANDLORD_ZOU):
                return StaCode.RULE_ERR, f"对亮牌者只能杀或走，当前操作：{sa_pu_status}"
        if sa_pu_status == OperateType.FARMER_MI:
            if operate not in (OperateType.LANDLORD_KAI, OperateType.LANDLORD_XIN):
                return StaCode.RULE_ERR, f"对密牌者只能开或信，当前操作：{sa_pu_status}"
            self.__operate_num += 1

        if self.__records_dealer_op.get(seat_id):
            return StaCode.FORBID, f"操作有误，庄家已经对该玩家{seat_id}操作过了"

        self.__records_dealer_op[seat_id] = operate
        self.info_log(f"庄{self.dealer_id}对闲{seat_id}进行：{operate.phrase}")

        wait_sec = 10
        operate_model = s2c_operate_model(seat_id, operate, wait_sec)
        await self.inner_broadcast(CmdRoom.DEALER_OPERATE, operate_model)

        if sa_pu_status == OperateType.FARMER_LP:
            # 只有亮牌的有后续操作
            if farmer.is_robot:
                self.call_flow_robot(1, self.robot_auto_farmer_operate, seat_id)
                wait_sec = 0
            farmer.call_flow(wait_sec, self.time_out_farmer_operate, farmer, _log=self.err_log)

        await self.continue_dealer_operate(dealer)

    async def time_out_dealer_operate(self, dealer, seat_id):
        """ 庄操作超时 """
        if not self.flow_status_is_equal(FlowStatus.FLOW_IN_OPERATE):
            self.info_log(f"庄操作超时，流程错误：{self.flow_status}")
            return
        if seat_id != self.curr_seat_id:
            self.info_log(f"庄操作超时，当前玩家id不对：", seat_id, self.curr_seat_id)
            return
        if self.__records_dealer_op.get(seat_id):
            self.info_log(f"庄操作超时，对当前玩家已操作过：", seat_id)
            return
        if not dealer.trustee:
            await self.do_trustee(dealer, True)

        curr_player = self.curr_player()
        if curr_player.sp_status == OperateType.FARMER_LP:
            await self.player_dealer_operate(dealer, OperateType.LANDLORD_ZOU, seat_id)
        elif curr_player.sp_status == OperateType.FARMER_MI:
            await self.player_dealer_operate(dealer, OperateType.LANDLORD_XIN, seat_id)

    async def time_out_farmer_operate(self, player):
        """ 闲操作超时 """
        if not self.flow_status_is_equal(FlowStatus.FLOW_IN_OPERATE):
            self.info_log(player.uid, player.seat_id, f"闲操作超时，流程错误：{self.flow_status}")
            return
        dealer_operate = self.__records_dealer_op.get(player.seat_id)
        if not dealer_operate:
            return
        if dealer_operate == OperateType.LANDLORD_ZOU:
            await self.player_farmer_operate(player, OperateType.FARMER_ZOU_XIN)
        if dealer_operate == OperateType.LANDLORD_SHA:
            await self.player_farmer_operate(player, OperateType.FARMER_SHA_XIN)

    async def player_farmer_operate(self, player, operate: int):
        """ 闲家操作 """
        if player.seat_id == self.dealer_id:
            return StaCode.FORBID, "操作有误，庄不能做闲的操作"
        if player.sp_status != OperateType.FARMER_LP:
            return StaCode.RULE_ERR, "闲操作有误，亮牌才有后续操作"
        dealer_operate = self.__records_dealer_op.get(player.seat_id)
        if not dealer_operate:
            return StaCode.NOT_YOUR_TURN, "操作有误，操作前必须等待庄操作"
        already_operate = self.__records_farmer_op.get(player.seat_id)
        if already_operate:
            return StaCode.ALREADY_DO, "已经操作过了"
        if dealer_operate == OperateType.LANDLORD_ZOU:
            if operate not in (OperateType.FARMER_ZOU_FAN, OperateType.FARMER_ZOU_XIN):
                return StaCode.RULE_ERR, "闲操作有误，亮牌庄走，闲只能杀反/信"
        if dealer_operate == OperateType.LANDLORD_SHA:
            if operate not in (OperateType.FARMER_SHA_FAN, OperateType.FARMER_SHA_XIN):
                return StaCode.RULE_ERR, "闲操作有误，亮牌庄杀，闲只能杀反/信"

        self.__operate_num += 1
        self.__records_farmer_op[player.seat_id] = operate

        operate_model = s2c_operate_model(player.seat_id, operate)
        await self.inner_broadcast(CmdRoom.FARMER_OPERATE, operate_model)

        if self.__operate_num == self.__real_count - 1:
            self.set_flow_status(FlowStatus.FLOW_IN_OPERATE_END)
            await self.round_over()

    @property
    def is_sa_pu_over(self):
        for p in self.seats:
            if p.sp_status == 0:
                return False
        return True

    async def round_over(self):
        """ 一局结束 """
        if not self.flow_status_is_equal(FlowStatus.FLOW_IN_OPERATE_END):
            self.info_log("round over err 庄闲没有操作完")
            return
        self.set_flow_status(FlowStatus.FLOW_IN_CHECK)
        result = self.compare_cards()
        await self.do_check_out(result)

        player_info = self.room_win_lose_data()
        data = {"check_infos": player_info}
        data_model = S2CRoundOver.pb_model(**data)
        await self.inner_broadcast(CmdRoom.ROUND_OVER, data_model)

        if self.has_next_round():
            pass
        else:
            await self.game_over()

    async def next_round_ready(self):
        self.set_room_status(RoomStatus.T_IDLE)  # 结束完又重置为空闲状态
        self.set_flow_status(FlowStatus.FLOW_IN_FREE)  # 结束完又重置为空闲状态
        await self.round_start()

    def get_sp_bei_lv(self, player):
        seat_id = player.seat_id
        if player.sp_status == OperateType.FARMER_QG:
            sp_bei_lv = OPERATE_RATE.get(OperateType.FARMER_QG)
        elif player.sp_status == OperateType.FARMER_MI:
            if self.__records_dealer_op.get(seat_id) == OperateType.LANDLORD_XIN:
                sp_bei_lv = OPERATE_RATE.get(OperateType.LANDLORD_XIN)
            else:
                sp_bei_lv = OPERATE_RATE.get(OperateType.LANDLORD_KAI)
        else:
            if self.__records_farmer_op.get(seat_id) == OperateType.FARMER_SHA_XIN:
                sp_bei_lv = OPERATE_RATE.get(OperateType.FARMER_SHA_XIN)
            elif self.__records_farmer_op.get(seat_id) == OperateType.FARMER_SHA_FAN:
                sp_bei_lv = OPERATE_RATE.get(OperateType.FARMER_SHA_FAN)
            else:
                sp_bei_lv = OPERATE_RATE.get(OperateType.FARMER_ZOU_FAN)
        return sp_bei_lv

    async def do_check_out(self, result: dict):
        """ 结算 """
        base_score = self.room_conf.get("base_score", 1)
        # 算分：撒扑倍率 * 下注倍率 * 场次倍率
        win_gold_info = {}
        lose_gold_info = {}  # 记录闲家输的
        for seat_id, res in result.items():
            if res == CompareRes.DRAW:
                continue
            player = self.get_player_by_seat_id(seat_id)
            sp_bei_lv = self.get_sp_bei_lv(player)

            score = sp_bei_lv * player.bet * base_score
            if res == CompareRes.LOSE:
                score = -score
                if score + player.gold < 0:
                    score = -player.gold
                lose_gold_info[seat_id] = score
            else:
                win_gold_info[seat_id] = score

        dealer = self.dealer()
        lose_gold = sum(lose_gold_info.values())
        win_gold = sum(win_gold_info.values())
        diff_gold = dealer.gold + abs(lose_gold) - win_gold
        self.info_log(dealer.uid, dealer.seat_id, "是否够赔付：", diff_gold)
        res_diff_gold = diff_gold  # 剩余的差额金币
        if diff_gold < 0:
            # 不够赔付时按赢家赔付 比例 递减
            for seat, gold in win_gold_info.items():
                rate_diff_gold = int(diff_gold * (gold / win_gold))
                gold += rate_diff_gold
                res_diff_gold -= rate_diff_gold
                win_gold_info[seat] = gold
            if res_diff_gold != 0:
                max_seat = max(win_gold_info, key=win_gold_info.get)
                win_gold_info[max_seat] = win_gold_info.get(max_seat, 0) + res_diff_gold

            win_gold = sum(win_gold_info.values())

        gold_info = {**lose_gold_info, **win_gold_info, dealer.seat_id: lose_gold + win_gold}
        await self.do_check_gold(gold_info, ReasonCostGold.CHECK_OUT_WATER_FISH)

    def compare_cards(self):
        """ 结算 """
        dealer = self.dealer()
        self.info_log("庄的牌：", dealer.cards)
        result = {}
        for p in self.seats:
            if p.seat_id == self.dealer_id:
                continue
            sp_status = p.sp_status
            op_enum = OperateType.find_member_by_val(sp_status)
            self.info_log(f"闲撒扑：{op_enum.phrase}, 牌：", p.cards)
            compare_num = 0
            if sp_status == OperateType.FARMER_QG:
                compare_num = 2
            elif sp_status == OperateType.FARMER_MI:
                if self.__records_dealer_op.get(p.seat_id) == OperateType.LANDLORD_KAI:
                    compare_num = 2
                else:
                    result[p.seat_id] = CompareRes.WIN
                    self.info_log("闲密庄信，庄输")
            elif sp_status == OperateType.FARMER_LP:
                if self.__records_dealer_op.get(p.seat_id) == OperateType.LANDLORD_SHA:
                    if self.__records_farmer_op.get(p.seat_id) == OperateType.FARMER_SHA_FAN:
                        compare_num = 1
                    # 庄赢
                    else:
                        result[p.seat_id] = CompareRes.LOSE
                        self.info_log("闲亮庄杀闲信，庄赢")
                else:
                    if self.__records_farmer_op.get(p.seat_id) == OperateType.FARMER_ZOU_FAN:
                        compare_num = 2
                    else:
                        result[p.seat_id] = CompareRes.DRAW
                        self.info_log("闲亮庄走闲走，平局")
            if compare_num > 0:
                res = Rule.compare(p.cards, dealer.cards, compare_num)
                if res:
                    result[p.seat_id] = CompareRes.WIN
                    self.info_log(f"闲比庄，比{compare_num}铺", "闲赢")
                else:
                    result[p.seat_id] = CompareRes.LOSE
                    self.info_log(f"闲比庄，比{compare_num}铺", "庄赢")
        return result

    async def round_start(self):
        """ 一局开始 """
        self.set_flow_status(FlowStatus.FLOW_IN_READY)
        await self.inner_broadcast(CmdRoom.ROUND_START)

        self.round_start_before()
        await self.start_confirm_dealer()

    def round_start_before(self):
        """ 开始前重置数据 """
        self.__real_count = self.in_room_count  # 游戏开始计算此次游戏人数
        self.clear_room_round_data()
        self.clear_player_round_data()

    def clear_room_round_data(self):
        """ 清除房间一局数据 """
        self.__records_dealer_op.clear()  # 记录庄家的操作
        self.__records_farmer_op.clear()  # 记录闲家的操作
        self.__operate_num: int = 0  # 双方都操作完计数1次

    def clear_player_round_data(self):
        """ 清除玩家一局数据 """
        for p in self.seats:
            if p:
                p.clear_round_data()

    @staticmethod
    def serialize_player_info(room_player_info):
        """ 序列化玩家信息 """
        print("序列化玩家信息: ", room_player_info)
        S2CPlayerInfo04WaterFish.pb_model(room_player_info)

    @staticmethod
    def serialize_room_info(room_info):
        """ 序列化房间信息 """
        print("序列化房间信息: ", room_info)
        S2CRoomInfo03WaterFish.pb_model(**room_info)

    def room_info(self):
        """ 子类重写该方法 """
        data = super().room_info()
        data["dealer_op"] = self.__records_dealer_op
        data["farmer_op"] = self.__records_dealer_op
        return data

    @staticmethod
    def get_player_info(player):
        info = player.player_info()
        info["sp_status"] = player.sp_status
        return info
