"""
游戏各种商店
"""
import datetime

from nsanic.libs import tool_dt
from nsanic.libs.tool import json_parse

from common.public.common_class import CommonApi
from common.utils.kit_dt import KitDt
from common.public.enum_const import Switch
from lucky_game.handler.douyin import DouYin
from lucky_game.model_db.main import Stores, Goods
from lucky_game.model_rc.active_behaviors import UserBehaviorsRC
from lucky_game.model_rc.base_rc import BaseCommonRC
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.const import StoreType, PayType, AdSlotItem
from tortoise.exceptions import OperationalError
from lucky_game.handler.random_utils import generate_random_string


class StoreRC(BaseCommonRC):
    """游戏商店"""
    db_model = Stores
    tb_name = db_model.sheet_name()

    KEY_STORE_ID = 'store_id'
    KEY_STORE_TYPE = 'store_type'

    COMMON_STORE_TYPES = (StoreType.DIAMOND, StoreType.GOLD, StoreType.PROP)

    @classmethod
    async def get_store_items(cls, uid, store_type=StoreType.DEFAULT, platform='', os=''):
        items = await cls.cache_all_conf_item()
        if items:
            items_list = await cls.organize_store_data(uid, items, store_type, filter_types=cls.COMMON_STORE_TYPES)
            return items_list
        return

    @classmethod
    async def get_store_item_by_id(cls, store_id, platform='', os=''):
        """按ID获取商店项目"""
        item = await cls.cache_conf_by_pk(store_id)
        return item

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

    @classmethod
    async def get_store_filter(cls, platform: any = None, sid: any = None, status: int = None, type_id: any = None,
                        start_time: int = None, end_time: int = None, currency: int = None,
                        order_by: str = None, sku_id: any = None, fields: str = None):
        """获取用户参与活动次数"""
        try:
            query = {}
            if platform is not None:
                if isinstance(platform, list):
                    query["platform__in"] = platform
                else:
                    query["platform__contains"] = platform
            if sid is not None:
                if isinstance(sid, list):
                    query["sid__in"] = sid
                else:
                    query["sid"] = sid
            if type_id is not None:
                if isinstance(type_id, list):
                    query["type__in"] = type_id
                else:
                    query["type"] = type_id
            if sku_id is not None:
                if isinstance(sku_id, list):
                    query["sku_id__in"] = sku_id
                else:
                    query["sku_id"] = sku_id
            if status is not None:
                query["status"] = status
            if currency is not None:
                query["currency"] = currency
            if order_by is None:
                order_by = "-rank"
            if start_time is not None:
                query["start_time__gte"] = start_time
            if end_time is not None:
                query["end_time__lte"] = end_time
            print("query", query)
            data = await cls.db_model.filter(**query).order_by(order_by).values()
        except OperationalError as e:
            return None, f"查询失败:{e}"
        return data, "成功"

