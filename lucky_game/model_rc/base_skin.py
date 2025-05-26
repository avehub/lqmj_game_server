"""
卡牌皮肤模型
"""
import asyncio
from collections import defaultdict
from nsanic.libs import tool_dt
from nsanic.libs.tool import json_encode, json_parse
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.transactions import in_transaction
from common.public.conf import R_UID_THRESHOLD
from common.utils.utils import UtilsTool
from .base_bag import UserBagRC
from .base_rc import BaseRC
from typing import Iterable
from lucky_game.model_db.main import ItemsSkin, ItemsSkinPublic, UserSkin
from .base_robot import ConfRobotRC
from .base_user import BaseUserRC
from .conf_json import ConfJsonRC
from lucky_game.const import GotType, HeldSta, GoodsType, GoodsItem
from common.public.enum_const import DbKey, ServiceEnum


class ItemsSkinRC(BaseRC):
    db_model = ItemsSkin
    db_model_public = ItemsSkinPublic

    tb_name = db_model.sheet_name()
    tb_name_public = db_model_public.sheet_name()

    pydantic = pydantic_model_creator(ItemsSkin, name="ItemsSkin")
    pydantic_public = pydantic_model_creator(ItemsSkinPublic, name="ItemsSkinPublic")

    KEY_FOREIGN_KEY = 'skin_public'
    KEY_GOODS_ID = 'goods_id'

    @classmethod
    async def get_goods_item_by_id_list(cls, id_list: Iterable):
        """ 获取多个皮肤 + 公共配置 """
        all_skin = await cls.get_skin_items()
        if not all_skin:
            return []

        skins = [s for s in all_skin if s.get(cls.KEY_GOODS_ID) in id_list]
        return skins

    @classmethod
    async def get_skin_items(cls, is_sort=True):
        """ 获取全部皮肤 + 公共配置 """
        all_skins = await cls.cache_all_conf_item_public(foreign_key=cls.KEY_FOREIGN_KEY)
        if all_skins:
            if is_sort:
                sorted_all_skins = sorted(all_skins, key=lambda x: (-x['match_card'], -x.get('skin_level', 0) or 0))
                return sorted_all_skins
            return all_skins

    @classmethod
    async def get_skin_items_by_id(cls, goods_id):
        """ 通过goods_id获取皮肤 + 公共配置 """
        return await cls.cache_conf_by_pk_public(goods_id)

    @classmethod
    async def filter_skin_items(cls, cs_type, match_card=None, public_id=None):
        """
        指定条件筛选皮肤数据
        cs_type：必传条件，每个游戏下皮肤不同，0为通用皮肤
        match_card：对应卡牌，例如孙悟空
        public_id：公共项ID，对应同款皮肤各星级
        general：大概数据
        """
        all_skin = await cls.get_skin_items()
        if not all_skin:
            return []

        filter_skin = []
        for s in all_skin:
            s_cs_type = s.get("cs_type") or 0
            # 只有默认cs_type或指定cs_type才可以
            if s_cs_type != 0 and s_cs_type != cs_type:
                continue

            if not match_card and not public_id:
                filter_skin.append(s)
            else:
                # if general and (s.get("star_level") == 0 or s.get("skin_level") == 0):  # 默认皮肤等级=0，其他皮肤星级=0
                #     filter_skin.append(s)
                if match_card and s.get("match_card") == match_card:
                    filter_skin.append(s)
                elif public_id and s.get("public_id") == public_id:
                    filter_skin.append(s)

        return filter_skin

    @classmethod
    def load_next_skin_items(cls, skin_conf):
        """
        加载下一级数据
        skin_list:同款皮肤各等级数据列表，通过筛选相同的public_id获取
        """
        # 按照 public_id 分组，每个组内按 star_level 排升序
        grouped_skin = defaultdict(list)
        result = []
        for s in skin_conf:
            grouped_skin[s.get('public_id')].append(s)

        for public_id, skins in grouped_skin.items():
            skins.sort(key=lambda x: x.get("star_level"))

            for i, cur_skin in enumerate(skins):
                if cur_skin.get('star_level') == cur_skin.get('top_star', 1):
                    next_skin = None
                else:
                    next_star_level = cur_skin.get('star_level') + 1
                    next_skin = next((m for m in skins if m.get('star_level') == next_star_level), None)

                # 构建返回结果
                cur_skin['next_star_level'] = next_skin.get('star_level') if next_skin else 0
                cur_skin['next_need_shards'] = next_skin.get('need_shards') if next_skin else 0
                cur_skin['next_extra_info'] = next_skin.get('extra_info') if next_skin else {}
                cur_skin['next_goods_id'] = next_skin.get('goods_id') if next_skin else None

                result.append(cur_skin)

        return result


