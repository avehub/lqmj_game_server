"""
玩家背包
"""
import asyncio
from nsanic.libs import tool_dt
from nsanic.orm.rc_model import RCModel
from lucky_game.model_db.main import UserBags
from nsanic.libs.tool import json_encode, json_parse
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.const import BagSta, GoodsItem, JumpTarget, GoodsType, BagType


class UserBagRC(RCModel):
    db_model = UserBags
    tb_name = db_model.sheet_name()

    expired_mode = 0
    expired_sec = 2 * 86400

    KEY_BAG_ID = 'id'
    KEY_GOODS_ID = 'good_id'
    KEY_GOODS_TYPE = 'good_type'
    KEY_NEWLY = 'user_new_bag'

    HIDDEN_TYPES = set()  # 背包隐藏的物品类型

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
    async def get_user_bag_by_type(cls, uid, good_types: list = None):
        """通过good_type获取背包物品"""
        items = await cls.cache_user_bag(uid=uid)
        if not items:
            return []

        bag_data = []
        for i in items:
            if i.get("count") < 1:
                continue
            if good_types and i.get(cls.KEY_GOODS_TYPE) in good_types:
                bag_data.append(i)
            elif i.get(cls.KEY_GOODS_TYPE) not in cls.HIDDEN_TYPES:
                bag_data.append(i)

        return bag_data

    @classmethod
    async def get_user_bag_by_id(cls, uid, bag_id=None, good_id=None):
        """ 通过bag_id / good_id查询具体项 """
        item = await cls.cache_user_bag(uid=uid)
        if not item:
            return {}

        for i in item:
            if bag_id and i.get(cls.KEY_BAG_ID) == bag_id:
                return i
            elif good_id and i.get(cls.KEY_GOODS_ID) == good_id:
                return i
        return {}

    @classmethod
    async def drop_user_bag_by_id(cls, uid, bag_id):
        """
        通过bag_id删除具体项
        调用之前确保已经验证bag_id有效性
        """
        sta = await cls.db_model.del_by_pk(bag_id)
        if sta:
            return await cls.cache_user_bag(uid=uid, refresh=True)
        return

    @classmethod
    async def update_user_bag(cls, uid, express: list, is_notice=True):
        """
        更新背包数据，没有uid/good_id/end_time相同的数据就插入
        express: 含有更新数据列表，参考update_assets处理后的数据
        """

        async def update_cache(info):
            await cls.conf.rds.set_item(f'{cls.tb_name}:{uid}', json_encode(info), ex_time=cls.expired_sec)
            if need_notify:
                await BaseUserRC.deal_user_update_goods(uid, id_list=list(need_notify), key_name=cls.KEY_NEWLY)
            return info

        async def insert_bag(info):
            """生成插入数据"""
            good_id = info.get('good_id')
            end_time = info.get('end_time') if info.get('end_time') else -1
            insert_bag_data = {
                'uid': uid,
                'good_id': good_id,
                'count': info.get('count', 1),
                'end_time': end_time,
                'created': cur_time
            }
            insert_obj = await cls.db_model.add_one(insert_bag_data)
            insert_bag_data['id'] = insert_obj.id
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
                good_id = item.get('good_id')
                new_exp_time = item.get('end_time') if item.get('end_time') else -1
                goods_count = item.get('count') or 1
                for ob in old_bag:
                    bag_id = ob.get('id')
                    old_count = ob.get('count') or 0
                    old_exp_time = ob.get('end_time') or 0

                    # 背包要结合过期时间确定一行数据，先模拟计算新过期时间
                    if ob.get('good_id') == good_id:
                        # 更新用模拟计算的新过期时间和good_id来判断是否需要更新
                        if new_exp_time != old_exp_time:
                            # 更新时效
                            ob["end_time"] = new_exp_time
                            # to_update["end_time"] = new_exp_time
                            to_update = {"end_time": new_exp_time}
                        else:
                            # 更新数量（需确认过期时间相同）
                            new_count = old_count + goods_count
                            ob["count"] = max(new_count, 0)  # 确保goods_count不会小于0
                            # to_update["count"] = ob.get('count') or 1,
                            to_update = {
                                "count": ob["count"],
                            }

                        if to_update:
                            update_tasks.append(cls.db_model.update_by_pk(bag_id, to_update))
                            founded = True
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
        bag_map = {b.get('good_id'): b for b in user_bag} if user_bag else {}
        filtered_items = []

        for g in goods_items:
            good_id = g.get('good_id')

            if is_ready:
                jump_target = g.get('jump_target')
                # 开赛：全部道具
                if season_sta and jump_target not in (JumpTarget.GO_LEISURE_GAME.val, JumpTarget.GO_RANKING.val):
                    continue
                # 休赛：除排位道具外
                if not season_sta and jump_target != JumpTarget.GO_LEISURE_GAME.val:
                    continue

            # 合并 user_bag 中的数据到 goods_items 中
            bag_data = bag_map.get(good_id)
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
        user_bag = await cls.get_user_bag_by_id(uid, good_id=GoodsItem.RELICS.val)
        if user_bag:
            upgrade_items['cur_relics'] = user_bag.get('count') or 0

        if shard_id:
            user_bag = await cls.get_user_bag_by_id(uid, good_id=shard_id)
            if user_bag:
                upgrade_items['cur_shards'] = user_bag.get('count') or 0

        return upgrade_items

    @classmethod
    async def batch_deal_new_props(cls, uid, goods_list):
        """
        游戏批量消除背包里道具红点
        传进为good_id
        缓存为bag_id
        """
        if not goods_list:
            return

        new_items = await BaseUserRC.deal_user_update_goods(uid, key_name=cls.KEY_NEWLY)  # 没缓存消什么消
        print("new_items", new_items)
        if not new_items:
            return
        new_items_set = set(new_items)
        bag_items = await cls.cache_user_bag(uid=uid)
        if not bag_items:
            return

        bag_id_set = {
            g.get("id") for g in bag_items
            if g.get("good_id") in goods_list and g.get("id") in new_items_set
        }

        if bag_id_set:
            await BaseUserRC.deal_user_update_goods(uid, id_list=bag_id_set, is_del=True, key_name=cls.KEY_NEWLY)


