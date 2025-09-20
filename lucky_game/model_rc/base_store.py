"""
游戏各种商店
"""
from nsanic.libs import tool_dt
from common.utils.kit_dt import KitDt
from common.public.enum_const import Switch
from lucky_game.handler.douyin import DouYin
from lucky_game.model_db.main import ConfStore, ConfMonopolyStore
from lucky_game.model_rc.active_behaviors import UserBehaviorsRC
from lucky_game.model_rc.base_rc import BaseRC
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.const import StoreType, PayType, AdSlotItem
from lucky_game.model_rc.goods_manager import GoodsManagerRC


class ConfStoreRC(BaseRC):
    """游戏商店"""
    db_model = ConfStore
    tb_name = db_model.sheet_name()

    expired_mode = 0
    expired_sec = 2 * 86400

    KEY_STORE_ID = 'store_id'
    KEY_STORE_TYPE = 'store_type'

    COMMON_STORE_TYPES = (StoreType.DIAMOND, StoreType.GOLD, StoreType.PROP)

    @classmethod
    async def get_store_items(cls, uid, store_type=StoreType.DEFAULT, platform='', os=''):
        items = await cls.cache_all_conf_item()
        if items:
            for item in items:
                DouYin.adjust_payment_for_douyin(item, platform, os)
            items_list = await cls.organize_store_data(uid, items, store_type, filter_types=cls.COMMON_STORE_TYPES)
            return items_list
        return

    @classmethod
    async def get_store_item_by_id(cls, store_id, platform='', os=''):
        """按ID获取商店项目"""
        item = await cls.cache_conf_by_pk(store_id)
        if item:
            DouYin.adjust_payment_for_douyin(item, platform, os)
            return item
        return

    @classmethod
    def __check_item_validity(cls, item):
        """检查商品有效性"""
        cur_time = tool_dt.cur_time()
        start_sale_time = item.get("start_sale_time", 0)
        end_sale_time = item.get("end_sale_time", 0)

        if start_sale_time > 0 and cur_time < start_sale_time:
            return False
        if end_sale_time > 0 and cur_time > end_sale_time:
            return False
        return True

    @classmethod
    async def __check_item_extra_info(cls, uid, item):
        store_id = item.get("store_id")
        pay_type = item.get("pay_type")
        buy_limit = item.get("buy_limit")
        # 短期限购商品查询
        if buy_limit:
            # 看广告支付次数
            if pay_type == PayType.BY_WATCH_AD:
                watch_record = await UserBehaviorsRC.cache_user_ad_times(uid, KitDt.timestamp_today())
                if watch_record:
                    ao_enum = AdSlotItem.find_member_by_val(store_id)
                    item["buy_times"] = watch_record.get(ao_enum.desc) or 0
            else:
                buy_record = await BaseUserRC.get_count_buy_limit(uid, store_id)
                item["buy_times"] = buy_record.get("buy_times") if buy_record else 0

        # 充值商品查询首单奖
        if pay_type in (PayType.BY_RMB.val, PayType.BY_DY_DIAMOND.val):
            is_first = await UserBehaviorsRC.query_is_first_buy(uid, store_id)
            item["first_gifts_sta"] = Switch.OPEN if is_first else Switch.CLOSE

    @classmethod
    async def organize_store_data(cls, uid, items_list, store_type=StoreType.DEFAULT, filter_types=None):
        """整理数据 / 检查限购"""
        if store_type:
            s_enum = StoreType.find_member_by_val(store_type)
            if not s_enum or s_enum == StoreType.DEFAULT:
                return []
            one_data = {
                "store_names": s_enum.phrase,
                "store_types": store_type,
                "items_lists": items_list
            }
            return [one_data]
        else:
            # 先按store_type分类
            classified_data = {}
            for item in items_list or []:
                s_type = item.get(cls.KEY_STORE_TYPE, 0)
                s_enum = StoreType.find_member_by_val(s_type)
                if not s_enum or s_enum not in filter_types:
                    continue
                if not cls.__check_item_validity(item):
                    continue
                await cls.__check_item_extra_info(uid, item)
                classified_data.setdefault(s_type, []).append(item)

            data_list = []
            for s_type, new_items_list in classified_data.items():
                s_enum = StoreType.find_member_by_val(s_type)
                one_data = {
                    "store_names": s_enum.phrase,
                    "store_types": s_type,
                    "items_lists": new_items_list
                }
                data_list.append(one_data)

            return data_list

    @classmethod
    async def get_store_free_chance(cls, uid, store_id):
        """获取商店白嫖机会"""
        buy_record = await BaseUserRC.get_count_buy_limit(uid, store_id)
        if not buy_record:
            return True

        buy_times = buy_record.get("buy_times") or 0
        buy_limit = buy_record.get("buy_limit") or {}
        if buy_limit:
            times = buy_limit.get("times", 0)
            if buy_times < times:
                return True
            return False
        return True


class ConfMonopolyStoreRC(BaseRC):
    """大富翁商店"""
    db_model = ConfMonopolyStore
    tb_name = db_model.sheet_name()

    expired_mode = 0
    expired_sec = 2 * 86400

    KEY_STORE_ID = 'store_id'
    KEY_STORE_TYPE = 'store_type'

    MONOPOLY_STORE_TYPES = (StoreType.SKIN, StoreType.PROP, StoreType.GOLD, StoreType.S_MAGIC)

    @classmethod
    async def get_monopoly_store_items(cls, uid, store_type=StoreType.DEFAULT):
        all_items = await cls.cache_all_conf_item()
        if all_items:
            await GoodsManagerRC.pack_goods_conf(all_items)
            items_list = await ConfStoreRC.organize_store_data(uid, all_items, store_type,
                                                               filter_types=cls.MONOPOLY_STORE_TYPES)
            return items_list

    @classmethod
    async def get_monopoly_store_item_by_id(cls, store_id):
        """按ID获取大富翁商店项目"""
        return await cls.cache_conf_by_pk(store_id)
