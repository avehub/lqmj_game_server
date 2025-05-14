import random
from typing import List
from common.proto.py_pb2.ws_c2s import ability_reverse_model, ability_select_area_model, reverse_model
from common.proto.py_pb2.ws_leisure import S2CPickCardsSequel, S2CPlayerInfo04MonsterSeq, \
    S2CRoomInfo03MonsterSeq, S2CTurnToSeq13, S2CPlayCardsSeq, use_ability_obj, S2CComplementCards
from common.public.enum_const import StaCode, MonsterCardType, ServiceEnum
from promising_game.const import ReasonCostGold
from .poker import Poker, Cards
from .player import Player
from .rule import Rule
from ..const.base_card import CardsSuit
from ..const.cs_enum_const import CmdRoom, CmdRobotMethods
from ..cs_monster.const import FlowStatus, InteractType
from .const import CardArea, CardCapability, CARD_CAMP_SCORE, ActType
from ..cs_monster.room_comb import RoomComb


class Room(RoomComb):
    """ 房间类，专注玩法实现 """

    def __init__(self, tid, service, room_conf, **extra_room_info):
        super().__init__(tid, service, room_conf, extra_room_info, Poker)

        # 出牌区
        self.__area_monster = []  # 妖怪区
        self.__area_prentice = []  # 徒弟区
        self.__area_master = []  # 师傅区
        self.__area_divine = []  # 神仙区

        self.__area_prentice_c2c = {}  # 徒弟区域的card2count（主要为了记录真假悟空）
        self.__next_reverse = False

        self.__cur_legal_actions = []  # 当前合法动作
        self.__cur_ability = 0  # 当前能力
        self.__cur_cards_area = []  # 当前出牌到哪些区域（客户端断线重连需要）

    def last_player(self, seat_id: int, with_cards=True):
        if self.__next_reverse:
            return super().next_player(seat_id, with_cards)
        return self.next_player_reverse(seat_id, with_cards)

    def next_player(self, seat_id: int, with_cards=True) -> Player or None:
        """ 下一个玩家 """
        if self.__next_reverse:
            return self.next_player_reverse(seat_id, with_cards)

        return super().next_player(seat_id, with_cards)

    def __fill_card_from_prentice(self):
        c = self.__area_prentice.pop()
        self.__area_prentice_c2c[c] -= 1
        return c

    def __pop_card_from_prentice(self, c):
        if c == self.__area_prentice[-1]:
            self.__area_prentice.pop()
            self.__area_prentice_c2c[c] -= 1

    def __fill_card_from_area(self, card: Cards):
        """ 根据出牌从出牌区补牌 """
        if card.suit == CardsSuit.DIAMONDS:
            # 妖怪从公共牌区补
            # 六耳猕猴有两种状态，视为孙悟空打出时执行孙悟空的补牌动作
            if card.val == Cards.FK_2.val:
                if not self.real_wo_kong_played():
                    if self.__area_monster:
                        c = self.__area_monster.pop()
                        return {'c': c, 'a': CardArea.MONSTER}
        elif card.suit == CardsSuit.CLUBS:
            # 徒弟从妖怪区补
            if self.__area_monster:
                c = self.__area_monster.pop()
                return {'c': c, 'a': CardArea.MONSTER}
        elif card.suit == CardsSuit.HEARTS:
            # 师傅从徒弟区补
            if self.__area_prentice:
                c = self.__fill_card_from_prentice()
                return {'c': c, 'a': CardArea.PRENTICE}
        elif card == Cards.HT_Q:
            # 白龙马从师傅区补牌
            if self.__area_master:
                c = self.__area_master.pop()
                return {'c': c, 'a': CardArea.MASTER}

        c = self.poker.pop()
        if c:
            # 其余的公共区补
            return {'c': c, 'a': CardArea.COMMON}  # todo: 不够补牌？
        return {}

    async def __notify_complement_cards(self, p, cards_list_map, ability=CardCapability.C0):
        """ 通知补牌 """
        self.info_log(p.uid, "补牌", cards_list_map, ability, p.cards)
        tribulation_val = self.cal_tribulation_val()
        t_val_multiple = str(self.get_t_val_multiple(tribulation_val))
        dm = S2CComplementCards.pb_model(p.seat_id, cards_list_map, tribulation_val, ability, t_val_multiple)
        await self.inner_broadcast(CmdRoom.COMPLEMENT_CARDS, dm)

    def complement_cards(self, player: Player, play_cards: list):
        """ 补牌 """
        if len(play_cards) == 2:
            if Rule.is_master_with_dragon(play_cards):
                return []
        play_cards_len = len(play_cards)
        if play_cards_len == 2:
            if Rule.is_master_with_dragon(play_cards):
                play_cards = [Cards.HX_A, Cards.HX_A]

        cards_list_map = []
        for c in play_cards:
            card_map = self.__fill_card_from_area(c)
            if card_map:
                cards_list_map.append(card_map)

        for card_map in cards_list_map:
            c = card_map['c']
            player.rev_card(c)

        return cards_list_map

    def __add_card_to_area(self, cards: List[Cards]):
        """ 将牌添加到指定区域 """
        if len(cards) == 1 and cards[0] in (Cards.HT_Q, Cards.HT_K):
            self.__area_divine.extend(cards)
            return self.__cur_cards_area
        cards2area = []
        for card in cards:
            match card.suit:
                case CardsSuit.DIAMONDS:
                    # 当徒弟区不存在11点孙悟空时，六耳猕猴当做11点孙悟空打出在徒弟区
                    if card == Cards.FK_2 and not self.real_wo_kong_played():
                        self.use_ability_let_fake_as_real()
                        cards2area.append({'c': card, 'a': CardArea.PRENTICE})
                    else:
                        self.__area_monster.append(card)
                        cards2area.append({'c': card, 'a': CardArea.MONSTER})
                case CardsSuit.CLUBS:
                    # 真悟空打出时，将所有假悟空放置在妖怪区最底部（悟空能力？？？）
                    self.__area_prentice.append(card)
                    self.__area_prentice_c2c[card] = self.__area_prentice_c2c.get(card, 0) + 1

                    cards2area.append({'c': card, 'a': CardArea.PRENTICE})
                case CardsSuit.HEARTS:
                    self.__area_master.append(card)
                    cards2area.append({'c': card, 'a': CardArea.MASTER})
                case _:
                    self.__area_divine.append(card)
                    cards2area.append({'c': card, 'a': CardArea.DIVINE})

        self.__cur_cards_area = cards2area
        return cards2area

    def use_ability_let_fake_as_real(self):
        """ 六耳猕猴能力：如果徒弟区没有孙悟空，则可视作孙悟空打出到悟空区 """
        self.__area_prentice.append(Cards.FK_2)
        self.__area_prentice_c2c[Cards.FK_2] = self.__area_prentice_c2c.get(Cards.FK_2, 0) + 1
        self.info_log("六耳猕猴 视作孙悟空打出到悟空区")
        return CardCapability.C7

    def use_ability_let_fake_wu_kong_to_monster_bottom(self):
        """ 孙悟空能力：让出牌区：徒弟区的假悟空放到妖怪底部 """
        fake_wu_kong_count = self.__area_prentice_c2c.get(Cards.FK_2) or 0
        if fake_wu_kong_count == 0:
            return CardCapability.C0, 0

        fake_wu_kong = []
        fake_wu_kong_card = Cards.FK_2
        self.__area_prentice_c2c.pop(fake_wu_kong_card)
        for _ in range(fake_wu_kong_count):
            self.__area_prentice.remove(fake_wu_kong_card)  # 从徒弟区移除
            fake_wu_kong.append(fake_wu_kong_card)

        if fake_wu_kong:
            fake_wu_kong.extend(self.__area_monster)  # 放到妖怪区底部
            self.__area_monster = fake_wu_kong
            self.info_log("孙悟空能力：让出牌区徒弟区的假悟空放到妖怪底部", fake_wu_kong)
            return CardCapability.C9, 0

        return CardCapability.C0, 0

    async def use_ability_let_last_play_cards_to_self_tribulation_area(self, p: Player, last_play_cards):
        """
        金角银角能力（可以）：无视上一家出牌，但需要将上一家出牌移至自己的磨难区
        必须是要不起时触发该功能
        """
        t_val = 0
        wu_kong_played = self.real_wo_kong_played()
        self.info_log(p.uid, "金角银角能力", wu_kong_played, last_play_cards)

        forward_t_val = self.cal_tribulation_val()
        for c in last_play_cards:
            match c.suit:
                case CardArea.MONSTER:
                    # 此处有可能先打的六耳猕猴，然后出了悟空，六耳猕猴被放到妖怪区，但后来悟空被补走了，此时六耳猕猴也未在徒弟区
                    if not wu_kong_played and c == Cards.FK_2 and c in self.__area_prentice:
                        self.info_log(p.uid, "真悟空未出，执行金角银角能力时应从徒弟区移除六耳猕猴到自己磨难区")
                        t_val += CARD_CAMP_SCORE.get(CardArea.PRENTICE)
                        self.__pop_card_from_prentice(c)
                        continue
                    Rule.rm_from_end(self.__area_monster, c)
                case CardArea.PRENTICE:
                    self.__pop_card_from_prentice(c)
                case _:
                    raise ValueError("金角银角能力触发有误：", last_play_cards)
            t_val += CARD_CAMP_SCORE.get(c.suit)

        self.__cur_ability = CardCapability.C2
        await self.do_checkout(p, t_val, forward_t_val, tigger_interact=False)
        self.info_log("金角银角能力：无视上一家出牌，但需要将上一家出牌移至自己的磨难区", last_play_cards)
        return CardCapability.C2

    async def use_ability_let_game_reverse(self):
        """ 铁扇公主能力：牌局反转 """
        self.__next_reverse = False if self.__next_reverse else True
        self.info_log("铁扇公主能力：牌局反转")
        dm = reverse_model()
        await self.inner_broadcast(CmdRoom.DO_USER_ABILITY, dm)
        return CardCapability.C4

    def use_ability_let_dragon_add_cards(self, p: Player, cards_len=1):
        """ 猪八戒能力：将场上(仙佛区)的小白龙加到手牌 """
        count = 0
        for card in self.__area_divine:
            if card == Cards.HT_Q:
                p.rev_card(card)
                count += 1
                if count == cards_len:
                    break
        if count == 0:
            return CardCapability.C0, 0
        for _ in range(count):
            self.__area_divine.remove(Cards.HT_Q)
        self.info_log("猪八戒能力：将场上(仙佛区)的小白龙加到手牌", count)

        return CardCapability.C8, count

    async def use_ability_take_card_from_area_prentice(self, p: Player, take_count=2):
        """ 唐三藏能力：和小白龙一起打出时，拿取徒弟区顶上2张牌（不再执行唐僧、白龙马自身的补牌动作） """
        count = 0
        cards_list_map = []
        while count < take_count and self.__area_prentice:
            c = self.__fill_card_from_prentice()
            p.rev_card(c)
            count += 1
            cards_list_map.append({'c': c, 'a': CardArea.PRENTICE})
        # todo: 如果徒弟区不足2张牌, 从公告区域补齐？？？
        if take_count - count > 0:
            for card in self.complement_cards_from_public_area(take_count - count):
                p.rev_card(card)
                cards_list_map.append({'c': card, 'a': CardArea.COMMON})

        if cards_list_map:
            await self.__notify_complement_cards(p, cards_list_map, CardCapability.C5)

        self.info_log("唐三藏能力：和小白龙一起打出时，拿取徒弟区顶上2张牌")
        return CardCapability.C5

    def use_ability_let_per_1_card_from_self_tribulation_to_other_tribulation(self, p: Player):
        """ 观世音能力：将自己磨难区的牌分给其他玩家每人一张，放到他们的磨难区（有争议，暂未用） """
        for other_p in self.seats:
            if other_p == p:
                continue
            card = p.pop_tribulation()
            if card:  # todo: 如果自己的磨难区不够
                other_p.add_tribulation([card])

    def complement_cards_from_public_area(self, count=1):
        """ 从公共区域补牌 """
        cards = []
        while count > 0:
            card = self.poker.pop()
            if not card:
                break
            cards.append(card)
            count -= 1
        return cards

    def use_ability_free_select_cards(self, p: Player, area: CardArea, count=2):
        """ 观世音能力：可以选择从牌组、徒弟区、师傅区补牌 """
        # area_enum = CardArea.find_member_by_val(area)
        match area:
            case CardArea.MONSTER:
                fill_area = self.__area_monster
            case CardArea.PRENTICE:
                fill_area = self.__area_prentice
            case CardArea.MASTER:
                fill_area = self.__area_master
            case _:
                return

        while count > 0:
            if not fill_area:
                break
            p.rev_card(fill_area.pop())
            count -= 1

        for card in self.complement_cards_from_public_area(count):
            p.rev_card(card)

    def real_wo_kong_played(self):
        return self.__area_prentice_c2c.get(Cards.MH_J, 0) > 0

    def do_specific_ability(self, player: Player, cards: list):
        """ 执行特殊能力 """
        cards_dict = Rule.stat_card_count(cards)
        if len(cards_dict) == 1:
            match cards[0]:
                # case Cards.FK_2:  # 六耳猕猴
                #     if not self.real_wo_kong_played():
                #         return self.use_ability_let_fake_as_real()
                case Cards.FK_4:  # 金角银角
                    last_cards = Rule.get_last_action(self.turn_cards)
                    if not last_cards:
                        return CardCapability.C0, 0
                    if len(last_cards) == 2 and Rule.is_master_with_dragon(last_cards):
                        return CardCapability.C0, 0
                    len_set = len(set(last_cards))
                    if len_set == 1 and last_cards[0] == Cards.HX_A:
                        return CardCapability.C0, 0
                    if not self.real_wo_kong_played() and len_set == 1 and last_cards[0] == Cards.FK_2:
                        return CardCapability.C2, last_cards

                    if max(last_cards) < Cards.FK_4:
                        return CardCapability.C0, 0

                    return CardCapability.C2, last_cards
                # case Cards.FK_6:  # 铁扇公主
                #     return self.use_ability_let_game_reverse()
                case Cards.MH_10:  # 八戒  若小白龙在场，则加入手牌
                    return self.use_ability_let_dragon_add_cards(player, len(cards))
                case Cards.MH_J:  # 悟空
                    return self.use_ability_let_fake_wu_kong_to_monster_bottom()
        else:
            if len(cards) == 2:
                if Rule.is_master_with_dragon(cards):
                    return CardCapability.C5, 0
        return CardCapability.C0, 0

    async def round_start(self, *args, **kwargs):
        """ 一局开始 """
        await super().round_start(*args, **kwargs)
        await self.delay_func(1, self.deal_cards)

    async def inner_deal_cards(self, set_dealer_card=None):
        self.dealer_id = random.randint(1, self.max_player_count)
        await super().inner_deal_cards(set_dealer_card)

    async def turn_to_someone(self, player):
        """ 轮到某人 """
        if not player:
            self.info_log("没有下一家了")
            return await self.enter_round_over()

        self.curr_seat_id = player.seat_id
        player.clear_operand()

        self.__cur_ability = 0
        self.__cur_legal_actions = self.get_legal_cards(player)

        wait_sec = 20
        notify_data = {
            "seat_id": player.seat_id,
            "seconds": wait_sec,
        }
        data_model = S2CTurnToSeq13.pb_model(**notify_data)
        await self.inner_broadcast(CmdRoom.TURN_TO, data_model, exclude_uid=player.uid)

        # 当前玩家下发合法动作
        for ac in self.__cur_legal_actions:
            la_list_obj = data_model.legal_actions.add()
            la_list_obj.action.extend(ac)

        await self.inner_send(player, CmdRoom.TURN_TO, data_model)

        self.info_log(
            "turn_to ",
            player.uid,
            player.cards,
            self.__cur_legal_actions,
            self.__area_monster,
            self.__area_prentice,
            self.__area_master,
            self.__area_divine,
        )

        if not self.__cur_legal_actions:
            rs = random.randint(2, 5) if player.is_robot else 5
            self.call_flow(rs, self.player_pick_cards, player)
            return

        if player.is_robot:
            # 计算机器人出牌
            self.call_flow_robot(4, self.robot_auto_play_cards, player)
            # self.call_flow_robot(4, self.robot_auto_play_cards_new, player)

        self.call_flow_trustee(1, self.time_out_play_card, player, "call trustee")
        self.call_flow(wait_sec, self.time_out_play_card, player, "call flow")

    def get_next_mint_cards(self):
        """ 获取下一家明牌（知道的牌） """
        next_p = self.next_player(self.curr_seat_id)
        if not next_p:
            return [], []
        next_next_p = self.next_player(next_p.seat_id)
        if not next_next_p:
            return next_p.mint_cards, []
        return next_p.mint_cards, next_next_p.mint_cards

    def get_other_left_cards(self):
        res_cards = self.poker.remain_cards
        for p in self.seats:
            if p.seat_id == self.curr_seat_id:
                continue
            res_cards.extend(p.cards)
        return res_cards

    def get_players_tribulation_val(self):
        t_val_list = [0, 0, 0, 0, 0, 0]
        for p in self.seats:
            t_val_list[p.seat_id - 1] = p.tribulation_val
        return t_val_list

    async def robot_auto_play_cards_new(self, player):
        legal_acts = self.__cur_legal_actions[:]
        if self.turn_cards:
            legal_acts.append([ActType.A2])
        await self.robot_auto_do_action(player, legal_acts)

    async def robot_auto_do_guan_yin_ability(self, p):
        legal_cards = []
        if self.__area_prentice:
            legal_cards.append([ActType.A5])
        if self.__area_master:
            legal_cards.append([ActType.A6])
        if self.poker.left_count > 0:
            legal_cards.append([ActType.A7])
        await self.robot_auto_do_action(p, legal_cards)

    async def robot_auto_do_action(self, player, legal_actions):
        """
        机器人自动选择策略，包括：打牌、选择执行观音、铁扇等技能
        :param player:
        :param legal_actions:
        :return:
        """
        next_mcards, next_next_mcards = self.get_next_mint_cards()
        state_data = {
            "seat_id": player.seat_id,
            "hand_cards": player.cards,
            "players_tribulation_val": self.get_players_tribulation_val(),
            "tribulation_val": self.cal_tribulation_val(),
            "last_action": Rule.get_last_action(self.turn_cards),
            "legal_actions": legal_actions,
            "other_left_cards": self.get_other_left_cards(),
            "area_monster": self.__area_monster,
            "area_prentice": self.__area_prentice,
            "area_master": self.__area_master,
            "area_divine": self.__area_divine,
            "next_mint_cards": next_mcards,
            "next_next_mint_cards": next_next_mcards,
            "play_reverse": self.__next_reverse,
        }

        await self.cs2cs_by_rmq(
            cs_type=ServiceEnum.ROBOT_MONSTER_SEQ,
            c_code=CmdRobotMethods.CAL_ACTION.val,
            msg=state_data,
            uid=player.uid,
        )

    async def robot_auto_play_cards(self, player):
        """ 机器人出牌 """
        self.info_log(player.uid, "机器人随机出牌")
        await self.play_card_by_rand(player)

    async def robot_auto_do_ability(self, p: Player, c: CardCapability):
        """ 机器人执行能力 """
        self.info_log(p.uid, "机器人执行能力", c)
        if c == CardCapability.C4:
            await self.use_ability_let_game_reverse()
            await self.turn_next()
            # await self.robot_auto_do_action(p, [[ActType.A3], [ActType.A4]])
        elif c == CardCapability.C6:
            await self.timeout_guan_yin_complement_cards(p)
            # await self.robot_auto_do_guan_yin_ability(p)

    def get_legal_cards(self, player):
        """ 获取合法动作 """
        wu_kong_played = self.real_wo_kong_played()
        legal_cards = Rule.get_legal_card_play_actions(self.turn_cards, player.cards, wu_kong_played)
        legal_cards = Rule.sort_legal_cards(legal_cards)
        # 单独处理八戒牵走小白龙的情况
        if Cards.HT_Q in self.__area_divine:
            for idx, act in enumerate(legal_cards):
                if act[0] == Cards.MH_10:
                    legal_cards.remove(act)
                    legal_cards.insert(0, act)
                    break
        return legal_cards

    @staticmethod
    def get_skill_movie_index_by_player_equip(p: Player, cards: List[Cards]):
        """ 获取装备技能id """
        match cards[0]:
            case Cards.HX_A:
                idx = MonsterCardType.TANG_SANZANG.val
            case Cards.MH_J:
                idx = MonsterCardType.SUN_WUKONG.val
            case Cards.MH_10:
                idx = MonsterCardType.ZHU_BAJIE.val
            case Cards.MH_9:
                idx = MonsterCardType.SHA_WUJING.val
            case _:
                return 0

        skin_info = p.skin_equip_info.get(str(idx))
        if not skin_info:
            return 0
        print("当前播放皮肤信息：", skin_info)
        skin_equip_id = skin_info.get("skin_id")
        if p.skin_movie_is_play(skin_equip_id):
            return 0

        p.set_skin_movie_is_play(skin_equip_id, True)  # 只播一次
        return skin_equip_id

    async def do_play_cards(self, player, cards: list, desc=""):
        code, msg = await self.player_play_cards(player, cards)
        self.info_log(player.uid, desc, code, msg)
        if code == StaCode.PASS:
            return await self.match_select_ability(player, cards[0])

    async def play_card_by_rand(self, player):
        """ 随机出牌 """
        # can_chu_cards = self.get_legal_cards(player)
        # cards = can_chu_cards[0]
        cards = [0]
        await self.do_play_cards(player, cards, "随机出牌")

    async def match_select_ability(self, player, cards_idx: int):
        """ 匹配是否选择能力 """
        if self.__cur_ability == CardCapability.C2:
            if player.gold <= 0:
                self.call_flow(0, self.notify_is_revenge, player)
            else:
                await self.turn_next()
            return

        cards = self.__cur_legal_actions[cards_idx]
        match cards[0]:
            # case Cards.FK_6 if self.in_play_count == 2:
            case Cards.FK_6:
                await self.enter_ask_use_ability_or_not(player, CardCapability.C4)
            case Cards.HT_K if (self.__area_prentice or self.__area_master or self.poker.left_count):
                await self.enter_ask_use_ability_or_not(player, CardCapability.C6)
            case _:
                await self.turn_next()

    async def enter_ask_use_ability_or_not(self, player, ability: CardCapability):
        """ 进入询问是否进入使用能力（出完牌进入该流程） """
        if not self.flow_status_is_equal(FlowStatus.T_IN_TURN_TO):
            return

        self.__cur_ability = ability

        if ability == CardCapability.C6:
            if await self.guan_yin_auto_do_only_select_one(player):
                return await self.turn_next()

        wait_sec = 20
        data = {
            "seat_id": player.seat_id,
            "seconds": wait_sec,
            "ability": ability,
        }
        dm = use_ability_obj(data)
        await self.inner_broadcast(CmdRoom.TURN_TO, dm)

        if player.is_robot:
            self.call_flow_robot(2, self.robot_auto_do_ability, player, ability)

        if ability == CardCapability.C6:
            self.call_flow(wait_sec, self.timeout_guan_yin_complement_cards, player)
            self.call_flow_trustee(0, self.timeout_guan_yin_complement_cards, player)
            return

        if player.trustee:
            # await self.delay_func(1, self.turn_next)
            return await self.turn_next()
        self.call_flow(wait_sec, self.turn_next)

    async def guan_yin_auto_do_only_select_one(self, player):
        """ 观音自动执行，当仅有1种情况选择 """
        c_info = {}
        if self.__area_prentice and not self.__area_master and self.poker.left_count <= 0:
            c = self.__area_prentice[-1]
            c_info = {'c': c, 'a': CardArea.PRENTICE}
        elif self.__area_master and not self.__area_prentice and self.poker.left_count <= 0:
            c = self.__area_master[-1]
            c_info = {'c': c, 'a': CardArea.MASTER}
        elif not self.__area_prentice and not self.__area_master and self.poker.left_count > 0:
            c = self.poker.pop()
            c_info = {'c': c, 'a': CardArea.COMMON}

        if c_info:
            player.rev_card(c_info['c'])
            self.info_log(player.uid, "打出观音只有1个选项，直接执行")
            await self.__notify_complement_cards(player, [c_info], CardCapability.C6)
            return True
        return False

    async def timeout_guan_yin_complement_cards(self, player):
        """ 打出观音超时补牌 """
        c_info = {}
        if self.__area_master:
            # c = self.__area_master.pop()
            c = self.__area_master[-1]
            c_info = {'c': c, 'a': CardArea.MASTER}
        elif self.__area_prentice:
            # c = self.__fill_card_from_prentice()
            c = self.__area_prentice[-1]
            c_info = {'c': c, 'a': CardArea.PRENTICE}
        else:
            c = self.poker.pop()
            if c:
                # 其余的公共区补
                c_info = {'c': c, 'a': CardArea.COMMON}  # todo: 不够补牌？

        if c_info:
            player.rev_card(c_info['c'])
            self.info_log(player.uid, "打出观音超时补牌")
            await self.__notify_complement_cards(player, [c_info], CardCapability.C6)

        await self.turn_next()

    def cal_tribulation_val(self):
        """ 计算磨难值 """
        area_monster_score = len(self.__area_monster) * CARD_CAMP_SCORE.get(CardArea.MONSTER)
        area_prentice_score = len(self.__area_prentice) * CARD_CAMP_SCORE.get(CardArea.PRENTICE)
        area_master_score = len(self.__area_master) * CARD_CAMP_SCORE.get(CardArea.MASTER)
        area_divine_score = len(self.__area_divine) * CARD_CAMP_SCORE.get(CardArea.DIVINE)
        tribulation_val = area_monster_score + area_prentice_score + area_master_score + area_divine_score
        return tribulation_val

    async def calc_score_by_camp(self, p: Player):
        """ 阵营算分 """
        # 将4个虚拟区域中的所有牌放到自己磨难区
        # all_play_cards_area = []
        # all_play_cards_area.extend(self.__area_monster)
        # all_play_cards_area.extend(self.__area_prentice)
        # all_play_cards_area.extend(self.__area_master)
        # all_play_cards_area.extend(self.__area_divine)
        # p.add_tribulation(all_play_cards_area)

        tribulation_val = self.cal_tribulation_val()
        self.info_log(p.uid, "捡牌", tribulation_val)

        await self.do_checkout(p, tribulation_val)

        # 重新分配一个新的空列表, 之前的自动垃圾回收
        self.__area_monster, self.__area_prentice, self.__area_master, self.__area_divine = [], [], [], []
        self.__area_prentice_c2c.clear()
        self.__cur_cards_area.clear()
        self.clear_turn_cards()  # 清除turn cards

    async def do_checkout(self, p, tribulation_val, forward_t_val=None, tigger_interact=True):

        forward_t_val = forward_t_val or tribulation_val
        p.add_tribulation_val(tribulation_val)

        other = tribulation_val * self.base_score
        mine = -other * (self.max_player_count - self.ren_shu_count - 1)

        t_val_multiple = self.get_t_val_multiple(forward_t_val)  # 磨难值倍率都根据场上的磨难值算
        other = int(other * t_val_multiple)
        mine = int(mine * t_val_multiple)

        if not p.free_loss and p.gold + mine < 0:
            # 玩家自身元宝不足扣除 捡牌玩家向上取整
            mine = -p.gold
            other = int(p.gold // (self.max_player_count - self.ren_shu_count - 1))  # 得分玩家向下取整

        # todo: 下发通知
        notify_info = {
            'seat_id': p.seat_id,
            'tribulation_val': tribulation_val,
            # 'room_tribulation_val': self.cal_tribulation_val(),
        }
        await self.instant_checkout(
            p, mine, other, notify_info, ReasonCostGold.CHECK_OUT_MONSTER_SECOND, tigger_interact)
        data_model = S2CPickCardsSequel.pb_model(**notify_info)
        await self.inner_broadcast(CmdRoom.PICK_CARDS, data_model)

    def judge_is_win_or_lose(self, field: str = 'tribulation_val'):
        return super().judge_is_win_or_lose(field)

    async def turn_end(self, after_pick=False):
        """ 重写turn end """
        after_pick = False if self.__cur_ability == CardCapability.C2 else after_pick
        await super(Room, self).turn_end(after_pick)

    async def player_play_cards(self, p: Player, cards: list):
        """ 玩家出牌 """
        if not self.flow_status_is_equal(FlowStatus.T_IN_TURN_TO):
            return StaCode.FORBID, "现在还不能出牌"
        if p.seat_id != self.curr_seat_id:
            return StaCode.NOT_YOUR_TURN, "未轮到你"
        if p.operand > 0:
            return StaCode.FORBID, "请勿重复操作"

        # 当前合法出牌已算出，不再重复校验（注意这里的cards传递的是索引）
        if len(cards) != 1:
            return StaCode.FORBID, "出牌不符合规则"
        if not (0 <= cards[0] < len(self.__cur_legal_actions)):
            return StaCode.FORBID, "请选择合适的出牌"

        p.add_operand()
        # cards = [Cards.find_member_by_val(card) for card in cards]
        cards = self.__cur_legal_actions[cards[0]]
        p.rm_cards(cards)

        cards_area = self.__add_card_to_area(cards)  # 打出的牌放到对应出牌区
        ability, extra_res = self.do_specific_ability(p, cards)

        turn_cards = [p.seat_id, cards]
        self.add_turn_cards(turn_cards)
        self.add_table_cards(turn_cards)
        self.info_log(p.uid, "出牌成功: ", cards)

        skill_index = self.get_skill_movie_index_by_player_equip(p, cards)

        t_val = self.cal_tribulation_val()
        data = {
            "tribulation_val": t_val,
            "ability": ability,
            "skill_index": skill_index,
            "cards_area": cards_area,
            "turn_card": turn_cards,
            "t_val_multiple": str(self.get_t_val_multiple(t_val)),
        }
        dm = S2CPlayCardsSeq.pb_model(**data)
        await self.inner_broadcast(CmdRoom.PLAY_CARDS, dm)  # 注意下面金角银角磨难值会再变一次，所以顺序可以先下发出牌

        cards_len = len(cards)
        if ability == CardCapability.C5:
            await self.use_ability_take_card_from_area_prentice(p)
        else:
            if ability == CardCapability.C2:
                last_play_cards = extra_res
                await self.use_ability_let_last_play_cards_to_self_tribulation_area(p, last_play_cards)
            # 打出观音时自行选择区域补牌
            if cards_len != 1 or cards[0] != Cards.HT_K:
                cards_list_map = self.complement_cards(p, cards)  # 根据打出的牌补牌
                if ability == CardCapability.C8:  # 猪八戒补小白龙在此处下发补牌
                    cards_list_map.extend([{'c': Cards.HT_Q, 'a': CardArea.DIVINE} for _ in range(extra_res)])

                if cards_list_map:
                    await self.__notify_complement_cards(p, cards_list_map)

        # 上家打出佛祖奔波儿霸霸波儿奔组合
        if cards_len == 1 and cards[0] == Cards.HT_A or cards_len == 2 and Rule.is_ben_bo_er_ba_and_ba_bo_er_ben(cards):
            next_player = self.next_player(p.seat_id)
            await self.robot_do_interact_emoticon(
                next_player, p.seat_id, InteractType.AFTER_PLAYED_BUDDHA_BEN_BO_ER_BA_COMB)

        return StaCode.PASS, ''

    async def player_pick_cards(self, p: Player):
        """ 玩家要不起 """
        if not self.flow_status_is_equal(FlowStatus.T_IN_TURN_TO):
            return StaCode.FORBID, "现在还不能出牌"
        if p.seat_id != self.curr_seat_id:
            return StaCode.NOT_YOUR_TURN, "未轮到你"
        if p.operand > 0:
            return StaCode.FORBID, "请勿重复操作"
        if not self.turn_cards:
            return StaCode.FORBID, "首出不能捡牌"

        p.add_operand()

        await self.calc_score_by_camp(p)

        if self.poker.left_count == 0:
            await self.enter_round_over()
            return StaCode.PASS, ''

        # todo: 下发磨难区的牌？
        if p.gold <= 0:
            self.call_flow(0, self.notify_is_revenge, p)
        else:
            self.call_flow(2, self.turn_end, True)
        return StaCode.PASS, ''

    async def player_do_use_ability(self, p: Player, data):
        """ 玩家执行能力 """
        if not self.flow_status_is_equal(FlowStatus.T_IN_TURN_TO):
            return StaCode.FORBID, "当前不能执行牌能力"
        if p.seat_id != self.curr_seat_id:
            return StaCode.NOT_YOUR_TURN, "未轮到你"
        if self.__cur_ability == 0:
            return StaCode.FORBID, "当前无可执行的能力"
        if p.operand == 0:
            return StaCode.FORBID, "操作顺序有误，请先出牌"
        if p.operand > 1:
            return StaCode.FORBID, "请勿重复操作"

        p.add_operand()

        if self.__cur_ability == CardCapability.C4:
            ability_reverse_model.ParseFromString(data)
            if ability_reverse_model.yes:
                await self.use_ability_let_game_reverse()
        elif self.__cur_ability == CardCapability.C6:
            ability_select_area_model.ParseFromString(data)

            if ability_select_area_model.area == CardArea.COMMON:
                if self.poker.left_count == 0:
                    return StaCode.FORBID, "请选择正确的区域"
                cards_pool = self.poker
                cards_area = CardArea.COMMON
            elif ability_select_area_model.area == CardArea.PRENTICE:
                if not self.__area_prentice:
                    return StaCode.FORBID, "请选择正确的区域"
                cards_pool = self.__area_prentice
                cards_area = CardArea.PRENTICE
            elif ability_select_area_model.area == CardArea.MASTER:
                if not self.__area_master:
                    return StaCode.FORBID, "请选择正确的区域"
                cards_pool = self.__area_master
                cards_area = CardArea.MASTER
            else:
                return StaCode.FORBID, "请选择正确的区域"

            if ability_select_area_model.area == CardArea.COMMON:
                c = cards_pool.pop()
            else:
                c = cards_pool[-1]
            p.rev_card(c)
            await self.__notify_complement_cards(p, [{'c': c, 'a': cards_area}], CardCapability.C6)

        return StaCode.PASS, ''

    @staticmethod
    def serialize_player_info(room_player_info):
        return S2CPlayerInfo04MonsterSeq.pb_model(room_player_info)

    def serialize_room_info(self):
        room_info = self.room_info()
        return S2CRoomInfo03MonsterSeq.pb_model(**room_info)

    def room_info(self):
        """ 房间信息 """
        data = super().room_info()
        t_val = self.cal_tribulation_val()
        data["turn_cards"] = self.turn_cards
        data["area_monster"] = self.__area_monster
        data["area_prentice"] = self.__area_prentice
        data["area_master"] = self.__area_master
        data["area_divine"] = self.__area_divine
        data["tribulation_val"] = t_val
        data["cards_len"] = self.poker.left_count
        data["reverse"] = self.__next_reverse
        data["cards_area"] = self.__cur_cards_area

        curr_player = self.curr_player()
        if (curr_player and not curr_player.is_robot and
                self.flow_status_is_equal(FlowStatus.T_IN_TURN_TO) and self.left_seconds() > 0):
            data["legal_actions"] = self.__cur_legal_actions

        data["t_val_multiple"] = str(self.get_t_val_multiple(t_val))
        data["mean_gold_base"] = self.mean_gold_base
        return data

    def clear_room(self):
        self.__area_monster = []  # 妖怪区
        self.__area_prentice = []  # 徒弟区
        self.__area_master = []  # 师傅区
        self.__area_divine = []  # 神仙区

        self.__area_prentice_c2c = {}  # 徒弟区域的card2count（主要为了记录真假悟空）
        self.__next_reverse = False

        self.__cur_legal_actions = []  # 当前合法动作
        self.__cur_ability = 0  # 当前能力
        self.__cur_cards_area = []  # 当前出牌到哪些区域（客户端断线重连需要）

        super().clear_room()

    def refresh_room_conf(self, room_conf, **extra_room_info):
        super(Room, self).refresh_room_conf(room_conf, **extra_room_info)
