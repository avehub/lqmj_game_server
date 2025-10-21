from nsanic.libs.tool import json_encode
from common.proto.pb2 import ws_leisure_pb2

one_of_model = ws_leisure_pb2.S2COneField()


def s2c_one_of_model():
    return ws_leisure_pb2.S2COneField()


def s2c_trustee_model(seat_id, is_trustee):
    """ 托管模型 """
    m = ws_leisure_pb2.S2CTrustee()
    m.seat_id = seat_id
    m.is_trustee = is_trustee
    return m


def s2c_recharge_model(seat_id, gold: str):
    """ 充值模型 """
    m = ws_leisure_pb2.S2CRechargeBroad()
    m.seat_id = seat_id
    m.gold = gold
    return m


def s2c_gold_model(seat_id, gold: int):
    m = ws_leisure_pb2.AfterCutTickets()
    m.seat_id = seat_id
    m.gold = gold
    return m


def s2c_tickets_model(gold_info: list):
    tickets_model = ws_leisure_pb2.S2CDeductTickets()  # 扣门票模型
    for info in gold_info:
        obj = tickets_model.gold_info.add()
        obj.seat_id = info.get("seat_id") or 0
        obj.gold = str(info.get("gold"))
    return tickets_model


# 水鱼
bet_model = ws_leisure_pb2.S2CStartBet()  # 下注流程
do_bet_model = ws_leisure_pb2.S2CDoBet()  # 玩家下注后广播模型

sa_pu_model = ws_leisure_pb2.SCPubDoSaPu()  # 撒扑模型
operate_model = ws_leisure_pb2.S2CDoOperate()  # 操作模型

# 斗地主
bid_model = ws_leisure_pb2.S2CTurnBid()  # 开始叫分
do_bid_model = ws_leisure_pb2.S2CDoBid()  # 玩家叫分
redouble_model = ws_leisure_pb2.S2CStartRedouble()  # 开始铲
do_redouble_model = ws_leisure_pb2.S2CDoRedouble()  # 玩家铲
confirm_dealer_model = ws_leisure_pb2.S2CConfirmDealer()  # 确定地主
play_cards_model = ws_leisure_pb2.S2CPlayCardsLandlords()  # 出牌模型


def s2c_operate_model(seat_id, operate, seconds=0):
    operate_model.seat_id = seat_id
    operate_model.operate = operate
    operate_model.seconds = seconds
    return operate_model


def pack_base_room_info(obj, **kwargs):
    """ 打包基础房间信息 """
    obj.base_room_info.tid = kwargs.get("tid") or 0
    obj.base_room_info.play_type = kwargs.get("play_type") or 0
    obj.base_room_info.curr_seat_id = kwargs.get("curr_seat_id") or 0
    obj.base_room_info.dealer_id = kwargs.get("dealer_id") or 0
    obj.base_room_info.room_status = kwargs.get("room_status") or 0
    obj.base_room_info.flow_status = kwargs.get("flow_status") or 0
    obj.base_room_info.seconds = kwargs.get("seconds") or 0

    room_conf = kwargs.get("room_conf", {})
    rule_conf = room_conf.get("rule_conf", {})

    obj.base_room_info.room_conf.max_player = rule_conf.get("max_player") or room_conf.get("max_player")
    obj.base_room_info.room_conf.total_round = rule_conf.get("total_round") or room_conf.get("total_round")

    obj.base_room_info.min_take = room_conf.get("min_take") or 0
    obj.base_room_info.max_take = room_conf.get("max_take") or 0
    obj.base_room_info.base_score = room_conf.get("base_score") or 0
    obj.base_room_info.desc = room_conf.get("desc") or ""
    obj.base_room_info.level = room_conf.get("level") or 0
    obj.base_room_info.level_desc = room_conf.get("level_desc") or ""
    obj.base_room_info.round_idx = kwargs.get("round_idx") or 0


class S2CRoomInfo03Monster:
    """ 打妖怪房间信息 """

    @staticmethod
    def pack_turn_cards(obj, kwargs):
        turn_cards = kwargs.get("turn_cards") or []
        for cards in turn_cards:
            t_obj = obj.turn_cards.add()
            t_obj.seat_id = cards[0]
            t_obj.cards.append(cards[1])
            t_obj.card_val = cards[2]

    @classmethod
    def pb_model(cls, **kwargs):
        obj = ws_leisure_pb2.S2CRoomInfo03Monster()
        pack_base_room_info(obj, **kwargs)
        obj.yao_de_qi = kwargs.get("yao_de_qi") or False
        cls.pack_turn_cards(obj, kwargs)
        obj.played_shi_fu = kwargs.get("played_shi_fu") or False
        obj.t_val_multiple = kwargs.get("t_val_multiple") or '0'
        obj.tribulation_val = kwargs.get("tribulation_val") or 0
        obj.mean_gold_base = kwargs.get("mean_gold_base") or 0
        return obj


class S2CRoomInfo03WaterFish:
    """ 水鱼房间信息 """

    @classmethod
    def pb_model(cls, **kwargs):
        obj = ws_leisure_pb2.S2CRoomInfo03WaterFish()
        pack_base_room_info(obj, **kwargs)

        obj.dealer_op.update(kwargs.get("dealer_op") or {})
        obj.farmer_op.update(kwargs.get("farmer_op") or {})
        return obj


def pack_base_player_info(obj, **kwargs):
    obj.base_player_info.cards[:] = []  # 清空cards

    obj.base_player_info.uid = kwargs.get("uid") or 0
    obj.base_player_info.seat_id = kwargs.get("seat_id") or 0
    obj.base_player_info.is_trustee = kwargs.get("is_trustee") or 0
    obj.base_player_info.offline = kwargs.get("offline") or False
    obj.base_player_info.cards.extend(kwargs.get("cards") or [])
    obj.base_player_info.round_score = kwargs.get("round_score") or 0
    obj.base_player_info.cards_len = kwargs.get("cards_len") or 0
    obj.base_player_info.gold = str(kwargs.get("gold", ""))


class S2CPlayerInfo04WaterFish:
    """ 水鱼玩家信息 """

    @classmethod
    def pb_model(cls, data: list):
        player_list_obj = ws_leisure_pb2.S2CPlayerInfo04WaterFish()
        for one_data in data:
            obj = player_list_obj.player_info.add()
            pack_base_player_info(obj, **one_data)
            obj.sp_status = one_data.get("sp_status") or 0

        return player_list_obj


