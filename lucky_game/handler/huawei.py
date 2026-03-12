from nsanic.libs.component import LogMeta
from nsanic.libs.tool import http_post, http_get, json_parse
from lucky_game.config import conf_srv, ConfSrv
from common.public.conf import HuaweiConf
from lucky_game.model_rc.order import OrderRC
from lucky_game.const import OrderStatus
import time
import json
import jwt
from jwt import algorithms
import hashlib


class Huawei(LogMeta):
    conf: ConfSrv = conf_srv

    @classmethod
    async def oauth_token(cls, code: str):
        params = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": HuaweiConf.APP_ID,
            "client_secret": HuaweiConf.APP_SECRET,
            "redirect_uri": HuaweiConf.REDIRECT_URI,
        }
        cls.log_info(f"华为登录换取token参数={{{'client_id': '{HuaweiConf.APP_ID}', 'redirect_uri': '{HuaweiConf.REDIRECT_URI}'}}}")
        resp = await http_post(HuaweiConf.OAUTH_TOKEN_URL, params)
        data = json_parse(resp)
        cls.log_info(f"华为登录token响应={data}")
        return data

    @classmethod
    async def userinfo(cls, access_token: str):
        url = f"{HuaweiConf.USERINFO_URL}?access_token={access_token}"
        resp = await http_get(url)
        data = json_parse(resp)
        cls.log_info(f"华为用户信息响应={data}")
        return data


