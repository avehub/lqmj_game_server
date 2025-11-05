from nsanic.libs import tool_jwt, tool_dt
from sanic import Request
from common.public.enum_const import JWType
from lucky_admin.base_api import AdminAuthApi
from lucky_admin.const import AdminPermission
from lucky_admin.model_rc.base_admin import BaseAdminRC
from common.utils.utils import UtilsTool


class UserList(AdminAuthApi):
    """ 用户列表 """

    async def get(self, req: Request):

        data = {}
        return self.answer(data=data)


class User(AdminAuthApi):

    async def get(self, req: Request):
        """ 用户详情 """
        data = {}
        return self.answer(data=data)


    async def put(self, req: Request):
        """ 更新用户信息 """
        data = {}
        return self.answer(data=data)

class UserStatus(AdminAuthApi):
    """ 用户状态 """

    async def get(self, req: Request):
        data = {}
        return self.answer(data=data)


class OrderList(AdminAuthApi):
    """ 充值记录 """

    async def get(self, req: Request):
        data = {}
        return self.answer(data=data)


class OrderStatistics(AdminAuthApi):
    """ 充值统计 """

    async def get(self, req: Request):
        data = {}
        return self.answer(data=data)


class ResourceChanges(AdminAuthApi):
    """ 资产流水 """

    async def get(self, req: Request):
        data = {}
        return self.answer(data=data)