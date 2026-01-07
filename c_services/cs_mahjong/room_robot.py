import random
from copy import deepcopy

from c_services.const.cs_enum_const import CmdRoom, CmdRobotCal
from c_services.cs_mahjong.const import ActionType, FlowStatus, TimerDelay, CardsType, HuType
from c_services.cs_mahjong.room_base import Room
from c_services.cs_mahjong.rule import Rule
from common.proto.py_pb2.ws_c2s import gang_model
from common.public.conf import C_SERVICE_SECRET_KEY
from common.public.enum_const import StaCode, ServiceEnum
from common.utils.utils import UtilsTool


class RoomRobot(Room):

    async def enter_mo_pai_call_by_robot(self,curr_player,seconds):
        if curr_player.is_robot:
            res = random.randint(1, 2)
            self.call_flow_robot(res, self.check_robot_operate)
        else:
            self.call_flow(seconds, self.turn_to_player_chu_pai, curr_player, False, 0)


    async def turn_to_chu_pai_by_robot(self,p,timeout_seconds):
        if p.is_robot:
            if p.seat_id == self.dealer_id and not p.all_chu_cards:
                rs = 4
            else:
                rs = UtilsTool.random_choice_num([1, 2, 3], [0.5, 0.3, 0.2])
            self.call_flow_robot(rs, self.check_robot_auto_chu_pai)
            return
        self.call_flow(timeout_seconds, self.chu_pai_time_out, p)

    async def chu_pai_time_out(self, p):
        if self.flow_status not in (FlowStatus.T_IN_DI_HU_CHU_PAI, FlowStatus.T_IN_CHU_PAI):
            return StaCode.FLOW_ERR
        if p.seat_id != self.curr_seat_id:
            return StaCode.NOT_YOUR_TURN
        cards = deepcopy(p.cards)
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

    async def chu_pai_call_time_out(self):
        if self.flow_status not in (FlowStatus.T_IN_PUBLIC_OPRATE, FlowStatus.T_IN_MO_PAI_CALL,
                                    FlowStatus.T_IN_ZHUAN_WAN_GANG_PAI_CALL):
            return
        for p in self.seats:
            if p.can_operates() and not self.has_do_action(p):
                self.log_info(self.tid, p.seat_id, p.uid, "玩家有操作 超时：", p.operates)
                await self.time_out_with_player_operates(p)
        self.record_operates.clear()
        await self.check_action_end()

    async def deal_enter_chu_pai_call_time_out(self):
        self.call_flow_robot(TimerDelay.ROBOT_TIME, self.check_robot_operate)
        await self.deal_chu_pai_call_time_out()

    async def deal_chu_pai_call_time_out(self):
        self.call_flow(TimerDelay.CHU_PAI_AFTER_WAIT_TIME, self.chu_pai_call_time_out)


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
        count_dict = {}
        for card in self.poker.remain_cards:
            key = str(card)
            count_dict[key] = count_dict.get(key, 0) + 1
        data = {
            "uid": p.uid,
            "tid": self.tid,
            "seat_id": p.seat_id,
            "curr_hand_cards": p.cards,
            "magic_card": CardsType.LAI_ZI if CardsType.LAI_ZI in p.cards else None,
            "piles": p.table_cards,
            "left_count": self.poker.left_count,
            "curr_card": self.curr_card,
            "remain_cards": count_dict,
            'cs_type': self.service.service_type,
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
        self.log_info("发送机器人自动出牌计算数据: ", state)
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
        self.log_info("发送机器人自动碰计算数据: ", state)
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
        self.log_info("发送机器人自动杠计算数据: ", state)
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
                    temp_cards = deepcopy(p.cards)
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
        cards = deepcopy(player.cards)
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

        # todo: 机器人自动计算出牌
        await self.robot_auto_attack(player)
