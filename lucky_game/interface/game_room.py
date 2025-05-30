"""
游戏房间接口
"""
from sanic import Request
from lucky_game.base_api import GameAuthApi
from common.public.enum_const import StaCode
from lucky_game.model_rc.game_rooms import GameRoomsRC
from lucky_game.model_rc.club_room_templates import ClubRoomTemplatesRC
from lucky_game.model_rc.club_users import ClubUsersRC


class GameRoomAPI(GameAuthApi):
    async def _before_create_room(self, club_id: int, creator_uid: int, play_type: int, req: Request, club_templates_id: int = 0):
        """创建游戏房间前的预处理"""
        # 茶馆房间特殊处理
        if club_id > 0:
            # 校验茶馆成员身份
            club_user, _ = await ClubUsersRC.get_club_user_by_id(creator_uid)
            if not club_user or club_user.club_id != club_id:
                return self.answer(StaCode.FAIL, hint="非茶馆成员无法创建房间")

            # 获取茶馆模板
            templates, _ = await ClubRoomTemplatesRC.get_by_id(club_templates_id)
            if not templates or templates.club_id != club_id:
                return self.answer(StaCode.FAIL, hint="无该玩法模板")

            # 使用第一个模板创建
            room_rule = templates["room_rule"]
            max_player = templates["max_player"]
            cs_type = templates["cs_type"]
        else:
            # 普通房间默认参数
            room_rule = req.json.get("room_rule", {})
            max_player = req.json.get("max_player", 4)
            cs_type = req.json.get("cs_type", 0)
        return room_rule, max_player, cs_type


class CreateRoom(GameRoomAPI):
    """创建房间（支持普通房间和茶馆房间）"""
    async def post(self, req: Request, **kwargs):
        # 公共参数
        u_info = kwargs.get("u_info")
        creator = u_info.get("uid")
        platform = req.json.get("platform")
        play_type = req.json.get("play_type")
        club_id = req.json.get("club_id", 0)
        club_id = req.json.get("club_id", 0)
        club_templates_id = req.json.get("template_id", 0)
        self.check_int(platform, require=True, minval=1, maxval=3, p_name="平台")
        self.check_int(play_type, require=True, minval=1, maxval=3, p_name="玩法类型")
        self.check_int(club_id, require=False, minval=100000, p_name="茶馆ID")
        self.check_int(club_templates_id, require=False, p_name="茶馆ID")

        # 预处理
        room_rule, max_player, cs_type = await self._before_create_room(
            club_id, creator, play_type, req
        )
        # 创建房间
        new_room, err = await GameRoomsRC.create_game_room(
            platform=platform,
            creator=creator,
            room_rule=room_rule,
            cs_type=cs_type,
            club_id=club_id,
            max_player=max_player
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
    
    async def post(self, req: Request):
        room_id = req.json.get("room_id")
        user_id = req.ctx.user.uid
        
        # 获取并更新房间信息
        room, _ = await GameRoomsRC.get_game_room_by_id(room_id)
        if room.current_players >= room.max_player:
            return self.answer(StaCode.FAIL, hint="房间已满")
        
        # 更新玩家列表
        uids = room.room_uids.split(",") if room.room_uids else []
        if str(user_id) not in uids:
            uids.append(str(user_id))
            await GameRoomsRC.update_game_room(
                room_id, 
                current_players=room.current_players+1,
                room_uids=",".join(uids)
            )
        
        return self.answer()


class LeaveRoom(GameRoomAPI):
    """离开房间"""
    
    async def post(self, req: Request):
        room_id = req.json.get("room_id")
        user_id = req.ctx.user.uid
        # 更新房间信息
        room, _ = await GameRoomsRC.get_game_room_by_id(room_id)
        uids = room.room_uids.split(",") if room.room_uids else []
        if int(user_id) in uids:
            uids.remove(int(user_id))
            await GameRoomsRC.update_game_room(
                room_id, 
                current_players=room.current_players-1,
                room_uids=",".join(uids) if uids else ""
            )
        
        return self.answer()


class DismissRoom(GameRoomAPI):
    """解散房间"""
    
    async def post(self, req: Request):
        room_id = req.json.get("room_id")
        user_id = req.ctx.user.uid
        
        # 校验房主身份
        room, _ = await GameRoomsRC.get_game_room_by_id(room_id)
        if room.creator_uid != user_id:
            return self.answer(StaCode.FAIL, hint="只有房主可解散房间")
        
        # 删除房间
        await GameRoomsRC.delete_game_room(room_id)
        return self.answer()
