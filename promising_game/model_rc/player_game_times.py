"""
游戏记录统计
"""
from promising_game.model_db.main import StatsPlayerGameTimes
from promising_game.model_rc.base_rc import BaseRC


class PlayerGameTimesRC(BaseRC):
    db_model = StatsPlayerGameTimes
    tb_name = db_model.sheet_name()

    expired_mode = 0
    expired_sec = 2 * 86400

    @staticmethod
    def is_exist_data_in_db(old_info: list, cs_type, play_type):
        for info in old_info:
            if info.get("cs_type") == cs_type and info.get("play_type") == play_type:
                return info
        return {}

    @classmethod
    async def get_game_time_info(cls, uid, cs_type, play_type=1):
        old_info_list = await cls.cache_multiterm_by_cond({"uid": uid}) or []
        old_info = cls.is_exist_data_in_db(old_info_list, cs_type, play_type)
        return old_info_list, old_info

    @classmethod
    async def update_game_times(cls, new_info: dict):
        """更新玩家游戏次数记录等"""

        async def update_cache(info: list):
            key_name = f'{cls.tb_name}'
            unique_val = '_'.join([str(query_params.get(k)) for k in sorted(query_params)])
            key = f'{key_name}:{unique_val}'

            if cls.expired_mode:
                await cls.conf.rds.set_item(key, info, ex_time=cls.expired_sec)
            else:
                await cls.conf.rds.set_hash(key_name, unique_val, info)

        uid = new_info.get("uid")
        cs_type = new_info.get("cs_type")
        play_type = new_info.get("play_type")
        query_params = {"uid": uid}

        old_info_list, old_info = await cls.get_game_time_info(uid, cs_type, play_type)

        if not old_info:
            await cls.db_model.add_one(new_info)
            old_info_list.append(new_info)
            await update_cache(old_info_list)
            return old_info_list

        win_count = new_info.get("win_count", 0)
        new_info["total_count"] = old_info.get("total_count", 0) + 1
        new_info["win_count"] = old_info.get("win_count", 0) + win_count

        curr_win_streak = old_info.get("curr_win_streak", 0)
        curr_win_streak = curr_win_streak + 1 if win_count > 0 else 0  # 非胜局则打断连胜
        new_info["curr_win_streak"] = curr_win_streak

        max_win_streak = old_info.get("max_win_streak", 0)
        max_win_streak = curr_win_streak if curr_win_streak > max_win_streak else max_win_streak  # 当前连胜大于最高连胜
        new_info["max_win_streak"] = max_win_streak

        new_info.pop("id", None)

        sta = await cls.db_model.update_by_cond(old_info, new_info)
        old_info.update(new_info)

        if sta:
            await update_cache(old_info_list)
            return old_info
        return
