import asyncio
from alipay.aop.api.AlipayClientConfig import AlipayClientConfig
from alipay.aop.api.DefaultAlipayClient import DefaultAlipayClient
from alipay.aop.api.domain.AlipayTradeAppPayModel import AlipayTradeAppPayModel
from alipay.aop.api.request.AlipayTradeAppPayRequest import AlipayTradeAppPayRequest
from alipay.aop.api.request.AlipaySystemOauthTokenRequest import AlipaySystemOauthTokenRequest
from alipay.aop.api.response.AlipaySystemOauthTokenResponse import AlipaySystemOauthTokenResponse
from alipay.aop.api.request.AlipayUserInfoShareRequest import AlipayUserInfoShareRequest
from alipay.aop.api.response.AlipayUserInfoShareResponse import AlipayUserInfoShareResponse
from alipay.aop.api.domain.AlipayUserGamecenterCoinQueryModel import AlipayUserGamecenterCoinQueryModel
from alipay.aop.api.request.AlipayUserGamecenterCoinQueryRequest import AlipayUserGamecenterCoinQueryRequest
from alipay.aop.api.response.AlipayUserGamecenterCoinQueryResponse import AlipayUserGamecenterCoinQueryResponse
from alipay.aop.api.domain.AlipayUserGamecenterCoinPayModel import AlipayUserGamecenterCoinPayModel
from alipay.aop.api.request.AlipayUserGamecenterCoinPayRequest import AlipayUserGamecenterCoinPayRequest
from alipay.aop.api.response.AlipayUserGamecenterCoinPayResponse import AlipayUserGamecenterCoinPayResponse
from alipay.aop.api.domain.AlipayUserGamecenterPaymentRefundModel import AlipayUserGamecenterPaymentRefundModel
from alipay.aop.api.request.AlipayUserGamecenterPaymentRefundRequest import AlipayUserGamecenterPaymentRefundRequest
from alipay.aop.api.response.AlipayUserGamecenterPaymentRefundResponse import AlipayUserGamecenterPaymentRefundResponse
from alipay.aop.api.domain.AlipayUserGamecenterPaymentQuerystatusModel import \
    AlipayUserGamecenterPaymentQuerystatusModel
from alipay.aop.api.request.AlipayUserGamecenterPaymentQuerystatusRequest import \
    AlipayUserGamecenterPaymentQuerystatusRequest
from alipay.aop.api.response.AlipayUserGamecenterPaymentQuerystatusResponse import \
    AlipayUserGamecenterPaymentQuerystatusResponse
from alipay.aop.api.util.SignatureUtils import verify_with_rsa
from nsanic.libs.tool import json_parse
from common.public.conf import AliPayConf
from common.public.conf import LIVE_SERVER
from promising_game.config import conf_srv, ConfSrv
from common.public.enum_const import StaCode
from promising_game.const import AliGrantType


