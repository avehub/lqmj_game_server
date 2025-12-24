from decimal import Decimal, ROUND_HALF_UP

from nsanic.libs.component import LogMeta

from common.public.base_enum import BaseEnum
from enum import unique
from common.public.conf import WeChatConf, H5_SERVER_ADDR, SERVER_ADDR, ENV
from lucky_game.config import conf_srv, ConfSrv
from nsanic.libs.tool import http_get, http_post, json_parse, json_encode
from nsanic.libs import tool_dt
from common.utils.utils import UtilsTool
from lucky_game.const import PlatForm, OrderStatus
from lucky_game.handler.WXBizMsgCrypt import WXBizMsgCrypt
from lucky_game.model_rc.base_user import BaseUserRC
from nsanic.libs.mult_log import NLogger
"""
from tortoise import Tortoise
db = Tortoise.get_connection("default")
result = await db.execute_query_dict("SELECT * FROM user WHERE id=%s", [1])
print(result)
"""

class WeChatMpLogin(LogMeta):
    @classmethod
    async def wechat_gzh_login(cls, code):
        """ 微信公众号登陆 """
        gzh_id = WeChatConf.WE_CHAT_GZH_APP_ID
        gzh_secret = WeChatConf.WE_CHAT_GZH_APP_SECRET

        url = "https://api.weixin.qq.com/sns/oauth2/access_token?appid={}&secret={}&code={}&grant_type=authorization_code&connect_redirect=1"
        url = url.format(gzh_id, gzh_secret, code)
        cls.log_info(f"微信H5登录获取用户授权url：{url}")
        req_data_str = await http_get(url)
        req_data_json = json_parse(req_data_str)
        NLogger.info(f"微信平台接口返参解析：{req_data_json}")
        errcode = req_data_json.get("errcode") or 0
        if errcode == 0:
            return await cls.wechat_userinfo(req_data_json["access_token"], req_data_json["openid"])
        return False, req_data_json.get("errmsg")

    @classmethod
    async def wechat_userinfo(cls, access_token, open_id):
        """获取微信用户信息"""
        url = f"https://api.weixin.qq.com/sns/userinfo?access_token={access_token}&openid={open_id}&connect_redirect=1"
        # 通过access_token和open_id获取用户个人信息（UnionID机制）
        req_get = await http_get(url)
        req_data = json_parse(req_get)
        cls.log_info('Wechat userinfo result:', req_data)
        errcode = req_data.get("errcode", 0)
        if errcode != 0:
            data = {"errcode": errcode, "errmsg": req_data}
            return False, data
        return True, req_data
