import tortoise
from sanic import Request
from c_services.const.cs_enum_const import CmdWorkers
from common.public.conf import R_UID_THRESHOLD, ROBOT_AVATAR
from common.public.enum_const import Sex, ServiceEnum, CacheKey, GameType
from lucky_game.base_api import GameAuthApi
from lucky_game.const import RED_DOTS_OPPORTUNITY_MAP, ActivityItem
from lucky_game.model_db.extra import RecordsGameGrade
from lucky_game.model_rc.base_activity import UserActivityRC
from lucky_game.model_rc.base_ranking import ConfSeasonRC, UserRankingRC
from lucky_game.model_rc.base_skin import UserSkinRC
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.model_rc.base_robot import BaseRobotRC
from lucky_game.model_rc.conf_leisure import LeisureConfRC
from lucky_game.model_rc.player_game_times import PlayerGameTimesRC
from common.utils.utils import UtilsTool
from lucky_game.model_rc.vip_level import UserVipRC
from common.proto.py_pb2.common import get_one_of_model


class QueryUserInfo(GameAuthApi):
    """ 查询用户信息（一般桌子内使用） """

    async def get(self, req: Request, **_b):

        r_user_model = {}
        uid = self.check_int(req.args.get("uid"), require=True, minval=100000, p_name="uid")
        if uid > R_UID_THRESHOLD:
            user_info = await BaseUserRC.cache_by_uid(uid)
            vip_info = await UserVipRC.get_vip_conf_by_uid(uid)
            ur_data = await UserRankingRC.cache_by_unique(uid, u_info=user_info) or {}
            r_user_model["vip_level"] = vip_info.get("level")
            r_user_model["ranking_id"] = ur_data.get("ranking_id") or 0
        else:
            user_info = await BaseRobotRC.cache_by_pk(uid) or {}
            avatar = user_info.get("avatar") or ""
            user_info["avatar"] = ROBOT_AVATAR + avatar if avatar else ""

        r_user_model["name"] = user_info.get("name") or ""
        r_user_model["uid"] = user_info.get("uid") or 0
        r_user_model["sex"] = user_info.get("sex") or Sex.DEFAULT
        r_user_model["address"] = user_info.get("address") or ""
        r_user_model["avatar"] = user_info.get("avatar") or ""

        return self.answer(data=r_user_model)


class RefreshAssets(GameAuthApi):
    """ 刷新玩家资产 """

    async def get(self, _: Request, **kwargs):
        u_info = kwargs.get("u_info")
        data = {
            "gold": u_info.get("gold"),
            "diamond": u_info.get("diamond")
        }
        return self.answer(data=data)


class GetLeisureList(GameAuthApi):
    """ 获取休闲场列表 """

    async def get(self, req: Request, **kwargs):
        cs_type = self.check_int(req.args.get("cs_type"), require=True, p_name="cs_type")
        cs_enum = ServiceEnum.find_member_by_val(cs_type)
        not cs_enum and self.answer(self.sta_code.ERR_ARG)
        if not isinstance(cs_enum.desc, GameType) or cs_enum.desc != GameType.LEISURE:
            self.answer(self.sta_code.ERR_ARG, hint="非休闲场")

        data = await LeisureConfRC.cache_all_by_cs_type(cs_type=cs_type)
        return self.answer(data=data)


class QueryUserAdditionInfo(GameAuthApi):
    """查询玩家加成信息（准备界面使用）"""

    async def get(self, _, **kwargs):
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")

        season_conf = await ConfSeasonRC.get_current_season()
        (not season_conf) and self.answer(self.sta_code.NOT_WITHIN_VALID_PERIOD, hint="赛季即将开放，敬请期待！")

        add_info = {}
        # 终生卡修为加成
        conf_lifetime = await UserActivityRC.check_top_lifetime_card(uid)
        if conf_lifetime:
            add_info['lifetime_addition'] = conf_lifetime.get("ranking_addition", 0)

        # vip修为加成
        conf_vip = await UserVipRC.get_vip_conf_by_uid(uid)
        add_info['vip_addition'] = conf_vip.get("ranking_addition", 0)

        return self.answer(data=add_info)


class QueryUserGameStates(GameAuthApi):
    """ 查询玩家游戏情况 """

    async def get(self, req: Request, **_b):

        cs_type = self.check_int(req.args.get("cs_type"), require=True, minval=ServiceEnum.C_WORKERS, p_name="cs_type")
        if not ServiceEnum.find_member_by_val(cs_type):
            self.answer(self.sta_code.ERR_ARG, hint="参数错误")

        uid = self.check_int(req.args.get("uid"), require=True, minval=100000, p_name="uid")
        if uid > R_UID_THRESHOLD:
            p_data = await PlayerGameTimesRC.cache_multiterm_by_cond({"uid": uid}) or []
            win_count_key = "win_count"
            game_count_key = "total_count"

            game_data = [i for i in p_data if i.get("cs_type") == cs_type]
        else:
            r_data = await BaseRobotRC.cache_by_pk(uid)
            game_data = [r_data] if r_data else []

            win_count_key = f"game_win_count_{cs_type}"
            game_count_key = f"game_count_{cs_type}"

        if not game_data:
            self.answer(self.sta_code.PASS, hint="无数据")

        total_count = 0
        total_win_count = 0
        for one_data in game_data:
            win_count = one_data.get(win_count_key) or 0
            game_count = one_data.get(game_count_key) or 0

            total_count += game_count
            total_win_count += win_count

            one_data["win_rate"] = UtilsTool.get_percent((win_count / game_count) * 100)

        win_rate = UtilsTool.get_percent((total_win_count / total_count) * 100)
        data = {
            "total_count": total_count,
            "win_rate": win_rate,  # 胜率
            "games_info": game_data
        }
        self.answer(data=data)


