"""
用户相关
"""
import asyncio
from typing import Union, Iterable
from datetime import datetime, date
from nsanic.libs import tool_dt
from nsanic.libs.tool import json_encode, json_parse
from nsanic.orm.rc_model import RCModel
from c_services.const.cs_enum_const import CmdWorkers
from common.public.enum_const import BaseEnum, CacheKey, BanType
from common.utils.kit_dt import KitDt
from tortoise.exceptions import OperationalError
from lucky_game.const import GoodsItem, ReasonCostGold, ReasonCostDiamond
from lucky_game.model_db.log import RecordsUserBan
from lucky_game.model_db.main import User
from lucky_game.model_rc.base_rc import BaseCommonRC


class BaseUserRC(BaseCommonRC):
    db_model = User
    tb_name = db_model.sheet_name()

    expired_mode = 1
    expired_sec = 172800  # 2 * 86400

    KEY_PHONE_CACHE = 'phone'
    KEY_EMAIL_CACHE = 'email'
    KEY_DEVICE_ID = 'device_id'
    KEY_UNION_ID = 'union_id'
    KEY_OPENID = 'open_id'
    KEY_SESSION = "session_key"
    KEY_USER_PAY_INFO = "user_pay_info"  # 已下单的支付信息
    KEY_USER_PAID_ORDER = "user_paid_order"  # 已支付订单

    """限制次数类缓存"""
    KEY_BUY_LIMIT = "buy_limit"  # 限购情况
    KEY_USE_LIMIT = "use_limit"  # 使用限制情况
    KEY_REQ_LIMIT = "req_limit"  # 限流情况

    @classmethod
    async def cache_session_key(cls, uid, session_key):
        await cls.conf.rds.set_item(f"{cls.KEY_SESSION}:{uid}", session_key, ex_time=7 * 86400)

    @classmethod
    async def get_session_key(cls, uid):
        return await cls.conf.rds.get_item(f"{cls.KEY_SESSION}:{uid}")

    @classmethod
    async def cache_user_pay_info(cls, uid, order_id, pay_info):
        """缓存平台的支付信息"""
        await cls.conf.rds.set_item(f"{cls.KEY_USER_PAY_INFO}:{uid}_{order_id}", json_encode(pay_info), ex_time=86400)

    @classmethod
    async def get_user_pay_info(cls, uid, order_id):
        """获取平台的支付信息"""
        pay_info = await cls.conf.rds.get_item(f"{cls.KEY_USER_PAY_INFO}:{uid}_{order_id}")
        if pay_info:
            return json_parse(pay_info, cls.logerr)
        return {}

    @classmethod
    async def cache_user_paid_order(cls, uid, order_id, goods=None, gifts=None):
        """
        缓存已支付的订单（预发货）
        若有多个未领取，则存为列表
        """
        # 初始化默认值
        goods = goods or []
        gifts = gifts or []

        cache_key = f"{cls.KEY_USER_PAID_ORDER}:{uid}"

        # 获取已有的缓存订单信息
        old_items = await cls.conf.rds.get_item(cache_key)
        if old_items:
            old_items = json_parse(old_items, cls.logerr)  # 解析为 Python 列表
        else:
            old_items = []

        if not any(item.get("order_id") == order_id for item in old_items):  # 检查是否已经存在该订单号
            new_order = {
                "order_id": order_id,
                "goods": goods,
                "gifts": gifts,
            }
            old_items.append(new_order)  # 添加新订单信息
        await cls.conf.rds.set_item(cache_key, json_encode(old_items), ex_time=86400)

    @classmethod
    async def get_user_paid_order(cls, uid):
        """
        获取已支付的订单，并删除缓存（预发货）
        """
        cache_key = f"{cls.KEY_USER_PAID_ORDER}:{uid}"

        old_items = await cls.conf.rds.get_item(cache_key)
        if old_items:
            old_items = json_parse(old_items, cls.logerr)
            await cls.conf.rds.drop_item(cache_key)  # 删除缓存

            return old_items
        return []

    @classmethod
    async def get_relief_count(cls, uid):
        """ 获取救济金次数 """
        relief_info = await cls.conf.rds.get_item(f"{cls.KEY_USE_LIMIT}:'relief':{uid}")
        if relief_info:
            return json_parse(relief_info, cls.logerr)
        return {}

    @classmethod
    async def cache_relief_count(cls, uid, data: dict):
        """ 缓存救济金次数 """
        return await cls.conf.rds.set_item(f"{cls.KEY_USE_LIMIT}:{'relief'}:{uid}", json_encode(data),
                                           ex_time=cls.expired_sec)

    @classmethod
    async def get_safe_box_count(cls, uid):
        """ 获取保险箱使用次数 """
        safe_box_info = await cls.conf.rds.get_item(f"{cls.KEY_USE_LIMIT}:'safe_box':{uid}")
        if safe_box_info:
            return json_parse(safe_box_info, cls.logerr)
        return {}

    @classmethod
    async def cache_safe_box_count(cls, uid, data: dict):
        """ 缓存保险箱使用次数 """
        return await cls.conf.rds.set_item(f"{cls.KEY_USE_LIMIT}:'safe_box':{uid}", json_encode(data),
                                           ex_time=cls.expired_sec)

    @classmethod
    async def get_count_buy_limit(cls, uid, trade_item):
        """ 获取短期限购次数（通用）  """
        data = await cls.conf.rds.get_item(f"{cls.KEY_BUY_LIMIT}:{uid}_{trade_item}")
        if data:
            data_dict = json_parse(data, cls.logerr)
            cur_time = tool_dt.cur_time()

            if cur_time > data_dict.get("time_node", 0):
                # 如果当前时间超过了周期结束时间，重置 buy_times 为 0
                data_dict["buy_times"] = 0

            return data_dict
        return {}

    @classmethod
    async def cache_count_buy_limit(cls, uid, trade_item, data):
        """ 缓存短期限购次数（通用） """
        # 从 data 中获取周期类型，例如：{"times": 5, "limit_period": 1}
        buy_limit = data.get("buy_limit")
        limit_period = buy_limit.get("limit_period", 0)
        cur_time = tool_dt.cur_time()

        # 计算周期结束时间
        time_node = KitDt.cal_period_deadline(limit_period, cur_time)
        data["time_node"] = time_node

        return await cls.conf.rds.set_item(f"{cls.KEY_BUY_LIMIT}:{uid}_{trade_item}", json_encode(data),
                                           ex_time=cls.expired_sec)

    @classmethod
    async def cache_by_pk(cls, pk_val: Union[bytes, int, str], **kwargs):
        """ 玩家去数据库都用这个！！ """

        async def from_db():
            db_info = await cls.db_model.get_by_pk(pk_val)
            if db_info:
                if cls.expired_mode:
                    await cls.conf.rds.set_item(key, json_encode(db_info), ex_time=cls.expired_sec)
                else:
                    await cls.conf.rds.set_hash(cls.tb_name, pk_val, json_encode(db_info))
                return db_info
            return

        if isinstance(pk_val, bytes):
            pk_val = pk_val.decode('utf-8')
        key = f"{cls.tb_name}:{pk_val}"
        if cls.expired_mode:
            info = await cls.conf.rds.get_item(key)
        else:
            info = await cls.conf.rds.get_hash(cls.tb_name, pk_val)
        if info:
            return json_parse(info, cls.logerr)

        return await from_db()

    @classmethod
    async def cache_by_uid(cls, uid: Union[bytes, int, str], is_lock=True):
        if is_lock:
            info = await cls.conf.rds.locked(f"{cls.tb_name}:{uid}", cls.cache_by_pk, (uid,))
        else:
            info = await cls.cache_by_pk(uid)
        if info:
            info["gold"] = float(info.get("gold", 0))
        return info

    @classmethod
    async def cache_by_unique(
            cls, unique: dict, suffix: str, split: Union[str, int, float, datetime, date] = None, **kwargs):
        info = await cls.cache_by_unique_inner(unique, suffix, split, **kwargs)
        if info:
            info["gold"] = float(info.get("gold", 0))
        return info

    @classmethod
    async def cache_by_unique_inner(
            cls, unique: dict, suffix: str, split: Union[str, int, float, datetime, date] = None, **kwargs):
        """添加通过联合主键缓存的逻辑"""

        async def from_db():
            info = await cls.db_model.get_by_dict(unique, limit=1, split=split)
            if info:
                pk_val = info.get(cls.db_model.pk_name())
                if cls.expired_mode:
                    await cls.conf.rds.set_item(key, pk_val, ex_time=cls.expired_sec)
                else:
                    await cls.conf.rds.set_hash(key_name, unique_val, pk_val)
                return info
            return

        key_name = f'{cls.db_model.sheet_name(split)}_{suffix}'
        if unique.get("platform"):
            unique_copy = unique.copy()
            platform = unique_copy.pop("platform") or 0
            unique_val = '_'.join([str(unique_copy.get(k)) for k in sorted(unique_copy)])
            key = f'{key_name}_{platform}:{unique_val}'
        else:
            unique_val = '_'.join([str(unique.get(k)) for k in sorted(unique)])
            key = f'{key_name}:{unique_val}'

        if cls.expired_mode:
            item_id = await cls.conf.rds.get_item(key)
        else:
            item_id = await cls.conf.rds.get_hash(key_name, unique_val)
        if item_id:
            return await cls.cache_by_uid(item_id)
        return await cls.conf.rds.locked(key, fun=from_db)

    @classmethod
    async def update_cache(cls, pk_val, new_info: dict):
        new_info["gold"] = float(new_info.get("gold", 0))
        if cls.expired_mode:
            key = f"{cls.tb_name}:{pk_val}"
            await cls.conf.rds.set_item(key, json_encode(new_info), ex_time=cls.expired_sec)
        else:
            await cls.conf.rds.set_hash(cls.tb_name, pk_val, json_encode(new_info))

    @classmethod
    async def update_info(cls, info: dict, new_info: dict):
        """更新玩家信息，必须是玩家在线的情况下"""
        pk_val = info.get('uid')
        sta = await cls.db_model.update_by_pk(pk_val, new_info, old_data=info)
        if sta:
            info.update(new_info)
            await cls.update_cache(pk_val, info)
            return info
        return

    @classmethod
    async def insert_statement(cls, u_info: dict, update_info: dict, *reason_list, _type=1):
        """ 插入资产流水 """
        send_task = []
        for reason in reason_list:
            # 如果 reason 是 int 类型，尝试转换为 ReasonCostGold 枚举
            if isinstance(reason, int):
                reason = ReasonCostGold.find_member_by_val(reason)

            if isinstance(reason, ReasonCostGold):
                cmd = CmdWorkers.INSERT_GOLD_STATEMENT
                data = {
                    "reason_id": reason.val,  # 使用 .value 替代 .val
                    "reason_desc": reason.phrase,  # 使用 .name 替代 .phrase
                    "count": update_info.get("gold"),
                    "res_count": u_info.get("gold"),
                    "g_type": _type
                }
            elif isinstance(reason, ReasonCostDiamond):
                cmd = CmdWorkers.INSERT_DIAMOND_STATEMENT
                data = {
                    "reason_id": reason.val,
                    "reason_desc": reason.phrase,
                    "count": update_info.get("diamond"),
                    "res_count": u_info.get("diamond"),
                    "d_type": _type
                }
            else:
                continue
            send_task.append(cls.push_task2worker(cmd, data, u_info.get("uid")))

        if send_task:
            await asyncio.gather(*send_task)

    @classmethod
    async def update_user_asset(cls, uid, update_info: dict, *reasons: Iterable[BaseEnum]):
        """
        update_info: 更新数据，filed必须与User表中对应上，否在更新可能会失败
        更新玩家信息，必须是玩家在线的情况下
        """

        async def update_db():
            # 在此查一遍缓存
            info = await cls.cache_by_uid(uid, is_lock=False) or {}
            for field, val in update_info.items():
                if field in (GoodsItem.GOLD.desc, GoodsItem.DIAMOND.desc):
                    new_count = info.get(field, 0) + val
                    update_info[field] = max(new_count, 0)

            sta = await cls.db_model.update_by_pk(uid, update_info, old_data=info)
            if sta:
                info.update(update_info)
                await cls.update_cache(uid, info)
                return info
            return

        ori_update_info = {**update_info}
        p_info = await cls.conf.rds.locked(f"{uid}_update_asset", update_db)
        if p_info:
            await cls.insert_statement(p_info, ori_update_info, *reasons)
        return p_info

    @classmethod
    async def get_receiver_by_uid_list(cls, uid_list):
        """获取所有群发玩家uid"""
        receivers_data = await User.get_by_dict({"uid__in": uid_list}, field=['uid'])
        receivers = []
        for u in receivers_data or []:
            if u:
                receivers.append(u.get('uid'))
        return receivers

    @classmethod
    async def fetch_uid_by_batch_size(cls, batch_size: int = 1000, start_uid: int = 0):
        """ 获取uid """
        batch = await cls.db_model.filter(uid__gt=start_uid).limit(batch_size).values('uid')
        if not batch:
            return []
        # 更新最后看到的 uid
        # 扩展 all_uid 列表，添加新一批的 uid
        all_uid = []
        all_uid.extend([item['uid'] for item in batch])
        return all_uid

    @classmethod
    async def get_online_uid(cls, uid_list=None):
        """
        获取全部在线用户uid集合
        uid_list：如果非空则只判断uid_list里的在线用户
        """
        online_data = await cls.conf.rds.conn.hkeys(CacheKey.WS_ONLINE_INFO)
        if online_data:
            online_uid = {int(uid) for uid in online_data}
            if uid_list:
                return online_uid.intersection(set(uid_list))
            return online_uid
        return set()

    @classmethod
    async def deal_user_update_goods(cls, uid, id_list=None, is_del=False, key_name='user_new_bag'):
        """
        用户新获得/可升级物品缓存goods_id或者其他id集合用于通知
        id_list: []时删所有，None时查询
        is_del: 是否点击删除
        key_name: 缓存名
        """
        key = f"{key_name}:{uid}"

        # 删除操作
        if is_del:
            if id_list:
                await cls.conf.rds.conn.srem(key, *id_list)
            else:
                await cls.conf.rds.conn.delete(key)
            return True

        # 添加操作
        if id_list:
            await cls.conf.rds.conn.sadd(key, *id_list)
            return True

        res = await cls.conf.rds.conn.smembers(key)
        if res:
            return [int(one) for one in res]
        return []

    @classmethod
    async def check_cool_down(cls, uid, wait_key="look_ads"):
        """
        检查用户是否需要等待冷却时间
        :param wait_key: 等待key
        :return 是否等待, 等待时间
        """
        key = f"{cls.KEY_REQ_LIMIT}:{wait_key}:{uid}"
        limit_time = await cls.conf.rds.conn.ttl(key)  # 设置键过期时间
        if limit_time > 0:
            return True, limit_time
        return False, 0

    @classmethod
    async def set_cool_down(cls, uid, wait_key="look_ads", cool_down_time=10):
        """
        设置用户的冷却时间
        :param cool_down_time: 冷却时间（秒）
        :param wait_key: 等待key
        """
        key = f"{cls.KEY_REQ_LIMIT}:{wait_key}:{uid}"
        return await cls.conf.rds.set_item(key, 1, cool_down_time)


