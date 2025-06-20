"""
茶馆
"""
from sanic import Request
from lucky_game.base_api import GameAuthApi
from common.public.enum_const import StaCode
from lucky_game.model_rc.base_clubs import BaseClubRC
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.model_rc.game_rooms import GameRoomsRC
from lucky_game.model_rc.club_users import ClubUsersRC
from lucky_game.model_rc.club_room_templates import ClubRoomTemplatesRC
from lucky_game.model_rc.extra_club_behavior import ExtraClubBehaviorRC
from nsanic.libs.tool import json_encode, json_parse
from c_services.const.cs_enum_const import RoomStatus


class BaseClub(GameAuthApi):
    async def check_solid_params(self, req: Request):
        """ 检查固有参数 """
        pass


class ClubCreate(BaseClub):
    """创建茶馆"""
    async def post(self, req: Request, **kwargs):
        # 参数校验
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        name = self.check_str(req.json.get("name"), require=True, minlen=2, maxlen=10, p_name="茶馆名称")
        has = self.conf.sw.contain_sensitive_words(name)
        if has:
            return self.answer(StaCode.FAIL, hint="茶馆名包含敏感词")
        room_card = u_info.get("room_card")
        if room_card < BaseClubRC.KEY_CLUB_CARD_LIMIT:
            return self.answer(StaCode.FAIL, hint="房卡不足")
        club = await BaseClubRC.db_model.get_or_none(name=name)
        if club:
            return self.answer(StaCode.FAIL, hint="茶馆名已存在")
        new, e = await BaseClubRC.create_club(name, uid, room_card)
        if not new:
            return self.answer(StaCode.FAIL, hint=e)
        return self.answer(data={"club_id": new.id})


class UpdateClub(BaseClub):
    """更新茶馆信息"""
    async def post(self, req: Request, **kwargs):
        # 参数校验
        uid = kwargs.get("u_info").get("uid")
        club_id = self.check_int(req.json.get("club_id"), require=True, p_name="茶馆ID")
        name = self.check_str(req.json.get("name"), require=True, minlen=2, maxlen=10, p_name="茶馆名称")



class ClubList(BaseClub):
    """获取茶馆列表"""
    async def get(self, req: Request, **kwargs):
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        result, e = await BaseClubRC.get_club_by_uid(uid)
        if result is False:
            return self.answer(StaCode.FAIL, hint=e)
        return self.answer(data=result)


class ClubHall(BaseClub):
    """茶馆大厅"""
    async def get(self, req: Request, **kwargs):
        club_id = self.check_int(req.args.get("club_id"), require=True, p_name="茶馆ID")
        status = self.check_int(req.args.get("status"), minval=0, maxval=6, require=False, p_name="房间状态")
        if status is None:
            status = [RoomStatus.T_IDLE, RoomStatus.T_READY, RoomStatus.T_PLAYING]
        # 玩法模板
        templates, e = await ClubRoomTemplatesRC.get_by_club(club_id=club_id)
        # 游戏房间
        room_list, e = await GameRoomsRC.get_game_rooms_by_filter(
            club_id=club_id,
            status=status,
        )
        # 玩法模板和游戏房间列表合并
        result = []
        if isinstance(templates, list):
            result.extend(templates)
        if isinstance(room_list, list):
            for room in room_list:
                user_uids, _ = await GameRoomsRC.get_room_player(room["room_id"])
                room["seats"] = user_uids if user_uids else []
            result.extend(room_list)
        return self.answer(data=result)


class ClubSearch(BaseClub):
    """茶馆搜索"""
    async def get(self, req: Request, **kwargs):
        # 获取请求参数
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        club_id = req.args.get("club_id")
        self.check_int(club_id, require=True, p_name="茶馆ID")
        # 从数据库查询茶馆信息
        club, e = await BaseClubRC.get_club_by_id(club_id)
        if club is None:
            return self.answer(hint=e)
        # 茶馆和用户关系
        club_user, e = await ClubUsersRC.get_club_user_by_one(uid, club_id)
        data = {"club": club, "join_status": 0}
        if club_user:
            data["join_status"] = 1
        return self.answer(data=data)


