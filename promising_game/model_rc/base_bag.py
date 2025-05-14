"""
玩家背包
"""
import asyncio
from nsanic.libs import tool_dt
from nsanic.orm.rc_model import RCModel
from promising_game.model_db.main import UserBag
from nsanic.libs.tool import json_encode, json_parse
from promising_game.model_rc.base_user import BaseUserRC
from promising_game.const import BagSta, GoodsItem, JumpTarget, GoodsType, BagType


class UserBagRC(RCModel):
    db_model = UserBag
    tb_name = db_model.sheet_name()

    expired_mode = 0
    expired_sec = 2 * 86400

    KEY_BAG_ID = 'bag_id'
    KEY_GOODS_ID = 'goods_id'
    KEY_GOODS_TYPE = 'goods_type'
    KEY_NEWLY = 'user_new_bag'

    HIDDEN_TYPES = (GoodsType.G_ASSET.val, GoodsType.MAGIC.val)  # 背包隐藏的物品类型

    @classmethod
    async def cache_user_bag(cls, uid, refresh=False):
        """ 获取背包所有物品 """

        async def from_db():
            user_bag = await cls.db_model.get_by_dict({"uid": uid})
            if user_bag:
                await cls.conf.rds.set_item(key, json_encode(user_bag), ex_time=cls.expired_sec)
                return user_bag
            return []

        key = f'{cls.tb_name}:{uid}'
        if refresh:
            return await cls.conf.rds.locked(key, fun=from_db)

        user_bag = await cls.conf.rds.get_item(key)
        if user_bag:
            return json_parse(user_bag, cls.logerr)

        return await cls.conf.rds.locked(key, fun=from_db)

    @classmethod
    def organize_bag_data(cls, bag_list: list):
        """按页签分类背包"""
        if not bag_list:
            return

        for bag in bag_list:
            goods_type = bag.get('goods_type')
            if goods_type == GoodsType.GAME_PROP:
                bag['bag_type'] = BagType.B_PROP
            elif goods_type == GoodsType.SKIN_SHARD:
                bag['bag_type'] = BagType.B_SKIN_SHARD

    @classmethod
    async def get_user_bag_by_type(cls, uid, goods_types: list = None):
        """通过goods_type获取背包物品"""
        items = await cls.cache_user_bag(uid=uid)
        if not items:
            return []

        bag_data = []
        for i in items:
            if i.get("goods_count") < 1:
                continue
            if goods_types and i.get(cls.KEY_GOODS_TYPE) in goods_types:
                bag_data.append(i)
            elif i.get(cls.KEY_GOODS_TYPE) not in cls.HIDDEN_TYPES:
                bag_data.append(i)

        return bag_data

    @classmethod
    async def get_user_bag_by_id(cls, uid, bag_id=None, goods_id=None):
        """ 通过bag_id / goods_id查询具体项 """
        item = await cls.cache_user_bag(uid=uid)
        if not item:
            return {}

        for i in item:
            if bag_id and i.get(cls.KEY_BAG_ID) == bag_id:
                return i
            elif goods_id and i.get(cls.KEY_GOODS_ID) == goods_id:
                return i
        return {}

    @classmethod
    async def drop_user_bag_by_id(cls, uid, bag_id):
        """
        通过bag_id删除具体项
        调用之前确保已经验证bag_id有效性
        """
        sta = await cls.db_model.update_by_pk(bag_id, {"bag_sta": BagSta.B_DELETED})
        if sta:
            return await cls.cache_user_bag(uid=uid, refresh=True)
        return

    @classmethod
    async def update_user_bag(cls, uid, express: list, is_notice=True):
        """
        更新背包数据，没有uid/goods_id/time_limit相同的数据就插入
        express: 含有更新数据列表，参考update_assets处理后的数据
        """

        async def update_cache(info):
            await cls.conf.rds.set_item(f'{cls.tb_name}:{uid}', json_encode(info), ex_time=cls.expired_sec)
            if need_notify:
                await BaseUserRC.deal_user_update_goods(uid, id_list=list(need_notify), key_name=cls.KEY_NEWLY)
            return info

        async def insert_bag(info):
            """生成插入数据"""
            goods_id = info.get('goods_id')
            add_type = info.get('add_type') or 0
            time_limit = info.get('time_limit') or 0
            insert_bag_data = {
                'uid': uid,
                'goods_id': goods_id,
                'goods_type': info.get('goods_type'),
                'goods_count': info.get('goods_count', 1),
                'exp_time': cur_time + time_limit if add_type else 0,
                'got_time': cur_time
            }
            insert_obj = await cls.db_model.add_one(insert_bag_data)
            insert_bag_data['bag_id'] = insert_obj.bag_id
            if is_notice and info.get('goods_type') not in cls.HIDDEN_TYPES:
                need_notify.add(insert_obj.bag_id)
            return insert_bag_data

        old_bag = await cls.cache_user_bag(uid=uid)
        cur_time = tool_dt.cur_time()
        need_notify = set()  # 收集需通知物品
        if not old_bag:
            new_bag = [await insert_bag(item) for item in express]
            return await update_cache(new_bag)
        else:
            new_bag = []
            update_tasks = []
            for item in express:
                founded = False  # 找到过标识
                goods_id = item.get('goods_id')
                add_type = item.get('add_type') or 0
                time_limit = item.get('time_limit') or 0
                goods_count = item.get('goods_count') or 1

                for ob in old_bag:
                    bag_id = ob.get('bag_id')
                    old_count = ob.get('goods_count') or 0
                    old_exp_time = ob.get('exp_time') or 0
                    old_bag_sta = ob.get('bag_sta') or BagSta.B_DEFAULT

                    # 背包要结合过期时间确定一行数据，先模拟计算新过期时间
                    if ob.get('goods_id') == goods_id:
                        if add_type:
                            # 1.原本有时效（判断）
                            if old_exp_time > 0:
                                # 1.1 增加有时效（计算）
                                if time_limit > 0:
                                    # 未过期，续期/过期，从现在开始计算
                                    new_exp_time = old_exp_time + time_limit if old_exp_time > cur_time else cur_time + time_limit
                                else:  # 1.2 增加永久（保持）
                                    new_exp_time = 0
                            # 2.原本永久（保持）
                            else:
                                new_exp_time = 0
                        else:
                            new_exp_time = old_exp_time

                        # 更新用模拟计算的新过期时间和goods_id来判断是否需要更新，因为uid/goods_id/exp_time联合主键
                        to_update = {}
                        if add_type and new_exp_time != old_exp_time:
                            # 更新时效
                            ob["exp_time"] = new_exp_time
                            to_update = {"exp_time": new_exp_time}
                        elif not add_type or new_exp_time == old_exp_time:
                            # 更新数量（需确认过期时间相同）
                            new_count = old_count + goods_count
                            ob["goods_count"] = max(new_count, 0)  # 确保goods_count不会小于0
                            ob["bag_sta"] = BagSta.B_DELETED.val if new_count <= 0 else BagSta.B_DEFAULT.val
                            to_update = {
                                "goods_count": ob.get('goods_count') or 1,
                                "bag_sta": ob.get('bag_sta') or 0
                            }

                        if to_update:
                            update_tasks.append(cls.db_model.update_by_pk(bag_id, to_update))
                            founded = True
                            if is_notice and ob.get('goods_type') not in cls.HIDDEN_TYPES:
                                should_notify = (
                                    (ob['goods_count'] > old_count) or  # 数量变化（增加）
                                    (old_exp_time > 0 and (new_exp_time == 0 or new_exp_time > old_exp_time)) or  # 过期时间变化（有时效变为永久 / 延长过期时间）
                                    (old_bag_sta == BagSta.B_DELETED and ob['bag_sta'] == BagSta.B_DEFAULT)  # 状态变化（已删除变化到其他）
                                )
                                if should_notify:
                                    need_notify.add(bag_id)
                        break

                if not founded:
                    res = await insert_bag(item)
                    new_bag.append(res)

            if update_tasks:
                await asyncio.gather(*update_tasks)

            all_prop = old_bag + new_bag
            return await update_cache(all_prop)

    @classmethod
    def check_bag_data(cls, user_bag: list, goods_items: list, is_ready=False, season_sta=False):
        """
        检查用户背包持有数据
        is_ready：是否准备界面使用
        season_sta：判断好的赛季状态，True表示开赛，False表示休赛期
        """
        bag_map = {b.get('goods_id'): b for b in user_bag} if user_bag else {}
        filtered_items = []

        for g in goods_items:
            goods_id = g.get('goods_id')

            if is_ready:
                jump_target = g.get('jump_target')
                # 开赛：全部道具
                if season_sta and jump_target not in (JumpTarget.GO_LEISURE_GAME.val, JumpTarget.GO_RANKING.val):
                    continue
                # 休赛：除排位道具外
                if not season_sta and jump_target != JumpTarget.GO_LEISURE_GAME.val:
                    continue

            # 合并 user_bag 中的数据到 goods_items 中
            bag_data = bag_map.get(goods_id)
            if bag_data:
                g.update(bag_data)
            filtered_items.append(g)

        return filtered_items

    @classmethod
    async def get_skin_upgrade_items(cls, uid, shard_id=None):
        """
        获得持有皮肤升星物品
        指定皮肤精魄 or 万能法相舍利
        """
        upgrade_items = {'cur_shards': 0, 'cur_relics': 0}
        user_bag = await cls.get_user_bag_by_id(uid, goods_id=GoodsItem.RELICS.val)
        if user_bag:
            upgrade_items['cur_relics'] = user_bag.get('goods_count') or 0

        if shard_id:
            user_bag = await cls.get_user_bag_by_id(uid, goods_id=shard_id)
            if user_bag:
                upgrade_items['cur_shards'] = user_bag.get('goods_count') or 0

        return upgrade_items

    @classmethod
    async def batch_deal_new_props(cls, uid, goods_list):
        """
        游戏批量消除背包里道具红点
        传进为goods_id
        缓存为bag_id
        """
        if not goods_list:
            return

        new_items = await BaseUserRC.deal_user_update_goods(uid, key_name=cls.KEY_NEWLY)  # 没缓存消什么消
        if not new_items:
            return
        new_items_set = set(new_items)

        bag_items = await cls.cache_user_bag(uid=uid)
        if not bag_items:
            return

        bag_id_set = {
            g.get("bag_id") for g in bag_items
            if g.get("goods_id") in goods_list and g.get("bag_id") in new_items_set
        }
        if bag_id_set:
            await BaseUserRC.deal_user_update_goods(uid, id_list=bag_id_set, is_del=True, key_name=cls.KEY_NEWLY)