class BaseBanRC(BaseCommonRC):
    db_model = RecordsUserBan
    tb_name = db_model.sheet_name()

    expired_mode = 1
    expired_sec = 172800  # 2 * 86400

    @classmethod
    async def check_ban_by_type(cls, uid, ban_type: BanType):
        """
        获取指定类型是否被封禁
        :param uid: 用户ID
        :param ban_type: 封禁类型枚举
        :return: 是否被封禁（True/False）
        """
        ban_records = await cls.cache_ban_records(uid)
        cur_time = tool_dt.cur_time()

        for r in ban_records:
            if r.get("ban_type") == ban_type:
                ban_time = r.get("ban_time")
                if ban_time == -1:  # 永久封禁
                    return True
                elif ban_time > 0:
                    created = r.get("created") or cur_time
                    end_time = created + ban_time
                    if cur_time < end_time:
                        return True
        return False

    @classmethod
    async def cache_ban_records(cls, uid):
        """ 缓存封禁记录 """

        async def from_db():
            try:
                db_info = await cls.db_model.get_by_dict({"uid": uid})
                if db_info:
                    await cls.conf.rds.set_item(key, json_encode(db_info), ex_time=cls.expired_sec)
                    return db_info
            except OperationalError:
                cls.log_info("cache_ban_records 暂无表")
                return []
            return []

        key = f'{cls.db_model.sheet_name()}:{uid}'
        info = await cls.conf.rds.get_item(key)
        if info:
            return json_parse(info, cls.log_err)
        return await cls.conf.rds.locked(key, fun=from_db)

    @classmethod
    async def update_user_int_field(cls, uid: int, field_name: str, value: int, operation: str = 'add'):
        try:
            user, e = await cls.update_int_field(uid, field_name, value, operation)
            if not user:
                return False, e
            # 更新缓存
            userinfo = await cls.db_model.get_or_none(uid=uid)
            await cls.update_cache(uid, userinfo)
        except OperationalError as e:
            return False, f"更新失败：{str(e)}"
        return True, "更新成功"