class ClubCheckList(BaseClub):
    """茶馆审批列表"""
    async def get(self, req: Request, **kwargs):
        # 获取请求参数
        u_info = kwargs.get("u_info")
        check_uid = u_info.get("uid")
        # 获取用户管理的茶馆
        club_ids, e = await ClubUsersRC.get_club_user_by_uid_club_ids(check_uid, [1, 9])
        data = []
        if club_ids:
            data, e = await ExtraClubBehaviorRC.get_behavior_by_filter(
                type=ExtraClubBehaviorRC.BEHAVIOR_APPLY_INDEX,
                club_id=club_ids,
                status=ExtraClubBehaviorRC.BEHAVIOR_STATUS_DEFAULT
            )
            if data is False:
                return self.answer(StaCode.FAIL, hint=e)
            # 查询茶馆信信
            for item in data:
                club, e = await BaseClubRC.get_club_by_id(item["club_id"])
                item["club"] = json_parse(club)
        return self.answer(data=data)


class ClubCheck(BaseClub):
    """茶馆审批"""
    async def post(self, req: Request, **kwargs):
        # 获取请求参数
        u_info = kwargs.get("u_info")
        check_uid = u_info.get("uid")
        behavior_id = req.json.get("behavior_id")
        status = req.json.get("status")
        self.check_int(behavior_id, require=True, p_name="申请行为ID")
        self.check_int(status, require=True, p_name="审批状态")
        # TODO 管理员校验 测试暂不加
        sta, e = await ExtraClubBehaviorRC.update_club_behavior(behavior_id, {"status": status, "check_uid": check_uid})
        if not sta:
            return self.answer(StaCode.FAIL, hint=e)
        return self.answer()


class ClubApply(BaseClub):
    """茶馆申请"""
    async def post(self, req: Request, **kwargs):
        # 获取请求参数
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        club_id = req.json.get("club_id")
        self.check_int(club_id, require=True, p_name="茶馆ID")
        # 校验是否已申请
        has, e = await ExtraClubBehaviorRC.get_behavior_by_filter(type=ExtraClubBehaviorRC.BEHAVIOR_APPLY_INDEX, uid=uid, club_id=club_id, status=ExtraClubBehaviorRC.BEHAVIOR_STATUS_DEFAULT)
        if not has:
            sta, e = await ExtraClubBehaviorRC.create_club_behavior(ExtraClubBehaviorRC.BEHAVIOR_APPLY_INDEX, uid, club_id)
            if not sta:
                return self.answer(StaCode.FAIL, hint=e)
        return self.answer()


class ClubApplyList(BaseClub):
    """茶馆申请列表"""

    async def get(self, req: Request, **kwargs):
        # 获取请求参数
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        data, e = await ExtraClubBehaviorRC.get_behavior_by_filter(
            type=ExtraClubBehaviorRC.BEHAVIOR_APPLY_INDEX,
            uid=uid,
            status=ExtraClubBehaviorRC.BEHAVIOR_STATUS_DEFAULT
        )
        if data is False:
            return self.answer(StaCode.FAIL, hint=e)
        # 查询茶馆信信
        for item in data:
            club, e = await BaseClubRC.get_club_by_id(item["club_id"])
            item["club"] = json_parse(club)
        return self.answer(data=data)


class ClubUserInfo(BaseClub):
    """茶馆用户信息"""
    async def get(self, req: Request, **kwargs):
        # 获取请求参数
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        club_id = req.args.get("club_id")
        self.check_int(club_id, require=True, p_name="茶馆ID")
        data, e = await ClubUsersRC.get_club_user_by_one(uid, club_id)
        if not data:
            return self.answer(StaCode.FAIL, hint=e)
        return self.answer(data=data)


class ClubLeave(BaseClub):
    """离开茶馆"""
    async def post(self, req: Request, **kwargs):
        pass

