from c_services.base.base_leisure_room import BaseLeisureRoom
from c_services.cs_journey_west_killer.const import FlowStatus
from c_services.cs_journey_west_killer.poker import Poker


class Room(BaseLeisureRoom):
    def __init__(self, tid, service, room_conf, **extra_room_info):
        super().__init__(tid, service, room_conf, extra_room_info, Poker)

    async def inner_deal_cards(self, set_dealer_card=None):
        self.set_flow_status(FlowStatus.T_IN_DEAL_CARDS)
        all_cards = self.poker.deal_cards(self.max_player_count, 5)
        all_cards[-1].append(self.poker.pop())  # 尾家多发一张
        await self.do_deal_cards(all_cards, set_dealer_card)
        # 下发消息
        await self.turn_start(first=True)

    async def deal_cards(self, set_dealer_card=None):
        """ 发牌 """
        if not self.flow_status_is_equal(FlowStatus.T_IN_IDLE):
            self.info_log(f"flow error: {self.flow_status}")
            return
        await self.inner_deal_cards(set_dealer_card)

    @staticmethod
    def get_team_id(player):
        if player.seat_id == 1:
            return 4
        if player.seat_id == 4:
            return 1
        if player.seat_id == 2:
            return 3
        if player.seat_id == 3:
            return 2

        return 0
