"""
用户互动相关
例如 分享 / 看广告 / 抽奖 / 运势
类型：配置 conf / 使用 use
"""
import random
from nsanic.orm.rc_model import RCModel
from common.utils.kit_dt import KitDt
from common.utils.utils import UtilsTool
from promising_game.model_rc.base_activity import UserActivityRC
from promising_game.model_rc.base_award import ConfAwardRC
from promising_game.model_rc.goods_manager import GoodsManagerRC
from nsanic.libs.tool import json_encode, json_parse
from promising_game.model_rc.base_user import BaseUserRC
from promising_game.model_rc.conf_json import ConfJsonRC
from promising_game.model_rc.vip_level import UserVipRC


class InteractionRC(RCModel):
    expired_mode = 1
    expired_sec = 2 * 86400

    """配置缓存名"""
    CONF_RAFFLE_LUCK = 'conf_raffle_luck'  # 运势抽奖
    CONF_RAFFLE_SIGN_IN = 'conf_raffle_sign_in'  # 累计抽奖签到
    CONF_SEVEN_SIGN_IN = 'conf_seven_sign_in'  # 七日登陆签到
    CONF_WEEK_SIGN_IN = 'conf_week_sign_in'  # 每周七日签到
    CONF_ACTIVE_DAILY = 'conf_daily_active'  # 日活
    SING_TARGET_S = 'seven_sign_targets'  # 七日签到累计目标
    SING_TARGET_R = 'raffle_sign_targets'  # 抽奖签到累计目标
    SING_TARGET_W = 'week_sign_targets'  # 每周七日签到累计目标

    @classmethod
    async def load_raffle_luck_conf(cls, raffle_awards):
        """ 打包运势抽奖数据（不能传空值） """
        awards_list = []
        for a_item in raffle_awards or []:
            conf_items = a_item.get("conf_items")
            if conf_items:
                awards_conf = random.choice(conf_items)
                awards_conf["award_level"] = a_item.get("award_level")
                awards_list.append(awards_conf)

        await GoodsManagerRC.pack_goods_list(awards_list)
        data = []
        for ac in awards_list:
            data.append({
                "award_level": ac["award_level"],
                "conf_items": [ac],
            })
        cache_data = {"data": data, "time_node": KitDt.timestamp_today()}
        await cls.conf.rds.set_item(cls.CONF_RAFFLE_LUCK, json_encode(cache_data))
        return data

    @classmethod
    async def get_conf_raffle_luck(cls, raffle_awards, time_node: int):
        """运势抽奖配置（每日刷新奖品）"""
        sign_conf = await cls.conf.rds.get_item(cls.CONF_RAFFLE_LUCK)
        if sign_conf:
            sign_data = json_parse(sign_conf, cls.logerr)
            if sign_data.get("time_node", KitDt.timestamp_today()) == time_node:
                return json_parse(sign_data.get("data"), cls.logerr)
        return await cls.load_raffle_luck_conf(raffle_awards)

    @classmethod
    async def get_conf_sign_in(cls, sign_awards, key_name=CONF_RAFFLE_SIGN_IN):
        """累计签到配置"""
        awards = await cls.conf.rds.get_item(key_name)
        if awards:
            return json_parse(awards, cls.logerr)
        return await ConfAwardRC.load_award_conf(key_name, sign_awards)

    @classmethod
    async def get_conf_daily_active(cls, active_items):
        """活跃值奖励配置"""
        key_name = cls.CONF_ACTIVE_DAILY
        awards = await cls.conf.rds.get_item(key_name)
        if awards:
            return json_parse(awards, cls.logerr)
        return await ConfAwardRC.load_award_conf(key_name, active_items)

    @classmethod
    async def get_relief_chance(cls, uid) -> bool:
        """获取救济机会"""
        u_info = await BaseUserRC.cache_by_uid(uid)
        conf_relief_data = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_RELIEF)
        if u_info.get("gold") >= conf_relief_data.get("limit_count", 0):
            return False
        u_relief_info = await BaseUserRC.get_relief_count(uid)
        if not u_relief_info:
            return True
        today_time_node = KitDt.timestamp_today()
        used_times = u_relief_info.get("used_times", 0) if u_relief_info.get("time_node") == today_time_node else 0

        conf_relief_data = await cls.stat_relief_with_additions(uid, conf_relief_data) or {}
        relief_times = conf_relief_data.get("times") or 2
        return used_times < relief_times

    @classmethod
    async def stat_relief_with_additions(cls, uid, conf_relief: dict = None, is_free=False):
        """
        计算总救济次数/额度
        在原救济基础上判断是否有其它特权加成
        """
        if not conf_relief:
            conf_relief = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_RELIEF)
        # 终生卡次数加成
        conf_lifetime = await UserActivityRC.check_top_lifetime_card(uid)
        if conf_lifetime:
            conf_relief['times'] += conf_lifetime.get("relief_add_times", 0)

        # vip次数加成
        conf_vip = await UserVipRC.get_vip_conf_by_uid(uid)
        conf_relief['times'] += conf_vip.get("relief_add_times", 0)

        # vip额度加成
        multiple = conf_relief.get("multiple", 1) * (conf_vip.get("relief_addition", 1))

        # 广告随机额度加成
        if is_free:
            ad_odds = conf_relief.get("ad_odds", {})
            ad_addition = UtilsTool.select_element_by_prob(ad_odds, size=100)
            multiple *= int(ad_addition)

        conf_relief['multiple'] = int(multiple)
        conf_relief['count'] = int(conf_relief.get("count", 0) * multiple)
        return conf_relief
