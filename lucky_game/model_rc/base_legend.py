"""
英雄角色模型
"""
from .base_rc import BaseRC
from typing import Iterable
from lucky_game.model_db.main import ItemsLegend


class ItemsLegendRC(BaseRC):
    db_model = ItemsLegend
    tb_name = db_model.sheet_name()


    @classmethod
    async def get_goods_item_by_id_list(cls, id_list: Iterable):
        return await cls.cache_conf_item_by_id_list(id_list)