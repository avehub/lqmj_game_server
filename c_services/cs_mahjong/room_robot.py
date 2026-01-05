import random
from copy import deepcopy

from c_services.cs_mahjong.const import ActionType, FlowStatus, TimerDelay
from c_services.cs_mahjong.room_base import Room
from common.public.enum_const import StaCode
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
