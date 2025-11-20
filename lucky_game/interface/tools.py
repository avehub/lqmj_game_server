"""
工具类相关接口
"""
import hashlib
import os
from datetime import datetime
from urllib import parse
from urllib.parse import urlparse, urlunparse

from sanic import Request, response
from lucky_game.base_api import SpecialApi
from nsanic.libs.tool import read_file
from common.public.enum_const import StaCode
from lucky_game.handler.random_utils import generate_random_string
from lucky_game.handler.wechat import WeChat
from common.public.conf import WeChatConf
from lucky_game.model_rc.app_versions import AppVersionsRC
from lucky_game.model_rc.base_records_game import BaseRecordsGameRC


class GetWeChatShareData(SpecialApi):
    """
    获取微信分享配置数据
    """
    async def get(self, req: Request, **kwargs):
        url = self.check_str(req.args.get('url'), require=True, p_name="分享地址")
        if not url:
            return self.answer(StaCode.FAIL, hint="分享地址不能为空")
        # share_url = url.split("#")[0]
        # parse_data = parse.urlparse(share_url)
        # url_host = parse_data.hostname
        url_parts = list(urlparse(url))
        url_parts[5] = ''  # 清除fragment部分
        share_url = urlunparse(url_parts)
        if not share_url:
            return self.answer(StaCode.FAIL, hint="分享地址错误")
        access_token_status, access_token = await WeChat.wechat_get_access_token_stable(app_id=WeChatConf.WE_CHAT_GZH_APP_ID,
                                                                                        app_secret=WeChatConf.WE_CHAT_GZH_APP_SECRET)
        if access_token_status != 0 or not access_token:
            return self.answer(StaCode.FAIL, hint="获取微信access_token失败")
        ticket_status, jsapi_ticket = await WeChat.wechat_get_ticket(access_token)
        if ticket_status != 0 or not jsapi_ticket:
            return self.answer(StaCode.FAIL, hint="获取微信jsapi_ticket失败")
        params = {
            'jsapi_ticket': jsapi_ticket,
            'noncestr': generate_random_string(16),
            'timestamp':  int(datetime.now().timestamp()),
            'url': share_url
        }
        tmp_str = '&'.join([f"{k}={params[k]}" for k in sorted(params.keys())])
        self.log_info("生成签名参数", tmp_str)
        sign_str = hashlib.sha1(tmp_str.encode('utf-8')).hexdigest()
        self.log_info("生成签名结果", sign_str)
        js_data = await read_file(os.getcwd() + "/resource/default/wxjs_sdk.js", "utf-8")
        if not js_data:
            return self.answer(StaCode.FAIL, hint="配置文件不存在")
        if not isinstance(js_data, str):
            return self.answer(StaCode.FAIL, hint="文件内容格式错误")
        js_data = js_data.replace("leqi_app_id", WeChatConf.WE_CHAT_GZH_APP_ID)
        js_data = js_data.replace("leqi_timestamp", str(params['timestamp']))
        js_data = js_data.replace("leqi_nonce_str", params['noncestr'])
        js_data = js_data.replace("leqi_signature", sign_str)
        return response.HTTPResponse(
            body=js_data,
            content_type="application/javascript; charset=UTF-8"
        )


class GetAppVersion(SpecialApi):
    """ 获取应用版本信息 """
    async def get(self, req: Request, **kwargs):
        platform = self.check_str(req.args.get("platform"), require=True, p_name="平台")
        c_ver = self.check_str(req.args.get("c_ver"), require=True, p_name="版本号")
        device_id = self.check_str(req.args.get("device_id"), require=True, p_name="设备ID")
        data, msg = await AppVersionsRC.get_app_info(platform)
        if not data:
            return self.answer(StaCode.FAIL, hint=msg)
        data["is_update"] = await AppVersionsRC.compare_versions(c_ver, data.get("version_code"))
        return self.answer(data=data)


class GetWechatCode(SpecialApi):
    """ 微信授权转发
    文档：https://developers.weixin.qq.com/doc/oplatform/Third-party_Platforms/2.0/api/Before_Develop/Official_Accounts/official_account_website_authorization.html
    """
    decorators = []
    async def get(self, req: Request):
        redirect_url = self.check_str(req.args.get('redirect_url'), require=True, p_name="redirect_url")
        return response.redirect(
            redirect_url,
            status=301,
            headers={"Cache-Control": "no-store"}
        )


class GetGameRecord(SpecialApi):
    """
    获取游戏回放战绩
    """
    async def get(self, req: Request):
        uid = self.check_int(req.args.get("uid"), require=False, p_name="用户ID")
        room_id = self.check_int(req.args.get("room_id"), require=False, p_name="房间ID")
        if not uid and not room_id:
            return self.answer(StaCode.FAIL, hint="参数错误")
        result, e = await BaseRecordsGameRC.get_by_game_record(
            room_id=room_id,
            uid=uid,
        )
        return self.answer(data=result, hint=e)
