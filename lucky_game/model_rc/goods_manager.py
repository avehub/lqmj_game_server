"""
物品管理员系统
通用基础物品处理模型
"""
from .base_rc import BaseRC
from .base_goods import ItemsBaseRC
from .base_cosmetic import ItemsCosmeticRC
from .base_prop import ItemsPropRC
from .base_skin import ItemsSkinRC
from lucky_game.const import GoodsType


class GoodsManagerRC(BaseRC):
    """

    配置字段内容示例：[{"goods_id": 1000, "goods_type": 1, "time_limit": 0, "usage_limit": 0, "goods_count": 600000}]
    加载通用字段："goods_name"、"add_type"、"img_url"、"desc"、"jump_target"、"target_data"、"jump_data"
    加载全部字段：is_all=True
    """
    KEY_GOODS_ID = "goods_id"
    KEY_GOODS_TYPE = "goods_type"

    # 通用配置字段名称
    CONF_FIELDS = [
        "conf_items", "act_awards", "daily_awards", "level_awards", "season_awards", "display_awards"
    ]

    # GoodsType对应表名
    MODEL_MAP = {
        GoodsType.V_ASSET: ItemsBaseRC,
        GoodsType.COSMETIC: ItemsCosmeticRC,
        GoodsType.GAME_PROP: ItemsPropRC,
        GoodsType.CARD_SKIN: ItemsSkinRC,
        GoodsType.SKIN_SHARD: ItemsBaseRC,
        GoodsType.MAGIC: ItemsBaseRC,
        GoodsType.G_ASSET: ItemsBaseRC
    }

    @classmethod
    def get_db_model(cls, goods_type: GoodsType):
        """
        根据goods_type返回正确的表名
        """
        model = cls.MODEL_MAP.get(goods_type)
        if not model:
            raise ValueError(f"Unsupported goods type: {goods_type}")
        return model

    @classmethod
    async def pack_goods_conf(cls, item_list: list, is_all=False):
        """
        物品打包 1：主要打包各种业务的基础conf_items
        传入查询好的业务数据，不能传空值
        """
        all_goods_ids = {}
        # 遍历item_list，收集所有需要查询的商品ID，并按goods_type分类
        for i in item_list:
            for cf in i.get("conf_items") or []:
                goods_type = cf.get(cls.KEY_GOODS_TYPE)
                if goods_type:
                    all_goods_ids.setdefault(goods_type, set()).add(cf[cls.KEY_GOODS_ID])

        goods_map = await cls.get_all_goods_map(all_goods_ids)

        for item in item_list:
            conf_items = item.get("conf_items")
            if conf_items:
                cls.pack_item_list(conf_items, goods_map, is_all)

    @classmethod
    async def pack_goods_many_conf(cls, item_list: list, is_all=False):
        """
        物品打包 2：主要一次性打包一条数据的多个物品配置
        传入查询好的业务数据，不能传空值
        """
        all_goods_ids = {}
        # 遍历item_list，收集所有需要查询的商品ID，并按goods_type分类
        for i in item_list:
            for field in cls.CONF_FIELDS:
                for cf in i.get(field) or []:
                    goods_type = cf.get(cls.KEY_GOODS_TYPE)
                    if goods_type:
                        all_goods_ids.setdefault(goods_type, set()).add(cf[cls.KEY_GOODS_ID])

        goods_map = await cls.get_all_goods_map(all_goods_ids)

        for item in item_list:
            for field in cls.CONF_FIELDS:
                field_item_list = item.get(field) or []
                if field_item_list:
                    cls.pack_item_list(field_item_list, goods_map, is_all)

    @classmethod
    async def pack_goods_list(cls, item_list: list, is_all=False):
        """
        物品打包 3：直接打包统计好的conf_items列表，
        直接传入conf_items组成的列表，不能传空值
        """
        all_goods_ids = {}
        # 遍历item_list，收集所有需要查询的商品ID，并按goods_type分类
        for i in item_list:
            goods_type = i.get(cls.KEY_GOODS_TYPE)
            if goods_type:
                all_goods_ids.setdefault(goods_type, set()).add(i[cls.KEY_GOODS_ID])

        goods_map = await cls.get_all_goods_map(all_goods_ids)

        cls.pack_item_list(item_list, goods_map, is_all)

    @classmethod
    async def get_all_goods_map(cls, all_goods_ids):
        """
        查询所有物品信息
        创建物品映射字典
        """
        goods_map = {}
        for goods_type, g_ids in all_goods_ids.items():
            if g_ids:
                model = cls.get_db_model(goods_type)
                goods = await model.get_goods_item_by_id_list(g_ids) or []
                for g in goods:
                    goods_map[g[cls.KEY_GOODS_ID]] = g

        return goods_map

    @classmethod
    def pack_item_list(cls, item_list, goods_map, is_all):
        """打包具体字段"""
        for item in item_list:
            gc = goods_map.get(item[cls.KEY_GOODS_ID])
            if not gc:
                continue
            if is_all:
                for key, value in gc.items():
                    item[key] = value
            else:
                item["goods_name"] = gc.get("goods_name", '')
                item["add_type"] = gc.get("add_type", 0)
                item["put_type"] = gc.get("put_type", 0)
                item["img_url"] = gc.get("img_url", '')
                item["desc"] = gc.get("desc", '')
                item["jump_target"] = gc.get("jump_target", 0)
                item["target_data"] = gc.get("target_data", '')
                item["jump_data"] = gc.get("jump_data", '')


