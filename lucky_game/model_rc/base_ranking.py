"""
排行榜模型
"""
import math
import orjson
from types import SimpleNamespace
from nsanic.libs import tool_dt
from nsanic.libs.tool import json_encode, json_parse
from nsanic.orm.rc_model import RCModel
from common.public.conf import ROBOT_RANK, ROBOT_AVATAR
from common.public.enum_const import RegionEnum, REGION_ENUM_MAP
from common.utils.utils import UtilsTool
from lucky_game.const import SeasonStatus, LvDefendType, CompleteSta
from lucky_game.model_db.main import ConfRanking, UserRanking, ConfSeason, ConfRankingMatchTime
from lucky_game.model_rc.base_rc import BaseRC
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.model_rc.conf_json import ConfJsonRC
from lucky_game.model_rc.goods_manager import GoodsManagerRC


class ConfSeasonRC(RCModel):
    """ 赛季模型 """
    db_model = ConfSeason
    tb_name = db_model.sheet_name()

    @classmethod
    async def update_cache(cls, s_info: dict):
        await cls.conf.rds.set_item(cls.tb_name, json_encode(s_info), ex_time=cls.expired_sec)

    @classmethod
    async def get_next_id(cls, season_id: int) -> int:
        next_season = await cls.db_model.filter(
            season_id__gt=season_id, status__not=SeasonStatus.OUT_OF_TIME).order_by('season_id').first()
        return next_season.season_id if next_season else season_id

    @staticmethod
    def __model_data(model: ConfSeason):
        data = {
            'season_id': model.season_id,
            'season_desc': model.season_desc,
            'start_time': model.start_time,
            'end_time': model.end_time,
            'off_season_time': model.off_season_time,
            'status': model.status,
            'condition': model.condition,
            'img_url': model.img_url
        }
        return data

    @classmethod
    async def update_season_info(cls, season_id, new_info, old_info):
        await cls.db_model.update_by_pk(season_id, new_info, old_info, fun_success=cls.update_cache)

    @classmethod
    async def get_current_season(cls):
        """
        根据当前时间获取当前赛季记录，包括边界
        赛季：某段时间（start_time - end_time）
        当只有一个赛季时，永远不会过期
        """

        async def from_db():
            # one_model = await cls.db_model.filter(Q(start_time__lte=time_node), Q(end_time__gte=time_node)).first()
            model_list = await cls.db_model.filter(status__not=SeasonStatus.OUT_OF_TIME)
            if not model_list:
                return {}

            if len(model_list) >= 2:
                model_list.sort(key=lambda m: m.start_time)
                u_model = model_list[0]  # update
                r_model = model_list[1]  # return
                # 如果当前时间大于等于最新的开赛时间
                if time_node >= r_model.start_time:
                    if u_model.status != SeasonStatus.OUT_OF_TIME:
                        u_model.status = SeasonStatus.OUT_OF_TIME
                        await u_model.save()

                    if r_model.status != SeasonStatus.ACTIVE_SEASON:
                        r_model.status = SeasonStatus.ACTIVE_SEASON
                        await r_model.save()
                else:
                    if cls.__check_model(u_model, time_node):
                        await u_model.save()
                    # 过期则返回新赛季
                    if u_model.status == SeasonStatus.OUT_OF_TIME:
                        u_model = r_model
                    data = cls.__model_data(u_model)
                    await cls.update_cache(data)
                    return data
            else:
                r_model = model_list[0]
                if cls.__check_model(r_model, time_node):
                    await r_model.save()

            data = cls.__model_data(r_model)
            await cls.update_cache(data)
            return data

        key_name = cls.tb_name
        res = await cls.conf.rds.get_item(key_name)
        time_node = tool_dt.cur_time()
        if res:
            # 此处仅返回当前 赛季信息，大于该赛期间则查表
            season_res = json_parse(res, cls.logerr)
            s_status = season_res.get('status')
            if time_node >= season_res.get("start_time", 0):
                model = SimpleNamespace(**season_res)
                if cls.__check_model(model, time_node):
                    await cls.update_season_info(model.season_id, {"status": model.status}, season_res)
                # if model.status != SeasonStatus.OUT_OF_TIME and time_node < season_res.get("next_season_time", 0):
                if model.status != SeasonStatus.OUT_OF_TIME:
                    return season_res
            elif s_status == SeasonStatus.NEXT_SEASON:
                return season_res

        return await cls.conf.rds.locked(key_name, fun=from_db)

    @classmethod
    def __check_model(cls, model, time_node):
        """
        检查当前model的状态
        根据时间节点相应更改赛季状态
        """
        if model.start_time < time_node < model.end_time:
            if model.status != SeasonStatus.ACTIVE_SEASON:
                model.status = SeasonStatus.ACTIVE_SEASON
                return True
        # 休赛期
        # elif model.end_time < time_node < (model.end_time + model.off_season_time):
        elif model.end_time < time_node:
            if model.status == SeasonStatus.DAN_RESET:
                model.status = SeasonStatus.OUT_OF_TIME
                return True
            if model.status != SeasonStatus.OFF_SEASON:
                model.status = SeasonStatus.OFF_SEASON
                return True
        return False

    @classmethod
    async def add_season(cls, **kwargs):
        """ 添加赛季 """
        model_list = await ConfSeasonRC.db_model.filter(status__not=SeasonStatus.OUT_OF_TIME)
        # if len(model_list) >= 2:
        #     return False, "非过期赛季，最多只能配置两个！"
        model_list.sort(key=lambda m: m.start_time)
        start_time = kwargs.get("start_time", 0)
        cur_time = tool_dt.cur_time()
        if start_time < cur_time:
            return False, "开始时间不能小于当前时间！"
        if start_time > kwargs.get("end_time", 0):
            return False, "开始时间不能小于结束时间！"
        last_sm = None
        if model_list:
            last_sm = model_list[-1]  # season model
            if kwargs.get("status", 0) != SeasonStatus.NEXT_SEASON:
                return False, f"赛季状态错误，新赛季应为即将开始状态！{kwargs.get('status', 0)}"
            # if start_time < last_sm.end_time + last_sm.off_season_time * 2:
            if start_time < last_sm.end_time + last_sm.off_season_time:
                return False, f"开始时间不能在上赛季休赛期和重置期之内！, {last_sm.season_id}"
            # 该条判断主要为玩家修为分重置预留时间，重置条件需要配置下一个赛季。（可能当前赛季已经是分数重置状态了，但此时才配置下一赛季）
            if start_time < cur_time + last_sm.off_season_time:
                return False, f"开始时间需要为上个赛季预留分数重置期！, {last_sm.season_id}"
        sta = await cls.db_model.add_one(kwargs)
        if sta:
            return sta, last_sm

        return False, ''


