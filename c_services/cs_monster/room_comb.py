import math
import asyncio
import random

import ws_leisure_pb2
from c_services.base.base_leisure_room import BaseLeisureRoom
from c_services.base.base_player import BasePlayer
from c_services.const.cs_enum_const import RoomStatus, CmdRoom
from c_services.cs_monster.const import FlowStatus, InteractType, INITIATIVE_INTERACT
from common.proto.py_pb2.ws_leisure import S2CRoundOver
from common.public.enum_const import StaCode
from common.utils.kit_async import DelayCall
from common.utils.utils import UtilsTool
from lucky_game.const import ReasonCostGold, SeasonStatus, QuickChatType, InteractPropType, PayType
from lucky_game.model_rc.conf_quick_chat import ConfQuickChatRC


class RoomComb(BaseLeisureRoom):
    def __init__(self, tid, service, room_conf, extra_room_info, poker):
        super().__init__(tid, service, room_conf, extra_room_info, poker)
        self.__turn_cards = []
        self.__table_cards = []
        rule_conf = room_conf.get("rule_conf", {})
        self.__cards_count = rule_conf.get("cards_count") or 7
        self.__ranking_addition_at_session = room_conf.get("ranking_addition") or 0
        self.__ranking_addition_win_streak = rule_conf.get("win_streak_addition") or {}
        self.__limit_ra_win_streak = int(
            max(self.__ranking_addition_win_streak)) if self.__ranking_addition_win_streak else 6
        self.__ranking_addition_mvp = rule_conf.get("mvp_addition") or 5

        # 2025/3/22 数值变动
        self.__double_base = room_conf.get("rule_conf", {}).get("double_base", {}).get(str(self.level))
        t_val_multiple = room_conf.get("rule_conf", {}).get("tribulation_val_multiple", {})
        self.__t_val_multiple = {int(key): value for key, value in t_val_multiple.items()}
        self.__mean_gold_base = 0

        self.__interact_threshold = room_conf.get("rule_conf", {}).get("interact_threshold") or 6  # 机器人互动表情磨难值阈值

    @property
    def turn_cards(self):
        return self.__turn_cards

    def add_turn_cards(self, cards: list):
        self.__turn_cards.append(cards)

    def clear_turn_cards(self):
        self.__turn_cards.clear()

    @property
    def table_cards(self):
        return self.__table_cards

    def add_table_cards(self, cards: list):
        self.__table_cards.append(cards)

    def clear_table_cards(self):
        self.__table_cards.clear()

    @property
    def ranking_addition_mvp(self):
        return self.__ranking_addition_mvp

    @property
    def mean_gold_base(self):
        return self.__mean_gold_base

    async def round_start(self, *args, **kwargs):
        await super().round_start(*args, **kwargs)
        # self.__mean_gold_base = max(sum(self.record_ori_gold.values()) // self.max_player_count // self.__double_base, 1)
        self.__mean_gold_base = 1
        self.base_score = self.base_score * self.__mean_gold_base

    def get_t_val_multiple(self, t_val):
        """ 获取场上磨难值倍数 """
        for key, multiple in sorted(self.__t_val_multiple.items(), key=lambda x: x[0], reverse=True):
            if t_val >= key:
                return multiple
        return 1

    async def inner_deal_cards(self, set_dealer_card=None):
        self.set_flow_status(FlowStatus.T_IN_DEAL_CARDS)
        all_cards = self.poker.deal_cards(self.max_player_count, self.__cards_count)
        await self.do_deal_cards(all_cards, set_dealer_card, {"mean_gold_base": self.mean_gold_base})
        # 下发消息
        await self.turn_start(first=True)

    async def deal_cards(self, set_dealer_card=None):
        """ 发牌 """
        if not self.flow_status_is_equal(FlowStatus.T_IN_IDLE):
            self.log_info(f"flow error: {self.flow_status}")
            return
        await self.inner_deal_cards(set_dealer_card)

    async def turn_start(self, last_player=None, first=False):
        """ 一轮开始 """
        if not self.in_flow_status(FlowStatus.T_IN_DEAL_CARDS, FlowStatus.T_IN_TURN_TO, FlowStatus.T_IN_RECHARGE):
            self.log_info(f"flow error: {self.flow_status}")
            return
        if self.flow_status == FlowStatus.T_IN_RECHARGE:
            if self.ren_shu_count == self.max_player_count - 1:
                self.log_info("剩一人，其余玩家皆认输")
                return await self.enter_round_over(is_force=True)
            # next_player = self.next_player(last_player.seat_id)
            # if not next_player:
            #     self.log_info("都没牌了，直接结束")
            #     return await self.enter_round_over(is_force=True)

        self.set_flow_status(FlowStatus.T_IN_TURN_TO)
        self.__turn_cards = []
        turn_player = self.dealer() if first else last_player
        # self.log_info("turn_start", turn_player.seat_id)
        await self.turn_to_someone(turn_player)

    async def turn_next(self):
        await self.turn_to_someone(self.next_player(self.curr_seat_id))

    async def turn_to_someone(self, player):
        pass

    async def player_play_cards(self, player, cards) -> (StaCode, str):
        """ 玩家出牌 """

    def cal_tribulation_val(self) -> int:
        """ 计算当前磨难值 """

    def last_player(self, *args, **kwargs) -> BasePlayer or None:
        pass

    async def do_play_cards(self, player, cards: list, desc=""):
        code, msg = await self.player_play_cards(player, cards)
        self.log_info(player.uid, desc, code, msg)
        if code == StaCode.PASS:
            return await self.turn_next()

    async def time_out_play_card(self, player, desc=""):
        if not self.flow_status_is_equal(FlowStatus.T_IN_TURN_TO):
            return
        if player.seat_id != self.curr_seat_id:
            return
        self.log_info(player.uid, "超时出牌：", player.trustee, desc)
        not player.trustee and await super().do_trustee(player)
        await self.play_card_by_rand(player)

    async def robot_do_interact_emoticon(self, player, to_seat_id, interact_type: InteractType):
        """ 机器人做互动表情 """
        if not player:
            return
        if not player.is_robot:
            return
        if player.is_out:
            return
        if interact_type in INITIATIVE_INTERACT:  # 主动仍的再加一层磨难值判断
            t_val = self.cal_tribulation_val()
            if t_val < self.__interact_threshold:
                return

        DelayCall(random.randint(2, 4), self.__robot_do_interact, player, to_seat_id, interact_type).start()

    async def __robot_do_interact(self, player, to_seat_id, interact_type: InteractType):
        if self.room_status != RoomStatus.T_PLAYING:
            return
        conf = self.robot_interact.get(interact_type)
        if not conf:
            return
        chat_id_list = conf.get("chat_id_list")
        prob = conf.get("prob")
        if prob > 100:
            return
        flag = UtilsTool.select_element_by_prob({1: prob, 2: 100 - prob})
        if flag == 2:
            return
        chat_id = random.choice(chat_id_list)
        data_list = await ConfQuickChatRC.cache_by_chat_type()
        for one_data in data_list:
            if one_data.get("chat_id") == chat_id:
                break
        else:
            return

        pay_type = one_data.get("pay_type")
        quick_chat_model = ws_leisure_pb2.C2SQuickChat()
        quick_chat_model.send_seat_id = player.seat_id
        quick_chat_model.rec_seat_id = to_seat_id
        quick_chat_model.chat_id = chat_id
        quick_chat_model.chat_type = QuickChatType.HU_DONG
        quick_chat_model.pay_type = pay_type
        if pay_type == PayType.BY_GOLD:
            player.gold -= one_data.get("price", 0)
            quick_chat_model.res_count = str(player.gold)

        await self.send_quit_chat(player.seat_id, to_seat_id, one_data, quick_chat_model)

    async def send_quit_chat(self, send_seat_id, recv_seat_id, chat_info, m):
        send_player = self.get_player_by_seat_id(send_seat_id)
        player = self.get_player_by_seat_id(recv_seat_id)
        if not send_player.is_robot and player.is_robot:  # 仅真人发给机器人时触发
            if chat_info.get("prop_type") == InteractPropType.GOOD:
                interact_type = InteractType.AFTER_RECV_GOOD_PROP
            else:
                interact_type = InteractType.AFTER_RECV_BAD_PROP
            await self.robot_do_interact_emoticon(player, send_seat_id, interact_type)

        await self.inner_broadcast(CmdRoom.BROADCAST_CHAT, m)

    async def notify_is_revenge(self, player):
        """ 判断是否复仇"""
        # 判断破产玩家，弹出充值，充值继续，不充值认输
        self.set_flow_status(FlowStatus.T_IN_RECHARGE)
        await super().notify_is_revenge(player)

    async def instant_checkout(
            self, p, mine, other, notify_info: dict, reason_cost: ReasonCostGold, tigger_interact=True):
        """ 即时结算 """
        player_info = []
        update_task = []
        for other_p in self.seats:
            if other_p.is_out:
                continue
            if other_p.seat_id == p.seat_id:
                win_score = mine
            else:
                win_score = other

            other_p.add_actual_score(win_score)

            if not other_p.is_robot:
                # 免输卡、翻倍卡对结算的影响
                if win_score < 0:
                    if other_p.free_loss:
                        other_p.add_free_loss_num(abs(win_score))
                        continue
                else:
                    if other_p.checkout_multiple > 1:  # 系统额外赠送 checkout_multiple - 1倍数
                        addition_num = win_score * (other_p.checkout_multiple - 1)
                        win_score += addition_num
                        other_p.add_multiple_card_addition_num(addition_num)

                update_task.append(self.update_user_gold(other_p, win_score, reason_cost))

            other_p.update_gold(win_score)
            tmp_info = {
                "seat_id": other_p.seat_id,
                "win_gold": win_score,
                "res_gold": other_p.gold
            }

            player_info.append(tmp_info)

        if update_task:
            await asyncio.gather(*update_task)
        notify_info["check_infos"] = player_info

        if not tigger_interact:
            return

        # 道具互动：
        last_player = self.last_player(p.seat_id, with_cards=False)
        if not last_player:
            return
        if p.is_robot:
            await self.robot_do_interact_emoticon(p, last_player.seat_id, InteractType.AFTER_PICK_CARDS_SELF)

        for other_p in self.seats:
            if other_p.is_out:
                continue
            if other_p.seat_id == p.seat_id:
                continue
            if other_p.seat_id == last_player.seat_id:
                continue
            if not other_p.is_robot:
                continue
            await self.robot_do_interact_emoticon(other_p, last_player.seat_id, InteractType.AFTER_PICK_CARDS_OTHER)

    @staticmethod
    def __skin_ranking_addition(p, digit=3) -> float:
        num = 0.0
        for _, info in p.skin_equip_info.items():
            num += info.get("sr_addition")
        return round(num, digit)  # 保留三位小数

    def do_check_ranking_score(self, mvp_seat_id):
        """ 结算排位分 """
        # 1.输赢段位分
        for p in self.seats:
            if p.is_robot:
                continue
            if p.is_win > 0:
                ranking_score = p.ranking_win_score
                # 加修卡|场次加成|连胜加成(数值)|vip加成|终身卡|法相
                prop_addition = p.ranking_addition
                session_addition = self.__ranking_addition_at_session
                vip_addition = p.ranking_addition_vip
                lifetime_card_addition = p.ranking_addition_lifetime_card
                sr_addition = self.__skin_ranking_addition(p)  # 法相（皮肤）加成
                all_addition = (prop_addition + session_addition + vip_addition + lifetime_card_addition + sr_addition)

                all_addition = round(all_addition, 3)
                all_addition_score = ranking_score * all_addition
                all_addition_score = math.ceil(all_addition_score)  # 向上取整

                win_streak = p.win_streak + 1
                p.win_streak = win_streak

                if win_streak > self.__limit_ra_win_streak:
                    win_streak = self.__limit_ra_win_streak
                win_streak_addition_score = self.__ranking_addition_win_streak.get(str(win_streak)) or 0

                mvp_score = 0
                if p.seat_id == mvp_seat_id:
                    mvp_score = self.__ranking_addition_mvp

                p.ranking_score = ranking_score + all_addition_score + win_streak_addition_score + mvp_score
                self.log_info(
                    p.uid, "段位分结算：",
                    prop_addition, session_addition, vip_addition, lifetime_card_addition, sr_addition, all_addition,
                    win_streak_addition_score, mvp_score, ranking_score, p.ranking_score
                )
                p.set_check_info_ranking(self.__ranking_addition_at_session, win_streak_addition_score, sr_addition)
            else:
                p.win_streak = 0
                lose_score = p.ranking_lose_score
                if p.ranking_score_free_loss:
                    p.add_ranking_score_free_num(lose_score)
                    continue
                p.ranking_score = -lose_score
                self.log_info(p.uid, "段位分结算：", p.ranking_score)

    def judge_is_win_or_lose(self, field: str = 'pick_len'):
        """
        根据净胜张判断玩家此局输还是赢
        """
        pick_map = {p.uid: getattr(p, field) for p in self.seats}
        pick_map_copy = {**pick_map}
        sum_len = sum(pick_map.values())
        for p in self.seats:
            if p.is_out:
                pick_map_copy.pop(p.uid)
                continue
            if p.is_robot:
                continue
            if sum_len - (getattr(p, field) * self.max_player_count) >= 0:  # 其余人捡牌数 - 自己捡牌数*3 = 总捡牌数 - 自己捡牌数*4
                p.is_win = 1
            else:
                p.is_win = 0

        seat_id = self.__judge_mvp(pick_map_copy, field)
        self.log_info("mvp：", seat_id, pick_map, pick_map_copy)
        return seat_id

    def __judge_mvp(self, min_pick_map: dict, field):
        """ 判断mvp """
        min_pick_len = min(min_pick_map.values())
        # for seat_id in range(self.dealer_id, self.max_player_count + 1):
        #     if getattr(self.seats[seat_id - 1], field) == min_pick_len:
        #         return seat_id
        #
        # for seat_id in range(self.dealer_id):
        #     if getattr(self.seats[seat_id - 1], field) == min_pick_len:
        #         return seat_id
        for p in self.seats:
            if p.is_out:
                continue
            if getattr(p, field) == min_pick_len:
                return p.seat_id
        return 0

    async def check_out(self):
        mvp_seat_id = self.judge_is_win_or_lose()
        if self.season_status == SeasonStatus.ACTIVE_SEASON:
            self.do_check_ranking_score(mvp_seat_id)
        player_info = self.room_win_lose_data()
        self.log_info('一局结束, 结算信息：', self.season_status)

        data = {
            "check_infos": player_info,
            "mvp": mvp_seat_id,
            "mvp_ranking_add": self.__ranking_addition_mvp,
            "season_status": self.season_status,
        }
        data_model = S2CRoundOver.pb_model(**data)
        await self.inner_broadcast(CmdRoom.ROUND_OVER, data_model)

    async def round_over(self, is_force=False):
        """ 一局结束 """
        if not is_force and not self.flow_status_is_equal(FlowStatus.T_IN_SHOU_PAI):
            return
        self.set_room_status(RoomStatus.T_CHECK_OUT)
        self.set_flow_status(FlowStatus.T_IN_CHECK_OUT)

        await self.check_out()

        await self.game_over(is_force)

    async def enter_round_over(self, is_force=False):
        """ 进入一局结束 """
        self.set_flow_status(FlowStatus.T_IN_SHOU_PAI)
        await self.round_over(is_force)

    def clear_room(self):
        """ 清理房间 """
        self.__turn_cards.clear()
        self.__table_cards.clear()
        super().clear_room()

    def refresh_room_conf(self, service, room_conf, **extra_room_info):
        super().refresh_room_conf(service, room_conf, **extra_room_info)
        self.__ranking_addition_at_session = room_conf.get("ranking_addition") or 0
        rule_conf = room_conf.get("rule_conf", {})
        self.__ranking_addition_win_streak = rule_conf.get("win_streak_addition") or {}
        self.__limit_ra_win_streak = int(
            max(self.__ranking_addition_win_streak)) if self.__ranking_addition_win_streak else 6
        self.__ranking_addition_mvp = rule_conf.get("mvp_addition") or 5

        self.__double_base = room_conf.get("rule_conf", {}).get("double_base", {}).get(str(self.level))
        t_val_multiple = room_conf.get("rule_conf", {}).get("tribulation_val_multiple", {})
        self.__t_val_multiple = {int(key): value for key, value in t_val_multiple.items()}
        self.__mean_gold_base = 0

        self.__interact_threshold = room_conf.get("rule_conf", {}).get("interact_threshold") or 6
