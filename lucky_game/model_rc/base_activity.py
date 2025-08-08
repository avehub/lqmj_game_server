"""
泛指充值活动项目
"""
from nsanic.libs import tool_dt
from common.public.enum_const import LevelType, Switch
from common.utils.kit_dt import KitDt
from nsanic.libs.tool import json_encode, json_parse
from lucky_game.handler.douyin import DouYin
from lucky_game.model_rc.base_user import BaseUserRC
# from lucky_game.model_rc.goods_manager import GoodsManagerRC
from lucky_game.model_rc.base_rc import BaseRC
from lucky_game.model_db.main import ConfActivity, UserActivity
from lucky_game.model_rc.conf_json import ConfJsonRC
from lucky_game.const import ActivitySta, ConditionType, ActivityItem, ActivityType, RandType
from tortoise.exceptions import OperationalError


class ConfActivityRC(BaseRC):
    db_model = ConfActivity
    tb_name = db_model.sheet_name()
    expired_mode = 0
    # 救济金领取门槛 gold < 50000
    RELIEF_THRESHOLD = 50000

    @classmethod
    async def get_activity_item_by_id(cls, act_id, platform='', os=''):
        """按ID获取活动配置"""
        item = await cls.cache_conf_by_pk(act_id)
        if item:
            DouYin.adjust_payment_for_douyin(item, platform, os)
            return item
        return {}

    @classmethod
    async def get_activity_items(cls, platform='', os=''):
        """获取/缓存活动配置+打包"""
        items = await cls.cache_all_conf_item()
        if items:
            for item in items:
                DouYin.adjust_payment_for_douyin(item, platform, os)
            #             await GoodsManagerRC.pack_goods_many_conf(items)
            return items
        return []

    @classmethod
    async def get_activity_items_by_type(cls, act_type, platform='', os=''):
        """按act_type获取活动配置"""
        info = await cls.get_activity_items(platform, os)
        if not info:
            return
        return [i for i in info if i.get("act_type") == act_type]

    @classmethod
    async def get_activity_by_once(cls, act_type: int = None, act_id: int = None, status: int = 1):
        """获取单条活动信息"""
        query = {"status": status}
        try:
            if act_type:
                query["act_type"] = act_type
            if act_id:
                query["act_id"] = act_id
            info = await cls.db_model.filter(**query).first().values()
            if not info:
                return None, "暂时没找到这类型的活动哦"
        except OperationalError as e:
            return None, f"获取活动信息失败: {str(e)}"
        return info, "成功"


