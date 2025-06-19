"""
茶馆隔离相关接口
"""
from sanic import Request
from common.public.enum_const import StaCode
from datetime import datetime, timedelta
from lucky_game.base_api import GameAuthApi
from lucky_game.model_rc.club_group import ClubGroupRC
from lucky_game.model_rc.base_user import BaseUserRC
from nsanic.libs.tool import json_encode, json_parse


async def dict_u_ids(u_ids):
    if "'" in u_ids:
        str_ids = u_ids.replace("'", "\"")
    else:
        str_ids = u_ids
    return json_parse(str_ids)


class CreatGroup(GameAuthApi):
    """创建隔离组"""
    async def post(self, req: Request, **kwargs):
        uid = kwargs.get("u_info").get("uid")
        u_ids = self.check_str(req.json.get("u_ids"), require=True, p_name="被隔离用户ID")
        club_id = self.check_int(req.json.get("club_id"), require=True, p_name="茶馆ID")
        name = self.check_str(req.json.get("name"), maxlen=16, require=True, p_name="隔离组名")
        group, e = await ClubGroupRC.creat_club_group(
            uid=uid,
            u_ids=await dict_u_ids(u_ids),
            club_id=club_id,
            name=name,
        )
        if not group:
            return self.answer(StaCode.FAIL, hint=e)
        return self.answer(data={"gid": group.gid})


class UpdateGroup(GameAuthApi):
    """更新隔离组"""
    async def post(self, req: Request, **kwargs):
        uid = kwargs.get("u_info").get("uid")
        gid = self.check_int(req.json.get("gid"), require=True, p_name="隔离组ID")
        name = self.check_str(req.json.get("name"), maxlen=16, require=False, p_name="隔离组名")
        u_ids = self.check_str(req.json.get("u_ids"), require=False, p_name="被隔离用户ID")
        group, e = await ClubGroupRC.update_club_group(
            uid=uid,
            gid=gid,
            name=name,
            u_ids=await dict_u_ids(u_ids),
        )
        if not group:
            return self.answer(StaCode.FAIL, hint=e)
        return self.answer()


class GetGroup(GameAuthApi):
    """获取隔离组"""
    async def get(self, req: Request, **kwargs):
        uid = kwargs.get("u_info").get("uid")
        club_id = self.check_int(req.args.get("club_id"), require=False, p_name="茶馆ID")
        data, e = await ClubGroupRC.get_club_group_by_filter(
            club_id=club_id,
        )
        return self.answer(data=data, hint=e)


class DelGroup(GameAuthApi):
    """删除隔离组"""
    async def post(self, req: Request, **kwargs):
        uid = kwargs.get("u_info").get("uid")
        gid = self.check_int(req.json.get("gid"), require=True, p_name="隔离组ID")
        group, e = await ClubGroupRC.delete_group(gid)
        if not group:
            return self.answer(StaCode.FAIL, hint=e)
        return self.answer()
