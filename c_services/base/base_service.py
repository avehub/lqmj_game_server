"""
server 基类
"""
import asyncio
from nsanic.libs.tool import json_parse
from c_services.base.base_manager import SessionManager
from common.proto.py_pb2.ws_leisure import one_of_model
from common.utils.kit_async import DelayCall
from common.utils.utils import UtilsTool
from c_services.base.base_player import BasePlayer
from c_services.base.base_server import BaseServer
from c_services.const.cs_enum_const import CmdRoom, CallCheck
from common.proto.py_pb2.ws_c2s import play_card_model, ws_leisure_pb2
from common.public.enum_const import StaCode, CacheKey
from promising_game.const import ReasonCostGold, PayType, QuickChatType, ActivityType
from promising_game.model_rc.base_activity import UserActivityRC
from promising_game.model_rc.base_user import BaseUserRC
from promising_game.model_rc.conf_quick_chat import ConfQuickChatRC


class BaseService(BaseServer, SessionManager):
    """
    基础服务：和具体的child service相关
    """
    ROOM = None
    PLAYER = None

    def __init__(self):
        super().__init__()
        SessionManager.__init__(self, use_pool=self.conf.USE_OBJ_POOL)
        self.add_handlers({
            CmdRoom.NEW_MATCH.val: self.__on_new_match,

            CmdRoom.LOST_CONNECT.val: self.__lost_connect,
            CmdRoom.TRUSTEE.val: self.__on_trustee,
            CmdRoom.BROADCAST_CHAT.val: self.__on_broadcast_chat,
            CmdRoom.QUERY_PLAYER_IN_SERVICE.val: self.__on_query_player_is_in_service,

            CmdRoom.ENTER_ROOM.val: self.__enter_room,
            CmdRoom.QUIT_ROOM.val: self.__on_quit_room,
            CmdRoom.FORCE_DISMISS.val: self.__on_force_dismiss,
            CmdRoom.SET_CARDS_IN_DEBUG.val: self.__on_set_cards,
        })
        self.register_rc_model(
            BaseUserRC, ConfQuickChatRC, UserActivityRC
        )

        self.__limit_call_tag = set()

    async def __on_new_match(self, _, data):
        """ 新匹配（服务器内部使用，不能给其它人调用） """
        await self.new_match(self.ROOM, self.PLAYER, data)

    async def __lost_connect(self, player, room, _):
        """ 离线处理 """
        player.offline = True
        self.info_log(room.tid, player.uid, "玩家掉线")
        # await room.inner_broadcast(CmdRoom.BROADCAST_CHAT)

    @staticmethod
    async def __on_trustee(player, room, _):
        """ 托管 """
        await room.do_trustee(player)

    def __clear_limit_call_tag(self, tag):
        self.__limit_call_tag.discard(tag)

    async def __on_broadcast_chat(self, player, room, data):
        """ 广播客户端发的消息 """
        quick_chat_model = ws_leisure_pb2.C2SQuickChat()
        quick_chat_model.ParseFromString(data)
        chat_id = quick_chat_model.chat_id

        chat_tag = f'{"quick_chat"}:{player.uid}:{chat_id}'
        if chat_tag in self.__limit_call_tag:
            room.inner_send(
                player, CmdRoom.BROADCAST_CHAT, code=StaCode.FAIL, hint=f"调用频率过高，请稍后再试")

        one_data = {}
        if quick_chat_model.chat_type == QuickChatType.HU_DONG:
            data_list = await ConfQuickChatRC.cache_by_chat_type()
            for one_data in data_list:
                if one_data.get("chat_id") == chat_id:
                    break
            else:
                return await room.inner_send(
                    player, CmdRoom.BROADCAST_CHAT, code=StaCode.FAIL, hint=f"互动id错误：{chat_id}")

            pay_type = one_data.get("pay_type")
            price = one_data.get("price") or one_data.get("leisure_rate") * room.base_score

            free_type = await UserActivityRC.check_hu_dong_free_privilege(player.uid)
            self.info_log(player.uid, "互动表情", free_type)
            if free_type == ActivityType.LIFETIME_CARD:
                price = 0
            elif free_type == ActivityType.WEEK_CARD:
                if chat_id <= 3:
                    price = 0

            if pay_type == PayType.BY_GOLD:
                if price > player.gold:
                    return await room.inner_send(player, CmdRoom.BROADCAST_CHAT, code=StaCode.GOLD_NOT_ENOUGH)
                if price != 0:
                    u_info = await self.update_user_gold(player, -price, ReasonCostGold.QUICK_CHAT)
                    if u_info:
                        player.update_gold(-price, accumulate=False)

                quick_chat_model.pay_type = pay_type
                quick_chat_model.res_count = str(player.gold)

            elif pay_type == PayType.BY_DIAMOND:
                if price > player.diamond:
                    return await room.inner_send(player, CmdRoom.BROADCAST_CHAT, code=StaCode.FAIL, hint='仙玉不足！')
                if price != 0:
                    u_info = await BaseUserRC.update_user_asset(player.uid, {"diamond": -price}, ReasonCostGold.QUICK_CHAT)
                    if u_info:
                        player.update_diamond(-price)

                quick_chat_model.pay_type = pay_type
                quick_chat_model.res_count = str(player.diamond)

        self.__limit_call_tag.add(chat_tag)
        DelayCall(5, self.__clear_limit_call_tag, chat_tag).start()

        rec_seat_id = quick_chat_model.rec_seat_id
        await room.send_quit_chat(player.seat_id, rec_seat_id, one_data, quick_chat_model)

    async def __enter_room(self, player, room, data):
        """ 进入房间 """
        # 离开房间则断线，重进则上线
        player.offline = False  # 此处不改变状态，玩家收不到房间以下两条信息
        if player.trustee:
            await room.do_trustee(player)

        self.info_log(player.uid, "__enter_room", player.tid, id(player))

        # 同步房间、玩家信息
        one_of_model.ParseFromString(data)
        req_id = one_of_model.req_id
        await self.notify_player_enter_room(room, player)
        # todo: 通知其它玩家该玩家上线
        await room.inner_send(player, CmdRoom.ENTER_ROOM, req_id=req_id)

    @staticmethod
    async def __on_quit_room(player, room, data):
        """ 离开房间 """
        one_of_model.ParseFromString(data)
        req_id = one_of_model.req_id
        await room.player_quit_room(player, req_id)

    async def __on_force_dismiss(self, player, room, data):
        """ 强制解散房间，主要用于休闲玩法 """
        if not self.check_inner_call(data):
            return
        room = self.get_room(room.tid)
        if not room:
            self.info_log(player.uid, "房间强制解散失败，找不到该房间")
            return
        await room.force_dismiss()

    async def __on_query_player_is_in_service(self, uid, data):
        is_exist = self.get_player(uid)
        data["is_exist"] = is_exist
        return data

    async def __on_set_cards(self, player, room, data):
        """ 设牌 """
        code, msg = room.set_cards_in_debug(data)
        if code != StaCode.PASS:
            await self.cs2ws_by_rmq(CmdRoom.SET_CARDS_IN_DEBUG, player.uid, code, msg, ws_id=player.ws_id)

    async def on_play_cards(self, player, room, data):
        """ 打牌 """
        play_card_model.ParseFromString(data)
        cards = play_card_model.cards or []
        code, msg = await room.player_play_cards(player, cards)
        if code != StaCode.PASS:
            await self.cs2ws_by_rmq(CmdRoom.PLAY_CARDS, player.uid, code, msg, ws_id=player.ws_id)
            return False, False, False
        return player, room, cards

    async def notify_player_enter_room(self, room, player=None):
        """ 玩家进入房间通知 """
        if player:
            await self.set_player_ws_id(player)
        await room.notify_player_enter_room(player)

    async def set_player_ws_id(self, player: BasePlayer):
        player.ws_id = await self.get_player_ws_id(player.uid)
        self.info_log(player.uid, "设置玩家ws_id", player.ws_id)

    @staticmethod
    async def init_player(player):
        player_info = await BaseUserRC.cache_by_uid(player.uid)
        player.init_player(player_info)

    @staticmethod
    async def update_user_gold(player, gold, reason):
        return await BaseUserRC.update_user_asset(player.uid, {"gold": gold}, reason)

    async def check_in_room(self, uid, cmd, with_notify=True):
        player = self.get_player(uid)
        if not player:
            if with_notify:
                await self.cs2ws_by_rmq(cmd, uid, StaCode.FAIL, hint='玩家未在服务中')
            return None, False
        room = self.get_room(player.tid)
        if not room:
            if with_notify:
                await self.cs2ws_by_rmq(cmd, uid, StaCode.FAIL, hint='房间不存在')
            return None, None
        return player, room

    async def clear_in_service(self):
        """ 启动时清理in service """
        all_in_service = await self.conf.rds.get_hash_all(CacheKey.IN_SERVICE)
        if not all_in_service:
            return
        uid_list = []
        for uid, info in all_in_service.items():
            uid = UtilsTool.to_py(uid)
            info = json_parse(info)
            if info.get("cs_type") == self.service_type:
                uid_list.append(uid)
        uid_list and await self.conf.rds.drop_hash_bulk(CacheKey.IN_SERVICE, uid_list)

    async def call_handler(self, cmd, uid, data):
        """
        uid: uid or ws
        注意顺序
        """
        func = self.cmd2func.get(cmd)
        if not func or not callable(func):
            return
        player, room = await self.check_in_room(uid, cmd)
        if not player:
            c_enum = CmdRoom.find_member_by_val(cmd)
            if c_enum.desc != CallCheck.INNER:
                return
            data = self.check_inner_call(data)
            if not data:
                return
            return await func(uid, data) if asyncio.iscoroutinefunction(func) else func(uid, data)

        return await func(player, room, data) if asyncio.iscoroutinefunction(func) else func(player, room, data)
