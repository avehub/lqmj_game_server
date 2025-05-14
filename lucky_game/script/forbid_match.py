from datetime import datetime

import aio_pika
from nsanic.libs import tool_dt
from nsanic.libs.tool import json_encode
from c_services.const.cs_enum_const import CmdMatch
from common.public.conf import CONF_AMQP
from common.public.enum_const import ServiceEnum, Channel
from lucky_game.script.protocol import pack_data


async def let_service_forbid_match(cs_type, time_str: str):
    """ 使某个cs禁止匹配 """
    cs_enum = ServiceEnum.find_member_by_val(cs_type)
    if not isinstance(cs_enum, ServiceEnum):
        raise ValueError("cs_type error")
    # async with redis.Redis(**CONF_RDS['default']) as client:
    #     print(f"Ping successful: {await client.ping()}")
    #     await client.hdel("conf_leisure", cs_enum.val)

    time_obj = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
    if time_obj.timestamp() - tool_dt.cur_time() < 0:
        raise ValueError(f"指定时间早于指定时间：{time_str}")

    msg = {"cs_type": cs_type, "time_str": time_str, "secret": r"eFSvMBklwiWoVbv85KzPjEM_jjHJ7d-TIishQaGlR8w"}
    msg = json_encode(msg, u_byte=True)
    async with await aio_pika.connect_robust(**CONF_AMQP['default']) as connection:
        data, exchange_name, routing_key = pack_data(
            Channel.C_SERVICES, ServiceEnum.C_MATCH, CmdMatch.ADD_FORBID_SERVICE, msg)
        channel = await connection.channel()
        match_exchange = await channel.get_exchange(exchange_name)
        await match_exchange.publish(
            aio_pika.Message(body=data),
            routing_key=routing_key,
        )
