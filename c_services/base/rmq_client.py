import asyncio
import uuid
from typing import AnyStr, MutableMapping, Type
from aio_pika.abc import AbstractRobustConnection, ExchangeType, AbstractIncomingMessage, AbstractQueue
from aio_pika.pool import Pool
from aio_pika import DeliveryMode, Message, connect_robust, Channel
from nsanic.libs.tool import json_encode
from common.public.enum_const import ServiceEnum, Channel as ChannelEnum
from common.utils.utils import UtilsTool


class Rmq():
    """ rabbitmq client """
    CONN_MAP = {}
    # rpc相关
    CALLBACK_QUEUE: AbstractQueue = None
    FUTURES: MutableMapping[str, asyncio.Future] = {}

    def __init__(self, conf, logs=None):
        self.__conf = conf
        self.__max_connections = conf.pop("max_connections", 2)
        self.__max_channel = conf.pop("max_channel", 10)
        self.__logs = logs
        self.__conn_pool = None  # 连接池：从连接池中获取连接频道
        self.__c_conn_pool = None  # 频道连接池
        self.__fut = None

    @classmethod
    def init(cls, conf: dict, logs=None):
        if not all(key in conf for key in ['host', 'port', 'login']):
            raise Exception('rabbitmq连接配置错误,没有必须的配置项')
        conf_name = f"{conf['host']}-{conf['port']}-{conf['login']}"
        clt = cls.CONN_MAP.get(conf_name)
        if not clt:
            clt = cls(conf, logs=logs)
            cls.CONN_MAP[conf_name] = clt
        return clt

    def init_pool(self):
        if not self.__conn_pool:
            self.__conn_pool: Pool = Pool(self.get_connection, max_size=self.__max_connections)
        if not self.__c_conn_pool:
            self.__c_conn_pool = Pool(self.get_channel, max_size=self.__max_channel)

    async def get_connection(self) -> AbstractRobustConnection:
        return await connect_robust(**self.__conf)

    async def get_channel(self) -> Channel:
        async with self.__conn_pool.acquire() as connection:
            return await connection.channel()

    async def del_queue(self, que_name: str):
        """ 删除队列 """
        async with self.__c_conn_pool.acquire() as channel:
            queue = await channel.get_queue(que_name)
            await queue.delete()

    @staticmethod
    async def del_exchange(exchange):
        """ 删除交换器 """
        hasattr(exchange, 'delete') and await exchange.delete()

    def close(self):
        if self.__fut:
            self.__fut.set_result("close")

    async def consume(
            self,
            exchange_name,
            que_name,
            routing_key='',
            extra_rkey="",
            on_message=None,
            que_auto_del=False,
            enable_rpc=False,
            fanout_name = '',
    ) -> None:
        """
        消费
        que_auto_del：队列是否在程序停止时删除
            注意：这跟durable不一样，que_auto_del=True且durable=False时，rmq服务重启，队列也不存在
        """
        async with self.__c_conn_pool.acquire() as channel:  # type: Channel
            # await channel.set_qos(10)  # 只有当这10条消息中的至少一条被确认后，RabbitMQ才会发送更多的消息。
            match_exchange = await channel.declare_exchange(
                exchange_name, ExchangeType.DIRECT, durable=True
            )
            # 声明队列
            queue = await channel.declare_queue(
                que_name, auto_delete=que_auto_del
            )

            # Binding the queue to the exchange
            # 将队列绑定到交换器
            await queue.bind(match_exchange, routing_key=routing_key)
            extra_rkey and await queue.bind(match_exchange, routing_key=extra_rkey)

            if fanout_name:
                fanout_exchange = await channel.declare_exchange(fanout_name, ExchangeType.FANOUT,durable=True)
                await queue.bind(fanout_exchange)

            # Start listening the queue
            # 监听队列
            await queue.consume(on_message)

            # 是否启用rpc
            if enable_rpc:
                async def on_response(message: AbstractIncomingMessage) -> None:
                    if message.correlation_id is None:
                        print(f"Bad message {message!r}")
                        return
                    future: asyncio.Future = self.FUTURES.pop(message.correlation_id, None)
                    if future:
                        future.set_result(message.body)

                self.CALLBACK_QUEUE = await channel.declare_queue(exclusive=True)
                await self.CALLBACK_QUEUE.bind(match_exchange, routing_key=self.CALLBACK_QUEUE.name)
                await self.CALLBACK_QUEUE.consume(on_response, no_ack=True)

            print(" [*] Waiting for msgs. To exit press CTRL+C")
            self.__fut = asyncio.Future()
            await self.__fut

            # 使用迭代器读取消息
            # async with queue.iterator() as queue_iter:
            #     async for message in queue_iter:
            #         print(message)
            #         await message.ack()

    async def publish(
            self,
            msg: bytes,
            exchange_name,
            routing_key="",
            exp=None,
            msg_durable=DeliveryMode.PERSISTENT,
            correlation_id=None
    ) -> None:
        """ 推送消息 """
        async with self.__c_conn_pool.acquire() as channel:  # type: Channel
            # match_exchange = await channel.declare_exchange(
            #     exchange_name, ExchangeType.DIRECT, durable=True
            # )
            match_exchange = await channel.get_exchange(exchange_name)

            msg_obj = Message(
                msg,
                correlation_id=correlation_id,
                expiration=exp,
                delivery_mode=msg_durable,  # 标记持久消息
            )
            await match_exchange.publish(
                msg_obj,
                routing_key=routing_key,
            )

    async def cs2cs_rmp(
            self,
            target_cs: ServiceEnum,
            cmd,
            uid=1,
            msg: AnyStr = None,
            r_key="",
            exp=30,
            msg_durable=DeliveryMode.PERSISTENT,
            channel=ChannelEnum
    ):
        """
        子服务间（进程间）发送消息通过rmq（主要用在匹配）
        r_key: 指定路由键，不指定取c_type.phrase
        exp: 过期时间 seconds or (or datetime or timedelta)
        uid = 1 时默认为不需要uid（打包消息时不能小于等于0）
        msg: 传递json
        msg_durable: 消息默认持久化
        """
        if not isinstance(msg, bytes):
            msg = json_encode(msg, u_byte=True)
        pack_data = UtilsTool.pack_inner_msg(cmd, uid, msg)
        await self.push_data_to_service_by_rmq(target_cs, pack_data, channel, r_key, exp, msg_durable)

    async def push_data_to_service_by_rmq(
            self,
            target_cs: ServiceEnum,
            msg: bytes,
            channel: Type[ChannelEnum],
            r_key="",
            exp=None,
            msg_durable=DeliveryMode.PERSISTENT,
            correlation_id=None,
            log_fun=None,
    ):
        """
        通过rmq推送消息
        r_key: 指定路由键，不指定取c_type.phrase
        target_cs: 目标服务
        此处使用直连交换器
        """
        exchange_name = f"{channel.C_SERVICES}_{target_cs.val}"
        routing_key = r_key or f"{target_cs.phrase}_{target_cs.val}"
        try:
            await self.publish(msg, exchange_name, routing_key, exp, msg_durable, correlation_id)
        except Exception as e:
            err_info = f"push_data_by_rmq error {e}"
            log_fun(err_info) if callable(log_fun) else print(err_info)

    async def rep_by_rpc(
            self,
            target_cs: ServiceEnum,
            msg: AnyStr = None,
            r_key="",
            correlation_id=None,
            channel=ChannelEnum
    ):
        """
        rpc响应
        """
        await self.push_data_to_service_by_rmq(target_cs, msg, channel, r_key=r_key, correlation_id=correlation_id)

    async def req_by_rpc(self, target_cs, c_code, uid, msg: bytes, r_key='rpc_queue', channel=ChannelEnum):
        """ 通过rpc请求 """
        if not self.CALLBACK_QUEUE:
            raise AttributeError("no CALLBACK_QUEUE object ")
        if not isinstance(msg, bytes):
            msg = json_encode(msg, u_byte=True)
        msg = UtilsTool.pack_inner_msg(c_code, uid, msg)

        exchange_name = f"{channel.C_SERVICES}_{target_cs.val}"
        r_key = r_key or f"{target_cs.phrase}_{target_cs.val}"

        async with self.__c_conn_pool.acquire() as channel:  # type: Channel
            exchange = await channel.get_exchange(exchange_name)
            correlation_id = str(uuid.uuid4())
            loop = asyncio.get_running_loop()
            future = loop.create_future()

            self.FUTURES[correlation_id] = future

            await exchange.publish(
                Message(
                    msg,
                    content_type="text/plain",
                    correlation_id=correlation_id,
                    reply_to=self.CALLBACK_QUEUE.name,
                ),
                routing_key=r_key,
            )

            return await future
