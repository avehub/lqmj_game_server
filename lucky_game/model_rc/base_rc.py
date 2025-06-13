from typing import Union
from nsanic.libs.tool import json_parse, json_encode
from nsanic.orm.rc_model import RCModel
from tortoise.expressions import Q
from tortoise.exceptions import OperationalError
from common.public.common_class import CommonApi


class BaseRC(RCModel):
    db_model = None
    db_model_public = None

    tb_name = None
    tb_name_public = None

    pydantic = None
    pydantic_public = None

    expired_mode = 0
    expired_sec = 2 * 86400

    @classmethod
    async def cache_multiterm_by_cond(cls, cond: dict, field=None, split=None, limit=0):
        """
        缓存多条 通过多条件
        cond: 查询条件
        extra_cond: 额外条件
        field: 查询字段，不指定则查全部
        """

        async def from_db():
            db_info = await cls.db_model.get_by_dict(cond, field, split=split, limit=limit)
            if db_info:
                if cls.expired_mode:
                    await cls.conf.rds.set_item(key, db_info, ex_time=cls.expired_sec)
                else:
                    await cls.conf.rds.set_hash(key_name, unique_val, db_info)
                await cls.fun_set_cache(db_info)
                return db_info
            return

        key_name = f'{cls.tb_name}'
        unique_val = '_'.join([str(cond.get(k)) for k in sorted(cond)])
        key = f'{key_name}:{unique_val}'
        if cls.expired_mode:
            info = await cls.conf.rds.get_item(key)
        else:
            info = await cls.conf.rds.get_hash(key_name, unique_val)
        if info:
            return json_parse(info, cls.logerr)
        return await cls.conf.rds.locked(key, fun=from_db)

    @classmethod
    async def cache_all_conf_item(
            cls,
            has_status=True,
            orders: Union[str, list, tuple] = '-created',
            field: list = None,
            cond: dict = None,
            key_name=None,
            is_lock=True
    ):
        """
        根据主键id 缓存所有配置项
        key_name: 缓存键
        """

        async def from_db():
            query_params = cond or {}
            if has_status:
                query_params.update({"status": 1})
            db_info = await cls.db_model.get_by_dict(query_params, field, orders=orders)
            if db_info:
                cache_db_info_dict = {}
                pk_field = cls.db_model.pk_name()
                for one_info in db_info:
                    _id = one_info.get(pk_field)
                    cache_db_info_dict[str(_id)] = json_encode(one_info)
                await cls.conf.rds.set_hash_bulk(key_name, cache_db_info_dict)
                return db_info
            return []

        key_name = key_name or f'{cls.tb_name}'
        info_list = await cls.conf.rds.get_hash_val(key_name)
        if info_list:
            info_list = [json_parse(one, cls.logerr) for one in info_list]
            if orders:
                order_key = orders[1:] if orders[0] == '-' else orders
                info_list.sort(key=lambda d: d[order_key], reverse=True if orders[0] == '-' else False)
            return info_list
        if is_lock:
            return await cls.conf.rds.locked(key_name, fun=from_db)
        return await from_db()

    @classmethod
    async def cache_all_conf_item_public(cls, has_status: bool = True, orders: Union[str, list, tuple] = '-created',
                                         foreign_key='skin_public'):
        """ 根据主键id 缓存所有配置项 + 公共配置项 """

        async def from_db():
            query_params = {}
            if has_status:
                query_params.update({"status": 1})
            # 联合查询
            data_model = await cls.db_model.filter(Q(**query_params)).select_related(foreign_key).order_by(orders)
            if data_model:
                cache_db_info_dict = {}
                for o in data_model:
                    data = await cls.pydantic.from_tortoise_orm(o)
                    public_data = await cls.pydantic_public.from_tortoise_orm(getattr(o, foreign_key))
                    # 将 data 和 public_data 数据合并到一个字典中
                    combined_data = {
                        **data.dict(),
                        **public_data.dict()
                    }
                    cache_db_info_dict[str(data.goods_id)] = json_encode(combined_data)

                await cls.conf.rds.set_hash_bulk(key_name, cache_db_info_dict)
                return [json_parse(v) for v in cache_db_info_dict.values()]
            return []

        key_name = f'{cls.tb_name}'
        info_list = await cls.conf.rds.get_hash_val(key_name)

        if info_list:
            info_list = [json_parse(one) for one in info_list]
            if orders:
                order_key = orders[1:] if orders[0] == '-' else orders
                info_list.sort(key=lambda d: d[order_key], reverse=True if orders[0] == '-' else False)
            return info_list
        return await cls.conf.rds.locked(key_name, fun=from_db)

    @classmethod
    async def cache_conf_item_by_id_list(cls, id_list):
        """ 根据id_list获取多项配置 """

        async def from_db(*pk_list):
            query_params = {"status": 1}
            if pk_list:
                query_params.update({f'{pk_field}__in': pk_list})
            db_info = await cls.db_model.get_by_dict(query_params)
            if db_info:
                db_info_dict = {}
                cache_db_info_dict = {}
                for one_info in db_info:
                    _id = one_info.get(pk_field)
                    db_info_dict[_id] = one_info
                    cache_db_info_dict[str(_id)] = json_encode(one_info)
                await cls.conf.rds.set_hash_bulk(key_name, cache_db_info_dict)

                result = []
                for _id in id_list:
                    data = db_info_dict.get(_id)
                    data and result.append(data)
                return result
            return []

        key_name = f'{cls.tb_name}'
        id_list = [id_list] if isinstance(id_list, int) else list(id_list)
        pk_field = cls.db_model.pk_name()
        info_list = await cls.conf.rds.conn.hmget(key_name, id_list)
        no_cache_idx = []
        for i, one in enumerate(info_list):
            if not one:
                no_cache_idx.append(i)

        if no_cache_idx:
            no_cache_id_list = [id_list[i] for i in no_cache_idx]
            lock_name = f'{key_name}_{no_cache_id_list}'
            no_cache_data = await cls.conf.rds.locked(lock_name, from_db, no_cache_id_list)
            for i, d in enumerate(no_cache_data):
                idx = no_cache_idx[i]
                info_list[idx] = d

        if info_list:
            return [json_parse(one, cls.logerr) for one in info_list]
        return await cls.conf.rds.locked(key_name, fun=from_db)

    @classmethod
    async def cache_conf_item_by_id_list_public(cls, id_list, foreign_key='skin_public'):
        """ 根据id_list获取多项配置项 + 公共配置项 """

        async def from_db(*pk_list):
            query_params = {"status": 1}
            if pk_list:
                query_params.update({f'{pk_field}__in': pk_list})
            # 联合查询
            data_model = await cls.db_model.filter(Q(**query_params)).select_related(foreign_key)
            if data_model:
                db_info_dict = {}
                cache_db_info_dict = {}
                for o in data_model:
                    data = await cls.pydantic.from_tortoise_orm(o)
                    public_data = await cls.pydantic_public.from_tortoise_orm(getattr(o, foreign_key))
                    # 将 data 和 public_data 数据合并到一个字典中
                    combined_data = {
                        **data.dict(),
                        **public_data.dict()
                    }
                    _id = data.goods_id
                    db_info_dict[_id] = combined_data
                    cache_db_info_dict[str(_id)] = json_encode(combined_data)

                await cls.conf.rds.set_hash_bulk(key_name, cache_db_info_dict)
                result = []
                for _id in id_list:
                    data = db_info_dict.get(_id)
                    if data:
                        result.append(data)
                return result
            return []

        key_name = f'{cls.tb_name}'
        id_list = list(id_list)
        pk_field = cls.db_model.pk_name()
        info_list = await cls.conf.rds.conn.hmget(key_name, id_list)
        no_cache_idx = []
        for i, one in enumerate(info_list):
            if not one:
                no_cache_idx.append(i)

        if no_cache_idx:
            no_cache_id_list = [id_list[i] for i in no_cache_idx]
            lock_name = f'{key_name}_{no_cache_id_list}'
            no_cache_data = await cls.conf.rds.locked(lock_name, from_db, no_cache_id_list)
            for i, d in enumerate(no_cache_data):
                idx = no_cache_idx[i]
                info_list[idx] = d

        if info_list:
            return [json_parse(one) for one in info_list if one]
        return await cls.conf.rds.locked(key_name, fun=from_db)

    @classmethod
    async def cache_conf_by_pk(cls, pk_val, has_status=True, orders: Union[str, list, tuple] = '-created',
                               field: list = None):
        """通过主键缓存，无缓存时优先全部缓存"""
        info = await cls.conf.rds.get_hash(cls.tb_name, pk_val)
        if info:
            return json_parse(info, cls.logerr)

        await cls.cache_all_conf_item(has_status, orders, field)
        info = await cls.conf.rds.get_hash(cls.tb_name, pk_val)
        if info:
            return json_parse(info, cls.logerr)
        return {}

    @classmethod
    async def cache_conf_by_pk_public(cls, pk_val, has_status=True, orders: Union[str, list, tuple] = '-created'):
        """通过主键缓存配置项 + 公共配置项，无缓存时优先全部缓存"""
        info = await cls.conf.rds.get_hash(cls.tb_name, pk_val)
        if info:
            return json_parse(info, cls.logerr)
        await cls.cache_all_conf_item_public(has_status, orders)
        info = await cls.conf.rds.get_hash(cls.tb_name, pk_val)
        if info:
            return json_parse(info, cls.logerr)
        return {}


