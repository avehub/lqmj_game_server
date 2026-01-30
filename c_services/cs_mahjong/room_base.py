import asyncio
from collections import Counter
from datetime import datetime

from common.proto.py_pb2.ws_c2s import gang_model, shang_ga_model, exchange_model, player_position_model
from common.proto.py_pb2.ws_leisure import S2CReady07Mahjong, S2CRoomInfo04Mahjong, S2CPlayerInfo05Mahjong, \
    S2CRoundStartMahjong, \
    S2CShangGaMahjong, S2CShangGaBeginMahjong, S2CDealCardsMahjong, s2c_one_of_model, S2CPublicOperatesMahjong, \
    S2CTurnToMahjong, \
    S2CPlayCardsMahjong, S2CFirstJiMahjong, S2CHuInfoMahjong, S2CHuAfterCards, S2CMenInfoMahjong, S2CAfterGangMoCard, \
    S2CGangInfo, \
    S2CHuBaseInfo, S2CExchangeCardsInfo, S2CTianTingInfo, S2CStartDingQueInfo, S2CNotifyPosition, S2CStartExchangeCards, \
    S2CRoomDismissInfo
from common.utils import earth_position
from . import const
from .player import Player
from .poker import Poker
from .rule import Rule
from .const import (FlowStatus, TimerDelay, ChangeThreeType, OverType, HuType, ActionType, ChangeCardsType,
                    ExtraHuPai, JiType, CardsType, CheckType, PlayerStatusType, PlayType, SPECIAL_HU_TYPE_BY_EIGHT)
import random
from c_services.base.base_card_room import BaseCardRoom
from ..const.cs_enum_const import RoomStatus, CmdRoom, CmdClub, ClubMsgType, CmdRobotCal
from common.public.enum_const import StaCode, ServiceEnum