class S2CPlayerInfo04Monster:
    """ 玩家信息 """
    __proto = None

    @classmethod
    def pb_model(cls, data: list):
        cls.__proto = ws_leisure_pb2.S2CPlayerInfo04Monster()
        for one_data in data:
            obj = cls.__proto.player_info.add()
            pack_base_player_info(obj, **one_data)
            obj.pick_len = one_data.get("pick_len") or 0
            obj.is_give_up = one_data.get("is_give_up") or False
            obj.skin_id_list.extend(one_data.get("skin_id_list") or [])
        return cls.__proto


class S2CDealCards:
    """ 发牌 """

    @classmethod
    def pb_model(cls, **kwargs):
        obj = ws_leisure_pb2.S2CDealCards()
        obj.seat_id = kwargs.get("seat_id") or 0
        obj.cards.extend(kwargs.get("cards") or [])
        obj.mean_gold_base = kwargs.get("mean_gold_base") or 0
        return obj


class S2CTurnTo13:
    """ 轮到 """

    @classmethod
    def pb_model(cls, **kwargs):
        obj = ws_leisure_pb2.S2CTurnTo13()
        obj.seat_id = kwargs.get("seat_id") or 0
        obj.seconds = kwargs.get("seconds") or 0
        # obj.yao_de_qi = kwargs.get("yao_de_qi") or False
        # pack_turn_cards(obj, kwargs)
        return obj


class S2CPlayCards:
    """ 出牌 """

    @classmethod
    def pb_model(cls, **kwargs):
        obj = ws_leisure_pb2.S2CPlayCards()
        obj.case_index = kwargs.get("case_index") or 0
        obj.skill_index = kwargs.get("skill_index") or 0
        turn_card = kwargs.get("turn_card") or []
        if turn_card:
            obj.turn_card.seat_id = turn_card[0]
            obj.turn_card.cards.append(turn_card[1])
            obj.turn_card.card_val = turn_card[2]
        obj.t_val_multiple = kwargs.get("t_val_multiple") or '0'
        obj.tribulation_val = kwargs.get("tribulation_val") or 0
        return obj


def pack_i_info(obj, kwargs):
    """ 打包即时信息 """
    check_infos = kwargs.get("check_infos") or []
    for info in check_infos:
        c_obj = obj.check_infos.add()
        c_obj.seat_id = info.get("seat_id") or 0
        c_obj.win_gold = str(info.get("win_gold") or '0')
        c_obj.res_gold = str(info.get("res_gold", '0'))


class S2CPickCards:
    """ 捡牌消息 """

    @classmethod
    def pb_model(cls, **kwargs):
        obj = ws_leisure_pb2.S2CPickCards()
        obj.seat_id = kwargs.get("seat_id") or 0
        obj.player_pick_len = kwargs.get("player_pick_len") or 0
        obj.room_pick_len = kwargs.get("room_pick_len") or 0
        obj.curr_pick_len = kwargs.get("curr_pick_len") or 0
        pack_i_info(obj, kwargs)
        return obj


class S2CBrokeBroad:
    """ 破产广播 """

    @staticmethod
    def pack_gift(obj, gift_conf: dict):
        gift_obj = obj.gift_item.add()
        gift_obj.activity_id = gift_conf.get("activity_id") or 0
        gift_obj.gift_type = gift_conf.get("gift_type") or 0

    @classmethod
    def pb_model(cls, **kwargs):
        obj = ws_leisure_pb2.S2CBrokeBroad()
        obj.seconds = kwargs.get("seconds") or 0
        obj.seat_id = kwargs.get("seat_id") or 0
        obj.ori_gold = str(kwargs.get("ori_gold", ""))
        gift_conf = kwargs.get("gift_conf") or []
        for conf in gift_conf:
            cls.pack_gift(obj, conf)
        return obj


class S2CRoundOver:
    """ 打妖怪上篇round """

    @staticmethod
    def pack_round_info(obj, kwargs):
        """ 游戏结束消息 """
        check_infos = kwargs.get("check_infos") or []
        for info in check_infos:
            c_obj = obj.check_infos.add()
            c_obj.seat_id = info.get("seat_id") or 0
            c_obj.win_gold = str(info.get("win_gold", "0"))
            c_obj.res_gold = str(info.get("res_gold", "0"))
            c_obj.skin_addition_num = info.get("skin_addition_num") or 0
            c_obj.multiple_card_addition_num = info.get("multiple_card_addition_num") or 0
            c_obj.multiple = info.get("multiple") or 0
            c_obj.free_loss_num = info.get("free_loss_num") or 0

            ranking_info = info.get("ranking_info") or {}
            c_obj.ranking_info.r_score = ranking_info.get("r_score") or 0
            c_obj.ranking_info.win_streak_count = ranking_info.get("win_streak_count") or 0
            c_obj.ranking_info.r_score_free_num = ranking_info.get("r_score_free_num") or 0

            c_obj.ranking_info.ranking_addition.prop_card = ranking_info.get("prop_card") or ""
            c_obj.ranking_info.ranking_addition.session = ranking_info.get("session") or ""
            c_obj.ranking_info.ranking_addition.win_streak = ranking_info.get("win_streak") or 0
            c_obj.ranking_info.ranking_addition.vip = ranking_info.get("vip") or ""
            c_obj.ranking_info.ranking_addition.lifetime_card = ranking_info.get("lifetime_card") or ""
            c_obj.ranking_info.ranking_addition.skin = ranking_info.get("skin") or ""
            c_obj.is_win = info.get("is_win") or 0

    @classmethod
    def pb_model(cls, **kwargs):
        obj = ws_leisure_pb2.S2CRoundOver()
        S2CRoundOver.pack_round_info(obj, kwargs)
        obj.mvp = kwargs.get('mvp') or 0
        obj.mvp_ranking_add = kwargs.get('mvp_ranking_add') or 0
        obj.season_sta = kwargs.get('season_status') or 0
        return obj


# ################################## 神魔仙逆下篇 ##################################

class S2CTurnToSeq13:
    """ 轮到某人 """

    @classmethod
    def pb_model(cls, **kwargs):
        obj = ws_leisure_pb2.S2CTurnToSeq13()
        obj.seat_id = kwargs.get("seat_id") or 0
        obj.seconds = kwargs.get("seconds") or 0
        # legal_actions = kwargs.get("legal_actions") or []
        # for ac in legal_actions:
        #     la_list_obj = obj.legal_actions.add()
        #     la_list_obj.legal_action.extend(ac)
        return obj


