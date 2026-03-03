"""
赛事配置RC类
"""
from tortoise.exceptions import OperationalError
from lucky_game.model_db.main import ConfCompetition
from lucky_game.model_rc.base_rc import BaseCommonRC
from nsanic.libs.tool import json_encode


class ConfCompetitionRC(BaseCommonRC):
    """赛事配置模型RC类"""
    db_model = ConfCompetition
    tb_name = db_model.sheet_name()
    cache_key = "conf_competition"

    @classmethod
    async def cache_conf_data_by_pk(cls, competition_id) -> dict:
        db_conf_data = await cls.cache_by_pk(competition_id) or {}
        return db_conf_data

    @classmethod
    async def update_competition_time(cls, competition_id, start_time=None, end_time=None ,cycle_id=None):
        """
        更新比赛的开始时间和结束时间

        Args:
            competition_id: 比赛ID
            start_time: 开始时间（时间戳）
            end_time: 结束时间（时间戳）
            cycle_id: 周期ID
        Returns:
            tuple: (bool, str) - (操作结果, 消息)
        """
        try:
            # 构建更新数据
            update_data = {}
            if start_time is not None:
                update_data['start_time'] = start_time
            if end_time is not None:
                update_data['end_time'] = end_time
            if cycle_id is not None:
                update_data['cycle_id'] = cycle_id

            # 如果没有需要更新的字段，直接返回
            if not update_data:
                return True, "没有需要更新的字段"

            # 更新数据库
            result = await cls.db_model.update_by_pk(competition_id, update_data)
            if not result:
                return False, "更新数据库失败"

            # 获取最新的数据
            latest_data = await cls.db_model.get_by_pk(competition_id)
            if latest_data:
                # 更新缓存
                await cls.conf.rds.set_hash(cls.tb_name, competition_id, json_encode(latest_data))
                return True, "更新成功"
            else:
                return False, "更新成功，但无法获取最新数据"

        except OperationalError as e:
            return False, f"更新失败：{str(e)}"
        except Exception as e:
            return False, f"更新失败：{str(e)}"
