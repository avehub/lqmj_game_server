"""
游戏装扮模型
"""
import asyncio
from .base_rc import BaseRC
from typing import Iterable
from nsanic.libs import tool_dt
from common.public.enum_const import DbKey
from lucky_game.model_db.main import UserCosmetic
from nsanic.libs.tool import json_encode, json_parse
from tortoise.transactions import in_transaction
from lucky_game.const import GotType, CosmeticType
from lucky_game.model_db.main import ItemsCosmetic
from .base_user import BaseUserRC
from .conf_json import ConfJsonRC


class ItemsCosmeticRC(BaseRC):
    db_model = ItemsCosmetic
    tb_name = db_model.sheet_name()

    KEY_GOODS_ID = 'goods_id'

    @classmethod
    async def get_goods_item_by_id_list(cls, id_list: Iterable):
        """ 获取多个装扮 """
        all_cos = await cls.get_cosmetic_items()
        if not all_cos:
            return []

        return [c for c in all_cos if c.get(cls.KEY_GOODS_ID) in id_list]

    @classmethod
    async def get_cosmetic_items(cls):
        """ 获取全部装扮 """
        return await cls.cache_all_conf_item()


class UserCosmeticRC(BaseRC):
    db_model = UserCosmetic
    tb_name = db_model.sheet_name()

    expired_mode = 1
    expired_sec = 2 * 86400

    KEY_COS_ID = 'cos_id'
    KEY_FK_ID = 'cosmetic_item_id'
    KEY_NEWLY = 'user_new_cosmetic'

    @classmethod
    async def get_user_cosmetic_by_id(cls, uid, cos_id=None, goods_id=None):
        """ 通过cos_id / goods_id查询具体项 """
        item = await cls.cache_user_cosmetic(uid=uid)
        if not item:
            return {}

        for i in item:
            if cos_id and i.get(cls.KEY_COS_ID) == cos_id:
                return i
            elif goods_id and i.get(cls.KEY_FK_ID) == goods_id:
                return i
        return {}

    @classmethod
    async def get_user_used_cosmetic(cls, uid, cosmetic_type=None):
        """装扮使用项查询，没有给默认装扮"""
        items = await cls.cache_user_cosmetic(uid=uid)
        if not items:
            gift_conf = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_NEW_USER_GIFT)
            if gift_conf:
                return gift_conf.get("cosmetic")

        if cosmetic_type is not None:
            return [i[cls.KEY_FK_ID] for i in items if
                    i.get("got_type") == GotType.USED and i.get("cosmetic_type") == cosmetic_type]
        else:
            return [i[cls.KEY_FK_ID] for i in items if i.get("got_type") == GotType.USED]

    @classmethod
    async def cache_user_cosmetic(cls, uid, refresh=False):
        """获取用户已获得装扮"""

        async def from_db():
            user_cos = await cls.db_model.get_by_dict({"uid": uid})
            if not user_cos:
                cls.loginfo(f"{uid}, 暂无装扮数据，准备初始化")
                user_cos = await cls.__init_cosmetic_data(uid)

            if user_cos:
                await cls.conf.rds.set_item(key, json_encode(user_cos), ex_time=cls.expired_sec)
                return user_cos
            return []

        key = f'{cls.tb_name}:{uid}'
        if refresh:
            return await cls.conf.rds.locked(key, fun=from_db)

        user_cos = await cls.conf.rds.get_item(key)
        if user_cos:
            return json_parse(user_cos, cls.logerr)
        return await cls.conf.rds.locked(key, fun=from_db)

    @classmethod
    async def check_cosmetic_data(cls, uid, cos_conf):
        """检查用户装扮数据"""
        user_cos = await cls.cache_user_cosmetic(uid)
        if not user_cos:
            return []

        cos_map = {c.get('cosmetic_item_id'): c for c in user_cos}
        for c in cos_conf:
            p_data = cos_map.get(c.get('goods_id'))
            if p_data:
                c.update(p_data)
        return cos_conf

    @classmethod
    async def __init_cosmetic_data(cls, uid):
        """初始化默认装扮"""
        gift_conf = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_NEW_USER_GIFT)
        if not gift_conf:
            return []

        all_prop = await ItemsCosmeticRC.get_cosmetic_items()
        if not all_prop:
            return []

        prop_ids = gift_conf.get("cosmetic")
        filtered_prop_conf = [item for item in all_prop if item.get('goods_id') in prop_ids]

        insert_data = {
            'uid': uid,
            'got_type': GotType.USED,
            'got_time': tool_dt.cur_time(),
            'exp_time': 0
        }
        id_set = set()
        add_tasks = []
        for item in filtered_prop_conf:
            goods_id = item.get("goods_id")
            insert_data["cosmetic_item_id"] = goods_id
            insert_data["cosmetic_type"] = item.get("cosmetic_type")

            # 添加到批量插入的任务列表中
            add_tasks.append(insert_data.copy())
            id_set.add(goods_id)

        await cls.db_model.bulk_create([cls.db_model(**data) for data in add_tasks])
        return add_tasks

    @classmethod
    async def update_user_cosmetic(cls, uid, express: list, is_notice=True):
        """
        更新装扮数据，没有uid/goods_id/time_limit相同的数据就插入
        express: 含有更新数据列表，参考update_assets处理后的数据
        """

        async def update_cache(info):
            await cls.conf.rds.set_item(f'{cls.tb_name}:{uid}', json_encode(info), ex_time=cls.expired_sec)
            if need_notify:
                await BaseUserRC.deal_user_update_goods(uid, id_list=list(need_notify), key_name=cls.KEY_NEWLY)
            return info

        async def insert_cosmetic(info):
            cur_time = tool_dt.cur_time()
            goods_id = info.get('goods_id')
            time_limit = info.get('time_limit') or 0
            insert_cosmetic_data = {
                'uid': uid,
                'got_type': GotType.UNUSED,
                'exp_time': cur_time + time_limit if time_limit > 0 else 0,
                'got_time': cur_time,
                'cosmetic_item_id': goods_id,
                'cosmetic_type': info.get('cosmetic_type')
            }
            insert_obj = await cls.db_model.add_one(insert_cosmetic_data)
            insert_cosmetic_data["cos_id"] = insert_obj.cos_id
            if is_notice:
                need_notify.add(goods_id)
            return insert_cosmetic_data

        old_cos = await cls.cache_user_cosmetic(uid) or []
        need_notify = set()  # 收集需通知物品
        if not old_cos:
            new_cos = [await insert_cosmetic(item) for item in express]
            return await update_cache(new_cos)
        else:
            new_cos = []
            update_tasks = []
            for item in express:
                founded = False  # 找到过标识
                time_limit = item.get('time_limit') or 0
                for op in old_cos:
                    goods_id = item.get('goods_id')
                    if op.get('cosmetic_item_id') == goods_id:
                        exp_time = op.get('exp_time') or 0
                        old_got_type = op.get('got_type') or GotType.NOT_GOT.val

                        # 有永久的过滤，后期可能会补充逻辑
                        if exp_time == 0:
                            pass
                        else:
                            if time_limit == 0:
                                new_exp_time = 0
                            else:
                                new_exp_time = exp_time + time_limit

                            to_update = {}
                            if exp_time != new_exp_time:
                                op['exp_time'] = new_exp_time
                                to_update['exp_time'] = new_exp_time
                            if op.get('got_type') == GotType.NOT_GOT:
                                op['got_type'] = GotType.UNUSED
                                to_update['got_type'] = GotType.UNUSED.val

                            if to_update:
                                update_tasks.append(cls.db_model.update_by_pk(op.get('cos_id'), to_update))
                                if is_notice and old_got_type == GotType.NOT_GOT and op['got_type'] != GotType.NOT_GOT:
                                    need_notify.add(goods_id)
                        founded = True
                        break

                if not founded:
                    res = await insert_cosmetic(item)
                    new_cos.append(res)

            if update_tasks:
                await asyncio.gather(*update_tasks)

            all_cos = old_cos + new_cos
            return await update_cache(all_cos)

    @classmethod
    async def set_user_cosmetic(cls, uid, goods_id, cosmetic_type: CosmeticType):
        """同类型装扮设置使用，同时把其他正在使用的状态修改"""
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                # 将所有相同类型且为使用状态的物品设置为备用状态
                await cls.db_model.filter(
                    uid=uid,
                    cosmetic_item__cosmetic_type=cosmetic_type,
                    got_type=GotType.USED
                ).update(got_type=GotType.UNUSED)

                # 将指定的装扮设置为使用状态
                await cls.db_model.filter(
                    uid=uid,
                    cosmetic_item__goods_id=goods_id
                ).update(got_type=GotType.USED)

                await cls.cache_user_cosmetic(uid, refresh=True)
        except Exception as e:
            cls.loginfo(f"set_user_cosmetic 事务执行失败，原因：{e}")
            return False
        return True

    @classmethod
    async def get_cosmetic_with_items(cls, uid, goods_id):
        """查询玩家装扮，并关联ItemsCosmetic获取基础信息"""
        data_model = await cls.db_model.filter(
            uid=uid,
            cosmetic_item__goods_id=goods_id
        ).prefetch_related("cosmetic_item").first()

        return data_model
