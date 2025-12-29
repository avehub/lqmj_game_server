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
