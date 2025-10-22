"""
封禁玩家
"""
import aio_pika
from nsanic.libs.tool import json_encode
from c_services.const.cs_enum_const import CmdWorkers
from common.public.conf import CONF_AMQP
from common.public.enum_const import ServiceEnum, Channel
from lucky_game.script.protocol import pack_data


async def ban_player(uid, ban_time: int):
    msg = {
        "uid": uid,
        "ban_time": ban_time,
    }
    msg = json_encode(msg, u_byte=True)
    async with await aio_pika.connect_robust(**CONF_AMQP['default']) as connection:
        data, exchange_name, routing_key = pack_data(
            Channel.C_SERVICES, ServiceEnum.C_WORKERS, CmdWorkers.BAN_PLAYER, msg)
        channel = await connection.channel()
        match_exchange = await channel.get_exchange(exchange_name)
        await match_exchange.publish(
            aio_pika.Message(body=data),
            routing_key=routing_key,
        )
