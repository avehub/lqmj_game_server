from typing import Dict

from c_services.base.base_service import BaseService
from common.public.enum_const import ServiceEnum, StaCode
# from lucky_game.model_rc.base_activity import ConfActivityRC
# from lucky_game.model_rc.base_safe_box import UserSafeBoxRC
from lucky_game.model_rc.conf_leisure import LeisureConfRC
from nsanic.libs import tool

from lucky_game.model_rc.game_rooms import GameRoomsRC
from ..const.cs_enum_const import CmdRoom, RoomType
from ..cs_mahjong.const import OverType


class LeisureService():
    def __init__(self):
        self.add_handlers({
            CmdRoom.REFRESH_CONF_LEISURE.val: self.__refresh_conf_leisure,
        })
        self.__leisure_conf: Dict[str, list] = {}  # -> {service_num: [{},{}...]}

    async def __read_leisure_conf(self, cs_type):
        self.__leisure_conf.clear()
        data = await LeisureConfRC.cache_all_by_cs_type(cs_type=cs_type)
        for d in data:
            pt = d.get('play_type') or 1
            self.__leisure_conf.setdefault(f'{cs_type}_{pt}', []).append(d)

    async def leisure_conf(self, cs_type=0, play_type=1):
        # 读取休闲场配置
        k = f'{cs_type}_{play_type}'
        if not self.__leisure_conf.get(k):
            await self.__read_leisure_conf(cs_type)
        return self.__leisure_conf.get(k) or []

    async def __refresh_conf_leisure(self, _, data):
        """ 刷新休闲场配置 """
        data = tool.json_parse(data)
        cs_type = data.get("cs_type")
        cs_enum = ServiceEnum.find_member_by_val(cs_type)
        if not isinstance(cs_enum, ServiceEnum):
            return
        self.log_info("刷新休闲场配置", data)
        await self.__read_leisure_conf(cs_type)


class BaseLeisureService(BaseService, LeisureService):
    """
    休闲玩法基础服务：不限于休闲场，准确来说非房卡场
    """

    def __init__(self):
        BaseService.__init__(self)
        LeisureService.__init__(self)
        self.add_handlers({
            CmdRoom.GIVE_UP.val: self.__on_give_up,
            CmdRoom.RECHARGE.val: self.__on_recharge,
            CmdRoom.RECHARGE_ING.val: self.__on_recharge_ing,
            CmdRoom.FORCE_DISMISS_ROOM.val: self.__force_dismiss_room,
        })

    async def get_level_conf(self, level, play_type=1) -> dict:
        data = await self.leisure_conf(self.service_type.val, play_type)
        return data[level - 1]

    # async def safe_box_auto_complement(self, player):
    #     """ 保险箱自动补足 """
    #     safe_box_info = await UserSafeBoxRC.cache_by_pk(player.uid)
    #     if not safe_box_info or safe_box_info.get("default_cache"):
    #         return False
    #     u_info = {"gold": player.gold, "uid": player.uid}
    #     sta_code, hint = await UserSafeBoxRC.safe_box_use_complement(u_info, safe_box_info)
    #     self.log_info(player.uid, "自动补足", sta_code, hint)
    #     if sta_code == StaCode.PASS:
    #         await self.init_player(player)
    #         return True
    #     return False

    async def new_match(self, room, c_player, data):
        """ 新匹配（服务器内部使用，不能给其它人调用） """
        user_list = data.get("u_list")
        level = data.get("level")
        play_type = data.get("pt") or 1
        platform = data.get("platform") or 0
        room_conf = await self.get_level_conf(level, play_type)
        room_conf["room_type"] = RoomType.COMMON
        room_conf["rule_details"] = {}
        extra_room_info = data.get("extra_room_info") or {}
        max_player = room_conf.get("rule_conf", {}).get("max_player") or 4
        room_data = {
            "max_player":max_player,
            "pay_type": 0,
            "price": 0,
            "cs_type": self.service_type.val,
            "is_location": 0,
            "is_friend": 0,
            "room_type": RoomType.COMMON.val,
            "status": 0,
            "round_num": 1,
        }
        new_room,err = await GameRoomsRC.create_game_room(platform,user_list[0].get("uid"),{},play_type,0,**room_data)
        if not new_room:
            self.log_info("休闲场创建房间失败",err,"参数",platform,user_list[0].get("uid"),play_type,room_data)
            return
        extra_room_info["tid"] = new_room
        room = self.create_room(room, room_conf, **extra_room_info)
        self.log_info("接收到新匹配：", data, "开启新桌子：", room.tid)
        player_list = []
        for u_info in user_list:
            uid = u_info.get("uid")
            is_robot = u_info.get("is_robot")
            player = self.create_player(c_player, uid, is_robot)
            player.init_additional_info(u_info)  # 初始化附属信息：道具、皮肤等
            player_list.append(player)
        await room.player_join_room(player_list)
        await self.notify_player_enter_room(room)
        room.try_round_start()

    @staticmethod
    async def __on_give_up(player, room, _):
        """ 认输 """
        await room.player_give_up(player)

    @staticmethod
    async def __on_recharge(player, room, _):
        """ 充值 """
        await room.player_recharge(player)

    @staticmethod
    async def __on_recharge_ing(player, room, _):
        """ 充值中回调 """
        await room.player_recharge_ing(player)

    async def __force_dismiss_room(self, _, data):
        tid = data.get("room_id")
        room = self.get_room(tid)
        if room:
            await room.force_dismiss()
