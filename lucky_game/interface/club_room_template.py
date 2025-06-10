"""
游戏房间接口
"""
from sanic import Request
from lucky_game.base_api import GameAuthApi
from common.public.enum_const import StaCode, ServiceEnum
from nsanic.libs.tool import json_encode, json_parse
from lucky_game.model_rc.game_rooms import GameRoomsRC
from lucky_game.model_rc.club_room_templates import ClubRoomTemplatesRC
from lucky_game.model_rc.club_users import ClubUsersRC
from lucky_game.model_rc.base_clubs import BaseClubRC
from c_services.const.cs_enum_const import CmdRoom
from lucky_game.const.const import PlatForm
from lucky_game.handler.decorator import BaseDecorator
from pprint import pprint


class RoomTemplateAPI(GameAuthApi):

    async def _before_create_room(self, creator, price, club_id, u_info, rule_details):
        """创建游戏房间前的预处理"""
        # 是否已有创建房间
        room, e = await GameRoomsRC.get_game_rooms_by_filter(creator=creator)
        if room:
            return self.answer(StaCode.FAIL, data=room, hint="已有创建房间")
        # 茶馆房间特殊处理
        if club_id and club_id > 0:
            # 校验茶馆成员身份
            club_user, e = await ClubUsersRC.check_club_user(creator, club_id)
            if not club_user:
                return self.answer(StaCode.FAIL, hint=e)
            # 权限&规则校验
            club = await BaseClubRC.cache_session_get(club_id)
            club = json_parse(club)
            if club['uid'] != creator and club['other'].get("host_power_room") in [0, 2]:
                return self.answer(StaCode.FAIL, hint="无法创建房间")
            if club['other'].get("pay_type") == 1 and u_info.get("room_card") < price:
                return self.answer(StaCode.FAIL, hint="房卡不足")
            if club['other'].get("pay_type") == 2 and club["room_card"] < price:
                return self.answer(StaCode.FAIL, hint="茶馆基金不足")
        else:
            if rule_details.get("pay_type") == 1:
                if u_info.get("room_card") < price:
                    return self.answer(StaCode.FAIL, hint="房卡不足")
        return True

    async def _check_rule_detail(self, rule_details):
        """游侠房间规则校验"""
        for k in GameRoomsRC.RULE_DETAILS:
            BaseDecorator.check_inner(
                val=rule_details.get(k),
                require=True,
                inner_list=GameRoomsRC.oriupper(k),
                p_name=k
            )


class CreateRoomTemplate(GameAuthApi):
    """创建房间（支持普通房间和茶馆房间）"""
    async def post(self, req: Request, **kwargs):
        # 公共参数
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        platform = BaseDecorator.check_inner(val=req.json.get("platform"), require=True, inner_list=PlatForm, p_name="平台")
        game_type = self.check_int(req.json.get("game_type"), require=True, p_name="游戏类型")
        play_type = self.check_int(req.json.get("play_type"), require=True, p_name="玩法类型")
        club_id = self.check_int(req.json.get("club_id"), require=True, p_name="茶馆ID")
        max_player = self.check_int(req.json.get("max_player"), require=True, p_name="最大人数")
        rule_details = self.check_str(req.json.get("rule_details"), require=True, p_name="规则详情")
        total_round = self.check_int(req.json.get("total_round"), require=True, p_name="总局数")
        price = self.check_int(req.json.get("price"), require=True, p_name="支付金额")
        # 预处理
        await self._check_rule_detail(rule_details)

        # 创建房间
        new, err = await ClubRoomTemplatesRC.create_template(
            platform=platform,
            game_type=game_type,
            play_type=play_type,
            price=price,
            total_round=total_round,
            max_player=max_player,
            rule_details=rule_details,
            club_id=club_id
        )
        if not new:
            return self.answer(StaCode.FAIL, hint=err)

        return self.answer(data={"template_id": new})


class RoomList(GameAuthApi):
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


class JoinRoom(GameAuthApi):
    """加入房间"""
    async def post(self, req: Request, **kwargs):
        room_id = req.json.get("room_id")
        self.check_int(room_id, require=True, p_name="房间ID")
        u_info = kwargs.get("u_info")
        room_data, e = await GameRoomsRC.get_game_room_by_room_id(room_id)
        if not room_data:
            return self.answer(StaCode.FAIL, hint=e)
        if room_data.rule_details.get("pay_type") == 1:
            if u_info.get("room_card") < room_data['price']:
                return self.answer(StaCode.FAIL, hint="房卡不足")
        uid = u_info.get("uid")
        sta, e = await GameRoomsRC.join_room(room_data, uid)
        if sta is False:
            return self.answer(StaCode.FAIL, hint=e)
        cs_enum = ServiceEnum.find_member_by_val(room_data['cs_type'])
        await self.cs2cs_by_rmq(
            cs_enum,
            CmdRoom.ENTER_ROOM,
            room_data,
            uid,
        )
        return self.answer()


class LeaveRoom(GameAuthApi):
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


class DismissRoom(GameAuthApi):
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