class BaseCommonRC(RCModel, CommonApi):

    @classmethod
    async def update_int_field(cls, club_id: int, field_name: str, value: int, operation: str = 'add'):
        """
        更新数据表的整型字段

        Args:
            club_id (int): 茶馆ID
            field_name (str): 要修改的字段名
            value (int): 修改的值
            operation (str): 操作类型，'add' 或 'sub'，默认为'add'

        Returns:
            tuple: (bool, str) - (操作结果, 消息)
        """
        if operation not in ['add', 'sub']:
            return False, "无效的操作类型，只支持'add'或'sub'"
        try:
            # 获取当前值
            data = await cls.db_model.get_or_none(id=club_id)
            if not data:
                return False, "数据不存在"

            # 获取当前字段值
            current_value = getattr(data, field_name)
            if not isinstance(current_value, (int, float)):
                return False, f"字段{field_name}不是数值类型"

            # 计算新值
            if operation == 'add':
                new_value = current_value + value
            else:
                new_value = current_value - value
            if new_value < 0:
                return False, "数值不能小于0"
            # 更新数据
            update_data = {field_name: new_value}
            up = await cls.db_model.update_by_pk(club_id, update_data)
            if not up:
                return False, "更新失败"
        except OperationalError as e:
            return False, f"更新失败：{str(e)}"
        return True, "更新成功"


