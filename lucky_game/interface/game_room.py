"""
游戏房间接口
"""
from sanic import Request
from common.public.enum_const import StaCode, ServiceEnum, CacheKey
from nsanic.libs.tool import json_encode, json_parse
from lucky_game.model_rc.game_rooms import GameRoomsRC
from lucky_game.model_rc.club_room_templates import ClubRoomTemplatesRC
from lucky_game.model_rc.club_users import ClubUsersRC
from lucky_game.model_rc.base_clubs import BaseClubRC
from c_services.const.cs_enum_const import CmdRoom
from lucky_game.interface.club_room_template import RoomTemplateBase
from lucky_game.model_rc.club_group import ClubGroupRC
from common.public.conf import C_SERVICE_SECRET_KEY


class GameRoomAPI(RoomTemplateBase):

    async def _before_create_room(self, creator, price, club_id, u_info, rule_details):
        """创建游戏房间前的预处理"""
        # 是否已有创建房间
        cs_info = await self.conf.rds.get_hash(CacheKey.IN_SERVICE, u_info.get("uid"), jsparse=True)
        if cs_info:
            self.answer(self.sta_code.FAIL, data=cs_info, hint="已有在游戏房间")
        # 茶馆房间特殊处理
        if club_id and club_id > 0:
            # 校验茶馆成员身份
            club_user, e = await ClubUsersRC.check_club_user(creator, club_id)
            if not club_user:
                return self.answer(StaCode.FAIL, hint=e)
            # 权限&规则校验
            club, _ = await BaseClubRC.get_club_by_id(club_id)
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

    async def room_clone(self, template_id, uid, **kwargs):
        """房间克隆"""
        template, e = await ClubRoomTemplatesRC.get_by_id(template_id)
        if not template:
            return self.answer(StaCode.FAIL, hint=e)
        platform = template.platform
        play_type = template.play_type
        club_id = template.club_id
        max_player = template.max_player
        price = template.price
        total_round = template.total_round
        rule_details = template.rule_details
        cs_type = template.cs_type
        return platform, play_type, club_id, max_player, rule_details, total_round, price, cs_type

    async def check_group(self, uid: int, club_id: int, room_id: int):
        """校验是否是有隔离成员"""
        # 当前房间存在的用户ID
        room_ids = await self.conf.rds.smembers(f"{GameRoomsRC.SESSION_DISK_KEY}:{room_id}")
        if room_ids:
            room_ids = await self.bytes_by_int_list(room_ids)
            for r_id in room_ids:
                sta, group_ids = await ClubGroupRC.check_group_by_uid(
                    uid=uid,
                    r_uid=r_id,
                    club_id=club_id,
                )
                if sta:
                    return True
        return False



class CreateRoom(GameRoomAPI):
    """创建房间（支持普通房间和茶馆房间）"""
    async def post(self, req: Request, **kwargs):
        u_info = kwargs.get("u_info")
        creator = u_info.get("uid")
        template_id = self.check_int(req.json.get("template_id"), require=False, p_name="模板ID")
        is_location = self.check_int(req.json.get("is_location"), require=True, p_name="是否开启位置")
        is_friend = self.check_int(req.json.get("is_friend"), require=True, p_name="是否开启位置")
        if not template_id:
            platform, play_type, club_id, max_player, rule_details, total_round, price, cs_type = await self.verify_params(req, **kwargs)
            pay_type = self.check_int(req.json.get("pay_type"), require=True, p_name="支付方式")
        else:
            platform, play_type, club_id, max_player, rule_details, total_round, price, cs_type = await self.room_clone(template_id, creator, **kwargs)
            club, _ = await BaseClubRC.get_club_by_id(club_id)
            pay_type = club["other"]["pay_type"]
        # 预处理
        rule_details = await self.verify_rule_detail(rule_details)
        await self._before_create_room(
            creator=creator,
            price=int(price),
            club_id=club_id,
            u_info=u_info,
            rule_details=rule_details
        )
        # 创建房间
        new_room, err = await GameRoomsRC.create_game_room(
            platform=platform,
            creator=creator,
            play_type=play_type,
            pay_type=pay_type,
            price=price,
            total_round=total_round,
            max_player=max_player,
            rule_details=rule_details,
            club_id=club_id,
            is_location=is_location,
            is_friend=is_friend,
            cs_type=cs_type,
            room_type=2,
        )
        if not new_room:
            return self.answer(StaCode.FAIL, hint=err)
        # 创建房间后直接加入
        room_data, _ = await GameRoomsRC.get_game_room_by_room_id(new_room)
        sta, e = await GameRoomsRC.join_room(room_data, creator)
        if sta is False:
            return self.answer(StaCode.FAIL, hint=e)
        cs_enum = ServiceEnum.find_member_by_val(cs_type)
        if not cs_enum:
            await GameRoomsRC.delete_game_room(new_room)
            return self.answer(StaCode.FAIL, hint="非法服务")
        room_data["secret"] = C_SERVICE_SECRET_KEY
        await self.cs2cs_by_rmq(
            cs_enum,
            CmdRoom.NEW_MATCH,
            room_data,
            creator,
        )
        return self.answer(data=room_data)


class RoomList(GameRoomAPI):
    """房间列表（合并模板和现有房间）"""
    async def get(self, req: Request):
        club_id = req.args.get("club_id", 0)
        room_list, e = await GameRoomsRC.get_game_rooms_by_filter(club_id=club_id)
        if isinstance(room_list, list):
            for room in room_list:
                user_uids, _ = await GameRoomsRC.get_room_player(room["room_id"])
                room["seats"] = user_uids if user_uids else []
        return self.answer(data=room_list)


class JoinRoom(GameRoomAPI):
    """加入房间"""
    async def post(self, req: Request, **kwargs):
        room_id = self.check_int(req.json.get("room_id"), require=True, p_name="房间ID")
        u_info = kwargs.get("u_info")
        room_data, e = await GameRoomsRC.get_game_room_by_room_id(room_id)
        if not room_data:
            return self.answer(StaCode.FAIL, hint=e)
        if room_data["pay_type"] == 1:
            if u_info.get("room_card") < room_data['price']:
                return self.answer(StaCode.FAIL, hint="房卡不足")
        uid = u_info.get("uid")
        sta, e = await GameRoomsRC.join_room(room_data, uid)
        if sta is False:
            return self.answer(StaCode.FAIL, hint=e)
        cs_enum = ServiceEnum.find_member_by_val(room_data['cs_type'])
        room_data["secret"] = C_SERVICE_SECRET_KEY
        await self.cs2cs_by_rmq(
            cs_enum,
            CmdRoom.ENTER_ROOM,
            room_data,
            uid,
        )
        return self.answer(data=room_data)


class LeaveRoom(GameRoomAPI):
    """离开、解散房间(主动)"""
    async def post(self, req: Request, **kwargs):
        room_id = self.check_int(req.json.get("room_id"), require=True, p_name="房间ID")
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        # 更新房间信息
        sta, e = await GameRoomsRC.leave_room(room_id, uid)
        if sta is False:
            return self.answer(StaCode.FAIL, hint=e)
        return self.answer()


class DismissRoom(GameRoomAPI):
    """解散房间(被动)"""
    async def post(self, req: Request):
        room_ids = self.check_str(req.json.get("room_ids"), require=True, p_name="房间ID")
        room_ids = json_parse(room_ids)
        failed_ids = []
        for room_id in room_ids:
            sta, e = await GameRoomsRC.abnormal_room(room_id)
            if not sta:
                failed_ids.append(room_id)
                continue
        return self.answer(data={"failed_ids": failed_ids})


