"""
工具类相关接口
"""
import hashlib
import os
import time
from urllib import parse

from sanic import Request, response
from lucky_game.base_api import SpecialApi
from nsanic.libs.tool import read_file
from common.public.enum_const import StaCode
from lucky_game.handler.random_utils import generate_random_string
from lucky_game.handler.wechat import WeChat
from common.public.conf import WeChatConf


class GetWeChatShareData(SpecialApi):
    """
    获取微信分享配置数据
    """
    async def get(self, req: Request, **kwargs):
        url = self.check_str(req.args.get('url'), require=True, p_name="分享地址")
        if not url:
            return self.answer(StaCode.FAIL, hint="分享地址不能为空")
        share_url = url.split("#")[0]
        parse_data = parse.urlparse(share_url)
        url_host = parse_data.hostname
        if not url_host:
            return self.answer(StaCode.FAIL, hint="分享地址错误")
        # if url_host not in get_by_key('share_check_urls') and url_host[0:12] != '192.168.111.':
        #     return self.answer(StaCode.FAIL, hint="分享地址错误")
        num, jsapi_ticket = await WeChat.wechat_get_access_token_stable(WeChatConf.WE_CHAT_GZH_APP_ID, WeChatConf.WE_CHAT_GZH_APP_SECRET)
        if not jsapi_ticket:
            return self.answer(StaCode.FAIL, hint="获取微信access_token失败")
        cur_time = time.time() * 1000
        nonce_str = generate_random_string(16)
        sign_str = hashlib.sha1("jsapi_ticket={0}&noncestr={1}&timestamp={2}&url={3}".format(
            jsapi_ticket, nonce_str, cur_time, share_url).encode('utf-8'))
        js_data = await read_file(os.getcwd() + "/resource/default/wxjs_sdk.js", "utf-8")
        if not js_data:
            return self.answer(StaCode.FAIL, hint="配置文件不存在")
        if not isinstance(js_data, str):
            return self.answer(StaCode.FAIL, hint="文件内容格式错误")
        js_data = js_data.replace("leqi_app_id", WeChatConf.WE_CHAT_GZH_APP_ID)
        js_data = js_data.replace("leqi_timestamp", str(cur_time))
        js_data = js_data.replace("leqi_nonce_str", nonce_str)
        js_data = js_data.replace("leqi_signature", sign_str.hexdigest())
        return response.HTTPResponse(
            body=js_data,
            content_type="application/javascript; charset=UTF-8"
        )
