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



