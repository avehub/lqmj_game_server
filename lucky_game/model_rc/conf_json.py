"""
简单配置
"""
from datetime import datetime

from nsanic.orm.rc_model import RCModel
from lucky_game.model_rc.base_rc import BaseCommonRC
from lucky_game.model_db.main import ConfJson
from lucky_game.const import CompleteSta
from tortoise.exceptions import OperationalError


class ConfJsonRC(BaseCommonRC):
    """ json配置模型 """
    db_model = ConfJson
    tb_name = db_model.sheet_name()

    """ 配置ID """
    CONF_VIP = 'CONF_VIP'  # VIP通用配置
    CONF_NEW_USER_GIFT = 'CONF_NEW_USER_GIFT'  # 新人礼包配置
    CONF_RELIEF = 'CONF_RELIEF'  # 救济通用配置
    CONF_LUCK = "CONF_LUCK"  # 今日运势
    CONF_KF = "CONF_KF"  # 客服信息
    CONF_SWITCH = "CONF_SWITCH" # 开关配置，如内购等
    CONF_NOTICE = "CONF_NOTICE"  # 系统公告
    CONF_MAINTAIN = "CONF_MAINTAIN"  # 维护配置
    CONF_ROOM_STOP = "CONF_ROOM_STOP"  # 停止创建加入房间配置
    CONF_PROXY_VIP_DISCOUNT = "CONF_PROXY_VIP_DISCOUNT"  # 渠道代理商消费折扣

    @classmethod
    async def cache_conf_data_by_pk(cls, pk_val) -> dict:
        db_conf_data = await cls.cache_by_pk(pk_val) or {}
        conf_data = db_conf_data.get("conf_data") or {}
        return conf_data

    @classmethod
    def stat_of_completion(cls, cur_value: int, cur_achieved: list, stat_targets: list):
        """
        按CompleteSta统计通用完成情况
        cur_value：当前值，用于判断是否满足领取条件
        cur_achieved：当前已领取记录
        stat_targets：统计目标的配置列表 [None, 2, 3, 4, 5, 6, 7, 8, 9]，例如1没有奖励则为None，其他按照奖励位顺序
        awards_sta：返回领取状态 [1, 2, 3, 1, 1, 1]
        """
        if not stat_targets:
            return []

        targets = list(stat_targets)
        complete_sta = [CompleteSta.INCOMPLETE.val] * len(targets)

        for i, target in enumerate(targets):
            if target is None:
                complete_sta[i] = CompleteSta.INCOMPLETE.val
            else:
                if cur_value >= int(target):
                    complete_sta[i] = CompleteSta.COMPLETED.val
                if cur_achieved and target in cur_achieved:
                    complete_sta[i] = CompleteSta.CLAIMED.val

        return complete_sta

    @classmethod
    async def create_conf(cls, conf_id: str, conf_data: str, desc: str):
        """新增配置"""
        try:
            data = {
                "conf_id": conf_id,
                "conf_data": conf_data,
                "desc": desc,
            }
            new = await cls.db_model.add_one(data)
            if not new:
                return False, "添加失败"
        except OperationalError as e:
            return None, f"失败:{e}"
        return True, "成功"

    @classmethod
    async def update_conf(cls, conf_id: str, conf_data: str = None, desc: str = None):
        """新增配置"""
        try:
            data = await cls.cache_conf_data_by_pk(conf_id)
            if not data:
                return False, "编辑的配置不存在"
            up_data = {}
            if conf_data is not None:
                up_data["conf_data"] = conf_data

            if desc is not None:
                up_data["desc"] = desc

            if up_data:
                up_data["update_time"] = int(datetime.now().timestamp())
                await cls.db_model.filter(conf_id=conf_id).update(**up_data)
                await cls.conf.rds.del_item(f"{cls.tb_name}:{conf_id}")
        except OperationalError as e:
            return None, f"失败:{e}"
        return True, "成功"


    @classmethod
    async def del_conf(cls, conf_id: str):
        try:
            sta = await cls.db_model.filter(conf_id=conf_id).delete()
            if sta:
                await cls.conf.rds.del_item(f"{cls.tb_name}:{conf_id}")
        except OperationalError as e:
            return None, f"失败:{e}"
        return True, "成功"

    @classmethod
    async def get_conf_list(cls, desc: str = None, page: int = None, page_size: int = None):
        try:
            query = {}
            if desc is not None:
                query["desc__contains"] = desc
            order_field = "-update_time"
            if page and page_size:
                total = await cls.db_model.filter(**query).count()
                data = []
                if total > 0:
                    offset = (page - 1) * page_size
                    data = await cls.db_model.filter(**query).order_by(order_field).offset(
                        offset).limit(page_size).values()
                result = await cls.page_result(page, page_size, total, data)
            else:
                result = data = await cls.db_model.filter(**query).order_by(order_field).values()
            if not data:
                return False, result
        except OperationalError as e:
            return None, f"查询失败:{e}"
        return True, result
