from nsanic.libs import tool_dt
from nsanic.libs.component import LogMeta

from common.public.conf import DouYinConf
from common.utils.utils import UtilsTool
from lucky_game.config import conf_srv, ConfSrv
from nsanic.libs.tool import http_get, http_post, json_parse
from lucky_game.const import PayType, PlatForm


class DouYin(LogMeta):
    """ 抖音相关 """
    conf: ConfSrv = conf_srv
    DOUYIN_ACCESS_TOKEN = "douyin_access_token"  # access_token
    DOUYIN_CLIENT_TOKEN = "douyin_client_token"  # client_token
    DOUYIN_COIN_RATE = 100  # 价格（人名币） * 游戏币兑换比例 = 游戏币扣除数量 1:100
    DOUYIN_DIAMOND_RATE = 10  # 价格（人名币） * 黄钻兑换比例 = 黄钻扣除数量 1:10

    @classmethod
    async def douyin_get_access_token(cls, refresh=False):
        """
        获取抖音access_token
        参考文档：https://developer.open-douyin.com/docs/resource/zh-CN/mini-game/develop/server/interface-request-credential/get-access-token
        """
        if not refresh:
            cache_at = await cls.conf.rds.get_item(cls.DOUYIN_ACCESS_TOKEN)
            if cache_at:
                return 0, cache_at.decode()

        url = "https://minigame.zijieapi.com/mgplatform/api/apps/v2/token"
        params = {
            "appid": DouYinConf.DOUYIN_APP_ID,
            "secret": DouYinConf.DOUYIN_APP_SECRET,
            "grant_type": "client_credential"
        }
        req_data = await http_post(url, param=params)
        res = json_parse(req_data)
        err_no = res.get("err_no") or 0
        if err_no != 0:
            cls.log_err(f'DouYin get_access_token failed: {res}')
            return err_no, res.get("err_tips")

        data = res.get("data") or {}
        access_token = data.get("access_token")
        expires_in = (data.get("expires_in") or 7200) - 5
        # expires_in = data.get("expires_in") or 7200
        await cls.conf.rds.set_item(cls.DOUYIN_ACCESS_TOKEN, access_token, ex_time=expires_in)
        return err_no, access_token

    @classmethod
    async def douyin_get_client_token(cls, refresh=False):
        """
        获取抖音client_token
        该接口用于获取接口调用的凭证 client_token，该接口适用于抖音授权；
        参考文档：https://developer.open-douyin.com/docs/resource/zh-CN/mini-app/develop/server/basic-abilities/interface-request-credential/non-user-authorization/get-client_token
        """
        if not refresh:
            cache_at = await cls.conf.rds.get_item(cls.DOUYIN_CLIENT_TOKEN)
            if cache_at:
                return 0, cache_at.decode()

        url = "https://open.douyin.com/oauth/client_token/"
        headers = {"content-type": 'application/json'}
        params = {
            "client_key": DouYinConf.DOUYIN_APP_ID,
            "client_secret": DouYinConf.DOUYIN_APP_SECRET,
            "grant_type": 'client_credential'
        }
        req_data = await http_post(url, param=params, headers=headers)
        res = json_parse(req_data)
        data = res.get("data") or {}

        error_code = data.get("error_code") or 0
        if error_code != 0:
            cls.log_err(f'DouYin get_client_token failed: {res}')
            return error_code, data.get("message")

        client_token = data.get("access_token")
        expires_in = (data.get("expires_in") or 7200) - 5
        await cls.conf.rds.set_item(cls.DOUYIN_CLIENT_TOKEN, client_token, ex_time=expires_in)
        return error_code, client_token

    @classmethod
    async def douyin_mini_game_login(cls, code):
        """
        抖音小游戏登录
        参考文档：https://partner.open-douyin.com/docs/resource/zh-CN/mini-game/develop/server/log-in/code-2-session
        """
        app_id = DouYinConf.DOUYIN_APP_ID
        app_secret = DouYinConf.DOUYIN_APP_SECRET
        url = "https://minigame.zijieapi.com/mgplatform/api/apps/jscode2session?appid={}&secret={}&code={}"
        url = url.format(app_id, app_secret, code)
        req_data = await http_get(url)
        return cls.__return_req_data(req_data)

    @classmethod
    def __return_req_data(cls, req_data):
        """ 返回请求数据 """
        req_data = json_parse(req_data)
        errcode = req_data.get("errcode") or 0
        if errcode != 0:
            return errcode, req_data.get("errmsg")
        return errcode, req_data

    @classmethod
    async def __request_by_sign(cls, url, path, params: dict, method='POST'):
        """
        支付签名参与请求
        所有请求参数除了mp_sig以外都要参与签名生成
        url:只需要相对路径path参加签名，例如/api/apps/game/wallet/get_balance
        """
        # 对参与签名的参数按照key=value的格式，并按照参数名 ASCII 字典序升序排序
        sorted_params = sorted(params.items())
        # 拼接 stringA
        str_a = '&'.join([f"{k}={v}" for k, v in sorted_params])
        # 拼接 stringB
        str_b = f"{str_a}&org_loc={path}&method={method}"
        # 把支付密钥作为 key，使用 HMAC-SHA256 得到签名
        signature = UtilsTool.get_hash_secrets(DouYinConf.DOUYIN_PAY_SECRET, str_b, secrets_type="sha256")
        params["mp_sig"] = signature

        req_data = await http_post(url.format(path), param=params)
        return req_data

    @classmethod
    async def douyin_mini_game_coin_query(cls, open_id: str, access_token: str):
        """
        获取游戏币余额
        参考文档：https://developer.open-douyin.com/docs/resource/zh-CN/mini-game/develop/api/payment/acquire-mini-game-coin-balance
        """
        url = "https://developer.toutiao.com/api{0}"
        path = "/wxa/game/getbalance"
        params = {
            "openid": open_id,
            "appid": DouYinConf.DOUYIN_APP_ID,
            "ts": tool_dt.cur_time(),
            "zone_id": "1",
            "pf": "android",  # 平台 目前仅为安卓："android", "ios"
            "access_token": access_token
        }
        req_data = await cls.__request_by_sign(url, path, params, method='POST')
        return cls.__return_req_data(req_data)

    @classmethod
    async def douyin_mini_game_coin_pay(cls, open_id: str, access_token: str, pay_amount: int, order_id: str):
        """
        游戏币扣除接口
        参考文档：https://developer.open-douyin.com/docs/resource/zh-CN/mini-game/develop/api/payment/mini-game-coin-deduction-interface
        """

        url = "https://developer.toutiao.com{0}"
        path = "/api/apps/game/wallet/game_pay"
        params = {
            "openid": open_id,
            "appid": DouYinConf.DOUYIN_APP_ID,
            "ts": tool_dt.cur_time(),
            "zone_id": "1",
            "pf": "android",  # 平台 安卓：android
            "amt": int(pay_amount) * cls.DOUYIN_COIN_RATE,
            "bill_no": order_id,
            "access_token": access_token
        }
        req_data = await cls.__request_by_sign(url, path, params, method='POST')
        return cls.__return_req_data(req_data)

    @classmethod
    async def douyin_query_pay_status(cls, access_token: str, order_id: str):
        """
        查询订单支付状态 queryPayState
        参考文档：https://developer.open-douyin.com/docs/resource/zh-CN/mini-game/develop/api/payment/payment-server-callback
        """
        url = "https://developer.toutiao.com/api/apps/game/payment/queryPayState"
        params = {
            "access_token": access_token,
            "orderno": order_id
        }
        req_data = await http_get(url, param=params)
        res = json_parse(req_data)
        err_no = res.get("err_no") or 0
        if err_no != 0:
            cls.log_err(f'DouYin query_pay_status failed: {res}')
            return err_no, res.get("message")
        return err_no, res.get("data")

    @classmethod
    def adjust_payment_for_douyin(cls, item: dict, platform: str, os: str) -> None:
        """调整抖音平台的支付类型和价格"""
        if platform == PlatForm.DOUYIN_MINI_GAME.phrase and os == 'ios' and item.get('pay_type') == PayType.BY_RMB:
            item['pay_type'] = PayType.BY_DY_DIAMOND
            item['price'] = int(item.get('price', 0)) * cls.DOUYIN_DIAMOND_RATE
            item['orig_price'] = int(item.get('orig_price', 0)) * cls.DOUYIN_DIAMOND_RATE
            item['discount_price'] = int(item.get('discount_price', 0)) * cls.DOUYIN_DIAMOND_RATE

