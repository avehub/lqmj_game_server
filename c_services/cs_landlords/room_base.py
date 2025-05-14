import random

from nsanic.libs.tool import json_encode

from common.proto.py_pb2.ws_leisure import bid_model, do_bid_model, confirm_dealer_model, \
    S2CTurnTOLandlords, redouble_model, do_redouble_model, play_cards_model, S2CRoundOverLandlords, \
    S2CPlayerInfo04Landlords, S2CRoomInfo03Landlords
from .rule import Rule
from common.public.enum_const import StaCode, ServiceEnum, TaskId, PlayType
from .const import FlowStatus, ActionType
from .poker import Poker, Cards
from c_services.base.base_leisure_room import BaseLeisureRoom
from ..const.cs_enum_const import RoomStatus, CmdRoom, CmdRobotMethods
from promising_game.const import ReasonCostGold


class Room(BaseLeisureRoom):
    """ 斗地主房间类，专注玩法实现 """

    def __init__(self, tid, service, room_conf):
        super().__init__(tid, service, room_conf, Poker)
        self.__bid_list = room_conf.get("rule_conf", {}).get("bid_list") or [0, 1, 2, 3]
        self.__allow_act = room_conf.get("rule_conf", {}).get("allow_act")
        self.__max_bid_score = 0  # 记录最大叫分
        self.__max_bid_seat = 0  # 记录最大叫分玩家
        self.__max_bid_count = 3  # 最多叫分几次
        self.__bid_count = 0  # 记录当前叫了几次分
        self.__dealer_cards = []  # 地主牌
        self.__table_cards = []  # 所有桌牌
        self.__newest_table_cards = self.init_newest_table_cards()  # 最新三个桌牌
        self.__multiple = 1  # 倍数
        self.__header_redouble_seat = 0  # 叫铲玩家
        self.__is_redouble = False  # 是否铲过
        self.__header_re_redouble_seat = 0  # 反铲玩家
        self.__is_re_redouble = False  # 是否反铲过
        self.__yao_de_qi = False  # 记录turn to时是否要得起

        # todo: 封装斗地主机器人模型请求参数
        self.__position_maps = {}
        self.__action_history = []
        self.__last_move_dict = {"landlord_up": [], "landlord": [], "landlord_down": []}  # 三个玩家最新的action
        self.__played_cards_dict = {"landlord_up": [], "landlord": [], "landlord_down": []}  # 三位玩家出过的牌
        self.__bomb_num = 0

    @staticmethod
    def init_newest_table_cards():
        return [
            {
                "seat_id": 1,
                "cards": []
            },
            {
                "seat_id": 2,
                "cards": []
            },
            {
                "seat_id": 3,
                "cards": []
            },
        ]

    async def round_start(self, **kwargs):
        """ 一局开始 """
        await super().round_start()
        await self.delay_func(1, self.deal_cards)

    async def deal_cards(self):
        """ 发牌 """
        if not self.flow_status_is_equal(FlowStatus.F_IN_IDLE):
            self.info_log(f"flow error: {self.flow_status}")
            return
        self.info_log("开始发牌")
        self.set_flow_status(FlowStatus.F_IN_DEAL_CARDS)
        self.set_room_status(RoomStatus.T_PLAYING)
        all_cards = self.poker.deal_cards(self.max_player_count)
        await super().do_deal_cards(all_cards)

        self.curr_seat_id = random.randint(1, self.max_player_count)
        await self.delay_func(4, self.start_bid)

    async def start_bid(self):
        """ 开始叫分 """
        self.set_flow_status(FlowStatus.F_IN_BID)
        self.info_log("开始叫分", self.curr_seat_id)
        await self.inner_broadcast(CmdRoom.START_BID)
        await self.turn_bid(True)

    async def re_deal_cards(self):
        """ 重新发牌 """
        for p in self.seats:
            p.bid_score = -1
        self.set_flow_status(FlowStatus.F_IN_IDLE)
        return await self.deal_cards()

    async def turn_bid(self, is_first=False):
        """ 叫分turn """
        if is_first:
            player = self.curr_player()
        else:
            if self.__max_bid_score == self.__bid_list[-1]:
                # 走到了最高叫分 则进入加倍
                return await self.start_redouble()

            player = self.next_player(self.curr_seat_id, False)
            if player.bid_score != -1:
                # 都叫过分了
                if self.__max_bid_score == 0:
                    # 都不要则重新发牌
                    self.__bid_count += 1
                    if self.__bid_count < self.__max_bid_count:
                        self.info_log("都未叫分，进入重新发牌", self.__bid_count)
                        return await self.re_deal_cards()

                if self.play_type == PlayType.CLASSICAL:  # 全国玩法确定地主后加倍
                    return await self.start_redouble()

                await self.confirm_dealer()
                return await self.delay_func(1, self.turn_start)

            self.curr_seat_id = player.seat_id

        if player.is_robot:
            # todo: 机器人叫分
            self.call_flow_robot(2, self.robot_auto_bid, player)

        wait_sec = 10

        bid_model.seconds = wait_sec
        bid_model.seat_id = self.curr_seat_id
        bid_model.bid_list.extend(self.__bid_list)
        await self.inner_broadcast(CmdRoom.TURN_BID, bid_model)
        bid_model.bid_list[:] = []  # 清空列表

        trustee = False
        if player.trustee:
            wait_sec = 1
            trustee = True

        self.call_flow(wait_sec, self.time_out_bid, player, trustee)

    async def time_out_bid(self, player, trustee=False):
        """ 超时叫分 """
        if not self.flow_status_is_equal(FlowStatus.F_IN_BID):
            return
        if player.seat_id != self.curr_seat_id:
            return
        not trustee and await self.do_trustee(player, True)
        code, msg = await self.player_bid(player, 0)
        self.info_log(player.uid, player.seat_id, "超时叫分：", code, msg, trustee)
        if code == StaCode.PASS:
            await self.turn_bid()

    async def start_redouble(self):
        """ 开始加倍 """  # todo: 每个玩家都能加倍？
        self.set_flow_status(FlowStatus.F_IN_REDOUBLE)
        self.__header_redouble_seat = self.curr_seat_id
        self.info_log("开始铲", self.__header_redouble_seat)
        await self.inner_broadcast(CmdRoom.START_REDOUBLE)

        await self.turn_redouble()

    async def turn_redouble(self):
        player = self.next_player(self.curr_seat_id, False)
        if self.__header_redouble_seat == player.seat_id:
            await self.confirm_dealer()
            return await self.delay_func(1, self.turn_start)

        self.info_log(player.uid, player.seat_id, "轮到玩家铲")
        self.curr_seat_id = player.seat_id
        wait_sec = 10

        redouble_model.seat_id = player.seat_id
        redouble_model.seconds = wait_sec
        await self.inner_broadcast(CmdRoom.TURN_REDOUBLE, redouble_model)

        if player.is_robot:
            self.call_flow_robot(3, self.robot_auto_chan, player)

        trustee = False
        if player.trustee:
            wait_sec = 1
            trustee = True

        self.call_flow(wait_sec, self.time_out_redouble, player, trustee)

    async def time_out_redouble(self, player, trustee=False):
        """ 超时铲 """
        if not self.in_flow_status(FlowStatus.F_IN_REDOUBLE, FlowStatus.F_IN_RE_REDOUBLE):
            return
        if player.seat_id != self.curr_seat_id:
            return
        not trustee and await self.do_trustee(player, True)
        code, msg = await self.player_redouble(player, 0)
        self.info_log(player.uid, player.seat_id, "超时铲：", code, msg)
        if code == StaCode.PASS:
            await self.turn_redouble()

    async def start_re_redouble(self):
        """ 开始反铲 """
        self.set_flow_status(FlowStatus.F_IN_RE_REDOUBLE)
        self.info_log("开始反铲")
        self.__header_re_redouble_seat = self.curr_seat_id
        await self.inner_broadcast(CmdRoom.START_RE_REDOUBLE, redouble_model)
        await self.turn_re_redouble()

    async def turn_re_redouble(self):
        """ 反铲turn """
        player = self.next_player(self.curr_seat_id, False)
        if self.__header_re_redouble_seat == player.seat_id:
            # 无人反铲时则叫铲的玩家为地主
            await self.confirm_dealer()
            return await self.delay_func(1, self.turn_start)

        self.info_log(player.uid, player.seat_id, "轮到玩家反铲")
        self.curr_seat_id = player.seat_id
        wait_sec = 10
        redouble_model.seat_id = player.seat_id
        redouble_model.seconds = wait_sec
        await self.inner_broadcast(CmdRoom.TURN_RE_REDOUBLE, redouble_model)

        if player.is_robot:
            # self.call_flow_robot(0, self.robot_re_redouble, player)
            self.call_flow_robot(3, self.robot_auto_chan, player, CmdRobotMethods.CAL_RE_CHAN)

        trustee = False
        if player.trustee:
            wait_sec = 1
            trustee = True

        self.call_flow(wait_sec, self.time_out_re_redouble, player, trustee)

    async def time_out_re_redouble(self, player, trustee=False):
        """ 超时反铲 """
        if not self.flow_status_is_equal(FlowStatus.F_IN_RE_REDOUBLE):
            return
        if player.seat_id != self.curr_seat_id:
            return
        not trustee and await self.do_trustee(player, True)
        code, msg = await self.player_re_redouble(player, 0)
        self.info_log(player.uid, player.seat_id, "超时反铲：", code, msg)
        if code == StaCode.PASS:
            await self.turn_re_redouble()

    def achieve_call_landlord(self, uid):
        """ 完成叫地主 """
        data = {
            "task_id": TaskId.ROB_LANDLORD_3,
            "add_val": 1,
            "uid": uid
        }
        self.add_task(data)

    def play_three_bomb(self, uid):
        data = {
            "task_id": TaskId.PLAY_THREE_BOMB,
            "add_val": 1,
            "uid": uid,
        }
        self.add_task(data)

    async def confirm_dealer(self, dealer_id=0):
        """ 确定庄家 """
        self.set_flow_status(FlowStatus.F_IN_CONFIRM_DEALER)

        dealer_id = dealer_id or self.__max_bid_seat or self.curr_seat_id
        self.dealer_id = dealer_id

        dealer = self.dealer()
        if not dealer.is_robot:
            self.achieve_call_landlord(dealer.uid)

        # 补牌
        self.__dealer_cards = []
        for _ in range(3):
            card = self.poker.pop()
            dealer.rev_card(card)
            self.__dealer_cards.append(card)

        self.info_log("开始定庄", dealer_id, self.__dealer_cards)

        # 通知地主
        confirm_dealer_model.seat_id = self.dealer_id
        confirm_dealer_model.dealer_cards.extend(self.__dealer_cards)

        # 设置本局玩家位置映射
        self.set_position_maps()
        await self.inner_broadcast(CmdRoom.CONFIRM_DEALER, confirm_dealer_model)
        confirm_dealer_model.dealer_cards[:] = []  # 清空列表

    def set_position_maps(self):
        """
        设置位置映射
        """
        position_maps = {
            1: {1: "landlord", 2: "landlord_down", 3: "landlord_up"},
            2: {1: "landlord_up", 2: "landlord", 3: "landlord_down"},
            3: {1: "landlord_down", 2: "landlord_up", 3: "landlord"}
        }
        self.__position_maps = position_maps.get(self.dealer_id)

    async def turn_start(self, flow=FlowStatus.F_IN_CONFIRM_DEALER):
        """ 首出 """
        if not self.in_flow_status(flow, ):
            return
        self.info_log("turn_start")
        self.set_flow_status(FlowStatus.F_IN_TURN_TO)
        turn_player = self.dealer()
        await self.turn_to_someone(turn_player)

    async def turn_next(self):
        if self.__table_cards and not Rule.get_last_action(self.__table_cards):
            await self.inner_broadcast(CmdRoom.TURN_END)
        await self.turn_to_someone(self.next_player(self.curr_seat_id))

    async def turn_to_someone(self, player):
        """ 轮到某人 """
        self.curr_seat_id = player.seat_id
        yao_de_qi = True
        legal_actions = []

        if not player.is_robot and self.__table_cards:
            legal_actions = Rule.get_legal_card_play_actions(player.cards, self.__table_cards, self.__allow_act)
            if len(legal_actions) == 1 and not legal_actions[-1]:
                yao_de_qi = False
                legal_actions = []
            else:
                legal_actions.pop()

        wait_sec = 15

        self.__yao_de_qi = yao_de_qi
        notify_data = {
            "seat_id": player.seat_id,
            "seconds": wait_sec,
            "yao_de_qi": yao_de_qi,
        }
        data_model = S2CTurnTOLandlords.pb_model(**notify_data)
        await self.inner_broadcast(CmdRoom.TURN_TO, data_model, exclude_uid=player.uid)
        if legal_actions:
            data_model.legal_actions = json_encode(legal_actions)
        if not yao_de_qi:
            data_model.seconds = 5
        await self.inner_send(player, CmdRoom.TURN_TO, data_model)

        self.info_log("轮到某人", player.uid, self.curr_seat_id, yao_de_qi)

        if not yao_de_qi:
            wait_sec = 5
            if player.is_robot:
                wait_sec = random.randint(1, 3)  # 机器人随机时间要不起
            self.call_flow(wait_sec, self.do_play_cards, player, [])
            return

        if not Rule.get_last_action(self.__table_cards):
            if Rule.one_hand_play_out(player.cards, self.__allow_act):
                return await self.delay_func(0.5, self.do_play_cards, player, player.cards)

        if player.is_robot:
            self.call_flow_robot(2, self.robot_auto_play_cards, player)

        is_trustee = False
        if player.trustee:
            wait_sec = 2
            is_trustee = True

        self.call_flow(wait_sec, self.time_out_play_card, player, is_trustee)

    async def robot_auto_chan(self, curr_p, cmd=CmdRobotMethods.CAL_CHAN):
        """
        机器人自动铲/反铲
        """
        # 模型请求ID: 桌子号+玩家UID
        req_model_id = "".join([str(curr_p.tid), str(curr_p.uid)])
        state = {
            "cards": curr_p.cards,
            "req_model_id": req_model_id,
            "cmd": cmd,
        }
        # 使用rmq推送机器人预测铲/反铲
        self.info_log("推送斗地主机器人[铲/反铲]: ", req_model_id, cmd)
        await self.cs2cs_by_rmq(
            cs_type=ServiceEnum.ROBOT_LANDLORDS,
            c_code=cmd,
            uid=curr_p.uid,
            msg=state
        )

    async def robot_auto_bid(self, curr_p):
        """
        机器人自动叫分
        """
        # 模型请求ID: 桌子号+玩家UID
        max_bid = self.__max_bid_score
        max_score = self.__bid_list[-1]
        max_bid_list = list(range(max_bid + 1, max_score + 1))
        req_model_id = "".join([str(curr_p.tid), str(curr_p.uid)])
        state = {
            "cards": curr_p.cards,
            "can_bids": self.__bid_list[1:] if not max_bid else max_bid_list,
            "is_bxp": False,
            "req_model_id": req_model_id,
            "cmd": CmdRobotMethods.CAL_BID.val,
        }
        # 使用rmq推送机器人预测叫分
        self.info_log("推送斗地主机器人[叫分]: ", req_model_id)
        await self.cs2cs_by_rmq(
            cs_type=ServiceEnum.ROBOT_LANDLORDS,
            c_code=CmdRobotMethods.CAL_BID.val,
            uid=curr_p.uid,
            msg=state
        )

    async def robot_auto_play_cards(self, curr_p):
        """
        机器人自动出牌
        """
        # 处理手牌异常
        if not curr_p.cards:
            self.info_log(curr_p.seat_id, curr_p.cards, "No cards")
            return
        # 模型请求ID: 桌子号+玩家UID
        req_model_id = "".join([str(curr_p.tid), str(curr_p.uid)])
        state = {
            "tid": curr_p.tid,
            "position": curr_p.seat_id - 1,
            "dealer_id": self.dealer_id,
            "bomb_num": self.__bomb_num,
            "player_hand_cards": curr_p.cards,
            "action_seq": self.__action_history,
            "cards_left_dict": self.get_cards_left_dict(),
            "played_cards": self.__played_cards_dict,
            "last_move_dict": self.__last_move_dict,
            "is_bxp": False,
            "req_model_id": req_model_id,
            "allow_act": self.__allow_act,
            "cmd": CmdRobotMethods.CAL_ACTION.val,
        }
        # 使用rmq推送机器人预测叫分
        self.info_log("推送斗地主机器人[出牌]: ", req_model_id)
        await self.cs2cs_by_rmq(
            cs_type=ServiceEnum.ROBOT_LANDLORDS,
            c_code=CmdRobotMethods.CAL_ACTION.val,
            uid=curr_p.uid,
            msg=state
        )

    def get_cards_left_dict(self):
        """
        获取剩余的牌
        """
        cards_left_dict = {}
        for other_p in self.seats:
            if not other_p:
                continue
            cards_left_dict[self.__position_maps.get(other_p.seat_id)] = len(other_p.cards)
        return cards_left_dict

    async def time_out_play_card(self, player, trustee=False):
        """ 超时出牌 """
        self.info_log(player.uid, player.seat_id, "超时出牌：", trustee, self.flow_status)
        if not self.flow_status_is_equal(FlowStatus.F_IN_TURN_TO):
            return
        if player.seat_id != self.curr_seat_id:
            return
        not trustee and await self.do_trustee(player, True)
        await self.play_card_by_rand(player)

    async def play_card_by_rand(self, player):
        """ 随机出一张牌 """
        legal_cards = Rule.get_legal_card_play_actions(player.cards, self.__table_cards, self.__allow_act)
        rand_move = random.choice(legal_cards)
        cards = []
        if rand_move:
            rand_move = Rule.get_cards_by_val_list(player.cards, [rand_move])
            cards = rand_move[0]

        # 具体出牌
        await self.do_play_cards(player, cards)

    async def do_play_cards(self, player, cards: list):
        code, msg = await self.player_play_cards(player, cards)
        self.info_log(player.uid, player.seat_id, "do_play_cards 返回", code, msg)
        if code == StaCode.PASS:
            if not player.cards:
                return await self.delay_func(1, self.round_over)
            return await self.turn_next()

    async def do_check_out(self, curr_player):
        """ 结算 """
        base_score = self.room_conf.get("base_score", 1)
        score = base_score * self.__multiple
        gold_info = {}
        if curr_player.seat_id == self.dealer_id:
            # 庄家赢
            win_score = 0
            for p in self.seats:
                if p.seat_id == self.dealer_id:
                    continue
                p_score = -score * p.self_multiple
                if p.gold + p_score < 0:
                    p_score = -p.gold
                gold_info[p.seat_id] = p_score
                win_score += p_score * -1
            gold_info[self.dealer_id] = win_score
        else:
            # 地主输
            farmer_win_info = {}
            for p in self.seats:
                if p.seat_id == self.dealer_id:
                    continue
                farmer_win_info[p.seat_id] = score * p.self_multiple

            farmer_win = sum(farmer_win_info.values())
            landlord_lose = -farmer_win

            dealer = self.dealer()
            if dealer.gold + landlord_lose < 0:
                landlord_lose = -dealer.gold  # 地主最多能输

            # 如果地主足够赔付
            if farmer_win + landlord_lose == 0:
                gold_info.update(farmer_win_info)
            else:
                # 按比例赔付
                for seat, score in farmer_win_info.items():
                    per_farmer_win = -int((landlord_lose * (score / farmer_win)))  # +
                    gold_info[seat] = per_farmer_win

                diff_gold = sum(gold_info.values()) + landlord_lose  # 差额分
                if diff_gold != 0:
                    max_win_seat = min(gold_info, key=gold_info.get)
                    gold_info[max_win_seat] -= diff_gold

            gold_info[self.dealer_id] = landlord_lose

        await self.do_check_gold(gold_info, ReasonCostGold.CHECK_OUT_LANDLORDS)

    def is_spring(self) -> bool:
        """ 是否是春天 """
        for player in self.seats:
            if player.seat_id == self.dealer_id:
                continue
            if player.play_count > 0:
                return False
        self.__multiple *= 2
        return True

    def is_re_spring(self) -> bool:
        """ 是否是反春天 """
        dealer = self.dealer()
        if dealer.play_count == 1:
            self.__multiple *= 2
            return True
        return False

    async def round_over(self):
        """ 一局结束 """
        self.set_room_status(RoomStatus.T_CHECK_OUT)
        self.set_flow_status(FlowStatus.F_IN_CHECK_OUT)

        curr_player = self.curr_player()
        self.info_log(
            "round_over", self.dealer_id, "赢家：", curr_player.uid, curr_player.seat_id, self.__table_cards)
        await self.do_check_out(curr_player)
        player_info = self.room_win_lose_data()
        hand_cards = []
        for player in self.seats:
            if player.seat_id == curr_player.seat_id:
                continue
            hand_cards.append({"seat_id": player.seat_id, "cards": player.cards})

        data = {
            "check_infos": player_info,
            "hand_cards": hand_cards,
            "is_spring": self.is_spring(),
            "is_re_spring": self.is_re_spring(),
            "multiple": self.__multiple,
            "bomb_num": self.__bomb_num,
        }
        data_model = S2CRoundOverLandlords.pb_model(**data)
        await self.inner_broadcast(CmdRoom.ROUND_OVER, data_model)

        await super().round_over()

    async def player_bid(self, player, bid_score):
        """ 玩家叫分 """
        if not self.flow_status_is_equal(FlowStatus.F_IN_BID):
            return StaCode.FLOW_ERR, "桌子状态非游戏中"
        if player.seat_id != self.curr_seat_id:
            return StaCode.NOT_YOUR_TURN, "未轮到你"
        if player.bid_score != -1:
            return StaCode.ALREADY_DO, "已叫过分"
        if bid_score not in self.__bid_list:
            return StaCode.RULE_ERR, "叫分错误"
        if bid_score != 0 and bid_score <= self.__max_bid_score:
            return StaCode.RULE_ERR, "叫分不能比之前的低"

        player.bid_score = bid_score

        if bid_score != 0:
            self.__multiple = bid_score
            self.__max_bid_score = bid_score
            self.__max_bid_seat = player.seat_id

        self.info_log(player.uid, "完成叫分: ", bid_score)

        do_bid_model.seat_id = player.seat_id
        do_bid_model.bid_score = bid_score
        await self.inner_broadcast(CmdRoom.DO_BID, do_bid_model)

        return StaCode.PASS, ""

    async def player_redouble(self, player, score, flow=FlowStatus.F_IN_REDOUBLE, cmd=CmdRoom.DO_REDOUBLE):
        """ 玩家加倍 """
        if not self.flow_status_is_equal(flow):
            return StaCode.FORBID, "非铲中"
        if self.__is_redouble:
            return StaCode.FORBID, "已经铲过"
        if player.seat_id != self.curr_seat_id:
            return StaCode.NOT_YOUR_TURN, "未轮到你"
        if score > 0:
            self.__multiple *= 2
            self.__is_redouble = True

        self.info_log(player.uid, "铲完成: ", score)

        do_redouble_model.seat_id = player.seat_id
        do_redouble_model.score = score
        do_redouble_model.multiple = self.__multiple

        await self.inner_broadcast(cmd, do_redouble_model)
        if score:  # 进入反铲
            await self.start_re_redouble()
        else:
            await self.turn_redouble()

        return StaCode.PASS, ""

    async def player_re_redouble(self, player, score):
        """ 玩家加加倍 """
        if not self.flow_status_is_equal(FlowStatus.F_IN_RE_REDOUBLE):
            return StaCode.FORBID, "非反铲中"
        if self.__is_re_redouble:
            return StaCode.FORBID, "已经反铲过"
        if player.seat_id != self.curr_seat_id:
            return StaCode.NOT_YOUR_TURN, "未轮到你"
        if score > 0:
            self.__multiple *= 2
            self.__is_re_redouble = True

        self.info_log(player.uid, "反铲完成: ", score)

        do_redouble_model.seat_id = player.seat_id
        do_redouble_model.score = score
        do_redouble_model.multiple = self.__multiple

        await self.inner_broadcast(CmdRoom.DO_RE_REDOUBLE, do_redouble_model)
        return StaCode.PASS, ""

    async def player_play_cards(self, player, cards):
        """ 玩家打牌 """
        if not self.room_status_is_equal(RoomStatus.T_PLAYING):
            return StaCode.FORBID, "桌子状态非游戏中"
        if not self.flow_status_is_equal(FlowStatus.F_IN_TURN_TO):
            return StaCode.FORBID, "现在还不能出牌"
        if player.seat_id != self.curr_seat_id:
            return StaCode.NOT_YOUR_TURN, "未轮到你"
        last_action = Rule.get_last_action(self.__table_cards)
        if not last_action and not cards:
            return StaCode.ERR_ARG, "首出不能不要"

        if not Rule.contain(player.cards, cards):
            return StaCode.ERR_ARG, "出的牌手里没有"

        act_type = ActionType.TYPE_0_PASS
        if cards:
            cards = [Cards.find_member_by_val(c) for c in cards]
            cards.sort(key=Rule.sort_rule)
            is_legal, move_info = Rule.is_legal_action(cards, last_action, self.__allow_act)
            if not is_legal:
                return StaCode.RULE_ERR, "出牌不符合规则"

            act_type = move_info['type']
            if act_type in [ActionType.TYPE_4_BOMB, ActionType.TYPE_5_KING_BOMB]:
                self.__bomb_num += 1
                self.__multiple *= 2
                if not player.is_robot:
                    self.play_three_bomb(player.uid)

            player.rm_cards(cards)

        self.info_log(player.uid, "出牌完成: ", cards)

        # todo: 记录AI使用参数
        # 清空上一个操作，用于记录最新的
        cards_val = [card.val for card in cards]
        position = self.__position_maps.get(player.seat_id)
        self.__played_cards_dict[position].extend(cards_val)
        self.__last_move_dict[position].clear()
        self.__last_move_dict[position].extend(cards_val)
        self.__action_history.append(cards_val)

        # 桌子参数
        self.__table_cards.append(cards)
        self.__newest_table_cards[player.seat_id - 1]["cards"] = cards

        play_cards_model.seat_id = player.seat_id
        play_cards_model.cards_len = len(player.cards)
        play_cards_model.act_type = act_type
        play_cards_model.multiple = self.__multiple
        play_cards_model.cards.extend(cards)
        await self.inner_broadcast(CmdRoom.PLAY_CARDS, play_cards_model)
        play_cards_model.cards[:] = []  # 清空数据

        return StaCode.PASS, ''

    @staticmethod
    def serialize_player_info(room_player_info):
        return S2CPlayerInfo04Landlords.pb_model(room_player_info)

    @staticmethod
    def serialize_room_info(room_info):
        """ 子类实现 """
        return S2CRoomInfo03Landlords.pb_model(**room_info)

    def room_info(self):
        """ 子类重写该方法 """
        data = super().room_info()
        curr_player = self.curr_player()
        if (curr_player and not curr_player.is_robot and
                self.flow_status_is_equal(FlowStatus.F_IN_TURN_TO) and self.left_seconds() > 0):
            data["yao_de_qi"] = self.__yao_de_qi

        data["dealer_cards"] = self.__dealer_cards
        newest_table_cards = []
        for cards_info in self.__newest_table_cards:
            newest_table_cards.append(cards_info)
        data["table_cards"] = newest_table_cards
        data["multiple"] = self.__multiple  # 倍数
        data["is_redouble"] = self.__is_redouble  # 铲
        data["is_re_redouble"] = self.__is_re_redouble  # 反铲
        return data

    def get_player_info(self, player):
        info = player.player_info()
        info["bid_score"] = player.bid_score
        info["multiple"] = player.self_multiple
        return info
