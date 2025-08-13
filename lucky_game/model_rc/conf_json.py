"""
简单配置
"""
from nsanic.orm.rc_model import RCModel
from lucky_game.model_db.main import ConfJson
from lucky_game.const import CompleteSta


class ConfJsonRC(RCModel):
    """ json配置模型 """
    db_model = ConfJson
    tb_name = db_model.sheet_name()

    """ 配置ID """
    CONF_VIP = 'CONF_VIP'  # VIP通用配置
    CONF_SAFE_BOX = 'CONF_SAFE_BOX'  # 保险箱配置
    CONF_NEW_USER_GIFT = 'CONF_NEW_USER_GIFT'  # 新人礼包配置
    CONF_RELIEF = 'CONF_RELIEF'  # 救济通用配置
    CONF_SING_IN = 'CONF_SING_IN'  # 签到通用配置
    CONF_ACTIVE_SCORE = 'CONF_ACTIVE_SCORE'  # 每日活跃配置
    CONF_STORE = 'CONF_STORE'  # 商店通用配置
    CONF_LIFETIME_CARD = 'CONF_LIFETIME_CARD'  # 终生卡配置
    CONF_RANKING = 'CONF_RANKING'  # 排位通用配置
    CONF_FIRST_CHARGE = 'CONF_FIRST_CHARGE'  # 首充通用配置
    CONF_SWITCH = 'CONF_SWITCH'  # 开关配置：如内购等
    CONF_ADS_AWARDS = 'CONF_ADS_AWARDS'  # 大厅看广告领奖几率
    CONF_LUCK = "CONF_LUCK"  # 今日运势
    CONF_KF = "CONF_KF"  # 客服信息

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
