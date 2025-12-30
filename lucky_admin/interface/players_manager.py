"""
玩家管理
"""
from nsanic import verify
from sanic import Request

from c_services.const.cs_enum_const import CmdRoom
from common.public.conf import R_UID_THRESHOLD, C_SERVICE_SECRET_KEY
from common.public.enum_const import ServiceEnum
from common.utils.utils import UtilsTool
from lucky_admin.base_api import AdminAuthApi
from lucky_game.model_db.main import RecordsAdminOperates, Admins
from lucky_admin.model_rc.base_admin import BaseAdminRC
from lucky_game.model_rc.base_ranking import UserRankingRC
from lucky_game.model_rc.base_user import BaseUserRC


class PlayerHandler(AdminAuthApi):
    async def get(self, req: Request, **_b):
        uid = self.check_int(req.args.get('uid'), require=True, minval=R_UID_THRESHOLD + 1, p_name='uid')
        u_info = await BaseUserRC.cache_by_uid(uid)
        if not u_info:
            self.answer(hint="没有该玩家信息")
        self.answer(data=u_info)


class OperatesRecordsHandler(AdminAuthApi):
    async def get(self, req: Request, **kwargs):
        # u_info = kwargs.get('u_info')
        username = self.check_str(req.args.get('username'))
        query_p = {}
        if username:
            query_p["username"] = username

        # sql = "SELECT COUNT(*) FROM {} WHERE username='{}'".format(RecordsAdminOperates.sheet_name(), username)
        timestamp = req.args.get('timestamp')
        if timestamp:
            timestamp = self.check_int(timestamp, require=True, minval=0, p_name='timestamp')
            query_p['created__gte'] = timestamp
            # sql += " AND created >= {}".format(timestamp)

        route = req.args.get('route')
        if route:
            route = self.check_str(route, require=True, p_name='route')
            query_p['route'] = route

        count = await RecordsAdminOperates.filter(**query_p).count()
        limit = 10
        page = self.check_int(req.args.get('page'), require=True, minval=1, p_name='page')
        offset = (page - 1) * limit
        data = await RecordsAdminOperates.get_by_dict(query_p, limit=limit, offset=offset)
        data = {
            'count': count,
            'records': data
        }
        self.answer(data=data)


class PlayerRankingHandler(AdminAuthApi):
    """ 玩家修为处理 """

    async def post(self, req: Request, **_):
        """ 修改修为 """
        uid = self.check_int(req.json.get('uid'), require=True, minval=R_UID_THRESHOLD + 1, p_name='uid')
        score = self.check_int(req.json.get('score'), require=True, p_name='score')
        if score == 0:
            self.answer(hint='ok')

        await UserRankingRC.update_user_ranking_score(uid, score)
        self.answer(hint='ok')


class ModifyPassword(AdminAuthApi):
    async def put(self, req: Request, **kwargs):
        """ 修改 """
        password = req.json.get("password")
        new_password = req.json.get("new_password")
        if password == new_password:
            self.answer(self.sta_code.FAIL, hint='新旧密码一样，请重新输入')

        u_info = kwargs.get("u_info")
        password = self.check_str(password, require=True, minlen=6, maxlen=28)
        encrypt_pass = UtilsTool.get_hash_secrets(self.conf.SERVER_SECRET_KEY, password, secrets_type='sha256')
        if encrypt_pass != u_info.get('password'):
            self.answer(self.sta_code.FAIL, hint='密码错误')

        flag, msg = verify.password(new_password, len_min=6, len_max=20, qc=3)
        if not flag:
            self.answer(self.sta_code.FAIL, hint=msg)

        new_password = UtilsTool.get_hash_secrets(self.conf.SERVER_SECRET_KEY, new_password, secrets_type='sha256')

        await BaseAdminRC.update_info(u_info.get("id"), u_info, {"password": new_password})

        self.answer(hint='ok')


class RoomPlayerHandler(AdminAuthApi):
    """ 房间玩家处理 """

    async def post(self, req: Request, **_b):
        cs_type = req.json.get("cs_type")
        cs_type = self.check_int(cs_type, minval=ServiceEnum.C_MONSTER.val, require=True, p_name='cs_type(服务类型)')
        cs_enum = ServiceEnum.find_member_by_val(cs_type)
        if not cs_enum:
            self.answer(code=self.sta_code.FAIL, hint="服务错误")
        uid = self.check_int(req.json.get("uid"), require=True, minval=R_UID_THRESHOLD+1, p_name='uid')

        data = {
            "secret": C_SERVICE_SECRET_KEY
        }
        await self.cs2cs_by_rmq(cs_enum, CmdRoom.FORCE_DISMISS, data, uid)
        self.answer(hint='ok')
