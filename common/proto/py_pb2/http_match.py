from common.proto.pb2 import http_match_pb2
from common.proto.py_pb2 import http_player_vault


class PbSeasonRankingConf():
    __proto = http_match_pb2.S2CSeasonRankingConf()

    @classmethod
    def pb_model(cls, data: dict):
        """ 消息模型(非序列化) """
        cls.__proto.Clear()

        # 1.赛季信息
        ss_conf = data.get("season_conf") or {}
        pack_season_conf(cls.__proto, **ss_conf)

        # 2.赛季奖励（段位奖/结算奖）
        awards_items = data.get("season_awards_items") or []
        cls.pack_awards_items(awards_items)

        return cls.__proto

    @classmethod
    def pack_awards_items(cls, awards_items):
        """ 打包奖励项 """
        for one_items in awards_items:  #
            one_award_obj = cls.__proto.awards_list.add()
            one_award_obj.ranking_id = one_items.get("id") or 0

            # 段位突破奖励
            level_awards = one_items.get("level_awards") or []
            for c in level_awards or []:
                c_obj = one_award_obj.level_awards.add()
                http_player_vault.pack_goods_items(c_obj, **c)

            # 赛季奖励（结算）
            season_awards = one_items.get("season_awards") or []
            for c in season_awards or []:
                s_obj = one_award_obj.season_awards.add()
                http_player_vault.pack_goods_items(s_obj, **c)

            # 显示奖励
            display_awards = one_items.get("display_awards") or []
            for c in display_awards or []:
                d_obj = one_award_obj.display_awards.add()
                http_player_vault.pack_goods_items(d_obj, **c)


class PbPlayerRankingInfo():
    __proto = http_match_pb2.S2CPlayerRankingInfo()

    @classmethod
    def pb_model(cls, data: dict):
        """ 消息模型(非序列化) """
        cls.__proto.Clear()

        # 1.玩家排位信息
        p_rk_data = data.get("player_ranking_data") or []
        cls.pack_player_ranking_data(p_rk_data)

        # 2.所有排位数据
        all_rk_data = data.get("all_ranking_data") or []
        for k in all_rk_data or []:
            ard = cls.__proto.all_ranking_data.add()
            pack_all_ranking_data(ard, **k)

        # 3.赛季信息
        ss_conf = data.get("season_conf") or {}
        pack_season_conf(cls.__proto, **ss_conf)

        return cls.__proto

    @classmethod
    def pack_player_ranking_data(cls, data: list):
        """ 打包用户排位数据 """
        for o in data:
            obj = cls.__proto.player_ranking_data.add()
            obj.uid = o.get("uid") or 0
            obj.ranking_id = o.get("ranking_id") or 0
            obj.cur_score = o.get("cur_score") or 0


class PbUserRankingInfo():
    __proto = http_match_pb2.S2CUserRankingInfo()

    @classmethod
    def pb_model(cls, data: dict):
        """ 消息模型(非序列化) """
        cls.__proto.Clear()

        # 1.自己排位信息
        u_rk_data = data.get("self_ranking_data") or {}
        cls.pack_user_ranking_data(**u_rk_data)

        # 2.下一个排位ID
        cls.__proto.next_ranking_id = data.get("next_ranking_id") or 0

        # 3.所有排位数据
        all_rk_data = data.get("all_ranking_data") or []
        for k in all_rk_data or []:
            ard = cls.__proto.all_ranking_data.add()
            pack_all_ranking_data(ard, **k)

        return cls.__proto

    @classmethod
    def pack_user_ranking_data(cls, **kwargs):
        """ 打包用户排位数据 """
        cls.__proto.ranking_data.ranking_id = kwargs.get("ranking_id") or 0
        cls.__proto.ranking_data.cur_score = kwargs.get("cur_score") or 0
        cls.__proto.ranking_data.top_score = kwargs.get("top_score") or 0
        cls.__proto.ranking_data.top_ranking_id = kwargs.get("top_ranking_id") or 0
        cls.__proto.ranking_data.level_awards_sta = kwargs.get("level_awards_sta") or '[]'
        cls.__proto.ranking_data.game_count = kwargs.get("game_count") or 0
        cls.__proto.ranking_data.region = kwargs.get("region") or 0


def pack_all_ranking_data(obj, **kwargs):
    obj.id = kwargs.get("id") or 0
    obj.level = kwargs.get("level") or 0
    obj.ranking_name = kwargs.get("ranking_name") or ""
    obj.min_score = kwargs.get("min_score") or 0
    obj.max_score = kwargs.get("max_score") or 0
    obj.lv_defend = kwargs.get("lv_defend") or 0
    obj.major_level = kwargs.get("major_level") or 0
    obj.minor_level = kwargs.get("minor_level") or 0
    obj.lose_score = kwargs.get("lose_deduct_score") or 0
    obj.lose_score_seq = kwargs.get("lose_deduct_score_seq") or 0


def pack_season_conf(obj, **kwargs):
    obj.season_conf.season_id = kwargs.get("season_id") or 1
    obj.season_conf.season_name = kwargs.get("season_desc") or ''
    obj.season_conf.start_time = kwargs.get("start_time") or 0
    obj.season_conf.end_time = kwargs.get("end_time") or 0
    obj.season_conf.game_condition = kwargs.get("condition") or 0
    obj.season_conf.status = kwargs.get("status") or 0
    obj.season_conf.img_url = kwargs.get("img_url") or ''


class S2CRankingList():
    __proto = http_match_pb2.S2CRankingList()

    @staticmethod
    def pack_ranking_world(rw_obj, info: dict):
        rw_obj.uid = info.get("uid") or 0
        rw_obj.u_name = info.get("u_name") or ''
        rw_obj.sex = info.get("sex") or 0
        rw_obj.u_avatar = info.get("u_avatar") or ''
        rw_obj.cur_score = info.get("cur_score") or 0
        rw_obj.top_score = info.get("top_score") or 0
        rw_obj.r_name = info.get("r_name") or ""
        rw_obj.avatar_frame = info.get("avatar_frame") or 0

    @classmethod
    def pb_model(cls, **data: dict):
        cls.__proto.Clear()

        ranking_data = data.get("ranking_list") or []
        for rd in ranking_data:
            rw_obj = cls.__proto.rank_list.add()
            cls.pack_ranking_world(rw_obj, rd)

        cls.__proto.self_ranking = data.get("self_ranking") or 0
        return cls.__proto
