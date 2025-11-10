from nsanic.libs.tool import json_parse
from sanic import Request
from common.utils import tool_certification
from lucky_game.base_api import GameAuthApi, SpecialApi
from lucky_game.handler.decorator import GameChecker, CurrentLimiting, LimitTestCall
from lucky_game.model_rc.base_user import BaseUserRC
from common.utils.utils import UtilsTool
from lucky_game.model_rc.extra_user_resource_changes import ExtraUserResourceChangesRC
from lucky_game.const import RED_DOTS_OPPORTUNITY_MAP, ActivityItem, ReasonCostGold
from c_services.const.cs_enum_const import CmdWorkers, RedDotType
from common.public.conf import R_UID_THRESHOLD, ROBOT_AVATAR
from lucky_game.model_rc.base_robot import BaseRobotRC
from lucky_game.logic.activity import Base
from lucky_game.handler.wechat import WeChat


class BaseUserInfo(GameAuthApi):

    def format_response_info(self, user: dict):
        self.log_info("format_response_info:", user)
        return self.answer(data=user)


class UserInfo(GameAuthApi):
    """ 查询用户信息 """

    async def get(self, req: Request, **kwargs):
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        q_uid = self.check_int(req.args.get("uid"), require=False, p_name="uid")
        if q_uid:
            uid = q_uid
        if uid >= R_UID_THRESHOLD:
            data = await BaseUserRC.cache_by_uid(uid)
            # vip_info = await UserVipRC.get_vip_conf_by_uid(uid)
            # ur_data = await UserRankingRC.cache_by_unique(uid, u_info=user_info) or {}
            # r_user_model["vip_level"] = vip_info.get("level")
            # r_user_model["ranking_id"] = ur_data.get("ranking_id") or 0
        else:
            data = await BaseRobotRC.cache_by_pk(uid) or {}
            data["avatar"] = ROBOT_AVATAR + data.get("avatar", "/male/462.jpg")

        return self.answer(data=data)


class UpdateUserInfo(GameAuthApi):
    """ 更新用户信息 """

    async def post(self, req: Request, **kwargs):
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        name = self.check_str(req.json.get("name"), require=False, p_name="玩家昵称")
        avatar = self.check_str(req.json.get("avatar"), require=False, p_name="头像地址")
        sex = self.check_int(req.json.get("sex"), minval=0, maxval=2, require=False, p_name="性别")
        phone = self.check_phone_number(req.json.get("phone"), require=False)
        email = self.check_str(req.json.get("email"), require=False, p_name="邮箱")
        address = self.check_str(req.json.get("address"), require=False, p_name="所在地址")
        album = self.check_str(req.json.get("album"), require=False, p_name="相册")
        new_data = {}
        if name:
            new_data["name"] = name
        if avatar:
            new_data["avatar"] = avatar
        if sex:
            new_data["sex"] = sex
        if phone:
            new_data["phone"] = phone
        if email:
            new_data["email"] = email
        if address:
            new_data["address"] = address
        if album:
            new_data["album"] = album
        data = await BaseUserRC.update_info(u_info, new_data)
        return self.answer(data=data)

class Certification(BaseUserInfo):
    """ 实名认证 """
    decorators = [CurrentLimiting, GameChecker]

    async def post(self, req, **kwargs):
        id_card = self.check_str(req.json.get("id_card"), require=True, minlen=18, maxlen=18, p_name="证件号码")
        real_name = self.check_str(req.json.get("real_name"), require=True, minlen=2, p_name="证件姓名")
        res = UtilsTool.check_id_card(id_card)
        not res and self.answer(self.sta_code.ERR_ARG, hint='请检查身份证合法性')
        res = UtilsTool.validate_name(real_name)
        not res and self.answer(self.sta_code.ERR_ARG, hint='姓名错误')
        u_info = kwargs.get("u_info") or {}
        if u_info.get("pi"):
            self.answer(self.sta_code.HAD_CERTIFICATED)

        status, result = await tool_certification.do_shi_ming_check(real_name, id_card, u_info.get("uid"))
        self.log_info("实名结果：", "status", status, "result", result)
        if not status:
            self.answer(code=self.sta_code.EXTERNAL_ERR, data=result, hint="您填的身份信息不对哦，请检查再提交认证")
        sex = UtilsTool.determine_gender(id_card)
        new_info = {
            "sex": sex,
            "id_card": id_card,
            "real_name": real_name,
            "pi": result.get('pi'),
        }
        p_info = await BaseUserRC.update_info(u_info, new_info)
        return self.format_response_info(p_info)


