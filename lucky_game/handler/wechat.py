from nsanic.libs.component import LogMeta

from common.public.base_enum import BaseEnum
from enum import unique
from common.public.conf import WeChatConf, H5_SERVER_ADDR, PROD_SERVER_ADDR, LIVE_SERVER, ENV
from lucky_game.config import conf_srv, ConfSrv
from nsanic.libs.tool import http_get, http_post, json_parse, json_encode
from nsanic.libs import tool_dt
from common.utils.utils import UtilsTool
from lucky_game.model_rc.base_user import BaseUserRC
from nsanic.libs.mult_log import NLogger


class WeChat(LogMeta):
    """ 微信相关 """
    conf: ConfSrv = conf_srv
    WECHAT_ACCESS_TOKEN = "wechat_access_token"  # 小程序access_token
    WECHAT_ACCESS_TOKEN_GZH = "wechat_access_token_gzh"  # 公众号access_token
    WECHAT_TICKET = "wechat_ticket"  # jsapi_ticket
    WECHAT_COIN_RATE = 100  # 价格（人名币） * 游戏币兑换比例 = 游戏币扣除数量 1:100

    @classmethod
    def __return_req_data(cls, req_data):
        """ 返回请求数据 """
        req_data = json_parse(req_data)
        NLogger.info(f"微信平台接口返参解析：{req_data}")
        errcode = req_data.get("errcode") or 0
        if errcode != 0:
            return errcode, req_data.get("errmsg")
        return errcode, req_data

    @classmethod
    async def wechat_mini_game_login(cls, code):
        """ 微信小游戏登录 code2Session """
        app_id = WeChatConf.WE_CHAT_MG_APP_ID
        app_secret = WeChatConf.WE_CHAT_MG_APP_SECRET

        url = "https://api.weixin.qq.com/sns/jscode2session?appid={0}&secret={1}" \
              "&js_code={2}&grant_type=authorization_code"
        url = url.format(app_id, app_secret, code)
        req_data = await http_get(url)
        return cls.__return_req_data(req_data)

    @classmethod
    async def wechat_check_session_key(cls, access_token, openid, session_key):
        """检查session_key是否过期 checkSessionKey """
        url = "https://api.weixin.qq.com/wxa/checksession?access_token={0}" \
              "&signature={1}&openid={2}&sig_method=hmac_sha256"
        params = {}
        params_str = json_encode(params)
        # 用户登录态签名  使用session_key（通过session key加密post请求数据）
        signature = UtilsTool.get_hash_secrets(session_key, params_str, secrets_type="sha256")
        url = url.format(access_token, signature, openid)
        req_data = await http_get(url)
        return cls.__return_req_data(req_data)

    @classmethod
    async def wechat_app_login(cls, code):
        """ 微信app登录 """
        wechat_id = WeChatConf.WE_CHAT_APP_ID
        wechat_secret = WeChatConf.WE_CHAT_APP_SECRET

        url = "https://api.weixin.qq.com/sns/oauth2/access_token?appid={}&secret={}&code={}&grant_type=authorization_code"
        url = url.format(wechat_id, wechat_secret, code)
        req_data = await http_get(url)
        return cls.__return_req_data(req_data)



    @classmethod
    async def wechat_gzh_login(cls, code):
        """ 微信公众号登陆 """
        gzh_id = WeChatConf.WE_CHAT_GZH_APP_ID
        gzh_secret = WeChatConf.WE_CHAT_GZH_APP_SECRET

        url = "https://api.weixin.qq.com/sns/oauth2/access_token?appid={}&secret={}&code={}&grant_type=authorization_code&connect_redirect=1"
        url = url.format(gzh_id, gzh_secret, code)
        NLogger.info(f"微信H5登录获取用户授权url：{url}")
        req_data = await http_get(url)
        NLogger.info(f"微信H5登录获取获取授权结果：{req_data}")
        return cls.__return_req_data(req_data)

    @classmethod
    async def __return_access_token(cls, result, app_id):
        result = json_parse(result)
        errcode = result.get("errcode") or 0
        if errcode != 0:
            return errcode, result.get("errmsg")
        access_token = result.get("access_token")
        expires_in = (result.get("expires_in") or 7200) - 5
        await cls.conf.rds.set_item(await cls.__session_key(app_id), access_token, ex_time=expires_in)
        return 0, access_token

    @classmethod
    async def __return_ticket(cls, result):
        result = json_parse(result)
        errcode = result.get("errcode") or 0
        if errcode != 0:
            return errcode, result.get("errmsg")
        ticket = result.get("ticket")
        expires_in = (result.get("expires_in") or 7200) - 5
        await cls.conf.rds.set_item(cls.WECHAT_TICKET, ticket, ex_time=expires_in)
        return 0, ticket

    @classmethod
    async def __session_key(cls, app_id):
        """ 获取session_key """
        if app_id == WeChatConf.WE_CHAT_MG_APP_ID:
            return cls.WECHAT_ACCESS_TOKEN
        else:
            return cls.WECHAT_ACCESS_TOKEN_GZH


    @classmethod
    async def wechat_get_access_token_stable(cls, app_id=WeChatConf.WE_CHAT_MG_APP_ID,
                                             app_secret=WeChatConf.WE_CHAT_MG_APP_SECRET):
        """ 获取微信access_token（稳定版） getStableAccessToken """
        cache_at = await cls.conf.rds.get_item(await cls.__session_key(app_id))
        if cache_at:
            return 0, cache_at.decode()

        url = "https://api.weixin.qq.com/cgi-bin/stable_token"
        params = {
            "grant_type": "client_credential",
            "appid": app_id,
            "secret": app_secret
        }
        req_data = await http_post(url, param=params)
        return await cls.__return_access_token(req_data, app_id)

    @classmethod
    async def wechat_get_ticket(cls, access_token):
        """ 获得jsapi_ticket """
        cache_at = await cls.conf.rds.get_item(cls.WECHAT_TICKET)
        if cache_at:
            return 0, cache_at.decode()

        url = f"https://api.weixin.qq.com/cgi-bin/ticket/getticket?access_token={access_token}&type=jsapi"
        req_data = await http_get(url)
        return await cls.__return_ticket(req_data)

    @classmethod
    async def __request_by_sign(cls, uid, url, path, params, access_token):
        """ 签名后请求数据 """
        # 获取session_key
        session_key = await BaseUserRC.get_session_key(uid)
        if not session_key:
            return cls.conf.STA_CODE.SESSION_KEY_EXPIRED, ""
        session_key = session_key.decode("utf-8")

        params_str = json_encode(params)
        # 用户登录态签名  使用session_key（通过session_key加密post请求数据）
        signature = UtilsTool.get_hash_secrets(session_key, params_str, secrets_type="sha256")
        # 支付请求签名（加密url和post请求数据）
        pay_sign = UtilsTool.get_hash_secrets(WeChatConf.WE_CHAT_APP_KEY, f"{path}&{params_str}", secrets_type="sha256")

        url = url.format(access_token, signature, pay_sign)
        req_data = await http_post(url, params_str, jsparse=False)
        return cls.__return_req_data(req_data)

    @classmethod
    async def wechat_mini_game_coin_pay(cls, uid, open_id: str, access_token: str, trade_amount: int, order_id: str,
                                        u_ip: str):
        """ 小游戏扣除游戏币 pay_v2.pay """
        url = "https://api.weixin.qq.com/wxa/game/pay?access_token={0}&signature={1}" \
              "&sig_method=hmac_sha256&pay_sig={2}"
        path = "/wxa/game/pay"

        params = {
            "openid": open_id,
            "offer_id": WeChatConf.WE_CHAT_MG_OFFER_ID,  # 支付应用id
            "ts": tool_dt.cur_time(),
            "zone_id": "1",
            "env": 0,
            "user_ip": u_ip,  # 用户外网ip
            "amount": int(trade_amount) * cls.WECHAT_COIN_RATE,
            # 扣除游戏币订单号，业务需要保证全局唯一，相同的订单号多次请求不会重复扣除；长度不超过63，只能是数字、英文大小写字母及_-的组合；不能以下划线（_）开头（2.0新增约束）
            "bill_no": order_id
        }
        return await cls.__request_by_sign(uid, url, path, params, access_token)

    @classmethod
    async def wechat_mini_game_coin_query(cls, uid, open_id: str, access_token: str, u_ip: str):
        """ 小游戏查询游戏币余额 pay_v2.getBalance """
        url = "https://api.weixin.qq.com/wxa/game/getbalance?access_token={0}&signature={1}" \
              "&sig_method=hmac_sha256&pay_sig={2}"
        path = "/wxa/game/getbalance"

        params = {
            "openid": open_id,
            "offer_id": WeChatConf.WE_CHAT_MG_OFFER_ID,
            "ts": tool_dt.cur_time(),
            "zone_id": "1",
            "env": 0,  # 0：现网环境 也叫正式环境 1：沙箱环境
            "user_ip": u_ip,  # 用户外网ip
        }
        return await cls.__request_by_sign(uid, url, path, params, access_token)

    @classmethod
    async def wechat_mini_game_query_order(cls, uid, open_id: str, access_token: str, order_id: str):
        """ 小游戏查询订单接口 pay_v2.queryOrder """
        url = "https://api.weixin.qq.com/wxa/game/queryorderinfo?access_token={0}&signature={1}" \
              "&sig_method=hmac_sha256&pay_sig={2}"
        path = "/wxa/game/queryorderinfo"

        params = {
            "openid": open_id,
            "offer_id": WeChatConf.WE_CHAT_MG_OFFER_ID,
            "ts": tool_dt.cur_time(),
            "zone_id": "1",
            "env": 0,  # 0：现网环境 也叫正式环境 1：沙箱环境
            "out_trade_no": order_id,
            "biz_id": 1,  # 1 代币 2 道具直购
        }
        return await cls.__request_by_sign(uid, url, path, params, access_token)

    @classmethod
    async def wechat_mini_game_return_order(cls, uid, trade_amount: int, order_id: str, product_id: str,
                                            method="requestMidasPaymentGameItem"):
        """
        小游戏创建订单返回（道具直购专用）
        参考文档：https://docs.qq.com/doc/DVFBybVlRWHVhRmZj?code=TxnmQLUsjkiErEunFwGJ5CoekYpT1ZPe7Tn5Seqgi5I&state=weworklogin&u=4187683d01314903b57f8cf4bb93aa63
        """
        # 获取session_key
        session_key = await BaseUserRC.get_session_key(uid)
        if not session_key:
            return
        session_key = session_key.decode("utf-8")
        env = 0
        app_key = WeChatConf.WE_CHAT_APP_KEY
        if ENV != "prod":
            env = 1
            app_key = WeChatConf.WE_CHAT_APP_KEY_DEV
        sign_data = {
            "mode": 'goods',  # game 游戏币 / goods 道具直购
            "offerId": WeChatConf.WE_CHAT_MG_OFFER_ID,
            "buyQuantity": 1,
            "env": env,  # 0：现网环境 也叫正式环境 / 1：沙箱环境
            "currencyType": 'CNY',
            "platform": 'android',
            "zoneId": '1',
            "productId": product_id or '',
            "goodsPrice": int(trade_amount * cls.WECHAT_COIN_RATE),  # 单位（分）
            "outTradeNo": order_id,
        }
        encode_data = json_encode(sign_data)
        # 用户登录态签名  使用session_key（通过session key加密post请求数据）
        signature = UtilsTool.get_hash_secrets(session_key, encode_data, secrets_type="sha256")
        # 支付请求签名（加密url和post请求数据）
        pay_sign = UtilsTool.get_hash_secrets(app_key, f"{method}&{encode_data}",
                                              secrets_type="sha256")  # 支付请求签名

        params = {
            "sign_data": encode_data,
            "pay_sign": pay_sign,
            "signature": signature,
        }
        return params

    @classmethod
    async def wechat_send_custom_msg(cls, uid, open_id: str, access_token: str, order_info: dict):
        """
        发送客服消息 sendCustomMessage
        参考文档：https://developers.weixin.qq.com/miniprogram/dev/OpenApiDoc/kf-mgnt/kf-message/sendCustomMessage.html
        """
        url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={access_token}"

        order_id = order_info.get("order_id")
        trade_amount = order_info.get("trade_amount")
        # 重定向跳转目标地址，简单说就是支付页面，环境：测试
        server_addr = PROD_SERVER_ADDR
        params = {
            "touser": open_id,  # 用户的 OpenID
            "msgtype": 'link',  # text表示文本消息；image表示图片消息；link表示图文链接；miniprogrampage表示小程序卡片。
            "link":
                {
                    "title": '点我充值',
                    "description": f'{trade_amount}元\n支付完成请返回游戏查看',
                    "url": f'{H5_SERVER_ADDR}/smxn/payH5/index.html?uid={uid}&orderId={order_id}&price={trade_amount}&curSever={server_addr}',
                    # 微信商户后台配置没位了，只能暂用他们的
                    "thumb_url": 'https://ddzres.lpyqp.com/pay2.png'  # 图片地址
                }
        }
        req_data = await http_post(url, param=json_encode(params), jsparse=False)
        return cls.__return_req_data(req_data)

    @classmethod
    async def update_gzh_openid(cls, uid, code):
        """把公众号openid更新到缓存中"""
        u_info = await BaseUserRC.cache_by_uid(uid) or {}
        gzh_openid = u_info.get('gzh_openid')
        if gzh_openid:
            return gzh_openid

        if not code:
            return None

        errcode, req_data = await cls.wechat_gzh_login(code)
        if errcode != 0:
            return None

        new_openid = req_data.get("openid")
        cls.log_info('update_gzh_openid result:', errcode, new_openid)
        if new_openid:
            u_info["gzh_openid"] = new_openid
            await BaseUserRC.update_cache(u_info.get("uid"), u_info)
            return new_openid

    @classmethod
    async def wechat_gzh_userinfo(cls, access_token, open_id):
        """获取公众号用户信息"""
        url = f"https://api.weixin.qq.com/sns/userinfo?access_token={access_token}&openid={open_id}&connect_redirect=1"
        # 通过access_token和open_id获取用户个人信息（UnionID机制）
        req_get = await http_get(url)
        req_data = json_parse(req_get)
        cls.log_info('Wechat userinfo result:', req_data)
        errcode = req_data.get("errcode", 0)
        if errcode > 0:
            data = {"errcode": errcode, "errmsg": req_data}
            return False, data
        return True, req_data


@unique
class WeChatPayCode(BaseEnum):
    """errcode的合法值"""
    ORDER_DUPLICATE = 90012, "订单号重复"
