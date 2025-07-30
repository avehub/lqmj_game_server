"""
泛指免费奖励类
"""
from .base_rc import BaseRC
from nsanic.libs.tool import json_encode, json_parse
from tortoise.exceptions import OperationalError
from lucky_game.model_db.main import ConfAward
from lucky_game.model_db.main import Awards
from lucky_game.model_db.extra import RecordsUserAwards


# from .goods_manager import GoodsManagerRC


class ConfAwardRC(BaseRC):
    """ 奖励缓存模型 """
    db_model = ConfAward
    tb_name = db_model.sheet_name()

    KEY_AWARD_TYPE = 'award_type'
    KEY_AWARD_ID = 'award_id'
    KEY_GOODS_ID = "goods_id"
    KEY_GOODS_TYPE = "goods_type"

    @classmethod
    async def get_award_item_by_id(cls, award_id):
        """按ID获取奖项"""
        return await cls.cache_conf_by_pk(award_id)

    @classmethod
    async def get_award_items(cls, award_type=None, is_pack=False):
        info = await cls.cache_all_conf_item()
        if not info:
            return []

        # award_type为空则返回所有，否则返回符合award_type的
        type_awards = [i for i in info if not award_type or i.get(cls.KEY_AWARD_TYPE) == award_type]

        if is_pack and type_awards:
            await cls.pack_goods_conf(type_awards)
        return type_awards

    @classmethod
    async def load_award_conf(cls, key_name, awards: list):
        """
        作用：按 key_name 加载通用配置
        格式：按照data.append的格式
        """
        await cls.pack_goods_conf(awards)
        data = []
        for item in awards:
            data.append({
                "achieve_value": item.get("achieve_value") or 0,
                "achieve_type": item.get("achieve_type") or 0,
                "award_level": item.get("award_level") or 0,
                "img_url": item.get("img_url"),
                "conf_items": item.get("conf_items")
            })
        await cls.conf.rds.set_item(key_name, json_encode(data))
        return data

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


class AwardRC(BaseRC):
    db_model = Awards
    tb_name = db_model.sheet_name()

    @classmethod
    async def get_award_by_filter(cls, award_id: any = None, award_type: any = None, level: int = None,
                                  name: str = None,
                                  order_field: str = None):
        """按条件获取奖项"""
        try:
            query = {}
            if award_id is not None:
                if isinstance(award_id, list):
                    query["award_id__in"] = award_id
                else:
                    query["award_id"] = award_id
            if award_type is not None:
                if isinstance(award_type, list):
                    query["type__in"] = award_type
                else:
                    query["type"] = award_type
            if level is not None:
                if isinstance(level, list):
                    query["level__in"] = level
                else:
                    query["level"] = level
            if name is not None:
                query["name__contains"] = name
            if order_field is None:
                order_field = "-award_id"
            print("query:", query)
            result = await cls.db_model.filter(**query).order_by(order_field).values()
            if not result:
                return None, "暂无战绩"
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return result, "成功"


class UserAwardRC(BaseRC):
    """
    用户奖励记录
    泛指限量的单奖，例如：抖音侧边栏访问奖励
    """
    db_model = RecordsUserAwards
    tb_name = db_model.sheet_name()

    expired_mode = 0
    expired_sec = 2 * 86400

    @classmethod
    async def cache_user_award_records(cls, unique: dict):
        """获取/缓存领奖记录"""

        async def from_db():
            try:
                db_info = await cls.db_model.get_by_dict(unique, limit=1)
                if db_info:
                    await cls.conf.rds.set_item(key, json_encode(db_info), ex_time=cls.expired_sec)
                    return db_info
            except OperationalError:
                cls.conf.info_log("cache_user_award_records 暂无表")
            return {}

        unique_val = '_'.join([str(unique.get(k)) for k in sorted(unique)])
        key = f'{cls.tb_name}:{unique_val}'
        info = await cls.conf.rds.get_item(key)
        if info:
            return json_parse(info, cls.conf.error_log)
        return await cls.conf.rds.locked(key, fun=from_db)

    @classmethod
    async def update_user_award_records(cls, unique: dict, new_data: dict, old_data):
        """更新用户领奖记录"""

        async def update_cache(info: dict):
            unique_val = '_'.join([str(unique.get(k)) for k in sorted(unique)])
            key = f'{cls.tb_name}:{unique_val}'
            await cls.conf.rds.set_item(key, json_encode(info), ex_time=cls.expired_sec)

        if not old_data:
            await cls.db_model.split_add_one(new_data)
            await update_cache(new_data)
            return new_data

        sta = await cls.db_model.update_by_cond(unique, new_data)
        if sta:
            old_data.update(new_data)
            await update_cache(old_data)
            return old_data
        return