class ConfRankingRC(BaseRC):
    """ 排行榜配置模型 """
    db_model = ConfRanking
    tb_name = db_model.sheet_name()

    @staticmethod
    def get_ranking_data_by_score(ranking_conf, score):
        """ 根据分数获取具体配置 """
        idx = UtilsTool.binary_search(
            ranking_conf, score, inner=True, min_field="min_score", max_field="max_score", max_field_inf=True
        )
        if isinstance(idx, int):
            return ranking_conf[idx]
        return {}

    @classmethod
    async def get_ranking_items(cls, season_id: int, is_lock=True):
        """缓存所有排位配置+打包"""
        return await cls.cache_all_conf_item(
            has_status=False,
            orders="level",
            key_name=f'{cls.tb_name}:{season_id}',
            cond={"season_id": season_id},
            is_lock=is_lock
        )

    @classmethod
    async def get_season_awards_items(cls, season_id: int, is_all=False):
        """ 获取赛季奖励 """
        ranking_data = await cls.get_ranking_items(season_id)
        awards_data = [
            {
                "id": one_data.get("id"),
                "level_awards": one_data.get("level_awards"),
                "season_awards": one_data.get("season_awards"),
                "display_awards": one_data.get("display_awards"),
            }
            for one_data in ranking_data
        ]
        if awards_data:
            await GoodsManagerRC.pack_goods_many_conf(awards_data, is_all=is_all)
            awards_data.sort(key=lambda x: x["id"])
            return awards_data, ranking_data

        return [], []


