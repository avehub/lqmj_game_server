"""
实名认证
"""
import asyncio
import base64
import binascii
import os
from Crypto.Cipher import AES
from nsanic.libs import tool_dt
from nsanic.libs.tool import http_post, http_get, json_parse, json_encode
from common.public.conf import CertificationConf
from common.utils.utils import UtilsTool

APPID = CertificationConf.APPID
SECRET_KEY = CertificationConf.SECRET_KEY
BIZ_ID = CertificationConf.BIZ_ID  # 游戏备案识别码（bizId）
CODE_SUCCESS = 0  # 成功


class AesGcm(object):
    def __init__(self, key):
        self.key = key  # 秘钥
        self.MODE = AES.MODE_GCM
        self.iv = os.urandom(12)

    def aes_encrypt(self, params):
        aes = AES.new(binascii.unhexlify(self.key), self.MODE, self.iv)
        params, tag = aes.encrypt_and_digest(json_encode(params, u_byte=True))
        base64_data = self.iv + params + tag
        encrypted_text = str(base64.b64encode(base64_data), encoding='utf-8')
        return encrypted_text

    def aes_decrypt(self, encrypted_text):
        encrypted_text = base64.b64decode(encrypted_text)
        cipher = AES.new(binascii.unhexlify(self.key), self.MODE, encrypted_text[:12])
        cc = cipher.decrypt_and_verify(encrypted_text[12:-16], encrypted_text[-16:])
        return json_parse(cc)


async def do_shi_ming_check(real_name, id_num, ai, test_code=""):
    """
    实名认证
    文档说明：https://wlc.nppa.gov.cn/fcm_company/index.html#/technical-support/document
    """
    aesobject = AesGcm(SECRET_KEY)
    data = {
        "ai": str(ai),  # 在游戏内部对应的唯一标识，该标识将作为实名认证结果查询的唯一依据
        "name": real_name,
        "idNum": id_num
    }
    aes_gcm = aesobject.aes_encrypt(data)
    body_data = '{"data":"%s"}' % aes_gcm  # 国家游戏防沉迷的api试了不能进行json.dumps()
    # 加入请求头报文
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "appId": APPID,
        "bizId": BIZ_ID,
        "timestamps": str(tool_dt.cur_time(ms=True))
    }
    # 对请求头报文排序并排除 不必要的字段进行字符串拼接
    params_str = "".join([
        "%s%s" % i for i in
        sorted(headers.items(), key=lambda d: d[0]) if i[0] not in ["Content-Type"] or []
    ])
    headers["sign"] = UtilsTool.calc_hash("".join([SECRET_KEY, params_str, body_data]), "sha256")
    # url = f"https://wlc.nppa.gov.cn/test/authentication/check/{test_code}"
    url = "https://api.wlc.nppa.gov.cn/idcard/authentication/check"
    req_res = await http_post(url, param=body_data, headers=headers, jsparse=False)
    data = json_parse(req_res)  # '{"errcode":1005,"errmsg":"SYS REQ IP ERROR"}'
    errcode = data.get('errcode')  # 响应结果：0表示请求成功
    result = False
    if errcode == CODE_SUCCESS:
        status = data.get('result').get('status')  # 认证结果：0认证成功, 1认证中, 2认证失败
        if status == CODE_SUCCESS:
            result = True
    return result, data


async def do_shi_ming_query(ai, test_code=""):
    """ 查询实名 """
    # 加入请求头报文
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "appId": APPID,
        "bizId": BIZ_ID,
        "timestamps": str(tool_dt.cur_time(ms=True)),
        "ai": ai
    }
    # 对请求头报文排序并排除 不必要的字段进行字符串拼接
    params_str = "".join([
        "%s%s" % i for i in
        sorted(headers.items(), key=lambda d: d[0]) if i[0] not in ["Content-Type"] or []
    ])
    headers["sign"] = UtilsTool.calc_hash("".join([SECRET_KEY, params_str]), "sha256")
    url = f"http://api2.wlc.nppa.gov.cn/idcard/authentication/query?ai={ai}"
    # url = f"https://wlc.nppa.gov.cn/test/authentication/query/{test_code}?ai={ai}"
    response = await http_get(url, headers=headers)
    print(response)


async def do_shi_ming_update(index, hui_hua_id, offline, is_guest, dev_mark, pi, test_code=""):
    """ 数据上报接口 """
    aesobject = AesGcm(SECRET_KEY)
    collections = []

    collect = {
        "no": index,  # 相当于index
        "si": hui_hua_id,  # 会话ID
        "bt": offline,  # 0 上线  1下线
        "ot": tool_dt.cur_time(),
        "ct": is_guest,  # 2 游客 0 认证
        "di": dev_mark,  # 设备标识
        "pi": pi  # 已通过实名认证用户的唯一标识，已认证通过用户必填，由check接口返回
    }
    collections.append(collect)
    data = {"collections": collections}
    aes_gcm = aesobject.aes_encrypt(data)
    body_data = '{"data":"%s"}' % aes_gcm  # 国家游戏防沉迷的api试了不能进行json.dumps()
    # 加入请求头报文
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "appId": APPID,
        "bizId": BIZ_ID,
        "timestamps": str(tool_dt.cur_time(ms=True))
    }

    # 对请求头报文排序并排除 不必要的字段进行字符串拼接
    params_str = "".join([
        "%s%s" % i for i in
        sorted(headers.items(), key=lambda d: d[0]) if i[0] not in ["Content-Type"] or []
    ])
    headers["sign"] = UtilsTool.calc_hash("".join([SECRET_KEY, params_str, body_data]), "sha256")
    url = "http://api2.wlc.nppa.gov.cn/behavior/collection/loginout"
    # url = f"https://wlc.nppa.gov.cn/test/collection/loginout/{test_code}"
    res = await http_post(url, param=body_data, headers=headers, jsparse=False)
    print(res)


if __name__ == '__main__':
    # asyncio.run(do_shi_ming_check("张富进", 522322199611281331, 1000109, "F4qnR7"))
    asyncio.run(do_shi_ming_query('1111'))