class HuaweiPay(LogMeta):
    conf: ConfSrv = conf_srv
    JWKS_CACHE = None
    JWKS_TIME = 0
    ORDER_STATUS_QUERY_PATH = "/order/harmony/v1/application/order/status/query"
    ORDER_SHIPPED_CONFIRM_PATH = "/order/harmony/v1/application/purchase/shipped/confirm"

    @classmethod
    async def _get_jwks(cls):
        now = int(time.time())
        if cls.JWKS_CACHE and now - cls.JWKS_TIME < 3600:
            return cls.JWKS_CACHE
        url = getattr(HuaweiConf, "JWKS_URL", "") or ""
        if not url:
            return {}
        resp = await http_get(url)
        data = json_parse(resp)
        cls.JWKS_CACHE = data or {}
        cls.JWKS_TIME = now
        return cls.JWKS_CACHE

    @classmethod
    async def verify(cls, order_no: str, purchase_token: str, product_id: str = ""):
        if not purchase_token:
            return False, "缺少purchase_token", {}
        mask_token = f"{purchase_token[:10]}****" if isinstance(purchase_token, str) else ""
        cls.log_info(f"华为支付校验开始 order_no={order_no}, product_id={product_id}, token前缀={mask_token}")
        kid = None
        try:
            header = jwt.get_unverified_header(purchase_token)
            kid = header.get("kid")
        except Exception as e:
            cls.log_err(f"解析JWT头失败 {e}")
        cls.log_info(f"JWT头解析完成 kid={kid}")
        pub_key = None
        if kid:
            jwks = await cls._get_jwks()
            keys = jwks.get("keys") or []
            cls.log_info(f"拉取JWKS完成 keys数量={len(keys)}")
            for k in keys:
                if k.get("kid") == kid:
                    pub_key = algorithms.RSAAlgorithm.from_jwk(json.dumps(k))
                    break
            cls.log_info(f"公钥匹配结果 是否找到={pub_key is not None}")
        options = {"require": ["exp", "iat"], "verify_exp": True}
        aud = HuaweiConf.APP_ID or None
        iss_expected = getattr(HuaweiConf, "IAP_ISS", "") or None
        try:
            payload = jwt.decode(
                purchase_token,
                pub_key,
                algorithms=["RS256"],
                audience=aud,
                options=options
            ) if pub_key else jwt.decode(purchase_token, options={"verify_signature": False})
        except Exception as e:
            cls.log_err(f"JWT校验失败 {e}")
            return False, "校验失败", {}
        cls.log_info(f"JWT解析成功 payload部分={{'iss': '{payload.get('iss')}', 'aud': '{payload.get('aud')}', 'orderId': '{payload.get('orderId') or payload.get('order_id')}', 'productId': '{payload.get('productId') or payload.get('product_id')}', 'purchaseState': '{payload.get('purchaseState')}'}}")
        if iss_expected and payload.get("iss") != iss_expected:
            cls.log_err(f"签发方不匹配 期望={iss_expected}, 实际={payload.get('iss')}")
            return False, "签发方不匹配", {}
        claim_order = payload.get("orderId") or payload.get("order_id") or order_no
        claim_product = payload.get("productId") or payload.get("product_id") or product_id
        purchase_state = payload.get("purchaseState")
        purchase_time = payload.get("purchaseTime") or payload.get("purchase_time")
        # 基础字段校验
        if product_id and claim_product and claim_product != product_id:
            cls.log_err(f"商品不匹配 期望={product_id}, 实际={claim_product}")
            return False, "商品不匹配", {}
        if order_no and claim_order and claim_order != order_no:
            order_to_update = order_no
        else:
            order_to_update = claim_order or order_no
        # 判定支付成功（purchaseState==0 视为成功；若字段不存在则默认成功）
        if purchase_state is not None and int(purchase_state) != 0:
            cls.log_info(f"订单未完成 purchase_state={purchase_state} order_no={order_to_update}")
            return False, "订单未完成", {"order_no": order_to_update, "product_id": claim_product, "purchase_state": purchase_state}
        cls.log_info(f"订单校验成功 准备更新订单状态为已支付 order_no={order_to_update}, product_id={claim_product}, purchase_time={purchase_time}")
        return True, "ok", {"order_no": order_to_update, "product_id": claim_product, "purchase_time": purchase_time}

    @classmethod
    async def query_order_status(cls, order_no: str, product_id: str, purchase_token: str):
        url = f"{getattr(HuaweiConf, 'IAP_URL_ROOT', 'https://iap.cloud.huawei.com')}{cls.ORDER_STATUS_QUERY_PATH}"
        body = {
            "purchaseToken": purchase_token,
            "purchaseOrderId": order_no,
        }
        jwt_token = cls._gen_iap_jwt(body)
        if not jwt_token:
            return False, "JWT生成失败", {}
        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "Authorization": f"Bearer {jwt_token}"
        }
        cls.log_info(f"查询鸿蒙订单状态 请求 url={url}, 参数={{'purchaseOrderId': '{order_no}', 'token前缀': '{purchase_token[:10] if isinstance(purchase_token,str) else ''}****'}}")
        try:
            resp = await http_post(url, body, headers=headers)
            data = json_parse(resp)
            cls.log_info(f"查询鸿蒙订单状态 响应={data}")
            if not isinstance(data, dict):
                return False, "响应异常", {}
            state = data.get("orderStatus") or data.get("orderState") or data.get("purchaseState") or data.get("state")
            success = str(state) == "0" or str(state).lower() in ("success", "paid", "shipped")
            return success, "ok" if success else "未完成", {"state": state, "detail": data}
        except Exception as e:
            cls.log_err(f"查询订单状态异常 {e}")
            return False, "查询异常", {}

    @classmethod
    async def confirm_shipped(cls, order_no: str, purchase_token: str):
        url = f"{getattr(HuaweiConf, 'IAP_URL_ROOT', 'https://iap.cloud.huawei.com')}{cls.ORDER_SHIPPED_CONFIRM_PATH}"
        body = {
            "purchaseToken": purchase_token,
            "purchaseOrderId": order_no,
        }
        jwt_token = cls._gen_iap_jwt(body)
        if not jwt_token:
            return False, "JWT生成失败", {}
        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "Authorization": f"Bearer {jwt_token}"
        }
        cls.log_info(f"确认发货 请求 url={url}, 参数={{'purchaseOrderId': '{order_no}', 'token前缀': '{purchase_token[:10] if isinstance(purchase_token,str) else ''}****'}}")
        try:
            resp = await http_post(url, body, headers=headers)
            data = json_parse(resp)
            cls.log_info(f"确认发货 响应={data}")
            if not isinstance(data, dict):
                return False, "响应异常", {}
            code = str(data.get("code") or data.get("retCode") or "").lower()
            ok = code in ("0", "success", "ok")
            return ok, "ok" if ok else "确认失败", {"detail": data}
        except Exception as e:
            cls.log_err(f"确认发货异常 {e}")
            return False, "确认异常", {}
    @classmethod
    def _gen_iap_jwt(cls, body: dict) -> str:
        try:
            body_str = json.dumps(body, ensure_ascii=False)
            digest = hashlib.sha256(body_str.encode("utf-8")).hexdigest()
            now = int(time.time())
            active = getattr(HuaweiConf, "IAP_JWT_ACTIVE_SECONDS", 3600) or 3600
            payload = {
                "iss": getattr(HuaweiConf, "IAP_ISSUER_ID", ""),
                "aud": "iap-v1",
                "iat": now,
                "exp": now + active,
                "aid": getattr(HuaweiConf, "APP_ID", ""),
                "digest": digest,
            }
            headers = {
                "alg": "ES256",
                "typ": "JWT",
                "kid": getattr(HuaweiConf, "IAP_KEY_ID", ""),
            }
            pri_key = getattr(HuaweiConf, "IAP_PRI_KEY", "")
            if not pri_key:
                cls.log_err("IAP私钥未配置")
                return ""
            token = jwt.encode(payload, pri_key, algorithm="ES256", headers=headers)
            return token
        except Exception as e:
            cls.log_err(f"生成IAP JWT失败 {e}")
            return ""
