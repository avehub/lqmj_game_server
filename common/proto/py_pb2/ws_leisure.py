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

    obj.base_room_info.room_conf.max_player = rule_conf.get("max_player")
    obj.base_room_info.room_conf.total_round = rule_conf.get("total_round")

    obj.base_room_info.min_take = room_conf.get("min_take") or 0
    obj.base_room_info.max_take = room_conf.get("max_take") or 0
    obj.base_room_info.base_score = room_conf.get("base_score") or 0
    obj.base_room_info.desc = room_conf.get("desc") or ""
    obj.base_room_info.level = room_conf.get("level") or 0

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
