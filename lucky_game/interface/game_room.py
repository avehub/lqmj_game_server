"""
游戏房间接口
"""
from sanic import Request
from lucky_game.base_api import GameAuthApi
from common.public.enum_const import StaCode
from nsanic.libs.tool import json_encode, json_parse
from lucky_game.model_rc.game_rooms import GameRoomsRC
from lucky_game.model_rc.club_room_templates import ClubRoomTemplatesRC
from lucky_game.model_rc.club_users import ClubUsersRC
from lucky_game.model_rc.base_clubs import BaseClubRC
from pprint import pprint


class GameRoomBase(GameAuthApi):
    """游戏房间基础类"""
    async def _game_name(self, play_type: int):
        """获取游戏名称"""
        pass


class GameRoomAPI(GameAuthApi):
    async def _before_create_room(self, creator, price, club_id, u_info, rule_details):
        """创建游戏房间前的预处理"""
        # 茶馆房间特殊处理
        if club_id and club_id > 0:
            # 校验茶馆成员身份
            club_user, e = await ClubUsersRC.check_club_user(creator, club_id)
            if not club_user:
                return self.answer(StaCode.FAIL, hint=e)
            # 权限&规则校验
            club = await BaseClubRC.cache_session_get(club_id)
            if club['other'].get("host_power_room") == 1:
                return self.answer(StaCode.FAIL, hint="无法创建房间")
            if club['other'].get("pay_type") == 1 and u_info.room_card < price:
                return self.answer(StaCode.FAIL, hint="房卡不足")
            if club['other'].get("pay_type") == 2 and club.room_card < price:
                return self.answer(StaCode.FAIL, hint="茶馆基金不足")
        else:
            if rule_details.get("pay_type") == 1:
                if u_info.get("room_card") < price:
                    return self.answer(StaCode.FAIL, hint="房卡不足")
        return True


class CreateRoom(GameRoomAPI):
    """创建房间（支持普通房间和茶馆房间）"""
    async def post(self, req: Request, **kwargs):
        # 公共参数
        u_info = kwargs.get("u_info")
        creator = u_info.get("uid")
        platform = req.json.get("platform")
        game_type = req.json.get("game_type")
        play_type = req.json.get("play_type")
        pay_type = req.json.get("pay_type")
        price = req.json.get("price")
        m_game_name = req.json.get("m_game_name")
        total_round = req.json.get("total_round", 4)
        max_player = req.json.get("max_player", 4)
        rule_details = req.json.get("rule_details", 0)
        club_id = req.json.get("club_id")
        self.check_int(platform, require=True, minval=1, maxval=3, p_name="平台")
        self.check_int(game_type, require=True, p_name="游戏类型")
        self.check_int(play_type, require=True, p_name="玩法类型")
        self.check_int(club_id, require=False, minval=100000, p_name="茶馆ID")
        self.check_int(max_player, require=True, p_name="最大人数")
        self.check_str(rule_details, require=True, p_name="规则详情")
        self.check_str(m_game_name, require=True, p_name="游戏名称")
        self.check_int(total_round, require=True, p_name="总局数")
        self.check_int(pay_type, require=True, p_name="支付方式")
        self.check_int(price, require=True, p_name="支付金额")
        # 预处理
        before_status = await self._before_create_room(
            creator=creator,
            price=int(price),
            club_id=club_id,
            u_info=u_info,
            rule_details=json_parse(rule_details)
        )
        if before_status is not True:
            return before_status

        # 创建房间
        new_room, err = await GameRoomsRC.create_game_room(
            platform=platform,
            creator=creator,
            game_type=game_type,
            play_type=play_type,
            pay_type=pay_type,
            price=price,
            m_game_name=m_game_name,
            total_round=total_round,
            max_player=max_player,
            rule_details=rule_details,
            club_id=club_id
        )

        if not new_room:
            return self.answer(StaCode.FAIL, hint=err)
        return self.answer(data={"room_id": new_room})


class RoomList(GameRoomAPI):
    """房间列表（合并模板和现有房间）"""
    
    async def get(self, req: Request):
        club_id = req.args.get("club_id", 0)
        
        # 获取模板和房间
        templates, _ = await ClubRoomTemplatesRC.get_by_club(club_id)
        rooms, _ = await GameRoomsRC.get_game_rooms_by_filter(club_id=club_id)
        
        return self.answer(data={
            "templates": templates or [],
            "active_rooms": rooms or []
        })


class JoinRoom(GameRoomAPI):
    """加入房间"""
    async def post(self, req: Request, **kwargs):
        room_id = req.json.get("room_id")
        self.check_int(room_id, require=True, p_name="房间ID")
        u_info = kwargs.get("u_info")
        room_data, e = await GameRoomsRC.get_game_room_by_room_id(room_id)
        rule_details = json_parse(room_data['rule_details'])
        if rule_details.get("pay_type") == 1:
            if u_info.get("room_card") < room_data['price']:
                return self.answer(StaCode.FAIL, hint="房卡不足")
        uid = u_info.get("uid")
        sta, e = await GameRoomsRC.join_room(room_id, uid)
        if sta is False:
            return self.answer(StaCode.FAIL, hint=e)
        return self.answer()


class LeaveRoom(GameRoomAPI):
    """离开房间"""
    async def post(self, req: Request, **kwargs):
        room_id = req.json.get("room_id")
        self.check_int(room_id, require=True, p_name="房间ID")
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        # 更新房间信息
        sta, e = await GameRoomsRC.leave_room(room_id, uid)
        if sta is False:
            return self.answer(StaCode.FAIL, hint=e)
        return self.answer()


class DismissRoom(GameRoomAPI):
    """解散房间"""
    async def post(self, req: Request):
        room_id = req.json.get("room_id")
        user_id = req.ctx.user.uid
        
        # 校验房主身份
        room, _ = await GameRoomsRC.get_game_room_by_id(room_id)
        if room.creator != user_id:
            return self.answer(StaCode.FAIL, hint="只有房主可解散房间")
        
        # 删除房间
        await GameRoomsRC.delete_game_room(room_id)
        return self.answer()
