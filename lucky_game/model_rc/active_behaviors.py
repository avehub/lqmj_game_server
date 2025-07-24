"""
用户活跃行为统计
活跃：包含用户每天和产品的互动行为
类型：统计 Stats / 记录 Records
"""
import datetime
import random
from typing import Type
from nsanic.orm.db_model import DBModel
from nsanic.libs.tool import json_encode, json_parse
from tortoise.exceptions import OperationalError
from common.utils.kit_dt import KitDt
from lucky_game.model_rc.base_interaction import InteractionRC
from lucky_game.model_rc.conf_json import ConfJsonRC
from lucky_game.config import conf_srv, ConfSrv
from lucky_game.const import AwardType, CompleteSta
# from lucky_game.model_db.main import StatsWatchAdTimes, ConfAward, RecordsUserSignIn
from lucky_game.model_db.extra import RecordsUserLuck, RecordsUserActiveScore, RecordsUserRaffle


class UserBehaviorsRC():
    expired_mode = 1
    expired_sec = 1 * 86400

    conf: ConfSrv = conf_srv

    @classmethod
    async def update_user_ad_times(cls, uid, time_node, ad_fields: str, ad_value: int):
        """
        更新用户看广告次数表
        ad_fields: 字段名, ad_value: 增加值
        """

        async def update_cache(info: dict):
            key = f"{StatsWatchAdTimes.sheet_name()}:{uid}_{time_node}"
            await cls.conf.rds.set_item(key, json_encode(info), ex_time=cls.expired_sec)

        if not ad_fields:
            return False

        new_param = {'uid': uid, 'time_node': time_node, ad_fields: ad_value}

        # 优先查询缓存
        old_data = await cls.cache_user_ad_times(uid, time_node)
        if not old_data:
            # 如果没有记录，创建新记录
            new_record = await StatsWatchAdTimes.add_one(new_param)
            new_param['id'] = new_record.id
            return await update_cache(new_param)

        # 如果有记录，更新记录
        old_value = old_data.get(ad_fields, 0)
        new_value = old_value + ad_value
        new_param[ad_fields] = new_value

        # 更新数据库
        await StatsWatchAdTimes.update_by_pk(old_data.get('id'), new_param, old_data, fun_success=update_cache)

    @classmethod
    async def cache_user_ad_times(cls, uid, time_node):
        """查询并缓存用户广告观看次数"""

        async def from_db():
            db_info = await StatsWatchAdTimes.get_by_dict({'uid': uid, 'time_node': time_node}, limit=1)
            if db_info:
                await cls.conf.rds.set_item(key, json_encode(db_info), ex_time=cls.expired_sec)
                return db_info
            return {}

        key = f"{StatsWatchAdTimes.sheet_name()}:{uid}_{time_node}"
        info = await cls.conf.rds.get_item(key)
        if info:
            return json_parse(info, cls.conf.error_log)
        return await cls.conf.rds.locked(key, fun=from_db)

    @classmethod
    async def cache_user_sign_in_records(cls, unique: dict):
        """获取/缓存用户签到记录"""

        async def from_db():
            db_info = await RecordsUserSignIn.get_by_dict(unique, limit=1)
            if db_info:
                await cls.conf.rds.set_item(key, json_encode(db_info), ex_time=cls.expired_sec)
                return db_info
            return {}

        unique_val = '_'.join([str(unique.get(k)) for k in sorted(unique)])
        key = f'{RecordsUserSignIn.sheet_name()}:{unique_val}'
        rc_info = await cls.conf.rds.get_item(key)
        if rc_info:
            return json_parse(rc_info, cls.conf.error_log)
        return await cls.conf.rds.locked(key, fun=from_db)

    @classmethod
    async def update_user_sign_in_records(cls, unique: dict, new_data: dict, old_data):
        """更新用户签到记录"""
        return await cls.update_user_records(RecordsUserSignIn, unique, new_data, old_data)

    @classmethod
    async def cache_user_luck_number(cls, uid, time_node, award_type):
        """获取/缓存运势"""

        async def query_luck():
            try:
                db_info = await RecordsUserLuck.get_by_dict({"uid": uid, "time_node": time_node}, limit=1)
                if db_info:
                    await cls.conf.rds.set_item(key, json_encode(db_info), ex_time=cls.expired_sec)
                    return db_info
                return await cache_luck()
            except OperationalError:
                cls.conf.info_log("cache_luck_number 暂无表")
            return await cache_luck()

        async def cache_luck():
            luck_num = random.randint(1, 5)
            luck_conf = await ConfAward.get_by_dict({"award_type": award_type, "award_level": luck_num}, limit=1)
            if luck_conf:
                data = {
                    "uid": uid,
                    "time_node": time_node,
                    "award_type": award_type,
                    "luck": luck_num,
                    "luck_desc": luck_conf.get("desc")
                }
                sta = await RecordsUserLuck.split_add_one(data)
                if sta:
                    await cls.conf.rds.set_item(key, json_encode(data), ex_time=cls.expired_sec)
                    return data
                return
            return

        key = f'{RecordsUserLuck.sheet_name()}:{uid}_{time_node}'
        luck_info = await cls.conf.rds.get_item(key)
        if luck_info:
            return json_parse(luck_info, cls.conf.error_log)
        return await cls.conf.rds.locked(key, fun=query_luck)

    @classmethod
    async def cache_user_active_score(cls, unique: dict):
        """ 获取/缓存用户活跃值 """

        async def from_db():
            try:
                db_info = await RecordsUserActiveScore.get_by_dict(unique, limit=1)
                if db_info:
                    await cls.conf.rds.set_item(key, json_encode(db_info), ex_time=cls.expired_sec)
                    return db_info
            except OperationalError:
                cls.conf.info_log("cache_user_active_score 暂无表")
                return {}
            return {}

        unique_val = '_'.join([str(unique.get(k)) for k in sorted(unique)])
        key = f'{RecordsUserActiveScore.sheet_name()}:{unique_val}'
        info = await cls.conf.rds.get_item(key)
        if info:
            return json_parse(info, cls.conf.error_log)
        return await cls.conf.rds.locked(key, fun=from_db)

    @classmethod
    async def stat_active_achieve_award(cls, uid, today_time_node):
        """ 获取用户活跃值 / 计算活跃达成奖励 """
        active_record = await UserBehaviorsRC.cache_user_active_score({"uid": uid, "time_node": today_time_node})

        active_score = 0
        active_achieved = []
        if active_record:
            active_score = active_record.get("active_score") or 0
            old_active_achieved = active_record.get("active_achieved")
            active_achieved = json_parse(old_active_achieved) if old_active_achieved else []

        active_conf = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_ACTIVE_SCORE)
        active_awards_sta = ConfJsonRC.stat_of_completion(active_score, active_achieved,
                                                                active_conf.get("targets", []))

        return active_awards_sta, active_score

    @classmethod
    async def update_user_active_records(cls, unique: dict, new_data: dict, old_data):
        """更新用户活跃值"""

        async def update_cache(info: dict):
            await cls.conf.rds.set_item(key, json_encode(info), ex_time=cls.expired_sec)

        unique_val = '_'.join([str(unique.get(k)) for k in sorted(unique)])
        key = f'{RecordsUserActiveScore.sheet_name()}:{unique_val}'

        if not old_data:
            await RecordsUserActiveScore.split_add_one(new_data)
            await update_cache(new_data)
            return new_data

        sta = await RecordsUserActiveScore.update_by_cond(unique, new_data)
        if sta:
            old_data.update(new_data)
            await update_cache(old_data)
            return old_data
        return

    @classmethod
    async def get_sign_in_unclaimed(cls, uid, sign_type=AwardType.SIGN_IN_RF):
        """获取是否可签到/累计签到达成"""
        sign_info = await cls.cache_user_sign_in_records({"uid": uid, "award_type": sign_type})
        sign_info = UserBehaviorsRC.reset_sign_in_records(sign_info, sign_type)
        if not sign_info:
            return True

        time_node = UserBehaviorsRC.cal_should_sign_date(sign_type)  # 应签到的日期

        # 根据签到类型设置目标键名
        key_name = {
            AwardType.SIGN_IN_RF: InteractionRC.SING_TARGET_R,
            AwardType.SIGN_IN_WK: InteractionRC.SING_TARGET_W,
        }.get(sign_type, InteractionRC.SING_TARGET_S)

        # 解析已签到日期，并根据签到类型判断是否需要检查当天是否已签到
        sign_in_date = json_parse(sign_info.get('sign_in_date', '[]'))
        if sign_type in (AwardType.SIGN_IN_RF, AwardType.SIGN_IN_WK):
            if time_node not in sign_in_date:
                return True

        old_sign_in_achieved = sign_info.get('sign_in_achieved')
        sign_in_achieved = json_parse(old_sign_in_achieved) if old_sign_in_achieved else []
        if sign_type in (AwardType.SIGN_IN, AwardType.SIGN_IN_WK) and len(sign_in_achieved) == 7:
            return False

        conf_sign = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_SING_IN)
        sign_targets = conf_sign.get(key_name) or []

        sign_awards_sta = ConfJsonRC.stat_of_completion(len(sign_in_date), sign_in_achieved, sign_targets)
        return CompleteSta.COMPLETED.val in sign_awards_sta




    @classmethod
    async def cache_user_raffle_records(cls, unique: dict):
        """获取/缓存用户抽奖记录（各类抽奖通用）"""

        async def from_db():
            try:
                db_info = await RecordsUserRaffle.get_by_dict(unique, limit=1)
                if db_info:
                    await cls.conf.rds.set_item(key, json_encode(db_info), ex_time=cls.expired_sec)
                    return db_info
            except OperationalError:
                cls.conf.info_log("cache_user_raffle_records 暂无表")
            return {}

        unique_val = '_'.join([str(unique.get(k)) for k in sorted(unique)])
        key = f'{RecordsUserRaffle.sheet_name()}:{unique_val}'
        info = await cls.conf.rds.get_item(key)
        if info:
            return json_parse(info, cls.conf.error_log)
        return await cls.conf.rds.locked(key, fun=from_db)

    @classmethod
    async def update_user_records(cls, model: Type[DBModel], unique: dict, new_data: dict, old_data, is_split=False):
        """更新用户记录（通用）"""

        async def update_cache(info: dict):
            unique_val = '_'.join([str(unique.get(k)) for k in sorted(unique)])
            key = f'{model.sheet_name()}:{unique_val}'
            await cls.conf.rds.set_item(key, json_encode(info), ex_time=cls.expired_sec)

        if not old_data:
            if is_split:
                await model.split_add_one(new_data)
            else:
                await model.add_one(new_data)

            await update_cache(new_data)
            return new_data

        sta = await model.update_by_cond(unique, new_data)
        if sta:
            old_data.update(new_data)
            await update_cache(old_data)
            return old_data
        return

    @classmethod
    def reset_sign_in_records(cls, sign_info, award_type):
        """
        判断是否需要重置签到记录，并在必要时重置
        :param sign_info: 用户签到信息
        :param award_type: 奖励类型
        :return: 更新后的签到信息
        """
        if not sign_info:
            return {}

        time_node = sign_info.get('time_node', 0)
        if not time_node:
            return sign_info

        is_reset = False
        now_time = datetime.datetime.now()
        cur_time = datetime.datetime.fromtimestamp(time_node)  # 转换为datetime对象

        # 抽奖签到逻辑：如果time_node不在当前月份，则重置
        if award_type == AwardType.SIGN_IN_RF:
            if now_time.month != cur_time.month or now_time.year != cur_time.year:
                is_reset = True

        # 每周七日签到逻辑：如果time_node不在当前周（本周一至周日），则重置
        elif award_type == AwardType.SIGN_IN_WK:
            start_of_week = now_time - datetime.timedelta(days=now_time.weekday())  # 获取本周周一的时间
            start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)

            if cur_time < start_of_week:
                is_reset = True

        # 七日签到逻辑：无需重置，每人只有一次机会
        else:
            pass

        if is_reset:
            sign_info['sign_in_date'] = None
            sign_info['sign_in_achieved'] = None
            sign_info['time_node'] = 0

        return sign_info

    @classmethod
    def cal_should_sign_date(cls, award_type):
        """根据award_type计算应签到的日期"""
        now_time = datetime.datetime.now()

        if award_type == AwardType.SIGN_IN_RF:
            # 每月签到，直接使用当月的天数
            should_sign_date = now_time.day
        elif award_type == AwardType.SIGN_IN_WK:
            # 对于每周七日签到，返回今天的星期几（周一为1，周日为7）
            should_sign_date = now_time.isoweekday()
        else:
            should_sign_date = KitDt.timestamp_today()

        return int(should_sign_date)

    @classmethod
    async def get_sign_in_records(cls, uid, award_type):
        """获取最新签到记录，并且视情况重置记录"""
        sign_records = await cls.cache_user_sign_in_records({"uid": uid, "award_type": award_type})
        sign_info = cls.reset_sign_in_records(sign_records, award_type)

        return sign_info

    @classmethod
    def parse_sign_in_info(cls, sign_info: dict):
        """
        解析签到信息

        :param sign_info: 来自 get_sign_in_records 的签到记录字典
        :return: (sign_in_date, sign_in_achieved) 元组，其中包含解析后的日期列表和累计天数列表
        """
        si_d = sign_info.get('sign_in_date')
        si_a = sign_info.get('sign_in_achieved')
        sign_in_date = json_parse(si_d) if si_d else []
        sign_in_achieved = json_parse(si_a) if si_a else []
        return sign_in_date, sign_in_achieved
