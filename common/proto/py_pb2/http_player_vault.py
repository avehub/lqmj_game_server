from nsanic.libs.tool import json_encode
from common.proto.pb2 import http_player_vault_pb2


class PbGoods():

    @classmethod
    def pb_model(cls, data: list):
        """ 消息模型(非序列化) """
        __proto = http_player_vault_pb2.S2CGoodsItems()

        for i in data or []:
            if i:
                obj = __proto.goods_items.add()
                pack_goods_items(obj, **i)
        return __proto


class PbGoodsItems():
    __proto = http_player_vault_pb2.GoodsItems()

    @classmethod
    def pb_model(cls, goods_obj=None, **kwargs):
        goods_obj = goods_obj or cls.__proto
        pack_goods_items(goods_obj, **kwargs)
        return goods_obj


def pack_goods_items(obj, **kwargs):
    """ 打包基础物品信息 """
    obj.goods_id = kwargs.get("goods_id") or 0
    obj.goods_name = kwargs.get("goods_name") or ''
    obj.goods_type = kwargs.get("goods_type") or 0
    obj.add_type = kwargs.get("add_type") or 0
    obj.goods_count = kwargs.get("goods_count") or 0
    obj.time_limit = kwargs.get("time_limit") or 0
    obj.usage_limit = kwargs.get("usage_limit") or 0
    obj.img_url = kwargs.get("img_url") or ''
    obj.desc = kwargs.get("desc") or ''

    obj.jump_target = kwargs.get("jump_target") or 0
    target_data = kwargs.get("target_data") or ''
    obj.target_data = json_encode(target_data) if target_data else ''

    jump_data = kwargs.get("jump_data") or ''
    obj.jump_data = json_encode(jump_data) if jump_data else ''


class PbBag():

    @classmethod
    def pb_model(cls, data: dict):
        """ 消息模型(非序列化) """
        __proto = http_player_vault_pb2.S2CBag()

        all_bag = data.get("all_bag") or []
        for i in all_bag:
            if i:
                sd = __proto.all_bag.add()
                pack_user_bag(sd, **i)

        new_bag = data.get("new_bag") or []
        __proto.new_bag.extend(new_bag)

        return __proto


def pack_user_bag(obj, **kwargs):
    obj.bag_id = kwargs.get("bag_id") or 0
    obj.bag_sta = kwargs.get("bag_sta") or 0
    obj.got_time = kwargs.get("got_time") or 0
    obj.exp_time = kwargs.get("exp_time") or 0
    obj.bag_type = kwargs.get("bag_type") or 0
    pack_goods_items(obj.goods_items, **kwargs)


class PbCosmetic():

    @classmethod
    def pb_model(cls, data: dict):
        """ 消息模型(非序列化) """
        __proto = http_player_vault_pb2.S2CCosmetic()

        all_cos = data.get("all_cos") or []
        for i in all_cos:
            if i:
                sd = __proto.all_cos.add()
                pack_cosmetic_data(sd, **i)

        new_cos = data.get("new_cos") or []
        __proto.new_cos.extend(new_cos)

        return __proto


def pack_cosmetic_data(obj, **kwargs):
    obj.cosmetic_type = kwargs.get("cosmetic_type") or 0
    obj.got_type = kwargs.get("got_type") or 0
    obj.price = kwargs.get("price") or 0
    obj.got_time = kwargs.get("got_time") or 0
    obj.exp_time = kwargs.get("exp_time") or 0
    extra_info = kwargs.get("extra_info") or ''
    obj.extra_info = json_encode(extra_info) if extra_info else ''
    pack_goods_items(obj.goods_items, **kwargs)


class PbSafeBox():

    @classmethod
    def pb_model(cls, data: dict):
        """ 消息模型(非序列化) """
        __proto = http_player_vault_pb2.S2CSafeBox()

        sb_conf = data.get("safe_box_conf") or {}
        pack_conf_safe_box(__proto, **sb_conf)

        sb_data = data.get("safe_box_data") or {}
        pack_user_safe_box(__proto, **sb_data)
        return __proto


def pack_conf_safe_box(obj, **kwargs):
    """ 打包保险箱配置model """
    obj.safe_box_conf.draw_list[:] = []
    obj.safe_box_conf.save_list[:] = []
    obj.safe_box_conf.complement_list[:] = []
    draw_list = kwargs.get("draw_list") or []
    if draw_list:
        obj.safe_box_conf.draw_list.extend(draw_list)
    save_list = kwargs.get("save_list") or []
    if save_list:
        obj.safe_box_conf.save_list.extend(save_list)
    complement_list = kwargs.get("complement_list") or []
    if complement_list:
        obj.safe_box_conf.complement_list.extend(complement_list)


