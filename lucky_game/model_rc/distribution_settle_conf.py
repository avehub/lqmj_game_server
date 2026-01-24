"""
分销结算相关
"""
from nsanic.libs.tool import json_parse
from nsanic.orm.rc_model import RCModel
from pymysql import OperationalError

from lucky_game.model_db.main import DistributionSettleConf


class DistributionSettleConfRC(RCModel):
    db_model = DistributionSettleConf
    tb_name = db_model.sheet_name()

    # 类型：房卡分佣
    TYPE_ROOM_CARD_SETTLE = 1
    # 农产品
    TYPE_KIND_SETTLE = 2

    @classmethod
    async def cache_session_set(cls, query, value):
        return await cls.conf.rds.set_item(f"{cls.tb_name}:{query}", value)

    @classmethod
    async def cache_session_get(cls, query):
        data = await cls.conf.rds.get_item(f"{cls.tb_name}:{query}")
        if isinstance(data, bytes):
            data = json_parse(data.decode())
        return data

    @classmethod
    async def cache_session_drop(cls, query):
        return await cls.conf.rds.drop_item(f"{cls.tb_name}:{query}")

    @classmethod
    async def get_profit_conf_filter(cls, level: int = None, profit_type: int = None, range_num: int = None, profit_condition: str = None):
        """
        获取分销结算配置
        :return:
        """
        try:
            query = {}
            if level is not None:
                 query["level"] = level
            if profit_condition is not None:
                 query["profit_condition"] = profit_condition
            if profit_type is not None:
                 query["type"] = profit_type
            if range_num is not None:
                query["range_max"] = range_num
            result = records = await cls.db_model.filter(**query).order_by("level").values()
            if not records:
                return False, []
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return True, result


    @classmethod
    async def get_profit_ratio(cls, num: int, profit_type: int = TYPE_ROOM_CARD_SETTLE):
        """ 获取分润比例 """
        query = f"{profit_type}_raito_{num}"
        profit_ratio = await cls.cache_session_get(query)
        if not profit_ratio:
            sta, profit_data = await cls.get_profit_conf_filter(range_num=num, profit_type=profit_type)
            profit_ratio = 0
            if profit_data and profit_data[0]:
                profit_ratio = profit_data[0].get("profit_ratio", 0)
                await cls.cache_session_set(query, profit_ratio)
        return profit_ratio

    @classmethod
    async def get_profit_num(cls, num: int, profit_type: int = TYPE_ROOM_CARD_SETTLE):
        """ 获取分润比例 """
        query = f"{profit_type}_num_{num}"
        profit_num = await cls.cache_session_get(query)
        if not profit_num:
            sta, profit_data = await cls.get_profit_conf_filter(range_num=num, profit_type=profit_type)
            profit_num = 0
            if profit_data and profit_data[0]:
                profit_num = profit_data[0].get("profit_num", 0)
                await cls.cache_session_set(query, profit_num)
        return profit_num