class UserSkinRC(BaseRC):
    db_model = UserSkin
    tb_name = db_model.sheet_name()

    expired_mode = 1
    expired_sec = 2 * 86400

    KEY_SKIN_ID = 'skin_id'
    KEY_FK_ID = 'skin_item_id'
    KEY_PB_ID = 'skin_public_id'
    KEY_NEWLY = 'user_new_skin'
    KEY_UPGRADE = 'user_upgrade_skin'

    @classmethod
    async def get_user_used_skin(cls, uid, cs_type):
        """
        皮肤使用项查询（不同游戏使用状态独立），没有给默认ID
        """
        items_list = await cls.cache_user_skin(uid=uid)
        if not items_list:
            gift_conf = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_NEW_USER_GIFT)
            if gift_conf:
                return gift_conf.get("card_skin")

        used_list = []
        for item in items_list:
            if item.get("cs_type") == cs_type and item.get("got_type") == GotType.USED:
                used_list.append(item.get("skin_item_id"))
        return used_list

    @classmethod
    async def get_batch_user_used_skin(cls, uid_list, cs_type, leisure_id):
        """批量皮肤使用项查询（子游戏使用）"""
        if not uid_list:
            return {}

        # 1. 检查是否有机器人并获取机器人配置
        have_robot = any(uid <= R_UID_THRESHOLD for uid in uid_list)
        robot_conf = await ConfRobotRC.get_robot_conf_by_id(leisure_id) if have_robot else {}

        # 2.使用的皮肤获取
        used_skins = {}
        for uid in uid_list:
            if uid > R_UID_THRESHOLD:
                used_skins[uid] = await UserSkinRC.get_user_used_skin(uid, cs_type)
            elif robot_conf:
                skin_count = robot_conf.get("skin_count")
                count = int(UtilsTool.select_element_by_prob(skin_count, size=100))
                config = robot_conf.get("card_skin", {})
                used_item = set()
                used_skins[uid] = []
                while len(used_skins[uid]) < count:
                    res = UtilsTool.select_element_by_prob(config, size=410)
                    if res and res not in used_item:
                        used_item.add(res)
                        used_skins[uid].append(int(res))

        # 3.收集所有皮肤 ID 并去重
        skin_id_set = {skin_id for skins in used_skins.values() for skin_id in skins}

        skin_conf = {}
        if skin_id_set:
            skin_items = await ItemsSkinRC.get_goods_item_by_id_list(skin_id_set)
            for sc in skin_items:
                skin_info = {
                    "skin_item_id": sc.get("goods_id"),
                    "skin_addition": (sc.get("extra_info") or {}).get("addition", 0),  # todo:金币加成暂时未使用
                    "sr_addition": (sc.get("extra_info") or {}).get("ranking_addition", 0),  # 修为加成
                    "match_card": sc.get("match_card")
                }
                skin_conf[sc.get("goods_id")] = skin_info

        # 4.构建最终的结果字典
        result_dict = {}
        for uid, used_list in used_skins.items():
            if used_list:
                result_dict[uid] = [
                    skin_conf[s_id] for s_id in used_list if s_id in skin_conf
                ]

        return result_dict

    @classmethod
    async def get_user_skin_by_game(cls, uid, cs_type=None):
        """按游戏类型cs_type获取玩家皮肤数据"""
        items_list = await cls.cache_user_skin(uid=uid)
        if not items_list:
            return []

        if cs_type is None or cs_type == 0:
            return items_list

        type_list = []
        for item in items_list:
            if item.get("cs_type") == cs_type:
                type_list.append(item)
        return type_list

    @classmethod
    async def get_user_skin(cls, uid):
        """获取玩家的所有皮肤"""
        items_list = await cls.cache_user_skin(uid=uid)
        if items_list:
            return items_list
        return []

    @classmethod
    async def get_user_skin_by_id(cls, uid, cs_type, skin_item_id=None, skin_public_id=None):
        """ 通过goods_id查询具体项 """
        items = await cls.get_user_skin_by_game(uid, cs_type)
        if not items:
            return {}

        for i in items:
            if skin_item_id and i.get(cls.KEY_FK_ID) == skin_item_id:
                return i
            elif skin_public_id and i.get(cls.KEY_PB_ID) == skin_public_id:
                return i
        return {}

    @classmethod
    async def cache_user_skin(cls, uid, refresh=False):
        """获取用户已获得皮肤"""

        async def from_db():
            user_skin = await cls.db_model.get_by_dict({"uid": uid})
            if not user_skin:
                cls.loginfo(f"{uid}, 暂无皮肤数据，准备初始化")
                user_skin = await cls.__init_skin_data(uid)

            if user_skin:
                await cls.conf.rds.set_item(key, json_encode(user_skin), ex_time=cls.expired_sec)
                return user_skin
            return []

        key = f'{cls.tb_name}:{uid}'
        if refresh:
            return await cls.conf.rds.locked(key, fun=from_db)

        user_skin = await cls.conf.rds.get_item(key)
        if user_skin:
            return json_parse(user_skin, cls.logerr)
        return await cls.conf.rds.locked(key, fun=from_db)

    @classmethod
    async def check_skin_detail_data(cls, skin_conf, user_skin, is_more=False):
        """检查用户皮肤数据 / 加载详细数据"""
        if not user_skin:
            return [], []

        skin_map = {s.get('skin_item_id'): s for s in user_skin}  # 构建用户持有的皮肤映射

        if is_more:  # 二级加载下一级数据
            skin_conf = ItemsSkinRC.load_next_skin_items(skin_conf)
        # 按 public_id 分组
        grouped_skin = defaultdict(list)
        for s in skin_conf:
            grouped_skin[s.get('public_id')].append(s)

        result = []
        for public_id, skins in grouped_skin.items():
            owned_skin = None
            for s in skins:
                if s['goods_id'] in skin_map:
                    owned_skin = s
                    break

            if owned_skin:  # 用户持有皮肤，找到对应的皮肤数据
                cur_skin = owned_skin.copy()
                cur_skin.update(skin_map[owned_skin['goods_id']])
            else:  # 未持有皮肤，则返回当前 public_id 下的最低星级皮肤数据
                cur_skin = min(skins, key=lambda x: x.get('star_level')).copy()

            result.append(cur_skin)

        return result

    @classmethod
    async def __init_skin_data(cls, uid):
        """初始化默认皮肤"""
        gift_conf = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_NEW_USER_GIFT)
        if not gift_conf:
            return []

        all_skin = await ItemsSkinRC.get_skin_items()
        if not all_skin:
            return []

        skin_ids = gift_conf.get("card_skin")
        filtered_skin_conf = [item for item in all_skin if item.get('goods_id') in skin_ids]

        insert_data = {
            'uid': uid,
            'got_type': GotType.USED,
            'got_time': tool_dt.cur_time(),
            'exp_time': 0
        }
        id_set = set()
        add_tasks = []
        for item in filtered_skin_conf:
            insert_data["skin_item_id"] = item.get('goods_id')
            insert_data["skin_public_id"] = item.get('public_id')

            id_set_part, add_tasks_part = cls.__creat_add_tasks(item.get('cs_type'), insert_data)
            id_set.update(id_set_part)
            add_tasks.extend(add_tasks_part)

        await cls.db_model.bulk_create([cls.db_model(**data) for data in add_tasks])
        return add_tasks

    @classmethod
    async def deal_expire_skin(cls, uid, cs_type):
        """处理失效法相"""
        user_skin = await UserSkinRC.get_user_skin_by_game(uid, cs_type)
        if not user_skin:
            return
        cur_time = tool_dt.cur_time()

        limited_ids = [s.get('skin_item_id') for s in user_skin if s.get('got_type') != GotType.NOT_GOT.val
                       and s.get('exp_time') and s.get('exp_time') < cur_time]
        if not limited_ids:
            return

        skin_conf = await ItemsSkinRC.get_goods_item_by_id_list(limited_ids) or []
        if not skin_conf:
            return

        to_update_unused = set()
        to_update_use = set()

        for c in skin_conf:
            extra_info = c.get('extra_info')
            match_card = c.get('match_card')
            if not extra_info or not match_card:
                continue

            default = extra_info.get('default')
            if default:
                to_update_unused.add(match_card)
                to_update_use.add(default)

        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                # 将所有永久且正在使用的物品设置为备用状态
                if to_update_unused:
                    await cls.db_model.filter(
                        uid=uid,
                        skin_item__skin_public__match_card__in=list(to_update_unused),
                        exp_time=0,
                        got_type=GotType.USED
                    ).update(got_type=GotType.UNUSED)

                    await cls.db_model.filter(
                        uid=uid,
                        skin_item__skin_public__match_card__in=list(to_update_unused),
                        exp_time__gt=0,
                        got_type__not_in=[GotType.NOT_GOT]
                    ).update(got_type=GotType.NOT_GOT)

                # 将默认法相设置为使用状态
                if to_update_use:
                    await cls.db_model.filter(
                        uid=uid,
                        skin_item__goods_id__in=list(to_update_use)
                    ).update(got_type=GotType.USED)

                    await cls.cache_user_skin(uid, refresh=True)

        except Exception as e:
            cls.loginfo(f"deal_expire_skin 事务执行失败，原因：{e}")
            return False
        return True

    @classmethod
    async def set_user_skin(cls, uid, goods_id, match_card):
        """同角色皮肤装备，同时把其他正在使用的状态修改备用"""
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                # 将所有相同 match_card角色 和 cs_type游戏 且为使用状态的物品设置为备用状态
                await cls.db_model.filter(
                    uid=uid,
                    skin_item__skin_public__match_card=match_card,
                    got_type=GotType.USED
                ).update(got_type=GotType.UNUSED)

                # 将指定的装扮设置为使用状态
                await cls.db_model.filter(
                    uid=uid,
                    skin_item__goods_id=goods_id
                ).update(got_type=GotType.USED)

                await cls.cache_user_skin(uid, refresh=True)
        except Exception as e:
            cls.loginfo(f"set_user_skin 事务执行失败，原因：{e}")
            return False
        return True

    @classmethod
    async def deal_upgradable_skin(cls, uid, cs_type=ServiceEnum.C_MONSTER, id_list=None, is_del=False):
        """处理可升级皮肤"""
        key = f"{cls.KEY_UPGRADE}:{uid}"
        res = await cls.conf.rds.conn.smembers(key)

        # 1.id_list=None则直接查询
        if id_list is None:
            if res:
                res_lst = [int(one) for one in res]
                return res_lst

            id_list = await cls.check_upgradable_skin(uid, cs_type)
            if id_list:
                await cls.conf.rds.conn.sadd(key, *id_list)
                return id_list
            return False
        # 2.当客户端反馈已升级时，移除缓存中的皮肤id
        if is_del and res:
            if id_list:
                await cls.conf.rds.conn.srem(key, *id_list)
            else:
                await cls.conf.rds.conn.delete(key)
            return True

    @classmethod
    async def check_upgradable_skin(cls, uid, cs_type=ServiceEnum.C_MONSTER):
        """检查可升级皮肤"""
        user_skin = await cls.get_user_skin_by_game(uid, cs_type)
        if not user_skin:
            return []
        filter_skin = await ItemsSkinRC.filter_skin_items(cs_type)
        if not filter_skin:
            return []
        filter_skin = ItemsSkinRC.load_next_skin_items(filter_skin)
        user_map = {s.get('skin_item_id'): s for s in user_skin} if user_skin else {}

        up_list = []
        for skin in filter_skin:
            goods_id = skin.get('goods_id')
            cur_u_skin = user_map.get(goods_id)
            if not cur_u_skin:
                continue
            if cur_u_skin.get('got_type') == GotType.NOT_GOT:
                continue
            if cur_u_skin.get('exp_time', 0) > 0:
                continue
            # 如果 shard_id 为 null 或者已经是最高星级，则跳过
            shard_id = skin.get("shard_id")
            if not shard_id or skin.get("top_star", 1) == skin.get("star_level"):
                continue

            # 获取用户当前拥有的精魄数量
            upgrade_items = await UserBagRC.get_skin_upgrade_items(uid, shard_id=shard_id)
            cur_shards = upgrade_items.get("cur_shards") or 0
            next_need_shards = skin.get("next_need_shards") or 0

            # 如果用户有足够的精魄来升级该皮肤
            if cur_shards >= next_need_shards:
                up_list.append(goods_id)

        return up_list

    @classmethod
    def __creat_add_tasks(cls, cs_type, insert_data):
        """处理多个类型游戏同时解锁皮肤"""
        id_set = set()
        add_tasks = []
        if not cs_type:
            # 通用需添加上篇皮肤
            insert_data['cs_type'] = ServiceEnum.C_MONSTER
            add_tasks.append(insert_data.copy())
            # 通用需添加下篇皮肤
            insert_data['cs_type'] = ServiceEnum.C_MONSTER_SEQUEL
            add_tasks.append(insert_data.copy())

            id_set.add(insert_data.get('skin_item_id'))
        else:
            # 不是通用皮肤，直接按原cs_type添加
            insert_data['cs_type'] = cs_type
            add_tasks.append(insert_data.copy())
            id_set.add(insert_data.get('skin_item_id'))

        return id_set, add_tasks

    @classmethod
    async def update_user_skin(cls, uid, express, is_upgrade=False, user_skin=None, is_notice=True):
        """
        更新皮肤数据
        express: 注意皮肤的数据需要准备skin_item_id
        is_upgrade: 是否升级情况，上下篇共用星级
        """

        async def update_cache(info):
            await cls.conf.rds.set_item(f'{cls.tb_name}:{uid}', json_encode(info), ex_time=cls.expired_sec)
            return info

        async def insert_skin(info):
            cur_time = tool_dt.cur_time()
            add_type = info.get('add_type') or 0
            time_limit = info.get('time_limit') or 0
            if info.get('star_level') == 0:
                return
            insert_skin_data = {
                'uid': uid,
                'got_type': GotType.UNUSED,
                'exp_time': cur_time + time_limit if add_type and time_limit > 0 else 0,
                'got_time': cur_time,
                'skin_item_id': info.get('goods_id'),
                'skin_public_id': info.get('public_id')
            }
            id_set, add_tasks = cls.__creat_add_tasks(info.get('cs_type'), insert_skin_data)
            await cls.db_model.bulk_create([cls.db_model(**data) for data in add_tasks])
            if is_notice and insert_skin_data.get('exp_time') == 0:
                await BaseUserRC.deal_user_update_goods(uid, id_list=id_set, key_name=cls.KEY_NEWLY)
            await cls.cache_user_skin(uid, refresh=True)
            return add_tasks

        async def deal_upgrade(old_skin: list, express: dict):
            upgrade_tasks = []
            goods_id = express.get('goods_id')
            next_goods_id = express.get('next_goods_id')
            for os in old_skin:
                if os.get('skin_item_id') == goods_id:
                    os["skin_item_id"] = next_goods_id
                    task = cls.db_model.update_by_pk(os.get('skin_id'), {"skin_item_id": next_goods_id})
                    upgrade_tasks.append(task)
            if upgrade_tasks:
                await asyncio.gather(*upgrade_tasks)
            return old_skin

        async def deal_express(old_skin: list, express: list):
            new_skin = []
            update_tasks = []
            need_notify = set()  # 收集需通知物品
            skin_map = {s.get('skin_public_id'): s for s in old_skin} if old_skin else {}

            for item in express:
                u_skin = skin_map.get(item.get('public_id'))
                if u_skin:
                    exp_time = u_skin.get('exp_time') or 0
                    if exp_time == 0:  # 有永久的兑换精魄
                        pass
                    else:  # 否则把有效期延长
                        for os in old_skin:
                            goods_id = item.get('goods_id')
                            if os.get('skin_item_id') == goods_id:
                                time_limit = item.get('time_limit', 0)
                                old_got_type = os.get('got_type') or GotType.NOT_GOT.val
                                if time_limit == 0:
                                    new_exp_time = 0
                                else:
                                    new_exp_time = exp_time + time_limit

                                to_update = {}
                                if exp_time != new_exp_time:
                                    os['exp_time'] = new_exp_time
                                    to_update['exp_time'] = new_exp_time
                                if os.get('got_type') == GotType.NOT_GOT:
                                    os['got_type'] = GotType.UNUSED
                                    to_update['got_type'] = GotType.UNUSED.val

                                if to_update:
                                    update_tasks.append(cls.db_model.update_by_pk(os.get('skin_id'), to_update))
                                    if is_notice and old_got_type == GotType.NOT_GOT and os[
                                        'got_type'] != GotType.NOT_GOT:
                                        need_notify.add(goods_id)
                else:
                    res = await insert_skin(item)
                    new_skin.extend(res)

            all_skin = old_skin + new_skin
            if update_tasks:
                await asyncio.gather(*update_tasks)

            if need_notify:
                await BaseUserRC.deal_user_update_goods(uid, id_list=list(need_notify), key_name=cls.KEY_NEWLY)
            return all_skin

        # 获取用户的皮肤数据
        old_skin = user_skin if user_skin else await cls.cache_user_skin(uid=uid) or []
        # 处理升级
        if is_upgrade:
            updated_skin = await deal_upgrade(old_skin, express)
            return await update_cache(updated_skin)
        # 处理发货
        all_skin = await deal_express(old_skin, express)
        await update_cache(all_skin)
        return all_skin

    @classmethod
    def check_skin_hold_status(cls, user_skin: dict, this_skins: list, user_shard: dict):
        """检查单个皮肤的购买限制"""
        if not user_skin:
            return HeldSta.NOT_HELD, "未持有该法相，直接获得法相即可"

        # 查询皮肤配置
        skin_conf = next((s for s in this_skins if s.get('goods_id') == user_skin.get('skin_item_id')), None)
        if not skin_conf:
            return None, "法相配置不存在"

        cur_star = skin_conf.get('star_level')
        top_star = skin_conf.get('top_star')
        exp_time = user_skin.get('exp_time')

        if exp_time > 0:
            return HeldSta.LIMITED_HELD, "持有限时法相，可以升级为永久法相"

        if cur_star >= top_star:
            return HeldSta.MAX_LEVEL, "当前法相您已经满级，不需要再购买了"

        if user_shard:
            total_need_shards = sum(skin.get('need_shards') for skin in this_skins if skin.get('star_level') > cur_star)
            if user_shard.get('goods_count', 0) >= total_need_shards:
                return HeldSta.CAN_MAX_LEVEL, "您所持有的精魄足够升到满级法相，不需要再购买了"

        return HeldSta.HELD, "持有该法相但允许购买，兑换成等量精魄"

    @classmethod
    async def deal_skin_convert(cls, uid, skin_conf):
        """处理皮肤兑换其他物品"""
        cs_type = skin_conf.get("cs_type")
        user_skin = await cls.get_user_skin_by_id(uid, cs_type, skin_public_id=skin_conf.get("public_id"))
        convert_goods = {
            "goods_id": skin_conf.get("goods_id"),
            "goods_type": GoodsType.CARD_SKIN.val,
            "goods_count": 1
        }
        if not user_skin:
            return HeldSta.NOT_HELD, convert_goods

        this_skins = await ItemsSkinRC.filter_skin_items(cs_type, public_id=skin_conf.get("public_id"))  # 此款法相各星级配置
        user_shard = await UserBagRC.get_user_bag_by_id(uid, goods_id=skin_conf.get("shard_id"))  # 用户碎片数据

        held_sta, desc = UserSkinRC.check_skin_hold_status(user_skin, this_skins, user_shard)
        cls.loginfo(uid, f'检查皮肤结果{held_sta} 描述{desc}')
        if held_sta == HeldSta.HELD:
            shard_id = skin_conf.get("shard_id")
            if shard_id:
                shard_data = {
                    "goods_id": shard_id,
                    "goods_type": GoodsType.SKIN_SHARD.val,
                    "goods_count": 1
                }
                return held_sta, shard_data
            return held_sta, None

        if held_sta in (HeldSta.CAN_MAX_LEVEL, HeldSta.MAX_LEVEL):
            extra_info = skin_conf.get("extra_info")
            if extra_info and extra_info.get("convert_five"):
                event_data = {
                    "goods_id": GoodsItem.FIVE_AGGREGATES.val,
                    "goods_type": GoodsType.MAGIC.val,
                    "goods_count": extra_info.get("convert_five")
                }
                return held_sta, event_data
            return held_sta, None

        if held_sta == HeldSta.LIMITED_HELD:
            return held_sta, convert_goods

        return held_sta, None

    @classmethod
    async def deal_hold_skin(cls, uid, award_item: dict):
        """处理持有的皮肤"""
        if award_item.get("goods_type") == GoodsType.CARD_SKIN.val:
            skin_conf = await ItemsSkinRC.get_skin_items_by_id(award_item.get("goods_id"))
            if skin_conf:
                held_sta, convert_goods = await cls.deal_skin_convert(uid, skin_conf)
                if convert_goods:
                    award_item.update(convert_goods)
