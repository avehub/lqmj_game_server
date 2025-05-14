"""
获取所有项
"""
from sanic import Request
from lucky_admin.base_api import AdminAuthApi
from lucky_game.model_rc.base_activity import ConfActivityRC
from lucky_game.model_rc.base_cosmetic import ItemsCosmeticRC
from lucky_game.model_rc.base_goods import ItemsBaseRC
from lucky_game.model_rc.base_prop import ItemsPropRC
from lucky_game.model_rc.base_skin import ItemsSkinRC
from lucky_game.model_rc.base_store import ConfStoreRC


class GetAllItemsHandler(AdminAuthApi):
    """ 获取所有子物品 """

    async def get(self, _a: Request, **_b):
        items_base = await ItemsBaseRC.cache_all_conf_item()
        items_cosmetic = await ItemsCosmeticRC.get_cosmetic_items()
        items_prop = await ItemsPropRC.get_game_prop_items()
        items_skin = await ItemsSkinRC.get_skin_items(is_sort=False)

        data = {
            "items_base": items_base,
            "items_cosmetic": items_cosmetic,
            "items_prop": items_prop,
            "items_skin": items_skin
        }

        self.answer(data=data)


class GetAllStoresHandler(AdminAuthApi):
    """ 获取所有商品/充值 """

    async def get(self, _a: Request, **_b):
        conf_activity = await ConfActivityRC.get_activity_items()
        conf_store = await ConfStoreRC.cache_all_conf_item()

        data = {
            "conf_activity": conf_activity,
            "conf_store": conf_store,
        }

        self.answer(data=data)
