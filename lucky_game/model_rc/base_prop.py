"""
游戏道具模型
"""
from .base_rc import BaseRC
from typing import Iterable
from lucky_game.model_db.main import ItemsProp


class ItemsPropRC(BaseRC):
    db_model = ItemsProp
    tb_name = db_model.sheet_name()

    @classmethod
    async def get_goods_item_by_id_list(cls, id_list: Iterable):
        return await cls.cache_conf_item_by_id_list(id_list)

    @classmethod
    async def get_game_prop_items(cls):
        """ 获取全部游戏道具 """
        return await cls.cache_all_conf_item()
