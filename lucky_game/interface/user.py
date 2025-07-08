from sanic import Request
from common.utils import tool_certification
from lucky_game.base_api import GameAuthApi
from lucky_game.handler.decorator import GameChecker, CurrentLimiting, LimitTestCall
from lucky_game.model_rc.base_user import BaseUserRC
from common.utils.utils import UtilsTool
from lucky_game.model_rc.extra_user_resource_changes import ExtraUserResourceChangesRC


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
        data = await BaseUserRC.cache_by_uid(uid)
        return self.answer(data=data)


class UpdateUserInfo(GameAuthApi):
    """ 更新用户信息 """

    async def post(self, req: Request, **kwargs):
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        name = self.check_str(req.json.get("name"), require=False, p_name="玩家昵称")
        avatar = self.check_str(req.json.get("avatar"), require=False, p_name="头像地址")
        sex = self.check_int(req.json.get("sex"), minval=0, maxval=2, require=False, p_name="性别")
        phone = self.check_phone_number(req.json.get("phone"), require=False, p_name="手机号码")
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
        data = await BaseUserRC.update_info(uid, new_data)
        return self.answer(data=data)

class Certification(BaseUserInfo):
    """ 实名认证 """
    decorators = [CurrentLimiting, GameChecker]

    async def post(self, req, **kwargs):
        id_card = self.check_str(req.json.get("id_card"), require=True, minlen=18, maxlen=18, p_name="id_card")
        real_name = self.check_str(req.json.get("real_name"), require=True, minlen=2, p_name="real_name")
        res = UtilsTool.check_id_card(id_card)
        not res and self.answer(self.sta_code.ERR_ARG, hint='请检查身份证合法性')
        res = UtilsTool.validate_name(real_name)
        not res and self.answer(self.sta_code.ERR_ARG, hint='姓名错误')
        u_info = kwargs.get("u_info") or {}
        if u_info.get("id_card"):
            self.answer(self.sta_code.HAD_CERTIFICATED)

        status, result = await tool_certification.do_shi_ming_check(real_name, id_card, u_info.get("uid"))
        self.log_info("实名结果：", result)
        if not status:
            self.answer(code=self.sta_code.EXTERNAL_ERR, data=result)

        pi = result.get('data').get('result').get('pi')
        sex = UtilsTool.determine_gender(id_card)
        new_info = {
            "sex": sex,
            "id_card": id_card,
            "real_name": real_name,
        }
        if pi:
            new_info["pi"] = pi
        p_info = await BaseUserRC.update_info(u_info, new_info)
        return self.format_response_info(p_info)


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
            explain
        )
        if not sta:
            return self.answer(code=self.sta_code.FAIL, hint=e)
        p_info = await BaseUserRC.cache_by_pk(uid)
        return self.format_response_info(p_info)
