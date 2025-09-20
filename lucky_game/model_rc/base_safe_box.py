"""
保险箱相关
"""
from nsanic.libs import tool_dt
from nsanic.libs.tool import json_encode
from nsanic.orm.rc_model import RCModel
from tortoise.transactions import in_transaction
from common.public.enum_const import DbKey, Switch
from lucky_game.const import ReasonCostGold
from lucky_game.model_db.main import UserSafeBox
from lucky_game.model_rc.base_user import BaseUserRC


class UserSafeBoxRC(RCModel):
    db_model = UserSafeBox
    tb_name = db_model.sheet_name()

    expired_mode = 1
    expired_sec = 7 * 86400

    @classmethod
    async def cache_by_pk(cls, uid, **kwargs):
        """查询玩家vip，没有的活跃玩家给默认值"""
        info = await super().cache_by_pk(uid)
        if info:
            info["space"] = int(info.get("space", 0))
            info["amount"] = int(info.get("amount", 0))
            info["complement_count"] = int(info.get("complement_count", 0))
        else:
            info = {
                "uid": uid,
                "amount": 0,
                "complement_sta": Switch.CLOSE.val,
                "complement_count": 0,
                "space": 0,
                "times_limit": 0,
                "exp_time": 0,
                # 是否默认值判断（仅此处有）
                "default_cache": 1
            }
            await cls.conf.rds.set_item(f"{cls.tb_name}:{uid}", json_encode(info), ex_time=cls.expired_sec)
        return info

    @classmethod
    async def process_safe_box(cls, uid, default_space=0, times_limit=0, increase_space=0, exp_time=0):
        """
        激活/升级保险箱
        激活：第一次购买 / 升级：后续购买 / 扩容：VIP升级
        """
        # 最新容量 = 终生卡顶配容量 + 当前VIP等级扩容量
        increase_space = int(increase_space)
        space = default_space + increase_space if increase_space != -1 else increase_space

        cls.conf.info_log(f"{uid}, 终生卡容量：{default_space}, VIP扩容量：{increase_space}")
        data = {
            "uid": uid,
            "amount": 0,
            "got_time": tool_dt.cur_time(),
            "complement_sta": Switch.CLOSE.val,
            "complement_count": 0,
            "space": space,
            "times_limit": times_limit,
            "exp_time": exp_time  # todo:暂时加上过期时间，以防之后开始定有效期
        }
        safe_box_info = await cls.cache_by_pk(uid)
        if not safe_box_info or safe_box_info.get("default_cache"):
            sta = await cls.update_safe_box(uid, data)
        else:
            cur_space = int(safe_box_info.get("space"))
            exp_time = int(safe_box_info.get("exp_time", 0))
            if cur_space != -1:
                data["space"] = space
            if exp_time:
                data["exp_time"] = exp_time

            data["amount"] = safe_box_info.get("amount")
            data["complement_sta"] = safe_box_info.get("complement_sta")
            data["complement_count"] = safe_box_info.get("complement_count")
            sta = await cls.update_safe_box(uid, data, safe_box_info)
        if sta:
            return data
        return

    @classmethod
    async def update_safe_box(cls, uid, update_info: dict, old_info=None):
        """更新保险箱记录和缓存（激活保险箱之后调用）"""
        async def update_cache(new_info):
            new_info["space"] = str(new_info.get("space", 0))
            new_info["amount"] = str(new_info.get("amount", 0))
            new_info["complement_count"] = str(new_info.get("complement_count", 0))
            key = f'{cls.tb_name}:{uid}'
            await cls.conf.rds.set_item(key, json_encode(new_info), ex_time=cls.expired_sec)

        if not old_info:
            sta = await cls.db_model.add_one(update_info)
            if sta:
                return await update_cache(update_info)

        sta = await cls.db_model.update_by_pk(uid, update_info, old_info, fun_success=update_cache)
        return sta

    @classmethod
    async def safe_box_use_complement(cls, u_info, safe_box_info):
        """领取自动补足"""
        exp_time = safe_box_info.get("exp_time") or 0
        if exp_time and exp_time > tool_dt.cur_time():
            return cls.conf.STA_CODE.NOT_WITHIN_VALID_PERIOD, "保险箱已过期，请重新激活再领取"

        if safe_box_info.get("complement_sta") != Switch.OPEN:
            return cls.conf.STA_CODE.FORBID, "自动补足设置关闭，请打开并设置额度"

        cur_complement_count = safe_box_info.get("complement_count", 0)
        if not cur_complement_count:
            return cls.conf.STA_CODE.FORBID, "自动补足未正确设置额度"

        cur_gold = u_info.get("gold", 0)
        if cur_gold > cur_complement_count:
            return cls.conf.STA_CODE.GOLD_NOT_ENOUGH, "灵石余额未满足领取条件"

        cur_amount = safe_box_info.get("amount", 0)
        if not cur_amount:
            return cls.conf.STA_CODE.GOLD_NOT_ENOUGH, "保险箱灵石库存不足"

        # 计算实际补足金额
        cur_complement_count -= cur_gold
        if cur_amount < cur_complement_count:
            cur_complement_count = cur_amount

        # 补足
        uid = u_info.get("uid")
        box_data = {"amount": cur_amount - cur_complement_count}
        user_data = {"gold": cur_complement_count}
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                await UserSafeBoxRC.update_safe_box(uid, box_data, safe_box_info)
                await BaseUserRC.update_user_asset(uid, user_data, ReasonCostGold.SAFE_BOX_COMPLEMENT)
        except Exception as e:
            cls.conf.error_log(f"safe_box_use_complement 事务执行失败，原因：{e}")
            return cls.conf.STA_CODE.FAIL, "自动补足灵石失败，请稍后重试"

        return cls.conf.STA_CODE.PASS, ""

