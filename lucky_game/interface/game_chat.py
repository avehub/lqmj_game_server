"""
聊天/快捷聊天相关接口
"""
from nsanic.libs import tool_dt
from sanic import Request
from c_services.const.cs_enum_const import CmdChat
from common.proto.py_pb2.common import pack_chat_history
from common.public.enum_const import ServiceEnum, ChatChannel, BanType
from lucky_game.base_api import GameAuthApi
from lucky_game.handler.sensitive_words import SensitiveWords
from lucky_game.model_rc.base_chat import ChatRecordRC
from lucky_game.model_rc.base_user import BaseUserRC, BaseBanRC
from lucky_game.model_rc.conf_leisure import LeisureConfRC
from lucky_game.model_rc.conf_quick_chat import ConfQuickChatRC
from lucky_game.const import QuickChatType, PayType, ChatConst


class GetQuickChatConf(GameAuthApi):
    """获取快捷聊天配置"""

    async def get(self, req: Request, **_):
        chat_type = self.check_int(
            req.args.get("chat_type"), require=True, minval=QuickChatType.HU_DONG, p_name="chat_type")
        if not QuickChatType.find_member_by_val(chat_type):
            self.answer(self.sta_code.ERR_ARG, hint="快捷聊天类型错误")

        cs_type = self.check_int(req.args.get("cs_type"), require=True, minval=ServiceEnum.C_WORKERS, p_name="cs_type")
        if not ServiceEnum.find_member_by_val(cs_type):
            self.answer(self.sta_code.ERR_ARG, hint="参数错误")

        leisure_list = await LeisureConfRC.cache_all_by_cs_type(cs_type=cs_type)
        level = self.check_int(req.args.get("level"), require=True, minval=1, maxval=len(leisure_list), p_name="level")
        leisure_conf = leisure_list[level - 1]
        (not leisure_conf) and self.answer(self.sta_code.NO_CONFIGURATION, hint="没有对应休闲场配置")

        chat_confs = await ConfQuickChatRC.cache_by_chat_type(chat_type)
        (not chat_confs) and self.answer(self.sta_code.NO_CONFIGURATION, hint="没有快捷聊天配置")

        for q in chat_confs:
            if q.get("pay_type") == PayType.BY_FREE:
                continue

            leisure_rate = q.get("leisure_rate") or 0
            if leisure_rate:
                base_score = leisure_conf.get("base_score")
                q["price"] = base_score * leisure_rate
            else:
                pass

        self.log_info(f"GetQuickChatConf 快捷聊天 {chat_type}，游戏 {cs_type}，场次 {level} 配置加载成功")
        return self.answer(data=chat_confs)


class SendChatMessage(GameAuthApi):
    """发送聊天消息"""
    WAIT_KEY = 'chat_limit'

    async def post(self, req: Request, **kwargs):
        chat_channel = self.check_int(req.json.get("chat_channel"), require=True, p_name='chat_channel（聊天频道）')
        cc_enum = ChatChannel.find_member_by_val(chat_channel)
        (not isinstance(cc_enum, ChatChannel)) and self.answer(self.sta_code.ERR_ARG, hint="暂未开启的聊天频道")

        u_info = kwargs.get("u_info")
        from_uid = u_info.get("uid")  # 发送者

        # 检查禁言/冷却（仅对世界频道有效）
        if chat_channel == ChatChannel.WORLD.val:
            # 检查是否被禁言
            ban_sta = await BaseBanRC.check_ban_by_type(from_uid, BanType.WORLD_CHAT_BAN)
            if ban_sta:
                self.answer(self.sta_code.FORBID, hint="已被禁言")

            # 检查冷却时间
            is_wait, limit_time = await BaseUserRC.check_cool_down(from_uid, wait_key=self.WAIT_KEY)
            if is_wait:
                self.answer(self.sta_code.REQ_FREQUENT, hint=f"抱歉，请稍等{limit_time}秒再发送下一条信息")

        content = self.check_str(req.json.get("content"), p_name='content（内容）')
        # 检查内容是否为空或超出最大长度限制
        if not content or len(content) > ChatConst.WORLD_MAX_VAL:
            content_hint = "不能发送空消息" if not content else "不能超出50个字符"
            self.answer(self.sta_code.ERR_ARG, hint=content_hint)

        content = self.conf.sw.filter(content)  # 敏感词过滤

        to_uid = req.json.get("to_uid") or 1

        to_uid = self.check_int(to_uid, require=True, p_name="to_uid（接受者）")
        message = {
            "chat_channel": chat_channel,  # 聊天频道
            "from_uid": from_uid,  # 发送者
            "to_uid": to_uid,  # 接收者（仅私聊）
            "content": content,  # 内容
            "created": tool_dt.cur_time(),  # 发送时间，使用当前时间戳
        }

        match chat_channel:
            case ChatChannel.WORLD:
                await self.push_task2chat(CmdChat.RECEIVE_CHAT_MSG, msg=message)
                await BaseUserRC.set_cool_down(
                    from_uid, wait_key=self.WAIT_KEY, cool_down_time=ChatConst.COOLDOWN_TIME)  # 设置冷却时间

            case ChatChannel.FRIENDS:
                await self.push_task2chat(CmdChat.RECEIVE_CHAT_MSG, uid=to_uid, msg=message)

        self.answer(hint="OK")


class GetChatRecords(GameAuthApi):
    """获取聊天记录"""
    decorators = []

    async def get(self, req: Request, **_):
        chat_channel = self.check_int(req.args.get("chat_channel"), require=True, p_name='chat_channel（聊天频道）')
        cc_enum = ChatChannel.find_member_by_val(chat_channel)
        (not isinstance(cc_enum, ChatChannel)) and self.answer(self.sta_code.ERR_ARG, hint="暂未开启的聊天频道")

        limit = self.check_int(req.args.get("limit"), minval=10, maxval=100, default=50, p_name='limit（查询记录限制）')

        # 根据用户信息和请求参数查询聊天记录
        records = await ChatRecordRC.query_chat_records(chat_channel, limit=limit)

        m = pack_chat_history(records)

        # 返回结果
        return self.answer(self.sta_code.PASS, data=m)
