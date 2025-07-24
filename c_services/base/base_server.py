import asyncio
import traceback
from typing import AnyStr

from nsanic.libs import tool_dt
from nsanic.libs.tool import json_parse
from nsanic.orm.rc_model import RCModel
from tortoise import Tortoise, connections

from c_services.const.cs_enum_const import CmdChat, CallCheck
from common.public.common_class import CommonApi
from common.utils.utils import UtilsTool
from aio_pika.abc import AbstractIncomingMessage
from common.proto.py_pb2.ws_base import PbWsBaseRep
from common.public.enum_const import Channel, StaCode, ServiceEnum, CacheKey
from c_services.base.base_conf import BaseConf, base_conf
from common.public.pub_base_service import BasePubService


class BaseServer(BasePubService, CommonApi):
    """
    基础服务器，负责监听频道，收发消息
    """
    conf: BaseConf = base_conf
    enable_rpc: bool = False  # 是否开启RPC服务

    __slots__ = (
        "__listen_channel",
        "__listener_obj",
        "__server_id",
        "__service_name",
        "__queue_name",
        "__service_info",
    )

    def __init__(self):
        super().__init__(service_type=0)
        self.__listen_channel = []
        self.__listener_obj = None
        self.__server_id = 1  # 服务器ID
        self.__service_name = ""
        self.__queue_name = None
        self.__service_info = None

    @property
    def listen_channel(self):
        return self.__listen_channel

    @property
    def sid(self):
        return self.server_id

    @property
    def server_id(self):
        """服务ID"""
        return self.__server_id

    @property
    def service_name(self):
        return self.__service_name

    @property
    def queue_name(self):
        return self.__queue_name

    async def setup(self, server_id, service_type, service_name=None, server_info=None):
        """ 注册信息 """
        assert server_id > 0
        self.__server_id = server_id
        self.service_type = service_type
        self.__service_name = (service_name or self.__class__.__name__).lower()
        # self.__queue_name = f"{self._service_name}_{self._service_type}_{self.sid}"
        self.__queue_name = f"{self.__service_name}_{self.service_type}"
        self.__service_info = server_info
        self.conf.set_conf(self.__service_name, self.__server_id)
        self.__listen_channel.append(f'{Channel.C_SERVICES}_{service_type}')
        self.log_info(f"""
            启动服务: {self.__service_name}
            服务号: {self.service_type}
            监听频道：{self.__listen_channel}
            rmq监听频道(交换器)：{self.__listen_channel[0]}
            rmq监听路由键：{self.__queue_name}
            rmq监听队列(该队列绑定了上面的交换器与路由键)：{self.__queue_name}
            server_id: {self.__server_id}
            _service_info: {self.__service_info}
        """)

    async def init_db(self):
        """ 初始化db """
        # Here we create a mysql DB using file "config"
        #         #  also specify the app name of "models"
        #         #  which contain models from "app.models"
        await Tortoise.init(
            config=self.conf.db_conf(),
        )
        # Generate the schema
        # await Tortoise.generate_schemas()  # 运行时自动生成

    async def __read_task(self):
        """读取任务"""
        try:
            async for message in self.__listener_obj.listen():
                try:
                    data = message["data"]  # 订阅成功返回1（忽略）
                    self.log_info(f"收到消息：{message}")
                    if data == 1:
                        continue
                    await self.receive_data_callback(data)
                except Exception as e:
                    self.log_err(f"message callback error:{traceback.format_exc()} \n e: {e}")
        except asyncio.exceptions.CancelledError:
            await self.on_signal_stop("xxx")
        except Exception as data:
            self.log_err(f"read task error: {data}")
            await asyncio.sleep(0.5)

    async def receive_data_callback(self, data: AnyStr):
        """ 收到消息回调 """
        # todo: 解析data
        (cmd, uid), data = UtilsTool.parse_inner_msg(data)
        if not cmd:
            return
        # c_type, c_code = UtilsTool.explode_command(cmd)
        # if c_type not in (self._service_type,):
        #     return
        return await self.call_handler(cmd, uid, data)

    async def call_handler(self, cmd, uid, data):
        """
        uid: uid or ws
        注意顺序
        """
        func = self.cmd2func.get(cmd)
        if not func or not callable(func):
            return
        return await func(uid, data) if asyncio.iscoroutinefunction(func) else func(uid, data)

    async def rpc_client(self):
        pass

    async def __consume_rmq(self, exchange_name=''):
        """ 消费rabbitmq """
        exchange_name = exchange_name or self.listen_channel[0]
        que_name = self.queue_name
        await self.conf.rmq.consume(
            exchange_name, que_name, que_name, on_message=self.on_message, enable_rpc=self.enable_rpc)

    async def on_message(self, message: AbstractIncomingMessage) -> None:
        """ rmq消息回调 """
        async with message.process():  # 使用上下文处理器结束时也会消息确认
            try:
                res_data: dict = await self.receive_data_callback(message.body) or {}  # 调用方法
                if message.reply_to:  # 处理rpc调用
                    res_data.pop('secret', None)
                    cs_type = res_data.pop('cs_type')
                    cs_enum = ServiceEnum.find_member_by_val(cs_type)
                    if not cs_enum:
                        return
                    await self.rep_by_rpc(cs_enum, res_data, message.reply_to, message.correlation_id)
            except Exception as e:
                self.log_err(f"on_message_rpc error:{traceback.format_exc()} \n -->e: {e}")

    async def start_server(self):
        """ 启动服务 """
        await self.init_component()
        asyncio.create_task(self.__read_task())
        await self.clear_in_service()
        asyncio.create_task(self.rpc_client())
        await self.__consume_rmq()

    async def init_component(self):
        """ 初始化组件 """
        RCModel.set_conf(self.conf)
        await self.init_db()  # 初始化db
        self.conf.rds.init_loop()  # 初始化redis
        self.conf.rmq.init_pool()  # 初始化rmq
        await self.__init_listen_channel()

    async def clear_in_service(self):
        """ 子类重写（某些不是游戏的服务不需要清理） """

    async def sava_player_in_service(self, uid, tid):
        info = {
            "tid": tid,
            "cs_type": self.service_type,
            "sid": self.__server_id,
            "timestamp": tool_dt.cur_time()
        }
        await self.conf.rds.set_hash(CacheKey.IN_SERVICE, uid, info)

    async def get_player_in_service(self, uid):
        return await self.conf.rds.get_hash(CacheKey.IN_SERVICE, uid, jsparse=True)

    async def del_player_in_service(self, uid):
        await self.conf.rds.drop_hash(CacheKey.IN_SERVICE, uid)

    async def on_signal_stop(self, *args):
        """ 服务关闭时触发 """
        self.log_info(f"{self.service_name} 服务关闭")
        await connections.close_all()
        self.conf.rmq.close()
        await self.__listener_obj.close()

    async def __init_listen_channel(self):
        """初始化监听通道"""
        assert self.listen_channel
        if self.__listener_obj:
            await self.__listener_obj.close()
            self.__listener_obj = None
        await asyncio.sleep(0)
        while 1:
            try:
                obj = await self.conf.rds.pub_sub(self.listen_channel)  # 订阅与发布系统状态
                self.__listener_obj = obj
                break
            except Exception as data:
                self.log_err(f"sid {self.server_id} init_listen_channel error: {str(data)}")
                await asyncio.sleep(2)

    async def publish_data(self, channel: str, cmd, uid, data: AnyStr):
        """推送数据"""
        pack_data = UtilsTool.pack_inner_msg(cmd, uid, data)
        try:
            await self.conf.rds.publish(channel, pack_data)
        except Exception as data:
            self.log_err(f"publish data error: {self.server_id} {data}")

    async def cs2ws_by_rds(self, c_code, uid, code: StaCode, hint="", msg: AnyStr = None, req_id=""):
        """
        send to gateway by redis
        msg: protobuf消息体（对象）
        推送 -> child gateway
        [sid, body, server_index]
        """
        hint = hint or code.msg
        pb_data = PbWsBaseRep.encode(code, hint, msg, req_id)
        cmd = UtilsTool.packet_command(self.service_type, c_code)
        await self.publish_data(self.conf.CHILD_GATE_CHANNEL, cmd, uid, pb_data)

    async def cs2ws_by_rmq(
            self,
            c_code,
            uid,
            code: StaCode = StaCode.DEFAULT,
            hint="",
            msg=None,
            req_id="",
            ws_id=0,
    ):
        """
        send to gateway by rabbitmq
        通过rmq推送消息到网关
        broad：表示是否发给所有连上ws的人
        """
        hint = hint or code.msg
        pb_data = PbWsBaseRep.encode(code, hint, msg, req_id)
        await self.cs2ws_by_rmq_in_room(c_code, uid, pb_data, ws_id)

    async def cs2ws_by_rmq_in_room(self, c_code, uid, pb_data, ws_id=0):
        """
        房间内发送消息到ws, 因为存在广播，所以data可能一样，不需多次序列化
        broad：表示是否发给所有连上ws的人
        """
        cmd = UtilsTool.packet_command(self.service_type, c_code)
        ws_id = ws_id or await self.get_player_ws_id(uid)
        r_key = f"{ServiceEnum.WS_HALL.phrase}_{ServiceEnum.WS_HALL.val}_{ws_id}"
        await self.cs2cs_by_rmq(ServiceEnum.WS_HALL, cmd, pb_data, uid, r_key=r_key)

    async def notice_ws_by_rmq(
            self, c_code, uid=1, code=StaCode.DEFAULT, hint="", msg=None, req_id="", cs_type=ServiceEnum.C_NOTICE):
        """
        通过 notice 服务号8 通知玩家
        注意：uid=1时广播所有在线玩家
        uid=1: 默认为系统消息频道，推送该频道当前所有在线玩家都可收到消息
        """
        await self.send_msg_to_player(c_code, uid, code, hint, msg, req_id, cs_type=cs_type)

    async def send_msg_to_player(
            self,
            c_code,
            uid=1,
            code=StaCode.DEFAULT,
            hint="",
            msg=None,
            req_id="",
            cs_type: ServiceEnum = 0
    ):
        cs_type = cs_type or self.service_type
        await super().send_msg_to_player(c_code, uid, code, hint, msg, req_id, cs_type=cs_type)

    def check_inner_call(self, data, cmd=0, uid=0):
        """ 检查是否是服务器内部调用 """
        data = json_parse(data, self.log_err)
        if data.get("secret", "") != self.conf.SECRET_KEY:
            self.log_info("非法调用！！！", cmd, uid, data)
            return {}
        # data.pop("secret")
        return data


class JsonBaseServer(BaseServer):
    """ 内部服务调用消息协议使用Json """

    def __init__(self):
        super(JsonBaseServer, self).__init__()

    async def call_handler(self, cmd, uid, data: AnyStr):
        """ 重写call handler 反序列化data """
        data = self.check_inner_call(data, cmd, uid)  # 内部检查调用
        if not data:
            return
        data.pop("secret")
        return await super().call_handler(cmd, uid, data)
