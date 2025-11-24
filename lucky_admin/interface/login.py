from nsanic.libs import tool_jwt, tool_dt
from sanic import Request
from common.public.enum_const import JWType
from lucky_admin.base_api import AdminAuthApi
from lucky_admin.const import AdminPermission
from lucky_admin.model_rc.base_admin import BaseAdminRC
from common.utils.utils import UtilsTool


def refresh_token(u_info, jwt_type=JWType.MANAGER):
    """ 刷新token """
    safe_key = u_info.pop('safe_key')
    username = u_info.get('username')
    subject_info = f"{u_info.get('created')}_{username}"  # client_info
    token = tool_jwt.jencode(username, jwt_type, safe_key, subject_info, useful_life=jwt_type.desc)
    return token


class LoginByAccount(AdminAuthApi):
    """ 管理员登录 """

    decorators = []

    async def post(self, req: Request):
        username = req.json.get('username')
        username = self.check_str(username, require=True, minlen=5, maxlen=20, p_name='用户名')
        u_info = await BaseAdminRC.cache_by_unique({'username': username}, BaseAdminRC.KEY_USERNAME)
        if not u_info:
            self.answer(self.sta_code.FORBID, hint='非法用户')

        password = req.json.get('password')
        password = self.check_str(password, require=True, minlen=6, maxlen=28, p_name='密码')
        encrypt_pass = UtilsTool.get_hash_secrets(self.conf.SERVER_SECRET_KEY, password, secrets_type='sha256')
        if encrypt_pass != u_info.get('password'):
            self.answer(self.sta_code.FAIL, hint='密码错误，请更正！')

        # 同时1个账号只允许1人登录
        updated = {'safe_key': self.rng.mk_str(18)}
        u_info = await BaseAdminRC.update_info(u_info.get('id'), u_info, updated)
        token = refresh_token(u_info, JWType.MANAGER)
        self.answer(data={'token': token, 'permission': u_info.get('permission', AdminPermission.P1)})


class LoginByToken(AdminAuthApi):
    """ token等 """

    async def post(self, req: Request, **kwargs):
        jwt_info = kwargs.get("jwt_info")
        u_info = kwargs.get("u_info")
        if jwt_info.get('exp') - tool_dt.cur_time() <= 43200:
            # 有效期小于12小时则重新签发 60 * 60 * 12
            token = refresh_token(u_info, JWType.MANAGER)
        else:
            token = req.headers.get("Authorization")

        self.answer(data={'token': token})
