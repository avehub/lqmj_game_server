from typing import Optional

from aio_pika import DeliveryMode
# from nsanic.base_conf import BaseConf
from nsanic.libs import tool_dt
from nsanic.libs.rds_client import RdsClient
from c_services.base.base_conf import base_conf
from nsanic.libs.component import LogMeta
from nsanic.libs.tool import json_encode, json_parse
from c_services.base.rmq_client import Rmq
from common.proto.py_pb2.ws_base import PbWsBaseRep
from common.public.conf import C_SERVICE_SECRET_KEY
from common.public.enum_const import ServiceEnum, Channel, CacheKey, StaCode
from common.utils.utils import UtilsTool
from datetime import datetime
import calendar
from typing import Tuple, Union
from c_services.const.cs_enum_const import CmdNotice
from common.proto.py_pb2.common import common_pb2
from dateutil.relativedelta import relativedelta



class CommonApi(LogMeta):
    conf = base_conf
    SUBSCRIBE_FANOUT = Channel.C_SERVICES_COMMON
    if not conf.rds:
        conf.rds = RdsClient.init(conf.CONF_RDS['default'], logs=conf.log)
    if not conf.rmq:
        conf.rmq = Rmq.init(conf.CONF_AMQP['default'], logs=conf.log)

    @classmethod
    async def get_player_ws_id(cls, uid):
        ws_id, _ = await cls.get_player_ws_info(uid)
        return ws_id

    @classmethod
    async def get_player_join_gold(cls, uid):
        try:
            user_gold_key = f"{CacheKey.PLAYER_GOLD}:{uid}"
            gold = await cls.conf.rds.get_item(user_gold_key, jsparse=True)
            if gold is None:
                gold = {"gold": 0}
        except Exception as e:
            gold = {"gold": 0}
        return gold

    @classmethod
    async def get_player_in_game(cls, uid):
        try:
            is_gaming = await cls.conf.rds.get_hash(CacheKey.PLAYER_GOLD, uid, jsparse=True)
        except Exception as e:
            is_gaming = {"is_gaming": False}
        return is_gaming

    @classmethod
    async def get_player_ws_info(cls, uid):
        ws_info = await cls.conf.rds.get_hash(CacheKey.WS_ONLINE_INFO, uid)
        if ws_info:
            ws_id, timestamp = ws_info.split(b'--' if isinstance(ws_info, bytes) else '--')
            return int(ws_id), int(timestamp)
        return 0, 0

    @classmethod
    async def cs2cs_by_rmq(
            cls,
            cs_type: ServiceEnum,
            c_code,
            msg=None,
            uid=1,
            r_key="",
            exp: Optional[int] = 30,
            delivery_mode=DeliveryMode.NOT_PERSISTENT,
    ):
        """
        通过rmq推送消息到网关
        该方法默认消息不持久化
        """
        await cls.conf.rmq.cs2cs_rmp(cs_type, c_code, uid, msg, r_key, exp, delivery_mode)

    @classmethod
    async def push_task2worker(cls, c_code=0, msg=None, uid=1, r_key="", cs_type: ServiceEnum = ServiceEnum.C_WORKERS):
        """
        推送消息到worker服务，该服务的消息不会过期
        """
        msg = msg or {}
        msg["secret"] = C_SERVICE_SECRET_KEY
        await cls.cs2cs_by_rmq(cs_type, c_code, msg, uid, r_key, exp=None, delivery_mode=DeliveryMode.PERSISTENT)

    @classmethod
    async def push_task2chat(cls, c_code=0, msg=None, uid=1, r_key="", cs_type: ServiceEnum = ServiceEnum.C_CHAT):
        """
        推送消息到chat服务
        """
        msg = msg or {}
        msg["secret"] = C_SERVICE_SECRET_KEY
        await cls.cs2cs_by_rmq(cs_type, c_code, msg, uid, r_key, exp=None, delivery_mode=DeliveryMode.PERSISTENT)

    async def publish_to_fanout(cls, cmd, uid = 1, msg= None):
        """
        向SUBSCRIBE_FANOUT频道发送消息
        """
        if not isinstance(msg, bytes):
            msg = json_encode(msg, u_byte=True)
        pack_data = UtilsTool.pack_inner_msg(cmd, uid, msg)
        try:
            await cls.conf.rmq.publish(
                msg=pack_data,
                exchange_name=cls.SUBSCRIBE_FANOUT,
            )
        except Exception as e:
            cls.log_err(f"publish_to_fanout error: {e}")

    @classmethod
    async def inner_cs2ws(
            cls,
            service_type,
            c_code,
            uid=1,
            msg=None,
    ):
        """
        内部调用ws
        目标service: ws_hall
        发给ws服务的，非直接面向用户
        """
        r_key = await cls.__get_routing_key(uid)
        cmd = UtilsTool.packet_command(service_type, c_code)
        await cls.cs2cs_by_rmq(ServiceEnum.WS_HALL, cmd, msg, uid, r_key=r_key)

    @classmethod
    async def __get_routing_key(cls, uid):
        if uid == 1:
            r_key = Channel.CHANNEL_SYSTEM_MSG
        else:
            ws_id = await cls.get_player_ws_id(uid)
            r_key = f"{ServiceEnum.WS_HALL.phrase}_{ServiceEnum.WS_HALL.val}_{ws_id}"
        return r_key

    @classmethod
    async def send_msg_to_player(
            cls,
            c_code,
            uid=1,
            code=StaCode.DEFAULT,
            hint="",
            msg=None,
            req_id="",
            cs_type: ServiceEnum = 0
    ):
        """ 发送消息至玩家 """
        r_key = await cls.__get_routing_key(uid)
        hint = hint or code.msg
        pb_data = PbWsBaseRep.encode(code, hint, msg, req_id)
        cmd = UtilsTool.packet_command(cs_type, c_code)
        await cls.cs2cs_by_rmq(ServiceEnum.WS_HALL, cmd, pb_data, uid, r_key=r_key)

    @classmethod
    async def send_red_dot(cls, uid, rd_type):
        """ 红点消息 """
        model = common_pb2.S2COneFieldWeb()
        model.red_dot = rd_type
        await cls.send_msg_to_player(CmdNotice.RED_DOT, uid=uid, msg=model, cs_type=ServiceEnum.C_NOTICE)

    @classmethod
    async def req_by_rpc(cls, cs_type: ServiceEnum, c_code, uid, msg, r_key=''):
        """ rpc请求 """
        if not isinstance(msg, bytes):
            msg = json_encode(msg, u_byte=True)
        data = await cls.conf.rmq.req_by_rpc(cs_type, c_code, uid, msg, r_key)
        return json_parse(data, log_fun=cls.log_err)

    @classmethod
    async def rep_by_rpc(cls, cs_type: ServiceEnum, msg, r_key="", correlation_id=None):
        """ rpc响应 """
        if not isinstance(msg, bytes):
            msg = json_encode(msg, u_byte=True)
        await cls.conf.rmq.rep_by_rpc(cs_type, msg, r_key, correlation_id=correlation_id)

    @classmethod
    async def bytes_by_int_list(cls, bytes_list):
        """批量获取bytes"""
        result = []
        if not bytes_list:
            return result
        data = [p.decode('utf-8') for p in bytes_list]
        result = [int(p) for p in data]
        return result

    @classmethod
    async def merge_by_key(
            cls,
            arr1: list[dict[str, any]],
            arr2: list[dict[str, any]],
            key: str,
            fields: Optional[list[str]] = None
    ):
        """合并两个数组"""
        index = {
            item[key]: {k: v for k, v in item.items() if (not fields or k in fields)}
            for item in arr2
        }

        return [
            {
                **item,
                **{  # 仅合并指定字段
                    k: v
                    for k, v in index.get(item[key], {}).items()
                    if (not fields or k in fields)
                }
            }
            for item in arr1
        ]

    @classmethod
    async def json_by_dict(cls, data: str):
        """ json转dict  """
        if not data:
            return {}
        if "'" in data:
            str_json = data.replace("'", "\"")
        else:
            str_json = data
        return json_parse(str_json)

    @classmethod
    async def seconds_since_midnight(cls, now: datetime = None) -> int:
        """
        返回当前时间距离当天凌晨（00:00:00）过去的秒数

        Returns:
            int: 当天凌晨到现在的秒数
        """
        if now is None:
            now = datetime.now()
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return int((now - midnight).total_seconds())

    @classmethod
    async def get_time_range(cls, period: str = 'month', start_hour: int = 0, end_hour: int = 23, state_minute: int = 0,
                             end_minute: int = 59, start_second: int = 0, end_second: int = 59) -> Tuple:
        """
        获取本月或当天的第一天和最后一天的时间戳

        Args:
            period (str): 'month' 获取本月的时间戳, 'day' 获取当天的时间戳

        Returns:
            Tuple[int, int]: (开始时间戳, 结束时间戳)
        """
        # 获取当前时间
        now = datetime.now()

        if period == 'day':
            # 获取当天的日期时间（00:00:00）
            start_of_day = now.replace(hour=start_hour, minute=state_minute, second=start_second, microsecond=0)
            # 获取当天的日期时间（23:59:59）
            end_of_day = now.replace(hour=end_hour, minute=end_minute, second=end_second, microsecond=999999)
            return int(start_of_day.timestamp()), int(end_of_day.timestamp())

        elif period == 'month':
            # 获取本月第一天的日期时间（00:00:00）
            first_day = now.replace(day=1, hour=start_hour, minute=state_minute, second=start_second, microsecond=0)
            # 获取本月最后一天的日期
            last_day = calendar.monthrange(now.year, now.month)[1]
            # 获取本月最后一天的日期时间（23:59:59）
            last_day_dt = now.replace(day=last_day, hour=end_hour, minute=end_minute, second=end_second, microsecond=0)
            return int(first_day.timestamp()), int(last_day_dt.timestamp())

        else:
            return None, None

    @classmethod
    async def list_by_group(cls, arr: list[dict[str, any]], key: str, unordered: bool = True):
        result = {}
        try:
            for item in arr:
                index = item[key]
                if index not in result:
                    result[index] = []
                result[index].append(item)
            # 将字典转为列表
            if unordered:
                return list(result.values())
        except Exception as e:
            return e
        return result

    @classmethod
    async def append_query_params(cls, url, params):
        """
        追加查询参数到URL
        :param url: 基础URL
        :param params: 查询参数字典
        :return: 追加查询参数后的URL
        """
        if not params:
            return url
        query_string = '&'.join(f"{key}={value}" for key, value in params.items())
        if '?' in url:
            return f"{url}&{query_string}"
        else:
            return f"{url}?{query_string}"

    @classmethod
    async def date_time_range(cls, start_time: datetime, end_time: datetime) -> list[datetime]:
        """
        获取时间段内的所有时间点
        :param start_time: 开始时间
        :param end_time: 结束时间
        :return: 时间点列表
        """
        start_date = tool_dt.dt_str(start_time, '%Y-%m-%d').split('-')
        end_date = tool_dt.dt_str(end_time, '%Y-%m-%d').split('-')
        date_range = tool_dt.date_range(start=datetime(int(start_date[0]), int(start_date[1]), int(start_date[2])),
                                        end=datetime(int(end_date[0]), int(end_date[1]), int(end_date[2])))
        return date_range

    @classmethod
    async def get_month_start_timestamps(cls, start_timestamp: int, end_timestamp: int) -> list[int]:
        """
        使用 dateutil 库实现相同功能
        Args:
            start_timestamp (int): 起始时间戳(10位)
            end_timestamp (int): 结束时间戳(10位)
        Returns:
            list[int]: 包含每个月第一天时间戳的列表
        """
        start_date = datetime.fromtimestamp(start_timestamp)
        end_date = datetime.fromtimestamp(end_timestamp)
        # 调整开始时间为当月第一天
        current_date = start_date.replace(day=1)
        result = []
        while current_date <= end_date:
            result.append(int(current_date.timestamp()))
            # 增加一个月
            current_date += relativedelta(months=1)
        return result

    @classmethod
    async def get_month_end_timestamp(cls, start_timestamp: int) -> int:
        """
        使用dateutil获取月末时间戳
        Args:
            start_timestamp (int): 月份开始时间戳

        Returns:
            int: 月末23:59:59的时间戳
        """
        # 将时间戳转换为datetime对象
        start_date = datetime.fromtimestamp(start_timestamp)

        # 获取下个月第一天，然后减去一秒
        next_month_first = start_date.replace(day=1) + relativedelta(months=1)
        end_date = next_month_first - relativedelta(seconds=1)

        return int(end_date.timestamp())

    @classmethod
    async def calculate_quartiles(cls, data):
        """
        计算下四分位数(Q1)、中位数(Q2)、上四分位数(Q3)
        支持浮点数和Decimal类型

        参数:
            data: 数值列表，可以是float或Decimal类型

        返回:
            包含下四分位、中位、上四分位值的元组 (q1, q2, q3)
        """
        if not data:
            return 0, 0, 0

        # 确保数据是列表并排序
        sorted_data = sorted(data)
        n = len(sorted_data)

        def get_percentile(p):
            """
            获取指定百分位的值
            p: 百分位 (0-1)
            """
            if not (0 <= p <= 1):
                raise ValueError("百分位必须在0到1之间")

            k = (n - 1) * p
            f = int(k)
            c = k - f

            if f + 1 >= n:
                return sorted_data[-1]
            return sorted_data[f] + c * (sorted_data[f + 1] - sorted_data[f])

        q1 = get_percentile(0.25)
        q2 = get_percentile(0.5)
        q3 = get_percentile(0.75)

        return q1, q2, q3
    
    @classmethod
    async def custom_round(cls, num):
        """ 四舍五入 """
        if num - int(num) >= 0.5:
            return int(num) + 1
        else:
            return int(num)
