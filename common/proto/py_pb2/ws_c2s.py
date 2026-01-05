from common.proto.pb2 import ws_leisure_pb2


class C2SEnterLeisure:
    """ 进入休闲场 """
    __proto = ws_leisure_pb2.C2SEnterLeisure()

    @classmethod
    def decode(cls, msg):
        cls.__proto.ParseFromString(msg)
        return cls.__proto


play_card_model = ws_leisure_pb2.C2SPlayCards()
# quick_chat_model = ws_leisure_pb2.C2SQuickChat()

# 能力模型
ability_reverse_model = ws_leisure_pb2.C2SAbilityReverse()
ability_select_area_model = ws_leisure_pb2.C2SAbilitySelectArea()


def reverse_model():
    dm = ws_leisure_pb2.C2SAbilityReverse()
    dm.yes = True
    return dm
#麻将
gang_model = ws_leisure_pb2.C2SGangInfo()
shang_ga_model = ws_leisure_pb2.C2SShangGaInfo()
exchange_model = ws_leisure_pb2.C2SExchangeCardsInfo()
req_dismiss_model = ws_leisure_pb2.C2SReqDismissRoom()
enter_room_model = ws_leisure_pb2.C2SEnterRoom()
set_cards_model = ws_leisure_pb2.C2SSetCard()
ding_que_model = ws_leisure_pb2.C2SDingQue()
fan_ji_index_model = ws_leisure_pb2.C2SFanJi()
player_position_model = ws_leisure_pb2.C2SPlayerPosition()

#茶馆
leave_club_model = ws_leisure_pb2.C2SLeaveClubRoom()
club_room_set_model = ws_leisure_pb2.C2SClubRoomSetInfo()

# 比赛
join_competition_model = ws_leisure_pb2.C2SJoinCompetition()
