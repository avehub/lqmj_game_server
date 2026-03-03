from nsanic.libs import tool_jwt, tool_dt
from nsanic.libs.tool import json_parse, json_encode
from sanic import Request
from common.public.enum_const import JWType
from lucky_admin.base_api import AdminAuthApi
from lucky_admin.const import AdminPermission
from lucky_game.model_rc.conf_json import ConfJsonRC
from common.utils.utils import UtilsTool

class Config(AdminAuthApi):
    """ 新增/更新/删除/查询 配置 """

    async def post(self, req: Request, **kwargs):
        conf_id = self.check_str(req.json.get('conf_id'), require=True, maxlen=128, p_name='配置名')
        desc = self.check_str(req.json.get('desc'), require=True, maxlen=255, p_name='描述')
        conf_data = self.check_str(req.json.get('conf_data'), require=True, p_name='具体配置')
        sta, data = await ConfJsonRC.create_conf(conf_id, conf_data, desc)
        if not sta:
            self.answer(self.sta_code.FAIL, hint='创建配置失败')

        self.answer(data=data)

    async def put(self, req: Request, **kwargs):
        conf_id = self.check_str(req.json.get('conf_id'), require=True, maxlen=128, p_name='配置名')
        desc = self.check_str(req.json.get('desc'), require=False, maxlen=255, p_name='描述')
        conf_data = self.check_str(req.json.get('conf_data'), require=False, p_name='具体配置')
        sta, data = await ConfJsonRC.update_conf(conf_id, conf_data=conf_data, desc=desc)
        if not sta:
            self.answer(self.sta_code.FAIL, hint='更新配置失败')
        self.answer()

    async def delete(self, req: Request, **kwargs):
        conf_id = self.check_str(req.json.get('conf_id'), require=True, p_name='配置名')
        sta, data = await ConfJsonRC.del_conf(conf_id)
        if not sta:
            self.answer(self.sta_code.FAIL, hint='删除配置失败')

        self.answer()

    async def get(self, req: Request, **kwargs):
        desc = self.check_str(req.args.get('desc'), require=False, p_name='描述')
        page = self.check_int(req.args.get('page'), require=False, default=1, p_name='页码')
        page_size = self.check_int(req.args.get('page_size'), require=False, default=10, p_name='每页数量')
        sta, data = await ConfJsonRC.get_conf_list(desc=desc, page=page, page_size=page_size)
        self.answer(data=data)
