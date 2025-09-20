"""
大富翁相关
"""
import random
from nsanic.libs.tool import json_encode, json_parse
from lucky_game.const import EventType
from lucky_game.model_rc.base_rc import BaseRC
from lucky_game.model_db.main import UserMonopoly, ConfMonopolyMap, ConfMonopolyEvent
from lucky_game.model_rc.goods_manager import GoodsManagerRC

class MonopolyMapRC(BaseRC):
    """大富翁地图"""
    db_model = ConfMonopolyMap
    tb_name = db_model.sheet_name()


    @classmethod
    async def get_monopoly_map(cls, is_pack=False):
        map_conf = await cls.cache_all_conf_item(orders='cell_id')
        if is_pack and map_conf:
            await GoodsManagerRC.pack_goods_conf(map_conf)
        return map_conf


class MonopolyEventRC(BaseRC):
    """大富翁事件"""
    db_model = ConfMonopolyEvent
    tb_name = db_model.sheet_name()


    @classmethod
    async def get_monopoly_event(cls, is_pack=False):
        event_confs = await cls.cache_all_conf_item()
        if is_pack and event_confs:
            await GoodsManagerRC.pack_goods_conf(event_confs)
        return event_confs

    @classmethod
    async def randomly_gen_event(cls):
        """随机生成通用事件"""
        event_confs = await cls.get_monopoly_event(is_pack=True)
        if event_confs:
            common_events = [e for e in event_confs if e.get("event_type") == EventType.COMMON_EVENT]
            if common_events:
                return random.choice(common_events)
        return {}



class UserMonopolyRC(BaseRC):
    """用户大富翁记录"""
    db_model = UserMonopoly
    tb_name = db_model.sheet_name()

    expired_mode = 1
    expired_sec = 2 * 86400


    @classmethod
    async def cache_by_pk(cls, uid, **kwargs):
        """查询玩家大富翁记录，没有的活跃玩家给默认值"""
        info = await super().cache_by_pk(uid)
        if info:
            info["map"] = json_parse(info.get("map", {}), cls.conf.error_log)
        else:
            info = {
                "uid": uid,
                "map": {},
                "position": 0,
                # 是否默认值判断（仅此处有）
                "default_cache": 1
            }
            await cls.conf.rds.set_item(f"{cls.tb_name}:{uid}", json_encode(info), ex_time=cls.expired_sec)
        return info

    @classmethod
    async def update_user_monopoly(cls, uid, update_info: dict, old_info: dict):
        """更新用户大富翁记录"""

        async def update_cache(db_info):
            await cls.conf.rds.set_item(f"{cls.tb_name}:{uid}", json_encode(db_info), ex_time=cls.expired_sec)
            return db_info

        if not old_info or old_info.get("default_cache"):
            add_data = {
                "uid": uid,
                **update_info
            }
            sta = await cls.db_model.add_one(add_data)
            if sta:
                return await update_cache(add_data)
        else:
            sta = await cls.db_model.update_by_pk(uid, update_info, old_info, fun_success=update_cache)
            return sta if isinstance(sta, bool) else True