class S2CPlayCardsSeq:
    """ 下篇出牌 """

    @classmethod
    def pb_model(cls, **kwargs):
        obj = ws_leisure_pb2.S2CPlayCardsSeq()
        obj.tribulation_val = kwargs.get("tribulation_val")
        obj.ability = kwargs.get("ability") or 0
        obj.skill_index = kwargs.get("skill_index") or 0
        cards_list = kwargs.get("cards_area") or []
        for cards in cards_list:
            cards_obj = obj.cards_area.add()
            cards_obj.c = cards.get('c') or 0
            cards_obj.a = cards.get('a') or 0

        turn_card = kwargs.get("turn_card") or []
        if turn_card:
            obj.turn_card.seat_id = turn_card[0]
            obj.turn_card.cards.extend(turn_card[1])

        obj.t_val_multiple = kwargs.get("t_val_multiple") or '0'
        return obj


class S2CPickCardsSequel:
    """ 捡牌消息即时结算 """

    @classmethod
    def pb_model(cls, **kwargs):
        obj = ws_leisure_pb2.S2CPickCardsSequel()
        obj.seat_id = kwargs.get("seat_id") or 0
        obj.tribulation_val = kwargs.get("tribulation_val") or 0
        obj.room_tribulation_val = kwargs.get("room_tribulation_val") or 0
        pack_i_info(obj, kwargs)
        return obj


class S2CRoomInfo03MonsterSeq:
    """ 神魔下篇房间信息 """

    @staticmethod
    def pack_turn_cards(obj, kwargs):
        turn_cards = kwargs.get("turn_cards") or []
        for cards in turn_cards:
            t_obj = obj.turn_cards.add()
            t_obj.seat_id = cards[0]
            t_obj.cards.extend(cards[1])

    @classmethod
    def pb_model(cls, **kwargs):
        obj = ws_leisure_pb2.S2CRoomInfo03MonsterSeq()
        pack_base_room_info(obj, **kwargs)
        obj.yao_de_qi = kwargs.get("yao_de_qi") or False
        cls.pack_turn_cards(obj, kwargs)
        obj.area_monster.extend(kwargs.get("area_monster") or [])
        obj.area_prentice.extend(kwargs.get("area_prentice") or [])
        obj.area_master.extend(kwargs.get("area_master") or [])
        obj.area_divine.extend(kwargs.get("area_divine") or [])
        obj.tribulation_val = kwargs.get("tribulation_val") or 0
        obj.cards_len = kwargs.get("cards_len") or 0
        obj.reverse = kwargs.get("reverse") or 0
        obj.t_val_multiple = kwargs.get("t_val_multiple") or '0'
        obj.mean_gold_base = kwargs.get("mean_gold_base") or 0

        cards_list = kwargs.get("cards_area") or []
        for cards in cards_list:
            cards_obj = obj.cards_area.add()
            cards_obj.c = cards.get('c') or 0
            cards_obj.a = cards.get('a') or 0

        legal_actions = kwargs.get("legal_actions") or []
        for ac in legal_actions:
            la_list_obj = obj.legal_actions.add()
            la_list_obj.action.extend(ac)
        return obj


class S2CPlayerInfo04MonsterSeq:

    @classmethod
    def pb_model(cls, data: list):
        proto = ws_leisure_pb2.S2CPlayerInfo04MonsterSeq()
        for one_data in data:
            obj = proto.player_info.add()
            pack_base_player_info(obj, **one_data)
            obj.area_tribulation.extend(one_data.get("area_tribulation") or [])
            obj.is_give_up = one_data.get("is_give_up") or False
            obj.tribulation_val = one_data.get("tribulation_val") or 0
            obj.skin_id_list.extend(one_data.get("skin_id_list") or [])
        return proto


class S2CComplementCards:

    @classmethod
    def pb_model(cls, seat_id, cards_list: list[dict], tribulation_val: int, ability, t_val_multiple):
        dm = ws_leisure_pb2.S2CComplementCards()
        dm.seat_id = seat_id
        dm.tribulation_val = tribulation_val
        dm.ability = ability
        dm.t_val_multiple = t_val_multiple
        for cards in cards_list:
            cards_obj = dm.cards_area.add()
            cards_obj.c = cards.get('c') or 0
            cards_obj.a = cards.get('a') or 0
        return dm


def use_ability_obj(data):
    dm = ws_leisure_pb2.S2CUseAbilityOrNot()
    dm.seat_id = data.get("seat_id") or 0
    dm.seconds = data.get("seconds") or 0
    dm.ability = data.get("ability") or 0
    return dm


# ################################## 神魔仙逆下篇 ##################################


# ################################## 斗地主 ##################################
class S2CRoomInfo03Landlords:
    """ 斗地主房间信息 """

    @classmethod
    def pb_model(cls, **kwargs):
        obj = ws_leisure_pb2.S2CRoomInfo03Landlords()
        pack_base_room_info(obj, **kwargs)
        obj.yao_de_qi = kwargs.get("yao_de_qi") or False
        obj.dealer_cards.extend(kwargs.get("dealer_cards") or [])
        table_cards = kwargs.get("table_cards") or []
        if table_cards:
            obj.table_cards = json_encode(table_cards)
        obj.multiple = kwargs.get("multiple") or 0
        obj.is_redouble = kwargs.get("is_redouble") or False
        obj.is_re_redouble = kwargs.get("is_re_redouble") or False
        return obj


class S2CPlayerInfo04Landlords:
    """ 斗地主：玩家信息 """

    @classmethod
    def pb_model(cls, data: list):
        proto_obj = ws_leisure_pb2.S2CPlayerInfo04Landlords()
        for one_data in data:
            obj = proto_obj.player_info.add()
            pack_base_player_info(obj, **one_data)
            obj.bid_score = one_data.get("bid_score") or 0
            obj.double_type = one_data.get("double_type") or 0
            obj.multiple = one_data.get("multiple") or 0
        return proto_obj


