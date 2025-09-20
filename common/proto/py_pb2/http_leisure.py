from common.proto.pb2 import http_leisure_pb2
from common.proto.py_pb2.ws_leisure import S2CBrokeBroad
from common.utils.kit_dt import KitDt

S2CRoomUserInfo = http_leisure_pb2.S2CRoomUserInfo


class PbLeisure():
    __proto = None

    @classmethod
    def pb_model(cls, data: list):
        """ 消息模型 """
        """
        uint32 id = 1;
        uint32 created = 2;
        uint32 sid = 3;
        string addr = 4;
        string path = 5;
        uint32 status = 6;
        """
        cls.__proto = http_leisure_pb2.S2CLeisureList()
        for one_data in data:
            obj = cls.__proto.leisure_list.add()
            PbOneLeisure.pb_model(obj, **one_data)
        return cls.__proto


class PbOneLeisure:
    __proto = http_leisure_pb2.S2CLeisureList.OneRowData()

    @classmethod
    def pb_model(cls, obj=None, **kwargs):
        """ 消息模型 """
        """
        uint64 min_take = 1;  // 最低携带
        int64 max_take = 2;  // 最高携带
        uint64 base_score = 3;  // 底分
        uint64 price = 4;  // 门票
        uint32 status = 5;  // 状态
        string desc = 6;  // 描述
        uint32 cs_type = 7;  // 服务号
        uint32 id = 8;
        uint32 level = 9;  // 等级
        RuleConf rule_conf = 10;  // 规则配置
        """
        obj = obj or cls.__proto
        obj.min_take = kwargs.get("min_take")
        obj.max_take = kwargs.get("max_take")
        obj.base_score = kwargs.get("base_score")
        obj.price = kwargs.get("price")
        obj.status = kwargs.get("status")
        obj.desc = kwargs.get("desc")
        obj.cs_type = kwargs.get("cs_type")
        obj.id = kwargs.get("id")
        obj.level = kwargs.get("level")
        obj.level = kwargs.get("level")
        rule_conf = kwargs.get("rule_conf") or {}
        gift_item = kwargs.get("gift_conf") or []
        obj.rule_conf.max_player = rule_conf.get("max_player") or 0
        obj.rule_conf.total_round = rule_conf.get("total_round") or 0
        obj.ranking_addition = kwargs.get("ranking_addition") or 0
        for gift_conf in gift_item:
            S2CBrokeBroad.pack_gift(obj, gift_conf)

        obj.ranking_addition = kwargs.get("ranking_addition") or 0


class S2CUserGameStates:

    @staticmethod
    def pack_one_game_states(obj, **kwargs):
        """ 打包一个玩法的游戏情况 """
        obj.play_type = kwargs.get("play_type") or 0
        obj.games_count = kwargs.get("total_count") or 0
        obj.win_rate = kwargs.get("win_rate") or 0.0
        obj.max_win_streak = kwargs.get("max_win_streak") or 0
        obj.max_multiple = kwargs.get("max_multiple") or 0

    @classmethod
    def pb_model(cls, **kwargs):
        obj = http_leisure_pb2.S2CUserGameStates()
        obj.total_count = kwargs.get("total_count") or 0
        obj.win_rate = kwargs.get("win_rate") or ""

        game_list = kwargs.get("games_info") or []
        for one_game in game_list:
            one_obj = obj.game_states.add()
            S2CUserGameStates.pack_one_game_states(one_obj, **one_game)
        return obj


class S2CUserGameGrade:

    @staticmethod
    def pack_one_game_grade(obj, **kwargs):
        """ 打包一个玩法的游戏情况 """
        obj.cs_type = kwargs.get("cs_type") or 0
        obj.play_type = kwargs.get("play_type") or 0
        obj.score = kwargs.get("score") or 0
        obj.rank_score = kwargs.get("rank_score") or 0
        obj.is_win = kwargs.get("is_win") or 0
        obj.level_desc = kwargs.get("level_desc") or ''
        obj.game_time = KitDt.timestamp_2_time_str(kwargs.get("created") or 0)

    @classmethod
    def pb_model(cls, **kwargs):
        obj = http_leisure_pb2.S2CUserGameGrade()

        game_list = kwargs.get("games_info") or []
        for one_game in game_list:
            one_obj = obj.game_grade.add()
            S2CUserGameGrade.pack_one_game_grade(one_obj, **one_game)
        return obj


class PbUserAdditionInfo():
    __proto = http_leisure_pb2.S2CUserAdditionInfo()

    @classmethod
    def pb_model(cls, data: dict):
        """ 消息模型(非序列化) """
        cls.__proto.Clear()

        # 1.终生卡修为加成
        cls.__proto.lifetime_addition = data.get("lifetime_addition") or 0
        # 2.vip修为加成
        cls.__proto.vip_addition = data.get("vip_addition") or 0

        return cls.__proto


class PbQuickChat():
    __proto = None

    @classmethod
    def pb_model(cls, data: list):
        """ 消息模型 """
        __proto = http_leisure_pb2.S2CQuickChatList()

        for i in data or []:
            if i:
                obj = __proto.quick_chat_conf.add()
                pack_quick_chat_conf(obj, **i)
        return __proto


def pack_quick_chat_conf(obj, **kwargs):
    """ 打包快捷聊天配置 """
    obj.chat_id = kwargs.get("chat_id") or 0
    obj.chat_name = kwargs.get("chat_name") or ''
    obj.chat_type = kwargs.get("chat_type") or 0
    obj.price = kwargs.get("price") or 0
    obj.img_url = kwargs.get("img_url") or ''
    obj.cool_down = kwargs.get("cool_down") or 0
    obj.pay_type = kwargs.get("pay_type") or 0
    obj.level = kwargs.get("level") or 1
    obj.free_act_type = kwargs.get("free_act_type") or 0
