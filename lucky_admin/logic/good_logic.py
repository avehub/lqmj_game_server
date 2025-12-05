from nsanic.libs import tool_jwt, tool_dt
from lucky_game.model_rc.order import OrderRC
from lucky_game.model_rc.extra_user_resource_changes import ExtraUserResourceChangesRC
from lucky_game.model_rc.base_store import GoodRC


class GoodLogic:
    """ 商品逻辑 """
    @classmethod
    async def get_gift_good_ids(cls, goo_type: str = None):
        # 首充礼包
        first_good_ids = [25, 52]
        # 补足礼包
        replenish_good_ids = [26, 30, 31, 32]
        # 复活礼包
        reviver_good_ids = [33, 37, 38, 39]
        # 返还礼包
        return_good_ids = [40, 41, 42, 43]
        if goo_type == "first":
            return first_good_ids
        elif goo_type == "replenish":
            return replenish_good_ids
        elif goo_type == "reviver":
            return reviver_good_ids
        elif goo_type == "return":
            return return_good_ids
        else:
            # 所有礼包
            all_good_ids = first_good_ids + replenish_good_ids + reviver_good_ids + return_good_ids
            return all_good_ids