class QueryUserAllNumOfGames(GameAuthApi):
    """ 查询玩家总对局数 """

    async def get(self, req: Request, **_b):

        uid = self.check_int(req.args.get("uid"), require=True, minval=100000, p_name="uid")
        if uid > R_UID_THRESHOLD:
            game_data = await PlayerGameTimesRC.cache_multiterm_by_cond({"uid": uid})
            win_count_key = "win_count"
            game_count_key = "total_count"
        else:
            r_data = await BaseRobotRC.cache_by_pk(uid)
            game_data = [r_data] if r_data else []
            win_count_key = "game_win_count_5"
            game_count_key = "game_count_5"

        if not game_data:
            self.answer(self.sta_code.PASS, hint="无数据")

        total_count = 0
        total_win_count = 0
        for one_data in game_data:
            win_count = one_data.get(win_count_key, 0)
            game_count = one_data.get(game_count_key, 0)

            total_count += game_count
            total_win_count += win_count

        if total_count == 0:
            self.answer()
        else:
            win_rate = UtilsTool.get_percent((total_win_count / total_count) * 100)
            data = {
                "total_count": total_count,
                "win_rate": win_rate  # 胜率
            }
            self.answer(data=data)


class QueryUserGameGrade(GameAuthApi):
    """ 查询玩家游戏战绩 """

    async def get(self, req: Request, **kwargs):
        cs_type = self.check_int(req.args.get("cs_type"), require=True, minval=ServiceEnum.C_WORKERS, p_name="cs_type")
        if not ServiceEnum.find_member_by_val(cs_type):
            self.answer(self.sta_code.ERR_ARG, hint="参数错误")

        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        query_params = {"uid": uid, "cs_type": cs_type}
        try:
            data = await RecordsGameGrade.get_by_dict(query_params, limit=15)
        except tortoise.exceptions.OperationalError:
            data = {}
        if not data:
            self.answer(self.sta_code.PASS, hint="无数据")

        data_model = {"games_info": data}
        self.answer(data={"games_info": data})


class FetchRedDotsByOpportunity(GameAuthApi):
    """根据时机拉取红点"""

    async def get(self, req: Request, **kwargs):
        rd_enum = self.check_int(req.args.get("rd_enum"), require=True, p_name="rd_enum")
        # 1.批量获取红点（前端确定WS已经建立连接之后调用）
        # 该列表只能客户端在某些时机调用
        rd_type_list = RED_DOTS_OPPORTUNITY_MAP.get(rd_enum)
        if not rd_type_list:
            self.answer(hint="ok")

        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        cache_key = f"req_limit:{uid}:{req.server_path}:{rd_enum}"

        incr_value = await self.conf.rds.conn.incr(cache_key)
        await self.conf.rds.expired(cache_key, 60)  # 设置键过期时间

        if incr_value > 3:  # 60秒内只能调3次
            self.answer(code=self.sta_code.REQ_FREQUENT)

        await self.push_task2worker(CmdWorkers.GET_RED_DOT_LIST, msg={"rd_type_list": rd_type_list}, uid=uid)

        self.log_info(uid, '获取红点>>', rd_type_list)
        return self.answer(hint="OK!")


class QueryUserVipLevel(GameAuthApi):
    """ 查询用户VIP等级 """

    async def get(self, req: Request, **_b):
        uid = self.check_int(req.args.get("uid"), require=True, minval=1000, p_name="uid")

        if uid >= R_UID_THRESHOLD:
            vip_info = await UserVipRC.get_vip_conf_by_uid(uid)
            vip_level = vip_info.get("level") or 0
        else:
            user_info = await BaseRobotRC.cache_by_pk(uid)
            vip_info = user_info.get("extra_info")
            vip_level = vip_info.get("vip_level", 0) if vip_info else 0

        one_of_model = get_one_of_model()
        one_of_model.vip_level = vip_level
        return self.answer(self.sta_code.PASS, data=one_of_model)


class QueryUserSkinAmount(GameAuthApi):
    """
    查询玩家持有法相数
    限时不计、同款法相不论上下篇只计一个
    """

    async def get(self, _, **kwargs):
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")

        all_skins = await UserSkinRC.cache_user_skin(uid) or []
        held_skins = set()
        if all_skins:
            for skin in all_skins or []:
                if skin.get("exp_time", 0) == 0:
                    held_skins.add(skin.get("skin_public_id"))

        skin_amount = len(held_skins)
        if skin_amount < 4:
            self.log_info(uid, f"玩家的持有法相数量{skin_amount}不足4个，请检查初始化")
        one_of_model = get_one_of_model()
        one_of_model.skin_amount = skin_amount
        return self.answer(self.sta_code.PASS, data=one_of_model)


class QueryUserAdFreePrivilege(GameAuthApi):
    """
    查询用户免广告特权
    1.铂金周卡
    """

    async def get(self, _, **kwargs):
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")

        check_res = await UserActivityRC.verify_activation(uid, ActivityItem.WEEK_CARD_2)
        one_of_model = get_one_of_model()
        one_of_model.switch = check_res
        return self.answer(self.sta_code.PASS, data=one_of_model)


class QueryChatUserInfo(GameAuthApi):
    """ 查询聊天用户信息 """

    # todo:VIP等级、排位等级、装扮等即时性要求不高，可通过web接口查询（可重新封装一个查询聊天信息的借口）

    async def get(self, req: Request, **_b):
        uid = self.check_int(req.args.get("uid"), require=True, minval=1000, p_name="uid")

        pass
