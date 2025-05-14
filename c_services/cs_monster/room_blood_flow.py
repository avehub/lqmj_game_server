from common.public.enum_const import StaCode
from .const import FlowStatus
from .room_base import Room
from ..const.cs_enum_const import RoomStatus, CmdRoom


class RoomBf(Room):
    """ 血流房间（3局） """

    def __init__(self, tid, service, room_conf, **extra_room_info):
        super(RoomBf, self).__init__(tid, service, room_conf, **extra_room_info)

    async def pick_last_cards(self):
        """ 捡最后一次 """
        curr_player = self.curr_player()
        player_cards_len = len(curr_player.cards)

        self.add_tribulation_val(player_cards_len)
        await self.pick_and_calc_score(curr_player)

        if curr_player.gold <= 0 and not curr_player.free_loss:
            self.call_flow(0, self.notify_is_revenge, curr_player)
        else:
            self.call_flow(0, self.enter_round_over)
        return StaCode.PASS, ''

    async def start_next_round(self):
        """ 开始下一局 """
        self.incr_round_count()
        self.clear_data_round_over()
        self.set_room_status(RoomStatus.T_IDLE)
        self.set_flow_status(FlowStatus.T_IN_IDLE)
        self.try_next_round(rs=1)

    async def do_deal_cards(self, all_cards, set_dealer_card=None, extra_data=None):
        """ 血流模式发牌 """
        broke_seats = []
        playing_seats = []
        for p in self.seats:
            if not p.is_out:
                if set_dealer_card in all_cards[p.seat_id-1]:
                    return await super().do_deal_cards(all_cards, set_dealer_card, extra_data)
                playing_seats.append(p.seat_id)
            else:
                broke_seats.append(p.seat_id)

        # 正在游戏玩家与破产玩家交换牌
        playing_seat = playing_seats[0]-1
        for seat_id in broke_seats:
            if set_dealer_card in all_cards[seat_id - 1]:
                all_cards[seat_id - 1], all_cards[playing_seat] = all_cards[playing_seat], all_cards[seat_id - 1]
                self.info_log("破产玩家交换牌", playing_seat, seat_id - 1)
                break
        await super().do_deal_cards(all_cards, set_dealer_card, extra_data)

    async def round_over(self, is_force=False):
        """ 重写round over """
        if not is_force and not self.flow_status_is_equal(FlowStatus.T_IN_SHOU_PAI):
            return
        self.set_room_status(RoomStatus.T_CHECK_OUT)
        self.set_flow_status(FlowStatus.T_IN_CHECK_OUT)

        if not is_force and self.no_give_up_count > 1 and self.has_next_round():
            await self.inner_broadcast(CmdRoom.ROUND_OVER)
            return await self.delay_func(2, self.start_next_round)

        await self.check_out()
        await self.game_over(is_force)

    def clear_data_round_over(self):
        """ 小局清理 """
        super().clear_data_round_over()
        for p in self.seats:
            p.clear_data_round_over()
