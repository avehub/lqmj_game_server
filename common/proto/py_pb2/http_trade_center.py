from nsanic.libs.tool import json_encode

from common.proto.pb2 import http_trade_center_pb2
from common.proto.py_pb2 import http_player_vault


class PbOrder():
    __proto = http_trade_center_pb2.S2COrderInfo()

    @classmethod
    def pb_model(cls, data: dict):
        """ 消息模型(非序列化) """
        order_obj = cls.__proto
        order_obj.order_id = data.get("order_id") or ""
        order_obj.trade_time = data.get("trade_time") or 0
        order_obj.param = data.get("param") or ""
        order_obj.extra_info = data.get("extra_info") or ""
        return order_obj


class PbStore():

    @classmethod
    def pb_model(cls, data: list):
        """ 消息模型(非序列化) """
        __proto = http_trade_center_pb2.S2CStore()

        for i in data or []:
            if i:
                obj = __proto.all_items.add()
                pack_store_data(obj, **i)
        return __proto


def pack_store_data(obj, **kwargs):
    obj.store_names = kwargs.get("store_names") or ''
    obj.store_types = kwargs.get("store_types") or 0
    items_lists = kwargs.get("items_lists") or []
    for i in items_lists:
        if i:
            sd = obj.store_items.add()
            PbStoreItems.pb_model(sd, **i)

def pack_goods_by_key(conf_list, obj=None, conf_key=0):
    if not obj or not conf_list:
        return

    for c in conf_list:
        if c:
            if conf_key == 1:
                conf_obj = obj.first_gifts.add()
            elif conf_key == 2:
                conf_obj = obj.common_gifts.add()
            elif conf_key == 3:
                conf_obj = obj.act_items.add()
            elif conf_key == 4:
                conf_obj = obj.once_items.add()
            elif conf_key == 5:
                conf_obj = obj.level_items.add()
            elif conf_key == 6:
                conf_obj = obj.daily_items.add()
            else:
                conf_obj = obj.conf_items.add()
            http_player_vault.pack_goods_items(conf_obj, **c)


class PbStoreItems():
    __proto = http_trade_center_pb2.StoreItems()

    @classmethod
    def pb_model(cls, store_obj=None, **kwargs):
        """ 消息模型 """
        store_obj = store_obj or cls.__proto
        store_obj.store_id = kwargs.get("store_id") or 0
        store_obj.store_type = kwargs.get("store_type") or 0
        store_obj.store_name = kwargs.get("store_name") or ''
        store_obj.store_count = kwargs.get("store_count") or 0
        store_obj.pay_type = kwargs.get("pay_type") or 0
        store_obj.price = kwargs.get("price") or 0
        store_obj.product_id = kwargs.get("product_id") or ''
        store_obj.orig_price = kwargs.get("orig_price") or 0
        store_obj.time_limit = kwargs.get("time_limit") or 0
        store_obj.rand_type = kwargs.get("rand_type") or 0
        store_obj.number = kwargs.get("number") or 0
        store_obj.desc = kwargs.get("desc") or ''
        pack_goods_by_key(kwargs.get("conf_items", []), store_obj, 0)
        pack_goods_by_key(kwargs.get("first_gifts", []), store_obj, 1)
        pack_goods_by_key(kwargs.get("common_gifts", []), store_obj, 2)
        store_obj.img_url = kwargs.get("img_url") or ''
        store_obj.start_sale_time = kwargs.get("start_sale_time") or 0
        store_obj.end_sale_time = kwargs.get("end_sale_time") or 0
        store_obj.discount = kwargs.get("discount") or 0
        store_obj.buy_times = kwargs.get("buy_times") or 0
        store_obj.first_gifts_sta = kwargs.get("first_gifts_sta") or 0

        buy_limit = kwargs.get("buy_limit") or ''
        store_obj.buy_limit = json_encode(buy_limit) if buy_limit else ''

        sub_label = kwargs.get("sub_label") or ''
        store_obj.sub_label = json_encode(sub_label) if sub_label else ''

        store_obj.discount_price = kwargs.get("discount_price") or 0
        return store_obj