class S2CTurnTOLandlords:
    """ 轮到 """

    @staticmethod
    def pack_legal_actions(obj, kwargs):
        """ 打包合法动作 """
        legal_actions = kwargs.get("legal_actions") or []
        for cards in legal_actions:
            t_obj = obj.legal_actions.add()
            t_obj.legal_action.extend(cards)

    @classmethod
    def pb_model(cls, **kwargs):
        obj = ws_leisure_pb2.S2CTurnTOLandlords()
        obj.seat_id = kwargs.get("seat_id") or 0
        obj.seconds = kwargs.get("seconds") or 0
        obj.yao_de_qi = kwargs.get("yao_de_qi") or False

        legal_actions = kwargs.get("legal_actions") or []
        if legal_actions:
            obj.legal_actions = json_encode(legal_actions)
        return obj


def pack_hand_cards(obj, kwargs):
    hand_cards = kwargs.get("hand_cards") or []
    for info in hand_cards:
        c_obj = obj.hand_cards.add()
        c_obj.seat_id = info.get("seat_id") or 0
        c_obj.cards.extend(info.get("cards"))


class S2CRoundOverLandlords:
    @classmethod
    def pb_model(cls, **kwargs):
        obj = ws_leisure_pb2.S2CRoundOverLandlords()
        pack_i_info(obj, kwargs)
        pack_hand_cards(obj, kwargs)
        obj.is_spring = kwargs.get("is_spring") or False
        obj.is_re_spring = kwargs.get("is_re_spring") or False
        obj.multiple = kwargs.get("multiple") or 0
        return obj


# ################################## 斗地主 ##################################

# ################################## 麻将 ##################################


def pack_rule_details(obj, **kwargs):
    """ 打包规则信息 """
    rule_details = kwargs.get("rule_details", {})
    obj.rule_details.fan_ji_pai = rule_details.get("fan_ji_pai") or 0
    obj.rule_details.shang_xia_ji = rule_details.get("shang_xia_ji") or 0
    obj.rule_details.ben_ji = rule_details.get("ben_ji") or 0
    obj.rule_details.wu_gu_ji = rule_details.get("wu_gu_ji") or 0
    obj.rule_details.man_tang_ji = rule_details.get("man_tang_ji") or 0
    obj.rule_details.chong_feng_ji = rule_details.get("chong_feng_ji") or 0
    obj.rule_details.ze_ren_ji = rule_details.get("ze_ren_ji") or 0
    obj.rule_details.zhan_ji = rule_details.get("zhan_ji") or 0
    obj.rule_details.jian_gang_san = rule_details.get("jian_gang_san") or 0
    obj.rule_details.bao_ting = rule_details.get("bao_ting") or 0
    obj.rule_details.bi_men_yi_shou = rule_details.get("bi_men_yi_shou") or 0
    obj.rule_details.shang_ga = rule_details.get("shang_ga") or 0
    obj.rule_details.gu_mai_score = rule_details.get("gu_mai_score") or 0
    obj.rule_details.zi_mo_jia_bei = rule_details.get("zi_mo_jia_bei") or 0
    obj.rule_details.bao_ji = rule_details.get("bao_ji") or 0
    obj.rule_details.bao_gang = rule_details.get("bao_gang") or 0
    obj.rule_details.liang_men_pai = rule_details.get("liang_men_pai") or 0
    obj.rule_details.suo_de_jia_1 = rule_details.get("suo_de_jia_1") or 0
    obj.rule_details.hu_pai_ti_shi = rule_details.get("hu_pai_ti_shi") or 0
    obj.rule_details.left_3_bi_hu = rule_details.get("left_3_bi_hu") or 0
    obj.rule_details.di_long_qi = rule_details.get("di_long_qi") or 0
    obj.rule_details.limit_lose = rule_details.get("limit_lose") or 0
    obj.rule_details.huang_zhuang_bu_huang_ji = rule_details.get("huang_zhuang_bu_huang_ji") or 0
    obj.rule_details.four_card_bao_ting = rule_details.get("four_card_bao_ting") or 0
    obj.rule_details.xiao_pai_bi_men = rule_details.get("xiao_pai_bi_men") or 0
    obj.rule_details.tui_zhang_can_hu = rule_details.get("tui_zhang_can_hu") or 0
    obj.rule_details.bao_ting_bi_men = rule_details.get("bao_ting_bi_men") or 0
    obj.rule_details.exchange_three = rule_details.get("exchange_three") or 0
    obj.rule_details.exchange_cards_type = rule_details.get("exchange_cards_type") or 0
    obj.rule_details.yi_wan_ji = rule_details.get("yi_wan_ji") or 0
    obj.rule_details.qing_yi_se_extra_add = rule_details.get("qing_yi_se_extra_add") or 0
    obj.rule_details.shu_zi_ji = rule_details.get("shu_zi_ji") or 0
    obj.rule_details.xi_pai_score = rule_details.get("xi_pai_score") or 0
    obj.rule_details.wu_gu_ji_score = rule_details.get("wu_gu_ji_score") or 0
    obj.rule_details.after_peng_can_bao_ting = rule_details.get("after_peng_can_bao_ting") or 0
    obj.rule_details.yuan_bao = rule_details.get("yuan_bao") or 0
    obj.rule_details.yin_ji = rule_details.get("yin_ji") or 0
    obj.rule_details.lian_zhuang = rule_details.get("lian_zhuang") or 0


class S2CReady07Mahjong:
    @classmethod
    def pb_model(cls, **kwargs):
        obj = ws_leisure_pb2.S2CReady07Mahjong()
        obj.seat_id = kwargs.get("seat_id") or 0
        obj.is_ready = kwargs.get("is_ready") or False
        return obj

class S2CRoomInfo04Mahjong:

    @classmethod
    def pb_model(cls, **kwargs):
        obj = ws_leisure_pb2.S2CRoomInfo04Mahjong()
        pack_base_room_info(obj, **kwargs)
        dismiss_info = kwargs.get("dismiss_info", {})
        obj.dismiss_info.agree_seats.extend(dismiss_info.get("agree_seats") or [])
        obj.dismiss_info.req_dismiss_left_sec = dismiss_info.get("req_dismiss_left_sec") or 0
        obj.owner = kwargs.get("owner") or 0
        obj.left_count = kwargs.get("left_count") or 0
        obj.last_card = kwargs.get("last_card") or 0
        obj.last_seat_id = kwargs.get("last_seat_id") or 0
        obj.dice_num.extend(kwargs.get("dice_num") or [])
        obj.ding_que_list.extend(kwargs.get("ding_que_list") or [])
        obj.exchange_seats.extend(kwargs.get("exchange_seats") or [])
        obj.operate_seats.extend(kwargs.get("operate_seats") or [])
        obj.shang_ga_list.extend(kwargs.get("shang_ga_list") or [])
        pack_rule_details(obj, **kwargs)
        obj.cs_type = kwargs.get("cs_type") or 0
        obj.price = kwargs.get("price") or 0
        obj.is_location = kwargs.get("is_location") or 0
        obj.is_friend = kwargs.get("is_friend") or 0
        obj.club_id = kwargs.get("club_id") or 0
        obj.pay_type = kwargs.get("pay_type") or 0
        obj.lai_zi = kwargs.get("lai_zi") or 0
        return obj

