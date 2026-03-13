import random

from c_services.const.cs_enum_const import CmdRoom, CmdRobotCal
from c_services.cs_mahjong import const
from c_services.cs_mahjong.const import ActionType, FlowStatus, TimerDelay, CardsType, HuType, PlayType
from c_services.cs_mahjong.room_base import Room
from c_services.cs_mahjong.rule import Rule
from common.proto.py_pb2.ws_c2s import gang_model, exchange_model
from common.proto.py_pb2.ws_leisure import s2c_one_of_model
from common.public.conf import C_SERVICE_SECRET_KEY
from common.public.enum_const import StaCode, ServiceEnum
from common.utils.utils import UtilsTool


class RoomRobot(Room):

    async def exchange_three_time_out(self,seconds):
        if self.flow_status != FlowStatus.T_IN_EXCHANGE_CARDS:
            return StaCode.FLOW_ERR
        for p in self.seats:
            if p.is_robot:
                res = random.randint(2, 8)
                if self.robot_fast:
                    res = 0.5
                p.call_flow(res, self.exchange_three_auto,p)
        self.call_flow(seconds, self.deal_exchange_time_out)

    async def deal_exchange_time_out(self):
        for p in self.seats:
            await self.exchange_three_auto(p)

    async def exchange_three_auto(self,p):
        if not self.exchange_cards_info.get(p.seat_id):
            is_same_suit = self.is_same_suit()
            exchange_cards = self.recommend_exchange_cards(p,is_same_suit)
            self.log_info(p.uid, "推荐换牌：", exchange_cards)
            code, _ = await self.on_player_exchange_cards(p, exchange_cards)
            if StaCode.PASS != code:
                self.log_info(p.uid, "超时换牌有误", code)

    async def enter_mo_pai_call_by_robot(self,curr_player,seconds):
        if curr_player.is_robot:
            res = random.randint(1, 2)
            if self.robot_fast:
                res = 0.5
            self.call_flow_robot(res, self.check_robot_operate)
        else:
            if curr_player.card_is_lock() and curr_player.is_action_in_operates(ActionType.ACTION_TYPE_MEN):
                self.call_flow(seconds, self.operates_time_out)
            else:
                self.call_flow(seconds, self.turn_to_player_chu_pai, curr_player, False, 0)


    async def turn_to_chu_pai_by_robot(self,p,timeout_seconds):
        if p.is_robot:
            if p.seat_id == self.dealer_id and not p.all_chu_cards:
                rs = 4
            else:
                rs = UtilsTool.random_choice_num([1, 2, 3], [0.5, 0.3, 0.2])
            if self.robot_fast:
                rs = 0.5
            self.call_flow_robot(rs, self.check_robot_auto_chu_pai)
            return
        self.call_flow(timeout_seconds, self.chu_pai_time_out, p)

    async def chu_pai_time_out(self, p):
        if self.flow_status not in (FlowStatus.T_IN_DI_HU_CHU_PAI, FlowStatus.T_IN_CHU_PAI):
            return StaCode.FLOW_ERR
        if p.seat_id != self.curr_seat_id:
            return StaCode.NOT_YOUR_TURN
        cards = list(p.cards)
        code, _ = await self.on_player_chu_pai(p, self.serialized_chu_pai_data(cards[-1]))
        if StaCode.PASS == code:
            self.log_info(p.uid, "超时出牌_摸到什么打什么：", cards[-1])
            return self.call_flow(0.5, self.enter_chu_pai_call)

    async def check_robot_operate(self):
        has_operate = False
        for p in self.seats:
            if not p.is_robot:
                continue
            code = StaCode.FAIL
            if p.can_operates() and not self.has_do_action(p):
                has_operate = True
                gang_type = p.gang_in_operates()
                should_hu = False
                if self.play_type in (PlayType.JIAN_LOU_XUE_LIU, PlayType.AN_LONG_XUE_ZHAN) and p.is_action_in_operates(ActionType.ACTION_TYPE_HU):
                    hu_cards_count = self.calculate_hu_cards_count(p)
                    self.log_info("check_robot_operate 胡牌数量：", p.uid, hu_cards_count,p.seat_id)
                    if hu_cards_count <= 3:
                        # 剩余能胡的牌的数量小于等于3，直接胡牌
                        should_hu = True
                    elif 3 < hu_cards_count <= 6:
                        # 剩余能胡的牌的数量大于3小于等于6，有50%的概率胡牌
                        import random
                        should_hu = random.random() < 0.5
                    if should_hu:
                        code, _ = await self.on_player_hu(p)
                        if StaCode.PASS != code:
                            self.log_info("机器人操作胡牌有误", code)

                if not should_hu:
                    if p.is_action_in_operates(ActionType.ACTION_TYPE_MEN):
                        code, _ = await self.on_player_men(p)
                        self.log_info("check_robot_operate 闷")
                        if code != StaCode.PASS:
                            self.log_info("机器人操作闷有误", code)
                    elif p.is_action_in_operates(ActionType.ACTION_TYPE_JIAN):
                        self.log_info("check_robot_operate 捡")
                        code, _ = await self.on_player_jian(p)
                        if code != StaCode.PASS:
                            self.log_info("机器人操作捡有误", code)
                    elif p.is_action_in_operates(ActionType.ACTION_TYPE_HU):
                        code, _ = await self.on_player_hu(p)
                        if StaCode.PASS != code:
                            self.log_info("机器人操作胡牌有误", code)
                    elif p.is_action_in_operates(ActionType.ACTION_TYPE_TIAN_TING):
                        code, _ = await self.on_player_tian_ting(p)
                        if StaCode.PASS != code:
                            self.log_info("机器人操作天听有误", code)
                    elif gang_type:
                        # todo: AI机器人计算是否杠
                        code = StaCode.PASS
                        await self.robot_auto_gang(p, gang_type)
                    elif p.is_action_in_operates(ActionType.ACTION_TYPE_PENG):
                        # todo: AI机器人计算是否碰
                        code = StaCode.PASS
                        await self.robot_auto_pong(p)

                    if code != StaCode.PASS:
                        self.log_info("机器人操作有误，选择pass")
                        await self.on_player_pass(p)

        if has_operate:
            await self.check_action_end()

    async def operates_time_out(self):
        if self.flow_status not in (FlowStatus.T_IN_PUBLIC_OPRATE, FlowStatus.T_IN_MO_PAI_CALL,
                                    FlowStatus.T_IN_ZHUAN_WAN_GANG_PAI_CALL,FlowStatus.T_IN_TIAN_TING,
                                    FlowStatus.T_IN_FOUR_BAO_TING, FlowStatus.T_IN_TIAN_HU,
                                    FlowStatus.T_IN_EIGHT_TIAN_HU):
            return
        for p in self.seats:
            if p.can_operates() and not self.has_do_action(p):
                self.log_info(self.tid, p.seat_id, p.uid, "玩家有操作 超时：", p.operates)
                if p.is_action_in_operates(ActionType.ACTION_TYPE_HU) and self.poker.left_count < const.XUE_LIU_LEFT_BI_HU:
                    self.log_info("超时尾三必胡自动胡",p.uid,p.seat_id)
                    code, _ = await self.on_player_hu(p)
                    if StaCode.PASS != code:
                        self.log_info("超时尾三必胡操作胡牌有误", code)
                elif p.card_is_lock():
                    if p.is_action_in_operates(ActionType.ACTION_TYPE_MEN):
                        code, _ = await self.on_player_men(p)
                        self.log_info("锁牌后超时闷")
                        if code != StaCode.PASS:
                            self.log_info("锁牌后超时闷有误", code)
                    elif p.is_action_in_operates(ActionType.ACTION_TYPE_JIAN):
                        self.log_info("锁牌后超时捡")
                        code, _ = await self.on_player_jian(p)
                        if code != StaCode.PASS:
                            self.log_info("锁牌后超时捡有误", code)
                else:
                    await self.time_out_with_player_operates(p)
        self.record_operates.clear()
        await self.check_action_end()

    async def time_out_with_player_operates(self, p):
        code = await self.on_player_pass(p)
        if code != StaCode.PASS:
            p.operates = []
            one_of_model = s2c_one_of_model()
            one_of_model.seat_id = self.curr_seat_id
            await self.inner_send(p, CmdRoom.PLAYER_PASS, one_of_model)
        if self.flow_status in (FlowStatus.T_IN_PUBLIC_OPRATE, FlowStatus.T_IN_ZHUAN_WAN_GANG_PAI_CALL,
                                FlowStatus.T_IN_TIAN_TING, FlowStatus.T_IN_FOUR_BAO_TING, FlowStatus.T_IN_MING_GANG_PAI_CALL,
                                FlowStatus.T_IN_TIAN_HU, FlowStatus.T_IN_TIAN_TING, FlowStatus.T_IN_EIGHT_TIAN_HU):
            self.clear_record_operates(p.seat_id)
            if not self.record_operates:
                await self.check_action_end()
                return

    async def deal_operates_call_time_out(self):
        res = random.randint(2, 3)
        if self.robot_fast:
            res = 0.5
        self.call_flow_robot(res, self.check_robot_operate)
        await self.deal_operates_time_out()


    async def deal_operates_time_out(self):
        self.call_flow(TimerDelay.CHU_PAI_AFTER_WAIT_TIME, self.operates_time_out)


    @staticmethod
    def serialized_chu_pai_data(card):
        gang_model.card = card  # 设置 card 值
        serialized_data = gang_model.SerializeToString()
        return serialized_data

    def calc_others_cards_and_piles(self, curr_player):
        """
        todo: 计算其他玩家手牌和桌牌(碰杠)
        """
        ting_list = []
        others_hand_cards = []  # not self
        others_cards_and_piles = []  # only real player, not robot
        for other_player in self.seats:
            if other_player == curr_player:
                continue
            # 添加非当前玩家手牌
            others_hand_cards.extend(other_player.cards)
            # 不添加机器人手牌和碰牌，仅仅添加真人玩家数据
            if other_player.is_robot:
                continue
            ting_list.extend(other_player.ting_list)
            others_cards_and_piles.append((other_player.cards, other_player.table_cards))
        # 打包真人玩家数据
        data = {
            "others_hand_cards": others_hand_cards,
            "others_cards_and_piles": others_cards_and_piles
        }
        return data

    def solid_params(self, p):
        """
        todo: 设置机器人固定计算参数
        """
        data = {
            "uid": p.uid,
            "tid": self.tid,
            "seat_id": p.seat_id,
            "curr_hand_cards": p.cards,
            "magic_card": CardsType.LAI_ZI if CardsType.LAI_ZI in p.cards else None,
            "piles": p.table_cards,
            "left_count": self.poker.left_count,
            "curr_card": self.curr_card,
            "remain_cards": self.remain_cards_dict,
            'cs_type': self.service.service_type,
            'all_hu_cards':self.all_hu_cards,
            'all_played_cards':self.all_play_out_cards,
        }
        return data

    async def robot_auto_attack(self, p):
        """
        todo: 计算机器人自动出牌
        """
        state = {
            **self.solid_params(p),
            **self.calc_others_cards_and_piles(p),
            'cmd': CmdRoom.ROBOT_CAL_ACTION.value,
            "secret": C_SERVICE_SECRET_KEY
        }
        # self.log_info("发送机器人自动出牌计算数据: ", state)
        await self.cs2cs_by_rmq(ServiceEnum.ROBOT_MAHJONG_FC, CmdRobotCal.CAL_ACTION, state)

    async def robot_auto_pong(self, p):
        """
        todo: 计算机器人自动碰
        """
        state = {
            **self.solid_params(p),
            **self.calc_others_cards_and_piles(p),
            'cmd': CmdRoom.ROBOT_CAL_PENG.value,
            "secret": C_SERVICE_SECRET_KEY
        }
        # self.log_info("发送机器人自动碰计算数据: ", state)
        await self.cs2cs_by_rmq(ServiceEnum.ROBOT_MAHJONG_FC, CmdRobotCal.CAL_PONG, state)

    async def robot_auto_gang(self, p, gang_type):
        """
        todo: 计算机器人自动杠
        """
        state = {
            **self.solid_params(p),
            **self.calc_others_cards_and_piles(p),
            "gang_type": gang_type,
            "can_gang_cards": self.cal_gang_card(p, gang_type),
            'cmd': CmdRoom.ROBOT_CAL_GANG.value,
            "secret": C_SERVICE_SECRET_KEY
        }
        # self.log_info("发送机器人自动杠计算数据: ", state)
        await self.cs2cs_by_rmq(ServiceEnum.ROBOT_MAHJONG_FC, CmdRobotCal.CAL_GANG, state)

    def cal_gang_card(self, p, gang_type):
        """
        计算当前杠牌是否为摸牌
        """
        allow_hu_map = {HuType.DI_LONG_QI: self.di_long_qi, HuType.JIN_GOU_DIAO: True,
                        HuType.QI_DUI: True, HuType.FOUR_CARD_NO_NEAR: self.four_card_no_near,
                        HuType.FOUR_CARD_IS_SAME: self.four_card_tian_hu}
        if gang_type == ActionType.ACTION_TYPE_MING_GANG:
            return self.curr_card
        elif gang_type == ActionType.ACTION_TYPE_ZHUAN_WAN_GANG:
            _, card = p.can_zhuan_wan_gang(Rule)
            if card == self.curr_card:
                return card
            else:
                return 0
        elif gang_type == ActionType.ACTION_TYPE_AN_GANG:
            flag, cards = p.can_an_gang(Rule)
            # 可能有多张能杠
            if p.lock_cards:
                can_gang_list = []
                for gang_card in cards:
                    # 先计算杠之前的听牌
                    temp_cards = p.cards.copy()
                    # 再计算杠之后的听牌
                    temp_cards.remove(gang_card)
                    temp_cards.remove(gang_card)
                    temp_cards.remove(gang_card)
                    temp_cards.remove(gang_card)

                    # 听牌一致的话可以杠
                    ting_list1 = Rule.get_ting_hu_list([], temp_cards, allow_hu_map, self.lai_zi)
                    if ting_list1 == p.ting_list:
                        can_gang_list.append(gang_card)
                self.log_info(self.tid, "玩家不能改牌 但能暗杠1", can_gang_list)
                return can_gang_list
            if self.curr_card in cards:
                return self.curr_card
            else:
                return cards
        return 0

    async def check_robot_auto_chu_pai(self):
        player = self.curr_player()
        if not player:
            self.log_info("机器人出牌没找到 robot", player, self.curr_seat_id)
            return
        # 未锁牌情况：有缺打缺，无缺打非癞子
        cards = list(player.cards)
        if player.que > 0:
            if cards[-1] // 10 == player.que:
                code, _ = await self.on_player_chu_pai(player, self.serialized_chu_pai_data(cards[-1]))
                if StaCode.PASS == code:
                    self.log_info(self.tid, player.uid, "机器人打出摸的缺牌：", cards[-1])
                    self.call_flow(0.5, self.enter_chu_pai_call)
                    return
            for card in player.cards:
                if card // 10 == player.que:
                    code, _ = await self.on_player_chu_pai(player, self.serialized_chu_pai_data(card))
                    if StaCode.PASS == code:
                        self.log_info(player.uid, "机器人打出手里的缺牌：", card)
                        self.call_flow(0.5, self.enter_chu_pai_call)
                        return
        if player.card_is_lock():
            await self.turn_to_player_chu_pai(player, False, 0)
        else:
            # todo: 机器人自动计算出牌
            await self.robot_auto_attack(player)

    def calculate_hu_cards_count(self, p):
        """
        计算机器人剩余能胡的牌的数量
        """
        # 初始化能胡的牌的数量

        allow_hu_map = {HuType.DI_LONG_QI: self.di_long_qi, HuType.JIN_GOU_DIAO: True,
                        HuType.QI_DUI: True, HuType.FOUR_CARD_NO_NEAR: self.four_card_no_near,
                        HuType.FOUR_CARD_IS_SAME: self.four_card_tian_hu}
        hu_cards_count = 0

        # 获取玩家的听牌列表
        ting_list = Rule.get_ting_hu_list(p.table_cards, list(p.cards), allow_hu_map, self.lai_zi)

        # 获取剩余的牌
        remain_cards = self.poker.remain_cards if hasattr(self.poker, 'remain_cards') else []

        # 计算每种听牌在剩余牌中的数量
        for card in ting_list:
            # 计算该牌在剩余牌中的数量
            card_count = remain_cards.count(card)
            hu_cards_count += card_count

        return hu_cards_count

    def recommend_exchange_cards(self,player, same_suit=False):
        """
        推荐换三张牌的策略
        :param player: 玩家对象
        :param same_suit: 若为 True，优先从同一花色中选择三张（若存在）；
                          若不存在，则退化为普通策略。
        :return: 推荐舍弃的三张牌列表（长度 <=3，通常为3）
        """
        hand_cards = player.cards.copy()
        if len(hand_cards) < 3:
            return hand_cards[:]  # 全换

        # 按花色分组
        suit_cards = {}
        for card in hand_cards:
            suit = card // 10
            suit_cards.setdefault(suit, []).append(card)

        # 如果要求同花色且存在 >=3 的花色
        if same_suit:
            candidates = [(s, cs) for s, cs in suit_cards.items() if len(cs) >= 3]
            if candidates:
                # 选牌数最多的花色（可调整策略）
                _, best_cards = max(candidates, key=lambda x: len(x[1]))
                return self.select_most_isolated(best_cards, 3)

        # 普通策略：按花色数量升序处理（先处理杂花）
        suit_list = sorted(suit_cards.items(), key=lambda x: len(x[1]))
        recommended = []
        for suit, cards in suit_list:
            if len(recommended) >= 3:
                break
            to_select = 3 - len(recommended)
            isolated = self.select_most_isolated(cards, to_select)
            recommended.extend(isolated)

        return recommended[:3]

    @staticmethod
    def select_most_isolated(cards, n):
        """从 cards 中选出 n 张最孤立的牌"""
        if len(cards) <= n:
            return cards[:]
        sorted_cards = sorted(cards)
        scores = []
        for i, card in enumerate(sorted_cards):
            prev_gap = card - sorted_cards[i - 1] if i > 0 else float('inf')
            next_gap = sorted_cards[i + 1] - card if i < len(sorted_cards) - 1 else float('inf')
            score = min(prev_gap, next_gap)
            scores.append((card, score))
        scores.sort(key=lambda x: x[1], reverse=True)  # 孤立度高优先
        return [card for card, _ in scores[:n]]