class GoodRC(BaseCommonRC):
    """商品(道具)"""
    db_model = Goods
    tb_name = db_model.sheet_name()

    EXPIRED_DEFAULT = 0
    EXPIRED_PERMANENT = -1

    @classmethod
    async def cache_session_set(cls, query, value):
        return await cls.conf.rds.set_item(f"{cls.tb_name}:{query}", value)

    @classmethod
    async def cache_session_get(cls, query):
        data = await cls.conf.rds.get_item(f"{cls.tb_name}:{query}")
        if isinstance(data, bytes):
            data = json_parse(data.decode())
        return data

    @classmethod
    async def cache_session_del(cls, query):
        return await cls.conf.rds.del_item(f"{cls.tb_name}:{query}")

    @classmethod
    async def get_good_filter(cls, good_id: any = None, sid: any = None, status: int = None, type_id: any = None,
                              start_time: int = None, end_time: int = None, kind: int = None, currency: int = None,
                        order_by: str = None, bag_type: int = None, sku: any = None, fields: str = None,
                              page: int = None, page_size: int = None):
        """获取用户参与活动次数"""
        try:
            query = {}
            if good_id is not None:
                if isinstance(good_id, list):
                    query["good_id__in"] = good_id
                else:
                    query["good_id"] = good_id
            if sid is not None:
                if isinstance(sid, list):
                    query["sid__in"] = sid
                else:
                    query["sid"] = sid
            if type_id is not None:
                if isinstance(type_id, list):
                    query["type__in"] = type_id
                else:
                    query["type"] = type_id
            if sku is not None:
                if isinstance(sku, list):
                    query["sku__in"] = sku
                else:
                    query["sku"] = sku
            if status is not None:
                query["status"] = status
            if kind is not None:
                query["kind"] = kind
            if currency is not None:
                query["currency"] = currency
            if order_by is None:
                order_by = "-rank"
            if bag_type is not None:
                query["bag_type"] = bag_type
            if start_time is not None:
                query["up_time__gte"] = start_time
            if end_time is not None:
                query["down_time__lte"] = end_time
            if page and page_size:
                total = await cls.db_model.filter(**query).count()
                data = []
                if total > 0:
                    offset = (page - 1) * page_size
                    data = await cls.db_model.filter(**query).order_by(order_by).offset(
                        offset).limit(page_size).values()
                result = await cls.page_result(page, page_size, total, data)
            else:
                result = data = await cls.db_model.filter(**query).order_by(order_by).values()
            if not data:
                return result, "无数据"
        except OperationalError as e:
            return None, f"查询失败:{e}"
        return result, "成功"

    @classmethod
    async def get_good_info(cls, sku: str) -> dict:
        """获取商品信息"""
        cache_data = await cls.cache_session_get(sku)
        if cache_data:
            return cache_data
        data, msg = await cls.get_good_filter(sku=sku)
        if not data:
            return {}
        await cls.cache_session_set(sku, data[0])
        return data[0] if data else {}

    @classmethod
    async def get_good_by_id(cls, good_id: int) -> dict:
        """根据商品id获取商品信息"""
        cache_data = await cls.cache_session_get(good_id)
        if cache_data:
            return cache_data
        data, msg = await cls.get_good_filter(good_id=good_id)
        if not data:
            return {}
        await cls.cache_session_set(good_id, data[0])
        return data[0] if data else {}


    @classmethod
    async def __make_sku(cls, length: int = 8) -> str:
        """生成商品sku"""
        while True:
            sku = generate_random_string(length, use_uppercase=True, use_lowercase=False, use_digits=False)
            good_info = await cls.get_good_info(sku)
            if not good_info:
                return sku

    @classmethod
    async def create_good(cls, sid: int, type: int, currency: int, name: str, img: str, original: float, price: float,
                      content: str, status: int = 1, desc: str = None, purchase_limit: str = None,
                      total: int = -1, kind: int = 0, up_time: int = None, down_time: int = None, bag_type: int = 0,
                          rank: int = 0) -> tuple:
        good = {
            "sid": sid,
            "kind": kind,
            "type": type,
            "currency": currency,
            "sku": await cls.__make_sku(),
            "total": total,
            "purchase_limit": purchase_limit,
            "name": name,
            "img": img,
            "desc": desc,
            "original": original,
            "price": price,
            "content": content,
            "status": status,
            "up_time": up_time,
            "down_time": down_time,
            "bag_type": bag_type,
            "rank": rank,
        }
        new = await cls.db_model.add_one(good)
        if not new:
            return None, "添加失败"
        return True, new


    @classmethod
    async def update_good(cls, good_id, up_data: dict):
        """更新商品"""
        try:
            query = {"good_id": good_id}
            valid_fields = {"sid", "kind", "type", "currency", "total", "purchase_limit", "name", "img", "desc", "original", "price", "content", "status", "up_time", "down_time", "bag_type", "rank"}
            update_data = {k: v for k, v in up_data.items() if k in valid_fields}
            if update_data:
                await cls.db_model.filter(**query).update(**update_data)
                await cls.cache_session_del(good_id)
        except OperationalError as e:
            return None, f"失败:{e}"
        return True, "成功"

    @classmethod
    async def get_good_sku(cls, good_type: int) -> list:
        """获取指定范围的商品sku列表"""
        result = []
        data, msg = await cls.get_good_filter(type_id=good_type)
        if not data:
            return result
        return [item["sku"] for item in data]

    @classmethod
    async def get_good_end_time(cls, good_type: int) -> int:
        """获取指定类型商品过期时间"""
        end_time = cls.EXPIRED_DEFAULT
        # 赛事 13赛事-代金券 14赛事-晋级资格 15赛事-农产品
        if good_type in [13, 14]:
            start_time, end_time = await CommonApi.get_time_range()
        if good_type == 15:
            end_time = cls.EXPIRED_PERMANENT
        return end_time