def pack_table_cards(obj, **kwargs):
    table_cards = kwargs.get("table_cards") or []
    for cards in table_cards:
        table = obj.table_cards.add()
        table.from_seat_id = cards.get("from_seat_id") or 0
        table.card = cards.get("card") or 0
        table.act_type = cards.get("act_type") or 0

class S2CPlayerInfo05Mahjong:
    @classmethod
    def pb_model(cls, data:list):
        obj = ws_leisure_pb2.S2CPlayerInfo05Mahjong()
        for one_data in data:
            p_info = obj.player_info.add()
            pack_base_player_info(p_info, **one_data)
            p_info.is_ready = one_data.get("is_ready") or False
            p_info.shang_ga = one_data.get("shang_ga") or False
            p_info.shang_ga_score = one_data.get("shang_ga_score") or 0
            p_info.is_bao_ting = one_data.get("is_bao_ting") or False
            p_info.mo_pai = one_data.get("mo_pai") or 0
            p_info.first_ji = one_data.get("first_ji") or 0
            p_info.first_wu_gu_ji = one_data.get("first_wu_gu_ji") or 0
            p_info.first_yi_tong_ji = one_data.get("first_yi_tong_ji") or 0
            p_info.first_yi_wan_ji = one_data.get("first_yi_wan_ji") or 0
            p_info.ze_ren_ji = one_data.get("ze_ren_ji") or 0
            p_info.ze_ren_wu_gu_ji = one_data.get("ze_ren_wu_gu_ji") or 0
            p_info.ze_ren_yi_tong_ji = one_data.get("ze_ren_yi_tong_ji") or 0
            p_info.ze_ren_yi_wan_ji = one_data.get("ze_ren_yi_wan_ji") or 0
            p_info.is_lock_cards = one_data.get("is_lock_cards") or False
            p_info.operates.extend(one_data.get("operates") or [])
            p_info.is_bi_hu = one_data.get("is_bi_hu") or False
            p_info.out_cards.extend(one_data.get("out_cards") or [])
            p_info.lock_cards.extend(one_data.get("lock_cards") or [])
            p_info.que = one_data.get("que") or 0
            p_info.total_score = one_data.get("total_score") or 0
            pack_table_cards(p_info, **one_data)
            men_cards = one_data.get("men_cards") or []
            for men_data in men_cards:
                men_card = p_info.men_cards.add()
                men_card.CopyFrom(S2CMenInfoMahjong.pb_model(**men_data))
        return obj

class S2CRoundStartMahjong:

    @classmethod
    def pb_model(cls,**kwargs):
        obj = ws_leisure_pb2.S2CRoundStartMahjong()
        obj.round_idx = kwargs.get("round_idx") or 1
        obj.dealer = kwargs.get("dealer") or 0
        obj.dice_num.extend(kwargs.get("dice_num") or [])
        return obj

class S2CShangGaMahjong:

    @classmethod
    def pb_model(cls,**kwargs):
        obj = ws_leisure_pb2.S2CShangGaMahjong()
        obj.seat_id = kwargs.get("seat_id") or 0
        obj.shang_ga = kwargs.get("shang_ga")
        return obj

class S2CShangGaBeginMahjong:
    @classmethod
    def pb_model(cls,**kwargs):
        obj = ws_leisure_pb2.S2CShangGaBeginMahjong()
        obj.can_shang_list.extend(kwargs.get("can_shang_list") or [])
        obj.seconds = kwargs.get("seconds") or 0
        obj.in_flow = kwargs.get("in_flow") or 0
        return obj

class S2CDealCardsMahjong:
    @classmethod
    def pb_model(cls,**kwargs):
        obj = ws_leisure_pb2.S2CDealCardsMahjong()
        obj.hand_cards.extend(kwargs.get("hand_cards") or [])
        obj.mo_pai = kwargs.get("mo_pai") or 0
        obj.cards_count.update(kwargs.get("cards_count") or {})
        obj.left_count = kwargs.get("left_count") or 0
        obj.seat_id = kwargs.get("seat_id") or 0
        return obj

class S2CPublicOperatesMahjong:
    @classmethod
    def pb_model(cls,**kwargs):
        obj = ws_leisure_pb2.S2CPublicOperatesMahjong()
        obj.seat_id = kwargs.get("seat_id") or 0
        obj.left_count = kwargs.get("left_count") or 0
        obj.seconds = kwargs.get("seconds") or 0
        obj.in_flow = kwargs.get("in_flow") or 0
        obj.is_bi_hu = kwargs.get("is_bi_hu") or 0
        obj.operates.extend(kwargs.get("operates") or [])
        obj.gang_hou_mo_pai = kwargs.get("gang_hou_mo_pai") or 0
        obj.is_show_bao_ting = kwargs.get("is_show_bao_ting") or 0
        obj.can_gang_list.extend(kwargs.get("can_gang_list") or [])
        obj.hand_cards.extend(kwargs.get("hand_cards") or [])
        return obj

class S2CTurnToMahjong:
    @classmethod
    def pb_model(cls,**kwargs):
        obj = ws_leisure_pb2.S2CTurnToMahjong()
        obj.seat_id = kwargs.get("seat_id") or 0
        obj.seconds = kwargs.get("seconds") or 0
        obj.lock_cards.extend(kwargs.get("lock_cards") or [])
        obj.in_flow = kwargs.get("in_flow") or 0
        return obj

class S2CPlayCardsMahjong:
    @classmethod
    def pb_model(cls,**kwargs):
        obj = ws_leisure_pb2.S2CPlayCardsMahjong()
        obj.seat_id = kwargs.get("seat_id") or 0
        obj.card = kwargs.get("card") or 0
        return obj