def pack_user_safe_box(obj, **kwargs):
    obj.safe_box_data.amount = str(kwargs.get("amount") or 0)
    obj.safe_box_data.complement_sta = kwargs.get("complement_sta") or 1
    obj.safe_box_data.complement_count = str(kwargs.get("complement_count") or 0)
    obj.safe_box_data.space = str(kwargs.get("space") or 0)
    obj.safe_box_data.times_limit = kwargs.get("times_limit") or 0
    obj.safe_box_data.used_times = kwargs.get("used_times") or 0
    obj.safe_box_data.exp_time = kwargs.get("exp_time") or 0


class PbGameProp():

    @classmethod
    def pb_model(cls, data: list):
        """ 消息模型(非序列化) """
        __proto = http_player_vault_pb2.S2CGameProp()
        for i in data or []:
            if i:
                sd = __proto.all_game_prop.add()
                pack_game_prop_data(sd, **i)

        return __proto


def pack_game_prop_data(obj, **kwargs):
    obj.game_prop_type = kwargs.get("game_prop_type") or 0
    obj.prop_level = kwargs.get("prop_level") or 1
    extra_info = kwargs.get("extra_info") or ''
    obj.extra_info = json_encode(extra_info) if extra_info else ''
    pack_goods_items(obj.goods_items, **kwargs)


class PbSkin():

    @classmethod
    def pb_model(cls, data: dict, is_more=False, is_upgrade=False):
        """ 消息模型(非序列化) """
        if is_upgrade:  # 升级返回
            __proto = http_player_vault_pb2.S2CSkinUpgrade()
            pack_skin_data(__proto.all_skin, **data)
            return __proto

        elif is_more:  # 二级信息
            __proto = http_player_vault_pb2.S2CSkin()
            all_skin = data.get("all_skin") or []
            for i in all_skin:
                if i:
                    sd = __proto.all_skin.add()
                    pack_skin_data(sd, **i)

        else:  # 一级信息
            __proto = http_player_vault_pb2.S2CSkinGeneral()
            all_skin = data.get("all_skin_general") or []
            for i in all_skin:
                if i:
                    sd = __proto.all_skin_general.add()
                    pack_skin_general_data(sd, **i)

            cur_relics = data.get("cur_relics") or 0
            __proto.cur_relics = cur_relics

        new_skin = data.get("new_skin") or []
        __proto.new_skin.extend(new_skin)

        upgrade_skin = data.get("upgrade_skin") or []
        __proto.upgrade_skin.extend(upgrade_skin)

        return __proto


def pack_skin_general_data(obj, **kwargs):
    obj.star_level = kwargs.get("star_level") or 0
    obj.top_star = kwargs.get("top_star") or 0
    obj.skin_level = kwargs.get("skin_level") or 0
    obj.match_card = kwargs.get("match_card") or 0
    obj.got_type = kwargs.get("got_type") or 0
    obj.cs_type = kwargs.get("cs_type") or 0
    obj.got_time = kwargs.get("got_time") or 0
    obj.exp_time = kwargs.get("exp_time") or 0
    pack_goods_items(obj.goods_items, **kwargs)


def pack_skin_data(obj, **kwargs):
    pack_skin_general_data(obj.all_skin_general, **kwargs)
    obj.shard_id = kwargs.get("shard_id") or 0
    extra_info = kwargs.get("extra_info") or ''
    obj.extra_info = json_encode(extra_info) if extra_info else ''
    obj.other_desc = kwargs.get("other_desc") or ''
    obj.cur_shards = kwargs.get("cur_shards") or 0
    # 下一等级数据
    obj.next_star_level = kwargs.get("next_star_level") or 0
    obj.next_need_shards = kwargs.get("next_need_shards") or 0
    next_extra_info = kwargs.get("next_extra_info") or ''
    obj.next_extra_info = json_encode(next_extra_info) if next_extra_info else ''
    obj.next_need_relics = kwargs.get("next_need_relics") or 0


class PbUsedGoods():

    @classmethod
    def pb_model(cls, data: list):
        """ 消息模型(非序列化) """
        __proto = http_player_vault_pb2.S2CUsedGoods()
        for i in data or []:
            if i:
                sd = __proto.used_goods.add()
                pack_used_goods_data(sd, **i)

        return __proto


def pack_used_goods_data(obj, **kwargs):
    obj.uid = kwargs.get("uid")
    used_goods = kwargs.get("used_goods") or []
    obj.goods_id.extend(used_goods)
