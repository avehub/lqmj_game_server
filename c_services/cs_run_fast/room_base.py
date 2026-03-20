import random
from collections import Counter

from nsanic.libs.tool import json_encode

from common.proto.py_pb2.ws_leisure import S2CReady07Mahjong, S2CDealCardsRunFast, S2CStartQiangGuan, \
    S2CQiangGuanRunFast, \
    S2CDoDoubleRunFast, S2CPlayCardsRunFast, S2CRoundOverInfoRunFast, S2CBombScoreRunFast, S2CRoomInfoRunFast, S2CPlayerInfoRunFast, \
    S2CEarlyShowCardRunFast, S2CRoundStartRunFast, s2c_one_of_model, S2CTurnToRunFast
from .player import Player
from .rule import RunFastRule
from common.public.enum_const import StaCode, ServiceEnum
from .const import FlowStatus, FirstPlayType
from .poker import Poker, Cards
from ..base.base_card_room import BaseCardRoom
from ..const.cs_enum_const import RoomStatus, CmdRoom
from ..cs_landlords.const import ActionType
from ..cs_mahjong.const import OverType


class Room(BaseCardRoom):
    """跑得快房间类 """

    def __init__(self, tid, service, room_conf):
        super().__init__(tid, service, room_conf, Poker)
        self.__table_cards = []  # 所有桌牌
        self.__newest_table_cards = self.init_newest_table_cards(self.max_player_count)  # 最新桌牌信息
        self.__yao_de_qi = False  # 记录turn to时是否要得起

        # todo: 封装斗地主机器人模型请求参数
        self.__position_maps = {}
        self.__last_move_dict = {"landlord_up": [], "landlord": [], "landlord_down": []}  # 三个玩家最新的action
        self.__played_cards_dict = {"landlord_up": [], "landlord": [], "landlord_down": []}  # 三位玩家出过的牌

        self.__winner_id = 0  # 记录赢家
        self.__last_dealer_id = 0  # 记录上一个庄家
        self.__card_count = self.rule_detail.get("card_count", 16)  # 手牌数
        self.__can_pass = self.rule_detail.get("can_pass", 0)  # 是否可以过牌
        self.__first_play_type = self.rule_detail.get("first_play_type", FirstPlayType.HT_3)  # 第一回合出牌类型
        self.__bomb_score = self.rule_detail.get("bomb_score", 5)  # 炸弹分数
        self.__is_double = self.rule_detail.get("is_double", 0)  # 是否加倍
        self.__is_qiang_guan = self.rule_detail.get("is_qiang_guan", 0)  # 是否抢关
        self.__is_fan_guan = self.rule_detail.get("is_fan_guan", 0)  # 是否反关
        self.__three_need_first = self.rule_detail.get("three_need_first", 0)  # 开门见三
        self.__can_four_with_three = self.rule_detail.get("can_four_with_three", 0)  # 四带三是否可以
        self.__three_A_is_bomb = self.rule_detail.get("three_A_is_bomb", 0)  # 三带A是否可以当炸弹
        self.__drift = self.rule_detail.get("drift", 0)  # 是否甩尾
        self.__early_show_cards = self.rule_detail.get("early_show_cards", 0)  # 提前亮牌
        self.__call_one_must_big = self.rule_detail.get("call_one_must_big", 0)  # 报单必大
        self.__show_cards_num = self.rule_detail.get("show_cards_num", 0)  # 展示牌数
        self.__card_tracker = self.rule_detail.get("card_tracker", 0)  # 记牌器

        self.__allow_act = {"0": True, "1": True, "2": True, "4": True,
                            "7": True, "8": True, "9": True, "12": True,
                            "13": True, "16": True, }

        if self.__is_qiang_guan:
            self.__three_need_first = False

        if self.__three_A_is_bomb:
            self.__allow_act[ActionType.TYPE_17_THREE_A_IS_BOMB.desc] = True

        if self.__can_four_with_three:
            self.__allow_act[ActionType.TYPE_18_4_3.desc] = True

        if self.__drift:
            self.__allow_act[ActionType.TYPE_19_SERIAL_3_2_DRIFT.desc] = True
            self.__allow_act[ActionType.TYPE_20_3_2_DRIFT.desc] = True
            self.__allow_act[ActionType.TYPE_21_4_2_DRIFT.desc] = True
            self.__allow_act[ActionType.TYPE_22_4_3_DRIFT.desc] = True

        self.__qiang_guan_win = False  # 记录抢关是否成功
        self.__has_qiang_guan = False  # 记录是否有玩家抢关
        self.__has_bao_pei = False  # 记录是否有玩家包赔

    @staticmethod
    def init_newest_table_cards(player_count=3):
        return [
            {
                "seat_id": seat_id,
                "cards": []
            }
            for seat_id in range(1, player_count + 1)
        ]

    @property
    def qiang_guan_win(self):
        return self.__qiang_guan_win

    @qiang_guan_win.setter
    def qiang_guan_win(self, value):
        self.__qiang_guan_win = value

    @property
    def has_qiang_guan(self):
        return self.__has_qiang_guan

    @property
    def has_bao_pei(self):
        return self.__has_bao_pei

    @has_bao_pei.setter
    def has_bao_pei(self, value):
        self.__has_bao_pei = value

    async def round_start(self, **kwargs):
        """ 一局开始 """
        await super().round_start()
        self.set_flow_status(FlowStatus.F_IN_IDLE)
        data = {"round_idx": self.round_idx}
        data_model = S2CRoundStartRunFast.pb_model(**data)
        await self.inner_broadcast(CmdRoom.ROUND_START, data_model)
        await self.delay_func(1, self.deal_cards)

    async def deal_cards(self):
        """ 发牌 """
        if not self.flow_status_is_equal(FlowStatus.F_IN_IDLE):
            self.log_info(f"flow error: {self.flow_status}")
            return
        self.log_info("开始发牌")
        self.set_flow_status(FlowStatus.F_IN_DEAL_CARDS)
        self.set_room_status(RoomStatus.T_PLAYING)
        all_cards = self.poker.deal_cards(self.max_player_count, self.__card_count)
        if self.__first_play_type == FirstPlayType.HT_3:
            has_ht3 = False
            for cards in all_cards:
                if Cards.HT_3 in cards:
                    has_ht3 = True
                    break
            if not has_ht3:
                target_player_idx = random.randint(0, self.max_player_count - 1)
                # 随机选择该玩家手牌中的一张牌
                target_card_idx = random.randint(0, len(all_cards[target_player_idx]) - 1)
                # 将选中的牌替换为黑桃3
                all_cards[target_player_idx][target_card_idx] = Cards.HT_3
                self.log_info(f"随机替换玩家 {target_player_idx + 1} 的牌为黑桃3")
        elif self.__first_play_type == FirstPlayType.HX_3:
            has_hx3 = False
            for cards in all_cards:
                if Cards.HX_3 in cards:
                    has_hx3 = True
                    break
            if not has_hx3:
                target_player_idx = random.randint(0, self.max_player_count - 1)
                # 随机选择该玩家手牌中的一张牌
                target_card_idx = random.randint(0, len(all_cards[target_player_idx]) - 1)
                # 将选中的牌替换为红桃3
                all_cards[target_player_idx][target_card_idx] = Cards.HX_3
                self.log_info(f"随机替换玩家 {target_player_idx + 1} 的牌为红桃3")

        data = {}
        dealer_id = 0
        for i, p in enumerate(self.seats):
            p.cards = all_cards[i]
            data["hand_cards"] = p.cards
            p.sort_cards()
            data["seat_id"] = p.seat_id
            if dealer_id == 0:
                if self.__first_play_type == FirstPlayType.HT_3 and Cards.HT_3 in all_cards[i]:
                    dealer_id = p.seat_id
                    p.is_header = True
                    print(f"玩家 {p.seat_id} 有黑桃3，成为头家{p.is_header}")
                elif self.__first_play_type == FirstPlayType.HX_3 and Cards.HX_3 in all_cards[i]:
                    dealer_id = p.seat_id
                    p.is_header = True
                elif self.__first_play_type == FirstPlayType.LAST_ROUND_WIN and self.__winner_id == p.seat_id:
                    dealer_id = p.seat_id
                    p.is_header = True
                else:
                    if self.__last_dealer_id == 0:
                        self.__last_dealer_id = 1
                    dealer_id = self.get_next_dealer_seat_id(self.__last_dealer_id)
            data["dealer_id"] = dealer_id
            self.__last_dealer_id = dealer_id
            data_model = S2CDealCardsRunFast.pb_model(**data)
            await self.inner_send(p, CmdRoom.DEALER_CARDS, data_model)
            self.log_info(f"玩家{p.seat_id}手牌{p.cards}是否先手：{p.is_header}")

        self.dealer_id = dealer_id
        self.curr_seat_id = dealer_id
        if self.__is_qiang_guan:
            self.call_flow(2, self.start_qiang_guan, self.curr_seat_id)
        elif self.__is_double:
            self.call_flow(2, self.start_redouble)
        else:
            await self.turn_start()

    async def start_redouble_or_turn_start(self):
        if self.__is_double:
            self.call_flow(1, self.start_redouble)
        else:
            await self.turn_start()

    async def start_qiang_guan(self, seat_id):
        """ 抢关 """
        self.set_flow_status(FlowStatus.F_IN_QIANG_GUAN)
        self.log_info("开始抢关", seat_id)
        data = {
            "seat_id": seat_id,
            "seconds": 10
        }
        data_model = S2CStartQiangGuan.pb_model(**data)
        await self.inner_broadcast(CmdRoom.START_QIANG_GUAN, data_model)

    async def on_player_qiang_guan(self, player: Player, qiang_guan):
        self.log_info("玩家抢关", player.uid,"操作",qiang_guan)
        if self.room_status != RoomStatus.T_PLAYING:
            return StaCode.FLOW_ERR, "桌子不在游戏中"
        if self.flow_status != FlowStatus.F_IN_QIANG_GUAN:
            return StaCode.FLOW_ERR, "流程不在抢关状态"
        if player.is_qiang_guan != -1:
            return StaCode.ALREADY_DO, "玩家已经操作过抢关"
        data = {"seat_id": player.seat_id, "qiang_guan": qiang_guan}
        player.is_qiang_guan = qiang_guan
        if qiang_guan == 1:
            self.dealer_id = player.seat_id
            self.curr_seat_id = player.seat_id
            self.__has_qiang_guan = True
        data_model = S2CQiangGuanRunFast.pb_model(**data)
        await self.inner_broadcast(CmdRoom.QIANG_GUAN, data_model)
        return StaCode.PASS, ""

    async def player_redouble(self, player, is_double, flow=FlowStatus.F_IN_REDOUBLE):
        """ 玩家加倍 """
        if not self.flow_status_is_equal(flow):
            return StaCode.FORBID, "非加倍流程"
        if player.is_double:
            return StaCode.ALREADY_DO, "玩家已经操作过了"
        player.has_double = True
        player.is_double = is_double
        self.log_info(player.uid, "操作加倍完成: ", is_double)
        data = {"seat_id": player.seat_id, "is_double": is_double}
        data_model = S2CDoDoubleRunFast.pb_model(**data)
        await self.inner_broadcast(CmdRoom.DO_REDOUBLE, data_model)

        return StaCode.PASS, ""

    def check_player_multiple_finish(self):
        """ 检查玩家是否加倍完成 """
        for p in self.seats:
            if not p.has_double:
                return False
        return True

    def check_player_qiang_guan(self):
        is_all_finish = False
        count = 0
        for p in self.seats:
            if p.is_qiang_guan == 1:
                is_all_finish = True
                return is_all_finish
            if p.is_qiang_guan != -1:
                count += 1
        if count == len(self.seats):
            is_all_finish = True
        return is_all_finish

    async def action_pass_to_next(self):
        """ 过到下一个玩家 """
        self.curr_seat_id = self.next_player(self.curr_seat_id).seat_id
        self.log_info("过牌到下一个玩家", self.curr_seat_id)
        await self.turn_next()

    def get_next_dealer_seat_id(self,last_dealer_id):
        return (last_dealer_id % self.max_player_count) + 1

    async def start_redouble(self):
        """ 开始加倍 """  # todo: 每个玩家都能加倍？
        self.set_flow_status(FlowStatus.F_IN_REDOUBLE)
        self.log_info("开始加倍")
        one_of_model = s2c_one_of_model()
        one_of_model.seconds = 10
        await self.inner_broadcast(CmdRoom.START_REDOUBLE, one_of_model)

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

    async def turn_start(self):
        """ 首出 """
        self.log_info("turn_start")
        self.set_flow_status(FlowStatus.F_IN_TURN_TO)
        turn_player = self.dealer()
        self.set_position_maps()
        await self.turn_to_someone(turn_player,True)

    async def turn_next(self):
        turn_end = self.get_turn_end()
        if turn_end:
            await self.inner_broadcast(CmdRoom.TURN_END)
        await self.turn_to_someone(self.next_player(self.curr_seat_id),turn_end)

    async def turn_to_someone(self, player,turn_end=False):
        """ 轮到某人 """
        self.log_info("turn_to_someone",player.seat_id,player.uid)
        self.curr_seat_id = player.seat_id
        yao_de_qi = True
        player.not_play_best = False
        legal_actions = []
        player_cards_len = len(player.cards)
        last_action = RunFastRule.get_last_action(self.__table_cards,self.max_player_count)
        if self.__early_show_cards and not last_action and player_cards_len>1:
            is_all_big = self.check_is_all_big(player)
            if is_all_big:
                player.is_all_big = True
                self.log_info("当前玩家全大",player.seat_id,player.cards)
                data = {"seat_id":player.seat_id,"cards":player.cards}
                data_model = S2CEarlyShowCardRunFast.pb_model(**data)
                await self.inner_broadcast(CmdRoom.EARLY_SHOW_CARD, data_model)
                if player.is_qiang_guan == 1:
                    self.__qiang_guan_win = True
                await self.round_over()
                return

        if self.__table_cards:
            legal_actions = RunFastRule.get_legal_card_play_actions_run_fast(player.cards, self.__table_cards, self.__allow_act,
                                                                             self.__drift,self.max_player_count)
            print(legal_actions,len(legal_actions))
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
            "turn_end": turn_end,
        }
        data_model = S2CTurnToRunFast.pb_model(**notify_data)
        await self.inner_broadcast(CmdRoom.TURN_TO, data_model, exclude_uid=player.uid)
        if legal_actions:
            data_model.legal_actions = json_encode(legal_actions)
        if not yao_de_qi:
            data_model.seconds = 5
        await self.inner_send(player, CmdRoom.TURN_TO, data_model)

        self.log_info("轮到某人", player.uid, self.curr_seat_id, yao_de_qi)

        if not yao_de_qi and not self.__can_pass:
            self.call_flow(0.5, self.do_play_cards, player, [])
            return
        last_action_len = len(last_action)
        if yao_de_qi and 2 >= last_action_len == player_cards_len:
            return await self.delay_func(0.5, self.do_play_cards, player, player.cards.copy())
        if not last_action:
            if RunFastRule.one_hand_play_out_run_fast(player.cards, self.__allow_act, self.__drift):
                return await self.delay_func(0.5, self.do_play_cards, player, player.cards.copy())

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

    async def do_play_cards(self, player, cards: list):
        code, msg = await self.player_play_cards(player, cards)
        self.log_info(player.uid, player.seat_id, "do_play_cards 返回", code, msg)
        if code == StaCode.PASS:
            if not player.cards:
                if player.is_qiang_guan == 1:
                    self.__qiang_guan_win = True
                if len(cards) == 1:
                    last_player = self.next_player_reverse(player.seat_id)
                    if last_player.not_play_best:
                        last_player.is_bao_pei = True
                        self.has_bao_pei = True
                return await self.delay_func(1, self.round_over)
            return await self.turn_next()

    async def do_check_out(self, curr_player, account: dict,over_type=OverType.DEFAULT):
        """ 结算 """
        win_score = 0
        have_qiang_guan = self.get_player_qiang_guan_status()
        if self.__is_qiang_guan and have_qiang_guan:
            self.qiang_guan_score(account,over_type)
        else:
            base_multiple = 2 if curr_player.is_double else 1
            bao_pei_player = 0
            for p in self.seats:
                if p.seat_id == curr_player.seat_id:
                    continue
                score = self.calc_score(len(p.cards), curr_player, p)
                if p.is_double:
                    score = score *2*base_multiple
                if over_type == OverType.FORCE:
                    score = 0
                win_score += score
                if self.__has_bao_pei:
                    if not p.is_bao_pei:
                        account[p.seat_id] = {"total_score": 0 + p.bomb_score}
                    else:
                        bao_pei_player = p
                else:
                    account[p.seat_id] = {"total_score": -score + p.bomb_score}
            if self.__has_bao_pei:
                account[bao_pei_player.seat_id] = {"total_score": -win_score + bao_pei_player.bomb_score}
            account[curr_player.seat_id] = {"total_score": win_score + curr_player.bomb_score}
            curr_player.add_win_count()

    def calc_score(self, card_count, winner, player):
        if card_count == 1:
            return 0
        if card_count == self.__card_count:
            if winner:
                winner.add_dan_fan_guan_count(1, 1)
            player.add_bei_guan_count(1)
            player.quan_guan = True
            return card_count * 2
        if self.__is_fan_guan:
            if player.is_header and player.play_count == 1:
                if winner:
                    winner.add_dan_fan_guan_count(1, 2)
                player.add_bei_guan_count(1)
                return card_count * 2
        return card_count

    def get_player_qiang_guan_status(self):
        have_qiang_guan = False
        for p in self.seats:
            if p.is_qiang_guan == 1:
                have_qiang_guan = True
        return have_qiang_guan

    def qiang_guan_score(self, account: dict,over_type=OverType.DEFAULT):
        """抢关算分：抢关失败：抢关者输以下分数，其余玩家平分他输的分。抢关成功：抢关者赢以下分数，其余玩家平分输分。
            2人场：16（手牌）*2（抢关）*2（春天）
            3人场：16（手牌）*2（抢关）*2（春天）*2（人数）"""
        win_score = self.__card_count * 2
        if over_type == OverType.FORCE:
            win_score = 0
        #  抢关计分
        if not self.__qiang_guan_win:  # 抢关失败
            for p in self.seats:
                if p.is_qiang_guan != 1:
                    account[p.seat_id] = {"total_score": win_score + p.bomb_score}
                    p.add_win_count()
                else:
                    score = -2 * win_score if self.max_player_count == 3 else -win_score
                    account[p.seat_id] = {"total_score": score + p.bomb_score}
        else:  # 抢关成功
            for p in self.seats:
                if p.is_qiang_guan != 1:
                    account[p.seat_id] = {"total_score": -win_score + p.bomb_score}
                    p.add_bei_guan_count(1)
                else:
                    score = 2 * win_score if self.max_player_count == 3 else win_score
                    account[p.seat_id] = {"total_score": score + p.bomb_score}
                    p.add_dan_fan_guan_count(1)
                    p.add_win_count()


    async def round_over(self, over_type=OverType.DEFAULT, **kwargs):
        """ 一局结束 """
        is_force = kwargs.get("is_force", False)
        if is_force:
            over_type = OverType.FORCE
        self.set_flow_status(FlowStatus.F_IN_CHECK_OUT)

        curr_player = self.curr_player()
        self.__winner_id = curr_player.seat_id
        self.log_info(
            "round_over", "赢家：", curr_player.uid, curr_player.seat_id, self.__table_cards)
        account = {}
        await self.do_check_out(curr_player,account,over_type)
        data = {
            "round_idx": self.round_idx,
            "has_next_round": self.has_next_round(),
            "seats": [],
            "finish_type": over_type,
            "dealer": self.dealer_id,
            "account": account,
            "round_over_msg_type": S2CRoundOverInfoRunFast
        }
        await super().round_over(over_type,**data)

    async def player_play_cards(self, player, cards):
        """ 玩家打牌 """
        if not self.room_status_is_equal(RoomStatus.T_PLAYING):
            return StaCode.FORBID, "桌子状态非游戏中"
        if not self.flow_status_is_equal(FlowStatus.F_IN_TURN_TO):
            return StaCode.FORBID, "现在还不能出牌"
        if player.seat_id != self.curr_seat_id:
            return StaCode.NOT_YOUR_TURN, "未轮到你"
        last_action = RunFastRule.get_last_action(self.__table_cards,self.max_player_count)
        if not self.__table_cards and self.__three_need_first:
            if self.__first_play_type == FirstPlayType.HX_3 and not Cards.HX_3 in cards:
                return StaCode.RULE_ERR, "首出必须出红桃3"
            if self.__first_play_type == FirstPlayType.HT_3 and not Cards.HT_3 in cards:
                return StaCode.RULE_ERR, "首出必须出黑桃3"

        if not last_action and not cards:
            return StaCode.ERR_ARG, "首出不能不要"

        if not RunFastRule.contain(player.cards, cards):
            return StaCode.ERR_ARG, "出的牌手里没有"

        self.log_info(player.uid,player.seat_id, "玩家出牌: ", cards)
        act_type = ActionType.TYPE_0_PASS
        if cards:
            cards = [Cards.find_member_by_val(c) for c in cards]
            cards.sort(key=RunFastRule.sort_rule)
            is_last_hand = len(cards) == len(player.cards) #是否是最后一手牌
            is_legal, move_info = RunFastRule.is_legal_action_run_fast(cards, last_action, self.__allow_act,self.__drift,is_last_hand)
            if not is_legal:
                return StaCode.RULE_ERR, "出牌不符合规则"

            act_type = move_info['type']
            if act_type == ActionType.TYPE_4_BOMB or self.__three_A_is_bomb and act_type == ActionType.TYPE_17_THREE_A_IS_BOMB:
                player.add_bomb_count()
                await self.bomb_cale_score(player)
            elif act_type == ActionType.TYPE_1_SINGLE:
                next_player = self.next_player(self.curr_seat_id)
                if len(next_player.cards) == 1 :
                    if self.__call_one_must_big:
                        if RunFastRule.check_card_in_hand_is_bigger(player.cards, cards[-1].val):
                            return StaCode.RULE_ERR, "下家报单必须出最大的牌"
                    else:
                        if RunFastRule.check_card_in_hand_is_bigger(player.cards, cards[-1].val):
                            player.not_play_best = True

            player.rm_cards(cards)

        self.log_info(player.uid, "玩家出牌完成: ", cards)

        # todo: 记录AI使用参数
        # 清空上一个操作，用于记录最新的
        cards_val = [card.val for card in cards]
        position = self.__position_maps.get(player.seat_id)
        self.__played_cards_dict[position].extend(cards_val)
        self.__last_move_dict[position].clear()
        self.__last_move_dict[position].extend(cards_val)

        # 桌子参数
        self.__table_cards.append(cards)
        self.__newest_table_cards[player.seat_id - 1]["cards"] = cards
        data = {"seat_id": player.seat_id, "cards_len": len(player.cards), "act_type": act_type, "cards": cards}
        data_model = S2CPlayCardsRunFast.pb_model(**data)
        await self.inner_broadcast(CmdRoom.PLAY_CARDS, data_model)
        return StaCode.PASS, ''

    async def on_player_ready(self, player: Player):
        self.log_info("玩家准备", player.uid)
        if self.room_status not in (RoomStatus.T_IDLE, RoomStatus.T_CHECK_OUT):
            return StaCode.FLOW_ERR, "桌子不在可准备状态"
        if player.is_ready:
            return StaCode.ALREADY_DO, "玩家已经准备"
        player.is_ready = True
        data = {"seat_id": player.seat_id, "is_ready": player.is_ready}
        data_model = S2CReady07Mahjong.pb_model(**data)
        await self.inner_broadcast(CmdRoom.READY, data_model)
        return StaCode.PASS, ""

    async def bomb_cale_score(self, bomb_player: Player):
        """ 计算炸弹得分 """
        result = {}
        bomb_score_data = []
        total_score = 0
        for p in self.seats:
            if p.seat_id == bomb_player.seat_id:
                continue
            p.bomb_score = -self.__bomb_score
            total_score += self.__bomb_score
            bomb_score_data.append({"seat_id": p.seat_id, "round_score": p.round_score, 'win_score': -self.__bomb_score})
        bomb_player.bomb_score = total_score
        bomb_score_data.append({"seat_id": bomb_player.seat_id, "round_score": bomb_player.round_score, 'win_score': total_score})
        result["data"] = bomb_score_data

        #广播炸弹分数
        data_model = S2CBombScoreRunFast.pb_model(**result)
        await self.inner_broadcast(CmdRoom.BOMB_SCORE, data_model)

    def check_is_all_big(self,curr_player):
        """检查是否是全大"""
        lowest_card = self.find_best_card(curr_player.cards,0)
        count = 0
        for p in self.seats:
            if p.seat_id == curr_player.seat_id:
                continue
            if self.find_bomb_card(p.cards):
                return False
            highest_card = self.find_best_card(p.cards,-1)
            if lowest_card >= highest_card:
                count += 1
        if count == len(self.seats) - 1:
            return True
        return False

    def get_turn_end(self):
        """ 是否是一轮结束 """
        turn_end = False
        if self.__table_cards and not RunFastRule.get_last_action(self.__table_cards,self.max_player_count):
            turn_end = True
        if not self.__table_cards:
            turn_end = True
        return turn_end

    @staticmethod
    def find_best_card(cards, index):
        """ 找到最大/小的牌 """
        cards_val = [c.val for c in cards]
        cards_val.sort()
        card = cards_val[index]
        return card

    def find_bomb_card(self, cards):
        """
        检查手牌中是否有炸弹
        - 四张相同的牌
        - 三个A（如果 __three_A_is_bomb 为真）
        """
        if not cards:
            return False

        cards_val = [c.val for c in cards]
        count_dict = Counter(cards_val)

        # 检查三个A的情况
        if self.__three_A_is_bomb and count_dict.get(14) == 3:
            return True

        # 检查四张相同牌的情况
        return any(count == 4 for count in count_dict.values())


    @staticmethod
    def serialize_player_info(room_player_info):
        return S2CPlayerInfoRunFast.pb_model(room_player_info)

    async def liu_ju(self):
        await super(BaseCardRoom, self).force_dismiss()

    def serialize_room_info(self):
        room_info = self.room_info()
        newest_table_cards = []
        for cards_info in self.__newest_table_cards:
            newest_table_cards.append(cards_info)
        room_info["table_cards"] = newest_table_cards
        room_info["turn_end"] = self.get_turn_end()
        if self.room_status == RoomStatus.T_CLOSED:
            self.log_info("房间已在关闭状态")
            return None
        return S2CRoomInfoRunFast.pb_model(**room_info)

    def clear_room_round_start(self):
        super().clear_room_round_start()
        self.__table_cards = []
        self.__newest_table_cards = self.init_newest_table_cards(self.max_player_count)
        self.__has_qiang_guan = False
        self.__qiang_guan_win = False
        self.__yao_de_qi = False
        self.__has_bao_pei = False

    def refresh_room_conf(self, service, room_conf):
        self.__init__(self.tid, service, room_conf)

    def clear_room(self):
        self.__table_cards = []
        self.__yao_de_qi = False
        self.__has_qiang_guan = False
        self.__qiang_guan_win = False
        self.__has_bao_pei = False
        self.__newest_table_cards = self.init_newest_table_cards(self.max_player_count)
        self.__position_maps = {}
        super().clear_room()