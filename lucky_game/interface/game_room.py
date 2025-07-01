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
from c_services.const.cs_enum_const import CmdRoom, RoomStatus, CmdNotice
from lucky_game.interface.club_room_template import RoomTemplateBase, verify_rule_detail
from common.public.conf import C_SERVICE_SECRET_KEY
from c_services.base.base_server import BaseServer
from common.public.common_class import CommonApi
from common.proto.py_pb2.ws_base import PbWsBaseRep
from common.proto.py_pb2.ws_client import S2CAgainRoomInfo


async def make_again_room_msg(room_data):
    """生成再来一局房间消息"""
    data = S2CAgainRoomInfo.pb_model(
        room_id=room_data["room_id"],
        play_type=room_data["play_type"],
        cs_type=room_data["cs_type"],
        creator=room_data["creator"],
        status=room_data["status"],
        total_round=room_data["total_round"],
        max_player=room_data["max_player"],
        rule_details=room_data["rule_details"],
    )
    return data


class GameRoomAPI(RoomTemplateBase):

    async def _before_create_room(self, creator, price, club_id, u_info, rule_details):
        """创建游戏房间前的预处理"""
        # 是否已有创建房间
        cs_info = await self.conf.rds.get_hash(CacheKey.IN_SERVICE, u_info.get("uid"), jsparse=True)
        if cs_info:
            self.answer(self.sta_code.FAIL, data=cs_info, hint="已有在游戏房间")
        # 茶馆房间特殊处理
        if club_id and club_id > 0:
            # 校验茶馆成员身份信息
            club_user, e = await ClubUsersRC.get_club_user_by_one(creator, club_id)
            if not club_user or club_user.status == ClubUsersRC.STATUS_BLACK:
                return self.answer(StaCode.FAIL, hint=e)
            # 权限&规则校验
            club, _ = await BaseClubRC.get_club_by_id(club_id)
            club = json_parse(club)
            # 茶馆创建房间配置权限校验
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

    async def again_mq(self, again_uid, room_data):
        """再来一局WS消息通知"""
        u_ids = await self.json_by_dict(again_uid)
        if u_ids:
            msg = await make_again_room_msg(room_data)
            for uid in u_ids:
                await self.send_msg_to_player(
                    ServiceEnum.C_NOTICE,
                    c_code=CmdNotice.INVITE_ROOM,
                    uid=uid,
                    hint='再来一局',
                    msg=msg,
                )


class CreateRoom(GameRoomAPI):
    """创建房间（支持普通房间和茶馆房间）"""
    async def post(self, req: Request, **kwargs):
        u_info = kwargs.get("u_info")
        creator = u_info.get("uid")
        template_id = self.check_int(req.json.get("template_id"), require=False, p_name="模板ID")
        is_location = self.check_int(req.json.get("is_location"), require=True, p_name="是否开启位置")
        is_friend = self.check_int(req.json.get("is_friend"), require=True, p_name="是否开启位置")
        again = self.check_int(req.json.get("again"), require=False, minval=0, maxval=1, p_name="开启再来一局")
        again_uid = self.check_str(req.json.get("again_uid"), require=False, p_name="再来一局玩家ID")
        if template_id:
            platform, play_type, club_id, max_player, rule_details, total_round, price, cs_type = await self.room_clone(template_id, creator, **kwargs)
            club, _ = await BaseClubRC.get_club_by_id(club_id)
            pay_type = club["other"]["pay_type"]
        else:
            platform, play_type, club_id, max_player, rule_details, total_round, price, cs_type = await self.verify_params(req, **kwargs)
            pay_type = self.check_int(req.json.get("pay_type"), require=True, p_name="支付方式")
        # 预处理
        rule_details = await verify_rule_detail(rule_details)
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
        if again == 1 and again_uid:
            print("再来一局")
            print("again->:", again)
            print("again_uid->:", again_uid)
            await self.again_mq(again_uid, room_data)
        return self.answer(data=room_data)


class RoomList(GameRoomAPI):
    """房间列表（合并模板和现有房间）"""
    async def get(self, req: Request, **kwargs):
        uid = kwargs.get("u_info").get("uid")
        club_id = self.check_int(req.args.get("club_id"), require=False, default=None, p_name="茶馆ID")
        status = self.check_int(req.args.get("status"), minval=0, maxval=6, require=False, default=None, p_name="房间状态")
        if status is None:
            status = [RoomStatus.T_IDLE, RoomStatus.T_READY, RoomStatus.T_PLAYING]
        not_rooms = await GameRoomsRC.before_room(club_id, uid)
        room_list, e = await GameRoomsRC.get_game_rooms_by_filter(club_id=club_id, status=status, not_room_id=not_rooms)
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
        if not room_data or room_data["status"] not in [RoomStatus.T_IDLE, RoomStatus.T_READY]:
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
            CmdRoom.NEW_MATCH,
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


