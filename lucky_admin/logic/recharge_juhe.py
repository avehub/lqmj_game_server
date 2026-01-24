from nsanic.libs.tool import http_get, json_parse
from nsanic.libs.component import LogMeta
from common.public.conf import JuheRechargeConf
from common.utils.utils import UtilsTool


class RechargeJuhe(LogMeta):
    @classmethod
    async def get_conf(cls):
        return {"url": JuheRechargeConf.URL, "key": JuheRechargeConf.KEY, "openid": getattr(JuheRechargeConf, "OPEN_ID", "") or getattr(JuheRechargeConf, "ju_he_openid", "")}

    @classmethod
    async def recharge(cls, phone: str, amount: int, order_id: str):
        conf = await cls.get_conf()
        key = conf.get("key")
        url = conf.get("url")
        openid = conf.get("openid")
        if not key or not url:
            cls.log_err("话费充值配置缺失")
            return False, "配置缺失", {}
        if not openid:
            cls.log_err("话费充值OPENID缺失")
            return False, "配置缺失", {}
        sign_str = f"{openid}{key}{phone}{amount}{order_id}"
        sign = UtilsTool.calc_hash(sign_str, htype='md5')
        base_url = url.split('?')[0]
        params = {
            "key": key,
            "phoneno": phone,
            "cardnum": amount,
            "orderid": order_id,
            "sign": sign,
            "openid": openid,
        }
        try:
            mask_key = f"{key[:4]}****"
            mask_phone = f"{phone[:3]}****{phone[-4:]}" if isinstance(phone, str) and len(phone) >= 7 else phone
            log_params = {**params, "key": mask_key, "phoneno": mask_phone, "sign": f"{sign[:6]}****"}
            cls.log_info(f"话费充值请求 url={base_url}, 参数={log_params}")
            resp = await http_get(base_url, params=params)
            cls.log_info(f"话费充值响应原始数据={resp}")
            data = json_parse(resp)
            cls.log_info(f"话费充值响应解析结果={data}")
            if not isinstance(data, dict):
                return False, "响应异常", {}
            error_code = data.get("error_code")
            reason = data.get("reason")
            if error_code == 0:
                result = data.get("result") or {}
                return True, "ok", result
            cls.log_err(f"话费充值失败 code={error_code} reason={reason}")
            return False, reason or "失败", data
        except Exception as e:
            cls.log_err(f"调用话费充值接口异常: {e}")
            return False, "异常", {}

    @classmethod
    async def query_status(cls, order_id: str):
        conf = await cls.get_conf()
        key = conf.get("key")
        if not key:
            cls.log_err("查询充值状态配置缺失")
            return False, "配置缺失", {}
        base_url = "http://op.juhe.cn/ofpay/mobile/ordersta"
        params = {
            "key": key,
            "orderid": order_id,
        }
        try:
            mask_key = f"{key[:4]}****"
            cls.log_info(f"查询话费充值状态 url={base_url}, 参数={{'key': '{mask_key}', 'orderid': '{order_id}'}}")
            resp = await http_get(base_url, params=params)
            cls.log_info(f"查询状态响应原始数据={resp}")
            data = json_parse(resp)
            cls.log_info(f"查询状态响应解析结果={data}")
            if not isinstance(data, dict):
                return False, "响应异常", {}
            error_code = data.get("error_code")
            reason = data.get("reason")
            if error_code != 0:
                return False, f"错误码:{error_code} 原因:{reason}", data
            result = data.get("result") or {}
            return True, "ok", result
        except Exception as e:
            cls.log_err(f"查询充值状态接口异常: {e}")
            return False, "异常", {}
