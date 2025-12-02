# coding=utf-8
import asyncio
import os

from nsanic.libs import tool_dt
from nsanic.libs.manager import WsRdsConnector
from nsanic.libs.tool import json_parse
from aio_pika.abc import AbstractIncomingMessage
from sanic import Request
from nsanic.base_ws import BaseWebsocket
from typing import AnyStr, Union
from nsanic.verify import vint
from sanic.exceptions import WebsocketClosed
from c_services.const.cs_enum_const import CmdRoom, CmdWs, CmdFanOut
from common.proto.py_pb2.ws_base import PbWsBaseRep
from common.public.common_class import CommonApi
from common.public.enum_const import Channel, ServiceEnum, CacheKey
from common.utils.utils import UtilsTool
from lucky_game.model_rc.base_user import BaseUserRC


class BaseWS(BaseWebsocket, CommonApi):
    ws_manager = WsRdsConnector

    dft_type: Union[int, str] = ServiceEnum.WS_HALL.val  # 系统默认消息类型
    beat_code: Union[int, str] = CmdWs.BEAT  # 心跳消息标码
    reject_code: Union[int, str] = CmdWs.REJECT  # 弹回消息标码
    mult_process_login_code = CmdWs.MULT_PROCESS_LOGIN  # 多进程登录

    _services = {}

    def __init__(self):
        super().__init__()
        self.fun_pack_msg: callable = UtilsTool.pack_msg_by_bytes
        self.fun_parse_msg: callable = UtilsTool.parse_msg_by_bytes
        self.__process_id = os.getpid()
        BaseUserRC.conf = self.conf

    @property
    def channel(self):
        return f"{Channel.C_SERVICES}_{ServiceEnum.WS_HALL}_{self.__process_id}"

    @property
    def que_name(self):
        return f"{self.conf.SERVER_NAME}_{self.conf.SERVER_ENUM.val}_{self.__process_id}"

    @property
    def routing_key(self):
        # return f"{self.que_name}_{self.__process_id}"
        return self.que_name

    @property
    def extra_rkey(self):
        return self.conf.CHANNEL_SYSTEM

    @classmethod
    def ori_ip(cls, req: Request):
        """ 多级代理最前面那个ip """
        ip_list = req.headers.get("x-forwarded-for")
        if ip_list:
            return ip_list.split(',')[0]
        return req.headers.get("x-real-ip") or req.client_ip

    def init_loop_task(self):
        asyncio.create_task(self.__consume_rmq())
        super().init_loop_task()

    async def client_listen(self, ws, _):
        while 1:
            try:
                msg = await ws.recv()
                (c_type, c_code), data = self.fun_parse_msg(msg, log_fun=self.log_err)
                if c_type and (c_type == self.dft_type) and (c_code == self.beat_code):
                    await ws.send(msg)
                else:
                    await self.distribute(ws, c_type, c_code, data)
            except WebsocketClosed as e:
                self.log_err(f"{ws.ukey}, ws关闭：{e}")
                return
            except Exception as e:
                self.log_err(f"消息错误：{e}")
                return

    async def __consume_rmq(self):
        """ 消费rabbitmq """
        exchange_name = f"{Channel.C_SERVICES}_{self.conf.SERVER_ENUM.val}"
        self.log_info(f"""
            ws启动rmq服务：
            交换器：{exchange_name},
            路由键：{self.routing_key},
            额外路由键：{self.extra_rkey},
            绑定到路由键的队列：{self.que_name},
        """)
        await self.conf.rmq.consume(
            exchange_name, self.que_name, self.routing_key, self.extra_rkey, self.on_message, que_auto_del=True)

    async def check_ws_req_params(self, req, ws):
        """ 检查参数 """
        timestamp = req.args.get('timestamp') or ""
        flag, timestamp = vint(timestamp, require=True)
        # if not flag or (cur_time() - timestamp) > 300:  # 5分钟时效
        if not flag:  # 5秒时效
            data = PbWsBaseRep.encode(self.sta_code.ERR_ARG, hint="timestamp err")
            await ws.send(self.fun_pack_msg(self.dft_type, self.reject_code, data))
            return False
        uid = req.args.get('uid')
        flag, val = vint(uid, require=True)
        if not flag:
            data = PbWsBaseRep.encode(self.sta_code.ERR_ARG)
            await ws.send(self.fun_pack_msg(self.dft_type, self.reject_code, data))
            return False
        user_info = await BaseUserRC.cache_by_uid(uid)
        if not user_info:
            data = PbWsBaseRep.encode(self.sta_code.NO_PLAYER_INFO, hint="user information is unavailable")
            await ws.send(self.fun_pack_msg(self.dft_type, self.reject_code, data))
            return False
        return user_info

    @staticmethod
    def __user_is_ban(u_info):
        """ 判断玩家是否被封禁 """
        ban_time = u_info.get("ban_time") or 0
        if ban_time == -1 or ban_time >= tool_dt.cur_time():
            return True
        return False

    async def check_ws_conn(self, u_info, req, ws):
        """ 检查ws连接 """
        if self.__user_is_ban(u_info):
            data = PbWsBaseRep.encode(self.sta_code.FORBID, hint="您已被封禁，待解禁！")
            await ws.send(self.fun_pack_msg(self.dft_type, self.reject_code, data))
            return False
        uid = u_info.get("uid")
        timestamp = req.args.get('timestamp')
        if not timestamp or not timestamp.isdigit():
            data = PbWsBaseRep.encode(self.sta_code.FAIL, hint="无效连接，缺少必要参数。")
            await ws.send(self.fun_pack_msg(self.dft_type, self.reject_code, data))

        timestamp = int(timestamp)
        # _, old_timestamp = await self.get_player_ws_info(uid)
        # if old_timestamp >= timestamp:
        #     self.delay_pre and (await asyncio.sleep(self.delay_pre))
        #     data = PbWsBaseRep.encode(self.sta_code.MULT_LOGIN, hint="您已在其它设备登录，不可重复登录。")
        #     await ws.send(self.fun_pack_msg(self.dft_type, self.reject_code, data))
        #     return

        old_ws = self.ws_manager.get_ws(uid)
        if old_ws:
            if old_ws.timestamp >= timestamp:
                self.log_info("ws请求过期", uid, old_ws.timestamp, timestamp)
                data = PbWsBaseRep.encode(self.sta_code.EXPIRED, hint=f"请求过期（{timestamp}），请刷新！")
                await ws.send(self.fun_pack_msg(self.dft_type, self.reject_code, data))
                return False
            data = PbWsBaseRep.encode(self.sta_code.MULT_LOGIN)
            await old_ws.send(self.fun_pack_msg(self.dft_type, self.reject_code, data))
            self.log_info("异地登录, 旧连接：", old_ws.ws_proto.id, "新连接：", ws.ws_proto.id)
        else:
            await self.mult_login_at_different_process(uid)

        setattr(ws, 'timestamp', timestamp)
        key_info = f'{self.__process_id}--{timestamp}'
        # key_info = f'{self.__process_id}'
        await self.ws_manager.set_ws(uid, ws, key_info)
        return True

    async def mult_login_at_different_process(self, uid):
        """ 异地登录在不同的进程 """
        ws_id = await self.get_player_ws_id(uid)
        if ws_id > 0 and ws_id != self.__process_id:
            self.log_info(uid, f"异地登录在不同的进程, 老进程：{ws_id}, 新进程: {self.__process_id}")
            data = {"from_pid": self.__process_id, "uid": uid}
            await self.cs2cs_by_rmq(ServiceEnum.WS_HALL, self.mult_process_login_code, data, 1, r_key=self.extra_rkey)

    async def deal_mult_process_login(self, data: bytes):
        """ 处理多进程登录 """
        data = json_parse(data, log_fun=self.log_err)
        from_pid = data.get('from_pid')
        if from_pid == self.__process_id:
            return
        uid = data.get("uid")
        old_ws = self.ws_manager.get_ws(uid)  # 旧连接没有与新连接不是一个进程
        if old_ws:
            self.log_info(uid, f"处理多进程登录, 新进程：{from_pid}通知老进程: {self.__process_id}关闭连接")
            data = PbWsBaseRep.encode(self.sta_code.MULT_LOGIN)
            await old_ws.send(self.fun_pack_msg(self.dft_type, self.reject_code, data))
            await self.ws_manager.close_ws(uid, del_key=False)

    async def on_offline(self, uid):
        """ 玩家断线处理 """
        # uid = off_ws.ukey
        # cur_ws = self.ws_manager.get_ws(uid)
        # if cur_ws and (cur_ws.ws_proto.id == off_ws.ws_proto.id):
        # await self.ws_manager.close_ws(uid)
        await super().on_offline(uid)  # todo: 这里不删除online key
        cs_info = await self.conf.rds.get_hash(CacheKey.IN_SERVICE, uid, jsparse=True)
        self.log_info(uid, "玩家断线, 通知所在子服务：", cs_info)
        if cs_info:
            cs_type = cs_info.get("cs_type")
            cs_enum = ServiceEnum.find_member_by_val(cs_type)
            await self.cs2cs_by_rmq(cs_enum, CmdRoom.LOST_CONNECT, uid=uid)
        await self.publish_to_fanout(CmdFanOut.LOST_CONNECT, uid )


    async def distribute(self, ws, c_type, c_code, msg: AnyStr):
        """ 分发消息 """
        service = self._services.get(c_type)
        if service:
            return await service.service(c_code, ws, msg)
        return await self.ws2cs(ws, c_type, c_code, msg)

    async def ws2cs(self, ws, c_type, c_code, msg: AnyStr):
        """ 推送至子服务（此处采用rmp发布订阅） """
        cs_enum = ServiceEnum.find_member_by_val(c_type)
        if not cs_enum:
            data = PbWsBaseRep.encode(self.sta_code.FAIL, hint="Invalid service")
            await ws.send(self.fun_pack_msg(self.dft_type, self.reject_code, data))
            return
        await self.cs2cs_by_rmq(cs_enum, c_code, msg, ws.ukey)

    async def publish_to_cs_by_rds(self, c_type, c_code, uid, msg: AnyStr):
        """ ws往子服务发送消息 """
        cmd = UtilsTool.packet_command(c_type, c_code)
        channel = f"{Channel.C_SERVICES}_{c_type}"
        try:
            data = UtilsTool.pack_inner_msg(cmd, uid, msg)
            print(data)
            await self.rds.publish(channel, data)
        except Exception as e:
            self.conf.log.error(f"ws2child error {e}")

    async def on_message(self, message: AbstractIncomingMessage):
        """ rmq监听消息回调 """
        async with message.process():
            # 此处用上下文处理必须走完所有逻辑消息才算完成
            c_type, c_code, data, uid = self.parse_channel_msg(message.body, self.log_err)
            match message.routing_key:
                case self.extra_rkey:
                    uid = -1
            # if message.routing_key == self.conf.CHANNEL_SYSTEM:
            #     uid = -1
            await self.on_receive_channel_msg(c_type, c_code, data, uid)

    @staticmethod
    def parse_channel_msg(msg: AnyStr, log_fun=None):
        """ 解析频道收到的消息 """
        (cmd, uid), data = UtilsTool.parse_inner_msg(msg, log_fun)
        if not cmd:
            return
        c_type, c_code = UtilsTool.explode_command(cmd)
        return c_type, c_code, data, uid

    async def __deal_ban_player_online(self, data):
        """ 在线处理封禁玩家 """
        data = json_parse(data, log_fun=self.log_err)
        uid = data.get("uid")
        ws = self.ws_manager.get_ws(uid)
        if not ws:
            return None
        data = PbWsBaseRep.encode(self.sta_code.FORBID, hint="您已被封禁，待解禁！")
        await ws.send(self.fun_pack_msg(self.dft_type, self.reject_code, data))
        return ws

    async def on_receive_channel_msg(self, c_type: Union[int, str], c_code, data, receiver):
        """接收处理指定频道的订阅消息"""
        if not receiver:
            return
        if receiver == -1:
            if c_code == self.mult_process_login_code:  # todo 此处code可能会冲突
                return await self.deal_mult_process_login(data)

            if c_code == CmdWs.BAN_PLAYER:
                if ws := await self.__deal_ban_player_online(data):
                    self.delay_aft and (await asyncio.sleep(self.delay_aft))
                    await ws.close()
                return

            for ws in self.ws_manager.all_ws():
                try:
                    ws and (await ws.send(self.fun_pack_msg(c_type, c_code, data)))
                except Exception as err:
                    self.log_info(f'公共消息推送失败：{err}')
            return
        ws = self.ws_manager.get_ws(receiver)
        if not ws:
            return
        try:
            return await ws.send(self.fun_pack_msg(c_type, c_code, data))
        except Exception as err:
            self.log_info(f'发送目标消息失败,receiver:{receiver},data:{data},错误信息：{err}')