class Alipay:
    """ 阿里相关 """
    conf: ConfSrv = conf_srv
    CLIENT: DefaultAlipayClient = None
    ALI_ACCESS_TOKEN = "ali_access_token"  # access_token
    ALI_REFRESH_TOKEN = "ali_refresh_token"  # refresh_token
    ALI_COIN_RATE = 100  # 价格（人名币） * 游戏币兑换比例 = 游戏币扣除数量 1:100

    @classmethod
    def get_client(cls):
        """
        得到客户端对象
        注意，一个alipay_client_config对象对应一个DefaultAlipayClient，定义DefaultAlipayClient对象后，alipay_client_config不得修改
        如果想使用不同的配置，请定义不同的DefaultAlipayClient。
        logger参数用于打印日志，不传则不打印，建议传递。
        """
        if not cls.CLIENT:
            alipay_client_config = AlipayClientConfig()
            alipay_client_config.app_id = AliPayConf.ALIPAY_APP_ID
            alipay_client_config.app_private_key = AliPayConf.ALIPAY_APP_PRIVATE_KEY
            alipay_client_config.alipay_public_key = AliPayConf.ALIPAY_PUBLIC_KEY
            cls.conf.log.info(f'ali_get_client ALIPAY_APP_ID: {AliPayConf.ALIPAY_APP_ID}')
            cls.CLIENT = DefaultAlipayClient(alipay_client_config=alipay_client_config, logger=cls.conf.log)
        return cls.CLIENT

    @classmethod
    def verify_with_rsa(cls, message, sign):
        """ 验签 """
        return verify_with_rsa(AliPayConf.ALIPAY_PUBLIC_KEY, message, sign)

    @classmethod
    def gen_order_str(cls, out_trade_no, body="body", subject="subject", total_amount="0", timeout_express="90m"):
        """ 生成订单字符串（返给客户端向支付宝支付时传递的请求串） """
        client = cls.get_client()
        model = AlipayTradeAppPayModel()
        model.timeout_express = timeout_express
        model.total_amount = total_amount
        model.seller_id = AliPayConf.SELLER_ID
        model.product_code = "QUICK_MSECURITY_PAY"
        model.body = body
        model.subject = subject
        model.out_trade_no = out_trade_no
        request = AlipayTradeAppPayRequest(biz_model=model)
        request.notify_url = AliPayConf.NOTIFY_URL if LIVE_SERVER else AliPayConf.NOTIFY_URL_DEV  # 阿里回调通知
        response = client.sdk_execute(request)
        return response

    @classmethod
    async def ali_order_query_status(cls, open_id: str, order_id: str) -> (bool, str):
        """
        alipay.user.gamecenter.payment.querystatus(充值状态查询)
        参考文档：https://opendocs.alipay.com/apis/085anm
        """
        client = cls.get_client()
        # 业务请求参数
        model = AlipayUserGamecenterPaymentQuerystatusModel()
        model.open_id = open_id
        model.custom_id = order_id
        request = AlipayUserGamecenterPaymentQuerystatusRequest(biz_model=model)
        # 执行请求，执行过程中如果发生异常，会抛出，请打印异常栈
        try:
            loop = asyncio.get_running_loop()
            response_content = await loop.run_in_executor(None, client.execute, request)  # 放线程池请求
            if not response_content:
                return False, {"errcode": StaCode.FAIL, "errmsg": f'ali_order_query_status error'}
        except Exception as e:
            cls.conf.log.error(f'ali_order_query_status error: {e}')
            return False, {"errcode": StaCode.FAIL, "errmsg": f'ali_order_query_status error: {e}'}
        else:
            # 解析响应结果
            response = AlipayUserGamecenterPaymentQuerystatusResponse()
            response.parse_response_content(response_content)
            if not response.is_success():
                cls.conf.log.error(
                    f"ali_query_order_status fail:"
                    f"{response.code}, {response.msg}, {response.sub_code}, {response.sub_msg}"
                )
                return False, json_parse(response.body)
            return True, json_parse(response.body)

    @classmethod
    async def ali_get_access_token(cls, auth_code: str, grant_type: AliGrantType, refresh_token=""):
        """
        alipay.system.oauth.token(换取授权访问令牌)
        参考文档：https://opendocs.alipay.com/open/bedfb807_alipay.system.oauth.token?pathHash=cca8eb7d
        grant_type 授权类型，支持如下类型:
            authorization_code：用户授权，传入 auth_code 换取授权令牌，无需传入 refresh_token。
            refresh_token：刷新令牌，传入有效的 refresh_token 用于刷新授权令牌，无需传入 auth_code。
        """
        client = cls.get_client()
        request = AlipaySystemOauthTokenRequest()
        request.grant_type = grant_type
        # 根据业务场景选择 grant_type
        if grant_type == AliGrantType.GET_TOKEN:
            request.code = auth_code
        else:
            request.refresh_token = refresh_token
        # 执行请求，执行过程中如果发生异常，会抛出，请打印异常栈
        try:
            loop = asyncio.get_running_loop()
            response_content = await loop.run_in_executor(None, client.execute, request)  # 放线程池请求
            if not response_content:
                return False, {"errcode": StaCode.FAIL, "errmsg": f'ali_get_access_token error'}
        except Exception as e:
            cls.conf.log.error(f'ali_get_access_token error: {e}')
            return False, {"errcode": StaCode.FAIL, "errmsg": f'ali_get_access_token error: {e}'}
        else:
            # 获取并解析响应结果
            response = AlipaySystemOauthTokenResponse()
            response.parse_response_content(response_content)
            if not response.is_success():
                cls.conf.log.error(
                    f"ali_get_access_token fail: "
                    f"{response.code}, {response.msg}, {response.sub_code}, {response.sub_msg}"
                )
                return False, json_parse(response.body)
            # 如果业务成功，则通过response属性获取需要的值
            return await cls.__return_access_token(response)

    @classmethod
    async def __return_access_token(cls, response):
        """
        access_token 令牌 / expires_in 有效期（秒） / scope 产品权限
        expires_in 有效期： 取决于授权时指定的 scope 的有效期，如果授权时指定多个 scope，最终的 expires_in 取决于有效期最短的 scope。
        到期时间 =（调用 alipay.system.oauth.token 接口的时间） +（expires_in）
        """
        # todo:因暂时没有接口用到access_token，所以先不存
        access_token = response.access_token
        # expires_in = int(response.expires_in) - 5
        #
        # refresh_token = response.refresh_token
        # re_expires_in = int(response.re_expires_in) - 5
        #
        # await cls.conf.rds.set_item(cls.ALI_PROGRAM_AT, access_token, ex_time=expires_in)
        # await cls.conf.rds.set_item(cls.ALI_PROGRAM_RT, refresh_token, ex_time=re_expires_in)
        return True, {"open_id": response.open_id, "access_token": access_token}

    @classmethod
    async def ali_user_info_share(cls, open_id: str, access_token: str):
        """
        alipay.user.info.share(支付宝会员授权信息查询接口)
        参考文档：https://opendocs.alipay.com/open/01834fa5_alipay.user.info.share?pathHash=af6ac2d2&scene=common
        """
        client = cls.get_client()
        request = AlipayUserInfoShareRequest()
        # 添加 auth_token（公共请求参数）
        request.add_other_text_param("auth_token", access_token)
        try:
            loop = asyncio.get_running_loop()
            response_content = await loop.run_in_executor(None, client.execute, request)
            if not response_content:
                return False, {"errcode": StaCode.FAIL, "errmsg": f'ali_user_info_share error'}
        except Exception as e:
            cls.conf.log.error(f'ali_user_info_share error: {e}')
            return False, {"errcode": StaCode.FAIL, "errmsg": f'ali_user_info_share error: {e}'}
        else:
            response = AlipayUserInfoShareResponse()
            response.parse_response_content(response_content)
            if not response.is_success():
                cls.conf.log.error(
                    f"ali_user_info_share fail: "
                    f"{response.code}, {response.msg}, {response.sub_code}, {response.sub_msg}"
                )
                return False, json_parse(response.body)
            return True, json_parse(response.body)

    @classmethod
    async def ali_mini_game_coin_query(cls, open_id: str):
        """
        alipay.user.gamecenter.coin.query(查询用户游戏币余额)
        参考文档：https://opendocs.alipay.com/open/b499ec2e_alipay.user.gamecenter.coin.query?pathHash=6b541dba
        """
        client = cls.get_client()
        # 业务请求参数
        model = AlipayUserGamecenterCoinQueryModel()
        model.open_id = open_id
        request = AlipayUserGamecenterCoinQueryRequest(biz_model=model)
        try:
            loop = asyncio.get_running_loop()
            response_content = await loop.run_in_executor(None, client.execute, request)
            if not response_content:
                return False, {"errcode": StaCode.FAIL, "errmsg": f'ali_mini_game_coin_query error:'}
        except Exception as e:
            cls.conf.log.error(f'ali_mini_game_coin_query error: {e}')
            return False, {"errcode": StaCode.FAIL, "errmsg": f'ali_mini_game_coin_query error: {e}'}
        else:
            response = AlipayUserGamecenterCoinQueryResponse()
            response.parse_response_content(response_content)
            if not response.is_success():
                cls.conf.log.error(
                    f"ali_mini_game_coin_query fail: "
                    f"{response.code}, {response.msg}, {response.sub_code}, {response.sub_msg}"
                )
                return False, json_parse(response.body)
            return True, json_parse(response.body)

    @classmethod
    async def ali_mini_game_coin_pay(cls, open_id: str, order_id: str, pay_amount: str, store_name: str, desc: str):
        """
        alipay.user.gamecenter.coin.pay(扣减用户游戏币)
        参考文档：https://opendocs.alipay.com/apis/085nrt
        ali_coin_rate: 价格（人名币） * 游戏币兑换比例 = 游戏币扣除数量
        """
        client = cls.get_client()
        # 业务请求参数
        model = AlipayUserGamecenterCoinPayModel()
        model.open_id = open_id
        model.bill_no = order_id
        model.amt = int(pay_amount) * cls.ALI_COIN_RATE
        model.pay_item = store_name
        model.app_remark = desc
        request = AlipayUserGamecenterCoinPayRequest(biz_model=model)
        try:
            loop = asyncio.get_running_loop()
            response_content = await loop.run_in_executor(None, client.execute, request)
            if not response_content:
                return False, {"errcode": StaCode.FAIL, "errmsg": f'ali_mini_game_coin_pay error'}
        except Exception as e:
            cls.conf.log.error("ali_pay_by_game_coins error: ", e)
            return False, {"errcode": StaCode.FAIL, "errmsg": f'ali_mini_game_coin_pay error: {e}'}
        else:
            response = AlipayUserGamecenterCoinPayResponse()
            response.parse_response_content(response_content)
            if not response.is_success():
                cls.conf.log.error(
                    f"ali_mini_game_coin_pay fail: "
                    f"{response.code}, {response.msg}, {response.sub_code}, {response.sub_msg}"
                )
                return False, json_parse(response.body)
            return True, json_parse(response.body)

    @classmethod
    async def ali_payment_refund(cls, open_id: str, trade_no: str) -> (bool, str):
        """
        alipay.user.gamecenter.payment.refund(充值退款接口)
        参考文档：https://opendocs.alipay.com/mini-game/6fc63327_alipay.user.gamecenter.payment.refund?pathHash=91f535af
        """
        client = cls.get_client()
        # 业务请求参数
        model = AlipayUserGamecenterPaymentRefundModel()
        model.open_id = open_id
        model.trade_no = trade_no
        request = AlipayUserGamecenterPaymentRefundRequest(biz_model=model)
        # 执行请求，执行过程中如果发生异常，会抛出，请打印异常栈
        try:
            loop = asyncio.get_running_loop()
            response_content = await loop.run_in_executor(None, client.execute, request)  # 放线程池请求
            if not response_content:
                return False, {"errcode": StaCode.FAIL, "errmsg": f'ali_payment_refund error'}
        except Exception as e:
            cls.conf.log.error(f'ali_payment_refund error: {e}')
            return False, {"errcode": StaCode.FAIL, "errmsg": f'ali_payment_refund error: {e}'}
        else:
            # 解析响应结果
            response = AlipayUserGamecenterPaymentRefundResponse()
            response.parse_response_content(response_content)
            if not response.is_success():
                cls.conf.log.error(
                    f"ali_payment_refund fail: "
                    f"{response.code}, {response.msg}, {response.sub_code}, {response.sub_msg}"
                )
                return False, json_parse(response.body)
            return True, json_parse(response.body)