class ConfRankingMatchTimeRc(RCModel):
    """ 段位匹配时间 """
    expired_sec = 60 * 60 * 24 * 7
    db_model = ConfRankingMatchTime
    tb_name = db_model.sheet_name()

    @classmethod
    async def cache_all_ranking_match_time(cls, season_id: int):
        """ 缓存所有排位等级匹配时间 """

        async def from_db():
            data_list = await cls.db_model.filter().select_related("ranking").filter(ranking__season_id=season_id)
            data_map = {}
            for one_data in data_list:
                data_map[str(one_data.ranking.level)] = {
                    "first_expend_time": one_data.first_expend_time,
                    "second_expend_time": one_data.second_expend_time,
                    "force_start_time": one_data.force_start_time,
                }
            await cls.conf.rds.set_item(key, json_encode(data_map, cls.logerr), ex_time=cls.expired_sec)
            return data_map

        key = f"{cls.tb_name}:{season_id}"
        info = await cls.conf.rds.get_item(key)
        if info:
            return json_parse(info, cls.logerr)
        info = await cls.conf.rds.locked(key, from_db)
        return info


class UserRankingRC(RCModel):
    """ 用户排名模型 """
    db_model = UserRanking
    tb_name = db_model.sheet_name()

    expired_mode = 1
    expired_sec = 172800  # 2 * 86400

    KEY_WORLD_RANKING = "ranking_list_world"
    KEY_REGION_RANKING = "ranking_list_region"

    @classmethod
    async def query_all(cls):
        """ 查询全部 """
        return await cls.db_model.get_by_dict(
            field=[
                "user_id",
                "ranking_id",
                "cur_score",
                "top_score",
                "season_achieved",
                "level_achieved",
                "region",
                "game_count"
            ]
        )

    @classmethod
    async def __get_ranking_id_by_default_score(cls, score):
        """ 根据默认分获取当前ranking id """
        season = await ConfSeasonRC.get_current_season()
        season_id = season.get("season_id")
        key = f'default_rd:{season_id}'
        cache_rid = await cls.conf.rds.get_item(key)
        if cache_rid:
            await cls.conf.rds.set_item(key, cache_rid, ex_time=cls.expired_sec)  # 热点数据
            return int(cache_rid)

        # season_status = season.get("status")
        # if season_status == SeasonStatus.DAN_RESET:
        #     # 如果是赛季重置期，下发下个赛季配置
        #     season_id = await ConfSeasonRC.get_next_id(season_id)

        ranking_conf = await ConfRankingRC.get_ranking_items(season_id)

        cur_ranking_conf = ConfRankingRC.get_ranking_data_by_score(ranking_conf, score)
        if cur_ranking_conf:
            rid = cur_ranking_conf.get('id')
            await cls.conf.rds.set_item(key, rid, ex_time=cls.expired_sec)
            return rid
        return 1

    @classmethod
    async def cache_by_unique(cls, uid, **kwargs):
        """查询玩家排位，没有的活跃玩家给默认值"""

        async def from_db():
            db_info = await cls.db_model.get_by_dict({"user_id": uid}, limit=1)
            # db_info = await cls.db_model.filter(**kwargs).first().select_related("ranking")
            if not db_info:
                db_info = {
                    "user_id": uid,
                    "level_achieved": None,
                    "season_achieved": None,
                    "game_count": 0,
                    # 是否默认值判断（仅此处有）
                    "default_cache": 1
                }
            return db_info

        key = f"{cls.tb_name}:{uid}"
        info = await cls.conf.rds.get_item(key)
        if info:
            return json_parse(info, cls.logerr)

        u_info = kwargs.pop("u_info", None)
        info = await cls.conf.rds.locked(key, from_db)
        if info.get("default_cache"):
            conf_ranking = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_RANKING)
            score = conf_ranking.get("initial_score") or 100
            info["cur_score"] = score

            u_info = u_info or await BaseUserRC.cache_by_uid(uid) or {}
            region = u_info.get("region")
            info["region"] = REGION_ENUM_MAP.get(region) or 0

            default_rid = await cls.__get_ranking_id_by_default_score(score)
            info["ranking_id"] = default_rid

        await cls.conf.rds.set_item(key, json_encode(info), ex_time=cls.expired_sec)
        return info

    @classmethod
    async def get_ranking_list(cls, season_id, limit=100):
        """ 获取排行榜 """
        info = await cls.conf.rds.get_item(cls.KEY_WORLD_RANKING)
        if info:
            return json_parse(info, cls.logerr)
        # 当世界排行榜缓存中没有，先查看地区排行榜缓存，没有再刷新地区排行榜
        all_data_list = await cls.get_ranking_list_all_region()
        if all_data_list:
            return await cls.__refresh_ranking_list(all_data_list, limit)
        _, world_rank_list = await cls.conf.rds.locked(
            cls.KEY_WORLD_RANKING, cls.refresh_ranking_list_group_by_region, (season_id, limit))
        return world_rank_list

    # @classmethod
    # async def refresh_ranking_list_old(cls, season_id, limit=100):
    #     """
    #     刷新排行榜
    #     注意：该方式舍弃，已换做下面的先刷新地区排行榜
    #         再从地区排行榜中选取最高的前100选出世界排行榜
    #     """
    #     data_list = await cls.db_model.filter().order_by("-cur_score").limit(limit).prefetch_related("ranking", "user")
    #     data_list = [
    #         {
    #             "uid": data.user.uid,  # todo: 玩家基础信息：头像、昵称等
    #             "u_name": data.user.name,
    #             "u_avatar": data.user.avatar,
    #             "cur_score": data.cur_score,
    #             "top_score": data.top_score,
    #             "r_name": data.ranking.ranking_name,
    #         }
    #         for data in data_list
    #     ]
    #     """
    #     # 还可以用此种方式
    #     data = await UserRanking.filter().order_by("-cur_score").limit(100).values(
    #     'user_id',  # UserRanking表的user_id字段
    #     'cur_score',  # UserRanking表的score字段
    #     'top_score',  # UserRanking表的top_score字段
    #     'user__name',  # User表的name字段
    #     'user__avatar',  # User表的avatar字段
    #     'ranking__ranking_name'  # ConfRanking表的ranking_name字段
    #     )
    #     """
    #
    #     diff_num = limit - len(data_list)
    #     if diff_num > 0:  # 机器人补齐
    #         if diff_num == limit:
    #             conf_json_rank = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_RANKING)
    #             last_one_score = conf_json_rank.get("initial_score") or 100
    #         else:
    #             # ▶机器人修为值=RAND(MIN(100,最低排名玩家修为×0.7),最低排名玩家修为）
    #             last_one = data_list[-1]
    #             last_one_score = last_one.get("cur_score")
    #
    #         ranking_conf = await ConfRankingRC.get_ranking_items(season_id)
    #         diff_data = await BaseRobotRC.db_model.filter(r_score__lte=last_one_score).limit(diff_num)
    #         for db_data in diff_data:
    #             if db_data.r_score == data_list[-1].get("cur_score"):
    #                 ur_name = data_list[-1].get("r_name")
    #             else:
    #                 idx = UtilsTool.binary_search(
    #                     ranking_conf, db_data.r_score, inner=True, min_field="min_score", max_field="max_score",
    #                     max_field_inf=True)
    #                 ur_name = ranking_conf[idx].get("ranking_name") if isinstance(idx, int) else ''
    #
    #             data_list.append({
    #                 "uid": db_data.uid,  # todo: 玩家基础信息：头像、昵称等
    #                 "u_name": db_data.name,
    #                 "u_avatar": db_data.avatar,
    #                 "cur_score": db_data.r_score,
    #                 "top_score": db_data.r_top_score,
    #                 "r_name": ur_name,
    #             })
    #
    #     await cls.conf.rds.set_item(cls.KEY_WORLD_RANKING, orjson.dumps(data_list))
    #     cls.conf.info_log("刷新世界排行榜：", data_list)
    #     return data_list

    @classmethod
    async def __refresh_ranking_list(cls, all_data_list: list, limit=100):
        """ 刷新世界排行榜 """
        all_data_list.sort(key=lambda d: d['cur_score'], reverse=True)
        rank_list = all_data_list[:limit]
        await cls.conf.rds.set_item(cls.KEY_WORLD_RANKING, orjson.dumps(rank_list))
        cls.conf.info_log("刷新世界排行榜成功！")
        return rank_list

    @classmethod
    async def get_ranking_list_all_region(cls):
        info = await cls.conf.rds.get_hash_val(cls.KEY_REGION_RANKING)
        all_data_list = []
        if info:
            for data in info:
                all_data_list.extend(json_parse(data, cls.logerr))
        return all_data_list

    @classmethod
    async def get_ranking_list_by_region(cls, season_id, region: RegionEnum, limit=100):
        info = await cls.conf.rds.get_hash(cls.KEY_REGION_RANKING, region)
        if info:
            return json_parse(info, cls.logerr)
        info_dic, _ = await cls.conf.rds.locked(
            cls.KEY_REGION_RANKING, cls.refresh_ranking_list_group_by_region, (season_id, limit))
        return info_dic.get(region) or []

    @classmethod
    async def get_ranking_list_group_by_region_by_player(cls, season_id, limit=100):
        """ 按地区获取真实玩家排行榜 """
        sql = """
            WITH ranked_users AS (
                SELECT
                    ur.user_id AS uid,
                    ur.region,
                    ur.cur_score,
                    ur.top_score,
                    ur.ranking_id,
                    u.name AS u_name,
                    u.sex,
                    u.avatar AS u_avatar,
                    cr.ranking_name AS r_name,
                    uc.cosmetic_item_id AS avatar_frame,
                    ROW_NUMBER() OVER (PARTITION BY ur.region ORDER BY ur.cur_score DESC) AS row_num
                FROM
                    user_ranking ur
                JOIN conf_ranking cr ON ur.ranking_id = cr.id
                JOIN user u ON ur.user_id = u.uid
                LEFT JOIN user_cosmetic uc ON ur.user_id = uc.uid AND uc.cosmetic_type = 1 AND uc.got_type = 1
                WHERE cr.season_id={}
            )
            SELECT
                uid,
                region,
                cur_score,
                top_score,
                ranking_id,
                u_name,
                sex,
                u_avatar,
                r_name,
                COALESCE(avatar_frame, 0) AS avatar_frame
            FROM
                ranked_users
            WHERE
                row_num <= {};
        """.format(season_id, limit)

        conn = cls.db_model.get_meta_db()
        data_list = await conn.execute_query_dict(sql)
        data_map = {}
        for data in data_list:
            data_map.setdefault(data.get("region"), []).append(data)
        return data_list, data_map

    @classmethod
    async def refresh_ranking_list_group_by_region(cls, season_id, limit=100):
        """
        1、先刷新地区排行榜
        2、再从地区排行榜中选前100名的排行作为世界排行榜
        查询排行榜根据地区分组
        使用窗口函数
        PARTITION BY region：将数据按 region 分区。
        窗口函数在同一个查询中对数据进行分组和排序，不需要多次扫描表
        """
        _, data_map = await cls.get_ranking_list_group_by_region_by_player(season_id, limit)
        # 按地区分区再保存到缓存
        data_map.pop(RegionEnum.DEFAULT, None)
        query_params = []
        for r_enum in REGION_ENUM_MAP.values():
            r_data_list = data_map.get(r_enum.val) or []
            diff_num = limit - len(r_data_list)  # 补充的机器人数量
            query_params.append((r_enum.phrase, diff_num))  # 地区 补充数量 低于多少分

        if query_params:
            last_score = 999999  # data_list and data_list[0].get("cur_score") or 100  # 最低分
            diff_region = ', '.join([f"'{params[0]}'" for params in query_params])
            diff_region_num = '\n'.join([f"WHEN region = '{params[0]}' THEN {params[1]}" for params in query_params])
            sql = """
                WITH ranked_robots AS (
                SELECT
                    uid,
                    name AS u_name,
                    sex,
                    avatar AS u_avatar,
                    r_score AS cur_score,
                    r_top_score AS top_score,
                    region,
                    extra_info,
                    -- ROW_NUMBER() OVER (PARTITION BY region ORDER BY r_score DESC) as row_num
                    ROW_NUMBER() OVER (PARTITION BY region ORDER BY RAND()) as row_num
                FROM
                    robot
                WHERE
                    region IN ({0})
                    AND r_score <= {1}
                    AND uid >= {2}
                )
                SELECT
                    uid,
                    u_name,
                    sex,
                    u_avatar,
                    cur_score,
                    top_score,
                    region,
                    extra_info
                FROM
                    ranked_robots
                WHERE
                    row_num <= CASE 
                        {3}
                    END;
            """.format(diff_region, last_score, ROBOT_RANK[0], diff_region_num)

            conn = cls.db_model.get_meta_db()
            diff_data_list = await conn.execute_query_dict(sql)
            ranking_conf = await ConfRankingRC.get_ranking_items(season_id, is_lock=False)
            for data in diff_data_list:
                region = REGION_ENUM_MAP.get(data.get("region", '')) or 0
                data["region"] = region
                data["u_avatar"] = ROBOT_AVATAR + data["u_avatar"]

                extra_info = data.get("extra_info")
                if extra_info:
                    extra_info = json_parse(extra_info)
                    data["avatar_frame"] = extra_info.get("avatar_frame", 0)
                ur_name = ''
                cur_ranking_conf = ConfRankingRC.get_ranking_data_by_score(ranking_conf, data.get('cur_score'))
                if cur_ranking_conf:
                    ur_name = cur_ranking_conf.get("ranking_name")
                data["r_name"] = ur_name
                data_map.setdefault(region, []).append(data)

        for values in data_map.values():
            values.sort(key=lambda x: x["cur_score"], reverse=True)
        data_map_str = {str(key): json_encode(values, cls.conf.error_log) for key, values in data_map.items()}

        await cls.conf.rds.set_hash_bulk(cls.KEY_REGION_RANKING, data_map_str)
        cls.conf.info_log("刷新地区排行榜成功！")

        all_data_list = []
        for region, data_list in data_map.items():
            all_data_list.extend(data_list)
        world_rank_list = await cls.__refresh_ranking_list(all_data_list, limit)
        return data_map, world_rank_list

    @classmethod
    async def update_user_ranking(cls, uid, update_info: dict, old_info: dict, is_unrated=False):
        """更新排位一般记录"""

        async def update_cache(db_info):
            await cls.conf.rds.set_item(f"{cls.tb_name}:{uid}", json_encode(db_info), ex_time=cls.expired_sec)

        if is_unrated:
            old_info.update(update_info)
            await update_cache(old_info)
            return True

        return await cls.db_model.update_by_pk(old_info.get("id"), update_info, old_info, fun_success=update_cache)

    @classmethod
    async def update_user_ranking_score(cls, uid, score, game_count=0):
        """更新排位分"""

        async def update_cache(db_info):
            await cls.conf.rds.set_item(f"{cls.tb_name}:{uid}", json_encode(db_info), ex_time=cls.expired_sec)

        # 获取当前赛季
        season_conf = await ConfSeasonRC.get_current_season()
        if not season_conf:
            cls.conf.error_log(uid, "当前赛季配置不存在")
            return 0

        season_id = season_conf.get("season_id")
        # 排位等级配置
        ranking_conf = await ConfRankingRC.get_ranking_items(season_id)
        if not ranking_conf:
            cls.conf.error_log(uid, "排位等级配置不存在")
            return 0

        # 用户排位数据
        ur_data = await cls.cache_by_unique(uid) or {}

        ranking_id = ur_data.get('ranking_id') or 1

        # 已加经验等级 (由于新增了一个分数重置期，这里不需要判断是否为本赛季了)
        # user_season_id = rank_data.get('season_id') or 0  # 玩家最新参赛的赛季
        # 段位保护检测
        cur_ranking_conf = {}
        idx = UtilsTool.binary_search(ranking_conf, ranking_id, "id")
        if isinstance(idx, int):
            cur_ranking_conf = ranking_conf[idx]

        cur_score = ur_data.get('cur_score', 0)
        cls.conf.info_log(uid, "玩家更新排位分之前", cur_score, ranking_id, score)
        if score < 0:
            if cur_ranking_conf.get("lv_defend") == LvDefendType.DEFEND_WHOLE:  # 完全保护
                cls.conf.info_log(uid, "玩家修为保护：", cur_ranking_conf.get("id"), cur_score, score)
                score = 0
            elif cur_ranking_conf.get("lv_defend") == LvDefendType.DEFEND_FLOOR:  # 保护修为下线
                if cur_score + score < cur_ranking_conf.get("min_score"):
                    cur_min_score = cur_ranking_conf.get("min_score")
                    score = cur_min_score - cur_score
                    cls.conf.info_log(uid, "保护修为下线：", cur_ranking_conf.get("id"), cur_score, score)
            else:
                sub_after_conf = ConfRankingRC.get_ranking_data_by_score(ranking_conf, cur_score + score)
                if sub_after_conf:
                    if sub_after_conf.get("lv_defend") == LvDefendType.DEFEND_WHOLE:
                        level = sub_after_conf.get("level")
                        while level < len(ranking_conf):
                            sub_after_conf = ranking_conf[level]
                            if sub_after_conf.get("lv_defend") == LvDefendType.DEFEND_FLOOR:
                                break
                            level += 1
                    if sub_after_conf.get("lv_defend") == LvDefendType.DEFEND_FLOOR:
                        if cur_score + score < sub_after_conf.get("min_score"):
                            min_score = sub_after_conf.get("min_score")
                            score = min_score - cur_score
                            cls.conf.info_log(uid, "最多减到保护修为下限：", sub_after_conf.get("id"), cur_score, score)

        if score == 0:
            cls.conf.info_log(uid, "修为更新0")

        cur_score += score
        cur_major_level = cur_ranking_conf.get('major_level') or 0
        cur_minor_level = cur_ranking_conf.get('minor_level') or 0

        new_ranking_conf = ConfRankingRC.get_ranking_data_by_score(ranking_conf, cur_score)

        new_major_level = new_ranking_conf.get('major_level') or 0
        new_minor_level = new_ranking_conf.get('minor_level') or 0
        ranking_id = new_ranking_conf.get("id")
        top_score = ur_data.get("top_score", 0)
        data = {
            "cur_score": cur_score,
            "top_score": cur_score if cur_score > top_score else top_score,
            "ranking_id": ranking_id,
            "game_count": ur_data.get("game_count", 0) + game_count
        }
        if not ur_data or ur_data.get("default_cache"):
            data["user_id"] = uid
            data["region"] = ur_data.get("region") or 0
            sta = await cls.db_model.add_one(data)
            if sta:
                data["id"] = sta.id
                await update_cache(data)
        else:
            sta = await cls.db_model.update_by_pk(ur_data.get("id"), data, ur_data, fun_success=update_cache)

        if not sta:
            cls.conf.error_log(uid, "玩家排位分更新失败", data)
            return 0

        cls.conf.info_log(uid, "玩家更新排位分之后", cur_score, score, ranking_id)
        if cur_major_level < new_major_level:
            cls.conf.info_log(uid, "玩家大段升级：", cur_major_level, "==>>", new_major_level)
        if cur_minor_level < new_minor_level:
            cls.conf.info_log(uid, "玩家小段升级：", cur_minor_level, "==>>", new_minor_level)

        return score

    @classmethod
    async def ranking_reset_before_next_season(cls, next_season_id):
        sql = """
                UPDATE user_ranking ur
                SET 
                    cur_score = CEIL(CASE
                        WHEN ur.cur_score > 1600 THEN
                            1600 - (1600 - 850) * 0.75 - (850 - 350) * 0.5
                        WHEN ur.cur_score BETWEEN 851 AND 1600 THEN
                            ur.cur_score - (ur.cur_score - 850) * 0.75 - (850 - 350) * 0.5
                        WHEN ur.cur_score BETWEEN 351 AND 850 THEN
                            ur.cur_score - (ur.cur_score - 350) * 0.5
                        ELSE
                            ur.cur_score
                    END),
                    top_score = cur_score,
                    ranking_id = COALESCE(
                        (SELECT r.id
                             FROM conf_ranking r
                             WHERE season_id = {} 
                             AND (cur_score BETWEEN r.min_score AND r.max_score 
                             OR (r.min_score <= cur_score AND r.max_score = -1))
                             LIMIT 1),
                            ur.ranking_id  -- 如果没有找到匹配的排名，保持原来的排名ID
                        ),
                    season_achieved=false,
                    level_achieved = '[]',
                    game_count=0
            """.format(next_season_id)
        conn = cls.db_model.get_meta_db()
        sta = await conn.execute_query_dict(sql)
        return sta

    @staticmethod
    def ranking_reset_before_next_season_no_used(score, reset_rule: dict = None) -> int:
        """
        暂未使用
        下个赛季开始之前段位重置规则
        ◆1601以上，全部扣除
        ◆851~1600部分，扣除75%
        ◆351~850部分，扣除50%
        ◆350以下，不扣除
        """
        reset_rule = reset_rule or {}
        grade_a = reset_rule.get("grade_a") or 1601
        grade_b = reset_rule.get("grade_b") or 851
        grade_c = reset_rule.get("grade_c") or 351
        if score < grade_c:
            return score
        if score > grade_a:
            score = grade_b - 1

        if score >= grade_b:
            score = score - (score - grade_b) * 0.75 - (grade_b - 1 - grade_c) * 0.5
        elif score >= grade_c:
            score -= (score - grade_c) * 0.5

        return math.ceil(score)

    @classmethod
    async def get_ranking_unclaimed(cls, uid):
        """境界奖励未领取"""
        ur_data = await cls.cache_by_unique(uid) or {}
        if not ur_data or ur_data.get("default_cache"):
            return False

        season_conf = await ConfSeasonRC.get_current_season()
        if not season_conf or season_conf.get("status") == SeasonStatus.NEXT_SEASON:
            return False

        ranking_conf = await ConfRankingRC.get_ranking_items(season_conf.get("season_id"))
        if not ranking_conf:
            return False

        cur_ranking = ConfRankingRC.get_ranking_data_by_score(ranking_conf, ur_data.get("cur_score"))
        if not cur_ranking:
            return False

        if not cur_ranking.get("level_awards"):
            return False
        # 等级奖
        old_level_achieved = ur_data.get("level_achieved") or ""
        level_achieved = [] if not old_level_achieved else json_parse(old_level_achieved)

        all_level = [i.get('level') if i.get('level_awards') else None for i in ranking_conf]
        level_awards_sta = ConfJsonRC.stat_of_completion(cur_ranking.get("level"), level_achieved, all_level)
        if CompleteSta.COMPLETED.val in level_awards_sta:
            return True
        return False