class S2CFirstJiMahjong:
    @classmethod
    def pb_model(cls,**kwargs):
        obj = ws_leisure_pb2.S2CFirstJiMahjong()
        obj.first_ji_seat_id = kwargs.get("first_ji_seat_id") or 0
        obj.first_ji_card = kwargs.get("first_ji_card") or 0
        return obj

def pack_hu_base_info(obj, data):
    """ 打包胡牌信息 """
    obj.seat_id = data.get("seat_id") or 0
    obj.curr_seat_id = data.get("curr_seat_id") or 0
    obj.curr_card = data.get("curr_card") or 0
    obj.hu_type = data.get("hu_type") or 0
    obj.is_zi_mo = data.get("is_zi_mo") or False
    obj.is_finish = data.get("is_finish") or 0
    obj.is_zha_hu = data.get("is_zha_hu") or 0
    obj.extra_hu_type.extend(data.get("extra_hu_type") or [])
    obj.winner_hand_cards.extend(data.get("winner_hand_cards") or [])


class S2CHuInfoMahjong:
    @classmethod
    def pb_model(cls,data_list: list):
        hu_info_obj = ws_leisure_pb2.S2CHuInfoMahjong()
        for data in data_list:
            obj = hu_info_obj.hu_info.add()
            pack_hu_base_info(obj,data)
        return hu_info_obj

class S2CHuAfterCards:
    @classmethod
    def pb_model(cls,data_list:list):
        cards_obj = ws_leisure_pb2.S2CHuAfterCards()
        for data in data_list:
            obj = cards_obj.cards_info.add()
            obj.seat_id = data.get("seat_id") or 0
            obj.hand_cards.extend(data.get("hand_cards") or[])
        return cards_obj

class S2CMenInfoMahjong:
    @classmethod
    def pb_model(cls,**kwargs):
        obj = ws_leisure_pb2.S2CMenInfoMahjong()
        obj.seat_id = kwargs.get("seat_id") or 0
        obj.curr_seat_id = kwargs.get("curr_seat_id") or 0
        obj.curr_card = kwargs.get("curr_card") or 0
        obj.is_zi_mo = kwargs.get("is_zi_mo") or False
        obj.extra_hu_type.extend(kwargs.get("extra_hu_type") or [])
        obj.bei_sha_bao_seats.extend(kwargs.get("bei_sha_bao_seats") or [])
        obj.fang_pao_seat_id = kwargs.get("fang_pao_seat_id") or 0
        obj.re_pao_score = kwargs.get("re_pao_score") or 0
        obj.qiang_gang_score = kwargs.get("qiang_gang_score") or 0
        gang_card_data = kwargs.get("gang_card_data") or []
        for data in gang_card_data:
            obj = obj.gang_card.add()
            obj.act_type = data[0]
            obj.card = data[1]
        obj.score = kwargs.get("score") or 0
        obj.check_type = kwargs.get("check_type") or 0
        obj.is_yi_pao_duo_xiang = kwargs.get("is_yi_pao_duo_xiang") or 0
        obj.hu_type = kwargs.get("hu_type") or 0
        return obj

class S2CAfterGangMoCard:
    @classmethod
    def pb_model(cls,**kwargs):
        obj = ws_leisure_pb2.S2CAfterGangMoCard()
        obj.seat_id = kwargs.get("seat_id") or 0
        obj.left_count = kwargs.get("left_count") or 0
        obj.seconds = kwargs.get("seconds") or 0
        obj.card = kwargs.get("card") or 0
        obj.operates.extend(kwargs.get("operates") or [])
        return obj

class S2CGangInfo:
    @classmethod
    def pb_model(cls,**kwargs):
        obj = ws_leisure_pb2.S2CGangInfo()
        obj.seat_id = kwargs.get("seat_id") or 0
        obj.from_seat_id = kwargs.get("from_seat_id") or 0
        obj.is_finish = kwargs.get("is_finish") or 0
        obj.card = kwargs.get("card") or 0
        obj.act_type = kwargs.get("act_type") or 0
        obj.ze_ren_ji = kwargs.get("ze_ren_ji") or 0
        obj.han_bao_dou = kwargs.get("han_bao_dou") or 0
        return obj

class S2CHuBaseInfo:
    @classmethod
    def pb_model(cls,**kwargs):
        obj = ws_leisure_pb2.S2CHuBaseInfo()
        pack_hu_base_info(obj, kwargs)
        return obj

class S2CExchangeCardsInfo:
    @classmethod
    def pb_model(cls,**kwargs):
        obj = ws_leisure_pb2.S2CExchangeCardsInfo()
        obj.hand_cards.extend(kwargs.get("hand_cards")or [])
        obj.get_cards.extend(kwargs.get("get_cards")or [])
        obj.seat_id = kwargs.get("seat_id") or 0
        return obj

class S2CTianTingInfo:
    @classmethod
    def pb_model(cls,**kwargs):
        obj = ws_leisure_pb2.S2CTianTingInfo()
        obj.seat_id = kwargs.get("seat_id") or 0
        obj.tian_ting = kwargs.get("tian_ting") or 0
        obj.lock_cards.extend(kwargs.get("lock_cards") or [])
        return obj

class S2CStartDingQueInfo:
    @classmethod
    def pb_model(cls,**kwargs):
        obj = ws_leisure_pb2.S2CStartDingQueInfo()
        obj.ding_que_list.extend(kwargs.get("ding_que_list") or [])
        obj.seconds = kwargs.get("seconds") or 0
        obj.recommend_que = kwargs.get("recommend_que") or 0
        return obj

class S2CDingQueInfo:
    @classmethod
    def pb_model(cls,**kwargs):
        obj = ws_leisure_pb2.S2CDingQueInfo()
        obj.que = kwargs.get("que") or 0
        obj.seat_id = kwargs.get("seat_id") or 0
        return obj

