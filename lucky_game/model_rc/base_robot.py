"""
机器人
"""
from nsanic.libs.tool import json_parse, json_encode
from common.public.conf import ROBOT_BATTLE
from lucky_game.model_db.main import Robot, ConfRobot
from lucky_game.model_rc.base_rc import BaseRC


class BaseRobotRC(BaseRC):
    """机器人列表"""
    db_model = Robot
    tb_name = db_model.sheet_name()

    query_fields = [
        "uid", "name", "sex", "avatar", "address", "region", "r_score", "r_top_score",
        "game_count_5", "game_win_count_5", "extra_info"
    ]

    @classmethod
    async def cache_by_pk(cls, pk_val, *args, **kwargs):
        return await cls.cache_conf_by_pk(pk_val, has_status=False, orders='', field=cls.query_fields)

    @classmethod
    async def cache_all_robot(cls):
        """ 缓存robot """
        return await cls.cache_all_conf_item(has_status=False, orders='', field=cls.query_fields)

    @classmethod
    async def cache_part_robot(cls, id_list: list):
        key = cls.tb_name
        if not await cls.conf.rds.exists(key):
            await cls.cache_all_robot()
        info_list = await cls.conf.rds.conn.hmget(cls.tb_name, *id_list)
        if info_list:
            r_list = []
            for one in info_list:
                data = json_parse(one, cls.logerr)
                r_list.append({"uid": data["uid"]})
            return r_list
        return info_list

    @classmethod
    async def refresh_robot_cache(cls):
        """ 刷新机器人cache """

        async def from_db():
            db_info = await cls.db_model.get_by_dict({}, field=cls.query_fields)
            if db_info:
                cache_db_info_dict = {}
                pk_field = cls.db_model.pk_name()
                for one_info in db_info:
                    _id = one_info.get(pk_field)
                    cache_db_info_dict[str(_id)] = json_encode(one_info)
                await cls.conf.rds.set_hash_bulk(cls.tb_name, cache_db_info_dict)
                return db_info
            return []

        return await cls.conf.rds.locked(cls.tb_name, fun=from_db)

    @classmethod
    async def refresh_ranking_info(
            cls,
            min_r_score,
            max_r_score,
            defend_score=850,
            min_game_count=0,
            max_game_count=0,
            min_game_win_count=0,
            max_game_win_game_count=0,
    ):
        """ 刷新玩家排行分 """
        # 使用一个子查询来生成随机数。
        # 在主查询中使用这些随机数进行更新。
        sql = """
            UPDATE robot
            SET 
                r_score = CASE
                    -- 生成随机数并存储在变量 @random 中 RAND()生成0-1直接小数
                    WHEN (@random := FLOOR(RAND() * ({1} - {0} + 1)) + {0}) IS NOT NULL THEN
                        CASE
                            WHEN r_score < {2} AND @random < r_score THEN r_score
                            WHEN r_score >= {2} AND @random < {2} THEN {2}
                            ELSE @random
                        END
                    END,
                r_top_score = GREATEST(r_top_score, r_score),
                game_count_5 = CASE -- 100到2000
                    WHEN (@r_game_count := FLOOR(RAND() * ({4} - {3} + 1)) + {3}) IS NOT NULL THEN
                        CASE
                            WHEN @r_game_count < game_count_5 THEN game_count_5
                            ELSE @r_game_count
                        END
                    END,
                game_win_count_5 = CASE
                    WHEN (@r_game_win_count := FLOOR(RAND() * ({6} - {5} + 1)) + {5}) IS NOT NULL THEN
                        CASE
                            WHEN @r_game_win_count < game_win_count_5 THEN game_win_count_5
                            ELSE @r_game_win_count
                        END
                    END
            WHERE uid >= {7};
        """.format(
            min_r_score,
            max_r_score,
            defend_score,
            min_game_count,
            max_game_count,
            min_game_win_count,
            max_game_win_game_count,
            ROBOT_BATTLE[0]
        )
        conn = cls.db_model.get_meta_db()
        sta = await conn.execute_query_dict(sql)
        return sta

    @classmethod
    async def refresh_game_count_info(
            cls,
            min_game_count=0,
            max_game_count=0,
            min_game_win_count=0,
            max_game_win_game_count=0,
    ):
        """ 刷新机器人局数 """
        sql = """
            UPDATE robot
                SET 
                    game_count_5 = CASE -- 100到2000
                        WHEN (@r_game_count := FLOOR(RAND() * ({1} - {0} + 1)) + {0}) IS NOT NULL THEN
                            CASE
                                WHEN @r_game_count < game_count_5 THEN game_count_5
                                ELSE @r_game_count
                            END
                        END,
                    game_win_count_5 = CASE
                        WHEN (@r_game_win_count := FLOOR(RAND() * ({3} - {2} + 1)) + {2}) IS NOT NULL THEN
                            CASE
                                WHEN @r_game_win_count < game_win_count_5 THEN game_win_count_5
                                ELSE @r_game_win_count
                            END
                        END
                WHERE uid >= {4};
        """.format(
            min_game_count,
            max_game_count,
            min_game_win_count,
            max_game_win_game_count,
            ROBOT_BATTLE[0]
        )
        conn = cls.db_model.get_meta_db()
        sta = await conn.execute_query_dict(sql)
        return sta

    @classmethod
    async def ranking_reset_before_next_season(cls):
        """ 重置修为 """
        sql = """
            UPDATE robot r
                SET 
                    r_score = CEIL(CASE
                        WHEN r.r_score > 1600 THEN
                            1600 - (1600 - 850) * 0.75 - (850 - 350) * 0.5
                        WHEN r.r_score BETWEEN 851 AND 1600 THEN
                            r.r_score - (r.r_score - 850) * 0.75 - (850 - 350) * 0.5
                        WHEN r.r_score BETWEEN 351 AND 850 THEN
                            r.r_score - (r.r_score - 350) * 0.5
                        ELSE
                            r.r_score
                    END),
                    r_top_score = r_score
        """.format(cls.tb_name)
        conn = cls.db_model.get_meta_db()
        sta = await conn.execute_query_dict(sql)
        return sta


class ConfRobotRC(BaseRC):
    """机器人简单配置"""
    db_model = ConfRobot
    tb_name = db_model.sheet_name()

    @classmethod
    async def get_robot_conf_by_id(cls, leisure_id):
        return await cls.cache_conf_by_pk(leisure_id)
