from nsanic.libs import tool_jwt
from sanic.request import Request
from common.public.enum_const import JWType
from promising_admin.const import AdminPermission
from promising_admin.model_rc.base_admin import BaseAdminRC
from promising_game.config import conf_srv, ConfSrv
from promising_game.handler.decorator import BaseDecorator


class AdminChecker(BaseDecorator):
    """ 后台检测器 """
    conf: ConfSrv = conf_srv

    def __init__(self, func):
        super().__init__(func)

    async def __call__(self, req: Request, *args, **kwargs):
        self.check_method(req)
        token = req.headers.get("Authorization") or (req.json and req.json.get("token")) or ""
        if not token:
            return self.answer(self.sta_code.FAIL, hint="Token error")
        # 1.获取载荷信息
        username, _ = tool_jwt.get_jwinfo(token)
        username = self.check_str(username, require=True, minlen=6, maxlen=20)
        u_info = await BaseAdminRC.cache_by_unique({'username': username}, BaseAdminRC.KEY_USERNAME)
        not u_info and self.answer(self.sta_code.FORBID, hint='非法用户')
        # 2.通过safe_key验签token合法性
        safe_key = u_info.get("safe_key")
        subject_info = f"{u_info.get('created')}_{username}"
        data, hint = tool_jwt.jdecode(token, JWType.MANAGER, safe_key, subject_info)
        (not data) and self.answer(self.sta_code.FAIL, hint=hint)

        if u_info.get("permission") == AdminPermission.P1:
            route = req.path.strip('/').split('/')[-1]
            if req.method != 'GET' and route != 'LoginByToken':
                self.answer(self.sta_code.FAIL, hint="权限不足，该操作不允许，请联系超级管理员~")

        kwargs.update({"u_info": u_info})
        kwargs.update({"jwt_info": data})
        return await self.call_method(req, *args, **kwargs)


def sensitive_data_handler(data: dict):
    """ 敏感数据处理 """
    if data.get("password"):
        data["password"] = "xxx"
    if data.get("new_password"):
        data["new_password"] = "xxx"


def filter_not_out_of_date_data(info_list, cur_time, exclude_status=0):
    filter_list = []
    update = False
    for info in info_list:
        end_time = info.get('end_time', 0)
        if cur_time > end_time:
            update = True
            continue
        if cur_time < info.get('start_time', 0):  # 还未开始
            continue
        if info.get('status') == exclude_status:
            continue
        filter_list.append(info)
    return filter_list, update
