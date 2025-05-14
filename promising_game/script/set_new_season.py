"""
设置新赛季
"""
import aio_pika
from nsanic.libs.tool import json_encode
from c_services.const.cs_enum_const import CmdWorkers
from common.public.conf import CONF_AMQP
from common.public.enum_const import ServiceEnum, Channel
from promising_game.const import SeasonStatus
from promising_game.script.protocol import pack_data


async def set_new_season():
    msg = {
        "season_desc": "雾山五行",
        "off_season_time": 300,
        "start_time": 1733305200,
        "end_time": 1733307600,
        "condition": 30,
        "status": SeasonStatus.NEXT_SEASON
    }
    msg = json_encode(msg, u_byte=True)

    async with await aio_pika.connect_robust(**CONF_AMQP['default']) as connection:
        data, exchange_name, routing_key = pack_data(
            Channel.C_SERVICES, ServiceEnum.C_WORKERS, CmdWorkers.SET_NEW_SEASON, msg)
        channel = await connection.channel()
        match_exchange = await channel.get_exchange(exchange_name)
        await match_exchange.publish(aio_pika.Message(body=data), routing_key=routing_key)