class FetchRedDotsByOpportunity(GameAuthApi):
    """根据时机拉取红点"""

    async def get(self, req: Request, **kwargs):
        rd_enum = self.check_int(req.args.get("rd_enum"), require=True, p_name="rd_enum")
        # 1.批量获取红点（前端确定WS已经建立连接之后调用）
        # 该列表只能客户端在某些时机调用
        rd_type_list = RED_DOTS_OPPORTUNITY_MAP.get(rd_enum)
        if not rd_type_list:
            self.answer(hint="ok")

        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        cache_key = f"req_limit:{uid}:{req.server_path}:{rd_enum}"

        incr_value = await self.conf.rds.conn.incr(cache_key)
        await self.conf.rds.expired(cache_key, 60)  # 设置键过期时间

        if incr_value > 3:  # 60秒内只能调3次
            self.answer(code=self.sta_code.REQ_FREQUENT)

        await self.push_task2worker(CmdWorkers.GET_RED_DOT_LIST, msg={"rd_type_list": rd_type_list}, uid=uid)

        self.log_info(uid, '获取红点>>', rd_type_list)
        return self.answer(hint="OK!")


class UpdateUserResource(BaseUserInfo):
    """修改用户资源（调试用）"""
    decorators = [LimitTestCall, GameChecker]

    async def post(self, req, **kwargs):
        operation_values = await ExtraUserResourceChangesRC.change_operation()
        field_values = await ExtraUserResourceChangesRC.change_field()

        def is_valid_operation(x):
            return x in operation_values

        def is_valid_field(x):
            return x in field_values

        uid = kwargs.get("u_info").get("uid")
        operation = self.check_type(
            req.json.get("operation"),
            query_fun=is_valid_operation,
            require=True,
            is_int=False,
            p_name="operation"
        )
        change_field = self.check_type(
            req.json.get("change_field"),
            query_fun=is_valid_field,
            is_int=False,
            require=True,
            p_name="change_field"
        )
        change_val = self.check_int(req.json.get("change_val"), require=True, minval=0, p_name="change_val")
        explain = self.check_str(req.json.get("explain"), default='', require=False, p_name="explain")
        sta, e = await ExtraUserResourceChangesRC.change_user_resource(
            uid,
            change_field,
            change_val,
            operation,
            reason=ReasonCostGold.TEST_ADD
        )
        if not sta:
            return self.answer(code=self.sta_code.FAIL, hint=e)
        p_info = await BaseUserRC.cache_by_pk(uid)
        return self.format_response_info(p_info)

class WriteOff(GameAuthApi):
    """ 注销账号 """
    async def post(self, req: Request, **kwargs):
        u_info = kwargs.get("u_info")
        status = self.check_int(req.json.get("status"), require=True, minval=0, maxval=2, p_name="status")
        new_data = {"ban_time": status}
        data = await BaseUserRC.update_info(u_info, new_data)
        if not data:
            return self.answer(code=self.sta_code.FAIL)
        return self.answer()

class WebUpUserResource(SpecialApi):
    """ 网页更新用户资源 """
    async def post(self, req):
        operation_values = await ExtraUserResourceChangesRC.change_operation()
        field_values = await ExtraUserResourceChangesRC.change_field()
        def is_valid_operation(x):
            return x in operation_values
        def is_valid_field(x):
            return x in field_values
        uid = self.check_int(
            req.json.get("uid"),
            require=True,
            p_name="uid"
        )
        operation = self.check_type(
            req.json.get("operation"),
            query_fun=is_valid_operation,
            require=True,
            is_int=False,
            p_name="operation"
        )
        change_field = self.check_type(
            req.json.get("change_field"),
            query_fun=is_valid_field,
            is_int=False,
            require=True,
            p_name="change_field"
        )
        change_val = self.check_int(req.json.get("change_val"), require=True, minval=0, p_name="change_val")
        sta, e = await ExtraUserResourceChangesRC.change_user_resource(
            uid,
            change_field,
            change_val,
            operation,
            reason=ReasonCostGold.WECHAT_STORE_SHOPPING
        )
        if not sta:
            return self.answer(code=self.sta_code.FAIL, hint=e)
        p_info = await BaseUserRC.cache_by_pk(uid)
        return self.format_response_info(p_info)

class UpWechatUserInfo(GameAuthApi):
    """ 更新微信用户信息 """

    async def post(self, req: Request, **kwargs):
        uid = self.check_int(
            req.json.get("uid"),
            require=True,
            p_name="uid"
        )
        u_info = await BaseUserRC.cache_by_pk(uid)
        # 获取微信登录信息
        login_info = await BaseUserRC.get_wechat_access_token_info(uid)
        if not login_info:
            return self.answer(code=self.sta_code.FAIL, hint="用户登录信息已过期")
        # 检查access_token是否过期
        errcode, _ = await WeChat.wechat_check_access_token(login_info)
        if errcode == -1:
            # 过期，刷新access_token
            sta, data = await WeChat.wechat_refresh_access_token(uid, login_info)
            if sta != 0:
                return self.answer(code=self.sta_code.FAIL, hint="微信登录过期，请重新登录")
            login_info = data
        u_sta, u_data = await WeChat.wechat_userinfo(login_info.get("access_token"), login_info.get("openid"))
        if not u_sta:
            return self.answer(code=self.sta_code.FAIL, hint=u_data.get("errmsg", "更新用户信息失败"))
        new_data = {
            "nickname": u_data.get("nickname"),
            "avatar": u_data.get("headimgurl"),
            "sex": u_data.get("sex"),
        }
        data = await BaseUserRC.update_info(u_info, new_data)
        return self.answer(data=data)