class S2CRoundOverInfo:

    @staticmethod
    def pack_ming_xi_info(obj, data_list:list):
        """ 打包结算明细信息 """
        for other_data in data_list:
            new_obj = obj.add()
            new_obj.check_type = other_data.get("check_type") or 0
            new_obj.card = other_data.get("card") or 0
            new_obj.score = other_data.get("score") or 0
            new_obj.hu_type = other_data.get("hu_type") or 0
            new_obj.get_bearer = other_data.get("get_bearer") or 0
            new_obj.lose_to.extend(other_data.get("lose_to") or [])
            new_obj.extra_hu_type.extend(other_data.get("extra_hu_type") or [])
            new_obj.win_from.extend(other_data.get("win_from") or [])

    @classmethod
    def pb_model(cls,**kwargs):
        obj = ws_leisure_pb2.S2CRoundOverInfo()
        obj.round_idx = kwargs.get("round_idx") or 0
        obj.has_next_round = kwargs.get("has_next_round") or 0
        obj.finish_type = kwargs.get("finish_type") or 0
        obj.curr_card = kwargs.get("curr_card") or 0
        obj.dealer = kwargs.get("dealer") or 0
        obj.is_huang_dealer = kwargs.get("is_huang_dealer") or 0
        obj.fan_ji_card = kwargs.get("fan_ji_card") or 0
        obj.left_cards.extend(kwargs.get("left_cards") or [])
        obj.all_ji.extend(kwargs.get("all_ji") or [])
        seats_data = kwargs.get("seats") or []
        for data in seats_data:
            seat = obj.seats.add()
            seat.seat_id = data.get("seat_id") or 0
            seat.round_score = data.get("round_score") or 0
            seat.total_score = data.get("total_score") or 0
            seat.jiao_pai = data.get("jiao_pai") or 0
            seat.fang_pao = data.get("fang_pao") or 0
            seat.hu_type = data.get("hu_type") or 0
            seat.is_zha_hu = data.get("is_zha_hu") or 0
            seat.ji_pai.extend(data.get("ji_pai") or [])
            men_cards = data.get("men_cards") or []
            seat.hand_cards.extend(data.get("hand_cards") or [])
            for men_data in men_cards:
                men_card = seat.men_cards.add()
                men_card.CopyFrom(S2CMenInfoMahjong.pb_model(**men_data))
            pack_table_cards(seat, **data)
            account_data = data.get("account") or {}
            seat.account.total_score = account_data.get("total_score") or 0
            ming_xi_data = account_data.get("ming_xi") or {}
            other_list = ming_xi_data.get("other") or []
            self_list = ming_xi_data.get("self") or []
            cls.pack_ming_xi_info(seat.account.ming_xi.other,other_list)
            cls.pack_ming_xi_info(seat.account.ming_xi.self,self_list)

        return obj

class S2CReqDismissRoom:
    @classmethod
    def pb_model(cls,**kwargs):
        obj = ws_leisure_pb2.S2CReqDismissRoom()
        obj.seat_id = kwargs.get("seat_id") or 0
        obj.agree = kwargs.get("agree") or False
        obj.agree_seats.extend(kwargs.get("agree_seats") or [])
        obj.total_time = kwargs.get("total_time") or 0
        obj.left_seconds = kwargs.get("left_seconds") or 0
        return obj

class S2CNotifyPosition:
    @classmethod
    def pb_model(cls,**kwargs):
        obj = ws_leisure_pb2.S2CNotifyPosition()
        obj.distances.extend(kwargs.get("distances") or [])
        return obj

class S2CGameOverInfo:

    @classmethod
    def pb_model(cls,**kwargs):
        obj = ws_leisure_pb2.S2CGameOverInfo()
        obj.time_stamp = kwargs.get("time_stamp") or 0
        obj.tid = kwargs.get("tid") or 0
        seats_data = kwargs.get("seats") or []
        for data in seats_data:
            seat = obj.seats.add()
            seat.seat_id = data.get("seat_id") or 0
            seat.uid = data.get("uid") or 0
            seat.total_score = data.get("total_score") or 0
            seat.diao_pao_count = data.get("diao_pao_count") or 0
            seat.jie_pao_count = data.get("jie_pao_count") or 0
            seat.zi_mo_count = data.get("zi_mo_count") or 0
            seat.ming_gang_count = data.get("ming_gang_count") or 0
            seat.dian_gang_count = data.get("dian_gang_count") or 0
            seat.an_gang_count = data.get("an_gang_count") or 0
            seat.zhuan_wan_gang_count = data.get("zhuan_wan_gang_count") or 0
        return obj

class S2CStartExchangeCards:
    @classmethod
    def pb_model(cls,**kwargs):
        obj = ws_leisure_pb2.S2CStartExchangeCards()
        obj.seconds = kwargs.get("seconds") or 0
        obj.in_flow = kwargs.get("in_flow") or 0
        return obj

class S2CKouFen:
    @classmethod
    def pb_model(cls,**kwargs):
        obj = ws_leisure_pb2.S2CKouFen()
        obj.win_seat_id = kwargs.get("win_seat_id") or 0
        obj.check_out_type = kwargs.get("check_out_type") or 0
        obj.win_gold = str(kwargs.get("win_gold") or 0)
        obj.winner_res_gold = str(kwargs.get("winner_res_gold") or 0)
        lose_list = kwargs.get("lose_list") or []
        for data in lose_list:
            lose = obj.lose_list.add()
            lose.lose_seat_id = data.get("lose_seat_id") or 0
            lose.lose_gold = str(data.get("lose_gold") or 0)
            lose.loser_res_gold = str(data.get("loser_res_gold") or 0)
        obj.extra_hu_type.extend(kwargs.get("extra_hu_type") or [])
        return obj

class S2CStartFanJi:
    @classmethod
    def pb_model(cls,**kwargs):
        obj = ws_leisure_pb2.S2CStartFanJi()
        obj.seconds = kwargs.get("seconds") or 0
        obj.can_fan_ji = kwargs.get("can_fan_ji") or False
        obj.fan_ji_list.extend(kwargs.get("fan_ji_list") or [])
        return obj

class S2CFanJi:
    @classmethod
    def pb_model(cls,**kwargs):
        obj = ws_leisure_pb2.S2CFanJi()
        obj.seat_id = kwargs.get("seat_id") or 0
        obj.fan_ji_card = kwargs.get("fan_ji_card") or 0
        return obj

class S2CFanJiInfo:
    @classmethod
    def pb_model(cls,**kwargs):
        obj = ws_leisure_pb2.S2CFanJiInfo()
        obj.fan_ji_cards.extend(kwargs.get("fan_ji_cards") or [])
        result = kwargs.get("result") or {}
        for data in result:
            seat = obj.result.add()
            seat.seat_id = data.get("seat_id") or 0
            seat.ji_cards.extend(data.get("ji_cards") or [])
        return obj

