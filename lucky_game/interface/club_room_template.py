"""
游戏房间接口
"""
from sanic import Request
from lucky_game.base_api import GameAuthApi
from common.public.enum_const import StaCode
from lucky_game.model_rc.game_rooms import GameRoomsRC
from lucky_game.model_rc.club_room_templates import ClubRoomTemplatesRC
from lucky_game.model_rc.club_users import ClubUsersRC
from lucky_game.handler.decorator import BaseDecorator
from common.public.common_class import CommonApi


async def verify_rule_detail(rule_details) -> dict:
    """游侠房间规则校验"""
    rule = await CommonApi.json_by_dict(rule_details)
    decorator = BaseDecorator(None)
    for k, v in GameRoomsRC.RULE_DETAILS.items():
        await decorator.check_inner(
            val=rule.get(k),
            require=True,
            inner_dick=v,
            p_name=k
        )
    return rule


class RoomTemplateBase(GameAuthApi):

    async def verify_params(self, req: Request, **kwargs):
        """游戏房间常规参数校验"""
        platform = self.check_int(req.args.get("platform"), require=True, minval=1, maxval=3, p_name="平台")
        cs_type = self.check_int(req.json.get("cs_type"), require=True, p_name="子服务类型")
        play_type = self.check_int(req.json.get("play_type"), require=True, p_name="玩法类型")
        club_id = self.check_int(req.json.get("club_id"), minval=100000, require=True, p_name="茶馆ID")
        max_player = self.check_int(req.json.get("max_player"), require=True, p_name="最大人数")
        rule_details = self.check_str(req.json.get("rule_details"), require=True, p_name="规则详情")
        total_round = self.check_int(req.json.get("total_round"), require=True, p_name="总局数")
        price = self.check_int(req.json.get("price"), require=True, p_name="支付金额")
        return platform, play_type, club_id, max_player, rule_details, total_round, price, cs_type
    
    async def check_authority(self, uid, club_id):
        """校验权限"""
        club_user, e = await ClubUsersRC.get_club_user_by_one(uid, club_id)
        if not club_user:
            return self.answer(StaCode.FAIL, hint=e)
        if club_user["status"] != ClubUsersRC.STATUS_NORMAL or club_user["role"] not in [ClubUsersRC.ROLE_MANAGE,
                                                                                         ClubUsersRC.ROLE_HOST]:
            return self.answer(StaCode.FAIL, hint="暂无权限")
        return True


class RoomTemplateCreate(RoomTemplateBase):
    """房间模板创建"""
    async def post(self, req: Request, **kwargs):
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        platform, play_type, club_id, max_player, rule_details, total_round, price, cs_type = await self.verify_params(req, **kwargs)
        rule_dick = await verify_rule_detail(rule_details)
        await self.check_authority(uid, club_id)
        # 创建模板
        new, err = await ClubRoomTemplatesRC.create_template(
            platform=platform,
            play_type=play_type,
            cs_type=cs_type,
            price=price,
            total_round=total_round,
            max_player=max_player,
            rule_details=rule_dick,
            club_id=club_id,
        )
        if not new:
            return self.answer(StaCode.FAIL, hint=err)
        return self.answer(data={"template_id": new})


class RoomTemplateUpdate(RoomTemplateBase):
    """房间模板更新"""
    async def post(self, req: Request, **kwargs):
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        template_id = self.check_int(req.json.get("template_id"), require=True, p_name="模板ID")
        platform, play_type, club_id, max_player, rule_details, total_round, price, cs_type = await self.verify_params(req, **kwargs)
        await self.check_authority(uid, club_id)
        rule_dick = await verify_rule_detail(rule_details)
        new, err = await ClubRoomTemplatesRC.update_template(
            template_id=template_id,
            play_type=play_type,
            cs_type=cs_type,
            price=price,
            total_round=total_round,
            max_player=max_player,
            rule_details=rule_dick,
        )
        if not new:
            return self.answer(StaCode.FAIL, hint=err)
        return self.answer()

class RoomTemplateList(RoomTemplateBase):
    """房间模板列表"""
    async def get(self, req: Request, **kwargs):
        club_id = self.check_int(req.args.get("club_id", 0), minval=100000, require=False, p_name="茶馆ID")
        if club_id == 0:
            u_info = kwargs.get("u_info")
            uid = u_info.get("uid")
            club_user, e = await ClubUsersRC.get_club_user_by_uid(uid)
            if club_user is False:
                return self.answer(StaCode.FAIL, hint=e)
            club_id = club_user.club_id

        # 获取模板和房间
        templates, _ = await ClubRoomTemplatesRC.get_by_club(club_id)
        return self.answer(data=templates)


class RoomTemplateDelete(RoomTemplateBase):
    """移除房间模板"""
    async def post(self, req: Request, **kwargs):
        template_id = self.check_int(req.json.get("template_id"), require=True, p_name="房间模板ID")
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        # 查询所属茶馆
        template, e = await ClubRoomTemplatesRC.get_by_id(template_id)
        if template is None:
            return self.answer(StaCode.FAIL, hint=e)
        club_id = template.club_id
        await self.check_authority(uid, club_id)
        sta, e = await ClubRoomTemplatesRC.delete_template(template_id, club_id)
        if not sta:
            return self.answer(StaCode.FAIL, hint=e)
        return self.answer()
