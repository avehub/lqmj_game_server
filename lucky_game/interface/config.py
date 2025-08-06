"""
配置相关
"""
from sanic import Request
from lucky_game.base_api import GameAuthApi
from lucky_game.model_rc.conf_json import ConfJsonRC


class GetConf(GameAuthApi):
    """ 获取基础配置 """

    async def get(self, req: Request, **kwargs):
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        key = self.check_str(req.args.get("key"), require=True, p_name="配置key")
        data = await ConfJsonRC.cache_conf_data_by_pk(key)
        return self.answer(data=data)