class Room(BaseCardRoom):
    def __init__(self, tid, service, room_conf):
        self.__liang_men_pai = room_conf.get("rule_details").get("liang_men_pai", 1)  # 两门牌
        super().__init__(tid, service, room_conf, Poker, self.__liang_men_pai)
        self.__shang_ga_list = [1, 2, 3, 4, 5, 0]
        self.__exchange_cards_info = {}
        self.__dice_num = None
        self.__over_type = 0
        self.__card_count = 13
        self.__curr_card = 0
        self.__que_list = [1, 2, 3]
        self.__gang_hou_mo_pai = []
        self.__gang_hou_chu_pai = []
        self.__tui_zhang_can_hu = 0
        self.__curr_action_player = None
        self.__jie_pao_count = -1
        self.__bird_count = 1  # 默认只翻一张牌
        self.__round_first_ji = 0  # 记录冲锋鸡 0 表示还有 1表示无
        self.__round_first_wgj = 0  # 记录冲锋乌骨鸡
        self.__record_cfj = 0  # 冲锋鸡处理（主要面对炸捡）1被炸捡
        self.__record_cfwgj = 0  # 冲锋鸡处理（主要面对炸捡）1被炸捡
        self.__chong_feng_ji_seat_id = 0  # 冲锋幺鸡鸡玩家
        self.__ze_ren_ji_seat_id = 0  # 责任幺鸡玩家
        self.__cfwgj_seat_id = 0  # 冲锋乌骨鸡玩家
        self.__ze_ren_ji_win_seat_id = 0
        self.__ze_ren_wgj_seat_id = 0  # 乌骨责任鸡玩家
        self.__ze_ren_wgj_win_seat_id = 0
        self.__is_yi_pao_duo_xiang = 0  # 是否是一炮多响
        self.__after_peng = False  # 记录是否是碰后出牌（若此时玩家退出重进同步信息，让客户端知道）
        self.__men_in_tian_ting = False  # 在报听流程中闷
        self.__curr_card_exist = 0  # 当前牌是否存在
        self.__before_seat_id = 0
        self.__win_seat_list = []

        self.__ji_cards = None
        self.__player_actions = []  # 玩家动作
        self.__men_record = []
        self.__winner_list = []
        self.__kai_pai_hu_info = []  # 玩家开牌记录胡牌信息，后续不必再计算一遍
        self.__shao_ji_gang_seats = set()  # 被烧杠者
        self.__zha_jian_seats = set()  # 记录炸捡玩家，主要解决A打牌，B炸捡，C正常捡的情况
        self.__record_operates = {}  # 当玩家手牌未固定时，别人出的牌与自己手牌形成能胡 或和手牌固定后都记录
        self.__exchange_three = self.rule_detail.get("exchange_three", 0)  # 换3张
        self.__exchange_cards_type = self.rule_detail.get("__exchange_cards_type", 0)
        self.__four_card_bao_ting = self.rule_detail.get("four_card_bao_ting", 0)
        self.__shang_ga = int(self.rule_detail.get("shang_ga", 0))  # 估卖（额外卖）
        self.__gu_mai_score = self.rule_detail.get("gu_mai_score", 0)
        self.__zi_mo_jia_bei = self.rule_detail.get("zi_mo_jia_bei", 1)  # 自摸翻倍
        self.__bao_ting = self.rule_detail.get("bao_ting", 0)  # 报听
        self.__left_three_bi_hu = self.rule_detail.get("left_3_bi_hu", 1)  # 最后三张必胡
        self.__di_long_qi = self.rule_detail.get("di_long_qi", 0)  # 地七对改成选项
        self.__xiao_pai_bi_men = self.rule_detail.get("xiao_pai_bi_men", 0)  # 小牌必闷
        self.__bao_ting_bi_men = self.rule_detail.get("bao_ting_bi_men", 0)  # 报听必闷(小胡报听必闷)
        self.__jian_gang_san = self.rule_detail.get("jian_gang_san", 0)  # 见杠三
        self.__gang_score = self.rule_detail.get("gang_score") or 1  # 杠牌分约定
        self.__suo_de_jia_one = self.rule_detail.get("suo_de_jia_1", 0)  # 所得加1
        self.__bi_men_yi_shou = self.rule_detail.get("bi_men_yi_shou", 0)  # 平胡需要必闷一手
        self.__hu_pai_ti_shi = self.rule_detail.get("hu_pai_ti_shi", 0)
        # self.__liang_men_pai = self.rule_detail.get("liang_men_pai", 1)  # 两门牌
        self.__fan_ji_pai = self.rule_detail.get("fan_ji_pai", 1)  # 翻牌鸡
        self.__huang_zhuang_bu_huang_ji = self.rule_detail.get("huang_zhuang_bu_huang_ji", 0)  # 黄庄不黄鸡杠
        self.__chong_feng_ji = self.rule_detail.get("chong_feng_ji", 0)  # 冲锋鸡
        self.__ze_ren_ji = 1  # self.rule_detail.get("ze_ren_ji", 1)  # 责任鸡
        self.__man_tang_ji = self.rule_detail.get("man_tang_ji", 0)  # 满堂鸡
        self.__zhan_ji = self.rule_detail.get("zhan_ji", 0)  # 站鸡（手里的额外加1）
        self.__double_bao = self.rule_detail.get("double_bao", 0)  # 牌型和鸡杠都双倍包
        self.__bao_ji = self.rule_detail.get("bao_ji", 1)  # 包鸡
        self.__bao_gang = self.rule_detail.get("bao_gang", 1)  # 包杠
        self.__ruan_ying_ji = self.rule_detail.get("ruan_ying_ji", 0)  # 软硬鸡
        self.__ruan_ying_dou = self.rule_detail.get("ruan_ying_dou", 0)  # 软硬豆
        self.__week_ji = self.rule_detail.get("week_ji", 0)  # 星期鸡
        self.__wind_ji = self.rule_detail.get("wind_ji", 0)  # 吹风机
        self.__limit_lose = self.rule_detail.get("limit_lose", 0)  # 限制输分
        self.__decision_sec = self.rule_detail.get("decision_sec", 0)
        self.__chao_shi_time = self.rule_detail.get("chao_shi_time", 0)  # 多少时间进入超时

        self.__qiang_gang_shao_ji = self.rule_detail.get("qiang_gang_shao_ji", 0)
        self.__qiang_gang_shao_dou = self.rule_detail.get("qiang_gang_shao_dou", 0)
        self.__gan_kou = self.rule_detail.get("gan_kou", 0)
        self.__sea_moon = self.rule_detail.get("sea_moon", 0)

        self.__ji_and_gang_score = 0
        self.__four_card_no_near = 0
        self.__four_card_tian_hu = 0
        self.__eight_card_tian_hu = 0
        if self.__four_card_bao_ting:
            self.__four_card_no_near = self.rule_detail.get("four_card_no_near", 0)
            self.__eight_card_tian_hu = self.rule_detail.get("eight_card_tian_hu", 0)
            self.__four_card_tian_hu = self.rule_detail.get("four_card_tian_hu", 0)
        self.__lian_zhuang = 0
        self.__lai_zi = 0
        self.__lai_zi_ji = self.rule_detail.get("lai_zi_ji", 0)
        if self.play_type == PlayType.ZUN_YI_LAI_ZI or (self.play_type == PlayType.AN_SHUN_MJ and self.__lai_zi_ji):
            self.__lai_zi = self.rule_detail.get("lai_zi", CardsType.YI_TONG)
        if self.play_type in (PlayType.GUI_YANG_4, PlayType.BI_JIE_MJ):
            self.__lian_zhuang = self.rule_detail.get("lian_zhuang", 0)
        self.__yuan_bao = 0
        if self.play_type in (PlayType.GUI_YANG_4, PlayType.GUI_YANG_3, PlayType.BI_JIE_MJ, PlayType.ZUN_YI_LAI_ZI):
            # 起手牌满足听牌条件才能报听。摸第一张牌后不可再报听，庄家除外。
            self.__yuan_bao = self.rule_detail.get("yuan_bao", 0)
        self.__yin_ji = self.rule_detail.get("yin_ji", 0)
        self.__jin_yin_wu = self.rule_detail.get("jin_yin_wu", 0)
        self.__fan_jin_ji_cards = set()  # 记录翻金鸡cards
        self.__fan_yin_ji_cards = set()  # 记录翻银鸡cards
        # self.__exchange_first = 0
        # if self.__exchange_three != ChangeThreeType.NO_CHANGE:
        #     self.__exchange_first = self.rule_detail.get("__exchange_first", 0)
        if self.__fan_ji_pai:  # 有翻鸡才有摇摆鸡和本鸡
            self.__yao_bai_ji = self.rule_detail.get("shang_xia_ji", 0)  # 摇摆鸡(上下鸡)
            self.__ben_ji = self.rule_detail.get("ben_ji", 0)  # 本鸡
            self.__san_ji = self.rule_detail.get("san_ji", 0)  # 三鸡
            if self.__san_ji:
                self.__yao_bai_ji = 1
                self.__ben_ji = 1

        self.__wu_gu_ji = self.rule_detail.get("wu_gu_ji", 0)  # 乌骨鸡（也算默认鸡）
        self.__default_ji = {CardsType.YAO_JI}
        if self.__wu_gu_ji:
            self.__default_ji.add(CardsType.WU_GU_JI)
        if self.play_type == PlayType.GUI_YANG_4:
            self.__di_long_qi = 1

        if self.play_type == PlayType.JIAN_LOU_XUE_LIU:
            self.__liang_men_pai = 1

        self.__ji_pai_score = self.get_ji_pai_score_map()

        if self.__jian_gang_san or self.play_type == PlayType.ZUN_YI_LAI_ZI:
            self.__gang_score = self.__ji_pai_score.get(JiType.MING_GANG)

        self.__have_men_jian_hu = self.play_type != PlayType.JIAN_LOU_XUE_LIU

        if self.__have_men_jian_hu:
            self.__decision_sec = self.rule_detail.get("decision_sec", 0)
            self.__tui_zhang_can_hu = self.rule_detail.get("tui_zhang_can_hu", 0)
        self.__zhuo_ji_card = 0
        self.__week_ji_num = {}
        if self.__week_ji:
            today = datetime.today()
            num = today.isoweekday()
            self.__week_ji_num = {num + 10, num + 20, num + 30}

    @property
    def liang_men_pai(self):
        return self.__liang_men_pai

    @property
    def lian_zhuang(self):
        return self.__lian_zhuang

    @property
    def que_list(self):
        return self.__que_list

    @property
    def bao_ji(self):
        return self.__bao_ji

    @property
    def bao_gang(self):
        return self.__bao_gang

    @property
    def fan_jin_ji_cards(self):
        return self.__fan_jin_ji_cards

    @property
    def fan_yin_ji_cards(self):
        return self.__fan_yin_ji_cards

    @property
    def ji_pai_score(self):
        return self.__ji_pai_score

    @property
    def yuan_bao(self):
        return self.__yuan_bao

    @property
    def default_ji(self):
        return self.__default_ji

    def add_default_ji(self, value):
        self.__default_ji.add(value)

    @property
    def lai_zi(self):
        return self.__lai_zi

    @property
    def curr_card(self):
        return self.__curr_card

    @property
    def ji_cards(self):
        return self.__ji_cards

    @ji_cards.setter
    def ji_cards(self, value):
        self.__ji_cards = value

    @property
    def gang_hou_mo_pai(self):
        return self.__gang_hou_mo_pai

    @property
    def shao_ji_gang_seats(self):
        return self.__shao_ji_gang_seats

    @property
    def gang_hou_chu_pai(self):
        return self.__gang_hou_chu_pai

    @property
    def winner_list(self):
        return self.__winner_list

    @property
    def man_tang_ji(self):
        return self.__man_tang_ji

    @property
    def chong_feng_ji_seat_id(self):
        return self.__chong_feng_ji_seat_id

    @property
    def cfwgj_seat_id(self):
        return self.__cfwgj_seat_id

    @property
    def yin_ji(self):
        return self.__yin_ji

    @property
    def kai_pai_hu_info(self):
        return self.__kai_pai_hu_info

    @property
    def win_seat_list(self):
        return self.__win_seat_list

    @property
    def zhuo_ji_card(self):
        return self.__zhuo_ji_card

    @zhuo_ji_card.setter
    def zhuo_ji_card(self, value):
        self.__zhuo_ji_card = value

    @property
    def ze_ren_ji(self):
        return self.__ze_ren_ji

    @property
    def week_ji(self):
        return self.__week_ji

    @property
    def di_long_qi(self):
        return self.__di_long_qi

    @property
    def four_card_tian_hu(self):
        return self.__four_card_tian_hu

    @property
    def four_card_no_near(self):
        return self.__four_card_no_near

    @property
    def exchange_cards_info(self):
        return self.__exchange_cards_info

    def serialize_room_info(self):
        room_info = self.room_info()
        if self.room_status in (RoomStatus.T_PLAYING, RoomStatus.T_DISMISS):
            room_info["last_card"] = self.__curr_card
            room_info['last_seat_id'] = self.__before_seat_id
            room_info["left_count"] = self.poker.left_count
            room_info["dice_num"] = self.__dice_num
            room_info["ding_que_list"] = self.__que_list
            exchange_data = []
            for seat_id, c_info in self.__exchange_cards_info.items():
                info = {
                    "ex_cards": c_info.get("ex_cards"),
                    "seat_id": seat_id
                }
                exchange_data.append(info)
            room_info["exchange_seats"] = exchange_data
            room_info["operate_seats"] = self.get_operate_seats()
            room_info["shang_ga_list"] = self.__shang_ga_list
        room_info["lai_zi"] = self.__lai_zi
        room_info["match_room_id"] = self.match_room_id
        room_info["match_round"] = self.match_round
        room_info["total_match_round"] = self.total_match_round
        # self.log_info("房间信息", room_info)
        if self.room_status == RoomStatus.T_CLOSED:
            self.log_info("房间已在关闭状态")
            return None
        return S2CRoomInfo04Mahjong.pb_model(**room_info)

    def serialize_player_info(self, room_player_info):
        for data in room_player_info:
            player = self.get_player_by_seat_id(data["seat_id"])
            if self.has_do_action(player):
                data.pop("operates", None)
            else:
                self.is_bi_hu(data)
        return S2CPlayerInfo05Mahjong.pb_model(room_player_info)

    def get_operate_seats(self):
        return [item[0] for item in self.__player_actions if item]

    def is_bi_hu(self, info):
        """ 断线重连同步信息（是否是必胡） """
        if not self.__have_men_jian_hu:
            return
        operates = info.get("operates") or []
        if ActionType.ACTION_TYPE_HU in operates or ActionType.ACTION_TYPE_JIAN in operates:
            if self.flow_status == FlowStatus.T_IN_ZHUAN_WAN_GANG_PAI_CALL:
                info["is_bi_hu"] = 1
            if self.__gang_hou_chu_pai:
                info["is_bi_hu"] = 1
            # 2025/6/9最后三张必开重连遗漏
            if self.poker.left_count < const.XUE_LIU_LEFT_BI_HU:
                info["is_bi_hu"] = 1
            return

    async def force_set_gu_mai_score(self):
        """ 强制设置估牌分 """
        for p in self.seats:
            p.shang_ga_score = self.__gu_mai_score
            p.has_shang_ga = True
            data = {"seat_id": p.seat_id, "shang_ga": p.shang_ga_score}
            data_model = S2CShangGaMahjong.pb_model(**data)
            await self.inner_broadcast(CmdRoom.PLAYER_SHANG_GA, data_model)
        self.log_info("强制设置估牌分", self.__gu_mai_score)
        self.call_flow(1, self.deal_cards)

    async def start_player_shang_ga(self):
        if self.room_status not in (RoomStatus.T_PLAYING, RoomStatus.T_DISMISS):
            self.log_info("开始估牌分房间状态不在游戏中", self.room_status)
            return
        self.set_flow_status(FlowStatus.T_IN_GU_MAI)
        data = {
            "can_shang_list": self.__shang_ga_list,
            "seconds": TimerDelay.SHANG_GA_TIME,
            "in_flow": self.flow_status
        }
        data_model = S2CShangGaBeginMahjong.pb_model(**data)
        await self.inner_broadcast(CmdRoom.PLAYER_SHANG_GA_BEGIN, data_model)
        for p in self.seats:
            if not p.has_shang_ga:
                if p.trustee:
                    await self.player_shang_ga_call(p, 0)

    async def player_shang_ga_call(self, p, shang_ga_score):
        """ 与卖牌(额外加注)类似 """
        if p.has_shang_ga:
            return StaCode.RULE_ERR

        if shang_ga_score not in self.__shang_ga_list:
            return StaCode.RULE_ERR
        self.log_info("设置估牌分", shang_ga_score, p.uid, "seat_id", p.seat_id)
        p.has_shang_ga = True
        p.shang_ga_score = shang_ga_score
        data = {"seat_id": p.seat_id, "shang_ga": p.shang_ga_score}
        data_model = S2CShangGaMahjong.pb_model(**data)
        await self.inner_broadcast(CmdRoom.PLAYER_SHANG_GA, data_model)

        is_all_shang_ga = True
        for p in self.seats:
            if not p.has_shang_ga:
                is_all_shang_ga = False
                break
        if is_all_shang_ga:
            self.call_flow(1, self.deal_cards)
        return StaCode.PASS

    async def deal_cards(self):
        """ 发牌 """
        if self.flow_status not in (FlowStatus.T_IN_GU_MAI, FlowStatus.T_IN_ROUND_START):
            self.log_info(f"flow error: {self.flow_status}")
            return
        self.log_info("开始发牌")
        self.set_flow_status(FlowStatus.T_IN_DEAL_CARDS)
        # await self.async_set_room_status(RoomStatus.T_PLAYING)
        if self.__four_card_bao_ting:
            return await self.start_bao_ting_by_four_cards()
        all_cards = self.poker.deal_cards(self.max_player_count, self.deal_cards_count)
        data = {}
        c = self.poker.pop()  # 庄占起手，再摸一张
        for i, p in enumerate(self.seats):
            p.cards = all_cards[i]
            data["hand_cards"] = p.cards
            p.sort_cards()
            data["mo_pai"] = 0
            data["seat_id"] = p.seat_id
            if p.seat_id == self.dealer_id:
                self.__curr_card = c
                p.rev_card(c)
                p.mo_pai = c
                data["mo_pai"] = c
            data["left_count"] = self.poker.left_count
            data_model = S2CDealCardsMahjong.pb_model(**data)
            self.log_info("玩家手牌", p.cards, "座位号", p.seat_id)
            await self.inner_send(p, CmdRoom.DEALER_CARDS, data_model)

        if self.is_exchange_three():
            return await self.start_exchange_three()
        await self.ding_que_or_tian_ting() if self.__bao_ting else self.call_flow(0, self.enter_mo_pai_call)

    def dealer_turn(self):
        """ 庄家轮转的逻辑 """
        dealer = self.dealer()
        if not dealer:  # 首局随机庄
            if self.owner:
                p = self.get_player_by_uid(self.owner)
                if p:
                    self.dealer_id = p.seat_id
                    return
            dealer = random.randrange(1, self.in_room_count + 1)
            self.dealer_id = dealer
            return

        if self.__winner_list:  # 正常胡牌
            winner_len = len(self.__winner_list)
            dealer = None
            if winner_len == 1:
                dealer = self.__winner_list[0].seat_id
            elif winner_len > 1:
                dealer = self.curr_seat_id
            if not dealer or dealer <= 0:
                dealer = random.randrange(1, self.in_room_count + 1)
            self.dealer_id = dealer
            return

    def get_player_by_uid(self, uid):
        for p in self.seats:
            if p.uid == uid:
                return p

    def clear_room_round_start(self):
        super().clear_room_round_start()
        self.clear_room_init()

    def clear_room_init(self):
        self.__win_seat_list = []
        self.__gang_hou_mo_pai = []
        self.__gang_hou_chu_pai = []
        self.__round_first_ji = 0
        self.__round_first_wgj = 0
        self.__chong_feng_ji_seat_id = 0
        self.__cfwgj_seat_id = 0
        self.__ze_ren_ji_seat_id = 0
        self.__ze_ren_ji_win_seat_id = 0
        self.__ze_ren_wgj_seat_id = 0  # 责任鸡玩家
        self.__ze_ren_wgj_win_seat_id = 0
        self.__jie_pao_count = 0
        self.__is_yi_pao_duo_xiang = 0
        self.__men_record = []
        self.__exchange_cards_info = {}
        self.clear_table_actions()
        self.__record_operates = {}
        self.__kai_pai_hu_info = []
        self.__shao_ji_gang_seats = set()
        self.__zha_jian_seats = set()
        self.__ji_cards = None
        self.__record_cfj = 0
        self.__record_cfwgj = 0
        self.__men_in_tian_ting = False
        self.__dice_num = None
        self.__fan_jin_ji_cards = set()
        self.__fan_yin_ji_cards = set()
        self.__zhuo_ji_card = 0
        self.__ji_and_gang_score = 0

    def is_exchange_three(self):
        """ 判断是否换三张 """
        if self.__exchange_three == 0:
            return False
        if self.__exchange_cards_info:  # 换过则不再换
            return False
        if self.__exchange_three == ChangeThreeType.PER_ROUND:
            return True
        if self.__exchange_three == ChangeThreeType.SAME_POINT:
            return self.__dice_num[0] == self.__dice_num[1] or all(item in self.__dice_num for item in [1, 6])
        if self.__exchange_three == ChangeThreeType.LIU_JU:
            return self.__over_type == OverType.LIU_JU
        return False

    def can_four_card_bao_ting(self):
        if self.__exchange_three == ChangeThreeType.PER_ROUND:
            return False
        if self.__exchange_three == ChangeThreeType.SAME_POINT and (
                self.__dice_num[0] == self.__dice_num[1] or all(item in self.__dice_num for item in [1, 6])):
            return False
        if self.__exchange_three == ChangeThreeType.LIU_JU and self.__over_type == OverType.LIU_JU:
            return False
        return True

    async def start_bao_ting_by_four_cards(self):
        """ 四张牌报听 """
        self.log_info("进入四张报听")
        all_cards = self.poker.deal_cards(self.max_player_count, self.__four_card_bao_ting)
        self.set_flow_status(FlowStatus.T_IN_FOUR_BAO_TING)
        for i, p in enumerate(self.seats):
            p.cards = all_cards[i]
            cards = p.cards
            operates = []

            if self.__four_card_tian_hu or not (cards[0] == cards[1] == cards[2] == cards[3]):
                operates = []
                hu_type = Rule.can_tian_ting(
                    [], p.cards, p.que, {HuType.QI_DUI: True, HuType.JIN_GOU_DIAO: True,
                                         HuType.DI_LONG_QI: self.__di_long_qi,
                                         HuType.FOUR_CARD_NO_NEAR: self.__four_card_no_near,
                                         HuType.FOUR_CARD_IS_SAME: self.__four_card_tian_hu})
                if hu_type:
                    operates = [ActionType.ACTION_TYPE_TIAN_TING]
                    if cards[0] == cards[1] == cards[2] == cards[3]:
                        operates.append(ActionType.ACTION_TYPE_HU)
            if operates:
                operates.append(ActionType.ACTION_TYPE_PASS)
            p.operates = operates

        if self.can_four_card_bao_ting() and self.can_operates():  # 有人可以胡，则需要等待
            self.log_info("有人可以四张报听")
            data = {
                "left_count": self.poker.left_count,
                "seconds": TimerDelay.TIAN_TING_SECONDS,
                "in_flow": self.flow_status,
            }
            for p in self.seats:
                data["operates"] = p.operates
                data["seat_id"] = p.seat_id
                data["hand_cards"] = p.cards
                data_model = S2CPublicOperatesMahjong.pb_model(**data)
                await self.inner_send(p, CmdRoom.PUBLIC_OPERATES, data_model)
            if not self.__decision_sec:
                return
            self.call_flow(TimerDelay.TIAN_TING_SECONDS, self.tian_ting_time_out_by_four)
        # todo: 没人听就补牌
        if self.__eight_card_tian_hu:
            return await self.start_eight_cards_tian_hu()
        await self.deal_bu_pai(self.__four_card_bao_ting)

    async def start_eight_cards_tian_hu(self):
        self.__player_actions = []
        self.set_flow_status(FlowStatus.T_IN_EIGHT_TIAN_HU)
        seat_id_list = [p.seat_id for p in self.seats if not p.tian_ting]
        self.poker.not_set_cards_ordered(seat_id_list, 4, 4, False)

        for p in self.seats:
            if p.tian_ting or len(p.men_cards) > 0:
                continue
            for i in range(4):
                c = self.poker.pop()
                p.rev_card(c)
        for i, p in enumerate(self.seats):
            if p.tian_ting or len(p.men_cards) > 0:
                continue
            operates = []
            can_hu, _, hu_info = self.player_can_hu(p)
            if can_hu:
                operates = [ActionType.ACTION_TYPE_HU, ActionType.ACTION_TYPE_MEN]
            if operates:
                operates.append(ActionType.ACTION_TYPE_PASS)
            p.operates = operates
        if self.can_operates():  # 有人可以胡，则需要等待
            self.log_info("有人可以八张天胡")
            data = {
                "left_count": self.poker.left_count,
                "seconds": TimerDelay.TIAN_TING_SECONDS,
                "in_flow": self.flow_status,
            }
            for p in self.seats:
                data["operates"] = p.operates
                data["seat_id"] = p.seat_id
                data["hand_cards"] = p.cards
                data_model = S2CPublicOperatesMahjong.pb_model(**data)
                await self.inner_send(p, CmdRoom.PUBLIC_OPERATES, data_model)
            if not self.__decision_sec:
                return
            await self.deal_operates_call_time_out()
            return
        await self.deal_bu_pai(self.__eight_card_tian_hu)

    def can_operates(self):
        for p in self.seats:
            if len(p.operates) > 0:
                self.log_info("玩家", p.seat_id, "可以操作", p.operates)
                return True
        return False

    def can_tian_ting(self):
        for p in self.seats:
            if ActionType.ACTION_TYPE_TIAN_TING in p.operates:
                self.log_info("玩家", p.seat_id, "可以天听", p.operates)
                return True
        return False

    async def tian_ting_time_out_by_four(self):
        if self.flow_status != FlowStatus.T_IN_FOUR_BAO_TING:
            self.log_info("四张报听超时，且不在四张报听流程中", self.flow_status)
            return
        for p in self.seats:
            if p.can_tian_ting == -1:
                continue
            if ActionType.ACTION_TYPE_TIAN_TING in p.operates:
                # 如果可以四张报听，超时后自动过
                code = await self.on_player_pass(p)
                if code != StaCode.PASS:  # 自动过失败后直接移除天听
                    if ActionType.ACTION_TYPE_TIAN_TING in p.operates:
                        p.remove_operates(ActionType.ACTION_TYPE_TIAN_TING)
                    one_of_model = s2c_one_of_model()
                    one_of_model.seat_id = self.curr_seat_id
                    await self.inner_send(p, CmdRoom.PLAYER_PASS, one_of_model)
                self.log_info("四张报听超时，自动过", p.uid, "seat_id", p.seat_id)
        # 跳过后进行补牌发牌
        await self.deal_bu_pai(self.__four_card_bao_ting)

    async def deal_bu_pai(self, bu_card_count):
        """ 处理补牌 """
        if self.flow_status not in (FlowStatus.T_IN_FOUR_BAO_TING, FlowStatus.T_IN_EIGHT_TIAN_HU):
            self.log_info("补牌发牌，不在可补牌流程中", self.flow_status)
            return
        self.set_flow_status(FlowStatus.T_IN_DEAL_CARDS)
        seat_id_list = [p.seat_id for p in self.seats if not p.tian_ting]
        self.poker.not_set_cards_ordered(seat_id_list, bu_card_count, self.__card_count - bu_card_count)
        has_player_tian_ting = False
        for p in self.seats:
            if p.tian_ting or len(p.men_cards) > 0:
                has_player_tian_ting = True
                continue
            for i in range(self.__card_count - bu_card_count):
                c = self.poker.pop()
                p.rev_card(c)

        data = {}
        cards_count = {}

        for p in self.seats:
            cards_len = len(p.cards)
            if p.seat_id == self.dealer_id:
                cards_len += 1
            cards_count[p.seat_id] = cards_len
        data["cards_count"] = cards_count

        c = self.poker.pop()  # 庄占起手，再摸一张
        for p in self.seats:
            data["mo_pai"] = 0
            p.sort_cards()
            if p.seat_id == self.dealer_id:
                self.__curr_card = c
                p.rev_card(c)
                p.mo_pai = c
                data["mo_pai"] = c
            data["hand_cards"] = p.cards
            data["seat_id"] = p.seat_id
            data["left_count"] = self.poker.left_count
            self.log_info(self.tid, p.uid, "补牌发牌：", p.cards, p.mo_pai)
            data_model = S2CDealCardsMahjong.pb_model(**data)
            await self.inner_send(p, CmdRoom.DEALER_CARDS, data_model)

        if not has_player_tian_ting and self.is_exchange_three():
            return await self.start_exchange_three()
        await self.start_tian_ting() if self.__bao_ting else self.call_flow(0, self.enter_mo_pai_call)

    async def start_exchange_three(self):
        if self.flow_status != FlowStatus.T_IN_DEAL_CARDS:
            self.log_info(self.tid, "开始换三张，不在发牌流程中", self.flow_status)
            return
        if self.get_tian_ting_player_count() + 1 >= self.max_player_count:
            return self.enter_mo_pai_call()
        self.set_flow_status(FlowStatus.T_IN_EXCHANGE_CARDS)
        data = {"seconds": 15, "in_flow": self.flow_status}
        data_model = S2CStartExchangeCards.pb_model(**data)
        await self.inner_broadcast(CmdRoom.START_EXCHANGE_CARDS, data_model)
        self.log_info("开始换三张")
        await self.exchange_three_time_out(15)

    async def exchange_three_time_out(self, seconds):
        pass

    def get_tian_ting_player_count(self):
        count = 0
        for p in self.seats:
            if p.tian_ting:
                count += 1
        return count

    async def __mo_pai(self, choice_seat=None, after_gang=None):
        """
        摸牌
        """
        if self.flow_status == FlowStatus.T_IN_CHECK_OUT:
            self.log_info(self.tid, "桌子已结算，不再摸牌")
            return
        self.clear_table_actions()
        if choice_seat:
            p = self.get_player_by_seat_id(choice_seat)  # 杠后摸牌的玩家
        else:
            p = self.next_player(self.curr_seat_id)
        if self.poker.left_count <= const.LIU_JU_COUNT:  # 黄庄了
            send_command = CmdRoom.PLAYER_MO_PAI
            if after_gang:
                send_command = CmdRoom.AFTER_GANG_MO_CARD
            data = {
                "seat_id": p.seat_id,
                "left_count": 0,
                "card": 0,
                "operates": [],
                "seconds": TimerDelay.CALL_SECONDS,
            }
            data_model = S2CAfterGangMoCard.pb_model(**data)
            await self.inner_send(p, send_command, data_model)
            await self.liu_ju_notify()
            self.log_info("流局")
            self.__win_seat_list = []
            return await self.round_over(OverType.LIU_JU)

        self.set_flow_status(FlowStatus.T_IN_MO_PAI)
        send_command = CmdRoom.PLAYER_MO_PAI
        if after_gang:
            send_command = CmdRoom.AFTER_GANG_MO_CARD
            self.__gang_hou_mo_pai.append(after_gang)
        else:
            self.__gang_hou_mo_pai = []
            p.jian_next_player_card = 0

        self.curr_seat_id = p.seat_id
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

        await self.enter_mo_pai_call()

    async def liu_ju_notify(self):
        """ 通知客户端 流局 兴义麻将 有黄牌查叫数据"""
        cards_info = self.get_player_cards_info()
        cards_model = S2CHuAfterCards.pb_model(cards_info)
        await self.inner_broadcast(CmdRoom.HU_AFTER_CARDS_INFO, cards_model)
        await self.inner_broadcast(CmdRoom.LIU_JU_NOTIFY)

    def check_is_bi_hu(self, operates: list):
        """ 最后三张必胡，有其它操作时 """
        if self.play_type == PlayType.JIAN_LOU_XUE_LIU:
            return False
        if self.poker.left_count < const.XUE_LIU_LEFT_BI_HU and ActionType.ACTION_TYPE_HU in operates:
            return True
        if not self.__have_men_jian_hu:
            if ActionType.ACTION_TYPE_HU in operates or ActionType.ACTION_TYPE_JIAN in operates:
                if self.__gang_hou_chu_pai:
                    return True
        return False

    @staticmethod
    def remove_jmh_from_operates(operates) -> list:
        if ActionType.ACTION_TYPE_JIAN in operates:
            operates.remove(ActionType.ACTION_TYPE_JIAN)
        if ActionType.ACTION_TYPE_MEN in operates:
            operates.remove(ActionType.ACTION_TYPE_MEN)
        if ActionType.ACTION_TYPE_HU in operates:
            operates.remove(ActionType.ACTION_TYPE_HU)
        return operates

    async def enter_mo_pai_call(self):
        self.log_info("进入mo_pai_call")
        if self.flow_status not in (FlowStatus.T_IN_MO_PAI, FlowStatus.T_IN_DEAL_CARDS,
                                    FlowStatus.T_IN_DING_QUE, FlowStatus.T_IN_TIAN_TING,):
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
        curr_player.operates = list(operates)

        if self.play_type in (PlayType.JIAN_LOU_XUE_LIU, PlayType.AN_LONG_XUE_ZHAN):
            data["is_bi_hu"] = 1 if self.check_is_bi_hu(operates) else 0
        if not self.__have_men_jian_hu:
            self.remove_jmh_from_operates(operates)
        data["operates"] = operates
        data["gang_hou_mo_pai"] = 1 if len(self.__gang_hou_mo_pai) > 0 else 0
        data["is_show_bao_ting"] = 0 if curr_player.all_chu_cards else 1
        if can_gang_list:
            data["can_gang_list"] = can_gang_list
        if operates:
            data_model = S2CPublicOperatesMahjong.pb_model(**data)
            await self.inner_send(curr_player, CmdRoom.PUBLIC_OPERATES, data_model)  # 玩家公共操作
        self.__gang_hou_chu_pai = self.__gang_hou_mo_pai
        if curr_player.mo_pai_can_operates():
            self.log_info("mo_pai_call", curr_player.seat_id, "当前玩家可操作", operates)
            data = {"seat_id": curr_player.seat_id, "seconds": seconds, "in_flow": self.flow_status}
            data_model = S2CTurnToMahjong.pb_model(**data)
            await self.inner_broadcast(CmdRoom.TURN_TO, data_model)
            if not self.__decision_sec:
                return
            await self.enter_mo_pai_call_by_robot(curr_player, seconds)
            return
        await self.turn_to_player_chu_pai(curr_player)

    async def enter_mo_pai_call_by_robot(self, curr_player, seconds):
        pass

    def calc_operates_after_mo_pai(self, p: Player):
        """计算摸牌后能做的操作"""
        result = []
        can_gang_list = []
        # 如果庄14能听/胡选择过，则这里不再计算操作
        if p.seat_id == self.dealer_id and not p.all_chu_cards and p.can_tian_ting < 0 and p.tian_ting != 1:
            return result, can_gang_list

        self.check_hu_and_ting(p, result, can_gang_list)

        # 报听或者闷/牌后验证有杠是否能杠(杠后听牌一致才能杠)
        is_zhuan_wan_gang, gang_card = self.zhuan_wan_gang_de_qi(p)  # 提前验证是否能杠
        is_an_gang, gang_card_list = p.can_an_gang(Rule, p.mo_pai)  # 提前验证是否能暗杠
        if p.card_is_lock():
            if is_zhuan_wan_gang:
                if gang_card == p.mo_pai:
                    result.append(ActionType.ACTION_TYPE_ZHUAN_WAN_GANG)

            if is_an_gang:
                valid_gang_cards = [gc for gc in gang_card_list if gc == p.mo_pai]
                allow_hu_map = {HuType.DI_LONG_QI: self.__di_long_qi, HuType.JIN_GOU_DIAO: False,
                                HuType.QI_DUI: True, HuType.FOUR_CARD_NO_NEAR: self.__four_card_no_near,
                                HuType.FOUR_CARD_IS_SAME: self.__four_card_tian_hu}
                for gang_card in valid_gang_cards:
                    temp_cards = [c for c in p.cards if c != gang_card]
                    # 听牌一致的话可以杠
                    ting_list1 = Rule.get_ting_hu_list(p.table_cards, temp_cards, allow_hu_map, self.__lai_zi)
                    if ting_list1 and ting_list1 == p.ting_list:
                        can_gang_list.append(gang_card)
                        len(can_gang_list) == 1 and result.append(ActionType.ACTION_TYPE_AN_GANG)
        else:
            if is_zhuan_wan_gang:
                result.append(ActionType.ACTION_TYPE_ZHUAN_WAN_GANG)
            if is_an_gang:
                result.append(ActionType.ACTION_TYPE_AN_GANG)
        if self.__left_three_bi_hu and self.poker.left_count < const.XUE_LIU_LEFT_BI_HU and ActionType.ACTION_TYPE_HU in result:
            result = [ActionType.ACTION_TYPE_HU]
        if result and (
                ActionType.ACTION_TYPE_HU not in result or self.play_type not in (
        PlayType.JIAN_LOU_XUE_LIU, PlayType.AN_LONG_XUE_ZHAN)):
            result.append(ActionType.ACTION_TYPE_PASS)
        if result and ActionType.ACTION_TYPE_HU in result and not p.men_cards and self.poker.left_count >= const.XUE_LIU_LEFT_BI_HU:
            result.append(ActionType.ACTION_TYPE_PASS)
        required_actions = {ActionType.ACTION_TYPE_PASS, ActionType.ACTION_TYPE_MEN}
        if result and p.tian_ting and required_actions.issubset(result):
            result.remove(ActionType.ACTION_TYPE_PASS)
        return result, can_gang_list

    def check_hu_and_ting(self, p: Player, result, can_gang_list):
        can_hu, hu_info = self.hu_de_qi(p)
        if can_hu:
            result.append(ActionType.ACTION_TYPE_HU)
            result.append(ActionType.ACTION_TYPE_MEN)
            if self.poker.left_count >= const.XUE_LIU_LEFT_BI_HU:
                if len(p.men_cards) == 0:
                    hu_type = hu_info["hu_type"]
                    extra_hu_lst = hu_info.get("extra_hu_type", [])
                    if not p.tui_zhang_ke_kai and (self.__bi_men_yi_shou or self.xiao_hu_bi_men(hu_type, extra_hu_lst)
                                                   or self.bao_ting_bi_men(p, hu_type)) and not self.is_jue_zhang(p):
                        result.remove(ActionType.ACTION_TYPE_HU)
            else:
                if self.__left_three_bi_hu:
                    self.log_info("进入尾三必胡,摸牌")
                    result.remove(ActionType.ACTION_TYPE_MEN)
                    return result, can_gang_list
        # 闲家补牌报听
        if self.__bao_ting and not p.all_chu_cards and p.can_tian_ting > -1 and p.seat_id != self.dealer_id:
            if self.can_select_tian_ting(p, self.deal_cards_count + 1):
                result.append(ActionType.ACTION_TYPE_TIAN_TING)

    @staticmethod
    def can_operates_gang(p: Player):
        """判断是否有人能杠"""
        if p.is_action_in_operates(ActionType.ACTION_TYPE_ZHUAN_WAN_GANG):
            return True
        if p.is_action_in_operates(ActionType.ACTION_TYPE_AN_GANG):
            return True
        if p.is_action_in_operates(ActionType.ACTION_TYPE_AN_GANG):
            return True
        return False

    def xiao_hu_bi_men(self, hu_type, extra_hu_lst):
        if not self.__xiao_pai_bi_men:
            return False
        if hu_type != HuType.PING_HU:
            return False
        if set(extra_hu_lst).intersection(const.SPECIAL_HU_TYPE):
            return False
        return True

    def bao_ting_bi_men(self, p, hu_type) -> bool:
        """ 大牌报听可以开   平胡报听必闷一手 """
        if self.__bao_ting_bi_men:
            if p.tian_ting == 1 and hu_type == HuType.PING_HU:
                return True
        return False

    def set_tui_zhang_ke_kai(self, p: Player):
        if self.__tui_zhang_can_hu:
            p.tui_zhang_ke_kai = 1
            self.log_info("退张可开玩家", p.uid, "座位号", p.seat_id)

    def is_jue_zhang(self, player: Player) -> bool:
        """
        params: cards 手牌
        params: curr_card 当前牌
        当不能直接胡 或者 必密一手时 调用该接口
        判断当前牌是否是绝张
        除了所有玩家手上的牌，和牌堆里的牌 其它都是已知的牌
        从已知牌里遍历，不满足已经知道 3张牌 的略过遍历
        """
        # 未知牌 = 其余玩家手牌 + 牌堆未摸的牌
        unknown_cards = []
        for p in self.seats:
            if p.seat_id == player.seat_id:
                continue
            unknown_cards.extend(p.cards)
            unknown_cards.extend(p.zi_mo_cards)
        unknown_cards.extend(self.poker.remain_cards)

        # 已知牌：所有牌 - (其余玩家手牌 + 牌堆未摸的牌)[未知牌]
        total_cards = list(map(int, self.poker.cards))
        total_counter = Counter(total_cards)
        unknown_counter = Counter(unknown_cards)
        remaining_counter = total_counter - unknown_counter

        curr_card = self.__curr_card
        # 当前牌已知数量不等4
        if remaining_counter[curr_card] != 4:
            return False

        # 点炮情况下
        if player.cards_len % 3 == 2:
            try:
                cards = player.cards.copy()
                cards.remove(curr_card)
            except ValueError:
                return False
        else:
            cards = player.cards.copy()

        suits_hand = self.poker.cal_card_suit_count(cards)
        for card, count in unknown_counter.items():  # 遍历未知牌里面是否还有可胡的牌
            if not suits_hand.get(self.poker.get_suit(card)):  # 没有的花色就不算了
                continue
            # 还有其它牌能胡则不是绝张
            allow_hu_map = {HuType.DI_LONG_QI: self.__di_long_qi, HuType.JIN_GOU_DIAO: True,
                            HuType.QI_DUI: True, HuType.FOUR_CARD_NO_NEAR: self.__four_card_no_near,
                            HuType.FOUR_CARD_IS_SAME: self.__four_card_tian_hu}
            hu_type, _ = Rule.can_hu(
                player.table_cards, cards + [card], curr_card, allow_hu_map)
            if hu_type:
                return False
        self.log_info("是绝张", curr_card, "玩家", player.seat_id)
        return True

    def zhuan_wan_gang_de_qi(self, p: Player):
        if self.curr_seat_id != p.seat_id:
            return False
        return p.can_zhuan_wan_gang(Rule)

    def ming_gang_de_qi(self, p: Player, card):
        if self.curr_seat_id == p.seat_id:
            return False, card
        return p.can_ming_gang(Rule, card)

    async def turn_to_player_chu_pai(self, p: Player, after_peng=False, timeout_seconds=TimerDelay.CHU_PAI_TIME):
        contains_tian_ting = any(
            action[0] == p.seat_id and action[1] == ActionType.ACTION_TYPE_TIAN_TING
            for action in self.__player_actions
        )
        if contains_tian_ting:
            self.remove_player_action(tian_ting=True)
        if contains_tian_ting and ActionType.ACTION_TYPE_MEN in p.operates:
            self.log_info("天听后可以闷")
        else:
            self.clear_table_actions()
        self.__curr_card = p.mo_pai  # 因为存在炸胡，在玩家出牌阶段玩家也可点击胡，所以保存当前牌

        if after_peng:
            self.__after_peng = after_peng
        self.log_info("轮到玩家出牌: ", p.uid, "手牌", p.cards, p.tian_ting, contains_tian_ting)
        self.curr_seat_id = p.seat_id

        seconds = TimerDelay.CALL_SECONDS
        self.set_flow_status(FlowStatus.T_IN_CHU_PAI)
        data = {"seat_id": p.seat_id, "seconds": seconds, "in_flow": self.flow_status}
        data_model = S2CTurnToMahjong.pb_model(**data)
        await self.inner_broadcast(CmdRoom.TURN_TO, data_model, exclude_uid=p.uid)
        if p.card_is_lock():
            # data["lock_cards"] = p.lock_cards
            # data_model = S2CTurnToMahjong.pb_model(**data)
            data_model.lock_cards.extend(p.lock_cards or [])
            await self.inner_send(p, CmdRoom.TURN_TO, data_model)

            if self.__have_men_jian_hu and (
                    p.all_chu_cards or p.cards_len == 5 or not contains_tian_ting or p.is_robot):
                return self.call_flow(0.5, self.robot_play_card_by_suo_pai, p)
        else:
            await self.inner_send(p, CmdRoom.TURN_TO, data_model)
        if self.__decision_sec:
            await self.turn_to_chu_pai_by_robot(p, timeout_seconds)

    async def turn_to_chu_pai_by_robot(self, p, timeout_seconds):
        pass

    def clear_table_actions(self, beside_seat_id=-1):
        self.__player_actions = []
        self.clear_operates(beside_seat_id)
        self.__curr_card = 0
        self.__curr_action_player = None
        self.__jie_pao_count = -1
        self.__is_yi_pao_duo_xiang = 0
        self.__after_peng = False
        self.__record_operates = {}
        self.__zha_jian_seats = set()

    def clear_operates(self, beside_seat_id=-1):
        for p in self.seats:
            if not p:
                continue
            if p.seat_id == beside_seat_id:
                continue
            p.operates = []

    async def robot_play_card_by_suo_pai(self, p):
        """ 机器人锁牌后的打牌 """
        out_cards = p.get_out_not_lock_card()
        self.log_info("机器人锁牌后的打牌", "seat_id", p.seat_id, "out_cards", out_cards)
        if len(out_cards) == 0:
            return
        gang_model.card = out_cards[0]  # 设置 card 值
        serialized_data = gang_model.SerializeToString()
        code, _ = await self.on_player_chu_pai(p, serialized_data)
        if code == StaCode.PASS:
            return await self.enter_chu_pai_call()

    async def enter_chu_pai_call(self):
        self.log_info("进入chu_pai_call")
        if self.room_status not in (RoomStatus.T_PLAYING, RoomStatus.T_DISMISS):
            return
        if self.flow_status not in [FlowStatus.T_IN_CHU_PAI, FlowStatus.T_IN_DI_HU_CHU_PAI,
                                    FlowStatus.T_IN_MO_PAI_CALL]:
            return

        self.set_flow_status(FlowStatus.T_IN_PUBLIC_OPRATE)
        self.__player_actions = []  # 防止两个玩家，一个过、另个一碰后可杠同时触发导致过的玩家操作没有清除
        chu_pai_player = self.curr_player()
        chu_pai_player.operates = []
        self.log_info("玩家", chu_pai_player.seat_id, "出牌", self.__curr_card)
        jie_pao_count = 0
        can_hu_or_jian = 0
        can_peng_or_gang = 0
        seconds = TimerDelay.CHU_PAI_AFTER_WAIT_TIME
        data = {
            "seat_id": self.curr_seat_id,
            "seconds": seconds,
            "left_count": self.poker.left_count,
            "in_flow": self.flow_status,
        }
        for p in self.seats:
            if p.seat_id == self.curr_seat_id:
                continue
            operates = self.calc_operates_after_chu_pai(p)
            p.operates = operates
            data["is_bi_hu"] = 1 if self.check_is_bi_hu(p.operates) else 0
            if ActionType.ACTION_TYPE_JIAN in operates or ActionType.ACTION_TYPE_HU in operates:
                can_hu_or_jian = p.seat_id
            elif ActionType.ACTION_TYPE_PENG in operates or ActionType.ACTION_TYPE_MING_GANG in operates:
                can_peng_or_gang = p.seat_id
            if ActionType.ACTION_TYPE_HU in p.operates:
                jie_pao_count += 1
            elif ActionType.ACTION_TYPE_JIAN in p.operates:
                jie_pao_count += 1
            if not self.__have_men_jian_hu:
                operates = self.remove_jmh_from_operates(p.operates)
            else:
                operates = p.operates  # 提示密捡开
            data["operates"] = operates
            if self.play_type in (PlayType.JIAN_LOU_XUE_LIU, PlayType.AN_LONG_XUE_ZHAN):
                if can_hu_or_jian and can_peng_or_gang:
                    # data["operates"].append(ActionType.ACTION_TYPE_PASS)
                    p.add_operates(ActionType.ACTION_TYPE_PASS)
                elif ActionType.ACTION_TYPE_PASS in self.__record_operates.get(p.seat_id, []):
                    if ActionType.ACTION_TYPE_PASS not in operates:
                        operates.append(ActionType.ACTION_TYPE_PASS)
            if operates:
                data_model = S2CPublicOperatesMahjong.pb_model(**data)
                await self.inner_send(p, CmdRoom.PUBLIC_OPERATES, data_model)

        if jie_pao_count > 1:
            self.__jie_pao_count = jie_pao_count

        if self.can_operates():
            self.log_info("进入chu_pai_call 有玩家可以操作")
            if not self.__decision_sec:
                return
            await self.deal_operates_call_time_out()
            return
        if self.__have_men_jian_hu:
            await self.everyone_pass()

    async def deal_operates_call_time_out(self):
        pass

    async def deal_first_ji(self, curr_p: Player):
        """
        处理冲锋鸡handle
        冲锋幺鸡
        冲锋乌骨鸡
        """
        if self.flow_status != FlowStatus.T_IN_PUBLIC_OPRATE:
            self.log_info(self.tid, "冲锋鸡必须是成功打牌后")
            return
        if self.__curr_card == CardsType.YAO_JI and self.__round_first_ji == 0:
            self.__round_first_ji = 1
            self.__chong_feng_ji_seat_id = self.curr_seat_id
            curr_p.chong_feng_ji = 1
            await self.send_first_ji_info("冲锋鸡玩家成功")

        if self.__wu_gu_ji and self.__curr_card == CardsType.WU_GU_JI and self.__round_first_wgj == 0:
            self.__round_first_wgj = 1
            self.__cfwgj_seat_id = self.curr_seat_id
            curr_p.chong_feng_wgj = 1
            await self.send_first_ji_info("乌骨冲锋鸡玩家成功")

    async def send_first_ji_info(self, desc):
        self.log_info(desc, self.curr_seat_id)
        data = {"first_ji_seat_id": self.curr_seat_id, "first_ji_card": self.__curr_card}
        data_model = S2CFirstJiMahjong.pb_model(**data)
        await self.inner_broadcast(CmdRoom.CONFIRM_CHONG_FENG_JI, data_model)

    async def check_action_end(self):
        await self.service.conf.locker.locked(self.tid, self.lock_action_end)

    async def lock_action_end(self):
        operate_list = {}  # {动作: [seat_id, ...]}
        for item in self.__player_actions:
            if item[1] in const.ACTION_PRIORITY:
                operate_list.setdefault(item[1], []).append(item[0])
        if len(operate_list) == 0:
            return
        is_finish, max_operate_list = self.__is_player_actions_finish(operate_list)
        if max_operate_list[0] == ActionType.ACTION_TYPE_HU and self.flow_status != FlowStatus.T_IN_FOUR_BAO_TING:
            operate_list = self.get_operate_player_max_operate()  # {seat_id1: priority or 0, ...}
            # [seat_id1, ]
            hu_list = [seat_id for seat_id, action in operate_list.items() if action == ActionType.ACTION_TYPE_HU]
            return await self.somebody_hu(hu_list)
        if not is_finish:
            return

        # 下面主要是处理有操作且操作过的玩家
        action_map = {
            ActionType.ACTION_TYPE_HU: self.somebody_hu,
            ActionType.ACTION_TYPE_MEN: self.somebody_men,
            ActionType.ACTION_TYPE_JIAN: self.somebody_jian,
            ActionType.ACTION_TYPE_PENG: self.somebody_peng,
            ActionType.ACTION_TYPE_ZHUAN_WAN_GANG: self.somebody_zhuan_wan_gang,
            ActionType.ACTION_TYPE_MING_GANG: self.somebody_ming_gang,
            ActionType.ACTION_TYPE_AN_GANG: self.somebody_an_gang,

            ActionType.ACTION_TYPE_ZHA_JIAN: self.somebody_zha_jian,
            ActionType.ACTION_TYPE_ZHA_MEN: self.somebody_zha_men,
            ActionType.ACTION_TYPE_ZHA_HU: self.somebody_zha_hu,
        }

        act = max_operate_list[0]
        self.log_info("somebody " + str(act))
        if act in action_map and max_operate_list[1]:
            hu_list = list(set(max_operate_list[1]))
            result = await action_map[act](hu_list)
            return result

        self.log_info(self.tid, "every pass", self.__record_operates)
        if not self.__record_operates:
            return await self.everyone_pass()

    async def everyone_pass(self):
        if self.flow_status == FlowStatus.T_IN_CHECK_OUT:
            self.log_info("结算中，不处理操作")
            return
        p = self.curr_player()
        self.__chong_feng_ji and await self.deal_first_ji(p)
        self.log_info("进入everyone_pass flow_status", self.flow_status,"seat_id", p.seat_id)
        if self.flow_status == FlowStatus.T_IN_CHU_PAI:
            self.log_info(p.uid, p.seat_id, "everyone_pass flow error")
            return
        if self.flow_status == FlowStatus.T_IN_MO_PAI_CALL:  # 偎胡则不检查，提胡要检查八皮
            return await self.turn_to_player_chu_pai(p)
        elif self.flow_status == FlowStatus.T_IN_ZHUAN_WAN_GANG_PAI_CALL:
            return await self.do_zhuan_wan_gang_end()
        elif self.flow_status == FlowStatus.T_IN_TIAN_HU:
            return await self.turn_to_player_chu_pai(p)
        elif self.flow_status in (FlowStatus.T_IN_TIAN_TING, FlowStatus.T_IN_FOUR_BAO_TING):
            return await self.check_tian_ting_end()
        elif self.flow_status == FlowStatus.T_IN_EIGHT_TIAN_HU:
            return await self.operate_after_men_in_eight_tian_hu(p)

        return self.call_flow(0, self.__mo_pai)
        # return await self.__mo_pai()  # 继续摸牌

    async def check_tian_ting_end(self):
        for p in self.seats:
            if p.can_tian_ting != -1 and ActionType.ACTION_TYPE_TIAN_TING in p.operates:
                return
        if self.__four_card_bao_ting and self.flow_status == FlowStatus.T_IN_FOUR_BAO_TING:
            if self.__eight_card_tian_hu:
                return await self.start_eight_cards_tian_hu()
            return await self.deal_bu_pai(self.__four_card_bao_ting)

        if self.__men_in_tian_ting:
            self.log_info(self.tid, "天听完，有玩家在该阶段密，进入摸牌")
            await self.__mo_pai()
        else:
            await self.enter_mo_pai_call()

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

        # 还未操作的玩家最大操作大于已经操作的玩家最大操作(需要等待)
        if priority > self.get_action_priority(already_max_info[0]):
            return False, already_max_info

        return True, already_max_info

    async def somebody_hu(self, seat_list: list) -> bool:
        self.__curr_card_exist = 0
        await self.hu_da_notify(seat_list)
        self.__winner_list = [self.get_player_by_seat_id(seat) for seat in seat_list]
        self.__win_seat_list = seat_list
        await self.round_over(OverType.HU_KAI)
        return True

    async def somebody_men(self, seat_list: list):  # 三人均操作后判断有没有人胡牌
        self.__curr_card_exist = 0
        await self.men_da_notify(seat_list)
        seat_id = seat_list[0]
        p = self.get_player_by_seat_id(seat_id)
        p.set_lock_cards([])
        p.can_tian_ting = -1
        allow_hu_map = {HuType.DI_LONG_QI: self.__di_long_qi, HuType.JIN_GOU_DIAO: False,
                        HuType.QI_DUI: True, HuType.FOUR_CARD_NO_NEAR: self.__four_card_no_near,
                        HuType.FOUR_CARD_IS_SAME: self.__four_card_tian_hu}
        if len(p.ting_list) == 0:
            ting_list = Rule.get_ting_hu_list(p.table_cards, p.cards, allow_hu_map, self.__lai_zi)
            p.ting_list = ting_list

        if self.flow_status == FlowStatus.T_IN_TIAN_TING:
            self.__men_in_tian_ting = True
            self.operate_after_men_in_tian_ting(p)
        elif self.flow_status == FlowStatus.T_IN_EIGHT_TIAN_HU:
            await self.operate_after_men_in_eight_tian_hu(p)
        else:
            self.call_flow(1, self.__mo_pai)

    async def somebody_jian(self, seat_list: list):  # 三人均操作后判断有没有人胡牌
        """
        炸捡与捡都走这个逻辑，同时捡
        """
        self.__curr_card_exist = 0
        await self.jian_da_notify(seat_list)
        allow_hu_map = {HuType.DI_LONG_QI: self.__di_long_qi, HuType.JIN_GOU_DIAO: False,
                        HuType.QI_DUI: True, HuType.FOUR_CARD_NO_NEAR: self.__four_card_no_near,
                        HuType.FOUR_CARD_IS_SAME: self.__four_card_tian_hu}
        # 捡完 锁定牌组 自动出牌
        for seat_id in seat_list:
            p = self.get_player_by_seat_id(seat_id)
            p.set_lock_cards([])
            p.can_tian_ting = -1
            if len(p.ting_list) == 0:
                ting_list = Rule.get_ting_hu_list(p.table_cards, p.cards, allow_hu_map, self.__lai_zi)
                p.ting_list = ting_list

        if self.__jie_pao_count != 2 or len(seat_list) == 2:
            self.deal_dian_pao(True)
            self.call_flow(1, self.__mo_pai)

        if self.__jie_pao_count > 1:
            self.__is_yi_pao_duo_xiang = 1
            self.__jie_pao_count -= 1

    async def somebody_peng(self, peng_list: list) -> bool:  # 三人均操作后判断有没有人碰牌
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

            res, seat_id = self.__ze_ren_ji and self.deal_ze_ren_ji(p)
            if res:
                data["ze_ren_ji"] = seat_id

            data_model = S2CGangInfo.pb_model(**data)
            await self.inner_broadcast(CmdRoom.PLAYER_PENG, data_model)

            await self.check_can_gang_after_peng(p)

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
        is_zhuan_wan_gang, card = p.can_zhuan_wan_gang(Rule, card)
        if not is_zhuan_wan_gang:
            raise TypeError("xxxxxxxxxxxxxx")

        # 如果不是摸到就杠 是不算分的
        if self.flow_status == FlowStatus.T_IN_MO_PAI_CALL and self.curr_player().mo_pai == card:
            self.__curr_card_exist = 0
        await self.enter_zhuan_wan_gang_call(p, card)
        return True

    async def somebody_ming_gang(self, gang_list: list) -> bool:
        if len(gang_list) != 1:
            return False

        p = self.get_player_by_seat_id(gang_list[0])
        if not p:
            return False
        # is_ming_gang, card = p.can_ming_gang(self.__rule, self.__curr_card)
        from_p = self.get_player_by_seat_id(self.curr_seat_id)
        from_p.add_dian_gang_count()  # 点杠一次
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
            res = self.__ze_ren_ji and self.deal_ze_ren_ji(p)
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

        is_an_gang, card = p.can_an_gang(Rule, card)  # 判断能不能杠
        card = card[0]
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
            if card != p.mo_pai and (p.chu_cards or len(p.all_chu_cards) % 4 != 0):
                self.log_info(self.tid, p.uid, p.seat_id, "憨包杠", card)
                p.add_han_bao_dou_an_gang_count(card)
                data["han_bao_dou"] = 1

            data["card"] = card

            data_model = S2CGangInfo.pb_model(**data)
            await self.inner_broadcast(CmdRoom.PLAYER_GANG, data_model)

            self.log_info(self.tid, "somebody_an_gang end1")

            if self.flow_status == FlowStatus.T_IN_TIAN_TING:
                self.log_info(self.tid, p.uid, p.seat_id, "报听中选择暗杠")
                self.remove_target_player_act(p.seat_id, ActionType.ACTION_TYPE_AN_GANG)
                # 先补牌
                await self.an_gang_bu_pai_in_tian_ting(p, card)
                await self.check_tian_ting_enter_next()
            else:
                await self.__mo_pai(p.seat_id, [ActionType.ACTION_TYPE_AN_GANG, card])

            return True

        self.log_info(self.tid, "somebody_an_gang end2")
        return False

    async def somebody_zha_jian(self, hu_list: list):
        """ 炸捡按平胡计算 """
        self.__curr_card_exist = 0
        await self.zha_jian_notify(hu_list)
        # 捡完 锁定牌组 自动出牌
        allow_hu_map = {HuType.DI_LONG_QI: False, HuType.JIN_GOU_DIAO: False,
                        HuType.QI_DUI: True, HuType.FOUR_CARD_NO_NEAR: self.__four_card_no_near}
        for seat_id in hu_list:
            p = self.get_player_by_seat_id(seat_id)
            self.log_info(self.tid, p.uid, "选择炸捡")
            p.set_lock_cards([])
            p.can_tian_ting = -1
            if len(p.ting_list) == 0:
                ting_list = Rule.get_ting_hu_list(p.table_cards, p.cards, allow_hu_map, self.__lai_zi)
                p.ting_list = ting_list

        self.call_flow(1, self.__mo_pai)

    async def somebody_zha_men(self, hu_list: list):
        self.log_info(self.tid, hu_list, "选择炸闷")
        self.__curr_card_exist = 0
        # 炸闷按平胡算
        await self.zha_men_notify(hu_list)
        seat_id = hu_list[0]
        p = self.get_player_by_seat_id(seat_id)
        p.set_lock_cards([])
        p.can_tian_ting = -1
        allow_hu_map = {HuType.DI_LONG_QI: False, HuType.JIN_GOU_DIAO: False,
                        HuType.QI_DUI: True, HuType.FOUR_CARD_NO_NEAR: self.__four_card_no_near}
        if len(p.ting_list) == 0:
            ting_list = Rule.get_ting_hu_list(p.table_cards, p.cards, allow_hu_map, self.__lai_zi)
            p.ting_list = ting_list
        self.call_flow(1, self.__mo_pai)

    async def somebody_zha_hu(self, hu_list: list) -> bool:
        self.log_info(self.tid, hu_list, "选择炸胡")
        self.__curr_card_exist = 0
        await self.zha_hu_da_notify(hu_list)
        self.__winner_list = [self.get_player_by_seat_id(seat) for seat in hu_list]
        self.__win_seat_list = hu_list
        await self.round_over(OverType.ZHA_HU_KAI)
        return True

    async def zha_hu_da_notify(self, hu_list):
        """ 开牌结算 """
        self.log_info(self.tid, "zha_hu_da_notify", hu_list)
        data = []
        is_zi_mo = False
        for win_seat in hu_list:
            winner = self.get_player_by_seat_id(win_seat)
            is_zi_mo = win_seat == self.curr_seat_id
            if not is_zi_mo:
                self.remove_jian_or_hu(win_seat)

            hu_info, _, _ = self.get_zha_hu_type(winner)
            winner.set_hu_info(hu_info)
            check_type = CheckType.CHECK_HU_ZI_MO_ZHA if is_zi_mo else CheckType.CHECK_HU_DIAN_PAO_ZHA
            hu_info["check_type"] = check_type
            self.__kai_pai_hu_info.append(hu_info)
            winner.hu_type = hu_info.get("hu_type", 0)
            data.append({
                "is_zha_hu": 1,
                "seat_id": winner.seat_id,
                "curr_seat_id": self.curr_seat_id,
                "curr_card": self.__curr_card,
                "is_finish": 1,
                "is_zi_mo": is_zi_mo,
                "hu_type": winner.hu_type,
                "extra_hu_type": hu_info.get("extra_hu_type", []),
                "winner_hand_cards": winner.cards,
            })
            if not is_zi_mo:
                self.curr_player().fang_pao = 1

        if not is_zi_mo:
            # 当前玩家打的当前牌从出牌中删除
            self.deal_dian_pao(False, "炸胡")
        data_model = S2CHuInfoMahjong.pb_model(data)
        await self.inner_broadcast(CmdRoom.PLAYER_HU, data_model)

        cards_info = self.get_player_cards_info(hu_list, is_zi_mo)
        cards_model = S2CHuAfterCards.pb_model(cards_info)
        await self.inner_broadcast(CmdRoom.HU_AFTER_CARDS_INFO, cards_model)

        self.log_info(self.tid, "zha_hu_da_notify end")

    async def zha_men_notify(self, hu_list):
        for seat_id in hu_list:
            p = self.get_player_by_seat_id(seat_id)
            hu_info, _, _ = self.get_zha_hu_type(p)

            data = self.deal_men_jian_data(p, 0, hu_info, CheckType.CHECK_MEN_ZHA)
            p.add_men_cards(data, is_zha=True)
            self.__men_record.append(data)
            data_model = S2CMenInfoMahjong.pb_model(**data)
            await self.inner_send(p, CmdRoom.PLAYER_MEN_SUC, data_model)
            if self.flow_status == FlowStatus.T_IN_EIGHT_TIAN_HU:
                is_zi_mo = True
            else:
                is_zi_mo = p.seat_id == self.curr_seat_id
            data_broadcast = {
                "seat_id": p.seat_id,
                "curr_seat_id": self.curr_seat_id,
                "is_zi_mo": is_zi_mo,
                "extra_hu_type": data.get("extra_hu_type") or [],
            }
            data_broadcast_model = S2CMenInfoMahjong.pb_model(**data_broadcast)
            await self.inner_broadcast(CmdRoom.PLAYER_MEN_SUC, data_broadcast_model, exclude_uid=p.uid)

        self.log_info(self.tid, "zha_men_notify end", hu_list)

    async def zha_jian_notify(self, hu_list):
        """ 胡牌通知客户端 """
        for seat_id in hu_list:
            self.remove_jian_or_hu(seat_id)
            p = self.get_player_by_seat_id(seat_id)
            hu_info, _, _ = self.get_zha_hu_type(p)

            extra_hu_lst = hu_info["extra_hu_type"]
            base_score = self.get_base_score(hu_info, extra_hu_lst)
            extra_score = self.cal_extra_hu_score(hu_info, extra_hu_lst)
            data = self.deal_men_jian_data(p, base_score + extra_score, hu_info, CheckType.CHECK_JIAN_ZHA)
            p.add_jian_cards(data, is_zha=True)
            self.__men_record.append(data)

            other_data = {
                "fang_pao_seat_id": data.get("fang_pao_seat_id"),
                "seat_id": p.seat_id,
                "curr_seat_id": self.curr_seat_id,
                "curr_card": self.__curr_card,
                "is_zi_mo": False,
                "extra_hu_type": data.get("extra_hu_type") or [],
            }
            other_model = S2CMenInfoMahjong.pb_model(**other_data)
            await self.inner_broadcast(CmdRoom.PLAYER_JIAN_SUC, other_model)

        # 当前玩家打的当前牌从出牌中删除
        self.deal_dian_pao(False, "炸捡")

        self.log_info(self.tid, "zha_jian_notify end")

    def remove_target_player_act(self, seat_id, target_act):
        """ 移除玩家已经做过的操作 """
        for i, item in enumerate(self.__player_actions):
            if item[0] != seat_id:
                continue
            act = item[1]
            if act == target_act:
                self.__player_actions.pop(i)
            p = self.get_player_by_seat_id(seat_id)
            p.operates = []  # 这里不清除会导致进入超时中把玩家当做炸胡
            self.log_info(self.tid, seat_id, "remove_target_player_act", self.__player_actions)

    async def an_gang_bu_pai_in_tian_ting(self, p, card):
        """ 天听中玩家杠后补牌 """
        self.curr_seat_id = p.seat_id
        mo_pai = self.poker.pop()
        p.rev_card(mo_pai)
        p.mo_pai = mo_pai
        self.__gang_hou_mo_pai.append([ActionType.ACTION_TYPE_AN_GANG, card])
        self.log_info(self.tid, p.uid, "杠后摸牌", self.__gang_hou_mo_pai)
        for player in self.seats:
            data = {
                "seat_id": p.seat_id,
                "left_count": self.poker.left_count,
                "seconds": TimerDelay.CALL_SECONDS,
            }
            if player.uid == p.uid:
                data["card"] = p.mo_pai
            data_model = S2CAfterGangMoCard.pb_model(**data)
            await self.inner_send(player, CmdRoom.AFTER_GANG_MO_CARD, data_model)

    async def enter_ming_gang_call(self, curr_player, card):

        if self.flow_status not in (
                FlowStatus.T_IN_PUBLIC_OPRATE, FlowStatus.T_IN_MO_PAI_CALL, FlowStatus.T_IN_TIAN_HU):
            return
        self.set_flow_status(FlowStatus.T_IN_MING_GANG_PAI_CALL)
        self.clear_table_actions()
        self.__curr_card = card
        self.__curr_action_player = curr_player

        # 明杠如果有人能胡优先胡不会进入此流程，所以不需要考虑抢杠胡，抢杠胡只限于转弯杠
        await self.__mo_pai(curr_player.seat_id, [ActionType.ACTION_TYPE_MING_GANG, card])

    async def enter_zhuan_wan_gang_call(self, curr_player, card):
        """
        :return:
        """
        if self.flow_status != FlowStatus.T_IN_MO_PAI_CALL:
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
                "is_bi_hu": 1 if self.__have_men_jian_hu and ActionType.ACTION_TYPE_HU in operates else 0,
                "in_flow": self.flow_status,
            }
            if operates:
                opt_model = S2CPublicOperatesMahjong.pb_model(**data)
                self.log_info("有玩家可以抢杠胡", p.seat_id, operates, "is_bi_hu", data["is_bi_hu"])
                await self.inner_send(p, CmdRoom.PUBLIC_OPERATES, opt_model)

        if self.can_somebody_hu():  # 有人可以胡，则需要等待
            if not self.__decision_sec:
                return
            await self.deal_operates_call_time_out()
            return
        await self.do_zhuan_wan_gang_end()

    async def deal_chu_pai_call_time_out(self):
        pass

    async def do_zhuan_wan_gang_end(self):
        curr_player = self.__curr_action_player
        self.__gang_hou_mo_pai = []  # 有人转弯杠则连续杠被打断
        # 玩家 do 转弯杠
        curr_player.zhuan_wan_gang(self.__curr_card)

        if self.__curr_card != curr_player.mo_pai:  # 摸了就出才有分，
            curr_player.add_han_bao_dou_zhuan_wan_gang_count(self.__curr_card)

        await self.__mo_pai(curr_player.seat_id, [ActionType.ACTION_TYPE_ZHUAN_WAN_GANG, self.__curr_card])

    def calc_operates_after_zhuan_wan_gang(self, p: Player):
        """ 抢杠胡必胡 """
        result = []
        can_hu, _ = self.hu_de_qi(p)
        if can_hu:
            result.append(ActionType.ACTION_TYPE_HU)
            if self.play_type not in (PlayType.JIAN_LOU_XUE_LIU, PlayType.AN_LONG_XUE_ZHAN):
                result.append(ActionType.ACTION_TYPE_PASS)
            else:
                result.append(ActionType.ACTION_TYPE_JIAN)
        return result

    def can_somebody_hu(self):
        for p in self.seats:
            if p.is_action_in_operates(ActionType.ACTION_TYPE_HU):
                return True
        return False

    async def check_can_gang_after_peng(self, p):
        """ 检测玩家碰后是否能杠 """
        operates, gang_card_list = self.get_operates_after_peng(p)
        if operates:
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
            return

        await self.turn_to_player_chu_pai(p, after_peng=True)

    def get_operates_after_peng(self, p: Player):
        can_an_gang, gang_card_list = p.can_an_gang(Rule)
        can_zwg, gang_card = p.can_zhuan_wan_gang(Rule)
        operates = []
        if can_zwg:
            operates.append(ActionType.ACTION_TYPE_ZHUAN_WAN_GANG)
        if can_an_gang:
            operates.append(ActionType.ACTION_TYPE_AN_GANG)
        if operates and (
                ActionType.ACTION_TYPE_HU not in operates or self.play_type not in (
        PlayType.JIAN_LOU_XUE_LIU, PlayType.AN_LONG_XUE_ZHAN)):
            operates.append(ActionType.ACTION_TYPE_PASS)
        return operates, gang_card_list

    def deal_ze_ren_ji(self, p):
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
            self.log_info("玩家", curr_p.seat_id, "责任幺鸡")
            return 1, self.__ze_ren_ji_seat_id

        if self.__wu_gu_ji and self.__curr_card == CardsType.WU_GU_JI and self.__round_first_wgj == 0:
            self.__ze_ren_wgj_seat_id = self.curr_seat_id
            self.__ze_ren_wgj_win_seat_id = p.seat_id
            if self.__cfwgj_seat_id > 0:
                cfwgj_player = self.get_player_by_seat_id(self.__cfwgj_seat_id)
                cfwgj_player.chong_feng_wgj = 0
                self.__cfwgj_seat_id = 0

            curr_p = self.curr_player()
            curr_p.ze_ren_wgj = 1
            self.log_info("玩家", curr_p.seat_id, "责任乌骨鸡")
            self.__round_first_wgj = 1
            return 1, self.__ze_ren_wgj_seat_id
        return 0, 0

    def operate_after_men_in_tian_ting(self, player):
        player.operates = []
        self.__player_actions = []
        for p in self.seats:
            if p.can_tian_ting != -1 and ActionType.ACTION_TYPE_TIAN_TING in p.operates:
                return
        self.__mo_pai()

    async def operate_after_men_in_eight_tian_hu(self, player):
        player.operates = []
        self.__player_actions = []
        all_tian_hu = True
        for p in self.seats:
            if not len(p.men_cards) > 0:
                all_tian_hu = False
            if ActionType.ACTION_TYPE_HU in p.operates:
                return
        if all_tian_hu:
            await self.__mo_pai()
        else:
            await self.deal_bu_pai(self.__eight_card_tian_hu)

    async def men_da_notify(self, hu_list):
        """ 胡牌通知客户端 """
        for seat_id in hu_list:
            p = self.get_player_by_seat_id(seat_id)
            hu_info, _, _ = self.get_hu_type(p)

            data = self.deal_men_jian_data(p, 0, hu_info)
            p.add_men_cards(data)
            self.__men_record.append(data)
            data_model = S2CMenInfoMahjong.pb_model(**data)
            await self.inner_send(p, CmdRoom.PLAYER_MEN_SUC, data_model)
            if self.flow_status == FlowStatus.T_IN_EIGHT_TIAN_HU:
                is_zi_mo = True
            else:
                is_zi_mo = p.seat_id == self.curr_seat_id
            other_data = {
                "seat_id": p.seat_id,
                "curr_seat_id": self.curr_seat_id,
                "is_zi_mo": is_zi_mo,
                "extra_hu_type": data.get("extra_hu_type") or [],
            }
            other_model = S2CMenInfoMahjong.pb_model(**other_data)
            await self.inner_broadcast(CmdRoom.PLAYER_MEN_SUC, other_model, exclude_uid=p.uid)

    async def jian_da_notify(self, hu_list):
        """
        胡牌通知客户端
        此处算好分，后续不再算
        """
        hu_list_len = len(hu_list)
        for seat_id in hu_list:
            self.remove_jian_or_hu(seat_id)
            p = self.get_player_by_seat_id(seat_id)
            if seat_id in self.__zha_jian_seats:
                hu_info, _, _ = self.get_zha_hu_type(p)
                check_type = CheckType.CHECK_JIAN_ZHA
                is_zha = True
            else:
                hu_info, _, _ = self.get_hu_type(p, dian_pao=True)
                check_type = CheckType.CHECK_JIAN
                is_zha = False

            extra_hu_lst = hu_info["extra_hu_type"]  # 额外番
            base_score = self.get_base_score(hu_info, extra_hu_lst)
            extra_score = self.cal_extra_hu_score(hu_info, extra_hu_lst)

            data = self.deal_men_jian_data(p, base_score + extra_score, hu_info, check_type)

            p.add_jian_cards(data, is_zha)
            self.__men_record.append(data)
            other_data = {
                "fang_pao_seat_id": data.get("fang_pao_seat_id"),
                "seat_id": p.seat_id,
                "curr_seat_id": self.curr_seat_id,
                "curr_card": self.__curr_card,
                "is_zi_mo": False,
                "extra_hu_type": data.get("extra_hu_type") or [],
            }

            if self.__is_yi_pao_duo_xiang or hu_list_len > 1:
                other_data["is_yi_pao_duo_xiang"] = 1

            if ExtraHuPai.QIANG_GANG_HU in extra_hu_lst:
                curr_p = self.curr_player()
                if self.__curr_card in curr_p.cards:
                    curr_p.rm_cards([self.__curr_card])
                    self.log_info(self.tid, p.uid, "抢杠胡玩家捡", curr_p.cards, self.__curr_card)
            other_model = S2CMenInfoMahjong.pb_model(**other_data)
            await self.inner_broadcast(CmdRoom.PLAYER_JIAN_SUC, other_model)

    def get_zha_hu_type(self, p, is_over=False):
        """
        此接口计算玩家 听牌类型 + 额外得分(如天胡、杀报、抢杠等)
        """
        # 1.额外分(与牌型无关, 天胡|地胡|天听|杀报|杠上花|抢杠胡|杠上炮)
        extra_fan = []
        is_zi_mo = self.curr_seat_id == p.seat_id
        if self.flow_status == FlowStatus.T_IN_EIGHT_TIAN_HU:
            is_zi_mo = True
        is_sha_bao = False
        bei_sha_bao_seats = []  # 被杀报者需要记录，因为如果是自摸，可能有一个可能有多个
        re_pao_score = 0  # 记录热炮分(杠上炮分后续不好计算，此处算好后面直接用)
        qiang_gang_score = 0  # 记录抢杠分(抢杠分后续不好计算，此处算好后面直接用)
        gang_card = []  # 记录抢杠|杠上炮时的杠，如果是默认鸡后续算分时需要+鸡的分
        if is_zi_mo:
            if len(self.__gang_hou_mo_pai) > 0:  # 杠后摸牌
                extra_fan.append(ExtraHuPai.GANG_SHANG_HUA)

            if (
                    p.seat_id == self.dealer_id or self.flow_status == FlowStatus.T_IN_EIGHT_TIAN_HU) and not p.all_chu_cards and not p.men_cards:
                if p.tian_ting != 1:
                    extra_fan.append(ExtraHuPai.TIAN_HU)  # 天胡(选择报听后则不能算天胡)
                p.tian_hu = 1
                if self.flow_status == FlowStatus.T_IN_EIGHT_TIAN_HU:
                    p.eight_card_tian_hu = 1
                p.tian_ting = 1

            for other_p in self.seats:
                if p.seat_id == other_p.seat_id:
                    continue
                if other_p.tian_ting > 0:
                    is_sha_bao = True  # 杀报
                    bei_sha_bao_seats.append(other_p.seat_id)
        else:
            if self.flow_status_is_equal(FlowStatus.T_IN_ZHUAN_WAN_GANG_PAI_CALL):
                gang = ActionType.ACTION_TYPE_ZHUAN_WAN_GANG
                gang_card = [[gang, self.__curr_card]]
                qiang_gang_score += self.cal_score_by_gang_shang_pao(gang)
                extra_fan.append(ExtraHuPai.QIANG_GANG_HU)  # 抢杠胡(烧鸡烧杠)
            if len(self.__gang_hou_chu_pai) > 0:
                gang_card = self.__gang_hou_chu_pai[::]
                for gang in self.__gang_hou_chu_pai:
                    re_pao_score += self.cal_score_by_gang_shang_pao(gang[0])

                extra_fan.append(ExtraHuPai.GANG_SHANG_PAO)  # 杠上炮(烧鸡烧杠)

            curr_p = self.curr_player()
            if curr_p.tian_ting > 0:
                bei_sha_bao_seats.append(curr_p.seat_id)
                is_sha_bao = True  # 杀报

        if p.tian_ting > 0:
            if ExtraHuPai.TIAN_HU not in extra_fan and ExtraHuPai.DI_HU not in extra_fan:
                extra_fan.append(ExtraHuPai.TIAN_TING)

        if is_sha_bao:
            extra_fan.append(ExtraHuPai.SHA_BAO)

        if p.eight_card_tian_hu:
            extra_fan.append(ExtraHuPai.TIAN_HU)

        # 2.牌型分(平胡/大队子/小七对/龙七对/地龙背 + 清一色)
        allow_hu_map = {HuType.DI_LONG_QI: self.__di_long_qi, HuType.JIN_GOU_DIAO: True,
                        HuType.QI_DUI: True, HuType.FOUR_CARD_NO_NEAR: self.__four_card_no_near,
                        HuType.FOUR_CARD_IS_SAME: self.__four_card_tian_hu}
        if not is_over:
            hu_type = Rule.get_round_over_jiao_pai(
                p.table_cards, p.cards, allow_hu_map) or HuType.PING_HU
        else:
            hu_type = p.jiao_pai or HuType.PING_HU

        result = {
            "is_zha_hu": 1,
            "card": p.mo_pai,
            "seat_id": p.seat_id,
            "is_zi_mo": is_zi_mo,
            "hu_type": hu_type,
            "extra_hu_type": extra_fan,
        }
        if is_sha_bao:
            result["bei_sha_bao_seats"] = bei_sha_bao_seats
        if not is_zi_mo:
            result["fang_pao_seat_id"] = self.curr_seat_id
            result["re_pao_score"] = re_pao_score
            result["qiang_gang_score"] = qiang_gang_score
            result["card"] = self.__curr_card
            result["gang_card"] = gang_card

        return result, True, []

    async def hu_da_notify(self, hu_list):
        data = []
        is_zi_mo = False
        for win_seat in hu_list:
            winner = self.get_player_by_seat_id(win_seat)
            hu_info, _, _ = self.get_hu_type(winner, dian_pao=not is_zi_mo)
            is_zi_mo = hu_info.get("is_zi_mo")
            if not is_zi_mo:
                self.remove_jian_or_hu(win_seat)
            check_type = CheckType.CHECK_HU_ZI_MO if is_zi_mo else CheckType.CHECK_HU_DIAN_PAO
            hu_info["check_type"] = check_type
            self.__kai_pai_hu_info.append(hu_info)
            winner.set_hu_info(hu_info)
            winner.hu_type = hu_info.get("hu_type", 0)
            if self.flow_status in (FlowStatus.T_IN_EIGHT_TIAN_HU, FlowStatus.T_IN_FOUR_BAO_TING):
                self.__curr_card = winner.cards[-1]
            data.append({
                "seat_id": winner.seat_id,
                "curr_seat_id": self.curr_seat_id,
                "curr_card": self.__curr_card,
                "is_finish": 1,
                "is_zi_mo": is_zi_mo,
                "hu_type": winner.hu_type,
                "extra_hu_type": hu_info.get("extra_hu_type", []),
                "winner_hand_cards": winner.cards,

            })
            if not is_zi_mo:
                self.curr_player().fang_pao = 1
                winner.jie_pao_count()
            else:
                winner.zi_mo_count()
        if not is_zi_mo:
            # 当前玩家打的当前牌从出牌中删除
            self.deal_dian_pao(True)
        data_model = S2CHuInfoMahjong.pb_model(data)
        await self.inner_broadcast(CmdRoom.PLAYER_HU, data_model)

        cards_info = self.get_player_cards_info(hu_list, is_zi_mo)
        cards_model = S2CHuAfterCards.pb_model(cards_info)
        await self.inner_broadcast(CmdRoom.HU_AFTER_CARDS_INFO, cards_model)

    def get_not_operate_player_max_operate(self):
        result = {}
        already_action_seats = set([action[0] for action in self.__player_actions])
        not_operate_player_list = [p.seat_id for p in self.seats if p.seat_id not in already_action_seats]
        for seat_id in not_operate_player_list:
            player = self.get_player_by_seat_id(seat_id)
            if player.operates:
                result[seat_id] = max(player.operates, key=self.get_action_priority)

        return result

    def deal_dian_pao(self, is_dian_pao=False, desc=""):
        """ 处理点炮 """
        # 当前玩家打的当前牌从出牌中删除
        curr_p = self.curr_player()
        if curr_p.chu_cards and curr_p.chu_cards[-1] == self.__curr_card:
            if self.__curr_card == CardsType.YAO_JI and self.__round_first_ji == 1:
                self.log_info("{} 冲锋鸡".format(desc), curr_p.uid, curr_p.seat_id)
                self.__record_cfj = 1
            if self.__curr_card == CardsType.WU_GU_JI and self.__round_first_wgj == 1:
                self.log_info("{} 乌骨冲锋鸡".format(desc), curr_p.uid, curr_p.seat_id)
                self.__record_cfwgj = 1

            card = curr_p.pop_chu_pai()
            self.log_info(self.tid, "{} 删除牌".format(desc), card)
        is_dian_pao and curr_p.dian_pao_count()

    def remove_jian_or_hu(self, seat_id):
        """ 移除指定玩家的捡牌/胡牌相关动作 """
        p = self.get_player_by_seat_id(seat_id)
        p.operates = []

        # 倒序遍历避免索引错乱
        target_actions = {
            ActionType.ACTION_TYPE_JIAN,
            ActionType.ACTION_TYPE_ZHA_JIAN,
            ActionType.ACTION_TYPE_HU,
            ActionType.ACTION_TYPE_ZHA_HU
        }

        for i in reversed(range(len(self.__player_actions))):
            item = self.__player_actions[i]
            if item[0] != seat_id:
                continue
            if item[1] in target_actions:
                self.__player_actions.pop(i)

    def get_player_cards_info(self, hu_list=None, is_zi_mo=False):
        """ 获取玩家手牌信息 """
        cards_info = []
        for p in self.seats:
            if not p:
                continue
            if not is_zi_mo and hu_list and p.seat_id in hu_list:
                p.rev_card(self.__curr_card)  # 非自摸将当前牌放到玩家手牌中
            cards_info.append({"seat_id": p.seat_id, "hand_cards": p.cards})
        return cards_info

    @staticmethod
    def get_action_priority(act):
        return const.ACTION_PRIORITY.get(act) or 0

    def get_operate_player_max_operate(self):
        result = {}
        for player in self.seats:
            if player.operates:
                result[player.seat_id] = max(player.operates, key=self.get_action_priority)
        return result

    @property
    def record_operates(self):
        return self.__record_operates

    def clear_record_operates(self, seat_id: int):
        self.__record_operates.pop(seat_id, None)

    def has_do_action(self, p):
        for item in self.__player_actions:
            if item[0] == p.seat_id:
                return True
        return False

    def record_lou_hu(self, p: Player, desc=""):
        """记录漏胡"""
        if self.__have_men_jian_hu:  # 有胡牌提示不记录漏胡
            self.log_info(self.tid, p.uid, "胡牌提示不记录漏胡")
            return
        if p.tian_ting and not p.all_chu_cards:  # 能天胡，第一次选择天听后出牌不算漏胡
            self.log_info(self.tid, p.uid, "能天胡，第一次选听后出牌不算漏胡")
            return
        is_zi_mo = p.seat_id == self.curr_seat_id
        hu_info, _, _ = self.get_hu_type(p, lou=True)
        score = 0
        check_type = CheckType.LOU_MEN
        if not is_zi_mo:
            check_type = CheckType.LOU_JIAN
            score = self.cal_jian_score(p, hu_info)
        data = self.deal_men_jian_data(p, score, hu_info, check_type=check_type)
        p.is_zha_hu = 1
        self.log_info(self.tid, p.uid, "记录玩家漏胡: %s" % desc, hu_info)
        self.__men_record.append(data)

    def save_player_action(self, p, action, data=None):
        self.clear_record_operates(p.seat_id)
        p.operates = [action]
        self.__player_actions.append([p.seat_id, action, data])

    def remove_player_action(self, tian_ting=False):
        """
        当玩家所做动作不需要额外处理时，走过一遍check_action_end后就删除
        主要为了解决玩家报听后没清，另一个玩家能碰导致的碰失败
        """
        for i, item in enumerate(self.__player_actions):
            act = item[1]
            if tian_ting:
                if act != ActionType.ACTION_TYPE_TIAN_TING:
                    continue
            else:
                if act in (ActionType.ACTION_TYPE_HU, ActionType.ACTION_TYPE_MEN, ActionType.ACTION_TYPE_JIAN,
                           ActionType.ACTION_TYPE_PENG, ActionType.ACTION_TYPE_ZHUAN_WAN_GANG,
                           ActionType.ACTION_TYPE_MING_GANG, ActionType.ACTION_TYPE_AN_GANG,
                           ActionType.ACTION_TYPE_ZHA_JIAN, ActionType.ACTION_TYPE_ZHA_MEN,
                           ActionType.ACTION_TYPE_ZHA_HU):
                    continue
            self.__player_actions.pop(i)
            seat_id = item[0]
            p = self.get_player_by_seat_id(seat_id)
            p.operates = []  # 这里不清除会导致进入超时中把玩家当做炸胡
            self.log_info(self.tid, seat_id, "remove_player_action", self.__player_actions)

    def calc_operates_after_chu_pai(self, p: Player):
        """计算出牌后其他玩家的操作"""
        result = []
        if not self.__curr_card:
            return result
        self.check_hu_by_chu_pai(p, result)
        is_ming_gang, _ = self.ming_gang_de_qi(p, self.__curr_card)
        if p.card_is_lock():
            if is_ming_gang:
                allow_hu_map = {HuType.DI_LONG_QI: self.__di_long_qi, HuType.JIN_GOU_DIAO: False,
                                HuType.QI_DUI: True, HuType.FOUR_CARD_NO_NEAR: self.__four_card_no_near,
                                HuType.FOUR_CARD_IS_SAME: self.__four_card_tian_hu}
                temp_cards = [c for c in p.cards if c != self.__curr_card]
                ting_list1 = Rule.get_ting_hu_list(p.table_cards, temp_cards, allow_hu_map, self.__lai_zi)
                # 一致的话可以杠
                if ting_list1 == p.ting_list:
                    result.append(ActionType.ACTION_TYPE_MING_GANG)
        else:
            if is_ming_gang:
                result.append(ActionType.ACTION_TYPE_MING_GANG)
            if p.can_peng(self.__curr_card, Rule):
                result.append(ActionType.ACTION_TYPE_PENG)

        if not self.__have_men_jian_hu and not p.is_robot:
            self.__record_operates.setdefault(p.seat_id, []).append(ActionType.ACTION_TYPE_PASS)  # 房卡场让玩家每次点过
        if self.__left_three_bi_hu and self.poker.left_count < const.XUE_LIU_LEFT_BI_HU and ActionType.ACTION_TYPE_HU in result:
            result = [ActionType.ACTION_TYPE_HU]
        if result and (
                ActionType.ACTION_TYPE_HU not in result or self.play_type not in (
        PlayType.JIAN_LOU_XUE_LIU, PlayType.AN_LONG_XUE_ZHAN)):
            result.append(ActionType.ACTION_TYPE_PASS)
        if result and ActionType.ACTION_TYPE_HU in result and not p.men_cards and self.poker.left_count >= const.XUE_LIU_LEFT_BI_HU:
            result.append(ActionType.ACTION_TYPE_PASS)
        required_actions = {ActionType.ACTION_TYPE_PASS, ActionType.ACTION_TYPE_JIAN}
        if result and p.tian_ting and required_actions.issubset(result):
            result.remove(ActionType.ACTION_TYPE_PASS)
        return result

    def check_hu_by_chu_pai(self, p, result):
        can_hu, hu_info = self.hu_de_qi(p)
        if can_hu:
            result.append(ActionType.ACTION_TYPE_HU)
            result.append(ActionType.ACTION_TYPE_JIAN)
            if self.poker.left_count >= const.XUE_LIU_LEFT_BI_HU:
                if len(p.men_cards) == 0:
                    hu_type = hu_info["hu_type"]
                    extra_hu_lst = hu_info.get("extra_hu_type", [])
                    if not p.tui_zhang_ke_kai and (self.__bi_men_yi_shou or self.xiao_hu_bi_men(hu_type, extra_hu_lst)
                                                   or self.bao_ting_bi_men(p, hu_type)) and not self.is_jue_zhang(p):
                        result.remove(ActionType.ACTION_TYPE_HU)
                if self.curr_seat_id == (
                        p.seat_id - 2) % 3 + 1 and p.jian_next_player_card > 0:  # 连捡不能胡 捡过了上上家 上家出的就不能开了 2025/5/26
                    if self.__bi_men_yi_shou and ActionType.ACTION_TYPE_HU in result and not self.is_jue_zhang(p):
                        self.log_info("连捡不能胡,seat_id", p.seat_id)
                        result.remove(ActionType.ACTION_TYPE_HU)

            else:
                if self.__left_three_bi_hu:
                    # 最后三张必胡
                    self.log_info("进入尾三必胡,出牌,seat_id", p.seat_id)
                    result.remove(ActionType.ACTION_TYPE_JIAN)
                    return result
        # 杠上炮必胡/必捡
        if can_hu and len(self.__gang_hou_chu_pai) > 0:
            return result

    def cal_jian_score(self, p, hu_info):
        """ 计算捡分（好像不是很必要） """
        extra_hu_lst = hu_info["extra_hu_type"]
        base_score = self.get_base_score(hu_info, extra_hu_lst)
        extra_score = self.cal_extra_hu_score(hu_info, extra_hu_lst, self.curr_player().seat_id)
        total_score = base_score + extra_score + p.shang_ga_score + self.curr_player().shang_ga_score  # 正数
        return total_score

    def get_base_score(self, hu_info: dict, extra_hu_lst, seat_id=-1, zi_mo=False) -> int:
        """
        获取牌型分
        主要处理平胡与特殊胡同时存在时不算平胡分
        """
        hu_type = hu_info.get("hu_type")
        base_score = self.pai_xing_score_map[hu_type]
        # 牌型为平胡且额外番中有天胡/地胡/天听/杀报，则平胡牌型分不算
        if hu_type in (HuType.PING_HU, HuType.FOUR_CARD_NO_NEAR) and set(extra_hu_lst).intersection(
                const.SPECIAL_HU_TYPE):
            if zi_mo and seat_id > 0 and ExtraHuPai.SHA_BAO in extra_hu_lst:
                # 自摸时有杀报 无天听|天湖
                if seat_id in hu_info.get("bei_sha_bao_seats", []):
                    base_score = 0
                elif set(extra_hu_lst).intersection(const.SPECIAL_HU_TYPE1):
                    base_score = 0
            else:
                base_score = 0
        elif self.__eight_card_tian_hu and set(extra_hu_lst).intersection(SPECIAL_HU_TYPE_BY_EIGHT):
            base_score = 0
        elif self.__four_card_tian_hu and ExtraHuPai.TIAN_HU_BY_FOUR_CARD in extra_hu_lst:
            base_score = 0
        if self.__zi_mo_jia_bei and zi_mo:
            base_score *= 2
        return base_score

    def cal_extra_hu_score(self, hu_info: dict, extra_hu_lst: list, seat_id=-1, is_zi_mo=False):
        """ 统计额外胡的分 """
        total_score = 0
        for extra_fan in extra_hu_lst:
            if extra_fan == ExtraHuPai.SHA_BAO:
                # 非当前玩家被杀报(闷 杀报有可能是1人有可能是多人)
                if seat_id not in hu_info.get("bei_sha_bao_seats", []):
                    continue
            if extra_fan == ExtraHuPai.QIANG_GANG_HU:  # 抢杠胡按两倍牌型付
                score = hu_info.get("qiang_gang_score", 0)
                score += self.cal_suo_de_jia_1_gang_is_ji(hu_info.get("gang_card") or [])
            elif extra_fan == ExtraHuPai.GANG_SHANG_PAO:
                score = hu_info.get("re_pao_score", 0)
                score += self.cal_suo_de_jia_1_gang_is_ji(hu_info.get("gang_card") or [])
            else:
                score = self.extra_score_map[extra_fan]
            if is_zi_mo:
                if extra_fan in const.SPECIAL_HU_TYPE:
                    score *= 2
                elif extra_fan in SPECIAL_HU_TYPE_BY_EIGHT:
                    score *= 2
                elif extra_fan == ExtraHuPai.TIAN_HU_BY_FOUR_CARD:
                    score *= 2
            total_score += score
        return total_score

    def cal_suo_de_jia_1_gang_is_ji(self, gang_cards) -> int:
        """ 计算抢杠胡|杠上炮时的杠是鸡的情况下 """
        for gang_card in gang_cards:
            card = gang_card[1]
            if card not in self.__default_ji:
                continue
            gang_type = gang_card[0]
            score = self.__ji_pai_score.get(card)  # 单个鸡的分
            if gang_type == ActionType.ACTION_TYPE_AN_GANG:
                score *= 2  # 暗杠算站鸡
            if self.__ji_cards and card in self.__ji_cards:  # 默认鸡被翻到则翻倍（金鸡）
                score *= 2

            score *= 4  # 鸡有4个
            # -- snip --
            if gang_type != ActionType.ACTION_TYPE_MING_GANG:
                score *= (self.in_room_count - 1)
            # -- snip --
            return score
        return 0

    def deal_men_jian_data(self, p: Player, win_total_score, hu_info, check_type=CheckType.CHECK_MEN):
        data = {
            "curr_card": hu_info.get("card"),
            "score": win_total_score,
            "check_type": check_type,
        }
        data.update(hu_info)  # 胡info
        if self.flow_status == FlowStatus.T_IN_EIGHT_TIAN_HU:
            data["card"] = p.cards[-1]
        return data

    async def on_player_pass(self, p: Player):
        if self.room_status != RoomStatus.T_PLAYING:
            return StaCode.FLOW_ERR, "桌子状态不在游戏中"
        flows = [FlowStatus.T_IN_PUBLIC_OPRATE, FlowStatus.T_IN_MO_PAI_CALL,
                 FlowStatus.T_IN_MING_GANG_PAI_CALL, FlowStatus.T_IN_FOUR_BAO_TING,
                 FlowStatus.T_IN_ZHUAN_WAN_GANG_PAI_CALL, FlowStatus.T_IN_TIAN_HU,
                 FlowStatus.T_IN_TIAN_TING, FlowStatus.T_IN_EIGHT_TIAN_HU]
        if self.play_type == PlayType.JIAN_LOU_XUE_LIU:
            flows.append(FlowStatus.T_IN_CHU_PAI)
        if self.flow_status not in flows:
            return StaCode.FLOW_ERR, "游戏流程不在可过流程"

        if self.has_do_by_action(p, ActionType.ACTION_TYPE_PASS):  # 不允许再次操作
            return StaCode.ALREADY_DO, "已经操作过了"

        has_do_action = self.has_do_action(p)
        can_operates = p.can_operates()
        if can_operates and not has_do_action:
            # 2025/6/9 最后三张必开 重连后客户端会显示过 这里限制不允许过
            if self.play_type != PlayType.JIAN_LOU_XUE_LIU:
                if p.is_action_in_operates(
                        ActionType.ACTION_TYPE_HU) and self.poker.left_count < const.XUE_LIU_LEFT_BI_HU:
                    return StaCode.RULE_ERR, "尾三必胡"

        if self.flow_status == FlowStatus.T_IN_TIAN_TING and self.dealer_id == p.seat_id and p.cards_len == self.deal_cards_count + 1:
            p.can_tian_ting = -1

        if can_operates and not has_do_action:
            # 一炮多响时有人选择过则这里-1
            if self.__jie_pao_count > 1:
                self.__jie_pao_count -= 1

            flag = True  # 主要用于判断只走一次漏胡
            if p.is_action_in_operates(ActionType.ACTION_TYPE_HU):
                if self.flow_status == FlowStatus.T_IN_ZHUAN_WAN_GANG_PAI_CALL:
                    # 抢杠胡
                    flag = False
                    self.log_info(self.tid, p.uid, "抢杠胡选择过漏胡", p.tian_ting, p.operates)
                    self.set_tui_zhang_ke_kai(p)
                    self.record_lou_hu(p, "pass")
                elif len(self.__gang_hou_chu_pai) > 0:
                    # 抢杠胡
                    flag = False
                    self.log_info(self.tid, p.uid, "杠上炮", p.tian_ting, p.operates)
                    self.set_tui_zhang_ke_kai(p)
                    self.record_lou_hu(p, "pass")

            if flag and (p.can_hu_men_jian()):
                self.set_tui_zhang_ke_kai(p)
                if len(p.men_cards) > 0 or p.tian_ting == 1:
                    # todo: 能胡过了时间算漏胡 漏胡算分后续确认
                    self.record_lou_hu(p, "pass")
                    self.log_info(self.tid, p.uid, "玩家能胡选择过漏胡", p.tian_ting, p.operates)

            self.log_info(self.tid, p.uid, "玩家有操作选择过：", len(p.men_cards), p.tian_ting)

        self.save_player_action(p, ActionType.ACTION_TYPE_PASS)
        p.operates = []
        one_of_model = s2c_one_of_model()
        one_of_model.seat_id = self.curr_seat_id
        await self.inner_send(p, CmdRoom.PLAYER_PASS, one_of_model)
        return StaCode.PASS, ""

    async def on_player_chu_pai(self, player: Player, data):
        gang_model.ParseFromString(data)
        card = gang_model.card or 0
        if self.room_status != RoomStatus.T_PLAYING:
            return StaCode.RULE_ERR, "桌子状态不在游戏中，不可出牌"
        if self.flow_status not in (FlowStatus.T_IN_CHU_PAI, FlowStatus.T_IN_DI_HU_CHU_PAI,
                                    FlowStatus.T_IN_MO_PAI_CALL):
            desc = "当前有玩家选听中" if self.flow_status == FlowStatus.T_IN_TIAN_TING else "当前流程不在可出牌流程"
            return StaCode.FLOW_ERR, desc
        if self.curr_seat_id != player.seat_id:
            return StaCode.NOT_YOUR_TURN, "没有轮到你"
        if self.has_do_by_action(player, ActionType.ACTION_TYPE_CHU_PAI):  # 不允许再次操作
            return StaCode.ALREADY_DO, "已经操作过出牌了"
        if player.card_is_lock():
            if card not in player.get_out_not_lock_card():
                return StaCode.RULE_ERR, "出牌在锁定范围内，不可出"
        if card not in player.cards:
            return StaCode.RULE_ERR, "出牌不在手牌范围内，不可出"
        if player.cards_len % 3 != 2:
            return StaCode.RULE_ERR, "手牌数不对，不可出"
        if player.can_hu_men_jian() and self.play_type < 3:
            if self.__left_three_bi_hu and self.poker.left_count < 3:
                return StaCode.RULE_ERR, '尾三必开'

            self.set_tui_zhang_ke_kai(player)
            if len(player.men_cards) > 0 or player.tian_ting == 1:
                self.log_info(self.tid, player.uid, "玩家出牌漏胡, 闷牌后不能改牌", len(player.men_cards), player.operates)
                self.record_lou_hu(player, "出牌")
        self.save_player_action(player, ActionType.ACTION_TYPE_CHU_PAI, data)
        player.chu_pai(card)
        player.mo_pai = 0
        self.__curr_card = card
        self.__curr_card_exist = 1
        self.__before_seat_id = self.curr_seat_id

        if player.card_is_lock():
            # 若玩家起手能胡选择天听不锁牌，此处再锁牌
            if len(player.ting_list) == 0:
                allow_hu_map = {HuType.DI_LONG_QI: self.__di_long_qi, HuType.JIN_GOU_DIAO: False,
                                HuType.QI_DUI: True, HuType.FOUR_CARD_NO_NEAR: self.__four_card_no_near,
                                HuType.FOUR_CARD_IS_SAME: self.__four_card_tian_hu}
                ting_list = Rule.get_ting_hu_list(player.table_cards, player.cards, allow_hu_map, self.__lai_zi)
                player.ting_list = ting_list
                player.lock_cards = list(player.cards)
                data = {"lock_cards": player.lock_cards}
                data_model = S2CTurnToMahjong.pb_model(**data)
                await self.inner_send(player, CmdRoom.PLAYER_TIAN_TING, data_model)
        play_card = {
            "seat_id": self.curr_seat_id,
            "card": self.__curr_card,
        }
        data_model = S2CPlayCardsMahjong.pb_model(**play_card)
        await self.inner_broadcast(CmdRoom.PLAY_CARDS, data_model)
        return StaCode.PASS, ""

    async def on_player_peng(self, player: Player):
        if self.room_status != RoomStatus.T_PLAYING:
            return StaCode.FLOW_ERR, "桌子状态不在游戏中,不可碰"
        if self.flow_status != FlowStatus.T_IN_PUBLIC_OPRATE:
            return StaCode.FLOW_ERR, "当前流程不在可碰流程"
        if not player.is_action_in_operates(ActionType.ACTION_TYPE_PENG):
            return StaCode.RULE_ERR, "没有可碰操作"
        if self.has_do_by_action(player, [ActionType.ACTION_TYPE_PENG]):  # 不能再次操作
            return StaCode.ALREADY_DO, "已经操作过碰了"

        if self.play_type < 3 and ActionType.ACTION_TYPE_HU in player.operates or ActionType.ACTION_TYPE_JIAN in player.operates:
            self.set_tui_zhang_ke_kai(player)
            if self.__gang_hou_chu_pai:  # TODO: 记一个漏捡
                # 杠上炮必胡
                self.log_info(self.tid, player.uid, "杠上炮必须捡/胡, 不能碰")
                self.record_lou_hu(player, "peng")
        data = {"seat_id": player.seat_id, "is_finish": 0}
        self.save_player_action(player, ActionType.ACTION_TYPE_PENG, data)
        self.log_info(self.tid, player.uid, "choose peng action did suc!")
        return StaCode.PASS, ""

    async def on_player_gang(self, player: Player, data):
        if self.room_status != RoomStatus.T_PLAYING:
            return StaCode.FLOW_ERR, "桌子状态不在游戏中,不可杠"
        if self.flow_status not in (FlowStatus.T_IN_PUBLIC_OPRATE, FlowStatus.T_IN_MO_PAI_CALL,
                                    FlowStatus.T_IN_TIAN_HU, FlowStatus.T_IN_TIAN_TING):
            return StaCode.FLOW_ERR, "当前流程不在可杠流程"
        gang_act = player.gang_in_operates()
        if not gang_act:
            return StaCode.RULE_ERR, "没有可杠操作"

        if self.has_do_by_action(player, [ActionType.ACTION_TYPE_MING_GANG, ActionType.ACTION_TYPE_ZHUAN_WAN_GANG,
                                          ActionType.ACTION_TYPE_AN_GANG]):  # 不能再次操作
            return StaCode.ALREADY_DO, "已经操作过杠了"

        if self.play_type < 3 and player.can_hu_men_jian():
            self.set_tui_zhang_ke_kai(player)
            if self.__gang_hou_chu_pai:  # TODO: 记一个漏捡
                # 杠上炮必胡
                self.log_info(self.tid, player.uid, "杠上炮必须捡/胡, 不能杠")
                self.record_lou_hu(player, "gang")

        if gang_act in (ActionType.ACTION_TYPE_ZHUAN_WAN_GANG, ActionType.ACTION_TYPE_AN_GANG):
            gang_model.ParseFromString(data)
            card = gang_model.card or 0
            if player.check_zhuan_wan_gang(card):
                gang_act = ActionType.ACTION_TYPE_ZHUAN_WAN_GANG
            elif player.check_an_gang(card):
                if self.flow_status == FlowStatus.T_IN_TIAN_TING and self.dealer_id == player.seat_id:
                    player.can_tian_ting = -1  # 庄在报听中能杠，杠后不算听2023/11/2

                gang_act = ActionType.ACTION_TYPE_AN_GANG
            else:
                self.log_info(self.tid, "玩家杠，参数错误", card, player.cards)
                return StaCode.RULE_ERR, "参数错误"
        self.save_player_action(player, gang_act, data)

        self.log_info(self.tid, player.uid, "choose gang action did suc!")
        return StaCode.PASS, ""

    async def on_player_hu(self, player: Player):
        if self.room_status != RoomStatus.T_PLAYING:
            return StaCode.FLOW_ERR, "桌子状态不在游戏中，不可胡"
        if player.is_out:
            return StaCode.FLOW_ERR, "玩家已被淘汰"
        if self.flow_status not in (FlowStatus.T_IN_CHU_PAI, FlowStatus.T_IN_DI_HU_CHU_PAI, FlowStatus.T_IN_MO_PAI,
                                    FlowStatus.T_IN_MO_PAI_CALL, FlowStatus.T_IN_PUBLIC_OPRATE,
                                    FlowStatus.T_IN_MING_GANG_PAI_CALL, FlowStatus.T_IN_FOUR_BAO_TING,
                                    FlowStatus.T_IN_ZHUAN_WAN_GANG_PAI_CALL, FlowStatus.T_IN_TIAN_HU,
                                    FlowStatus.T_IN_TIAN_TING, FlowStatus.T_IN_EIGHT_TIAN_HU):
            return StaCode.FLOW_ERR, "当前流程不可胡"
        if self.has_do_by_action(player, [ActionType.ACTION_TYPE_HU]):  # 不能再次操作
            return StaCode.ALREADY_DO, "已经操作过胡了"
        if not player.is_action_in_operates(ActionType.ACTION_TYPE_HU):
            if self.__have_men_jian_hu:
                self.log_info(self.tid, player.uid, "胡牌提示版本没有炸胡!")
                return StaCode.RULE_ERR, "胡牌提示版本没有炸胡"
            # todo: 诈胡算分  自己的分，加别人的牌型分
            player.can_tian_ting = -1
            player.is_zha_hu = 1
            self.log_info(self.tid, player.uid, "choose hu action 诈胡了!", player.operates)
            self.save_player_action(player, ActionType.ACTION_TYPE_ZHA_HU)
            data = {"seat_id": player.seat_id, "is_finish": 0}
            data_model = S2CHuBaseInfo.pb_model(**data)
            await self.inner_send(player, CmdRoom.ZHA_HU, data_model)
            return StaCode.PASS, ""

        if self.flow_status == FlowStatus.T_IN_ZHUAN_WAN_GANG_PAI_CALL:
            # 被抢杠胡时删去转弯杠玩家杠的那张牌
            if self.__curr_card in self.__curr_action_player.cards:
                self.log_info(self.tid, "被抢杠胡时删去转弯杠玩家杠的那张牌", self.__curr_card)
                self.__curr_action_player.chu_pai(self.__curr_card, chu_pai=False)

        player.can_tian_ting = -1
        self.save_player_action(player, ActionType.ACTION_TYPE_HU)
        self.log_info("player", player.uid, "choose hu action did suc!")
        if self.flow_status == FlowStatus.T_IN_EIGHT_TIAN_HU:  # 八张天胡清除其他玩家胡操作
            for p in self.seats:
                if p.seat_id != player.seat_id:
                    p.operates = []

        return StaCode.PASS, ""

    async def on_player_men(self, player: Player):
        if self.room_status != RoomStatus.T_PLAYING:
            return StaCode.FLOW_ERR, "桌子状态不在游戏中，不可闷"
        if player.is_out:
            return StaCode.FLOW_ERR, "玩家已被淘汰，不可闷"
        if self.flow_status not in (FlowStatus.T_IN_CHU_PAI, FlowStatus.T_IN_MO_PAI, FlowStatus.T_IN_MO_PAI_CALL,
                                    FlowStatus.T_IN_PUBLIC_OPRATE, FlowStatus.T_IN_TIAN_HU,
                                    FlowStatus.T_IN_TIAN_TING, FlowStatus.T_IN_EIGHT_TIAN_HU):
            return StaCode.FLOW_ERR, "当前流程不可闷"
        if self.flow_status != FlowStatus.T_IN_EIGHT_TIAN_HU and player.seat_id != self.curr_seat_id:
            return StaCode.NOT_YOUR_TURN, "当前没有轮到该玩家"
        if self.poker.left_count < const.XUE_LIU_LEFT_BI_HU:
            return StaCode.RULE_ERR, "牌库小于三张必开，不可闷"
        if self.flow_status != FlowStatus.T_IN_EIGHT_TIAN_HU and player.mo_pai == 0:
            self.log_info(self.tid, player.uid, "当前非玩家摸牌阶段")
            return StaCode.FLOW_ERR, "当前非玩家摸牌阶段"
        if self.has_do_by_action(player, [ActionType.ACTION_TYPE_MEN]):  # 不能再次操作
            self.log_info(self.tid, player.uid, "men------重复操作不对：", self.flow_status)
            return StaCode.ALREADY_DO, "不能再次操作"
        if not player.is_action_in_operates(ActionType.ACTION_TYPE_MEN):
            if self.__have_men_jian_hu:
                self.log_info(self.tid, player.uid, "胡牌提示版本没有炸闷!")
                return StaCode.RULE_ERR, "胡牌提示版本没有炸闷"
            # todo: 诈胡算分  自己的分，加别人的牌型分
            player.can_tian_ting = -1  # 2025/1/17主要处理能听和能密的玩家同时出现，先密导致流程卡住
            player.is_zha_hu = 1
            self.log_info(self.tid, player.uid, "选择炸闷", player.operates)
            data = {"seat_id": player.seat_id, "is_finish": 0, "is_zha_hu": 1}
            data_model = S2CHuBaseInfo.pb_model(**data)
            await self.inner_send(player, CmdRoom.ZHA_MEN, data_model)
            self.save_player_action(player, ActionType.ACTION_TYPE_ZHA_MEN)
            return StaCode.PASS, ""

        player.can_tian_ting = -1  # 2025/1/17主要处理能听和能密的玩家同时出现，先密导致流程卡住
        self.save_player_action(player, ActionType.ACTION_TYPE_MEN)
        data = {"seat_id": player.seat_id, "is_finish": 0, "is_zha_hu": 0}
        data_model = S2CHuBaseInfo.pb_model(**data)
        await self.inner_send(player, CmdRoom.PLAYER_MEN, data_model)
        self.log_info("player", player.uid, "choose men action did suc!")
        return StaCode.PASS, ""

    async def on_player_jian(self, player: Player):
        if self.room_status != RoomStatus.T_PLAYING:
            return StaCode.FLOW_ERR, "桌子状态不在游戏中，不可捡"
        if player.is_out:
            return StaCode.FLOW_ERR, "玩家已被淘汰，不可捡"
        if self.flow_status not in (FlowStatus.T_IN_PUBLIC_OPRATE, FlowStatus.T_IN_ZHUAN_WAN_GANG_PAI_CALL,
                                    FlowStatus.T_IN_TIAN_HU, FlowStatus.T_IN_TIAN_TING,
                                    FlowStatus.T_IN_MING_GANG_PAI_CALL):
            return StaCode.FLOW_ERR, "当前流程不可捡"
        if self.poker.left_count < const.XUE_LIU_LEFT_BI_HU:
            return StaCode.RULE_ERR, "牌库小于三张必开，不可捡"
        if self.has_do_by_action(player, [ActionType.ACTION_TYPE_JIAN]):  # 不能再次操作
            return StaCode.ALREADY_DO, "已经操作过捡了"
        if not player.is_action_in_operates(ActionType.ACTION_TYPE_JIAN):
            if self.__have_men_jian_hu:
                self.log_info(self.tid, player.uid, "胡牌提示版本没有炸捡!")
                return StaCode.RULE_ERR, "胡牌提示版本没有炸捡"
                # todo: 诈胡算分  自己的分，加别人的牌型分
            player.is_zha_hu = 1
            self.log_info(self.tid, player.uid, player.uid, "选择炸捡", player.operates)
            data = {"seat_id": player.seat_id, "is_finish": 0, "is_zha_hu": 1}
            data_model = S2CHuBaseInfo.pb_model(**data)
            await self.inner_send(player, CmdRoom.ZHA_JIAN, data_model)
            self.save_player_action(player, ActionType.ACTION_TYPE_ZHA_JIAN)
            return StaCode.PASS, ""

        if self.curr_seat_id == (player.seat_id % 3) + 1:  # 记录下家在一圈内被捡过
            player.jian_next_player_card = 1

        self.save_player_action(player, ActionType.ACTION_TYPE_JIAN)
        self.log_info(self.tid, player.uid, player.seat_id, "choose jian action did suc!")
        return StaCode.PASS, ""

    async def on_player_shang_ga(self, player: Player, data):
        shang_ga_model.ParseFromString(data)
        shang_ga_score = shang_ga_model.shang_ga or 0
        if player.has_shang_ga:
            return StaCode.RULE_ERR, "已经估卖过了"
        if shang_ga_score not in self.__shang_ga_list:
            return StaCode.RULE_ERR, "当前分值不在估卖范围"
        player.has_shang_ga = True
        player.shang_ga_score = shang_ga_score
        data = {"seat_id": player.seat_id, "shang_ga": player.shang_ga_score}
        data_model = S2CShangGaMahjong.pb_model(**data)
        await self.inner_broadcast(CmdRoom.PLAYER_SHANG_GA, data_model)

        check_all_shang_ga = True
        for p in self.seats:
            if not p.has_shang_ga:
                check_all_shang_ga = False
                break
        if check_all_shang_ga:
            self.log_info(self.tid, "player_shang_ga_call is_all_chui")
            self.call_flow(1, self.deal_cards)

        return StaCode.PASS, ""

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

    async def on_player_exchange_cards(self, player: Player, data):
        if self.flow_status != FlowStatus.T_IN_EXCHANGE_CARDS:
            return StaCode.FLOW_ERR, "当前流程不可换牌"
        if player.tian_ting:
            return StaCode.RULE_ERR, "天听不可换牌"
            # 检测data是否是list类型
        if isinstance(data, list):
            ex_cards = data
        else:
            exchange_model.ParseFromString(data)
            ex_cards = exchange_model.cards or []

        if len(ex_cards) != 3:
            return StaCode.RULE_ERR, "所选换牌内容不符合"
        if self.__exchange_cards_type == ChangeCardsType.SAME_SUIT_CARDS:
            # 换同色
            group_cards = Rule.group_by_suit(ex_cards)
            if len(group_cards) > 1:
                return StaCode.RULE_ERR, "所选牌花色不是同色"
        target_player = self.find_target_exchange_cards_seat(player)
        if not target_player:
            return StaCode.RULE_ERR, "没有可交换位置"
        ex_cards_index = self.find_index_need_exchange_cards(player, ex_cards)
        if not ex_cards_index:
            self.log_info("换牌数据有误", ex_cards, player.seat_id)
            return StaCode.RULE_ERR, "数据错误"

        if self.exchange_cards_is_end() or player.seat_id in self.__exchange_cards_info:
            self.log_info(player.uid, "当前玩家是否选择换牌了", player.seat_id in self.__exchange_cards_info,
                          "exchange_cards_info_count:", len(self.__exchange_cards_info))
            return StaCode.RULE_ERR, "已经换过牌了"
        self.__exchange_cards_info[player.seat_id] = {
            "ex_cards": ex_cards,
            "ex_cards_index": ex_cards_index,
            "target_p": target_player
        }
        one_of_model = s2c_one_of_model()
        one_of_model.seat_id = player.seat_id
        await self.inner_broadcast(CmdRoom.PLAYER_EXCHANGE_CARDS, one_of_model)
        if self.exchange_cards_is_end():
            p_get_cards = {}
            for c_info in self.__exchange_cards_info.values():
                target_p = c_info.get("target_p")
                cards = c_info.get("ex_cards")
                target_c_info = self.__exchange_cards_info.get(target_p.seat_id)
                target_ex_cards_index = target_c_info.get("ex_cards_index")
                target_p.exchange_cards_seat(target_ex_cards_index, cards)
                p_get_cards[target_p.seat_id] = cards

            result = {}
            send_list = []
            for p in self.seats:
                get_cards = p_get_cards.get(p.seat_id) or []
                if p.seat_id == self.dealer_id and p.tian_ting != 1:
                    p.sort_cards()
                    p.mo_pai = p.cards[-1]
                    self.__curr_card = p.mo_pai
                    self.log_info(self.tid, "换牌后庄改变摸的牌", p.uid, p.cards[-1])
                result["seat_id"] = p.seat_id
                result["hand_cards"] = p.cards
                result["get_cards"] = get_cards
                data_model = S2CExchangeCardsInfo.pb_model(**result)
                send_list.append(self.inner_send(p, CmdRoom.PLAYER_EXCHANGE_CARDS, data_model))
            if send_list:
                await asyncio.gather(*send_list)
            self.call_flow(2, self.ding_que_or_tian_ting)
        return StaCode.PASS, ""

    async def on_player_tian_ting(self, p: Player):
        if self.flow_status not in (
        FlowStatus.T_IN_TIAN_TING, FlowStatus.T_IN_FOUR_BAO_TING, FlowStatus.T_IN_MO_PAI_CALL):
            return StaCode.RULE_ERR, "当前流程不可天听"
        if not p.is_action_in_operates(ActionType.ACTION_TYPE_TIAN_TING):
            return StaCode.RULE_ERR, "不存在可天听操作"
        if p.tian_ting:
            return StaCode.ALREADY_DO, "玩家已经天听"
        result = {
            "seat_id": p.seat_id,
        }
        if p.cards_len == self.deal_cards_count + 1 and p.is_action_in_operates(ActionType.ACTION_TYPE_HU):
            # 暂不锁牌，待玩家打出再锁牌
            if p.can_tian_ting >= 0:
                self.log_info(self.tid, p.uid, "玩家天听且能胡，暂不锁牌")
                p.tian_ting = 1
                p.can_tian_ting = -1

                result["tian_ting"] = p.tian_ting
                result["lock_cards"] = []
                data_model = S2CTianTingInfo.pb_model(**result)
                await self.inner_broadcast(CmdRoom.PLAYER_TIAN_TING, data_model)
        else:
            p.tian_ting = 1
            p.can_tian_ting = -1
            allow_hu_map = {HuType.QI_DUI: True, HuType.DI_LONG_QI: False,
                            HuType.FOUR_CARD_NO_NEAR: self.__four_card_no_near}
            if self.play_type != PlayType.ZUN_YI_LAI_ZI:
                _, tian_ting_cards = Rule.which_cards_to_play_can_tian_ting(p.table_cards, p.cards, allow_hu_map)
            else:
                _, tian_ting_cards = Rule.get_tian_ting_cards(p.table_cards, p.cards, p.que, lai_zi=self.__lai_zi)
            result["tian_ting"] = p.tian_ting
            data_model = S2CTianTingInfo.pb_model(**result)
            await self.inner_broadcast(CmdRoom.PLAYER_TIAN_TING, data_model, exclude_uid=p.uid)
            self.log_info(self.tid, p.uid, "tian_ting_cards", tian_ting_cards)
            p.set_lock_cards(tian_ting_cards)

            # 设置ting_list
            ting_list = Rule.get_ting_hu_list(p.table_cards, p.cards, allow_hu_map, self.__lai_zi)
            p.ting_list = ting_list
            # result["lock_cards"] = p.lock_cards
            # data_model = S2CTianTingInfo.pb_model(**result)

            data_model.lock_cards.extend(p.lock_cards)
            await self.inner_send(p, CmdRoom.PLAYER_TIAN_TING, data_model)
        self.save_player_action(p, ActionType.ACTION_TYPE_TIAN_TING)
        self.log_info("报听", p.uid)
        p.operates = []
        return StaCode.PASS, ""

    def exchange_cards_is_end(self):
        return len(self.__exchange_cards_info) == self.max_player_count - self.get_tian_ting_player_count()

    def has_do_by_action(self, p, action):
        """ 记录玩家操作，不能重复操作 """
        if isinstance(action, list):
            actions = [ActionType.ACTION_TYPE_MEN, ActionType.ACTION_TYPE_ZHA_MEN,
                       ActionType.ACTION_TYPE_JIAN, ActionType.ACTION_TYPE_ZHA_JIAN,
                       ActionType.ACTION_TYPE_HU, ActionType.ACTION_TYPE_ZHA_HU]
            target_actions = actions
        else:
            target_actions = [action]
        return any(
            item[0] == p.seat_id and item[1] in target_actions
            for item in self.__player_actions
        )

    async def ding_que_or_tian_ting(self):
        """如果二丁拐 三丁拐没开两门牌，开始定缺"""
        if self.play_type in (PlayType.GUI_YANG_3, PlayType.GUI_YANG_2) and self.__liang_men_pai == 0:
            await self.start_ding_que()
        else:
            await self.start_tian_ting()

    async def start_ding_que(self):
        self.log_info("开始定缺")
        if self.room_status not in (RoomStatus.T_PLAYING, RoomStatus.T_DISMISS):
            return StaCode.FLOW_ERR, "桌子状态不可定缺"
        data = {
            "ding_que_list": self.__que_list,
            "seconds": TimerDelay.SHANG_GA_TIME
        }
        data_model = S2CStartDingQueInfo.pb_model(**data)
        await self.inner_broadcast(CmdRoom.START_DING_QUE, data_model)
        self.set_flow_status(FlowStatus.T_IN_DING_QUE)

    async def start_tian_ting(self):
        self.log_info("开始天听")
        if self.flow_status not in (FlowStatus.T_IN_DEAL_CARDS, FlowStatus.T_IN_EXCHANGE_CARDS):
            return
        self.set_flow_status(FlowStatus.T_IN_TIAN_TING)
        self.clear_table_actions()
        self.curr_seat_id = self.dealer_id
        data = {
            "seconds": TimerDelay.TIAN_TING_SECONDS,
            "in_flow": self.flow_status,
            "left_count": self.poker.left_count,
        }
        for p in self.seats:
            if self.curr_seat_id == p.seat_id:
                self.__curr_card = p.mo_pai
            if self.__four_card_bao_ting and p.cards_len < 13:
                continue
            data["operates"] = self.get_tian_ting_operates(p)
            data["seat_id"] = p.seat_id
            data_model = S2CPublicOperatesMahjong.pb_model(**data)
            await self.inner_send(p, CmdRoom.PUBLIC_OPERATES, data_model)

        if self.can_tian_ting():
            self.log_info("玩家可以操作天听")
            if not self.__decision_sec:
                return
            await self.deal_operates_call_time_out()
            return
        await self.check_tian_ting_enter_next()

    def get_tian_ting_operates(self, p):
        """获取玩家天听操作"""
        operates = []
        if p.seat_id == self.dealer_id:
            flag, gang_card_list = p.can_an_gang(Rule)
            if flag:
                operates.append(ActionType.ACTION_TYPE_AN_GANG)
            can_hu, _ = self.hu_de_qi(p)
            if can_hu:
                if p.cards_len == self.deal_cards_count + 1:
                    operates.append(ActionType.ACTION_TYPE_HU)
                    if self.play_type in (PlayType.JIAN_LOU_XUE_LIU, PlayType.AN_LONG_XUE_ZHAN):
                        operates.append(ActionType.ACTION_TYPE_TIAN_TING)
                else:
                    if not self.__bi_men_yi_shou:
                        operates.append(ActionType.ACTION_TYPE_HU)
                    operates.append(ActionType.ACTION_TYPE_MEN)
            else:
                operates.extend(self.calc_operates_in_tian_ting(p, True))
        else:
            operates.extend(self.calc_operates_in_tian_ting(p))
        if self.play_type in (PlayType.JIAN_LOU_XUE_LIU, PlayType.AN_LONG_XUE_ZHAN):
            if operates:
                self.__record_operates.setdefault(p.seat_id, []).append(ActionType.ACTION_TYPE_PASS)
                operates.append(ActionType.ACTION_TYPE_PASS)

        if ActionType.ACTION_TYPE_HU not in operates:
            p.operates = operates
        else:
            # 能天胡，也把能报听存到玩家对象，只是不下发
            operates_copy = operates[:]
            operates_copy.append(ActionType.ACTION_TYPE_TIAN_TING)
            p.operates = operates_copy
        return operates

    async def tian_ting_time_out(self):
        if self.flow_status == FlowStatus.T_IN_TIAN_TING:
            return
        for p in self.seats:
            if p.can_tian_ting == -1:
                continue
            if ActionType.ACTION_TYPE_TIAN_TING in p.operates:
                await self.do_trustee(p)
                code = await self.on_player_pass(p)
                if code != 0:
                    if ActionType.ACTION_TYPE_TIAN_TING in p.operates:
                        p.remove_operates(ActionType.ACTION_TYPE_TIAN_TING)
                    one_of_model = s2c_one_of_model()
                    one_of_model.seat_id = self.curr_seat_id
                    await self.inner_send(p, CmdRoom.PLAYER_PASS, one_of_model)

        await self.enter_mo_pai_call()

    async def check_tian_ting_enter_next(self):
        if self.flow_status != FlowStatus.T_IN_TIAN_TING:
            return
        is_all_tian_ting = True
        have_eight_hu = False
        for p in self.seats:
            if len(p.men_cards) > 0:
                have_eight_hu = True
            if p.can_tian_ting >= 0 and ActionType.ACTION_TYPE_TIAN_TING in p.operates:  # 还有能天听的玩家且没有选择过
                is_all_tian_ting = False
                break
        if is_all_tian_ting:
            if have_eight_hu:
                self.call_flow(2, self.enter_mo_pai_call)
            else:
                await self.enter_mo_pai_call()
            return

    def hu_de_qi(self, player: Player, hu_type=1):
        if hu_type == 0 and player != self.curr_player:
            return False, {}
        can_hu, _, hu_info = self.player_can_hu(player)
        return can_hu, hu_info

    def calc_operates_in_tian_ting(self, p: Player, dealer=False):
        result = []
        if not p:
            return result
        if not dealer:
            if self.can_select_tian_ting(p, self.deal_cards_count):
                result.append(ActionType.ACTION_TYPE_TIAN_TING)
        else:
            if self.can_select_tian_ting(p, self.deal_cards_count + 1):
                result.append(ActionType.ACTION_TYPE_TIAN_TING)
        if result:
            result.append(ActionType.ACTION_TYPE_PASS)
        return result

    def can_select_tian_ting(self, p: Player, cards_len):
        if p.cards_len != cards_len:
            return False
        is_zy = self.play_type == PlayType.ZUN_YI_LAI_ZI
        allow_hu_map = {HuType.DI_LONG_QI: self.__di_long_qi, HuType.JIN_GOU_DIAO: True,
                        HuType.QI_DUI: True, HuType.FOUR_CARD_NO_NEAR: self.__four_card_no_near,
                        HuType.FOUR_CARD_IS_SAME: self.__four_card_tian_hu}
        if cards_len == self.deal_cards_count and p.chu_pai_len() == 0 and p.can_tian_ting >= 0:
            if Rule.r_can_tian_ting(p.table_cards, p.cards, p.que, allow_hu_map, is_zy, self.__lai_zi):
                return True
        if cards_len == self.deal_cards_count + 1 and p.table_cards_len() == 0 and p.chu_pai_len() == 0 and p.can_tian_ting >= 0:
            if Rule.r_can_tian_ting(p.table_cards, p.cards, p.que, allow_hu_map, is_zy, self.__lai_zi):
                return True

        return False

    def player_can_hu(self, player):
        """
        首先判断手牌能不能胡
        其次判断玩家此时能不能胡（平胡不能直接胡）

        主要判断玩家平胡不能点炮
        """
        info, can_hu, hu_path = self.get_hu_type(player, only_calc_hu=True)
        if not can_hu:
            return False, [], {}
        return self.check_can_hu(player, can_hu, info, hu_path)

    def check_can_hu(self, player, can_hu, info, hu_path=None):
        if hu_path is None:
            hu_path = []
        if player.que > 0:
            for t_card in player.cards:
                if t_card // 10 == player.que:
                    return False, [], False
        is_zi_mo = info["is_zi_mo"]
        hu_type = info["hu_type"]
        if not is_zi_mo:
            if hu_type != HuType.PING_HU:  # 其他类型都可接炮
                return can_hu, hu_path, info
            # 可接炮类型 抢杠胡  杠上炮 有杠 有闷过
            if len(player.men_cards) > 0:
                return can_hu, hu_path, info
            if player.check_has_permit() and not player.shao_tong_xing_zheng:
                return can_hu, hu_path, info
            if self.in_qiang_gang_hu_flow():
                return can_hu, hu_path, info
            # 杠上炮 先判断了自摸后才可以调
            if self.is_gang_shang_pao():
                return can_hu, hu_path, info
            if player.tian_ting:
                return can_hu, hu_path, info
            fang_pao_player = self.curr_player()
            if fang_pao_player and fang_pao_player.tian_ting:
                return can_hu, hu_path, info
            return False, [], False
        return can_hu, hu_path, info

    def in_qiang_gang_hu_flow(self):
        return self.flow_status in (FlowStatus.T_IN_MING_GANG_PAI_CALL, FlowStatus.T_IN_ZHUAN_WAN_GANG_PAI_CALL)

    def is_gang_shang_pao(self):
        return len(self.__gang_hou_chu_pai) > 0

    def get_hu_type(self, p: Player, dian_pao=False, only_calc_hu=False, lou=False):
        """
        此接口计算玩家手牌胡牌类型，玩家能不能胡不管
        params: dian_pao: 是否是计算点炮时的hu_type
        params: only_calc_hu: 仅仅计算是否能胡
        """
        # 1.额外分(与牌型无关, 天胡|地胡|天听|杀报|杠上花|抢杠胡|杠上炮)
        extra_fan = []
        is_zi_mo = self.curr_seat_id == p.seat_id
        if self.flow_status == FlowStatus.T_IN_EIGHT_TIAN_HU:
            is_zi_mo = True
        table_cards = p.table_cards
        hand_cards = list(p.cards)
        is_gy = self.play_type == PlayType.GUI_YANG_4
        is_wu_dui = self.play_type == PlayType.BI_JIE_MJ
        allow_hu_map = {HuType.QI_DUI: True, HuType.JIN_GOU_DIAO: not is_gy, HuType.DI_LONG_QI: self.__di_long_qi,
                        HuType.FOUR_CARD_NO_NEAR: self.__four_card_no_near,
                        HuType.FOUR_CARD_IS_SAME: self.__four_card_tian_hu}
        hu_type, hu_path = Rule.can_hu(table_cards, hand_cards, self.__curr_card, allow_hu_map, self.__lai_zi, is_gy,
                                       is_wu_dui)
        if not hu_type:
            return {}, False, []
        if hu_type == HuType.PING_HU and self.play_type == PlayType.REN_HUAI_MJ:
            hand_cards.remove(self.__curr_card)
            ting_list = Rule.get_ting_hu_list(table_cards, hand_cards, allow_hu_map, self.__lai_zi)
            if len(ting_list) == 3:
                if Rule.check_ting_list(ting_list):
                    hu_type = HuType.DA_KUAN_ZHANG

        # 地胡：第一轮接庄炮/自摸
        # 杀报(天听玩家未胡之前都可被杀报，只算一次，自己胡过或者被别人杀报过 后续则没有杀报)
        is_sha_bao = False
        bei_sha_bao_seats = []  # 被杀报者需要记录，因为如果是自摸，可能有一个可能有多个
        re_pao_score = 0  # 记录热炮分(杠上炮分后续不好计算，此处算好后面直接用)
        qiang_gang_score = 0  # 记录抢杠分(抢杠分后续不好计算，此处算好后面直接用)
        gang_card = []  # 记录抢杠|杠上炮时的杠，如果是默认鸡后续算分时需要+鸡的分

        if is_zi_mo:
            if len(self.__gang_hou_mo_pai) > 0:
                extra_fan.append(ExtraHuPai.GANG_SHANG_HUA)  # 杠上花

            if (
                    p.seat_id == self.dealer_id or self.flow_status == FlowStatus.T_IN_EIGHT_TIAN_HU) and not p.all_chu_cards and not p.men_cards:
                if p.tian_ting != 1:
                    if self.flow_status != FlowStatus.T_IN_EIGHT_TIAN_HU:
                        if hu_type == HuType.FOUR_CARD_IS_SAME:
                            extra_fan.append(ExtraHuPai.TIAN_HU_BY_FOUR_CARD)
                        else:
                            extra_fan.append(ExtraHuPai.TIAN_HU)  # 天胡(选择报听后则不能算天胡)

                if not only_calc_hu:
                    p.tian_hu = 1
                    if self.flow_status == FlowStatus.T_IN_EIGHT_TIAN_HU:
                        p.eight_card_tian_hu = 1
                    if hu_type != HuType.FOUR_CARD_IS_SAME and len(p.cards) != 8:
                        p.tian_ting = 1
                if hu_type == HuType.QI_DUI:
                    card_to_count = self.get_card_to_count(p)
                    # 起手是七对且手中有四张一样则判断为龙七对
                    if card_to_count and max(card_to_count.values()) == 4:
                        hu_type = HuType.LONG_QI_DUI

            for other_p in self.seats:
                if p.seat_id == other_p.seat_id:
                    continue
                if other_p.tian_ting > 0:
                    is_sha_bao = True  # 杀报
                    bei_sha_bao_seats.append(other_p.seat_id)
        else:
            if self.flow_status_is_equal(FlowStatus.T_IN_ZHUAN_WAN_GANG_PAI_CALL):
                gang = ActionType.ACTION_TYPE_ZHUAN_WAN_GANG
                gang_card = [[gang, self.__curr_card]]

                qiang_gang_score += self.cal_score_by_gang_shang_pao(gang)
                extra_fan.append(ExtraHuPai.QIANG_GANG_HU)  # 抢杠胡(烧鸡烧杠)
                if not only_calc_hu and not lou:
                    dian_pao and self.__shao_ji_gang_seats.add(self.curr_seat_id)
                    curr_p = self.curr_player()
                    curr_p and curr_p.set_shao_txz()

            if len(self.__gang_hou_chu_pai) > 0:
                gang_card = self.__gang_hou_chu_pai[::]
                for gang in self.__gang_hou_chu_pai:
                    re_pao_score += self.cal_score_by_gang_shang_pao(gang[0])

                extra_fan.append(ExtraHuPai.GANG_SHANG_PAO)  # 杠上炮(烧鸡烧杠)
                if not only_calc_hu and not lou:
                    dian_pao and self.__shao_ji_gang_seats.add(self.curr_seat_id)
                    curr_p = self.curr_player()
                    curr_p and curr_p.set_shao_txz()

            curr_p = self.curr_player()
            if curr_p.tian_ting > 0:
                bei_sha_bao_seats.append(curr_p.seat_id)
                is_sha_bao = True  # 杀报

        if p.tian_ting > 0:
            if ExtraHuPai.TIAN_HU not in extra_fan and ExtraHuPai.DI_HU not in extra_fan:
                extra_fan.append(ExtraHuPai.TIAN_TING)

        if is_sha_bao:
            if ExtraHuPai.TIAN_HU not in extra_fan or p.cards_len != self.deal_cards_count + 1:  # 庄起手的14张天胡，闲家报听无效则无杀报
                extra_fan.append(ExtraHuPai.SHA_BAO)

        if self.play_type == PlayType.AN_SHUN_MJ and self.poker.left_count <= const.LIU_JU_COUNT:
            extra_fan.append(ExtraHuPai.SEA_MOON)

        qing_upgrade_map = {
            HuType.QI_DUI: HuType.QING_QI_DUI,
            HuType.LONG_QI_DUI: HuType.QING_LONG_BEI,
            HuType.DA_DUI_ZI: HuType.QING_DA_DUI,
            HuType.DI_LONG_QI: HuType.QING_DI_LONG,
            HuType.JIN_GOU_DIAO: HuType.QING_JIN_GOU,
            HuType.DA_KUAN_ZHANG: HuType.QING_DA_KUAN_ZHANG
        }
        is_qing_yi_se = Rule.has_hu_is_qing_yi_se(p.table_cards, list(p.cards), self.__curr_card, self.__lai_zi)

        if is_qing_yi_se and hu_type != HuType.FOUR_CARD_IS_SAME:
            hu_type = qing_upgrade_map.get(hu_type, HuType.QING_YI_SE)
        result = {
            "card": p.cards[-1] if self.flow_status == FlowStatus.T_IN_EIGHT_TIAN_HU else p.mo_pai,
            "seat_id": p.seat_id,
            "is_zi_mo": is_zi_mo,
            "hu_type": hu_type,
            "extra_hu_type": extra_fan,
        }
        if p.eight_card_tian_hu:
            extra_hu_type = self.check_eight_card_tian_hu_type(hu_type)
            extra_fan.append(extra_hu_type)

        if is_sha_bao:
            result["bei_sha_bao_seats"] = bei_sha_bao_seats
        if not is_zi_mo:
            result["fang_pao_seat_id"] = self.curr_seat_id
            result["re_pao_score"] = re_pao_score
            result["qiang_gang_score"] = qiang_gang_score
            result["card"] = self.__curr_card
            result["gang_card"] = gang_card

        return result, True, hu_path

    @staticmethod
    def check_eight_card_tian_hu_type(hu_type):
        if hu_type == HuType.QING_YI_SE:
            return ExtraHuPai.TIAN_HU_BY_QING_YI_SE
        elif hu_type == HuType.QI_DUI:
            return ExtraHuPai.TIAN_HU_BY_QI_DUI
        elif hu_type == HuType.QING_QI_DUI:
            return ExtraHuPai.TIAN_HU_BY_QING_QI_DUI
        elif hu_type == HuType.DA_DUI_ZI:
            return ExtraHuPai.TIAN_HU_BY_DA_DUI_ZI
        elif hu_type == HuType.QING_DA_DUI:
            return ExtraHuPai.TIAN_HU_BY_QING_DA_DUI
        elif hu_type == HuType.LONG_QI_DUI:
            return ExtraHuPai.TIAN_HU_BY_LONG_QI_DUI
        elif hu_type == HuType.QING_LONG_BEI:
            return ExtraHuPai.TIAN_HU_BY_QING_LONG_QI
        else:
            return ExtraHuPai.TIAN_HU

    def cal_score_by_gang_shang_pao(self, gang):
        """
        处理杠上跑，勾选所得加一或不勾选的情况算分
        抢杠胡 | 杠上炮
        """
        if self.__suo_de_jia_one:
            score = self.__gang_score
            if gang == ActionType.ACTION_TYPE_ZHUAN_WAN_GANG:
                score *= (self.in_room_count - 1)
            elif gang == ActionType.ACTION_TYPE_AN_GANG:
                score *= (self.in_room_count - 1)
        else:
            score = self.extra_score_map.get(ExtraHuPai.GANG_SHANG_PAO)
        return score

    @staticmethod
    def get_card_to_count(p):
        card_to_count = {}
        for c in p.cards or []:
            card_to_count[c] = card_to_count.get(c, 0) + 1
        return card_to_count

    def find_target_exchange_cards_seat(self, player):
        for offset in range(1, self.max_player_count):
            target_seat_id = (player.seat_id - 1 + offset) % self.max_player_count
            target_player = self.seats[target_seat_id]
            if not target_player.tian_ting:
                return target_player

    @staticmethod
    def find_index_need_exchange_cards(player, ex_cards):
        """计算交换位置"""
        card_count = {}
        ex_cards.sort()
        for c in ex_cards:
            card_count[c] = card_count.get(c, 0) + 1
        ex_cards_index = []
        player.sort_cards()
        cards = player.cards.copy()
        for card, count in card_count.items():
            try:
                c_index = cards.index(card)
            except ValueError:
                return None
            if c_index + count - 1 >= len(cards):
                return None
            if cards.count(card) < count:
                return None
            ex_cards_index.append(c_index)
            for i in range(1, count):
                ex_cards_index.append(c_index + i)
            if len(ex_cards_index) == 3:
                return ex_cards_index

    async def round_start(self, **kwargs):
        """ 一局开始 """
        if self.room_status not in (RoomStatus.T_PLAYING, RoomStatus.T_DISMISS):
            return
        await super().round_start()
        self.set_flow_status(FlowStatus.T_IN_ROUND_START)
        self.dealer_turn()
        self.curr_seat_id = self.dealer_id
        self.clear_room_round_start()
        self.__dice_num = Rule.random_dice(2)
        data = {"round_idx": self.round_idx, "dealer": self.dealer_id, "dice_num": self.__dice_num}
        if self.play_type == PlayType.AN_SHUN_MJ and self.__lai_zi_ji:
            self.__lai_zi = random.choice(const.ALL_CARDS_WITHOUT_ZI_HUA)
            data["lai_zi_ji"] = self.__lai_zi

        data_model = S2CRoundStartMahjong.pb_model(**data)
        await self.inner_broadcast(CmdRoom.ROUND_START, data_model)
        self.log_info(self.tid, "round_start", self.__shang_ga, self.__default_ji)
        if self.__shang_ga:
            await self.force_set_gu_mai_score() if self.__gu_mai_score > 0 else self.call_flow(0.5,
                                                                                               self.start_player_shang_ga)
        else:
            self.call_flow(0.5, self.deal_cards)

    async def round_over(self, over_type=OverType.DEFAULT, **kwargs):
        is_force = kwargs.get("is_force", False)
        if is_force:
            over_type = OverType.FORCE
        self.get_player_jiao_pai()

        force_dismiss = over_type == OverType.FORCE
        if force_dismiss:
            account, zhuo_ji = self.dismiss_check_out()
        else:
            account, zhuo_ji = self.do_check_out(over_type)

        self.__over_type = over_type
        self.limit_lose_score(account)
        data = {
            "round_idx": self.round_idx,
            "has_next_round": self.has_next_round(),
            "seats": [],
            "finish_type": over_type,
            "curr_card": self.__curr_card,
            "dealer": self.dealer_id,
            "is_huang_zhuang": int(over_type == OverType.LIU_JU),
            "left_cards": self.poker.remain_cards,
            "fan_ji_card": zhuo_ji,  # 翻到的那张牌
            "all_ji": list(self.__ji_cards) if self.__ji_cards else [],
            "account": account,
        }
        await super().round_over(over_type, **data)

    def get_player_jiao_pai(self):
        allow_hu_map = {HuType.DI_LONG_QI: self.__di_long_qi, HuType.JIN_GOU_DIAO: True,
                        HuType.QI_DUI: True, HuType.FOUR_CARD_NO_NEAR: self.__four_card_no_near,
                        HuType.FOUR_CARD_IS_SAME: self.__four_card_tian_hu}
        is_gy = self.play_type == PlayType.GUI_YANG_4
        is_wu_dui = self.play_type == PlayType.BI_JIE_MJ
        for p in self.seats:
            if p:
                if p.seat_id in self.__win_seat_list:
                    p.lian_zhuang += 1
                else:
                    p.lian_zhuang = 0
                if self.__liang_men_pai == 0 and self.play_type in (PlayType.GUI_YANG_3, PlayType.GUI_YANG_2):
                    if p.que_count() > 0:
                        self.log_info(self.tid, p.uid, "玩家缺牌未打完", p.cards, p.que)
                        continue
                p.jiao_pai = Rule.get_round_over_jiao_pai(
                    p.table_cards, p.cards, allow_hu_map, is_gy=is_gy, lai_zi=self.__lai_zi, is_wu_dui=is_wu_dui)
                if p.seat_id not in self.__win_seat_list and self.flow_status == FlowStatus.T_IN_EIGHT_TIAN_HU:
                    p.jiao_pai = 0

    def limit_lose_score(self, account: dict):
        """ 限制输分 """
        if self.__limit_lose == 0:
            return
        lose_count = 0
        win_count = 0
        real_win = 0  # 真实赢的
        for _, acc in account.items():
            total_score = acc.get("total_score", 0)
            if total_score > 0:
                win_count += 1
                real_win += total_score
            elif total_score < 0:
                lose_count += 1

        if win_count == 0 and lose_count == 0:
            return

        # 计算最多能赢(即最多能输的)
        can_win = 0
        for _, acc in account.items():
            total_score = acc.get("total_score", 0)
            if total_score < 0:
                # 2家赢1家输
                if win_count == 2 and lose_count == 1:
                    if total_score < -self.__limit_lose * 2:
                        lose_limit = self.__limit_lose * 2  # 最多输封顶x2
                    else:
                        lose_limit = abs(total_score)
                else:
                    if total_score < -self.__limit_lose:
                        lose_limit = self.__limit_lose
                    else:
                        lose_limit = abs(total_score)  # 没到封顶就输自己携带的

                acc["total_score"] = -lose_limit
                can_win += lose_limit

        # 1人赢的情况（1v1 1v2）
        if win_count == 1:
            for _, acc in account.items():
                if acc.get("total_score", 0) > can_win:
                    acc["total_score"] = can_win
        else:
            record_info = {}
            if can_win < real_win:  # 当真实赢的大过能赢的
                for seat, acc in account.items():
                    total_score = acc.get("total_score", 0)
                    if total_score > 0:
                        total_score = int(can_win * (total_score / real_win))
                        record_info[seat] = total_score

                diff_score = can_win - sum(record_info.values())
                if diff_score != 0:
                    max_seat = max(record_info, key=record_info.get)
                    record_info[max_seat] += diff_score

                for seat, score in record_info.items():
                    account[seat]["total_score"] = score

    def dismiss_check_out(self):
        deal_cards = False  # 表示是否已发过牌(未发牌则不翻鸡)
        for p in self.seats:
            if not p:
                continue
            if p.cards:
                deal_cards = True
            p.on_round_over(0)
        bird_info = self.zhong_bird()
        return {}, 0 if not deal_cards else bird_info[0]

    def zhong_bird(self):
        """ 翻鸡 """
        bird_list = []
        for i in range(self.__bird_count):
            if self.poker.left_count > 0:
                bird_list.append(self.poker.pop())
            else:
                break
        return bird_list

    def do_check_out(self, over_type=OverType.DEFAULT):
        """
        捡漏房卡场结算，此处只管开牌与黄庄的情况
        黄庄结算与开牌结算分开，遵循单一职责原则
        return: accounts, zhuo_ji
        """
        # 当三位玩家全部诈胡时记作”合局“三位玩家之间不产生赔付。
        accounts = {}
        is_liu_ju = over_type == OverType.LIU_JU

        # 检查是否和局
        if self.__do_check_out_draw(accounts, is_liu_ju):
            bird_list = self.zhong_bird()
            return accounts, bird_list[0] if bird_list else 0

        # 流胡或胡开
        if is_liu_ju:
            return self.liu_ju_check_out(accounts), 0
        return self.kai_pai_check_out(accounts)

    def __do_check_out_draw(self, accounts, is_liu_ju=False):
        """
        处理平局的情况
        所有玩家均炸胡，此局为和局
        流局时: 所有玩家未叫牌或都叫牌,此局为和局
        """
        zha_hu_count = 0
        for p in self.seats:
            if p.is_zha_hu:
                zha_hu_count += 1
        if zha_hu_count == self.max_player_count:
            return True

        if is_liu_ju:
            no_jiao_count = 0
            jiao_count = 0
            for p in self.seats:
                if p.is_zha_hu:
                    continue
                if p.jiao_pai:
                    jiao_count += 1
                else:
                    no_jiao_count += 1
            if no_jiao_count == self.max_player_count:
                return True
            if jiao_count == self.max_player_count:
                if self.__huang_zhuang_bu_huang_ji:
                    self.check_chong_feng_ji(accounts, liu_ju=True)
                    self.check_ze_ren_ji(accounts, liu_ju=True)
                    self.check_ji(accounts, is_bao=False, liu_ju=True)
                    self.check_gang(accounts, is_bao=False, liu_ju=True)
                return True
        return False

    def check_chong_feng_ji(self, accounts, liu_ju=False, is_bao=False):
        """
        结算冲锋鸡
        炸胡者要承担未炸胡者的分
        """
        # 3.1 冲锋鸡
        if not self.__chong_feng_ji:
            return
        if self.__chong_feng_ji_seat_id != 0 and self.__record_cfj != 1:
            ji_card = CardsType.YAO_JI
            key = JiType.CHONG_FENG_JI
            if CardsType.YAO_JI in self.__fan_jin_ji_cards and self.play_type > 2:
                key = JiType.CHONG_FENG_JIN_JI
            score = self.__ji_pai_score.get(key, 0)
            self.__ji_and_gang_score += score
            self.concreteness_check_chong_feng_ji(accounts, score, ji_card, self.__chong_feng_ji_seat_id, liu_ju,
                                                  is_bao)

        if self.__cfwgj_seat_id != 0 and self.__record_cfwgj != 1:
            ji_card = CardsType.WU_GU_JI
            key = JiType.WU_GU_CFJ
            if CardsType.WU_GU_JI in self.__fan_jin_ji_cards and self.play_type > 2:
                key = JiType.WU_GU_CF_JIN_JI
            score = self.__ji_pai_score.get(key, 0)
            self.__ji_and_gang_score += score
            self.concreteness_check_chong_feng_ji(accounts, score, ji_card, self.__cfwgj_seat_id, liu_ju, is_bao)

    def check_ze_ren_ji(self, accounts, liu_ju=False, is_bao=False):
        """ 结算责任鸡 """
        # 3.2 责任鸡(责任鸡无金鸡一说，额外算分)
        if not self.__ze_ren_ji:
            return
        ze_ren_ji_score, ze_ren_wgj_score = self.get_ze_ren_ji_score()
        if self.__ze_ren_ji_seat_id != 0 and self.__ze_ren_ji_win_seat_id != 0:
            ji_card = CardsType.YAO_JI
            self.concreteness_check_ze_ren_ji(
                accounts, self.__ze_ren_ji_win_seat_id, self.__ze_ren_ji_seat_id, ji_card, ze_ren_ji_score, liu_ju,
                is_bao)

        if self.__ze_ren_wgj_seat_id != 0 and self.__ze_ren_wgj_win_seat_id != 0:
            ji_card = CardsType.WU_GU_JI
            self.concreteness_check_ze_ren_ji(
                accounts, self.__ze_ren_wgj_win_seat_id, self.__ze_ren_wgj_seat_id, ji_card, ze_ren_wgj_score, liu_ju,
                is_bao)

    def get_ze_ren_ji_score(self):
        """ 获取责任鸡分"""
        if CardsType.YAO_JI in self.__fan_jin_ji_cards and self.play_type > 2:  # 翻到为金鸡
            score = self.__ji_pai_score.get(JiType.CHONG_FENG_JIN_JI, 0)
            score -= self.__ji_pai_score.get(JiType.JIN_JI, 0)  # 翻到金鸡，在冲分的基础上减去一个金鸡，后续算碰的金鸡
        else:
            score = self.__ji_pai_score.get(JiType.ZE_REN_JI, 0)

        if CardsType.WU_GU_JI in self.__fan_jin_ji_cards and self.play_type > 2:
            wgj_score = self.__ji_pai_score.get(JiType.WU_GU_CF_JIN_JI, 0)
            wgj_score -= self.__ji_pai_score.get(JiType.WU_GU_JIN_JI, 0)
        else:
            wgj_score = self.__ji_pai_score.get(JiType.WU_GU_ZRJ, 0)
        ze_ren_ji_score = score
        ze_ren_wgj_score = wgj_score
        return ze_ren_ji_score, ze_ren_wgj_score

    def check_ji(self, accounts, is_bao=True, liu_ju=False):
        """ 结算鸡分 """
        if liu_ju and self.play_type > 2:
            return
        double_bao = self.__double_bao and is_bao
        fan_bird_list = self.__ji_cards.copy() if self.__ji_cards else set()
        type_ = CheckType.CHECK_JI
        if self.__wind_ji and self.__zhuo_ji_card == 35:
            type_ = CheckType.WIND_JI
        for p in self.seats:
            if p.jiao_pai <= 0 or p.is_zha_hu:
                continue
            if p.seat_id in self.__shao_ji_gang_seats:
                continue
            p.calc_all_ji_pai(self.__default_ji, fan_bird_list, self.__man_tang_ji,
                              week_ji=self.__week_ji_num)  # 计算玩家有几个鸡牌
            p_ji_cards = p.ji_pai[:]  # list
            p_stand_ji = p.calc_stand_ji(self.__default_ji)
            p_pg_ji = p.calc_peng_gang_ji(self.__default_ji)  # 除暗杠外的碰杠鸡
            # 冲锋鸡之前算过 -1
            self.remove_player_ji_card(p_ji_cards, p)
            if not p_ji_cards:
                continue
            bearer, get_bearer = self.zha_hu_bear_no_zha_hu(p)
            # 如果流局,未勾选黄庄不黄鸡杠，叫牌与叫牌玩家不结算
            if liu_ju:
                if not bearer:
                    bearer, get_bearer = self.no_jiao_bear_jiao(p)  # 有2人都没叫牌的情况，所以下面还要判断下

            ji_card_count = self.cal_card_count(p_ji_cards)
            stand_ji_card_count = self.cal_card_count(p_stand_ji)
            pg_ji_card_count = self.cal_card_count(p_pg_ji)

            for ji, count in ji_card_count.items():
                score = 0
                if ji in self.__default_ji:
                    # 金鸡 x2
                    bei_lv = 1
                    if ji in self.__fan_jin_ji_cards:
                        bei_lv = 2
                        pg_ji_count = pg_ji_card_count.get(ji, 0)  # 碰杠鸡
                        if pg_ji_count > 0:
                            count -= pg_ji_count  # 减去碰杠的金鸡
                            score = self.__ji_pai_score.get(ji, 1) * pg_ji_count * 2  # 金鸡 x 2

                    # 站鸡 x2
                    if self.__zhan_ji:
                        stand_ji_count = stand_ji_card_count.get(ji, 0)
                        if stand_ji_count > 0:
                            count -= stand_ji_count
                            # x2是站鸡翻倍
                            score += self.__ji_pai_score.get(ji, 1) * stand_ji_count * bei_lv * 2
                    if self.__week_ji_num and ji in self.__week_ji_num:
                        score *= 2
                    if self.__ruan_ying_ji:
                        score *= 2
                if bearer:
                    # x2是炸胡者承担2份
                    if ji == CardsType.WU_GU_JI and ji not in self.__default_ji:
                        score = (score + count) * 2
                    else:
                        score = (score + self.__ji_pai_score.get(ji, 1) * count) * 2

                    if double_bao:
                        score *= 2

                    self.update_score(type_, p.seat_id, bearer.seat_id, -score, ji, accounts, get_bearer.seat_id)
                else:
                    per_score = self.check_extra_ji(ji, score, count)
                    if self.week_ji and ji in self.fan_yin_ji_cards:
                        ji_type = CheckType.WEEK_JI
                    else:
                        ji_type = type_
                    win_total = 0
                    win_from = []
                    for other_p in self.seats:
                        if p.seat_id == other_p.seat_id:
                            continue
                        if liu_ju and other_p.jiao_pai > 0 and not self.__huang_zhuang_bu_huang_ji:
                            continue
                        if double_bao:
                            per_score *= 2

                        other_data = self.other_ming_xi_data(ji_type, p.seat_id, -per_score, ji)
                        self.update_result_score(accounts, other_p.seat_id, 0, other_data)
                        win_total += per_score
                        win_from.append(other_p.seat_id)

                    if self.__ruan_ying_ji:
                        win_total *= 2
                    self_data = self.self_ming_xi_data(type_, win_from, win_total, ji)
                    self.update_result_score(accounts, p.seat_id, 1, self_data)

    def remove_player_ji_card(self, p_ji_cards, p: Player):
        if self.__chong_feng_ji_seat_id != 0 and self.__chong_feng_ji_seat_id == p.seat_id:
            if CardsType.YAO_JI in p_ji_cards:
                p_ji_cards.remove(CardsType.YAO_JI)
        if self.__cfwgj_seat_id != 0 and self.__cfwgj_seat_id == p.seat_id:
            if CardsType.WU_GU_JI in p_ji_cards:
                p_ji_cards.remove(CardsType.WU_GU_JI)

    def check_extra_ji(self, ji, score, count):
        if ji == CardsType.WU_GU_JI and ji not in self.__default_ji:
            per_score = score + count
        else:
            per_score = score + self.__ji_pai_score.get(ji, 1) * count
        return per_score

    def check_gang(self, accounts, is_bao=True, liu_ju=False):
        """ 结算杠 """
        double_bao = self.__double_bao and is_bao
        for p in self.seats:
            if p.jiao_pai <= 0 or p.is_zha_hu:
                continue
            if p.seat_id in self.__shao_ji_gang_seats:
                continue
            mg_count = ag_count = zwg_count = 0  # 明杠/暗杠/转弯杠数量
            for data in p.table_cards:
                if data[0] == ActionType.ACTION_TYPE_AN_GANG:
                    ag_count += 1
                elif data[0] == ActionType.ACTION_TYPE_MING_GANG:
                    mg_count += 1
                elif data[0] == ActionType.ACTION_TYPE_ZHUAN_WAN_GANG:
                    zwg_count += 1
            # 减去憨包豆
            if self.play_type != PlayType.ZUN_YI_LAI_ZI:
                ag_count = ag_count - p.han_bao_dou_an_gang_count
                zwg_count = zwg_count - p.han_bao_dou_zhuan_wan_gang_count

            gang_score = self.__gang_score
            bearer, get_bearer = self.zha_hu_bear_no_zha_hu(p)
            if liu_ju:
                if not bearer:
                    # 流局没有人包且未勾选黄庄不黄鸡杠（不算鸡杠）
                    bearer, get_bearer = self.no_jiao_bear_jiao(p)

            if mg_count > 0:
                for data in p.table_cards:
                    if data[0] != ActionType.ACTION_TYPE_MING_GANG:
                        continue
                    card = data[1]
                    pei_seat = data[-1]
                    type_ = CheckType.CHECK_MING_GANG
                    per_score = gang_score
                    if double_bao:
                        per_score *= 2

                    if bearer and bearer.seat_id != pei_seat:
                        self.update_score(type_, p.seat_id, bearer.seat_id, -per_score, card, accounts,
                                          get_bearer.seat_id)
                    else:
                        pei_p = self.get_player_by_seat_id(pei_seat)
                        if liu_ju and pei_p and pei_p.jiao_pai > 0 and not self.__huang_zhuang_bu_huang_ji:
                            continue
                        if self.__ruan_ying_dou:
                            per_score *= 2
                        self.update_score(type_, p.seat_id, pei_seat, -per_score, card, accounts)

            if ag_count > 0 or zwg_count > 0:
                for data in p.table_cards:
                    act = data[0]
                    if act not in (ActionType.ACTION_TYPE_ZHUAN_WAN_GANG, ActionType.ACTION_TYPE_AN_GANG):
                        continue
                    card = data[1]
                    if self.play_type != PlayType.ZUN_YI_LAI_ZI:
                        if card in p.han_dou_cards:
                            continue

                    if act == ActionType.ACTION_TYPE_ZHUAN_WAN_GANG:
                        type_ = CheckType.CHECK_SUO_GANG
                    else:
                        type_ = CheckType.CHECK_AN_GANG

                    if bearer:
                        score = gang_score * 2  # 承担自己+未炸胡玩家

                        per_score = score
                        if double_bao:
                            per_score *= 2
                        self.update_score(type_, p.seat_id, bearer.seat_id, -per_score, card, accounts,
                                          get_bearer.seat_id)
                    else:
                        win_total = 0
                        win_from = []
                        for other_p in self.seats:
                            if p.seat_id == other_p.seat_id:
                                continue
                            if liu_ju and other_p.jiao_pai > 0 and not self.__huang_zhuang_bu_huang_ji:
                                continue

                            per_score = gang_score
                            if double_bao:
                                per_score *= 2

                            if self.__ruan_ying_dou:
                                per_score *= 2

                            other_data = self.other_ming_xi_data(type_, p.seat_id, -per_score, card)
                            self.update_result_score(accounts, other_p.seat_id, 0, other_data)
                            win_total += per_score
                            win_from.append(other_p.seat_id)

                        self_data = self.self_ming_xi_data(type_, win_from, win_total, card)
                        self.update_result_score(accounts, p.seat_id, 1, self_data)

    def concreteness_check_chong_feng_ji(self, accounts, score, card, cfj_seat_id, liu_ju, is_bao):
        """
        具体处理冲锋鸡的分
        炸胡者除了不赔付给炸胡者，其余都需要赔付
        炸胡者原本能够得到的收益则不能再有
        正常胡牌时，若冲锋鸡玩家炸胡，仍然要赔未听牌玩家
        """
        type_ = CheckType.CHECK_CHONG_FENG_JI
        if self.__wind_ji and self.__zhuo_ji_card == 35:
            type_ = CheckType.WIND_JI
        p = self.get_player_by_seat_id(cfj_seat_id)
        if p.seat_id in self.__shao_ji_gang_seats:
            return

        if self.__double_bao and is_bao and liu_ju:
            score *= 2

        if p.is_zha_hu:
            # type_ = CheckType.CHECK_ZE_REN_JI  # 炸胡或未叫牌变成责任鸡计算
            win_from = []
            total_score = 0
            for other_p in self.seats:
                if other_p.seat_id == p.seat_id:
                    continue
                if other_p.is_zha_hu or (liu_ju and other_p.jiao_pai <= 0):
                    continue
                win_from.append(other_p.seat_id)
                other_data = self.other_ming_xi_data(type_, cfj_seat_id, score, card)
                self.update_result_score(accounts, other_p.seat_id, 0, other_data)
                total_score += score

            self_data = self.self_ming_xi_data(type_, win_from, -total_score, card)
            self.update_result_score(accounts, cfj_seat_id, 1, self_data)
        else:
            # todo: 叫牌及未被烧鸡才能收包鸡的分！！！
            bearer, get_bearer = self.zha_hu_bear_no_zha_hu(p)
            if p.jiao_pai > 0:
                if liu_ju:
                    if not bearer:
                        bearer, get_bearer = self.no_jiao_bear_jiao(p)
                    # return  # 流局不算鸡
                if bearer:
                    # 当有炸胡者时，需要承担另一名玩家
                    score *= 2
                    self.update_score(type_, cfj_seat_id, bearer.seat_id, -score, card, accounts, get_bearer.seat_id)
                else:
                    win_from = []
                    total_score = 0
                    if self.__ruan_ying_ji:
                        score *= 2
                    for other_p in self.seats:
                        if other_p.seat_id == p.seat_id:
                            continue
                        win_from.append(other_p.seat_id)
                        other_data = self.other_ming_xi_data(type_, cfj_seat_id, -score, card)
                        self.update_result_score(accounts, other_p.seat_id, 0, other_data)
                        total_score += score
                    self_data = self.self_ming_xi_data(type_, win_from, total_score, card)
                    self.update_result_score(accounts, cfj_seat_id, 1, self_data)
            else:
                # 冲锋鸡玩家未炸胡+未听牌包鸡，炸胡者承担冲锋鸡玩家
                if bearer and get_bearer.jiao_pai > 0:
                    self.update_score(type_, get_bearer.seat_id, bearer.seat_id, -score, card, accounts,
                                      get_bearer.seat_id)
                else:
                    win_from = []
                    total_score = 0
                    for other_p in self.seats:
                        if other_p.seat_id == cfj_seat_id:
                            continue
                        if other_p.is_zha_hu or other_p.jiao_pai <= 0:
                            continue
                        # 包给叫牌玩家
                        win_from.append(other_p.seat_id)
                        other_data = self.other_ming_xi_data(type_, cfj_seat_id, score, card)
                        self.update_result_score(accounts, other_p.seat_id, 0, other_data)
                        total_score += score

                    self_data = self.self_ming_xi_data(type_, win_from, -total_score, card)
                    self.update_result_score(accounts, cfj_seat_id, 1, self_data)

    def concreteness_check_ze_ren_ji(self, accounts, ze_ren_win, ze_ren_lose, card, score, liu_ju, is_bao):
        """
        具体处理责任鸡算分
        责任鸡玩家：A，得到责任鸡玩家：B
        AB均炸胡，则都不赔付
        流局，A炸胡，B未听牌，则都不赔付
        """
        type_ = CheckType.CHECK_ZE_REN_JI
        if self.__wind_ji and self.__zhuo_ji_card == 35:
            type_ = CheckType.WIND_JI
        get_zrj_p = self.get_player_by_seat_id(ze_ren_win)
        if get_zrj_p.seat_id in self.__shao_ji_gang_seats:
            return

        if self.__double_bao and is_bao and liu_ju:
            score *= 2

        lose_zrj_p = self.get_player_by_seat_id(ze_ren_lose)
        if get_zrj_p.is_zha_hu:
            if lose_zrj_p.is_zha_hu or (liu_ju and lose_zrj_p.jiao_pai <= 0):
                return
            self.update_score(type_, ze_ren_win, ze_ren_lose, score, card, accounts)
        else:
            bearer, get_bearer = self.zha_hu_bear_no_zha_hu(get_zrj_p)
            if get_zrj_p.jiao_pai > 0:
                if liu_ju:
                    if not bearer:
                        bearer, get_bearer = self.no_jiao_bear_jiao(get_zrj_p)
                    # return
                pei_seat = ze_ren_lose
                get_bearer_seat = -1
                if bearer and bearer.seat_id != ze_ren_lose:  # 承担者为炸胡者非责任人
                    pei_seat = bearer.seat_id
                    get_bearer_seat = ze_ren_lose  # 获得承担者
                else:
                    pei_p = self.get_player_by_seat_id(pei_seat)
                    if liu_ju and pei_p and pei_p.jiao_pai > 0 and not self.__huang_zhuang_bu_huang_ji:
                        return
                self.update_score(type_, ze_ren_win, pei_seat, -score, card, accounts, get_bearer_seat)
            else:
                # 责任鸡玩家需要叫牌且未炸胡才能得到赔分
                if lose_zrj_p.jiao_pai > 0 and not lose_zrj_p.is_zha_hu:
                    pei_seat = ze_ren_win
                    get_bearer_seat = -1
                    if bearer:
                        pei_seat = bearer.seat_id
                        get_bearer_seat = ze_ren_win

                    other_data = self.other_ming_xi_data(type_, ze_ren_win, score, card)
                    self_data = self.self_ming_xi_data(type_, [ze_ren_lose], -score, card, get_bearer=get_bearer_seat)
                    self.update_result_score(accounts, ze_ren_lose, 0, other_data)
                    self.update_result_score(accounts, pei_seat, 1, self_data)

    def liu_ju_check_out(self, accounts: dict):
        """ 3人流局结算 """
        self.kai_hu_cha_jiao(accounts)
        # 1.流局查叫算分(牌型分)
        # 外循环控制叫牌且未炸胡玩家，内循环控制炸胡或未叫牌玩家
        no_zha_hu_and_jiao_players = []  # 未炸胡且叫牌玩家
        no_jiao_player = []
        zha_hu_player = []
        for p in self.seats:
            if p.is_zha_hu > 0:
                zha_hu_player.append(p.seat_id)
            elif p.jiao_pai <= 0:
                no_jiao_player.append(p.seat_id)
            else:
                no_zha_hu_and_jiao_players.append(p.seat_id)  # 叫牌且未炸胡

        if 0 < len(no_zha_hu_and_jiao_players) < self.max_player_count:
            flag = False  # 表示是否同时存在炸胡玩家和未叫牌玩家
            if zha_hu_player and no_jiao_player:
                flag = True
            for seat1 in no_zha_hu_and_jiao_players:
                p1 = self.get_player_by_seat_id(seat1)
                key = p1.jiao_pai
                score = self.pai_xing_score_map[key]
                type_ = CheckType.CHECK_LIU_JU_CHA_JIAO
                # 若有炸胡者和未听牌者
                if flag:
                    # 炸胡者承担未叫牌的查叫分
                    win_score = 0
                    one_score = score
                    if p1.tian_ting == 1:
                        if p1.jiao_pai == HuType.PING_HU:
                            one_score = self.pai_xing_score_map[HuType.QING_YI_SE]
                        else:
                            # 如果p叫大对子 + 报听，炸胡玩家包清一色 + 报听 = 双清
                            one_score += self.pai_xing_score_map[HuType.QING_YI_SE]

                    zha_hu_seat = zha_hu_player[0]
                    lose_data = self.other_ming_xi_data(type_, seat1, score=-one_score, get_bearer=no_jiao_player[0])
                    self.update_result_score(accounts, zha_hu_seat, 0, lose_data)
                    win_score += one_score

                    # 炸胡者自己承担>=清一色
                    is_gt, two_score = self.compare_pai_xing_is_big_qing_yi_se(key, score_map=self.pai_xing_score_map)
                    if p1.tian_ting == 1:
                        if p1.jiao_pai != HuType.PING_HU:
                            # 如果p叫大对子 + 报听，炸胡玩家包清一色 + 报听 = 双清
                            two_score += self.pai_xing_score_map[HuType.QING_YI_SE]

                    lose_data = self.other_ming_xi_data(type_, seat1, score=-two_score)
                    self.update_result_score(accounts, zha_hu_seat, 0, lose_data)
                    win_score += two_score

                    # 获得查叫分者
                    win_data = self.self_ming_xi_data(type_, [zha_hu_seat], score=win_score)
                    self.update_result_score(accounts, seat1, 1, win_data)
                else:
                    # 若只有炸胡者，则重新算包的分
                    if not no_jiao_player and zha_hu_player:
                        is_gt, score = self.compare_pai_xing_is_big_qing_yi_se(key, score_map=self.pai_xing_score_map)
                        if p1.tian_ting == 1:
                            if p1.jiao_pai != HuType.PING_HU:
                                score += self.pai_xing_score_map[HuType.QING_YI_SE]

                    pei_seats = no_jiao_player + zha_hu_player
                    for seat2 in pei_seats:
                        p2 = self.get_player_by_seat_id(seat2)
                        lose_data = self.other_ming_xi_data(type_, seat1, score=-score)
                        self.update_result_score(accounts, p2.seat_id, 0, lose_data)

                    win_data = self.self_ming_xi_data(type_, pei_seats, score * len(pei_seats))
                    self.update_result_score(accounts, seat1, 1, win_data)

        # 2.闷捡赔付：未叫牌玩家包闷/捡过的玩家分(外循环控制闷捡，内循环控制未叫牌玩家)
        self.check_men_jian(accounts, liu_ju=True)

        # 流局包鸡包杠？（荒庄时没有听牌的玩家碰杠的默认鸡，和打出的默认鸡要按相同分数给听牌玩家赔付）
        # 3.流局包鸡
        if self.__bao_ji:
            self.check_chong_feng_ji(accounts, liu_ju=True, is_bao=True)
            self.check_ze_ren_ji(accounts, liu_ju=True, is_bao=True)
            self.check_ji(accounts, liu_ju=True)
            self.bao_ji_check(accounts, True)

        # 4.流局包杠
        if self.__bao_gang:
            self.check_gang(accounts, liu_ju=True)
            self.bao_gang_check(accounts, liu_ju=True)

        return accounts

    def kai_pai_check_out(self, accounts: dict):
        """
        3人开牌结算
        统一数据结构
        """
        # 翻鸡
        if self.play_type != PlayType.ZUN_YI_LAI_ZI:
            self.__ji_cards, zhuo_ji = self.calc_fan_ji_cards()
        else:
            zhuo_ji = self.__zhuo_ji_card
        if self.play_type == PlayType.AN_LONG_XUE_ZHAN:
            self.kai_hu_cha_jiao(accounts)
        # 1.开牌牌型结算
        for hu_info in self.__kai_pai_hu_info:
            self.check_by_num_3(accounts, hu_info)
        # 2.结算闷捡
        self.check_men_jian(accounts)

        # 3.结算鸡分
        # 3.1 冲锋鸡
        self.check_chong_feng_ji(accounts)

        # 3.2 责任鸡(责任鸡无金鸡一说，额外算分)
        self.check_ze_ren_ji(accounts)

        # 3.3 翻鸡
        self.check_ji(accounts)

        # 4.结算杠分
        # 4.1 结算正常玩家的杠分
        self.check_gang(accounts)
        return accounts, zhuo_ji

    def calc_fan_ji_cards(self) -> tuple:
        """
        桌子层面
        根据翻的鸡计算出当前鸡牌
        这里计算之后不必再在玩家对象里面每个都计算一次
        return: set 集合互异性
        """
        fan_ji_set = set()
        if not self.__fan_ji_pai:
            return fan_ji_set, 0
        bird_list = self.zhong_bird()
        self.log_info("翻鸡牌", bird_list)
        for ji in bird_list:
            # 本鸡
            if self.__ben_ji:
                fan_ji_set.add(ji)
            # 上鸡
            if ji % 10 == 9:
                fan_ji_set.add(ji - 8)
                if ji // 10 == 2:
                    if self.play_type != PlayType.REN_HUAI_MJ or self.__jin_yin_wu:
                        self.__fan_jin_ji_cards.add(ji - 8)
                    self.log_info(self.tid, "翻到金鸡幺鸡")
                else:
                    if self.__yin_ji:
                        if self.play_type == PlayType.BI_JIE_MJ or self.__jin_yin_wu:
                            if ji // 10 == 3:
                                self.__fan_yin_ji_cards.add(ji - 8)
                        elif self.play_type != PlayType.REN_HUAI_MJ:
                            self.__fan_yin_ji_cards.add(ji - 8)
                        self.log_info(self.tid, "翻到银鸡", ji - 8)
            else:
                fan_ji_set.add(ji + 1)
                if ji + 1 == CardsType.WU_GU_JI:
                    self.__fan_jin_ji_cards.add(ji + 1)
                    self.log_info("翻到金鸡乌骨鸡")

            # 下鸡
            if self.__yao_bai_ji:
                if ji % 10 == 1:
                    fan_ji_set.add(ji + 8)
                else:
                    fan_ji_set.add(ji - 1)

        self.__zhuo_ji_card = bird_list[0] if bird_list else 0
        return fan_ji_set, bird_list[0] if bird_list else 0

    def kai_hu_cha_jiao(self, accounts: dict):
        """ 开胡查叫(炸胡包底分) """
        for p in self.seats:
            if not p.is_zha_hu:
                continue
            win_from = []
            win_score = 0
            type_ = CheckType.CHECK_KAI_HU_BAO
            key = p.jiao_pai or HuType.PING_HU  # p为炸胡者
            for other_p in self.seats:
                if p.seat_id == other_p.seat_id:
                    continue
                if other_p.is_zha_hu:
                    continue
                # other_p 为非炸胡者
                is_gt, score = self.compare_pai_xing_is_big_qing_yi_se(key, score_map=self.pai_xing_score_map)
                if p.tian_ting == 1:
                    if key != HuType.PING_HU:
                        # 如果p叫大对子 + 报听，炸胡玩家包清一色 + 报听 = 双清
                        score += self.pai_xing_score_map[HuType.QING_YI_SE]

                win_from.append(other_p.seat_id)
                win_score += score
                lose_data = self.other_ming_xi_data(type_, p.seat_id, score=score, hu_type=key)
                self.update_result_score(accounts, other_p.seat_id, 0, lose_data)

            # 获得查叫分者
            win_data = self.self_ming_xi_data(type_, win_from, score=-win_score, hu_type=key)
            self.update_result_score(accounts, p.seat_id, 1, win_data)

    def bao_ji_check(self, accounts, liu_ju=False):
        """
        结算包鸡
        只有炸胡/流局未听牌玩家需要包鸡
        是炸胡者/未听牌者出的分，外循环的p是出分者
        条件1：炸胡者不赔付已经被烧的鸡 todo
        """
        type_ = CheckType.CHECK_JI

        default_ji = self.__default_ji.copy()
        if self.play_type == PlayType.BI_JIE_MJ:
            for c in self.__fan_yin_ji_cards:
                default_ji.add(c)

        # 外循环为未叫牌/炸胡玩家
        for p in self.seats:
            if p.seat_id in self.__shao_ji_gang_seats:
                continue
            # 叫牌且未炸胡玩家不存在包杠
            if p.jiao_pai > 0 and not p.is_zha_hu:
                continue
            p.get_bao_ji(default_ji)  # 计算玩家有几个鸡牌
            p_ji_cards = p.ji_pai[:]  # list
            p_stand_ji = p.calc_stand_ji(default_ji)
            # 冲锋鸡之前算过 -1
            self.remove_player_ji_card(p_ji_cards, p)

            if not p_ji_cards:
                continue
            ji_card_count = self.cal_card_count(p_ji_cards)
            stand_ji_card_count = self.cal_card_count(p_stand_ji)
            # 未炸胡+未听牌包鸡
            # 若玩家炸胡，或者 未听牌且没有炸胡承担者，都需要自行赔付
            bearer, get_bearer = self.zha_hu_bear_no_zha_hu(p)
            bearer_seat_id = p.seat_id
            get_bearer_seat = -1
            if not p.is_zha_hu and bearer:
                bearer_seat_id = bearer.seat_id
                get_bearer_seat = p.seat_id

            for ji, count in ji_card_count.items():
                score = 0
                win_total = 0
                win_from = []

                per_score = self.get_per_score(ji, score, count, default_ji, liu_ju)

                for other_p in self.seats:
                    if other_p.seat_id == p.seat_id:
                        continue
                    if other_p.seat_id == bearer_seat_id:
                        continue
                    if other_p.is_zha_hu or not p.is_zha_hu and other_p.jiao_pai <= 0:
                        continue
                    if other_p.seat_id in self.__shao_ji_gang_seats:
                        continue
                    other_data = self.other_ming_xi_data(type_, bearer_seat_id, per_score, ji)
                    self.update_result_score(accounts, other_p.seat_id, 0, other_data)
                    win_total += per_score
                    win_from.append(other_p.seat_id)
                    # todo: 包鸡者未炸胡，但有人炸胡，炸胡者承担

                self_data = self.self_ming_xi_data(type_, win_from, -win_total, ji, get_bearer=get_bearer_seat)
                self.update_result_score(accounts, bearer_seat_id, 1, self_data)

    def get_per_score(self, ji, score, count, default_ji, liu_ju):
        if ji == CardsType.WU_GU_JI and ji not in default_ji:
            per_score = score + count
        else:
            per_score = score + self.__ji_pai_score.get(ji, 1) * count

        if self.__double_bao:
            per_score *= 2
        return per_score

    def bao_gang_check(self, accounts, liu_ju=False):
        """
        结算包杠
        """
        for p in self.seats:
            if self.play_type != PlayType.ZUN_YI_LAI_ZI:
                if p.seat_id in self.__shao_ji_gang_seats:
                    continue
            # 叫牌且未炸胡玩家不存在包杠
            if p.jiao_pai > 0 and not p.is_zha_hu:
                continue
            mg_count = ag_count = zwg_count = 0  # 明杠/暗杠/转弯杠数量
            for data in p.table_cards:
                if data[0] == ActionType.ACTION_TYPE_AN_GANG:
                    ag_count += 1
                elif data[0] == ActionType.ACTION_TYPE_MING_GANG:
                    mg_count += 1
                elif data[0] == ActionType.ACTION_TYPE_ZHUAN_WAN_GANG:
                    zwg_count += 1
            # 减去憨包豆
            if self.play_type != PlayType.ZUN_YI_LAI_ZI:
                ag_count = ag_count - p.han_bao_dou_an_gang_count
                zwg_count = zwg_count - p.han_bao_dou_zhuan_wan_gang_count

            # 算一个杠的分
            gang_score = self.__gang_score

            if p.is_zha_hu:
                if mg_count > 0:
                    type_ = CheckType.CHECK_MING_GANG
                    for data in p.table_cards:
                        if data[0] != ActionType.ACTION_TYPE_MING_GANG:
                            continue
                        pei_seat = data[-1]
                        if pei_seat in self.__shao_ji_gang_seats:
                            continue
                        pei_p = self.get_player_by_seat_id(pei_seat)
                        if pei_p.is_zha_hu:
                            continue
                        card = data[1]
                        per_score = gang_score
                        if self.__double_bao:
                            per_score *= 2

                        self.update_score(type_, p.seat_id, pei_seat, per_score, card, accounts)

                if zwg_count > 0 or ag_count > 0:
                    for data in p.table_cards:
                        act = data[0]
                        if act not in (ActionType.ACTION_TYPE_ZHUAN_WAN_GANG, ActionType.ACTION_TYPE_AN_GANG):
                            continue
                        card = data[1]
                        if self.play_type != PlayType.ZUN_YI_LAI_ZI:
                            if card in p.han_dou_cards:
                                continue

                        if act == ActionType.ACTION_TYPE_ZHUAN_WAN_GANG:
                            type_ = CheckType.CHECK_SUO_GANG
                        else:
                            type_ = CheckType.CHECK_AN_GANG

                        win_total = 0
                        win_from = []
                        for other_p in self.seats:
                            if other_p.seat_id == p.seat_id:
                                continue
                            if other_p.seat_id in self.__shao_ji_gang_seats:
                                continue
                            if other_p.is_zha_hu:
                                continue
                            per_score = gang_score
                            if self.__double_bao:
                                per_score *= 2

                            other_data = self.other_ming_xi_data(type_, p.seat_id, per_score, card)
                            self.update_result_score(accounts, other_p.seat_id, 0, other_data)
                            win_total += per_score
                            win_from.append(other_p.seat_id)

                        self_data = self.self_ming_xi_data(type_, win_from, -win_total, card)
                        self.update_result_score(accounts, p.seat_id, 1, self_data)
            else:
                if mg_count > 0:
                    type_ = CheckType.CHECK_MING_GANG
                    for data in p.table_cards:
                        if data[0] != ActionType.ACTION_TYPE_MING_GANG:
                            continue
                        pei_seat = data[-1]
                        if pei_seat in self.__shao_ji_gang_seats:
                            continue
                        pei_p = self.get_player_by_seat_id(pei_seat)
                        if pei_p.is_zha_hu or (liu_ju and pei_p.jiao_pai <= 0):
                            continue
                        card = data[1]
                        per_score = gang_score
                        if self.__double_bao:
                            per_score *= 2
                        bearer, get_bearer = self.zha_hu_bear_no_zha_hu(pei_p)
                        if bearer:
                            self.update_score(type_, bearer.seat_id, get_bearer.seat_id, per_score, card, accounts,
                                              get_bearer.seat_id)
                        else:
                            self.update_score(type_, p.seat_id, pei_seat, per_score, card, accounts)

                # 如果p未炸胡，则看有没有炸胡者为其承担赔付
                bearer, get_bearer = self.zha_hu_bear_no_zha_hu(p)
                if bearer:
                    if zwg_count > 0 or ag_count > 0:
                        for data in p.table_cards:
                            act = data[0]
                            if act not in (ActionType.ACTION_TYPE_ZHUAN_WAN_GANG, ActionType.ACTION_TYPE_AN_GANG):
                                continue
                            card = data[1]
                            if self.play_type != PlayType.ZUN_YI_LAI_ZI:
                                if card in p.han_dou_cards:
                                    continue

                            if act == ActionType.ACTION_TYPE_ZHUAN_WAN_GANG:
                                type_ = CheckType.CHECK_SUO_GANG
                            else:
                                type_ = CheckType.CHECK_AN_GANG

                            per_score = gang_score
                            if self.__double_bao:
                                per_score *= 2

                            self.update_score(type_, bearer.seat_id, get_bearer.seat_id, per_score, card, accounts,
                                              get_bearer.seat_id)
                else:
                    if zwg_count > 0 or ag_count > 0:
                        for data in p.table_cards:
                            act = data[0]
                            if act not in (ActionType.ACTION_TYPE_ZHUAN_WAN_GANG, ActionType.ACTION_TYPE_AN_GANG):
                                continue
                            card = data[1]
                            if self.play_type != PlayType.ZUN_YI_LAI_ZI:
                                if card in p.han_dou_cards:
                                    continue

                            if act == ActionType.ACTION_TYPE_ZHUAN_WAN_GANG:
                                type_ = CheckType.CHECK_SUO_GANG
                            else:
                                type_ = CheckType.CHECK_AN_GANG

                            win_total = 0
                            win_from = []
                            for other_p in self.seats:
                                if p.seat_id == other_p.seat_id:
                                    continue
                                if other_p.seat_id in self.__shao_ji_gang_seats:
                                    continue
                                if other_p.is_zha_hu or other_p.jiao_pai <= 0:
                                    continue
                                per_score = gang_score
                                if self.__double_bao:
                                    per_score *= 2

                                other_data = self.other_ming_xi_data(type_, p.seat_id, per_score, card)
                                self.update_result_score(accounts, other_p.seat_id, 0, other_data)
                                win_total += per_score
                                win_from.append(other_p.seat_id)

                            self_data = self.self_ming_xi_data(type_, win_from, -win_total, card)
                            self.update_result_score(accounts, p.seat_id, 1, self_data)

    @staticmethod
    def compare_pai_xing_is_big_qing_yi_se(hu_type, is_zi_mo=False, score_map=const.PAI_XING_SCORE_MAP):
        """
        牌型低于清一色算清一色，牌型高于清一色算实际牌型
        此接口只判断玩家牌型是否小于清一色
        """
        pai_xing_score = score_map.get(hu_type, 0)
        qing_yise_score = score_map.get(HuType.QING_YI_SE)
        flag = True
        if pai_xing_score < qing_yise_score:
            flag = False
            pai_xing_score = qing_yise_score
        if is_zi_mo:
            pai_xing_score *= 2
        return flag, pai_xing_score

    def check_men_jian(self, accounts: dict, liu_ju=False):
        """
        结算闷捡，流局和正常开牌统一为一个接口
        1.炸胡玩家以清一色为最低分赔付给正常玩家
        2.炸胡者之间不需要赔付
        3.玩家A未炸胡，玩家B炸胡，玩家C未炸胡，玩家A对BC的闷，B需要承担C赔付A的闷，捡也是
        4.流局时，若玩家之间 未炸胡 且 都叫牌 则彼此不用赔付
        注意：流局未叫牌一般是没有闷捡的，倘若未叫牌且有闷捡那一定是炸胡了
        """
        for men_info in self.__men_record:
            self.check_by_num_3(accounts, men_info, liu_ju=liu_ju)

    def check_by_num_3(self, accounts, hu_info, liu_ju=False):
        """
        处理3人胡牌|闷捡的结算，统一接口
        """
        card = hu_info.get("card")
        is_zi_mo = hu_info.get("is_zi_mo")
        seat_id = hu_info.get("seat_id")  # 闷捡者
        hu_type = hu_info.get("hu_type")
        extra_hu_lst = hu_info.get("extra_hu_type", [])
        check_type = hu_info.get("check_type")
        winner = self.get_player_by_seat_id(seat_id)

        if not is_zi_mo:
            pei_seat = hu_info.get("fang_pao_seat_id")
            fang_pao_p = self.get_player_by_seat_id(pei_seat)

            base_score = self.get_base_score(hu_info, extra_hu_lst)
            extra_score = self.cal_extra_hu_score(hu_info, extra_hu_lst, pei_seat)
            if winner.is_zha_hu:
                # if fang_pao_p.is_zha_hu or (liu_ju and fang_pao_p.jiao_pai <= 0):
                #     return
                if fang_pao_p.is_zha_hu:
                    return
                # 捡者炸胡
                pai_xing_score = base_score
                if pai_xing_score != 0:
                    _, pai_xing_score = self.compare_pai_xing_is_big_qing_yi_se(hu_type,
                                                                                score_map=self.pai_xing_score_map)
                total_score = pai_xing_score + extra_score
                self.update_score(check_type, seat_id, pei_seat, total_score, card, accounts, -1, hu_type, extra_hu_lst)
                # 估卖分
                if self.__shang_ga:
                    shang_ga_score = winner.shang_ga_score + fang_pao_p.shang_ga_score
                    check_type_ = CheckType.CHECK_GU_MAI  # 估卖
                    self.update_score(check_type_, seat_id, pei_seat, shang_ga_score, card, accounts)
            else:
                bearer, get_bearer = self.zha_hu_bear_no_zha_hu(winner)
                pai_xing_score = base_score
                # -- snip ---
                if liu_ju:
                    if not bearer:
                        if not fang_pao_p.is_zha_hu and fang_pao_p.jiao_pai > 0:
                            # 第三者承担
                            bearer, get_bearer = self.no_jiao_bear_jiao(winner)
                            if not bearer:
                                return
                # -- snip ---

                get_bearer_seat = -1
                if bearer:
                    # 若放炮者是炸胡玩家，承担清一色+，否则炸胡玩家承担另一名玩家的正常赔分
                    if bearer != fang_pao_p:
                        pei_seat = bearer.seat_id
                        get_bearer_seat = fang_pao_p.seat_id
                    else:
                        if base_score != 0:
                            is_gt, pai_xing_score = self.compare_pai_xing_is_big_qing_yi_se(hu_type,
                                                                                            score_map=self.pai_xing_score_map)

                total_score = pai_xing_score + extra_score
                self.update_score(check_type, seat_id, pei_seat, -total_score, card, accounts, get_bearer_seat, hu_type,
                                  extra_hu_lst)

                # 估卖分
                if self.__shang_ga:
                    shang_ga_score = winner.shang_ga_score + fang_pao_p.shang_ga_score
                    check_type_ = CheckType.CHECK_GU_MAI  # 估卖
                    self.update_score(check_type_, seat_id, pei_seat, -shang_ga_score, card, accounts, get_bearer_seat)

        else:
            # 闷牌算分
            total_score = 0
            total_gu_mai_score = 0
            if winner.is_zha_hu:
                # 闷牌者炸胡
                win_from = []
                for p in self.seats:
                    if p.seat_id == seat_id:
                        continue
                    if p.is_zha_hu:  # 双方都炸胡 或者 流局A炸胡B未听牌
                        continue
                    # 牌型包 >= 清一色
                    win_from.append(p.seat_id)
                    base_score = self.get_base_score(hu_info, extra_hu_lst, p.seat_id, True)
                    pai_xing_score = base_score
                    if pai_xing_score != 0:
                        _, pai_xing_score = self.compare_pai_xing_is_big_qing_yi_se(hu_type, True,
                                                                                    self.pai_xing_score_map)

                    per_score = pai_xing_score
                    per_score += self.cal_extra_hu_score(hu_info, extra_hu_lst, p.seat_id, is_zi_mo=True)

                    total_score += per_score
                    other_data = self.other_ming_xi_data(check_type, seat_id, per_score, card, hu_type, extra_hu_lst)
                    self.update_result_score(accounts, p.seat_id, 0, other_data)

                    if self.__shang_ga:
                        shang_ga_score = winner.shang_ga_score + p.shang_ga_score
                        total_gu_mai_score += shang_ga_score
                        check_type_ = CheckType.CHECK_GU_MAI  # 估卖
                        other_data = self.other_ming_xi_data(check_type_, seat_id, shang_ga_score, card)
                        self.update_result_score(accounts, p.seat_id, 0, other_data)

                self_data = self.self_ming_xi_data(check_type, win_from, -total_score, card, hu_type, extra_hu_lst)
                self.update_result_score(accounts, seat_id, 1, self_data)
                if self.__shang_ga:
                    check_type_ = CheckType.CHECK_GU_MAI  # 估卖
                    self_data = self.self_ming_xi_data(check_type_, win_from, -total_gu_mai_score, card)
                    self.update_result_score(accounts, seat_id, 1, self_data)
            else:
                # todo: 闷没有，需要添上
                status = self.detecting_player_status(winner)
                if liu_ju:
                    # 1.流局情况下
                    if status == PlayerStatusType.JIAO_2:  # 其余2个都叫牌
                        return
                    elif status == PlayerStatusType.ZHA_HU_AND_JIAO:  # 1个炸胡1个叫牌
                        self.check_zha_hu_bear_no_zha_hu(
                            winner, accounts, extra_hu_lst, hu_info, _type=check_type)
                    elif status == PlayerStatusType.ZHA_HU_AND_NO_JIAO:  # 1个炸胡1个未叫
                        self.check_zha_hu_bear_no_zha_hu(
                            winner, accounts, extra_hu_lst, hu_info, _type=check_type)
                        return
                    elif status == PlayerStatusType.JIAO_AND_NO_JIAO:  # 1个叫牌1个未叫

                        bearer, get_bearer = self.no_jiao_bear_jiao(winner)
                        base_score1 = self.get_base_score(hu_info, extra_hu_lst, bearer.seat_id, True)
                        base_score2 = self.get_base_score(hu_info, extra_hu_lst, get_bearer.seat_id, True)
                        total_score = base_score1 + base_score2

                        total_score += self.cal_extra_hu_score(hu_info, extra_hu_lst, bearer.seat_id, is_zi_mo=True)
                        total_score += self.cal_extra_hu_score(
                            hu_info, extra_hu_lst, get_bearer.seat_id, is_zi_mo=True)

                        pei_seat = bearer.seat_id
                        self.update_score(check_type, seat_id, pei_seat, total_score, card, accounts, -1, hu_type,
                                          extra_hu_lst)
                        if self.__shang_ga:
                            pei_p = self.get_player_by_seat_id(pei_seat)
                            shang_ga_score = winner.shang_ga_score * 2 + pei_p.shang_ga_score + get_bearer.shang_ga_score
                            check_type_ = CheckType.CHECK_GU_MAI  # 估卖
                            self.update_score(check_type_, seat_id, pei_seat, -shang_ga_score, card, accounts)

                    else:
                        # 统一处理均炸胡/均未听牌
                        self.__check_both_zha_hu_or_not(winner, accounts, extra_hu_lst, hu_info, _type=check_type)
                else:
                    # 当winner未炸胡，炸胡者需要承担其余
                    if status in (PlayerStatusType.ZHA_HU_AND_NO_JIAO, PlayerStatusType.ZHA_HU_AND_JIAO):
                        self.check_zha_hu_bear_no_zha_hu(
                            winner, accounts, extra_hu_lst, hu_info, _type=check_type)
                        return

                    # 其余两名玩家 均炸胡/均未炸胡
                    self.__check_both_zha_hu_or_not(winner, accounts, extra_hu_lst, hu_info, _type=check_type)

    def update_score(self, check_type_, seat_id, pei_seat, score, card, accounts, get_bearer=-1, hu_type=None,
                     extra_hu_type=None):
        if check_type_ == CheckType.WIND_JI:
            score = 0
        other_data = self.other_ming_xi_data(check_type_, seat_id, score, card, hu_type, extra_hu_type, get_bearer)
        self_data = self.self_ming_xi_data(check_type_, [pei_seat], -score, card, hu_type, extra_hu_type)
        self.update_result_score(accounts, pei_seat, 0, other_data)
        self.update_result_score(accounts, seat_id, 1, self_data)

    def check_zha_hu_bear_no_zha_hu(
            self, winner, accounts, extra_hu_lst, men_info, _type=CheckType.CHECK_MEN
    ):
        """
        炸胡者承担未炸胡者的赔付
        若A未炸胡自摸，B炸胡，B要承担C的赔付，所以B承担2倍赔付
        """
        bearer, get_bearer = self.zha_hu_bear_no_zha_hu(winner)
        if bearer:
            # 炸胡者承担自己的清一色+额外分，承担未炸胡玩家应该承担的牌型分+额外分
            base_score1 = self.get_base_score(men_info, extra_hu_lst, bearer.seat_id, True)
            base_score2 = self.get_base_score(men_info, extra_hu_lst, get_bearer.seat_id, True)
            total_score = base_score1 + base_score2

            total_score += self.cal_extra_hu_score(men_info, extra_hu_lst, bearer.seat_id, is_zi_mo=True)
            total_score += self.cal_extra_hu_score(men_info, extra_hu_lst, get_bearer.seat_id, is_zi_mo=True)

            card = men_info.get("card")
            self.update_score(_type, winner.seat_id, bearer.seat_id, -total_score, card, accounts, get_bearer.seat_id,
                              men_info.get("hu_type"), extra_hu_lst)

            if self.__shang_ga:
                # 炸胡者承担
                shang_ga_score = winner.shang_ga_score * 2 + bearer.shang_ga_score + get_bearer.shang_ga_score
                check_type = CheckType.CHECK_GU_MAI  # 估卖
                self.update_score(check_type, winner.seat_id, bearer.seat_id, -shang_ga_score, card, accounts,
                                  get_bearer.seat_id)

    def __check_both_zha_hu_or_not(
            self, winner, accounts, extra_hu_lst, men_info, _type=CheckType.CHECK_MEN
    ):
        """
        处理都要赔分的情况
        分两者都炸胡或其它
        炸胡包清一色
        """
        total_score = 0
        total_gu_mai_score = 0
        win_from = []
        card = men_info.get("card")
        for p in self.seats:
            if p.seat_id == winner.seat_id:
                continue
            win_from.append(p.seat_id)
            per_score = self.get_base_score(men_info, extra_hu_lst, p.seat_id, True)
            per_score += self.cal_extra_hu_score(men_info, extra_hu_lst, p.seat_id, is_zi_mo=True)

            other_data = self.other_ming_xi_data(
                _type, winner.seat_id, -per_score, card, men_info.get("hu_type"), extra_hu_lst)
            self.update_result_score(accounts, p.seat_id, 0, other_data)
            total_score += per_score

            if self.__shang_ga:
                shang_ga_score = winner.shang_ga_score + p.shang_ga_score
                total_gu_mai_score += shang_ga_score
                check_type = CheckType.CHECK_GU_MAI  # 估卖
                other_data = self.other_ming_xi_data(check_type, winner.seat_id, -shang_ga_score, card)
                self.update_result_score(accounts, p.seat_id, 0, other_data)

        self_data = self.self_ming_xi_data(
            _type, win_from, total_score, card, men_info.get("hu_type"), extra_hu_lst)
        self.update_result_score(accounts, winner.seat_id, 1, self_data)
        if self.__shang_ga:
            check_type = CheckType.CHECK_GU_MAI  # 估卖
            self_data = self.self_ming_xi_data(check_type, win_from, total_gu_mai_score, card)
            self.update_result_score(accounts, winner.seat_id, 1, self_data)

    def detecting_player_status(self, winner):
        """
        检测 玩家状态
        1.两名玩家都叫牌，则不承担
        2.未叫牌需要赔付叫牌玩家
        3.若炸胡玩家与未叫牌玩家同时存在，则炸胡玩家承担未叫牌玩家的赔分+自身赔分
        4.若两名都为未叫牌玩家则各自正常赔付
        5.若两名都为炸胡玩家，则赔付 清一色+额外分
        return: -> PlayerStatusType
        """
        zha_hu_count = 0
        jiao_count = 0
        no_jiao_count = 0
        for p in self.seats:
            if p == winner:
                continue
            if p.is_zha_hu:
                zha_hu_count += 1
            elif p.jiao_pai <= 0:
                no_jiao_count += 1
            else:
                jiao_count += 1
        if zha_hu_count >= 2:
            return PlayerStatusType.ZHA_HU_2
        if jiao_count >= 2:
            return PlayerStatusType.JIAO_2
        if no_jiao_count >= 2:
            return PlayerStatusType.NO_JIAO_2
        if zha_hu_count == 1 and jiao_count == 1:
            return PlayerStatusType.ZHA_HU_AND_JIAO
        if zha_hu_count == 1 and no_jiao_count == 1:
            return PlayerStatusType.ZHA_HU_AND_NO_JIAO
        if jiao_count == 1 and no_jiao_count == 1:
            return PlayerStatusType.JIAO_AND_NO_JIAO

    @staticmethod
    def cal_card_count(cards: list) -> dict:
        card_count = {}
        for c in cards:
            card_count[c] = card_count.get(c, 0) + 1
        return card_count

    @staticmethod
    def other_ming_xi_data(type_, lose_to=-1, score=0, card=0, hu_type=None, extra_hu_type=None, get_bearer=-1):
        if type_ == CheckType.WIND_JI:
            score = 0
        data = {
            "check_type": type_,
            "lose_to": [lose_to],
            "card": card,
            "score": score,
        }
        if hu_type:
            data["hu_type"] = hu_type
        if extra_hu_type:
            data["extra_hu_type"] = extra_hu_type
        if get_bearer > 0:
            data["get_bearer"] = get_bearer
        return data

    @staticmethod
    def update_result_score(res: dict, seat_id, is_self, data=None):
        """
        记录玩家结算明细，统一采用 加分形式
        res: account
        seat_id: 玩家座位号
        is_self: 0/1 0表示输,1表示赢(炸胡反过来)
        data: 明细分
        """
        score = data.get("score", 0)
        if score == 0:
            return
        if not res.get(seat_id):
            res[seat_id] = {"total_score": 0, "ming_xi": {"self": [], "other": []}}
        res[seat_id]["total_score"] += score
        if data:
            key = "self" if is_self else "other"
            res[seat_id]["ming_xi"].setdefault(key, []).append(data)

    @staticmethod
    def self_ming_xi_data(type_, win_from=None, score=0, card=0, hu_type=None, extra_hu_type=None, get_bearer=-1):
        if type_ == CheckType.WIND_JI:
            score = 0
        data = {
            "check_type": type_,
            "win_from": [] if not win_from else win_from,
            "card": card,
            "score": score,
        }
        if hu_type:
            data["hu_type"] = hu_type
        if extra_hu_type:
            data["extra_hu_type"] = extra_hu_type
        if get_bearer > 0:
            data["get_bearer"] = get_bearer
        return data

    def zha_hu_bear_no_zha_hu(self, winner):
        """
        炸胡者承担未炸胡者的赔付
        return: 炸胡者
        """
        bearer = None  # 承担着
        get_bearer = None  # 得到承担者
        for p in self.seats:
            if p == winner:
                continue
            if p.is_zha_hu:
                bearer = p
            else:
                get_bearer = p

        if bearer and get_bearer:
            return bearer, get_bearer
        elif bearer and not get_bearer:
            return False, PlayerStatusType.ZHA_HU_2
        elif not bearer and get_bearer:
            return False, PlayerStatusType.DEFAULT
        return False, 0

    def no_jiao_bear_jiao(self, winner):
        """
        炸胡者承担未炸胡者的赔付
        return: 炸胡者
        """
        bearer = None  # 承担着
        get_bearer = None  # 得到承担者
        for p in self.seats:
            if p == winner:
                continue
            if p.jiao_pai <= 0:
                bearer = p
            else:
                get_bearer = p

        if bearer and get_bearer:
            return bearer, get_bearer
        elif bearer and not get_bearer:
            return False, PlayerStatusType.NO_JIAO_2
        elif not bearer and get_bearer:
            return False, PlayerStatusType.DEFAULT
        return False, 0

    def get_all_distances(self):
        result = list()
        p1 = self.get_player_by_seat_id(1)
        p2 = self.get_player_by_seat_id(2)
        p3 = self.get_player_by_seat_id(3)
        p4 = self.get_player_by_seat_id(4)

        def __calc_distance(_p1, _p2):
            if not _p1 or not _p2:
                return earth_position.DISTANCE_UNKNOWN
            x1, y1 = _p1.position
            x2, y2 = _p2.position
            return earth_position.calc_earth_distance(x1, y1, x2, y2)

        result.append(__calc_distance(p1, p2))
        result.append(__calc_distance(p1, p3))
        result.append(__calc_distance(p1, p4))
        result.append(__calc_distance(p2, p3))
        result.append(__calc_distance(p2, p4))
        result.append(__calc_distance(p3, p4))
        self.log_info(self.tid, "get_all_distances end")
        return result

    async def notify_distance(self):
        distances = self.get_all_distances()
        self.log_info("下发定位信息", distances)
        data = {"distances": distances}
        data_model = S2CNotifyPosition.pb_model(**data)
        await self.inner_broadcast(CmdRoom.NOTIFY_POSITION, data_model)

    async def set_player_position(self, player: Player, data):

        player_position_model.ParseFromString(data)
        x = player_position_model.x or 0
        y = player_position_model.y or 0
        if x == 0 and y == 0:
            x = None
            y = None
        player.set_position(x, y)
        self.log_info("收到定位信息", player.uid, player.seat_id, "x", x, "y", y)
        await self.notify_distance()

    async def liu_ju(self):
        await self.liu_ju_notify()
        self.__win_seat_list = []
        await super(BaseCardRoom, self).force_dismiss()

    def refresh_room_conf(self, service, room_conf):
        self.__init__(self.tid, service, room_conf)

    def clear_room(self):
        self.__winner_list = []
        self.__gang_hou_mo_pai = []
        self.__gang_hou_chu_pai = []
        self.__que_list = [1, 2, 3]
        self.__shang_ga_list = [1, 2, 3, 4, 5, 0]
        self.clear_table_actions()
        self.clear_room_init()
        self.__ji_pai_score = self.get_ji_pai_score_map()
        self.__default_ji = {CardsType.YAO_JI}
        super().clear_room()
