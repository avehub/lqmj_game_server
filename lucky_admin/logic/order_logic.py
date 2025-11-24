from nsanic.libs import tool_jwt, tool_dt
from lucky_game.model_rc.order import OrderRC
from lucky_game.model_rc.extra_user_resource_changes import ExtraUserResourceChangesRC
from lucky_game.model_rc.base_store import GoodRC


class OrderLogic:
    """ 订单逻辑 """
    @classmethod
    async def order_sku_good(cls, order: list, type: str = None, range_tmp: list = None):

        if not order:
            return order
        sku_list = [item['sku'] for item in order]
        # 过滤掉重复的sku
        sku_list = list(set(sku_list))
        sku_data, msg = await GoodRC.get_good_filter(sku=sku_list)
        if sku_data:
            sku_dict = {item['sku']: item for item in sku_data}
            if type == "order_statistics":
                return await cls.__order_statistics(order, sku_dict, range_tmp)
            else:
                return await cls.__order_default(order, sku_dict)
        return order

    @classmethod
    async def __order_default(cls, data: list, sku_dict: dict) -> list:
        """ 订单统计 """
        for item in data:
            item['name'] = ""
            if item['sku'] in sku_dict:
                item['name'] = sku_dict[item['sku']]['name']
        return data


    @classmethod
    async def __order_statistics(cls, data: list, sku_dict: dict, range_tmp: list) -> dict:
        """ 订单统计 """
        tmp = {}
        for item in data:
            day = tool_dt.dt_str(item['created'], '%Y-%m-%d')
            if day in range_tmp:
                tmp[day]['amount'] += item['amount']
                tmp[day]['count'] += 1
                # 类型：1首充 2金币 3钻石 4房卡 5黄钻 6VIP 7周卡 8月卡 9终身卡 10金币补足 11复活礼包 12返还礼包
                if item['sku'] in sku_dict:
                    if sku_dict[item['sku']]['type'] == 1:
                        tmp[day]['first_amount'] += item['amount']
                        tmp[day]['first_count'] += 1
                    elif sku_dict[item['sku']]['type'] == 3:
                        tmp[day]['diamond_amount'] += item['amount']
                        tmp[day]['diamond_count'] += 1
                    elif sku_dict[item['sku']]['type'] == 4:
                        tmp[day]['room_card_amount'] += item['amount']
                        tmp[day]['room_card_count'] += 1
                    elif sku_dict[item['sku']]['type'] == 5:
                        tmp[day]['yellow_diamond_amount'] += item['amount']
                        tmp[day]['yellow_diamond_count'] += 1
                    elif sku_dict[item['sku']]['type'] == 10:
                        tmp[day]['replenish_gift_amount'] += item['amount']
                        tmp[day]['replenish_gift_count'] += 1
                    elif sku_dict[item['sku']]['type'] == 11:
                        tmp[day]['revive_gift_amount'] += item['amount']
                        tmp[day]['revive_gift_count'] += 1
                    elif sku_dict[item['sku']]['type'] == 12:
                        tmp[day]['return_gift_amount'] += item['amount']
                        tmp[day]['return_gift_count'] += 1
        return tmp
