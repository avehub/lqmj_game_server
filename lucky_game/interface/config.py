"""
配置相关
"""
from sanic import Request
from lucky_game.base_api import GameAuthApi, SpecialApi
from lucky_game.model_rc.conf_json import ConfJsonRC


class GetConf(SpecialApi):
    """ 获取基础配置 """
    async def get(self, req: Request, **kwargs):
        key = self.check_str(req.args.get("key"), require=True, p_name="配置key")
        data = await ConfJsonRC.cache_conf_data_by_pk(key)
        return self.answer(data=data)


class GetAppConf(SpecialApi):
    """ 获取应用配置 """
    async def get(self, req: Request, **kwargs):
        platform = self.check_str(req.args.get("platform"), require=True, p_name="平台")
        c_ver = self.check_str(req.args.get("c_ver"), require=True, p_name="版本号")
        device_id = self.check_str(req.args.get("device_id "), require=True, p_name="设备ID")
        key = ConfJsonRC.CONF_UP_APP
        data = await ConfJsonRC.cache_conf_data_by_pk(key)
        return self.answer(data=data)
