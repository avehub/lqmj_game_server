"""
泛指免费奖励类
"""
from .base_rc import BaseRC
from nsanic.libs.tool import json_encode, json_parse
from tortoise.exceptions import OperationalError
from lucky_game.model_db.main import ConfAward
from lucky_game.model_db.extra import RecordsUserAwards
from .goods_manager import GoodsManagerRC


class ConfAwardRC(BaseRC):
    """ 奖励缓存模型 """
    db_model = ConfAward
    tb_name = db_model.sheet_name()

    KEY_AWARD_TYPE = 'award_type'
    KEY_AWARD_ID = 'award_id'


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
            await GoodsManagerRC.pack_goods_conf(type_awards)
        return type_awards

    @classmethod
    async def load_award_conf(cls, key_name, awards: list):
        """
        作用：按 key_name 加载通用配置
        格式：按照data.append的格式
        """
        await GoodsManagerRC.pack_goods_conf(awards)
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