class PbActivityItems():

    @classmethod
    def pb_model(cls, data: dict):
        """ 消息模型(非序列化) """
        __proto = http_trade_center_pb2.S2CActivityItems()

        act_conf = data.get('act_conf') or []
        for i in act_conf or []:
            if i:
                obj = __proto.activity_items.add()
                pack_activity_items(obj, **i)

        __proto.extra_conf = data.get('extra_conf') or ''
        return __proto


def pack_activity_items(obj, **kwargs):
    """ 打包基础活动信息 """
    obj.act_id = kwargs.get("act_id") or 0
    obj.act_type = kwargs.get("act_type") or 0
    obj.act_name = kwargs.get("act_name") or ''
    obj.pay_type = kwargs.get("pay_type") or 0
    obj.price = kwargs.get("price") or 0
    obj.product_id = kwargs.get("product_id") or ''
    obj.orig_price = kwargs.get("orig_price") or 0
    obj.condition_type = kwargs.get("condition_type") or 0
    obj.time_limit = kwargs.get("time_limit") or 0
    obj.join_limit = kwargs.get("join_limit") or 0
    obj.join_limit_day = kwargs.get("join_limit_day") or 0
    obj.start_time = kwargs.get("start_time") or 0
    obj.end_time = kwargs.get("end_time") or 0
    obj.img_url = kwargs.get("img_url") or ''
    obj.activity_sta = kwargs.get("activity_sta") or 0
    obj.deadline = kwargs.get("deadline") or 0
    obj.times = kwargs.get("times") or 0
    obj.times_day = kwargs.get("times_day") or 0
    obj.awards_sta = kwargs.get("awards_sta") or '[]'
    obj.buy_times = kwargs.get("buy_times") or 0
    sale_limit = kwargs.get("sale_limit") or ''
    obj.sale_limit = json_encode(sale_limit) if sale_limit else ''
    obj.discount = kwargs.get("discount") or 0
    obj.discount_price = kwargs.get("discount_price") or 0
    obj.rand_type = kwargs.get("rand_type") or 0

    pack_goods_by_key(kwargs.get("act_awards", []), obj, 3)
    pack_goods_by_key(kwargs.get("conf_items", []), obj, 4)


class PbVip():

    @classmethod
    def pb_model(cls, data: dict):
        """ 消息模型(非序列化) """
        __proto = http_trade_center_pb2.S2CVip()

        vc_list = data.get("vip_conf") or []
        for one_vc in vc_list:
            sd = __proto.vip_conf.add()
            pack_vip_items(sd, **one_vc)

        vi_dict = data.get("vip_data") or {}
        pack_vip_data(__proto, **vi_dict)
        return __proto


def pack_vip_items(obj, **kwargs):
    """ 打包vip配置 """
    obj.level = kwargs.get("level") or 0
    obj.need_exp = kwargs.get("need_exp") or 0
    obj.ranking_addition = kwargs.get("ranking_addition") or 0
    obj.relief_add_times = kwargs.get("relief_add_times") or 0
    obj.relief_addition = kwargs.get("relief_addition") or 0

    pack_goods_by_key(kwargs.get("level_awards", []), obj, 5)
    pack_goods_by_key(kwargs.get("daily_awards", []), obj, 6)


def pack_vip_data(obj, **kwargs):
    """ 打包用户vip信息 """
    obj.vip_data.cur_level = kwargs.get("cur_level") or 0
    obj.vip_data.cur_exp = kwargs.get("cur_exp") or 0
    obj.vip_data.daily_awards_sta = kwargs.get("daily_awards_sta") or '[]'
    obj.vip_data.level_awards_sta = kwargs.get("level_awards_sta") or '[]'
    obj.vip_data.next_need_amount = kwargs.get("next_need_amount") or 0