class UserActivityRC(BaseRC):
    db_model = UserActivity
    tb_name = db_model.sheet_name()

    expired_mode = 1
    expired_sec = 2 * 86400

    @classmethod
    async def cache_user_charge_records(cls, uid, refresh=False):
        """ 获取用户充值记录 """

        async def from_db():
            user_records = await cls.db_model.get_by_dict({"uid": uid})
            if user_records:
                await cls.conf.rds.set_item(key, json_encode(user_records), ex_time=cls.expired_sec)
                return user_records
            return []

        key = f'{cls.tb_name}:{uid}'
        if refresh:
            return await cls.conf.rds.locked(key, fun=from_db)

        user_records = await cls.conf.rds.get_item(key)
        if user_records:
            return json_parse(user_records, cls.logerr)
        return await cls.conf.rds.locked(key, fun=from_db)

    @classmethod
    async def get_user_charge_records_by_id(cls, uid, act_id):
        """ 通过act_id查询具体项 """
        datas = await cls.cache_user_charge_records(uid=uid)
        if not datas:
            return {}
        return next((i for i in datas if i.get("act_id") == act_id), {})

    @classmethod
    async def get_user_charge_records_by_type(cls, uid, act_type):
        """ 通过act_type查询具体项 """
        datas = await cls.cache_user_charge_records(uid=uid)
        if not datas:
            return []
        return [i for i in datas if i.get("act_type") == act_type]

    @classmethod
    def __check_activity_sta(cls, act_data: dict):
        """ 检查状态是否完结 """
        if act_data.get("activity_sta") != ActivitySta.ACT_INCOMPLETE:
            return {}

        is_update = False
        # 1.截止日期
        deadline = act_data.get("deadline") or 0
        if deadline and deadline <= tool_dt.cur_time():
            is_update = True
            act_data["activity_sta"] = ActivitySta.ACT_COMPLETED

        # 2.总领奖次数
        if act_data.get("act_id") == ActivityItem.FIRST_CHARGE:
            awards_achieved = json_parse(act_data.get("awards_achieved")) if act_data.get("awards_achieved") else []
            if len(awards_achieved) >= 3:
                is_update = True
                act_data["activity_sta"] = ActivitySta.ACT_COMPLETED

        return is_update

    @classmethod
    async def check_charge_data(cls, uid, activity_items):
        """ 检查用户充值数据 """
        charge_records = await cls.cache_user_charge_records(uid=uid) or []
        charge_record_map = {a_data.get('act_id'): a_data for a_data in charge_records}

        for a_conf in activity_items:
            act_id = a_conf.get('act_id')
            sale_limit = a_conf.get("sale_limit")
            if sale_limit:
                buy_record = await BaseUserRC.get_count_buy_limit(uid, act_id) or {"buy_times": 0}
                buy_times = buy_record.get("buy_times") or 0
                a_conf["buy_times"] = buy_times

                if buy_times < sale_limit.get("times") or 0:
                    rand_type = a_conf.get("rand_type") or RandType.NONE
                    if rand_type == RandType.BACK_AND_DISCOUNT:
                        # 现价>>特价 / 原价>>现价
                        discount_price = a_conf.get("discount_price") or 0
                        price = a_conf.get("price") or 0
                        if discount_price > 0:
                            a_conf["orig_price"] = price
                            a_conf["price"] = discount_price

            a_record = charge_record_map.get(act_id)
            if a_record:
                a_conf.update({
                    "deadline": a_record.get('deadline'),
                    "times": a_record.get('times'),
                    "times_day": a_record.get('times_day') if a_record.get('time_node',
                                                                           0) == KitDt.timestamp_today() else 0,
                    "activity_sta": a_record.get('activity_sta'),
                    "join_time": a_record.get('join_time'),
                    "awards_achieved": a_record.get('awards_achieved')
                })
                cls.__check_activity_sta(a_conf)
                if a_conf.get("act_type") == ActivityType.FIRST_CHARGE:
                    awards_unlocked = UserActivityRC.cal_awards_unlocked(a_conf.get("join_time"))
                    awards_achieved = a_conf.get("awards_achieved")
                    awards_achieved = json_parse(awards_achieved) if awards_achieved else []
                    first_conf = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_FIRST_CHARGE)
                    awards_sta = ConfJsonRC.stat_of_completion(len(awards_unlocked), awards_achieved,
                                                               first_conf.get("targets", []))
                    a_conf["awards_sta"] = json_encode(awards_sta)

        return activity_items

    @classmethod
    async def update_user_charge_records(cls, uid, act_item: dict, update_info: dict = None):
        """
        更新充值状态，验证订单和商品之后，领奖单独处理
        act_item: 活动配置
        update_info: 外面加工好的更新数据，一般是领奖时用
        """

        async def update_cache(info):
            await cls.conf.rds.set_item(f'{cls.tb_name}:{uid}', json_encode(info), ex_time=cls.expired_sec)

        act_id = act_item.get("act_id")
        time_limit = act_item.get("time_limit")
        condition_type = act_item.get("condition_type")
        cur_time = tool_dt.cur_time()

        charge_records = await cls.cache_user_charge_records(uid=uid) or []
        old_record = next((record for record in charge_records if record.get('act_id') == act_id), None)

        if not old_record:
            insert_data = {
                "act_id": act_id,
                "uid": uid,
                "join_time": cur_time,
                "times": 1,
                "awards_achieved": None,
                "level": act_item.get("act_level"),
                "activity_sta": ActivitySta.ACT_COMPLETED if condition_type == ConditionType.DEFAULT else ActivitySta.ACT_INCOMPLETE,
                "time_node": KitDt.timestamp_today() if condition_type == ConditionType.DEFAULT else 0,
                "deadline": KitDt.cal_deadline(day_limit=time_limit) if time_limit else 0
            }
            if act_id == ActivityItem.LIFETIME_CARD_3:
                new_records = await cls.deal_double_lifetime_card(insert_data)
                if new_records:
                    await cls.cache_user_charge_records(uid, refresh=True)
            else:
                insert_obj = await cls.db_model.add_one(insert_data)
                if insert_obj:
                    insert_data["id"] = insert_obj.id
                    charge_records.append(insert_data)
                    return await update_cache(charge_records)
        else:
            if update_info:  # 有数据优先按update_info更新
                cls.__check_activity_sta(update_info)
                old_record.update(update_info)
            else:
                times = old_record.get('times', 0)
                deadline = old_record.get('deadline', 0)
                join_limit = act_item.get('join_limit')
                # 参与次数限制
                if join_limit and times >= join_limit:
                    return
                old_record['times'] = times + 1
                # 过期则续期
                if time_limit > 0 and deadline < cur_time:
                    old_record['deadline'] = KitDt.cal_deadline(day_limit=time_limit, start_time=cur_time)

            # 更新数据库，暂时排除 'id' 字段
            o_id = old_record.pop('id')
            updated_record = await cls.db_model.update_by_pk(o_id, old_record)
            if updated_record:
                old_record['id'] = o_id
                return await update_cache(charge_records)

    @classmethod
    async def deal_double_lifetime_card(cls, new_record):
        """
        若没有任何终生卡，则可以两张一起开通
        注意卡3是不会插入的，只是辅助支付
        """
        cards = (ActivityItem.LIFETIME_CARD_1, ActivityItem.LIFETIME_CARD_2)
        bulk_records = []
        for lc in cards:
            modified_record = new_record.copy()
            if lc == ActivityItem.LIFETIME_CARD_1:
                modified_record["act_id"] = ActivityItem.LIFETIME_CARD_1
                modified_record["level"] = LevelType.LEVEL_1
            elif lc == ActivityItem.LIFETIME_CARD_2:
                modified_record["act_id"] = ActivityItem.LIFETIME_CARD_2
                modified_record["level"] = LevelType.LEVEL_2
            bulk_records.append(modified_record)

        act_instances = [cls.db_model(**act_dict) for act_dict in bulk_records]
        await cls.db_model.bulk_create(act_instances)
        return bulk_records

    @classmethod
    async def check_top_lifetime_card(cls, uid):
        """
        检查终生卡目前的等级
        default_level：大于0表示当前正在开通的卡等级，数据库可能暂时未写入
        """
        cards = (ActivityItem.LIFETIME_CARD_1, ActivityItem.LIFETIME_CARD_2)
        charge_records = []
        for aid in cards:
            info = await cls.get_user_charge_records_by_id(uid, aid)
            if info:
                charge_records.append(info)

        if not charge_records:
            level = 0
        else:
            owned_levels = {record['level'] for record in charge_records}
            has_count = len(owned_levels)

            # 检查是否同时拥有 LIFETIME_CARD_1 和 LIFETIME_CARD_2
            if has_count == 2:
                level = LevelType.LEVEL_3.val  # 用户拥有两张终生卡，视为最高级
            else:
                level = max(owned_levels)  # 返回用户拥有的最高等级

        conf_data = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_LIFETIME_CARD)
        top_conf = conf_data.get(str(level))
        if not top_conf:
            return {}
        cls.conf.info_log(f"{uid}, 玩家目前的终生卡等级为：{level}, 配置为：{top_conf}")
        return top_conf

    @classmethod
    def cal_awards_unlocked(cls, join_time):
        """计算奖励解锁状态"""
        # 计算 join_time 的当天0点时间戳
        join_time_node = KitDt.cal_midnight_timestamp(join_time)
        day_1_end = KitDt.cal_deadline(day_limit=1, start_time=join_time_node)
        day_2_end = KitDt.cal_deadline(day_limit=2, start_time=join_time_node)

        cur_time = tool_dt.cur_time()
        awards_unlocked = []
        if cur_time >= join_time_node:
            awards_unlocked.append(1)  # 第一天奖励
        if cur_time >= day_1_end:
            awards_unlocked.append(2)  # 第二天奖励
        if cur_time >= day_2_end:
            awards_unlocked.append(3)  # 第三天奖励

        return awards_unlocked

    @classmethod
    async def get_activity_unclaimed(cls, uid, act_list: tuple):
        """获取日奖待领取活动"""
        for aid in act_list:
            charge_record = await cls.get_user_charge_records_by_id(uid, aid)
            if not charge_record:
                continue
            deadline = charge_record.get('deadline')
            if deadline and deadline <= tool_dt.cur_time():
                continue
            if charge_record.get("activity_sta") != ActivitySta.ACT_INCOMPLETE:
                continue
            old_awards_achieved = charge_record.get('awards_achieved')
            awards_achieved = [] if not old_awards_achieved else json_parse(old_awards_achieved)

            today_time_node = KitDt.timestamp_today()
            if today_time_node not in awards_achieved:
                return True
            return False
        return False

    @classmethod
    async def get_first_charge_chance(cls, uid, act_id):
        """获取首充之类的机会"""
        charge_record = await cls.get_user_charge_records_by_id(uid, act_id)
        if not charge_record:
            return True
        else:
            if not charge_record.get('times', 0):
                return True
            awards_unlocked = cls.cal_awards_unlocked(charge_record.get('join_time'))
            awards_achieved = charge_record.get("awards_achieved")
            awards_achieved = json_parse(awards_achieved) if awards_achieved else []
            for aw in awards_unlocked:
                if aw not in awards_achieved:
                    return True
            return False

    @classmethod
    async def verify_activation(cls, uid, act_id, act_record=None):
        """检查限时特权是否生效"""
        if not act_record:
            act_record = await cls.get_user_charge_records_by_id(uid, act_id)

        if not act_record:
            switch = Switch.CLOSE
        else:
            switch = Switch.OPEN
            activity_sta = act_record.get("activity_sta")
            if activity_sta != ActivitySta.ACT_INCOMPLETE:
                switch = Switch.CLOSE

            deadline = act_record.get("deadline")
            if deadline and deadline < tool_dt.cur_time():
                switch = Switch.CLOSE

        return switch

    @classmethod
    async def check_hu_dong_free_privilege(cls, uid):
        """
        检查是否有免费发送互动特效的特权
        按照优先级顺序检查：终身卡 -> 周卡
        返回拥有的最高优先级特权类型，若无则返回0
        """
        act_records = await cls.cache_user_charge_records(uid=uid)
        if not act_records:
            return ActivityType.DEFAULT.val

        lifetime_cards = {ActivityItem.LIFETIME_CARD_1, ActivityItem.LIFETIME_CARD_2}
        for data in act_records:
            act_id = data.get("act_id")
            if act_id in lifetime_cards:
                switch = await cls.verify_activation(uid, act_id, act_record=data)
                if switch == Switch.OPEN:
                    return ActivityType.LIFETIME_CARD.val

        week_cards = {ActivityItem.WEEK_CARD_1.val, ActivityItem.WEEK_CARD_2.val}
        for data in act_records:
            act_id = data.get("act_id")
            if act_id in week_cards:
                switch = await cls.verify_activation(uid, act_id, act_record=data)
                if switch == Switch.OPEN:
                    return ActivityType.WEEK_CARD.val

        return ActivityType.DEFAULT.val


