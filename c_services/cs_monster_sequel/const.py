from common.public.base_enum import BaseEnum
from common.proto.pb2 import ws_leisure_pb2

CardArea = ws_leisure_pb2.CardArea


class CardCapability(BaseEnum):
    """ 卡牌能力 """
    C0 = 0, "没任何能力"
    C1 = 1, "霸波儿奔 可以和奔波儿霸组合打出，大过任何单牌"
    C2 = 2, "金角大王 可以无视上1张牌打出，并将上家出的牌从出牌区转移到自己的磨难区"
    C3 = 3, "牛魔王 可以跟在孙悟空后面打出"
    C4 = 4, "铁扇公主 可以改变出牌方向为反转"
    C5 = 5, "唐三藏 可以和白龙马同时打出，拿取徒弟区最上方2张牌（不再执行补牌操作）"
    C6 = 6, "观音菩萨 可以选择从哪里补牌"

    C7 = 7, "六耳猕猴能力：如果徒弟区无孙悟空，则可视作孙悟空打出到徒弟区"
    C8 = 8, "猪八戒能力：将场上(仙佛区)的小白龙加到手牌"
    C9 = 9, "孙悟空能力：徒弟区（出牌区）的假悟空放到妖怪底部"


# 卡牌阵营分
CARD_CAMP_SCORE = {
    CardArea.MONSTER: 3,
    CardArea.PRENTICE: 5,
    CardArea.MASTER: 10,
    CardArea.DIVINE: 8,
}


class ActType(BaseEnum):
    """ 动作类型 """
    A1 = 1, "出牌"
    A2 = 2, "收牌"
    A3 = 3, "铁扇，改变出牌顺序"
    A4 = 4, "铁扇，不改变出牌顺序"
    A5 = 5, "观音，选择从徒弟区复制一张牌"
    A6 = 6, "观音，选择从师傅区复制一张牌"
    A7 = 7, "观音，选择从剩余牌堆补牌"
