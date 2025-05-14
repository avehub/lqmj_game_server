"""
缓存管理
"""
import aio_pika
import redis.asyncio as redis
from nsanic.libs.tool import json_encode
from tortoise import Tortoise

from c_services.const.cs_enum_const import CmdMatch, CmdRoom
from common.public.conf import CONF_RDS, CONF_AMQP, CONF_DB, C_SERVICE_SECRET_KEY
from common.public.enum_const import ServiceEnum, Channel
from lucky_game.model_db.main import User
from lucky_game.script.protocol import pack_data

DEFAULT_RDS = CONF_RDS['default']
DEFAULT_RDS = DEFAULT_RDS.copy()
DEFAULT_RDS.pop("use_block", None)


async def del_conf_leisure(cs_type_list: list):
    """ 删除休闲场配置，并刷新子服务内存取到的休闲场配置 """
    for cs_type in cs_type_list:
        cs_enum = ServiceEnum.find_member_by_val(cs_type)
        if not isinstance(cs_enum, ServiceEnum):
            raise ValueError("cs_type error")
        async with redis.Redis(**DEFAULT_RDS) as client:
            print(f"Ping successful: {await client.ping()}")
            await client.hdel("conf_leisure", cs_enum.val)
            # todo: 发送到匹配服务器和子游戏重置配置

        msg = {"cs_type": cs_type, "secret": C_SERVICE_SECRET_KEY}
        if not isinstance(msg, bytes):
            msg = json_encode(msg, u_byte=True)
        async with await aio_pika.connect_robust(**CONF_AMQP['default']) as connection:
            for cs_enum in (cs_enum, ServiceEnum.C_MATCHING):
                # if cs_enum == ServiceEnum.C_MATCHING:
                #     cmd = CmdMatch.REFRESH_CONF_LEISURE
                # else:
                #     cmd = CmdRoom.REFRESH_CONF_LEISURE
                cmd = CmdRoom.REFRESH_CONF_LEISURE

                data, exchange_name, routing_key = pack_data(
                    Channel.C_SERVICES, cs_enum, cmd, msg)

                print("刷新休闲场配置：", cs_enum, data, exchange_name, routing_key)

                channel = await connection.channel()
                match_exchange = await channel.get_exchange(exchange_name)
                await match_exchange.publish(
                    aio_pika.Message(body=data),
                    routing_key=routing_key,
                )


async def init_db():
    await Tortoise.init(
        config={
            'apps': {
                "promising_game": {'models': ["promising_game.model_db.main", "promising_game.model_db.extra"]}},
            'connections': CONF_DB,
            'use_tz': False,
            'timezone': "UTC"
        }
    )


async def delete_user(uid: int, platform=5):
    """ 删除账号 """
    await init_db()
    # 1.找到openid对应的uid并删除该缓存
    u_info = await User.get_by_pk(uid)
    if not u_info:
        raise ValueError(f'没有该玩家数据，请检查uid合法性: {uid}')
    dev_id = u_info.get("dev_ident")
    open_id = u_info.get("openid")
    sta = await User.del_by_pk(uid)
    if sta:
        async with redis.Redis(**DEFAULT_RDS) as client:
            print("删号并删缓存")
            await client.delete(f"user_device_id:{dev_id}")
            await client.delete(f"user_open_id_{platform}:{open_id}")
            await client.delete(f"user:{uid}")
