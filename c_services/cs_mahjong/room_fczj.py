import asyncio
import random
from copy import deepcopy

from nsanic.libs import tool_dt
from nsanic.libs.tool import json_encode

from c_services.base.base_leisure_room import BaseLeisureRoom
from common.proto.py_pb2.ws_c2s import ding_que_model, gang_model, fan_ji_index_model
from common.proto.py_pb2.ws_leisure import S2CDealCardsMahjong, S2CStartDingQueInfo, S2CDingQueInfo, \
    S2CPublicOperatesMahjong, S2CTurnToMahjong, S2CHuBaseInfo, s2c_one_of_model, S2CMenInfoMahjong, s2c_recharge_model, S2CAfterGangMoCard, \
    S2CPlayCardsMahjong, S2CFirstJiMahjong, S2CGangInfo, S2CKouFen, S2CStartFanJi, S2CFanJi, S2CFanJiInfo, S2CRecordAccountInfo, \
    S2CFanJiScore, S2CRoundOverInfoByLeisure, S2CRoomInfo04Mahjong, S2CPlayerInfo05Mahjong, S2CRoundStartMahjong, S2CHuAfterCards, \
    S2CManyHuInfo
from common.public.conf import C_SERVICE_SECRET_KEY
from common.public.enum_const import StaCode, ServiceEnum
from common.utils.kit_async import DelayCall
from common.utils.utils import UtilsTool
from lucky_game.const import ReasonCostGold
from lucky_game.logic.activity import ReturnGift
from lucky_game.model_rc.records_game_room import RecordsGameRoomRC
from lucky_game.model_rc.records_game_segment import RecordsGameSegmentRC
from lucky_game.model_rc.records_game_total import RecordsGameTotalRC
from . import const
from .const import FlowStatus, PlayType, TimerDelay, ActionType, HuType, CardsType, ExtraHuPai, CheckType, OverType, RechargeType, JiType, \
    SeatRelation, JI_PAI_SCORE, PAI_XING_SCORE_MAP, EXTRA_SCORE_MAP
from .player_fczj import PlayerFCZJ
from .poker import Poker
from .rule_fc import RuleFc
from ..const.cs_enum_const import RoomStatus, CmdRoom, CmdRobotCal


