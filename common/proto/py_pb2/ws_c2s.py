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
tian_ting_model = ws_leisure_pb2.C2STianTingInfo()