class S2CRecordAccountInfo:
    @classmethod
    def pb_model(cls,data_list:list):
        obj = ws_leisure_pb2.S2CRecordAccountInfo()
        for data in data_list:
            account = obj.result.add()
            account.curr_card = data.get("curr_card") or 0
            account.relation = data.get("relation") or 0
            account.multiple = data.get("multiple") or 0
            account.gold = str(data.get("gold") or 0)
            account.act = data.get("act") or 0
            account.win_from.extend(data.get("win_from") or [])
            account.lose_to.extend(data.get("lose_to") or [])
            account.hu_type.extend(data.get("hu_type") or [])
        return obj

class S2CFanJiScore:
    @classmethod
    def pb_model(cls,data_list:list):
        obj = ws_leisure_pb2.S2CFanJiScore()
        for data in data_list:
            fan_ji = obj.result.add()
            fan_ji.fan_ji_score = str(data.get("fan_ji_score") or 0)
            fan_ji.res_gold = str(data.get("res_gold") or 0)
            fan_ji.seat_id = data.get("seat_id") or 0
        return obj

class S2CRoundOverInfoByLeisure:
    @classmethod
    def pb_model(cls,**kwargs):
        obj = ws_leisure_pb2.S2CRoundOverInfoByLeisure()
        obj.round_idx = kwargs.get("round_idx") or 0
        obj.finish_type = kwargs.get("finish_type") or 0
        obj.curr_card = kwargs.get("curr_card") or 0
        obj.dealer = kwargs.get("dealer") or 0
        obj.left_cards.extend(kwargs.get("left_cards") or [])
        obj.winner.extend(kwargs.get("winner") or [])
        seats_data = kwargs.get("seats") or []
        for data in seats_data:
            seat = obj.seats.add()
            seat.seat_id = data.get("seat_id") or 0
            seat.win_gold = str(data.get("win_gold") or 0)
            seat.res_gold = str(data.get("res_gold") or 0)
            seat.is_win = data.get("is_win") or 0
            seat.jiao_pai = data.get("jiao_pai") or 0
            seat.fang_pao = data.get("fang_pao") or 0
            seat.hu_type = data.get("hu_type") or 0
            seat.hand_cards.extend(data.get("hand_cards") or [])
            seat.ji_pai.extend(data.get("ji_pai") or [])
            ji_score_data = data.get("ji_scores") or []
            for score in ji_score_data:
                ji = seat.ji_scores.add()
                ji.ji_card = score.get("ji_card") or 0
                ji.ji_count = score.get("ji_count") or 0
                ji.ji_score = score.get("ji_score") or 0
            pack_table_cards(seat, **data)
        return obj

class S2CManyHuInfo:
    @classmethod
    def pb_model(cls,**kwargs):
        obj = ws_leisure_pb2.S2CManyHuInfo()
        obj.curr_seat_id = kwargs.get("curr_seat_id") or 0
        obj.curr_card = kwargs.get("curr_card") or 0
        hu_list = kwargs.get("hu_list") or []
        for men_data in hu_list:
            hu_card = obj.hu_list.add()
            hu_card.CopyFrom(S2CMenInfoMahjong.pb_model(**men_data))
        return obj

class S2CChangeConnect:
    @classmethod
    def pb_model(cls,**kwargs):
        obj = ws_leisure_pb2.S2CChangeConnect()
        obj.seat_id = kwargs.get("seat_id") or 0
        obj.offline = kwargs.get("offline") or False
        return obj

class S2CRoomDismissInfo:
    @classmethod
    def pb_model(cls,**kwargs):
        obj = ws_leisure_pb2.S2CRoomDismissInfo()
        obj.game_begin = kwargs.get("game_begin") or False
        return obj

# ################################## 麻将 ##################################

# ################################## 茶馆通知 ##################################

class S2CClubRoomInfo:
    @classmethod
    def pb_mode(cls,**kwargs):
        obj = ws_leisure_pb2.S2CClubRoomInfo()
        obj.club_id = kwargs.get("club_id") or 0
        obj.created = kwargs.get("created") or 0
        obj.creator = kwargs.get("creator") or 0
        obj.cs_type = kwargs.get("cs_type") or 0
        obj.id = kwargs.get("id") or 0
        obj.is_friend = kwargs.get("is_friend") or 0
        obj.is_location = kwargs.get("is_location") or 0
        obj.max_player = kwargs.get("max_player") or 0
        obj.pay_type = kwargs.get("pay_type") or 0
        obj.platform = kwargs.get("platform") or 0
        obj.play_type = kwargs.get("play_type") or 0
        obj.price = kwargs.get("price") or 0
        obj.room_id = kwargs.get("room_id") or 0
        obj.room_type = kwargs.get("room_type") or 0
        pack_rule_details(obj, **kwargs)
        obj.seats.extend(kwargs.get("seats") or [])
        obj.total_round = kwargs.get("total_round") or 0
        obj.updated = kwargs.get("updated") or 0
        obj.msg_type = kwargs.get("msg_type") or 0
        obj.round_num = kwargs.get("round_num") or 1
        obj.online_group_user.extend(kwargs.get("online_group_user") or [])
        obj.status =  kwargs.get("status") or 0
        return obj

class S2CClubNotice:
    @classmethod
    def pb_model(cls,**kwargs):
        obj = ws_leisure_pb2.S2CClubNotice()
        obj.notice = kwargs.get("notice") or ""
        return obj

class S2CClubRoomSetInfo:
    @classmethod
    def pb_model(cls,**kwargs):
        obj = ws_leisure_pb2.S2CClubRoomSetInfo()
        obj.rank_members_only = kwargs.get("rank_members_only") or 0
        return obj


# ################################## 茶馆通知 ##################################


# ################################## ws大厅通知 ##################################
class S2CTopAnnouncements:

    @classmethod
    def pb_model(cls, data_list):
        obj = ws_leisure_pb2.S2CTopAnnouncements()
        # data_list = kwargs.get("announcement_list") or {}

        for data in data_list:
            m = obj.announcement.add()
            m.title = data.get("title") or ''
            m.content = data.get("content") or ''
            m.start_time = data.get("start_time") or 0
            m.end_time = data.get("end_time") or 0
            m.target_group = data.get("target_group") or 0
            m.carousel_count = data.get("carousel_count") or 0
            m.status = data.get("status") or 0
            m.weight = data.get("weight") or 1
        return obj

# ################################## ws大厅通知 ##################################