class RoomFCZJ(BaseLeisureRoom):
    def __init__(self, tid, service, room_conf, **extra_room_info):

        self.__lai_zi_count = room_conf.get("rule_conf").get("lai_zi_count") or 4
        super().__init__(tid, service, room_conf, extra_room_info, Poker, self.__lai_zi_count)

        self.__deal_cards_count = 13
        self.__curr_card = 0
        self.__que_list = [1, 2, 3]
        self.__dice_num = None
        self.__lai_zi = CardsType.LAI_ZI
        self.__gang_hou_mo_pai = []
        self.__gang_hou_chu_pai = []
        self.__shao_ji_gang_seats = set()
        self.__player_actions = []  # 玩家动作
        self.__curr_card_exist = 0  # 当前牌是否存在
        self.__recharge_wait = 0
        self.__wait_recharge_seats = []
        self.__curr_action_player = None
        self.__jie_pao_count = -1
        self.__hua_zhu_seats = []  # 花猪玩家
        self.__no_jiao_pai_seats = []  # 未叫牌玩家
        self.__win_seat_list = []
        self.__fan_ji_list = [0, 1, 2, 3, 4]
        self.__can_fan_ji_seats = []  # 有资格捉鸡的玩家
        self.__fan_ji_cards = []  # 记录所有玩家翻的鸡牌
        self.__fan_ji_result = []  # 记录所有玩家翻的鸡牌，已计算+1或者金鸡
        self.__default_ji = {CardsType.YAO_JI, CardsType.WU_GU_JI}
        self.__zhuo_ji_cards = {}  # 记录捉鸡结算信息
        self.__chong_feng_ji_seat_id = 0  # 冲锋幺鸡玩家
        self.__chong_feng_wgj_seat_id = 0  # 冲锋乌骨鸡玩家
        self.__round_first_ji = 0  # 记录冲锋鸡
        self.__round_first_wgj = 0  # 记录冲锋乌骨鸡
        self.__ze_ren_ji_seat_id = 0  # 责任幺鸡玩家
        self.__ze_ren_ji_win_seat_id = 0
        self.__ze_ren_wgj_seat_id = 0  # 乌骨责任鸡玩家
        self.__ze_ren_wgj_win_seat_id = 0
        self.__before_seat_id = 0
        self.__after_peng = False
        self.__ji_pai_score_map = self.get_ji_pai_score_map()
        self.__pai_xing_score_map = self.get_pai_xing_score_map()
        self.__extra_score_map = self.get_extra_score_map()
        self.__record_id = 0


    async def round_start(self, *args, **kwargs):
        """ 一局开始 """
        await super().round_start()
        record_info = await RecordsGameRoomRC.create_record_game_room(self.tid, tool_dt.cur_time())
        self.__record_id = record_info[0].record_rid
        self.__dice_num = RuleFc.random_dice(2)
        self.dealer_turn()
        self.curr_seat_id = self.dealer_id
        self.set_flow_status(FlowStatus.T_IN_ROUND_START)
        self.__dice_num = RuleFc.random_dice(2)
        data = {"round_idx": self.round_idx, "dealer": self.dealer_id, "dice_num": self.__dice_num}
        data_model = S2CRoundStartMahjong.pb_model(**data)
        await self.inner_broadcast(CmdRoom.ROUND_START, data_model)
        await self.delay_func(1, self.deal_cards)

    async def deal_cards(self):
        """ 发牌 """
        if not self.flow_status_is_equal(FlowStatus.T_IN_ROUND_START):
            self.log_info(f"flow error: {self.flow_status}")
            return
        self.log_info("开始发牌")
        self.set_flow_status(FlowStatus.T_IN_DEAL_CARDS)
        self.set_room_status(RoomStatus.T_PLAYING)
        self.poker.deal_good_cards(self.max_player_count)
        all_cards = self.poker.deal_cards(self.max_player_count, self.__deal_cards_count)
        data = {}
        c = self.poker.pop()  # 庄占起手，再摸一张
        for i, p in enumerate(self.seats):
            p.cards = all_cards[i]
            data["hand_cards"] = p.cards
            p.sort_cards()
            data["mo_pai"] = 0
            if p.seat_id == self.dealer_id:
                self.__curr_card = c
                p.rev_card(c)
                p.mo_pai = c
                data["mo_pai"] = c
            data["left_count"] = self.poker.left_count
            data_model = S2CDealCardsMahjong.pb_model(**data)
            self.log_info("玩家手牌", p.cards, "座位号", p.seat_id)
            await self.inner_send(p, CmdRoom.DEALER_CARDS, data_model)
        self.call_flow(1, self.start_ding_que)

    async def start_ding_que(self):
        if not self.room_status_is_equal(RoomStatus.T_PLAYING):
            return StaCode.FLOW_ERR, "桌子状态不可定缺"
        self.set_flow_status(FlowStatus.T_IN_DING_QUE)
        data = {
            "ding_que_list": self.__que_list,
            "seconds": TimerDelay.DING_QUE_TIME
        }

        re_times = 0
        start_rs = [1, 2, 3, 4]
        random.shuffle(start_rs)

        for p in self.seats:
            if not p.is_robot:
                recommend_que = self.get_ding_que_suit(p.cards)
                data["recommend_que"] = recommend_que
                data_model = S2CStartDingQueInfo.pb_model(**data)
                await self.inner_send(p, CmdRoom.START_DING_QUE, data_model)

        for p in self.seats:
            if p.is_robot:
                print("机器人定缺", p.seat_id)
                if p.que == 0:
                    DelayCall(start_rs[re_times], self.robot_auto_ding_que, p).start()
                    re_times += 1
                continue

        self.call_flow(TimerDelay.DING_QUE_TIME, self.ding_que_time_out)

    async def ding_que_time_out(self):
        if not self.flow_status_is_equal(FlowStatus.T_IN_DING_QUE):
            return StaCode.FLOW_ERR
        for p in self.seats:
            if p.is_out or p.que != 0:
                continue
            await self.do_trustee(p)
            que = self.get_ding_que_suit(p.cards)
            ding_que_model.que = que  # 设置 card 值
            serialized_data = ding_que_model.SerializeToString()
            code, _ = await self.on_player_ding_que(p, serialized_data)
            if code != StaCode.PASS:
                self.log_info("超时定缺错误", code)
                return
        self.call_flow(1, self.start_game_after_ding_que)

    async def robot_auto_ding_que(self, p: PlayerFCZJ):
        if self.flow_status != FlowStatus.T_IN_DING_QUE:
            return StaCode.FLOW_ERR
        que = self.get_ding_que_suit(p.cards)
        ding_que_model.que = que  # 设置 card 值
        print("que", que)
        serialized_data = ding_que_model.SerializeToString()
        code, _ = await self.on_player_ding_que(p, serialized_data)
        if code != StaCode.PASS:
            self.log_info("机器人自动定缺错误", code)

    def get_ding_que_suit(self, cards):
        """ 策略：采用当前手牌花色最少的card """
        if len(cards) < 13:
            return StaCode.RULE_ERR  # 出牌不符合规则
        suit_count = self.poker.cal_card_suit_count(cards)  # 计算同种花色出现的次数
        counts = {suit: suit_count.get(suit, 0) for suit in self.__que_list}
        min_suit = min(counts, key=counts.get)
        return min_suit

    async def on_player_ding_que(self, player: PlayerFCZJ, data):
        ding_que_model.ParseFromString(data)
        que = ding_que_model.que
        if not self.flow_status_is_equal(FlowStatus.T_IN_DING_QUE):
            return StaCode.FLOW_ERR, "不在定缺流程中"
        if self.play_type != PlayType.LEISURE_FCZJ:
            return StaCode.RULE_ERR, "当前玩法不存在定缺"
        if player.que != 0:
            return StaCode.ALREADY_DO, "当前玩家已经定缺过了"
        if player.is_out:
            return StaCode.FLOW_ERR, "当前玩家已经淘汰了"
        if que not in self.__que_list:
            return StaCode.RULE_ERR, "参数错误，不在定缺范围内"

        player.que = que
        data = {
            "que": player.que,
            "seat_id": player.seat_id,
        }
        data_model = S2CDingQueInfo.pb_model(**data)
        await self.inner_send(player, CmdRoom.PLAYER_DING_QUE, data_model)
        is_all_ding_que = True
        for p in self.seats:
            if p.que == 0:
                is_all_ding_que = False
                break
        if is_all_ding_que:
            for p in self.seats:
                if p.is_out:
                    continue
                data = {
                    "que": p.que,
                    "seat_id": p.seat_id,
                }
                data_model = S2CDingQueInfo.pb_model(**data)
                await self.inner_broadcast(CmdRoom.PLAYER_DING_QUE, data_model)
            self.call_flow(1, self.start_game_after_ding_que)
        return StaCode.PASS, ""

    async def on_player_men(self, player: PlayerFCZJ):
        self.log_info("on_player_men")
        if not self.room_status_is_equal(RoomStatus.T_PLAYING):
            return StaCode.FLOW_ERR, "桌子状态不在游戏中，不可闷"
        if player.is_out:
            return StaCode.FLOW_ERR, "玩家已被淘汰，不可闷"
        if self.flow_status not in (FlowStatus.T_IN_CHU_PAI, FlowStatus.T_IN_MO_PAI, FlowStatus.T_IN_MO_PAI_CALL,
                                    FlowStatus.T_IN_PUBLIC_OPRATE, FlowStatus.T_IN_TIAN_HU,):
            return StaCode.FLOW_ERR, "当前流程不可闷"
        if player.seat_id != self.curr_seat_id:
            return StaCode.NOT_YOUR_TURN, "当前没有轮到该玩家"
        if player.mo_pai == 0:
            self.log_info(self.tid, player.uid, "当前非玩家摸牌阶段")
            return StaCode.FLOW_ERR, "当前非玩家摸牌阶段"
        if self.has_do_by_action(player, [ActionType.ACTION_TYPE_MEN]):  # 不能再次操作
            self.log_info(self.tid, player.uid, "men------重复操作不对：", self.flow_status)
            return StaCode.RULE_ERR, "不能再次操作"
        if not player.is_action_in_operates(ActionType.ACTION_TYPE_MEN):
            return StaCode.RULE_ERR, "玩家没有操作没有闷"

        self.save_player_action(player, ActionType.ACTION_TYPE_MEN)
        data = {"seat_id": player.seat_id, "is_finish": 0}
        data_model = S2CHuBaseInfo.pb_model(**data)
        if not player.is_robot:
            await self.inner_send(player, CmdRoom.PLAYER_MEN, data_model)
        self.log_info("player", player.uid, "choose men action did suc!")
        return StaCode.PASS, ""

    async def on_player_jian(self, player: PlayerFCZJ):
        self.log_info("on_player_jian")
        if not self.room_status_is_equal(RoomStatus.T_PLAYING):
            return StaCode.FLOW_ERR, "桌子状态不在游戏中，不可捡"
        if player.is_out:
            return StaCode.FLOW_ERR, "玩家已被淘汰，不可捡"
        if self.flow_status not in (FlowStatus.T_IN_PUBLIC_OPRATE, FlowStatus.T_IN_ZHUAN_WAN_GANG_PAI_CALL,
                                    FlowStatus.T_IN_TIAN_HU):
            return StaCode.FLOW_ERR, "当前流程不可捡"
        if not player.is_action_in_operates(ActionType.ACTION_TYPE_JIAN):
            return StaCode.RULE_ERR, "玩家没有可捡操作"

        self.save_player_action(player, ActionType.ACTION_TYPE_JIAN)
        self.log_info(self.tid, player.uid, player.seat_id, "choose jian action did suc!")
        return StaCode.PASS, ""

    async def on_player_pass(self, player: PlayerFCZJ):
        if not self.room_status_is_equal(RoomStatus.T_PLAYING):
            return StaCode.FLOW_ERR, "桌子状态不在游戏中"
        if self.flow_status not in (FlowStatus.T_IN_PUBLIC_OPRATE, FlowStatus.T_IN_MO_PAI_CALL,
                                    FlowStatus.T_IN_MING_GANG_PAI_CALL, FlowStatus.T_IN_ZHUAN_WAN_GANG_PAI_CALL,
                                    FlowStatus.T_IN_TIAN_HU, FlowStatus.T_IN_MO_PAI,):
            return StaCode.FLOW_ERR, "游戏流程不在可过流程"

        if self.has_do_by_action(player, ActionType.ACTION_TYPE_PASS):  # 不允许再次操作
            return StaCode.RULE_ERR, "已经操作过了"

        has_do_action = self.has_do_action(player)
        can_operates = player.can_operates()

        if can_operates and not has_do_action:
            self.log_info(self.tid, player.uid, "玩家有操作选择过：", len(player.men_cards))

        self.save_player_action(player, ActionType.ACTION_TYPE_PASS)
        player.operates = []
        one_of_model = s2c_one_of_model()
        one_of_model.seat_id = self.curr_seat_id
        if not player.is_robot:
            await self.inner_send(player, CmdRoom.PLAYER_PASS, one_of_model)
        return StaCode.PASS, ""

    async def on_player_gang(self, player: PlayerFCZJ, data):
        if not self.room_status_is_equal(RoomStatus.T_PLAYING):
            return StaCode.FLOW_ERR, "桌子状态不在游戏中,不可杠"
        if self.flow_status not in (FlowStatus.T_IN_PUBLIC_OPRATE, FlowStatus.T_IN_MO_PAI_CALL,
                                    FlowStatus.T_IN_TIAN_HU, FlowStatus.T_IN_TIAN_TING):
            return StaCode.FLOW_ERR, "当前流程不在可杠流程"
        gang_act = player.gang_in_operates()
        if not gang_act:
            return StaCode.RULE_ERR, "没有可杠操作"

        if gang_act in (ActionType.ACTION_TYPE_ZHUAN_WAN_GANG, ActionType.ACTION_TYPE_AN_GANG):
            gang_model.ParseFromString(data)
            card = gang_model.card or 0
            if player.check_zhuan_wan_gang(card):
                gang_act = ActionType.ACTION_TYPE_ZHUAN_WAN_GANG
            elif player.check_an_gang(card):
                gang_act = ActionType.ACTION_TYPE_AN_GANG
            else:
                self.log_info(self.tid, "玩家杠，参数错误", card, player.cards)
                return StaCode.RULE_ERR, "参数错误"

        self.__gang_hou_chu_pai = []
        self.save_player_action(player, gang_act, data)

        self.log_info(self.tid, player.uid, "choose gang action did suc!")
        return StaCode.PASS, ""

    async def on_player_peng(self, player: PlayerFCZJ):
        if not self.room_status_is_equal(RoomStatus.T_PLAYING):
            return StaCode.FLOW_ERR, "桌子状态不在游戏中,不可碰"
        if not self.flow_status_is_equal(FlowStatus.T_IN_PUBLIC_OPRATE):
            return StaCode.FLOW_ERR, "当前流程不在可碰流程"
        if not player.is_action_in_operates(ActionType.ACTION_TYPE_PENG):
            return StaCode.RULE_ERR, "没有可碰操作"

        data = {"seat_id": player.seat_id, "is_finish": 0}
        self.save_player_action(player, ActionType.ACTION_TYPE_PENG, data)
        self.log_info(self.tid, player.uid, "choose peng action did suc!")
        return StaCode.PASS, ""

    async def on_player_fan_ji(self, player: PlayerFCZJ, data):
        fan_ji_index_model.ParseFromString(data)
        fan_ji_index = fan_ji_index_model.fan_ji_index or 0
        if not self.flow_status_is_equal(FlowStatus.T_IN_FAN_JI):
            return StaCode.FLOW_ERR, "不在翻鸡流程"
        if player.fan_ji != 0:
            return StaCode.FLOW_ERR, "已经翻过鸡了"
        if fan_ji_index < 0 or fan_ji_index > 4:
            return StaCode.ERR_ARG, "参数有误"
        self.log_info("玩家翻鸡", player.seat_id, fan_ji_index)
        fan_ji_card = self.player_fan_ji_call(player, fan_ji_index)
        if fan_ji_card:
            fan_ji_result = {
                "seat_id": player.seat_id,
                "fan_ji_card": fan_ji_card,
            }
            fan_ji_model = S2CFanJi.pb_model(**fan_ji_result)
            await self.inner_send(player, CmdRoom.FAN_JI, fan_ji_model)

        is_all_choose = True

        for seat_id in self.__can_fan_ji_seats:
            p = self.get_player_by_seat_id(seat_id)
            if p.fan_ji <= 0:
                is_all_choose = False
                break

        if is_all_choose:
            data = []
            for p in self.seats:
                self.player_zhuo_ji_call(p)
                ji_result = {
                    "seat_id": p.seat_id,
                    "ji_cards": p.ji_pai,
                }
                data.append(ji_result)
            fan_ji_info = {
                "fan_ji_cards": self.__fan_ji_cards,
                "result": data,
            }
            fan_ji_model = S2CFanJiInfo.pb_model(**fan_ji_info)
            await self.inner_broadcast(CmdRoom.FAN_JI_INFO, fan_ji_model)
            self.call_flow(1.5, self.round_over)
        return StaCode.PASS, ""

    async def on_player_chu_pai(self, player: PlayerFCZJ, data):
        gang_model.ParseFromString(data)
        card = gang_model.card or 0
        if not self.room_status_is_equal(RoomStatus.T_PLAYING):
            return StaCode.RULE_ERR, "桌子状态不在游戏中，不可出牌"
        if self.flow_status not in (FlowStatus.T_IN_CHU_PAI, FlowStatus.T_IN_DI_HU_CHU_PAI,
                                    FlowStatus.T_IN_MO_PAI_CALL):
            desc = "当前有玩家选听中" if self.flow_status == FlowStatus.T_IN_TIAN_TING else "当前流程不在可出牌流程"
            return StaCode.FLOW_ERR, desc
        if self.curr_seat_id != player.seat_id:
            return StaCode.NOT_YOUR_TURN, "没有轮到你"
        if player.card_is_lock():
            if card not in player.get_out_not_lock_card():
                return StaCode.RULE_ERR, "出牌在锁定范围内，不可出"
        if card not in player.cards:
            return StaCode.RULE_ERR, "出牌不在手牌范围内，不可出"
        if player.cards_len % 3 != 2:
            return StaCode.RULE_ERR, "手牌数不对，不可出"

        player.chu_pai(card, True)
        self.log_info("玩家出牌", card, "座位号", player.seat_id)
        player.mo_pai = 0
        self.__curr_card = card
        self.__curr_card_exist = 1
        self.__before_seat_id = self.curr_seat_id
        self.__player_actions.clear()
        if player.card_is_lock():
            # 若玩家起手能胡选择天听不锁牌，此处再锁牌
            if len(player.ting_list) == 0:
                allow_hu_map = {HuType.DI_LONG_QI: True, HuType.JIN_GOU_DIAO: True,
                                HuType.QI_DUI: True}
                ting_list = RuleFc.get_ting_hu_list([], player.cards, allow_hu_map, self.__lai_zi,player.que)
                player.ting_list = ting_list
                player.lock_cards = deepcopy(player.cards)
                data = {"lock_cards": player.lock_cards}
                data_model = S2CTurnToMahjong.pb_model(**data)
                await self.inner_send(player, CmdRoom.PLAYER_TIAN_TING, data_model)
        play_card = {
            "seat_id": self.curr_seat_id,
            "card": self.__curr_card,
        }
        data_model = S2CPlayCardsMahjong.pb_model(**play_card)
        await self.inner_broadcast(CmdRoom.PLAY_CARDS, data_model)
        print("on_player_chu_pai end")
        return StaCode.PASS, ""

    async def player_give_up(self, player: PlayerFCZJ):
        if player.is_out or player.seat_id == -1:  # 防止超时延时走到这里再次执行
            return
        player.is_out = True
        m = s2c_one_of_model()
        m.seat_id = player.seat_id
        if player.lian_sheng <= 0:
            player.lian_sheng -= 1
        else:
            player.lian_sheng = -1
        self.__wait_recharge_seats.remove(player.seat_id)
        await self.inner_broadcast(CmdRoom.GIVE_UP, m)
        self.log_info(player.uid, player.seat_id, "放弃_fc")
        if self.ren_shu_count == self.max_player_count - 1:
            self.log_info("剩一人，其余玩家皆认输")
            cards_info = self.get_player_cards_info()
            cards_model = S2CHuAfterCards.pb_model(cards_info)
            await self.inner_broadcast(CmdRoom.HU_AFTER_CARDS_INFO, cards_model)
            return self.call_flow(1.0, self.round_over, OverType.OTHERS_GIVE_UP)
        if len(self.__wait_recharge_seats) == 0:
            self.call_flow(0.5, self.recharge_continue)

    def player_zhuo_ji_call(self, p: PlayerFCZJ):
        """统计捉鸡数"""
        if p.is_out:
            return

        ji_key = []
        # 1. 处理金鸡（独立逻辑）
        self.process_jin_ji(p, ji_key)

        # 2. 计算基础数据
        zhuo_ji_list = deepcopy(self.__fan_ji_result)
        count_list = RuleFc.get_card_to_count(zhuo_ji_list)  # 翻鸡计数
        p.calc_all_ji_pai(self.__default_ji, zhuo_ji_list) if p.fan_ji > 0 else p.get_bao_ji(self.__default_ji)
        # 3. 动态计算鸡牌类型
        all_ji_pai = p.ji_pai.copy()
        stand_ji = p.calc_stand_ji(self.__default_ji)
        stand_ji_card_count = RuleFc.get_card_to_count(stand_ji)  # 站鸡计数

        # 4. 处理冲锋鸡移除
        self.remove_chong_feng_ji(p, all_ji_pai)

        if all_ji_pai:
            p.ji_pai.extend(all_ji_pai)

            # 5.鸡牌分类处理
            for fan_ji in set(all_ji_pai):
                repeat_count = count_list.get(fan_ji, 1)
                stand_ji_count = stand_ji_card_count.get(fan_ji, 0)

                # 分类处理三种鸡牌类型
                if fan_ji in self.__default_ji:
                    self.process_default_ji(p, fan_ji, ji_key, all_ji_pai,
                                            repeat_count, stand_ji_count)
                elif p.fan_ji > 0:
                    self.process_fan_ji_pai(p, fan_ji, ji_key, all_ji_pai,
                                            repeat_count)

        self.__zhuo_ji_cards[p.seat_id] = ji_key

    def process_jin_ji(self, p: PlayerFCZJ, ji_key):
        """处理金鸡逻辑"""
        if p.fan_ji == JiType.JIN_JI:
            base_score = self.__ji_pai_score_map[JiType.JIN_JI]
            ji_pai = {
                "ji_card": JiType.JIN_JI.value,
                "ji_count": 1,
                "ji_score": base_score,
            }
            p.ji_pai.append(JiType.JIN_JI.value)
            ji_key.append(ji_pai)
            self.log_info(f"玩家:{p.uid} 金鸡", ji_pai)

    def remove_chong_feng_ji(self, p: PlayerFCZJ, all_ji_pai):
        """移除冲锋鸡牌"""
        if self.__chong_feng_ji_seat_id == p.seat_id:
            self.safe_remove_ji(all_ji_pai, CardsType.YAO_JI.value, "YAO_JI")
        if self.__chong_feng_wgj_seat_id == p.seat_id:
            self.safe_remove_ji(all_ji_pai, CardsType.WU_GU_JI.value, "WU_GU_JI")

    def safe_remove_ji(self, all_ji_pai, ji_type, log_name):
        """安全移除鸡牌并记录"""
        if ji_type in all_ji_pai:
            all_ji_pai.remove(ji_type)
        else:
            self.log_info(f"{log_name}不存在于all_ji_pai")

    def process_default_ji(self, p: PlayerFCZJ, fan_ji, ji_key, all_ji_pai,
                           repeat_count, stand_ji_count):
        """处理默认鸡牌（幺鸡/乌骨鸡）"""
        # 映射鸡牌类型到处理参数
        ji_map = {
            CardsType.YAO_JI.value: {
                "key": JiType.DEFAULT,
                "name": "幺鸡",
                "silver_name": "银幺鸡",
                "multiplier": 2 if fan_ji in self.__fan_ji_result else 1
            },
            CardsType.WU_GU_JI.value: {
                "key": JiType.WU_GU_JI,
                "name": "乌骨鸡",
                "silver_name": "银乌骨鸡",
                "multiplier": 2 if fan_ji in self.__fan_ji_result else 1
            }
        }

        params = ji_map.get(fan_ji)
        if not params:
            return

        # 统一计算逻辑
        base_score = self.__ji_pai_score_map[params["key"]] * params["multiplier"]
        count = all_ji_pai.count(fan_ji)
        ji_score = (base_score * count + base_score * stand_ji_count) * repeat_count

        ji_name = params["silver_name"] if params["multiplier"] > 1 else params["name"]

        ji_pai = {
            "ji_card": fan_ji,
            "ji_count": count,
            "ji_score": ji_score
        }
        ji_key.append(ji_pai)
        self.log_info(f"玩家:{p.uid} {ji_name}", ji_pai, f'重复数:{repeat_count} 站鸡数:{stand_ji_count}')

    def process_fan_ji_pai(self, p: PlayerFCZJ, fan_ji, ji_key, all_ji_pai, repeat_count):
        """处理翻牌鸡"""
        base_score = self.__ji_pai_score_map[JiType.FAN_PAI_JI]
        count = all_ji_pai.count(fan_ji)
        ji_score = base_score * count * repeat_count

        ji_pai = {
            "ji_card": fan_ji,
            "ji_count": count,
            "ji_score": ji_score
        }
        ji_key.append(ji_pai)
        self.log_info(f"玩家:{p.uid} 翻牌鸡", ji_pai, f'重复数:{repeat_count}')

    async def start_game_after_ding_que(self):
        self.curr_seat_id = self.dealer_id
        await self.enter_mo_pai_call()

    async def enter_mo_pai_call(self):
        self.log_info("enter_mo_pai_call", self.flow_status)
        if self.flow_status not in (FlowStatus.T_IN_MO_PAI, FlowStatus.T_IN_DEAL_CARDS,
                                    FlowStatus.T_IN_DING_QUE, FlowStatus.T_IN_MO_PAI_CALL):
            return
        self.set_flow_status(FlowStatus.T_IN_MO_PAI_CALL)

        curr_player = self.curr_player()
        self.__curr_card = curr_player.mo_pai

        seconds = TimerDelay.CALL_SECONDS
        data = {
            "seat_id": curr_player.seat_id,
            "left_count": self.poker.left_count,
            "seconds": seconds,
            "in_flow": self.flow_status,
        }
        operates, can_gang_list = self.calc_operates_after_mo_pai(curr_player)
        self.log_info("摸牌后可以操作", operates, "玩家", curr_player.seat_id)
        curr_player.operates = deepcopy(operates)
        data["operates"] = operates
        data["gang_hou_mo_pai"] = 1 if len(self.__gang_hou_mo_pai) > 0 else 0
        if can_gang_list:
            data["can_gang_list"] = can_gang_list
        if operates:
            data_model = S2CPublicOperatesMahjong.pb_model(**data)
            if curr_player.card_is_lock():
                if ActionType.ACTION_TYPE_AN_GANG in operates or ActionType.ACTION_TYPE_ZHUAN_WAN_GANG in operates:
                    await self.inner_send(curr_player, CmdRoom.PUBLIC_OPERATES, data_model)
            else:
                await self.inner_send(curr_player, CmdRoom.PUBLIC_OPERATES, data_model)
        self.__gang_hou_chu_pai = self.__gang_hou_mo_pai
        if curr_player.mo_pai_can_operates():
            data = {"seat_id": curr_player.seat_id, "seconds": seconds, "in_flow": self.flow_status}
            data_model = S2CTurnToMahjong.pb_model(**data)
            await self.inner_send(curr_player, CmdRoom.TURN_TO, data_model)
            self.call_flow(TimerDelay.CHU_PAI_TIME, self.mo_pai_call_time_out, curr_player)
            self.call_flow_trustee(TimerDelay.TUO_GUAN_TIME, self.mo_pai_call_trustee, curr_player)
            if curr_player.is_robot:
                res = random.randint(1, 2)
                self.call_flow_robot(res, self.check_robot_operate)
            else:
                DelayCall(TimerDelay.KAI_HU_TIME, self.check_operate_after_kai_hu).start()
            return

        await self.turn_to_player_chu_pai(curr_player)

    async def mo_pai_call_trustee(self, p: PlayerFCZJ):
        if not p.trustee:
            return
        if p.is_lock:
            return
        self.log_info("mo_pai_call_trustee", self.flow_status)
        await self.mo_pai_call_time_out(p, do_trustee=False)

    async def mo_pai_call_time_out(self, p: PlayerFCZJ, do_trustee=False):
        if not self.flow_status_is_equal(FlowStatus.T_IN_MO_PAI_CALL):
            return
        is_can_men = False
        is_trustee = False
        if p.can_operates() and not self.has_do_action(p):
            if p.is_lock and ActionType.ACTION_TYPE_MEN in p.operates and (
                    ActionType.ACTION_TYPE_AN_GANG in p.operates or ActionType.ACTION_TYPE_ZHUAN_WAN_GANG in p.operates):
                is_can_men = True
                code, _ = await self.on_player_men(p)
                if code != StaCode.PASS:
                    self.log_info(p.uid, "玩家 auto 闷 fail!!!")
                await self.check_action_end()
            else:
                p.operates = []
                self.save_player_action(p, ActionType.ACTION_TYPE_PASS)
                one_of_model = s2c_one_of_model()
                one_of_model.seat_id = self.curr_seat_id
                await self.inner_send(p, CmdRoom.PLAYER_PASS, one_of_model)
            is_trustee = True

        is_trustee and await self.do_trustee(p)
        if not is_can_men:
            self.set_flow_status(FlowStatus.T_IN_CHU_PAI)  # 在出牌中
            self.log_info(p.uid, "玩家摸牌call超时，直接进入出牌")
            await self.chu_pai_time_out(p, do_trustee=do_trustee)

    async def chu_pai_time_out(self, p: PlayerFCZJ, do_trustee=True):
        if self.flow_status not in (FlowStatus.T_IN_DI_HU_CHU_PAI, FlowStatus.T_IN_CHU_PAI):
            return StaCode.FLOW_ERR
        if p.seat_id != self.curr_seat_id:
            return StaCode.NOT_YOUR_TURN
        do_trustee and await self.do_trustee(p)
        # 锁牌情况：自动将摸的牌打出，或出第一张牌（理论不会出现癞子，因为锁牌摸到癞子必胡）
        if p.is_lock or p.lock_cards or p.men_cards or p.tian_ting:
            sta = await self.lock_auto_chu_pai(p)
            if sta:
                return

        # 未锁牌情况：有缺打缺，无缺打非癞子
        sta = await self.no_lock_auto_chu_pai(p)
        if sta:
            return

        return self.call_flow(1, self.enter_chu_pai_call)

    async def chu_pai_trustee(self, p: PlayerFCZJ):
        if self.flow_status not in (FlowStatus.T_IN_DI_HU_CHU_PAI, FlowStatus.T_IN_CHU_PAI):
            return StaCode.FLOW_ERR
        if p.seat_id != self.curr_seat_id:
            return StaCode.NOT_YOUR_TURN
        if not p.trustee:
            return

        if p.is_lock or p.lock_cards or p.men_cards or p.tian_ting:
            await self.lock_auto_chu_pai(p)

        # 未锁牌情况：有缺打缺，无缺打非癞子
        await self.no_lock_auto_chu_pai(p)

        return self.call_flow(1, self.enter_chu_pai_call)

    async def check_robot_auto_chu_pai(self):
        print("检查机器人自动出牌")
        player = self.curr_player()
        if not player:
            self.log_info("机器人出牌没找到 robot", player, self.curr_seat_id)
            return
        # 锁牌情况：自动将摸的牌打出，或出第一张牌（理论不会出现癞子，因为锁牌摸到癞子必胡）
        if player.is_lock or player.lock_cards or player.men_cards or player.tian_ting:
            result = await self.lock_auto_chu_pai(player)
            if result:
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

    async def enter_chu_pai_call(self):
        if not self.room_status_is_equal(RoomStatus.T_PLAYING):
            return
        if self.flow_status not in [FlowStatus.T_IN_CHU_PAI, FlowStatus.T_IN_DI_HU_CHU_PAI,
                                    FlowStatus.T_IN_MO_PAI_CALL]:
            return
        self.set_flow_status(FlowStatus.T_IN_PUBLIC_OPRATE)
        chu_pai_player = self.curr_player()
        chu_pai_player.operates = []
        jie_pao_count = 0
        seconds = TimerDelay.CHU_PAI_AFTER_WAIT_TIME
        data = {
            "seat_id": self.curr_seat_id,
            "seconds": seconds,
            "left_count": self.poker.left_count,
        }
        opt_task = []
        for p in self.seats:
            if p.seat_id == self.curr_seat_id:
                continue
            if p.is_out:
                continue
            operates = self.calc_operates_after_chu_pai(p)
            print("出牌后", operates, p.seat_id, self.__curr_card)
            p.operates = operates

            if ActionType.ACTION_TYPE_HU in p.operates:
                jie_pao_count += 1
            elif ActionType.ACTION_TYPE_JIAN in p.operates:
                jie_pao_count += 1

            data["operates"] = operates

            data_model = S2CPublicOperatesMahjong.pb_model(**data)
            if not p.is_robot:
                if p.card_is_lock():
                    if ActionType.ACTION_TYPE_MING_GANG in operates:
                        opt_task.append(self.inner_send(p, CmdRoom.PUBLIC_OPERATES, data_model))
                else:
                    opt_task.append(self.inner_send(p, CmdRoom.PUBLIC_OPERATES, data_model))

        if opt_task:
            await asyncio.gather(*opt_task)

        if jie_pao_count > 1:
            self.__jie_pao_count = jie_pao_count

        if self.can_operates():
            DelayCall(TimerDelay.KAI_HU_TIME, self.check_operate_after_kai_hu).start()
            self.log_info("玩家 {} 出完牌call，其他玩家有操作".format(chu_pai_player.uid))
            self.call_flow_robot(TimerDelay.ROBOT_TIME, self.check_robot_operate)
            self.call_flow(TimerDelay.CHU_PAI_AFTER_WAIT_TIME, self.chu_pai_call_time_out, True)
            self.call_flow_trustee(TimerDelay.TUO_GUAN_TIME, self.chu_pai_call_trustee, "chu_pai_call")

            return

        await self.everyone_pass(0.5)

    async def everyone_pass(self,sec = 1.0):
        print("everyone_pass", self.flow_status)
        p = self.curr_player()
        await self.deal_first_ji(p)
        if self.flow_status == FlowStatus.T_IN_MO_PAI_CALL:  # 偎胡则不检查，提胡要检查八皮
            return await self.turn_to_player_chu_pai(p)
        elif self.flow_status == FlowStatus.T_IN_ZHUAN_WAN_GANG_PAI_CALL:
            return self.do_zhuan_wan_gang_end()
        elif self.flow_status == FlowStatus.T_IN_TIAN_HU:
            return await self.turn_to_player_chu_pai(p)
        # 都不要再摸牌
        return self.call_flow(sec, self.__mo_pai)  # 即时结算等待

    async def do_zhuan_wan_gang_end(self):
        curr_player = self.__curr_action_player
        self.__gang_hou_mo_pai = []  # 有人转弯杠则连续杠被打断
        # 玩家 do 转弯杠
        curr_player.zhuan_wan_gang(self.__curr_card)

        if self.__curr_card == curr_player.mo_pai:
            total_score = self.__extra_score_map[ActionType.ACTION_TYPE_ZHUAN_WAN_GANG]

            await self.kou_fen_notify(curr_player, total_score, [], CheckType.CHECK_SUO_GANG,
                                      [], RechargeType.WAIT_RECHARGE_ZHUAN_WAN_GANG)
        if self.__recharge_wait == 0:
            await self.__mo_pai(curr_player.seat_id, [ActionType.ACTION_TYPE_ZHUAN_WAN_GANG, self.__curr_card])

    async def kou_fen_notify(self, p: PlayerFCZJ, multiple, hu_type, act, extra_hu_list, wait_type, loser_seats=None):
        if loser_seats is None:
            loser_seats = []
        win_total_gold = 0
        update_task = []
        win_gold = multiple * self.base_score
        win_from = []
        lose_list = []
        win_data = {
            "win_from": [],
        }

        lose_data = {
            "lose_to": [p.seat_id],
            "relation": 0,
        }

        common_data = {
            "gold": 0,
            "multiple": multiple,
            "curr_card": self.__curr_card,
            "act": act,
            "hu_type": hu_type
        }
        lose_data.update(common_data)
        win_data.update(common_data)
        if loser_seats:
            seats = loser_seats
        else:
            seats = self.seats
        for p_loser in seats:
            if p_loser.is_out:
                continue
            if p_loser.seat_id == p.seat_id:
                continue

            if win_gold > p_loser.gold:
                lose_gold = p_loser.gold
            else:
                lose_gold = win_gold
            win_total_gold += lose_gold
            relation = self.confirm_relation(p_loser.seat_id, p.seat_id)
            lose_data["gold"] = - lose_gold
            lose_data["relation"] = relation
            win_from.append(p_loser.seat_id)
            p_loser.record_account(lose_data)
            p_loser.update_gold(- lose_gold)
            if not p_loser.is_robot:
                update_task.append(self.update_user_gold(p_loser, - lose_gold, ReasonCostGold.CHECK_OUT_MAHJONG))
            lose_list.append({
                "lose_seat_id": p_loser.seat_id,
                "lose_gold": - lose_gold,
                "loser_res_gold": p_loser.gold,
            })

            if p_loser.gold <= 0:
                self.__recharge_wait = wait_type
                if p_loser.seat_id not in self.__wait_recharge_seats:
                    self.__wait_recharge_seats.append(p_loser.seat_id)

        win_data["gold"] = win_total_gold
        win_data["win_from"] = win_from
        self.multi_user_record_account(p, win_data)
        p.update_gold(win_total_gold)
        if not p.is_robot:
            update_task.append(self.update_user_gold(p, win_total_gold, ReasonCostGold.CHECK_OUT_MAHJONG))
        if update_task:
            await asyncio.gather(*update_task)
        kf_data = {
            "win_seat_id": p.seat_id,
            "check_out_type": ExtraHuPai.ZHUAN_WAN_GANG,
            "win_gold": win_total_gold,
            "winner_res_gold": p.gold,
            "lose_list": lose_list,
            "extra_hu_type": extra_hu_list,
        }
        data_model = S2CKouFen.pb_model(**kf_data)
        await self.inner_broadcast(CmdRoom.TIMELY_KOU_FEN, data_model)
        seats = self.__wait_recharge_seats.copy()
        revenge_task = []
        for seat_id in seats:
            print("通知是否复活")
            player = self.get_player_by_seat_id(seat_id)
            if not player.is_out:
                revenge_task.append(self.notify_is_revenge(player))
        if revenge_task:
            await asyncio.gather(*revenge_task)

    def multi_user_record_account(self, p: PlayerFCZJ, record_data):
        """ 多个玩家关系记账 """
        count = len(record_data["win_from"])
        if count <= 0:
            return
        elif count == 3:
            relation = SeatRelation.THREE.value
        elif count == 2:
            relation = SeatRelation.TWO.value
        else:
            relation = self.confirm_relation(p.seat_id, record_data["win_from"][0])
        record_data["relation"] = relation
        p.record_account(record_data)

    def confirm_relation(self, self_id, curr_id):
        """确认当前玩家与self_id的位置关系"""
        # 获取环形座位列表长度和最大索引
        max_idx = self.max_player_count - 1

        # 计算标准化相对位置（解决环形结构）
        diff = (curr_id - self_id) % self.max_player_count

        # 直接判断位置关系
        if diff == 1:
            return SeatRelation.NEXT.value  # 下家（顺时针相邻）
        elif diff == self.max_player_count - 1:
            return SeatRelation.LAST.value  # 上家（逆时针相邻）
        elif self.max_player_count == 4 and diff == 2:
            return SeatRelation.OOP.value  # 对家（仅4人局有效）
        else:
            return None

    async def turn_to_player_chu_pai(self, p: PlayerFCZJ, after_peng=False):
        print("进入turn_to_player_chu_pai")
        self.clear_table_actions(p.seat_id)
        self.__curr_card = p.mo_pai  # 因为存在炸胡，在玩家出牌阶段玩家也可点击胡，所以保存当前牌

        if after_peng:
            self.__after_peng = after_peng
        self.log_info("轮到玩家出牌: ", p.uid)
        self.curr_seat_id = p.seat_id

        seconds = TimerDelay.CALL_SECONDS
        self.set_flow_status(FlowStatus.T_IN_CHU_PAI)
        data = {"seat_id": p.seat_id, "seconds": seconds, "in_flow": self.flow_status}
        data_model = S2CTurnToMahjong.pb_model(**data)
        await self.inner_broadcast(CmdRoom.TURN_TO, data_model, exclude_uid=p.uid)
        chu_pai_sta = False
        if p.card_is_lock():
            data["lock_cards"] = p.lock_cards
            data_model = S2CTurnToMahjong.pb_model(**data)
            await self.inner_send(p, CmdRoom.TURN_TO, data_model)
            chu_pai_sta = await self.lock_auto_chu_pai(p)

        else:
            await self.inner_send(p, CmdRoom.TURN_TO, data_model)
            if p.is_robot:
                if p.seat_id == self.dealer_id and not p.all_chu_cards:
                    rs = 4
                else:
                    rs = UtilsTool.random_choice_num([1, 2, 3], [0.5, 0.3, 0.2])
                self.call_flow_robot(rs, self.check_robot_auto_chu_pai)
                chu_pai_sta = True
        if chu_pai_sta:
            return
        self.call_flow(TimerDelay.CHU_PAI_TIME, self.chu_pai_time_out, p)
        self.call_flow_trustee(TimerDelay.TUO_GUAN_TIME, self.chu_pai_trustee, p)

    async def lock_auto_chu_pai(self, p: PlayerFCZJ):
        cards = p.get_out_not_lock_card()
        if not cards:
            self.log_info("chu_pai_time_out 玩家全锁无牌可出：", cards)
            return False
        self.log_info("chu_pai_time_out 玩家可出：", cards)
        if cards[0] != CardsType.LAI_ZI:
            code, _ = await self.delay_func(1, self.on_player_chu_pai, p, self.serialized_chu_pai_data(cards[0]))
            if StaCode.PASS == code:
                self.log_info(p.uid, "摸到的牌不是癞子，直接打出：", cards[0])
                self.call_flow(0.5, self.enter_chu_pai_call)
                return True
        return False

    async def no_lock_auto_chu_pai(self, p: PlayerFCZJ):
        cards = deepcopy(p.cards)
        if p.que > 0:
            if cards[-1] // 10 == p.que:
                code, _ = await self.on_player_chu_pai(p, self.serialized_chu_pai_data(cards[-1]))
                if StaCode.PASS == code:
                    self.log_info(self.tid, p.uid, "超时打缺：", cards[-1])
                    self.call_flow(0.5, self.enter_chu_pai_call)
                    return True
            for card in p.cards:
                if card // 10 == p.que:
                    code, _ = await self.on_player_chu_pai(p, self.serialized_chu_pai_data(card))
                    if StaCode.PASS == code:
                        self.log_info(p.uid, "超时打缺_by_cards：", card)
                        self.call_flow(0.5, self.enter_chu_pai_call)
                        return True

        if cards[-1] != CardsType.LAI_ZI:
            code, _ = await self.on_player_chu_pai(p, self.serialized_chu_pai_data(cards[-1]))
            if StaCode.PASS == code:
                self.log_info(p.uid, "超时出牌_摸到什么打什么，除了癞子：", cards[-1])
                self.call_flow(0.5, self.enter_chu_pai_call)
                return True
        for card in p.cards:
            if card != CardsType.LAI_ZI:
                code, _ = await self.on_player_chu_pai(p, self.serialized_chu_pai_data(card))
                if StaCode.PASS == code:
                    self.log_info(p.uid, "超时出牌_找手里不是癞子的牌：", card)
                    self.call_flow(0.5, self.enter_chu_pai_call)
                    return True
        return False

    @staticmethod
    def serialized_chu_pai_data(card):
        gang_model.card = card  # 设置 card 值
        serialized_data = gang_model.SerializeToString()
        return serialized_data

    @staticmethod
    def serialized_fan_ji_data(fan_ji):
        fan_ji_index_model.fan_ji_index = fan_ji  # 设置 card 值
        serialized_data = fan_ji_index_model.SerializeToString()
        return serialized_data

    async def deal_first_ji(self, curr_p: PlayerFCZJ):
        """
        处理冲锋鸡handle
        冲锋幺鸡
        冲锋乌骨鸡
        """
        if not self.flow_status_is_equal(FlowStatus.T_IN_PUBLIC_OPRATE):
            self.log_info(self.tid, "冲锋鸡必须是成功打牌后")
            return
        if self.__curr_card == CardsType.YAO_JI and self.__round_first_ji == 0:
            self.__round_first_ji = 1
            self.__chong_feng_ji_seat_id = self.curr_seat_id
            curr_p.chong_feng_ji = 1
            await self.send_first_ji_info("冲锋鸡玩家成功")

        if self.__curr_card == CardsType.WU_GU_JI and self.__round_first_wgj == 0:
            self.__round_first_wgj = 1
            self.__chong_feng_wgj_seat_id = self.curr_seat_id
            curr_p.chong_feng_wgj = 1
            await self.send_first_ji_info("乌骨冲锋鸡玩家成功")

    async def send_first_ji_info(self, desc):
        self.log_info(desc, self.curr_seat_id)
        data = {"first_ji_seat_id": self.curr_seat_id, "first_ji_card": self.__curr_card}
        data_model = S2CFirstJiMahjong.pb_model(**data)
        await self.inner_broadcast(CmdRoom.CONFIRM_CHONG_FENG_JI, data_model)

    async def chu_pai_call_time_out(self, is_chu_pai=False):
        print("进入chu_pai_call_time_out")
        if self.flow_status not in (FlowStatus.T_IN_PUBLIC_OPRATE, FlowStatus.T_IN_MO_PAI_CALL,
                                    FlowStatus.T_IN_ZHUAN_WAN_GANG_PAI_CALL):
            return
        for p in self.seats:
            if p.is_robot:
                continue
            if p.can_operates() and not self.has_do_action(p):
                if is_chu_pai:
                    await self.do_trustee(p)
                if p.is_lock and ActionType.ACTION_TYPE_MING_GANG in p.operates and ActionType.ACTION_TYPE_JIAN in p.operates:
                    code = await self.on_player_jian(p)
                    if code != StaCode.PASS:
                        self.log_info(p.uid, "玩家 超时捡 fail!!!")
                    await self.check_action_end()
                else:
                    p.operates = []
                    self.save_player_action(p, ActionType.ACTION_TYPE_PASS)
                    one_of_model = s2c_one_of_model()
                    one_of_model.seat_id = self.curr_seat_id
                    await self.inner_send(p, CmdRoom.PLAYER_PASS, one_of_model)
                    DelayCall(0.1, self.check_action_end).start()
            if is_chu_pai and self.player_do_pass(p):
                await self.check_action_end()

    def player_do_pass(self, p, action=ActionType.ACTION_TYPE_PASS):
        for item in self.__player_actions:
            if item[0] == p.seat_id and item[1] == action:
                return True
        return False

    async def chu_pai_call_trustee(self, desc=""):
        if self.flow_status not in (
                FlowStatus.T_IN_PUBLIC_OPRATE, FlowStatus.T_IN_MO_PAI_CALL, FlowStatus.T_IN_ZHUAN_WAN_GANG_PAI_CALL):
            return
        self.log_info(desc, "chu_pai_call_tuo_guan", self.flow_status)
        for p in self.seats:
            if p.is_robot:
                continue
            if p.trustee != 1:
                continue
            if p.is_lock:
                continue
            if p.can_operates() and not self.has_do_action(p):
                self.save_player_action(p, ActionType.ACTION_TYPE_PASS)  # pass
                self.log_info(self.tid, "玩家有操作，托管：", p.operates)
                one_of_model = s2c_one_of_model()
                one_of_model.seat_id = self.curr_seat_id
                await self.inner_send(p, CmdRoom.PLAYER_PASS, one_of_model)
                DelayCall(0.1, self.check_action_end).start()

    def calc_operates_after_chu_pai(self, p: PlayerFCZJ):
        """计算出牌后其他玩家的操作"""
        result = []
        if not self.__curr_card:
            return result
        can_hu, hu_info = self.hu_de_qi(p)
        allow_hu_map = {HuType.DI_LONG_QI: True, HuType.JIN_GOU_DIAO: True,
                        HuType.QI_DUI: True}
        if can_hu:
            hu_type = hu_info["hu_type"]
            if p.is_robot:
                if self.poker.left_count <= 30:
                    result.append(ActionType.ACTION_TYPE_JIAN)
                else:
                    hu_list = RuleFc.get_ting_hu_list([], p.cards, allow_hu_map, self.__lai_zi,p.que)
                    if len(p.cards) == 1 and self.__lai_zi in p.cards:
                        result.append(ActionType.ACTION_TYPE_JIAN)
                    elif hu_type == HuType.PING_HU and not p.is_lock:
                        print("胡牌 没锁牌，机器人不平胡去做大牌")
                    elif len(hu_list) < 10:
                        print("胡牌 没锁牌，机器人不胡去,胡牌太少")
                    else:
                        result.append(ActionType.ACTION_TYPE_JIAN)
            else:
                result.append(ActionType.ACTION_TYPE_JIAN)

        is_ming_gang, _ = self.ming_gang_de_qi(p, self.__curr_card)
        if p.card_is_lock():
            if is_ming_gang:

                temp_cards = [c for c in p.cards if c != self.__curr_card]
                ting_list1 = RuleFc.get_ting_hu_list([], temp_cards, allow_hu_map, self.__lai_zi,p.que)
                # 一致的话可以杠
                print("ting_list1",ting_list1,"p.ting_list",p.ting_list)
                if ting_list1 == p.ting_list:
                    result.append(ActionType.ACTION_TYPE_MING_GANG)
        else:
            if is_ming_gang:
                result.append(ActionType.ACTION_TYPE_MING_GANG)
            if p.can_peng(self.__curr_card, RuleFc):
                result.append(ActionType.ACTION_TYPE_PENG)

        return result

    def ming_gang_de_qi(self, p: PlayerFCZJ, card):
        if self.curr_seat_id == p.seat_id:
            return False, card
        return p.can_ming_gang(RuleFc, card)

    def can_operates(self):
        for p in self.seats:
            if len(p.operates) > 0 and not p.is_out:
                self.log_info("玩家", p.seat_id, "可以操作", p.operates)
                return True
        return False

    async def check_operate_after_kai_hu(self):
        """
        有操作时，优先进入这里
        开胡之后自动胡
        有杠等待
        """
        has_operate = False
        for p in self.seats:
            if p.is_robot:
                continue
            if not p.is_lock:
                continue
            if p.can_operates() and not self.has_do_action(p):
                has_operate = True
                if ActionType.ACTION_TYPE_AN_GANG in p.operates or \
                        ActionType.ACTION_TYPE_MING_GANG in p.operates or \
                        ActionType.ACTION_TYPE_ZHUAN_WAN_GANG in p.operates:
                    p.is_lock = False
                print("p.operates", p.operates)
                if ActionType.ACTION_TYPE_MEN in p.operates and p.is_lock:
                    print("玩家自动胡")
                    code, _ = await self.on_player_men(p)
                    if code != StaCode.PASS:
                        self.log_info(p.uid, "玩家 auto 闷 fail!!!")
                elif ActionType.ACTION_TYPE_JIAN in p.operates and p.is_lock:
                    code, _ = await self.on_player_jian(p)
                    if code != StaCode.PASS:
                        self.log_info(p.uid, "玩家 auto 捡 fail!!!")
                p.is_lock = True
        if has_operate:
            await self.check_action_end()

    async def check_robot_operate(self):
        has_operate = False
        for p in self.seats:
            if not p.is_robot:
                continue
            if p.is_out:
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
                elif gang_type:
                    print("机器人杠")
                    # todo: AI机器人计算是否杠
                    code = StaCode.PASS
                    await self.robot_auto_gang(p, gang_type)
                elif p.is_action_in_operates(ActionType.ACTION_TYPE_PENG):
                    print("机器人碰")
                    # todo: AI机器人计算是否碰
                    code = StaCode.PASS
                    await self.robot_auto_pong(p)

                if code != StaCode.PASS:
                    self.log_info("机器人操作有误，选择pass")
                    await self.on_player_pass(p)

        if has_operate:
            await self.check_action_end()

    @staticmethod
    def get_action_priority(act):
        return const.ACTION_PRIORITY_FC.get(act) or 0

    def get_not_operate_player_max_operate(self):
        result = {}
        already_action_seats = set([action[0] for action in self.__player_actions])
        not_operate_player_list = [p.seat_id for p in self.seats if p.seat_id not in already_action_seats and not p.is_out]
        for seat_id in not_operate_player_list:
            player = self.get_player_by_seat_id(seat_id)
            if player.operates:
                result[seat_id] = max(player.operates, key=self.get_action_priority)

        return result

    def __is_player_actions_finish(self, operate_list):
        max_operate = self.get_not_operate_player_max_operate()  # {seat_id: max_action}
        priority = 0
        if max_operate:
            # (seat_id, operate)  获取还没有操作的玩家最大操作
            remain_max_info = max(
                max_operate.items(),
                key=lambda v: v[1]
            )
            priority = self.get_action_priority(remain_max_info[1])

        # (action, [seat_id1, ..])
        already_max_info = max(
            operate_list.items(),
            key=lambda v: self.get_action_priority(v[0])  # 获取已经操作的玩家最大操作
        )
        print("already_max_info", already_max_info)
        print("priority", priority)
        # 还未操作的玩家最大操作大于已经操作的玩家最大操作(需要等待)
        if priority >= self.get_action_priority(already_max_info[0]):
            return False, already_max_info

        return True, already_max_info

    def get_operate_player_max_operate(self):
        result = {}
        for player in self.seats:
            if player.operates:
                result[player.seat_id] = max(player.operates, key=self.get_action_priority)
        return result

    async def check_action_end(self):
        print("check_action_end")
        operate_list = {}  # {动作: [seat_id, ...]}
        for item in self.__player_actions:
            if item[1] in const.ACTION_PRIORITY_FC:
                operate_list.setdefault(item[1], []).append(item[0])
        if len(operate_list) == 0:
            return
        print("operate_list", operate_list)
        is_finish, max_operate_list = self.__is_player_actions_finish(operate_list)
        print("max_operate_list", max_operate_list)
        print("is_finish", is_finish)
        # if max_operate_list[0] == ActionType.ACTION_TYPE_HU:
        #     operate_list = self.get_operate_player_max_operate()  # {seat_id1: priority or 0, ...}
        #     # [seat_id1, ]
        #     hu_list = [seat_id for seat_id, action in operate_list.items() if action == ActionType.ACTION_TYPE_HU]
        #     return await self.somebody_hu(hu_list)
        if not is_finish:
            return

        # 下面主要是处理有操作且操作过的玩家
        action_map = {
            ActionType.ACTION_TYPE_MEN: self.somebody_men,
            ActionType.ACTION_TYPE_JIAN: self.somebody_jian,
            ActionType.ACTION_TYPE_PENG: self.somebody_peng,
            ActionType.ACTION_TYPE_ZHUAN_WAN_GANG: self.somebody_zhuan_wan_gang,
            ActionType.ACTION_TYPE_MING_GANG: self.somebody_ming_gang,
            ActionType.ACTION_TYPE_AN_GANG: self.somebody_an_gang,
        }

        act = max_operate_list[0]
        self.log_info(self.tid, "somebody " + str(act))
        if act in action_map and max_operate_list[1]:
            hu_list = list(set(max_operate_list[1]))
            result = await action_map[act](hu_list)
            return result

        return await self.everyone_pass()

    async def notify_many_hu(self, hu_list: list):
        """一炮多响通知"""
        if len(hu_list) > 1:
            many_hu_data = []
            curr_p = self.curr_player()
            # p是胡牌者，curr_p是被胡者
            for seat_id in hu_list:
                p = self.get_player_by_seat_id(seat_id)
                # 牌型/额外番
                hu_info, _, _ = self.get_hu_type(p, dian_pao=True)
                extra_hu_list = hu_info["extra_hu_type"] or []
                # 牌型分（已处理）
                base_score = self.get_base_score(hu_info["hu_type"], extra_hu_list)
                # 额外番分
                extra_score = self.cal_extra_hu_score(extra_hu_list)
                # 倍数 = 牌型分（已处理） + 额外番分
                total_score = base_score + extra_score

                # 处理闷牌/闷牌记录
                data = self.deal_men_jian_data(p, total_score, hu_info, CheckType.CHECK_JIAN)
                many_hu_data.append(data)
            data = {
                "curr_seat_id": self.curr_seat_id,
                "hu_list": many_hu_data,
                "curr_card": self.__curr_card
            }
            print("一炮多响数据--->", data)
            data_model = S2CManyHuInfo.pb_model(**data)
            await self.inner_broadcast(CmdRoom.MANY_HU, data_model)  # 一炮多响
            return True
        return False

    def remove_jian(self, seat_id):
        """ 因为每次都要询问叫牌玩家过，则捡牌玩家可能会算两次 """
        for i, item in enumerate(self.__player_actions):
            if item[0] != seat_id:
                continue
            act = item[1]
            if act == ActionType.ACTION_TYPE_JIAN:
                self.__player_actions.pop(i)
            p = self.get_player_by_seat_id(seat_id)
            p.operates = []  # 这里不清除会导致进入超时中把玩家当做炸胡

    async def jian_da_notify(self, hu_list: list, many_hu=False):
        curr_p = self.curr_player()
        for seat_id in hu_list:
            # 多家被胡处理，免得重复胡
            self.remove_jian(seat_id)
            p = self.get_player_by_seat_id(seat_id)
            # 牌型/额外番
            hu_info, _, _ = self.get_hu_type(p, dian_pao=True)
            hu_type = hu_info["hu_type"] or 0
            extra_hu_list = hu_info["extra_hu_type"] or []
            # 所有胡key
            hu_types = [hu_type] + extra_hu_list
            # 牌型分（已处理）
            base_score = self.get_base_score(hu_type, extra_hu_list)
            # 额外番分
            extra_score = self.cal_extra_hu_score(extra_hu_list)
            # 倍数 = 牌型分（已处理） + 额外番分
            total_score = base_score + extra_score

            self.update_player_max_score(p,total_score,base_score,extra_score,hu_type,extra_hu_list)
            data = self.deal_men_jian_data(p, total_score, hu_info, CheckType.CHECK_JIAN)
            if many_hu:
                data["is_yi_pao_duo_xiang"] = 1
            data_model = S2CMenInfoMahjong.pb_model(**data)
            p.add_jian_cards(data)
            if not many_hu:
                await self.inner_broadcast(CmdRoom.PLAYER_JIAN_SUC, data_model)  # 捡成功/收牌

            await self.kou_fen_notify(p, total_score, hu_types, CheckType.CHECK_JIAN, extra_hu_list, RechargeType.WAIT_RECHARGE_JIAN,
                                      [curr_p])

    def deal_ze_ren_ji(self, p: PlayerFCZJ) -> int:
        """
        处理责任鸡handle
        责任幺鸡
        责任乌骨鸡
        """
        if self.__curr_card == CardsType.YAO_JI and self.__round_first_ji == 0:
            self.__ze_ren_ji_seat_id = self.curr_seat_id
            self.__ze_ren_ji_win_seat_id = p.seat_id
            if self.__chong_feng_ji_seat_id > 0:
                chong_feng_ji_player = self.get_player_by_seat_id(self.__chong_feng_ji_seat_id)
                chong_feng_ji_player.chong_feng_ji = 0
                self.__chong_feng_ji_seat_id = 0

            curr_p = self.curr_player()
            curr_p.ze_ren_ji = 1
            self.__round_first_ji = 1
            return 1

        if self.__curr_card == CardsType.WU_GU_JI and self.__round_first_wgj == 0:
            self.__ze_ren_wgj_seat_id = self.curr_seat_id
            self.__ze_ren_wgj_win_seat_id = p.seat_id
            if self.__chong_feng_wgj_seat_id > 0:
                cfwgj_player = self.get_player_by_seat_id(self.__chong_feng_wgj_seat_id)
                cfwgj_player.chong_feng_wgj = 0
                self.__chong_feng_wgj_seat_id = 0

            curr_p = self.curr_player()
            curr_p.ze_ren_wgj = 1
            self.__round_first_wgj = 1
            return 2
        return 0

    @staticmethod
    def get_operates_after_peng(p: PlayerFCZJ):
        can_an_gang, gang_card_list = p.can_an_gang(RuleFc)
        can_zwg, gang_card = p.can_zhuan_wan_gang(RuleFc)
        operates = []
        if can_zwg:
            operates.append(ActionType.ACTION_TYPE_ZHUAN_WAN_GANG)
        if can_an_gang:
            operates.append(ActionType.ACTION_TYPE_AN_GANG)
        return operates, gang_card_list

    async def check_can_gang_after_peng(self, p: PlayerFCZJ):
        """ 检测玩家碰后是否能杠 """
        print("check_can_gang_after_peng")
        operates, gang_card_list = self.get_operates_after_peng(p)
        if operates:
            print("check_can_gang_after_peng--operates", operates)
            self.clear_table_actions()
            self.set_flow_status(FlowStatus.T_IN_MO_PAI_CALL)  # 设置为在摸牌中
            self.curr_seat_id = p.seat_id  # 设置当前玩家

            seconds = TimerDelay.CALL_SECONDS
            data = {
                "seat_id": p.seat_id,
                "seconds": seconds,
                "left_count": self.poker.left_count,
                "in_flow": self.flow_status,
            }
            if ActionType.ACTION_TYPE_AN_GANG in operates:
                data["can_gang_list"] = gang_card_list
            p.operates = operates
            data["operates"] = p.operates
            opt_model = S2CPublicOperatesMahjong.pb_model(**data)
            await self.inner_send(p, CmdRoom.PUBLIC_OPERATES, opt_model)
            result = {"seat_id": p.seat_id, "seconds": seconds, "in_flow": self.flow_status}
            turn_model = S2CTurnToMahjong.pb_model(**result)
            await self.inner_send(p, CmdRoom.TURN_TO, turn_model)
            if p.is_robot:
                res = random.randint(1, 2)
                self.call_flow_robot(res, self.check_robot_operate)
            self.call_flow(TimerDelay.CHU_PAI_TIME, self.mo_pai_call_time_out, p)
            self.call_flow_trustee(TimerDelay.TUO_GUAN_TIME, self.mo_pai_call_trustee, p)
            self.log_info("碰后能杠", p.seat_id)
            return

        await self.turn_to_player_chu_pai(p, after_peng=True)

    def calc_operates_after_zhuan_wan_gang(self, p: PlayerFCZJ):
        """ 抢杠胡"""
        result = []
        can_hu, hu_info = self.hu_de_qi(p)
        if can_hu:
            hu_type = hu_info["hu_type"]
            allow_hu_map = {HuType.DI_LONG_QI: True, HuType.JIN_GOU_DIAO: True,
                            HuType.QI_DUI: True}
            if p.is_robot:
                if self.poker.left_count <= 30:
                    result.append(ActionType.ACTION_TYPE_JIAN)
                else:
                    hu_list = RuleFc.get_ting_hu_list([], p.cards, allow_hu_map, self.__lai_zi,p.que)
                    if hu_type == HuType.PING_HU and not p.is_lock:
                        print("胡牌 没锁牌且胡牌数量小于10，机器人不平胡去做大牌")
                        result.append(ActionType.ACTION_TYPE_PASS)
                    elif len(hu_list) < 10:
                        result.append(ActionType.ACTION_TYPE_PASS)
                    else:
                        result.append(ActionType.ACTION_TYPE_JIAN)

        return result

    async def enter_zhuan_wan_gang_call(self, curr_player: PlayerFCZJ, card):
        """
        :return:
        """
        if not self.flow_status_is_equal(FlowStatus.T_IN_MO_PAI_CALL):
            return
        self.set_flow_status(FlowStatus.T_IN_ZHUAN_WAN_GANG_PAI_CALL)
        self.clear_table_actions()
        self.__curr_card = card
        self.__curr_action_player = curr_player
        data = {
            "from_seat_id": self.curr_seat_id,
            "seat_id": curr_player.seat_id,
            "is_finish": 1,
            "card": self.__curr_card,
            "act_type": ActionType.ACTION_TYPE_ZHUAN_WAN_GANG
        }
        data_gang_model = S2CGangInfo.pb_model(**data)
        await self.inner_broadcast(CmdRoom.PLAYER_GANG, data_gang_model)

        for p in self.seats:
            if p.seat_id == curr_player.seat_id:
                continue
            operates = self.calc_operates_after_zhuan_wan_gang(p)
            p.operates = operates
            data = {
                "left_count": self.poker.left_count,
                "seconds": TimerDelay.CHU_PAI_AFTER_WAIT_TIME,
                "operates": operates,
            }
            opt_model = S2CPublicOperatesMahjong.pb_model(**data)
            if operates:
                await self.inner_send(p, CmdRoom.PUBLIC_OPERATES, opt_model)

        # if self.can_somebody_hu():  # 有人可以胡，则需要等待
        #     if not self.__decision_sec:
        #         return
        #     self.call_flow(TimerDelay.CHU_PAI_AFTER_WAIT_TIME, self.chu_pai_call_time_out)
        #     return
        await self.do_zhuan_wan_gang_end()

    async def enter_ming_gang_call(self, curr_player: PlayerFCZJ, card):

        if self.flow_status not in (
                FlowStatus.T_IN_PUBLIC_OPRATE, FlowStatus.T_IN_MO_PAI_CALL, FlowStatus.T_IN_TIAN_HU):
            return
        self.set_flow_status(FlowStatus.T_IN_MING_GANG_PAI_CALL)
        self.clear_table_actions()
        self.__curr_card = card
        self.__curr_action_player = curr_player

        from_p = self.get_player_by_seat_id(self.curr_seat_id)
        # 杠基础分
        total_score = self.__extra_score_map[ActionType.ACTION_TYPE_MING_GANG]
        await self.kou_fen_notify(curr_player, total_score, [], CheckType.CHECK_MING_GANG,
                                  [], RechargeType.WAIT_RECHARGE_MING_GANG, [from_p])

        if self.__recharge_wait == 0:
            await self.__mo_pai(curr_player.seat_id, [ActionType.ACTION_TYPE_MING_GANG, card])

    async def somebody_an_gang(self, gang_list: list) -> bool:
        if len(gang_list) != 1:
            return False
        p = self.get_player_by_seat_id(gang_list[0])
        self.__curr_action_player = p
        if not p:
            return False
        card = 0
        for item in self.__player_actions:
            seat_id, action, tmp = item
            if seat_id == p.seat_id and action == ActionType.ACTION_TYPE_AN_GANG:
                gang_model.ParseFromString(tmp)
                card = gang_model.card or 0
                break

        is_an_gang, card_list = p.can_an_gang(RuleFc, card)  # 判断能不能杠
        card = card_list[0]
        flag = p.an_gang(card)
        data = {
            "from_seat_id": self.curr_seat_id,
            "seat_id": p.seat_id,
            "is_finish": int(flag),
            "card": card,
            "act_type": ActionType.ACTION_TYPE_AN_GANG
        }

        if flag:
            # 当前杠的牌非摸的牌且打过牌（不是起手得到的），则算憨包豆
            # 特殊情况，第一张牌被碰，p.chu_cards等于空

            data["card"] = card

            data_model = S2CGangInfo.pb_model(**data)
            await self.inner_broadcast(CmdRoom.PLAYER_GANG, data_model)

            if card != p.mo_pai and (p.chu_cards or len(p.all_chu_cards) % 4 != 0):
                self.log_info(self.tid, p.uid, p.seat_id, "憨包杠", card)
                p.add_han_bao_dou_an_gang_count(card)
            else:
                total_score = self.__extra_score_map.get(ActionType.ACTION_TYPE_AN_GANG)
                await self.kou_fen_notify(p, total_score, [], CheckType.CHECK_AN_GANG,
                                          [], RechargeType.WAIT_RECHARGE_AN_GANG)

            self.log_info(self.tid, "somebody_an_gang end1")
        if flag and self.__recharge_wait == 0:
            await self.__mo_pai(p.seat_id, [ActionType.ACTION_TYPE_AN_GANG, card])

            return True

        self.log_info(self.tid, "somebody_an_gang end2")
        return False

    async def somebody_ming_gang(self, gang_list: list) -> bool:
        if len(gang_list) != 1:
            return False

        p = self.get_player_by_seat_id(gang_list[0])
        if not p:
            return False
        from_p = self.get_player_by_seat_id(self.curr_seat_id)
        card = from_p.pop_chu_pai()
        flag = p.ming_gang(card, self.curr_seat_id)
        data = {
            "from_seat_id": self.curr_seat_id,
            "seat_id": p.seat_id,
            "is_finish": int(flag),
            "card": card,
            "act_type": ActionType.ACTION_TYPE_MING_GANG
        }

        if flag:
            self.__gang_hou_mo_pai = []  # 有人明杠则连续杠被打断
            res = self.deal_ze_ren_ji(p)
            if res:
                if res == 1:
                    data["ze_ren_ji"] = self.__ze_ren_ji_seat_id
                else:
                    data["ze_ren_ji"] = self.__ze_ren_wgj_seat_id  # 责任乌骨鸡
            data_model = S2CGangInfo.pb_model(**data)
            await self.inner_broadcast(CmdRoom.PLAYER_GANG, data_model)
            await self.enter_ming_gang_call(p, card)
            return True
        return False

    async def somebody_zhuan_wan_gang(self, gang_list: list) -> bool:
        if len(gang_list) != 1:
            return False
        p = self.get_player_by_seat_id(gang_list[0])
        if not p:
            return False
        card = 0
        for item in self.__player_actions:
            seat_id, action, tmp = item
            if seat_id == p.seat_id and action == ActionType.ACTION_TYPE_ZHUAN_WAN_GANG:
                gang_model.ParseFromString(tmp)
                card = gang_model.card or 0
                break
        is_zhuan_wan_gang, card = p.can_zhuan_wan_gang(RuleFc, card)
        if not is_zhuan_wan_gang:
            raise TypeError("xxxxxxxxxxxxxx")

        # 如果不是摸到就杠 是不算分的
        if self.flow_status_is_equal(FlowStatus.T_IN_MO_PAI_CALL) and self.curr_player().mo_pai == card:
            self.__curr_card_exist = 0
        await self.enter_zhuan_wan_gang_call(p, card)
        return True

    async def somebody_peng(self, peng_list: list) -> bool:  # 三人均操作后判断有没有人碰牌
        print("somebody_peng")
        if len(peng_list) != 1:
            return False

        p = self.get_player_by_seat_id(peng_list[0])
        from_p = self.get_player_by_seat_id(self.curr_seat_id)
        if not p or not from_p:
            return False

        card = from_p.pop_chu_pai()
        flag = p.player_peng(card, self.curr_seat_id)
        data = {
            "from_seat_id": self.curr_seat_id,
            "seat_id": p.seat_id,
            "is_finish": int(flag),
            "card": card,
            "act_type": ActionType.ACTION_TYPE_PENG
        }
        if flag:
            self.__curr_card_exist = 0
            self.__gang_hou_chu_pai = []  # 有人碰则连续杠被打断(因为碰牌不需要补牌，所以清除gang_hou_chu_pai)
            res = self.deal_ze_ren_ji(p)
            if res:
                if res == 1:
                    data["ze_ren_ji"] = self.__ze_ren_ji_seat_id
                else:
                    data["ze_ren_ji"] = self.__ze_ren_wgj_seat_id  # 责任乌骨鸡

            data_model = S2CGangInfo.pb_model(**data)
            await self.inner_broadcast(CmdRoom.PLAYER_PENG, data_model)

            await self.check_can_gang_after_peng(p)

            return True
        return False

    async def somebody_jian(self, hu_list: list):
        """ 有人捡 """
        self.__curr_card_exist = 0
        # 捡结算完清除其他玩家的低级操作，不然结算的时间可能会碰杠
        self.__player_actions.clear()
        self.clear_operates()
        if await self.notify_many_hu(hu_list):
            await self.jian_da_notify(hu_list, many_hu=True)
        else:
            await self.jian_da_notify(hu_list)
        allow_hu_map = {HuType.DI_LONG_QI: True, HuType.JIN_GOU_DIAO: True,
                        HuType.QI_DUI: True}
        # 捡完 锁定牌组 自动出牌
        for seat_id in hu_list:
            p = self.get_player_by_seat_id(seat_id)
            p.set_lock_cards([])
            p.can_tian_ting = -1
            p.is_lock = True
            if len(p.ting_list) == 0:
                table_cards = deepcopy(p.table_cards)
                ting_list = RuleFc.get_ting_hu_list(table_cards, p.cards, allow_hu_map, self.__lai_zi,p.que)
                p.ting_list = ting_list

        if self.__recharge_wait == 0:
            self.call_flow(TimerDelay.KOU_FEI_TIME, self.__mo_pai)  # 即时结算等待

    async def somebody_men(self, seat_list: list):  # 三人均操作后判断有没有人胡牌
        print("进入somebody_men")
        self.__curr_card_exist = 0
        await self.men_da_notify(seat_list)
        seat_id = seat_list[0]
        p = self.get_player_by_seat_id(seat_id)
        p.set_lock_cards([])
        p.can_tian_ting = -1
        p.is_lock = True
        allow_hu_map = {HuType.DI_LONG_QI: True, HuType.JIN_GOU_DIAO: True,
                        HuType.QI_DUI: True}
        if len(p.ting_list) == 0:
            table_cards = deepcopy(p.table_cards)
            ting_list = RuleFc.get_ting_hu_list(table_cards, p.cards, allow_hu_map, self.__lai_zi,p.que)
            p.ting_list = ting_list

        if self.__recharge_wait == 0:
            self.call_flow(TimerDelay.KOU_FEI_TIME, self.__mo_pai)

    async def men_da_notify(self, hu_list: list):
        """血流红中捉鸡玩家闷牌结算"""
        for seat_id in hu_list:
            p = self.get_player_by_seat_id(seat_id)
            # 牌型/额外番/自摸
            hu_info, _, _ = self.get_hu_type(p)
            hu_type = hu_info["hu_type"] or 0
            extra_hu_list = hu_info["extra_hu_type"] or []
            is_zi_mo = hu_info["is_zi_mo"]
            p.hu_type = 2 if is_zi_mo else 1
            win_total_score = 0
            hu_pai_type = [hu_type] + extra_hu_list
            base_score = self.get_base_score(hu_type, extra_hu_list, is_zi_mo)  # 基础牌型分
            extra_score = self.cal_extra_hu_score(extra_hu_list)  # 额外胡分
            score = base_score + extra_score
            self.update_player_max_score(p, score, base_score, extra_score, hu_type, extra_hu_list)
            data = self.deal_men_jian_data(p, win_total_score, hu_info)
            p.add_men_cards(data)

            data_model = S2CMenInfoMahjong.pb_model(**data)
            await self.inner_broadcast(CmdRoom.PLAYER_MEN_SUC, data_model)
            await self.kou_fen_notify(p, score, hu_pai_type, CheckType.CHECK_MEN, extra_hu_list, RechargeType.WAIT_RECHARGE_MEN)

    async def notify_is_revenge(self, player: PlayerFCZJ):
        """ 判断是否复仇"""
        # 判断破产玩家，弹出充值，充值继续，不充值认输
        self.set_flow_status(FlowStatus.T_IN_RECHARGE)
        # 判断破产玩家，弹出充值，充值继续，不充值认输
        self.set_room_status(RoomStatus.T_RECHARGE_ING)
        self.log_info(player.uid, player.seat_id, "进入是否复仇")
        sec = 30
        if not player.is_robot:
            player.call_flow(sec, self.player_give_up, player)
        await self.notify_buy_gift_pack(player, seconds=sec)

    async def notify_resurgence(self, player: PlayerFCZJ):
        """ 通知复活 """
        self.log_info(player.uid, player.seat_id, "玩家复活")
        player.cancel_timer()
        rm = s2c_recharge_model(player.seat_id, str(player.gold))
        self.__wait_recharge_seats.remove(player.seat_id)
        await self.inner_broadcast(CmdRoom.RECHARGE, rm)
        if len(self.__wait_recharge_seats) == 0:
            await self.recharge_continue()

    async def recharge_continue(self):
        action_map = {
            RechargeType.WAIT_RECHARGE_JIAN: self.__mo_pai,
            RechargeType.WAIT_RECHARGE_MEN: self.__mo_pai,
            RechargeType.WAIT_RECHARGE_AN_GANG: self.operate_after_gang,
            RechargeType.WAIT_RECHARGE_MING_GANG: self.operate_after_gang,
            RechargeType.WAIT_RECHARGE_ZHUAN_WAN_GANG: self.operate_after_gang,
        }
        func = action_map.get(self.__recharge_wait)
        if not callable(func):
            return
        self.set_room_status(RoomStatus.T_PLAYING)
        self.__recharge_wait = 0
        return await func()

    async def operate_after_gang(self):
        """杠后摸牌"""
        curr_player = self.__curr_action_player
        await self.__mo_pai(curr_player.seat_id, [ActionType.ACTION_TYPE_MING_GANG, self.__curr_card])  # 继续摸牌

    def clear_table_actions(self, beside_seat_id=-1):
        self.__player_actions.clear()
        self.clear_operates(beside_seat_id)
        self.__curr_card = 0
        self.__curr_action_player = None
        self.__jie_pao_count = -1

    def clear_operates(self, beside_seat_id=-1):
        for p in self.seats:
            if p.seat_id == beside_seat_id:
                continue
            p.operates = []

    def get_player_cards_info(self):
        """ 获取玩家手牌信息 """
        cards_info = []
        for p in self.seats:
            cards_info.append({"seat_id": p.seat_id, "hand_cards": p.cards})
        return cards_info

    async def liu_ju_notify(self):
        """ 通知客户端 流局 兴义麻将 有黄牌查叫数据"""
        await self.inner_broadcast(CmdRoom.LIU_JU_NOTIFY)

    async def __mo_pai(self, choice_seat=None, after_gang=None):
        """
        摸牌
        """
        if self.room_status_is_equal(RoomStatus.T_RECHARGE_ING):
            self.log_info( "桌子在充值中，不摸牌")
            return
        if self.flow_status_is_equal(FlowStatus.T_IN_CHECK_OUT):
            self.log_info( "桌子已结算，不再摸牌")
            return
        self.clear_table_actions()
        if choice_seat:
            p = self.get_player_by_seat_id(choice_seat)  # 杠后摸牌的玩家
        else:
            p = self.next_player(self.curr_seat_id)
        if self.poker.left_count <= const.LIU_JU_COUNT:  # 黄庄了
            self.find_hua_zhu_players()
            self.not_jiao_pai_player()
            cards_info = self.get_player_cards_info()
            cards_model = S2CHuAfterCards.pb_model(cards_info)
            await self.inner_broadcast(CmdRoom.HU_AFTER_CARDS_INFO, cards_model)
            if len(self.__no_jiao_pai_seats) == self.in_room_count:
                await self.liu_ju_notify()
                return self.round_over(OverType.LIU_JU)
            else:
                return self.call_flow(2, self.start_fan_ji)

        self.set_flow_status(FlowStatus.T_IN_MO_PAI)
        send_command = CmdRoom.PLAYER_MO_PAI
        if after_gang:
            send_command = CmdRoom.AFTER_GANG_MO_CARD
            self.__gang_hou_mo_pai.append(after_gang)
        else:
            self.__gang_hou_mo_pai = []
            self.__gang_hou_chu_pai = []
            if not p.is_robot:
                p.add_quan_count()

        self.curr_seat_id = p.seat_id
        mo_pai = 0
        if not p.is_robot and p.gold <= self.base_score * 15:  # 记录玩家金币小于15倍
            p.add_first_down()
        # 真人玩家连输两次后有几率在规定打牌的圈数摸到癞子
        if not p.is_robot and p.cards.count(
                p.cards.count(CardsType.LAI_ZI) == 1) and p.quan_count == p.lucky_quan and p.lian_sheng < 0 and p.lian_sheng % 2 == 0:
            mo_pai = self.poker.pop(CardsType.LAI_ZI)
            self.log_info(p.uid, "玩家连输后给玩家摸癞子：", "圈数为", p.lucky_quan, mo_pai)
        elif not p.is_robot and p.first_down == 1 and p.gold <= self.base_score * 15:
            good_rate = int(UtilsTool.random_choice_num([0, 1], [0.75, 0.25]))
            if good_rate == 1:
                mo_pai = self.poker.pop(CardsType.LAI_ZI)
                self.log_info(p.uid, "玩家金币降低到低分*15后给玩家摸癞子：", mo_pai)
        else:
            if p.is_robot:
                good_rate = int(UtilsTool.random_choice_num([0, 1], [0.65, 0.35]))
            else:
                good_rate = int(UtilsTool.random_choice_num([0, 1], [0.5, 0.5]))

            if not p.is_lock and good_rate == 1:
                filtered_cards = [card for card in p.cards if card != CardsType.LAI_ZI]
                if filtered_cards:
                    card = random.choice(filtered_cards)
                    if self.poker.pop(card):
                        mo_pai = card
                        self.log_info("走好运，摸到手里面有的牌", mo_pai, "seat_id", p.seat_id)
        if mo_pai == 0:
            mo_pai = self.poker.pop()
        p.rev_card(mo_pai)
        p.mo_pai = mo_pai
        self.log_info("玩家", p.seat_id, "摸牌", mo_pai, "手牌", p.cards, "剩余", self.poker.left_count)
        for player in self.seats:
            data = {
                "seat_id": p.seat_id,
                "left_count": self.poker.left_count,
                "seconds": TimerDelay.CALL_SECONDS,
            }
            if player.uid == p.uid:
                data["card"] = p.mo_pai
                data["operates"] = []
            data_model = S2CAfterGangMoCard.pb_model(**data)
            await self.inner_send(player, send_command, data_model)
        if p.tian_ting == 1:
            # 天听状态，要出牌只能出摸的牌
            p.set_lock_cards([mo_pai])

        self.log_info("即将进入 enter_mo_pai_call")
        await self.enter_mo_pai_call()

    async def start_fan_ji(self):
        """
        捉鸡新规则
        所有牌打完之后，每人随机5张牌，非金鸡牌点数+1
        5张牌里随机一张为金鸡牌，10分，不属于任何牌型
        翻完鸡之后开始捉鸡，有金鸡、银鸡、默认鸡、站鸡
        """
        if self.room_status in [RoomStatus.T_CHECK_OUT, RoomStatus.T_DISMISS]:
            return StaCode.RULE_ERR
        self.log_info(self.tid, "开始捉鸡")
        self.set_flow_status(FlowStatus.T_IN_FAN_JI)
        data = {
            "fan_ji_list": self.__fan_ji_list,
            "seconds": TimerDelay.FAN_JI_TIME,
            "can_fan_ji": False
        }

        re_times = 0
        start_rs = [1, 2, 3, 4]
        random.shuffle(start_rs)
        # 查在桌可捉鸡人数
        for p in self.seats:
            if p.is_out:
                continue
            if p.jiao_pai:
                data["can_fan_ji"] = True
                self.__can_fan_ji_seats.append(p.seat_id)
                if p.fan_ji <= 0 and p.is_robot:
                    DelayCall(start_rs[re_times], self.robot_auto_fan_ji, p).start()
                    re_times += 1
            data_model = S2CStartFanJi.pb_model(**data)
            await self.inner_send(p, CmdRoom.START_FAN_JI, data_model)

        self.call_flow(TimerDelay.FAN_JI_TIME, self.fan_ji_time_out)
        self.call_flow_trustee(TimerDelay.TUO_GUAN_TIME, self.trustee_fan_ji_time_out)

    async def robot_auto_fan_ji(self, p: PlayerFCZJ):
        if self.flow_status != FlowStatus.T_IN_FAN_JI:
            return StaCode.FLOW_ERR
        fan_ji_index = self.__fan_ji_list
        fan_ji_record = random.choice(fan_ji_index)  # 机器人随机翻
        code, _ = await self.on_player_fan_ji(p, self.serialized_fan_ji_data(fan_ji_record))
        if code != StaCode.PASS:
            self.log_info(p.uid, "捉鸡错误！code：", code)
            return

    async def fan_ji_time_out(self):
        if not self.flow_status_is_equal(FlowStatus.T_IN_FAN_JI):
            return
        for seat_id in self.__can_fan_ji_seats:
            p = self.get_player_by_seat_id(seat_id)
            if p.is_out:
                continue
            if p.fan_ji <= 0:
                fan_ji_index = self.__fan_ji_list
                fan_ji_record = random.choice(fan_ji_index)
                code, _ = await self.on_player_fan_ji(p, self.serialized_fan_ji_data(fan_ji_record))
                if code != StaCode.PASS:
                    self.log_info(p.uid, "time_out 捉鸡错误！code：", code)
                    return
        return self.call_flow(1.5, self.round_over)

    async def trustee_fan_ji_time_out(self):
        if not self.flow_status_is_equal(FlowStatus.T_IN_FAN_JI):
            return
        for seat_id in self.__can_fan_ji_seats:
            p = self.get_player_by_seat_id(seat_id)
            if p.is_out:
                continue
            if not p.trustee:
                continue
            if p.fan_ji <= 0:
                fan_ji_index = self.__fan_ji_list
                fan_ji_record = random.choice(fan_ji_index)
                code, _ = await self.on_player_fan_ji(p, self.serialized_fan_ji_data(fan_ji_record))
                if code != StaCode.PASS:
                    self.log_info(p.uid, "trustee_time_out 捉鸡错误！code：", code)
                    return
        is_all_choose = True
        for seat_id in self.__can_fan_ji_seats:
            p = self.get_player_by_seat_id(seat_id)
            if p.fan_ji <= 0:
                is_all_choose = False
                break
        if is_all_choose:
            return self.call_flow(1.5, self.round_over)

    def player_fan_ji_call(self, p: PlayerFCZJ, fan_ji_index):
        if p.is_out:
            return
        if p.seat_id not in self.__can_fan_ji_seats:
            return
        jin_ji_index = random.randint(0, 4)
        all_cards = list(const.ALL_CARDS_WITHOUT_ZI_HUA)
        can_fan_ji_cards = random.sample(all_cards, 5)
        random.shuffle(can_fan_ji_cards)

        if fan_ji_index == jin_ji_index:
            fan_ji_card = JiType.JIN_JI
            p.fan_ji = fan_ji_card
        else:
            fan_ji_card = can_fan_ji_cards[fan_ji_index]
            if fan_ji_card % 10 == 9:
                fan_ji_result = fan_ji_card - 8
            else:
                fan_ji_result = fan_ji_card + 1
            p.fan_ji = fan_ji_result

        if p.fan_ji != JiType.JIN_JI:
            self.__fan_ji_cards.append(fan_ji_card)  # 翻坤牌（未+1，不含金）
            self.__fan_ji_result.append(p.fan_ji)  # 翻坤牌（已+1，不含金）
        return fan_ji_card

    def find_hua_zhu_players(self):
        """ 查花猪：游戏结束时，手上牌还有缺牌的玩家 """
        for p in self.seats:
            if p.is_out:
                continue
            cards = list(p.cards)
            if CardsType.LAI_ZI in cards:
                cards.remove(CardsType.LAI_ZI)

            suit_count = self.poker.cal_card_suit_count(cards)  # 计算同种花色出现的次数
            if suit_count.get(p.que, 0) > 0:
                self.__hua_zhu_seats.append(p.seat_id)
                p.hua_zhu = 1

    def deal_men_jian_data(self, p, win_total_score, hu_info, check_type=CheckType.CHECK_MEN):
        data = {
            "curr_card": p.mo_pai if hu_info.get("is_zi_mo") else self.__curr_card,
            "score": win_total_score,
            "check_type": check_type,
        }
        data.update(hu_info)
        return data

    def get_base_score(self, hu_type, extra_hu_list, is_zi_mo=False):
        base_score = self.__pai_xing_score_map[hu_type] or 0
        target_hu_list = [ExtraHuPai.TIAN_HU, ExtraHuPai.DI_HU]
        if hu_type == HuType.PING_HU and set(extra_hu_list).intersection(target_hu_list):
            base_score = 0
        if is_zi_mo:
            base_score *= 2
        return base_score

    def cal_extra_hu_score(self, extra_hu_lst):
        total_score = 0
        for extra_hu in extra_hu_lst:
            if extra_hu == ExtraHuPai.QIANG_GANG_HU:  # 抢杠胡：此杠被烧，被抢者额外输6分
                score = 6
            elif extra_hu == ExtraHuPai.GANG_SHANG_PAO:  # 杠上炮/热炮：此杠被烧，点炮者额外输3分
                score = 3
            else:
                score = self.__extra_score_map.get(extra_hu, 0)

            total_score += score
        return total_score

    def has_do_action(self, p: PlayerFCZJ):
        for item in self.__player_actions:
            if item[0] == p.seat_id:
                return True
        return False

    def has_do_by_action(self, p: PlayerFCZJ, action):
        """ 记录玩家操作，不能重复操作 """
        if isinstance(action, list):
            actions = [ActionType.ACTION_TYPE_MEN, ActionType.ACTION_TYPE_JIAN,
                       ActionType.ACTION_TYPE_HU, ]
            target_actions = actions
        else:
            target_actions = [action]
        return any(
            item[0] == p.seat_id and item[1] in target_actions
            for item in self.__player_actions
        )

    def save_player_action(self, p: PlayerFCZJ, action, data=None):
        self.__player_actions.append([p.seat_id, action, data])

    def calc_operates_after_mo_pai(self, p: PlayerFCZJ):
        """计算摸牌后能做的操作"""
        result = []
        can_gang_list = []
        allow_hu_map = {HuType.DI_LONG_QI: True, HuType.JIN_GOU_DIAO: True,
                        HuType.QI_DUI: True}
        can_hu, hu_info = self.hu_de_qi(p)
        if can_hu:
            hu_type = hu_info["hu_type"]
            if p.is_robot:
                if self.poker.left_count <= 30:
                    result.append(ActionType.ACTION_TYPE_MEN)
                else:
                    hand_card = deepcopy(p.cards)
                    hand_card.remove(p.mo_pai)
                    table_cards = deepcopy(p.table_cards)
                    hu_list = RuleFc.get_ting_hu_list(table_cards, hand_card, allow_hu_map, self.__lai_zi,p.que)
                    if len(p.cards) == 2 and self.__lai_zi in p.cards:
                        result.append(ActionType.ACTION_TYPE_MEN)
                    elif hu_type == HuType.PING_HU and not p.is_lock:
                        print("摸牌能胡 没锁牌，机器人不平胡去做大牌")
                    elif len(hu_list) < 10:
                        print("摸牌能胡 没锁牌，机器人不胡，胡牌太少")
                    else:
                        result.append(ActionType.ACTION_TYPE_MEN)
            else:
                result.append(ActionType.ACTION_TYPE_MEN)
        if len(self.__gang_hou_chu_pai) > 0:
            return result, can_gang_list
        else:
            is_zhuan_wan_gang, gang_card = self.zhuan_wan_gang_de_qi(p)  # 提前验证是否能杠
            is_an_gang, gang_card_list = p.can_an_gang(RuleFc)  # 提前验证是否能暗杠
            if p.card_is_lock():
                if is_zhuan_wan_gang:
                    if gang_card == p.mo_pai:
                        result.append(ActionType.ACTION_TYPE_ZHUAN_WAN_GANG)

                if is_an_gang:
                    valid_gang_cards = [gc for gc in gang_card_list if gc == p.mo_pai]
                    table_cards = deepcopy(p.table_cards)
                    for gang_card in valid_gang_cards:
                        temp_cards = [c for c in p.cards if c != gang_card]
                        # 听牌一致的话可以杠
                        ting_list1 = RuleFc.get_ting_hu_list(table_cards, temp_cards, allow_hu_map, self.__lai_zi,p.que)
                        print("ting_list12",ting_list1,"p.ting_list",p.ting_list)
                        if ting_list1 and ting_list1 == p.ting_list:
                            can_gang_list.append(gang_card)
                            len(can_gang_list) == 1 and result.append(ActionType.ACTION_TYPE_AN_GANG)
            else:
                if is_zhuan_wan_gang:
                    result.append(ActionType.ACTION_TYPE_ZHUAN_WAN_GANG)
                if is_an_gang:
                    result.append(ActionType.ACTION_TYPE_AN_GANG)
        return result, can_gang_list

    def hu_de_qi(self, p: PlayerFCZJ):
        """检查能不能胡 胡牌的类型"""
        can_hu, _, hu_type = self.player_can_hu(p)
        return can_hu, hu_type

    def zhuan_wan_gang_de_qi(self, p: PlayerFCZJ):
        if self.curr_seat_id != p.seat_id:
            return False
        return p.can_zhuan_wan_gang(RuleFc)

    def player_can_hu(self, player: PlayerFCZJ):
        """
        首先判断手牌能不能胡
        其次判断玩家此时能不能胡（平胡不能直接胡）

        主要判断玩家平胡不能点炮
        """
        info, can_hu, hu_path = self.get_hu_type(player)
        if not can_hu:
            return False, [], {}
        return self.check_can_hu(player, can_hu, info, hu_path)

    def check_can_hu(self, player: PlayerFCZJ, can_hu, info, hu_path=None):
        if hu_path is None:
            hu_path = []
        if player.que > 0:
            if self.__curr_card // 10 == player.que:
                return False, [], False
            for t_card in player.cards:
                if t_card // 10 == player.que:
                    return False, [], False
        return can_hu, hu_path, info

    def get_hu_type(self, p: PlayerFCZJ, dian_pao=False):
        """
        此接口计算玩家手牌胡牌类型，玩家能不能胡不管
        params: dian_pao: 是否是计算点炮时的hu_type
        params: only_calc_hu: 仅仅计算是否能胡
        """
        # 1.额外分(与牌型无关, 天胡|地胡|天听|杀报|杠上花|抢杠胡|杠上炮)
        extra_fan = []
        is_zi_mo = self.curr_seat_id == p.seat_id
        table_cards = deepcopy(p.table_cards)
        hand_cards = deepcopy(p.cards)
        allow_hu_map = {HuType.QI_DUI: True, HuType.JIN_GOU_DIAO: True, HuType.DI_LONG_QI: True, }
        hu_type, hu_path = RuleFc.can_hu(table_cards, hand_cards, self.__curr_card, allow_hu_map, self.__lai_zi, False, False)
        if not hu_type:
            return {}, False, []

        gang_card = []  # 记录抢杠|杠上炮时的杠，如果是默认鸡后续算分时需要+鸡的分

        if is_zi_mo:
            if len(self.__gang_hou_mo_pai) > 0:
                extra_fan.append(ExtraHuPai.GANG_SHANG_HUA)  # 杠上花

        else:
            if self.flow_status_is_equal(FlowStatus.T_IN_ZHUAN_WAN_GANG_PAI_CALL):
                gang = ActionType.ACTION_TYPE_ZHUAN_WAN_GANG
                gang_card = [[gang, self.__curr_card]]
                dian_pao and self.__shao_ji_gang_seats.add(self.curr_seat_id)
                extra_fan.append(ExtraHuPai.QIANG_GANG_HU)  # 抢杠胡(烧鸡烧杠)

            if len(self.__gang_hou_chu_pai) > 0:
                extra_fan.append(ExtraHuPai.GANG_SHANG_PAO)
                dian_pao and self.__shao_ji_gang_seats.add(self.curr_seat_id)
                gang_card = self.__gang_hou_chu_pai[-1][:]

        if p.seat_id == self.dealer_id:
            if (not p.all_chu_cards and not p.men_cards) or (p.tian_hu == 1):
                extra_fan.append(ExtraHuPai.TIAN_HU)  # 天胡

        if self.poker.left_count <= const.LIU_JU_COUNT:
            extra_fan.append(ExtraHuPai.SEA_MOON)

        result = {
            "card": p.mo_pai,
            "seat_id": p.seat_id,
            "is_zi_mo": is_zi_mo,
            "hu_type": hu_type,
            "extra_hu_type": extra_fan,
        }

        if not is_zi_mo:
            result["fang_pao_seat_id"] = self.curr_seat_id
            result["card"] = self.__curr_card
            result["gang_card"] = gang_card

        return result, True, hu_path

    @staticmethod
    def update_result_score(accounts, seat_id, check_key, scores, golds):
        """更新玩家结算明细"""
        if scores == 0:
            return

        account = accounts.setdefault(seat_id, {"score": 0, "gold": 0, "detail": {}})

        account["score"] += scores
        account["gold"] += golds

        account["detail"][check_key] = account["detail"].get(check_key, 0) + scores

    def do_check_hua_zhu_score(self, accounts: dict):
        """
        查花猪
        血流红中捉鸡必须打完，所以是否流局都要查花猪
        被花猪则不会叫牌，不参与查叫、包鸡、包杠
        """

        key = ExtraHuPai.HUA_ZHU
        # 花猪分数 = 花猪分 * 获赔/包赔玩家数
        score = self.__extra_score_map.get(key)
        gold = score * self.base_score

        # 查花猪(p为非花猪玩家，other_p为花猪玩家)
        for p in self.seats:
            if p.is_out:
                continue
            if p.seat_id in self.__hua_zhu_seats or p.hua_zhu > 0:
                continue
            for other_p in self.seats:
                if not other_p or other_p.is_out:
                    continue
                if other_p.hua_zhu <= 0:
                    continue
                if other_p.seat_id == p.seat_id:
                    continue

                # 记账
                self.update_result_score(accounts, p.seat_id, key, score, gold)
                self.update_result_score(accounts, other_p.seat_id, key, -score, -gold)
                self.log_info(other_p.uid, other_p.seat_id, "结算花猪", p.hua_zhu)

    def check_chong_feng_ji(self, accounts: dict):
        """结算冲锋鸡接口"""
        if self.__chong_feng_ji_seat_id:
            key = JiType.CHONG_FENG_JI
            self.check_chong_feng_ji_common(accounts, self.__chong_feng_ji_seat_id, key)
        if self.__chong_feng_wgj_seat_id:
            key = JiType.WU_GU_CFJ
            self.check_chong_feng_ji_common(accounts, self.__chong_feng_wgj_seat_id, key)

    def check_chong_feng_ji_common(self, accounts: dict, cfj_get_seat, key):
        """
        具体处理冲锋鸡：
        冲锋鸡玩家已叫牌-向所有玩家收取分数
        冲锋鸡玩家未叫牌-向所有叫牌玩家包冲锋鸡
        冲锋鸡/包冲锋鸡分 = 基础分 * 3

        cfj_get_seat：冲锋鸡玩家seat_id
        key：结算key
        """
        p = self.get_player_by_seat_id(cfj_get_seat)
        if not p or p.is_out:
            return
        if p.seat_id in self.__hua_zhu_seats or p.hua_zhu > 0:
            # 冲锋鸡牌花猪，不再结算
            return
        # 分 和 金币
        score = self.__ji_pai_score_map.get(key)
        gold = score * self.base_score
        # 冲锋鸡玩家未叫牌
        if p.jiao_pai <= 0:
            for other_p in self.seats:
                if other_p.is_out:
                    continue
                if other_p.seat_id == p.seat_id:
                    continue
                if other_p.jiao_pai <= 0:  # 必须叫牌
                    continue
                self.update_result_score(accounts, other_p.seat_id, key, score, gold)
                self.update_result_score(accounts, p.seat_id, key, -score, -gold)
                self.log_info(p.uid, p.seat_id, "结算包冲锋鸡", key, score)
        # 冲锋鸡玩家已叫牌
        else:
            for other_p in self.seats:
                if other_p.is_out:
                    continue
                if other_p.seat_id == p.seat_id:
                    continue
                self.update_result_score(accounts, other_p.seat_id, key, -score, -gold)
                self.update_result_score(accounts, p.seat_id, key, score, gold)
                self.log_info(other_p.uid, other_p.seat_id, "结算赔冲锋鸡", key, score)

    def check_ze_ren_ji(self, accounts):
        """ 结算责任鸡接口 """
        if self.__ze_ren_ji_seat_id and self.__chong_feng_ji_seat_id == 0:
            key = JiType.CHONG_FENG_JI
            self.check_out_ze_ren_ji(accounts, self.__ze_ren_ji_win_seat_id, self.__ze_ren_ji_seat_id, key)

        if self.__ze_ren_wgj_seat_id and self.__chong_feng_wgj_seat_id == 0:
            key = JiType.WU_GU_ZRJ
            self.check_out_ze_ren_ji(accounts, self.__ze_ren_wgj_win_seat_id, self.__ze_ren_wgj_seat_id, key)

    def check_out_ze_ren_ji(self, accounts, ze_ren_win, ze_ren_lose, key):
        """
        具体处理责任鸡（冲锋鸡被碰/杠，称为责任鸡，不计冲锋鸡）：

        被责任玩家分 = 基础 * 3
        其余玩家分 = 基础

        责任鸡玩家已叫牌-向所有玩家收取分数
        责任鸡玩家未叫牌-向所有叫牌玩家包责任鸡

        ze_ren_win：责任鸡玩家（赢分）seat_id
        ze_ren_lose：被责任玩家（输分）seat_id
        key：结算key
        """
        get_zrj_p = self.get_player_by_seat_id(ze_ren_win)
        lose_zrj_p = self.get_player_by_seat_id(ze_ren_lose)
        if not get_zrj_p or get_zrj_p.is_out:
            return
        if not lose_zrj_p or lose_zrj_p.is_out:
            return
        if get_zrj_p.seat_id in self.__hua_zhu_seats or get_zrj_p.hua_zhu > 0:
            return
        # 分 和 金币
        score = self.__ji_pai_score_map.get(key)
        gold = score * self.base_score
        zrj_score = score * 3
        zrj_gold = gold * 3
        # 责任鸡玩家已叫牌
        if get_zrj_p.jiao_pai > 0:
            self.update_result_score(accounts, get_zrj_p.seat_id, key, zrj_score, zrj_gold)
            self.update_result_score(accounts, lose_zrj_p.seat_id, key, -zrj_score, -zrj_gold)
            self.log_info(lose_zrj_p.uid, lose_zrj_p.seat_id, "结算赔责任鸡", key, zrj_score)
            for other_p in self.seats:
                if other_p.is_out:
                    continue
                if other_p.seat_id == get_zrj_p.seat_id:
                    continue
                if other_p.seat_id == lose_zrj_p.seat_id:
                    continue
                # 记录玩家结算明细，统一采用加分
                self.update_result_score(accounts, other_p.seat_id, key, -score, -gold)
                self.update_result_score(accounts, get_zrj_p.seat_id, key, score, gold)
                self.log_info(other_p.uid, other_p.seat_id, "结算赔责任鸡", key, score)
        # 责任鸡玩家未叫牌
        else:
            if lose_zrj_p.jiao_pai > 0:
                self.update_result_score(accounts, get_zrj_p.seat_id, key, -zrj_score, -zrj_gold)
                self.update_result_score(accounts, lose_zrj_p.seat_id, key, zrj_score, zrj_gold)
                self.log_info(get_zrj_p.uid, "结算包责任鸡", key, zrj_score)
                for other_p in self.seats:
                    if other_p.is_out:
                        continue
                    if other_p.seat_id == get_zrj_p.seat_id:
                        continue
                    if other_p.seat_id == lose_zrj_p.seat_id:
                        continue
                    if other_p.jiao_pai <= 0:  # 必须叫牌
                        continue
                    self.update_result_score(accounts, other_p.seat_id, key, score, gold)
                    self.update_result_score(accounts, get_zrj_p.seat_id, key, -score, -gold)
                    self.log_info(get_zrj_p.uid, "结算包责任鸡", key, score)

    def do_check_gang_score(self, accounts: dict):
        """杠分结算逻辑"""
        # 预计算常量避免重复查找
        base_bei_lv = self.base_score
        extra_score_map = self.__extra_score_map

        # 分非出局玩家
        active_players = [
            p for p in self.seats
            if not p.is_out
        ]

        # 1. 未叫牌玩家退税处理
        for seat_id in self.__no_jiao_pai_seats:
            p = self.get_player_by_seat_id(seat_id)
            if not p or p.is_out:
                continue

            ming_gang_count, zwg_count, an_gang_count = self.cal_p_gang_count(p)

            # 封装杠类型处理逻辑
            def process_gang_refund(gang_type, count, is_ming_gang=False):
                if count <= 0: return

                key = getattr(ActionType, gang_type)
                score = extra_score_map.get(key) * count
                gold = score * base_bei_lv

                # 筛选有效赔付玩家
                valid_payers = [
                    op for op in active_players
                    if op.seat_id != p.seat_id
                       and op.jiao_pai > 0
                ]

                for op in valid_payers:
                    # 明杠特殊处理（定向赔付）
                    if is_ming_gang:
                        from_seat_id = next(
                            (z[-1] for z in p.table_cards
                             if z[0] == ActionType.ACTION_TYPE_MING_GANG), None)
                        if op.seat_id != from_seat_id:
                            continue

                    # 执行结算
                    self.update_result_score(accounts, p.seat_id, key, -score, -gold)
                    self.update_result_score(accounts, op.seat_id, key, score, gold)

                log_msg = f"结算{gang_type}分，未叫牌退税"
                self.log_info(p.uid, p.seat_id, log_msg)

            # 处理各类杠型
            process_gang_refund("ACTION_TYPE_MING_GANG", ming_gang_count, is_ming_gang=True)
            process_gang_refund("ACTION_TYPE_ZHUAN_WAN_GANG", zwg_count)
            process_gang_refund("ACTION_TYPE_AN_GANG", an_gang_count)

        # 2. 结算叫牌玩家杠分
        for p in active_players:
            # 跳过特殊状态玩家
            if p.seat_id in self.__shao_ji_gang_seats:
                self.log_info(p.uid, p.seat_id, "玩家被烧杠，不再包杠")
                continue
            if p.seat_id in self.__hua_zhu_seats or p.hua_zhu > 0:
                self.log_info(p.uid, p.seat_id, "玩家被花猪，不再包杠")
                continue

            ming_gang_count, zwg_count, an_gang_count = self.cal_p_gang_count(p)
            is_jiao_pai = p.jiao_pai > 0

            # 封装结算逻辑
            def process_gang_settlement(gang_type, count, is_ming_gang=False):
                if count <= 0: return

                key = getattr(ActionType, gang_type)
                score_val = extra_score_map.get(key)
                score = score_val * count
                gold = score * base_bei_lv

                # 筛选有效玩家
                valid_players = [
                    op for op in active_players
                    if op.seat_id != p.seat_id
                       and (is_jiao_pai or op.jiao_pai > 0)
                ]

                for op in valid_players:
                    # 明杠特殊处理（定向赔付）
                    if is_ming_gang and not is_jiao_pai:
                        from_seat_id = next(
                            (z[-1] for z in p.table_cards
                             if z[0] == ActionType.ACTION_TYPE_MING_GANG), None)
                        if op.seat_id != from_seat_id:
                            continue

                    # 确定分数方向
                    if is_jiao_pai:  # 已叫牌：收分
                        self.update_result_score(accounts, p.seat_id, key, score, gold)
                        self.update_result_score(accounts, op.seat_id, key, -score, -gold)
                    else:  # 未叫牌：赔分
                        self.update_result_score(accounts, p.seat_id, key, -score, -gold)
                        self.update_result_score(accounts, op.seat_id, key, score, gold)

                # 聚合日志
                status = "叫牌玩家" if is_jiao_pai else "未叫牌退税"
                log_msg = f"结算{gang_type}分，{status}"
                self.log_info(p.uid, p.seat_id, log_msg)

            # 处理各类杠型
            process_gang_settlement("ACTION_TYPE_MING_GANG", ming_gang_count, is_ming_gang=True)
            process_gang_settlement("ACTION_TYPE_ZHUAN_WAN_GANG", zwg_count)
            process_gang_settlement("ACTION_TYPE_AN_GANG", an_gang_count)

    @staticmethod
    def cal_p_gang_count(p: PlayerFCZJ):
        """ 统计玩家明杠/暗杠/转弯杠的数量 """
        ming_gang_count = zwg_count = an_gang_count = 0
        for table_card in p.table_cards:
            act = table_card[0]
            if act == ActionType.ACTION_TYPE_MING_GANG:
                ming_gang_count += 1
            elif act == ActionType.ACTION_TYPE_ZHUAN_WAN_GANG:
                zwg_count += 1
            elif act == ActionType.ACTION_TYPE_AN_GANG:
                an_gang_count += 1

        zwg_count -= p.han_bao_dou_zhuan_wan_gang_count  # 憨包豆不结算
        an_gang_count -= p.han_bao_dou_an_gang_count
        return ming_gang_count, zwg_count, an_gang_count

    def do_check_by_liu_ju(self, accounts: dict):
        """
        流局/黄庄算分
        """
        # 1.查花猪
        self.do_check_hua_zhu_score(accounts)

        # 3.冲锋鸡(幺鸡、乌骨鸡)
        self.check_chong_feng_ji(accounts)

        # 4.责任鸡(幺鸡、乌骨鸡)
        self.check_ze_ren_ji(accounts)

        # 5.结算杠分
        self.do_check_gang_score(accounts)
        return accounts

    def do_check_jiao_pai_score(self, accounts: dict):
        """
        查叫牌
        血流红中捉鸡必须打完，所以是否流局都要查叫牌
        被包叫则不参与包鸡、包杠
        """
        # 查叫分(p为叫牌玩家，other_p为未叫牌玩家)
        for p in self.seats:
            if not p or p.is_out:
                continue
            if p in self.__no_jiao_pai_seats or p.jiao_pai <= 0:
                continue
            for other_p in self.seats:
                if other_p.is_out:
                    continue
                if other_p.jiao_pai > 0:
                    continue
                if other_p.seat_id in self.__hua_zhu_seats or other_p.hua_zhu > 0:  # 花猪排除
                    continue
                if other_p.seat_id == p.seat_id:
                    continue

                # 查叫分数 = 叫牌类型分
                score = self.__pai_xing_score_map.get(p.jiao_pai) or 0
                gold = score * self.base_score
                # 记账
                self.update_result_score(accounts, p.seat_id, p.jiao_pai, score, gold)
                self.update_result_score(accounts, other_p.seat_id, p.jiao_pai, -score, -gold)
                self.log_info(self.tid, other_p.uid, other_p.seat_id, "结算未叫牌", p.jiao_pai)

    def check_ji(self, accounts: dict):
        """鸡牌结算逻辑"""
        # 预计算常量避免重复访问
        base_score = self.base_score
        active_players = [p for p in self.seats if not p.is_out]

        # 鸡牌类型映射表（避免循环内重复判断）
        ji_type_map = {
            JiType.JIN_JI.value: JiType.JIN_JI,
            CardsType.YAO_JI.value: JiType.DEFAULT,
            CardsType.WU_GU_JI.value: JiType.WU_GU_JI
        }

        for p in active_players:
            ji_keys = self.__zhuo_ji_cards.get(p.seat_id)
            if not ji_keys:
                continue

            # 分离有效玩家：非花猪、非自身
            valid_players = [
                op for op in active_players
                if op.seat_id != p.seat_id
                   and op.seat_id not in self.__hua_zhu_seats
                   and op.hua_zhu <= 0
            ]

            for ji_key in ji_keys:
                ji_card = ji_key.get('ji_card')
                # 通过映射表快速确定鸡牌类型
                key = ji_type_map.get(ji_card, JiType.FAN_PAI_JI)
                score = ji_key.get('ji_score')
                gold = score * base_score  # 避免循环内重复计算

                if p.jiao_pai > 0:  # 已叫牌：向所有有效玩家收分
                    for other_p in valid_players:
                        self.update_result_score(accounts, p.seat_id, key, score, gold)
                        self.update_result_score(accounts, other_p.seat_id, key, -score, -gold)

                    self.log_info(
                        self.tid, p.uid, p.seat_id,
                        f"叫牌结算{key.name}鸡",
                        f"向{len(valid_players)}玩家收分"
                    )
                else:  # 未叫牌：仅向叫牌玩家赔付
                    jiao_pai_players = [op for op in valid_players if op.jiao_pai > 0]
                    for other_p in jiao_pai_players:
                        self.update_result_score(accounts, p.seat_id, key, -score, -gold)
                        self.update_result_score(accounts, other_p.seat_id, key, score, gold)
                    self.log_info(
                        self.tid, p.uid, p.seat_id,
                        f"未叫牌结算包{key.name}鸡",
                        f"向{len(jiao_pai_players)}玩家赔付"
                    )

    def do_check_by_fan_ji(self, accounts: dict):
        """
        主要结算鸡分、杠分，胡牌分游戏内已即时结算
        整局有人胡（血流是叫牌）时结算，若有玩家破产退出游戏，则不结算
        """
        # 1.查花猪
        self.do_check_hua_zhu_score(accounts)

        # 2.查叫牌
        self.do_check_jiao_pai_score(accounts)

        # 3.结算捉鸡/捉鸡（金鸡、银鸡、默认鸡、站鸡、普通鸡）
        self.check_ji(accounts)

        # 4.冲锋鸡(幺鸡、乌骨鸡)
        self.check_chong_feng_ji(accounts)

        # 5.责任鸡(幺鸡、乌骨鸡)
        self.check_ze_ren_ji(accounts)

        # 6.结算杠分
        self.do_check_gang_score(accounts)
        return accounts

    def do_check_out(self, is_liu_ju=False):
        """
        血流红中捉鸡麻将结算
        黄庄结算与胡牌结算分开，遵循单一职责原则
        account: {"score": xxx, "detail": {...}}
        """
        accounts = {}
        if is_liu_ju:
            accounts = self.do_check_by_liu_ju(accounts)
        else:
            accounts = self.do_check_by_fan_ji(accounts)
        return accounts

    async def round_over(self, over_type=OverType.DEFAULT, is_force=False):

        self.set_flow_status(FlowStatus.T_IN_CHECK_OUT)  # 结算中
        self.set_room_status(RoomStatus.T_CHECK_OUT)  # 结算中

        if over_type == OverType.LIU_JU:
            over_check = self.do_check_out(True)
        elif over_type == OverType.OTHERS_GIVE_UP:
            over_check = {}
            self.not_jiao_pai_player()
        else:
            over_check = self.do_check_out()

        round_data = {
            "round_idx": self.round_idx,
            "seats": [],
            "finish_type": over_type,
            "curr_card": self.__curr_card,
            "dealer": self.dealer_id,
            "left_cards": self.poker.remain_cards,
        }

        over_gold = 0
        fan_ji_score_list = []
        new_data = []
        update_task = []
        for p in self.seats:
            record_data = {
                "record_rid": self.__record_id,
                "record_tid": 0,
                "cs_type": self.service.service_type,
                "round_num": self.round_idx,
                "replay_msg": [],
            }
            p.cancel_timer()  # 清理延时
            if over_check:
                over_seat_id = over_check.get(p.seat_id)
                if over_seat_id:
                    over_gold = over_seat_id.get('gold', 0)
                else:
                    over_gold = 0
            p.update_gold(over_gold)
            if not p.is_robot:
                update_task.append(self.update_user_gold(p, over_gold, ReasonCostGold.CHECK_OUT_MAHJONG))

            # 麻将一局结束返分（金币）结算，相关表更新
            ji_scores = self.__zhuo_ji_cards.get(p.seat_id, [])

            over_data = p.round_over_info()
            print("over_data", over_data)
            over_data["over_check"] = over_check.get(p.seat_id, [])
            over_data["ji_score"] = ji_scores
            record_data["uid"] = p.uid
            record_data["round_status"] = 1 if p.round_score >= 0 else 0
            record_data["round_score"] = p.round_score
            record_data["round_ranking"] = 0
            record_data["round_result"] = p.round_over_info()
            new_data.append(record_data)
            fan_ji_score_list.append({"fan_ji_score": over_gold, "res_gold": p.gold, "seat_id": p.seat_id})
            account_model = S2CRecordAccountInfo.pb_model(p.round_account())
            await self.inner_send(p, CmdRoom.RECORD_ACCOUNT, account_model)

        if update_task:
            await asyncio.gather(*update_task)
        result_data = await RecordsGameSegmentRC.bulk_create_record_game_segment(new_data)
        self.log_info("一轮结束战绩插入", result_data)
        round_data["seats"] = self.room_win_lose_data()
        round_data["winner"] = self.__win_seat_list
        if over_type != OverType.OTHERS_GIVE_UP:
            fan_ji_score_model = S2CFanJiScore.pb_model(fan_ji_score_list)
            await self.inner_broadcast(CmdRoom.FAN_JI_SCORE, fan_ji_score_model)
        round_over_model = S2CRoundOverInfoByLeisure.pb_model(**round_data)
        await self.inner_broadcast(CmdRoom.ROUND_OVER, round_over_model)
        await self.record_game()
        await self.game_over()
        self.clear_round_over()

    def not_jiao_pai_player(self):
        allow_hu_map = {HuType.DI_LONG_QI: True, HuType.JIN_GOU_DIAO: True,
                        HuType.QI_DUI: True}

        for p in self.seats:
            if p.round_score >= 0:
                self.__win_seat_list.append(p.seat_id)
                p.lian_zhuang += 1
                p.is_win = 1
            else:
                p.lian_zhuang = 0
                p.is_win = 0
            if p.que_count() > 0:
                self.log_info(self.tid, p.uid, "玩家缺牌未打完", p.cards, p.que)
                continue
            p.jiao_pai = RuleFc.get_round_over_jiao_pai(
                p.table_cards, p.cards, allow_hu_map, lai_zi=self.__lai_zi)

            if p.jiao_pai <= 0:
                self.__no_jiao_pai_seats.append(p.seat_id)

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
            "curr_card": self.__curr_card,
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
        allow_hu_map = {HuType.DI_LONG_QI: True, HuType.JIN_GOU_DIAO: True,
                        HuType.QI_DUI: True}
        if gang_type == ActionType.ACTION_TYPE_MING_GANG:
            return self.__curr_card
        elif gang_type == ActionType.ACTION_TYPE_ZHUAN_WAN_GANG:
            _, card = p.can_zhuan_wan_gang(RuleFc)
            if card == self.__curr_card:
                return card
            else:
                return 0
        elif gang_type == ActionType.ACTION_TYPE_AN_GANG:
            flag, cards = p.can_an_gang(RuleFc)
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
                    ting_list1 = RuleFc.get_ting_hu_list([], temp_cards, allow_hu_map, self.__lai_zi,p.que)
                    if ting_list1 == p.ting_list:
                        can_gang_list.append(gang_card)
                self.log_info(self.tid, "玩家不能改牌 但能暗杠1", can_gang_list)
                return can_gang_list
            if self.__curr_card in cards:
                return self.__curr_card
            else:
                return cards
        return 0

    def get_ji_pai_score_map(self) -> dict:
        map_copy = JI_PAI_SCORE.copy()
        if self.play_type == PlayType.LEISURE_FCZJ:
            map_copy.update({
                JiType.WU_GU_CFJ: 6,
                JiType.ZE_REN_JI: 1,
                JiType.WU_GU_ZRJ: 2,
                JiType.FAN_PAI_JI: 1,
                JiType.JIN_JI: 10,
            })
            return map_copy
        return map_copy

    def get_pai_xing_score_map(self) -> dict:
        map_copy = PAI_XING_SCORE_MAP.copy()
        if self.play_type == PlayType.LEISURE_FCZJ:
            map_copy.update({
                HuType.SHI_BA_LUO_HAN: 24,  # 十八罗汉
                HuType.SI_JIE_GAO: 24,  # 四节高
                HuType.SI_AN_KE: 16,  # 四暗刻
                HuType.SHI_ER_JIN_CHAI: 12,  # 十二金钗
                HuType.SAN_JIE_GAO: 12,  # 三节高
                HuType.SAN_AN_KE: 8,  # 三暗刻
                HuType.JIN_GOU_DIAO: 8,  # 金钩钓
            })
            return map_copy
        else:
            return map_copy

    def get_extra_score_map(self) -> dict:
        map_copy = EXTRA_SCORE_MAP.copy()
        if self.play_type == PlayType.LEISURE_FCZJ:
            map_copy.update({
                ExtraHuPai.TIAN_HU: 20,
                ExtraHuPai.DI_HU: 2,
                ExtraHuPai.GANG_SHANG_HUA: 6,
                ExtraHuPai.QIANG_GANG_HU: 2,
                ExtraHuPai.SEA_MOON: 8,
                ExtraHuPai.HUA_ZHU: 16,
            })
            return map_copy
        return map_copy

    def get_operate_seats(self):
        return [item[0] for item in self.__player_actions if item]

    def serialize_room_info(self):
        room_info = self.room_info()
        if self.room_status_is_equal(RoomStatus.T_PLAYING):
            room_info["last_card"] = self.__curr_card
            room_info["left_count"] = self.poker.left_count
            room_info["dice_num"] = self.__dice_num
            room_info["ding_que_list"] = self.__que_list
            room_info["operate_seats"] = self.get_operate_seats()
        room_info["lai_zi"] = self.__lai_zi
        room_info["cs_type"] = self.service.service_type
        room_info["rule_details"] = {}
        room_info["rule_details"]["hu_pai_ti_shi"] = 1
        print("房间信息", room_info)
        if self.room_status == RoomStatus.T_CLOSED:
            self.log_info("房间已在关闭状态")
            return None
        return S2CRoomInfo04Mahjong.pb_model(**room_info)

    def serialize_player_info(self, room_player_info):
        for data in room_player_info:
            player = self.get_player_by_seat_id(data["seat_id"])
            if self.has_do_action(player):
                data.pop("operates", None)

        return S2CPlayerInfo05Mahjong.pb_model(room_player_info)

    def dealer_turn(self):
        if self.dealer_id > 0:
            return
        dealer = random.randrange(1, self.max_player_count)
        self.dealer_id = dealer
        return

    def clear_round_over(self):
        self.__recharge_wait = 0
        self.__wait_recharge_seats = []
        self.__gang_hou_mo_pai = []
        self.__gang_hou_chu_pai = []
        self.__fan_ji_cards = []  # 记录所有玩家翻的鸡牌
        self.__fan_ji_result = []  # 记录所有玩家翻的鸡牌，已计算+1或者金鸡
        self.__zhuo_ji_cards = {}  # 记录捉鸡结算信息
        self.__chong_feng_ji_seat_id = 0  # 冲锋幺鸡玩家
        self.__chong_feng_wgj_seat_id = 0  # 冲锋乌骨鸡玩家
        self.__round_first_ji = 0  # 记录冲锋鸡
        self.__round_first_wgj = 0  # 记录冲锋乌骨鸡
        self.__ze_ren_ji_seat_id = 0  # 责任幺鸡玩家
        self.__ze_ren_ji_win_seat_id = 0
        self.__ze_ren_wgj_seat_id = 0  # 乌骨责任鸡玩家
        self.__ze_ren_wgj_win_seat_id = 0
        self.__before_seat_id = 0
        self.__after_peng = False
        self.__shao_ji_gang_seats = set()
        self.__player_actions = []  # 玩家动作
        self.__curr_card_exist = 0  # 当前牌是否存在
        self.__can_fan_ji_seats = []
        self.__record_id = 0

    async def record_game(self):

        all_scores = [p.round_score for p in self.seats if p]
        sorted_scores = sorted(all_scores, reverse=True)
        score_rank_map = {}
        for idx, score in enumerate(sorted_scores):
            score_rank_map[score] = idx + 1

        final_result = {
            "level_desc": self.level_desc
        }

        for idx, p in enumerate(self.seats):
            if not p or p.is_robot:
                continue
            num = 1 if idx == 0 else 0
            final_result.update(p.game_over_data)
            final_ranking = score_rank_map[p.round_score]
            final_grade = 1 if final_ranking == 1 else 0
            over_record = await RecordsGameTotalRC.create_record_game_total(self.__record_id, p.uid, p.round_score >= 0, p.round_score
                                                                            , final_ranking, final_grade, final_result, num)
            self.log_info("休闲场总结算战绩插入", over_record)

    @staticmethod
    def update_player_max_score(p:PlayerFCZJ, total_score, base_score, extra_score, hu_type, extra_hu_list):
        if not p.is_robot:
            # 更新玩家最高总分
            if total_score > p.max_multiple:
                p.max_multiple = total_score

            if base_score == 0:
                # 当基础分为0时，用额外分比较牌型
                if extra_score > p.hu_type_score:
                    p.hu_type_score = extra_score
                    p.max_hu_type = extra_hu_list[0]
            else:
                # 基础分不为0时直接比较
                if base_score > p.hu_type_score:
                    p.hu_type_score = base_score
                    p.max_hu_type = hu_type


    @staticmethod
    def compare_hu_type(last_hu_type, curr_hu_type):
        map_copy = PAI_XING_SCORE_MAP.copy()
        map_copy.update({
            HuType.SHI_BA_LUO_HAN: 24,  # 十八罗汉
            HuType.SI_JIE_GAO: 24,  # 四节高
            HuType.SI_AN_KE: 16,  # 四暗刻
            HuType.SHI_ER_JIN_CHAI: 12,  # 十二金钗
            HuType.SAN_JIE_GAO: 12,  # 三节高
            HuType.SAN_AN_KE: 8,  # 三暗刻
            HuType.JIN_GOU_DIAO: 8,  # 金钩钓
        })
        last_base_score = map_copy[last_hu_type] or 0
        curr_base_score = map_copy[curr_hu_type] or 0
        if last_base_score >= curr_base_score:
            return last_hu_type, HuType.find_member_by_val(last_hu_type).phrase
        else:
            return curr_hu_type, HuType.find_member_by_val(curr_hu_type).phrase
