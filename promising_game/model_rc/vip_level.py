"""
充值VIP模型
"""
from nsanic.libs.tool import json_encode, json_parse
from nsanic.orm.rc_model import RCModel
from common.public.enum_const import LevelType
from common.utils.kit_dt import KitDt
from promising_game.const import CompleteSta
from promising_game.model_rc.goods_manager import GoodsManagerRC
from promising_game.model_rc.base_rc import BaseRC
from promising_game.model_db.main import ConfVip, UserVip
from promising_game.model_rc.conf_json import ConfJsonRC


class ConfVipRC(BaseRC):
    """ vip配置模型 """
    db_model = ConfVip
    tb_name = db_model.sheet_name()

    @classmethod
    async def get_all_vip_items(cls, is_all=False):
        """缓存所有vip配置+打包"""
        vip_conf = await cls.cache_all_conf_item(has_status=False, orders="level")
        if vip_conf:
            for vc in vip_conf:
                vc["increase_space"] = int(vc.get("increase_space", 0))
            await GoodsManagerRC.pack_goods_many_conf(vip_conf, is_all=is_all)
            return vip_conf


class UserVipRC(RCModel):
    """ 用户vip模型 """
    db_model = UserVip
    tb_name = db_model.sheet_name()

    expired_mode = 1
    expired_sec = 172800  # 2 * 86400

    @classmethod
    async def cache_by_pk(cls, uid, **kwargs):
        """查询玩家vip，没有的活跃玩家给默认值"""
        info = await super().cache_by_pk(uid)
        if info:
            info["recharge_amount"] = float(info.get("recharge_amount", 0))
        else:
            info = {
                "uid": uid,
                "cur_exp": 0,
                "recharge_amount": 0,
                "vip_id": 1,
                "time_node": 0,
                # 是否默认值判断（仅此处有）
                "default_cache": 1
            }
            await cls.conf.rds.set_item(f"{cls.tb_name}:{uid}", json_encode(info), ex_time=cls.expired_sec)
        return info

    @classmethod
    async def get_vip_conf_by_uid(cls, uid):
        """获取对应vip等级配置"""
        u_vip_info = await cls.cache_by_pk(uid)
        return await ConfVipRC.cache_conf_by_pk(u_vip_info.get("vip_id"), has_status=False, orders="level")

    @classmethod
    async def update_user_vip(cls, uid, update_info: dict, old_info: dict):
        """更新vip一般记录"""
        async def update_cache(db_info):
            await cls.conf.rds.set_item(f"{cls.tb_name}:{uid}", json_encode(db_info), ex_time=cls.expired_sec)

        return await cls.db_model.update_by_pk(uid, update_info, old_info, fun_success=update_cache)

    @classmethod
    async def update_user_vip_level(cls, uid, amount: int = 0, add_exp=0):
        """更新vip等级记录"""
        async def update_cache(db_info):
            await cls.conf.rds.set_item(f"{cls.tb_name}:{uid}", json_encode(db_info), ex_time=cls.expired_sec)

        vip_info = await cls.cache_by_pk(uid) or {}
        conf_data = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_VIP)
        vip_conf_list = await ConfVipRC.cache_all_conf_item(has_status=False, orders="level")

        add_exp = amount * conf_data.get("exp_rate", 10) or add_exp
        vip_id = vip_info.get("vip_id") or 1

        # 未加经验等级
        cur_level = 0
        for vip_conf in vip_conf_list or []:
            if vip_conf.get("id") == vip_id:
                cur_level = vip_conf.get("level")
                break

        # 已加经验等级
        cur_exp = vip_info.get("cur_exp") or 0
        cur_exp += add_exp
        cur_amount = vip_info.get("recharge_amount") or 0  # 当前充值金额
        cur_amount += amount

        top_reached = False  # 满级达成标识
        new_level = cur_level
        if cur_level != LevelType.LEVEL_10.val:
            for vip_conf in vip_conf_list or []:
                if vip_conf.get("level") == LevelType.LEVEL_10.val:  # 检查是否为最高等级
                    top_reached = True
                    new_level = vip_conf.get("level")
                    vip_id = vip_conf.get("id")
                    break
                elif not top_reached and vip_conf.get("need_exp", 0) > cur_exp:
                    break
                new_level = vip_conf.get("level")
                vip_id = vip_conf.get("id")

        data = {
            "uid": uid,
            "vip_id": vip_id,
            "cur_exp": add_exp,
            "recharge_amount": amount
        }
        if not vip_info or vip_info.get("default_cache"):
            for vip_conf in vip_conf_list or []:
                if vip_conf.get("need_exp", 0) > add_exp:
                    break
                data["vip_id"] = vip_conf.get("id")
            sta = await cls.db_model.add_one(data)
            if sta:
                await update_cache(data)
        else:
            data["vip_id"] = vip_id
            data["cur_exp"] = cur_exp
            data["recharge_amount"] = cur_amount
            sta = await cls.db_model.update_by_pk(uid, data, vip_info, fun_success=update_cache)
            sta = sta if isinstance(sta, bool) else True

        if not sta:
            return False, False

        cls.conf.info_log(uid, "玩家VIP经验更新：", cur_level, "==>>", new_level, "是否升到满级：", top_reached)
        return True, True if cur_level < new_level else False

    @classmethod
    async def get_vip_unclaimed(cls, uid):
        u_vip_info = await cls.cache_by_pk(uid)
        vip_id = u_vip_info.get("vip_id")
        if vip_id == 1 or u_vip_info.get("default_cache"):
            return False
        c_vip_data = await ConfVipRC.cache_conf_by_pk(u_vip_info.get("vip_id"), has_status=False, orders="level")
        if not c_vip_data:
            return False
        # 等级奖
        old_level_achieved = u_vip_info.get("level_achieved") or ""
        level_achieved = [] if not old_level_achieved else json_parse(old_level_achieved)

        conf_vip = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_VIP)
        vip_targets = conf_vip.get("targets") or []
        level_awards_sta = ConfJsonRC.stat_of_completion(c_vip_data.get("level"), level_achieved, vip_targets)
        if CompleteSta.COMPLETED.val in level_awards_sta:
            return True
        # 每日奖
        today_time_node = KitDt.timestamp_today()
        pull_time_node = u_vip_info.get("time_node", 0)

        old_daily_achieved = [] if pull_time_node != today_time_node else u_vip_info.get("daily_achieved")
        daily_achieved = [] if not old_daily_achieved else json_parse(old_daily_achieved)


        daily_awards_sta = ConfJsonRC.stat_of_completion(c_vip_data.get("level"), daily_achieved, vip_targets)
        if CompleteSta.COMPLETED.val in daily_awards_sta:
            return True
        return False

