#!/usr/bin/env python
# -*- encoding:utf-8 -*-

""" 对公众平台发送给公众账号的消息加解密示例代码.
@copyright: Copyright (c) 1998-2023 Tencent Inc.

"""
# ------------------------------------------------------------------------

import base64
import json
import string
import random
import hashlib
import time
import struct
from Crypto.Cipher import AES
from nsanic.libs.tool import json_parse, json_encode
import socket
# import sys
# import codecs

# sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
"""
关于Crypto.Cipher模块，ImportError: No module named 'Crypto'解决方案
请到官方网站 https://www.dlitz.net/software/pycrypto/ 下载pycrypto。
下载后，按照README中的“Installation”小节的提示进行pycrypto安装。
"""

WXBizMsgCrypt_OK = 0
WXBizMsgCrypt_ValidateSignature_Error = -40001
WXBizMsgCrypt_ParseJson_Error = -40002
WXBizMsgCrypt_ComputeSignature_Error = -40003
WXBizMsgCrypt_IllegalAesKey = -40004
WXBizMsgCrypt_ValidateAppid_Error = -40005
WXBizMsgCrypt_EncryptAES_Error = -40006
WXBizMsgCrypt_DecryptAES_Error = -40007
WXBizMsgCrypt_IllegalBuffer = -40008
WXBizMsgCrypt_EncodeBase64_Error = -40009
WXBizMsgCrypt_DecodeBase64_Error = -40010
WXBizMsgCrypt_GenReturnJson_Error = -40011


class FormatException(Exception):
    pass


def throw_exception(message, exception_class=FormatException):
    """my define raise exception function"""
    raise exception_class(message)


class SHA1:
    """计算公众平台的消息签名接口"""

    def getSHA1(self, token, timestamp, nonce, encrypt):
        """用SHA1算法生成安全签名
        @param token:  票据
        @param timestamp: 时间戳
        @param encrypt: 密文
        @param nonce: 随机字符串
        @return: 安全签名
        """
        try:
            sortlist = [token, timestamp, nonce, encrypt]
            sortlist.sort()
            sha = hashlib.sha1()
            sha.update("".join(sortlist).encode())
            return WXBizMsgCrypt_OK, sha.hexdigest()
        except Exception as e:
            print(e)
            return WXBizMsgCrypt_ComputeSignature_Error, None


class JSONParse:
    """提供提取消息格式中的密文及生成回复消息格式的接口"""

    def extract(self, json_text):
        """提取出 json 数据包中的加密消息
        @param json_text: 待提取的 json 字符串
        @return: 提取出的加密消息字符串
        """
        try:
            json_data = json_parse(json_text)
            encrypt = json_data.get("Encrypt")
            to_user_name = json_data.get("ToUserName")
            return WXBizMsgCrypt_OK, encrypt, to_user_name
        except Exception as e:
            print(e)
            return WXBizMsgCrypt_ParseJson_Error, None, None

    def generate(self, encrypt, signature, timestamp, nonce):
        """生成 json 消息
        @param encrypt: 加密后的消息密文
        @param signature: 安全签名
        @param timestamp: 时间戳
        @param nonce: 随机字符串
        @return: 生成的 json 字符串
        """
        resp_dict = {
            "Encrypt": encrypt,
            "MsgSignature": signature,
            "TimeStamp": timestamp,
            "Nonce": nonce,
        }
        resp_json = json_encode(resp_dict)
        return resp_json


class PKCS7Encoder():
    """提供基于PKCS7算法的加解密接口"""

    block_size = 32

    def encode(self, text):
        """ 对需要加密的明文进行填充补位
        @param text: 需要进行填充补位操作的明文
        @return: 补齐明文字符串
        """
        text_length = len(text)
        # 计算需要填充的位数
        amount_to_pad = self.block_size - (text_length % self.block_size)
        if amount_to_pad == 0:
            amount_to_pad = self.block_size
        # 获得补位所用的字符
        pad = chr(amount_to_pad)
        return text + (pad * amount_to_pad).encode()

    def decode(self, decrypted):
        """删除解密后明文的补位字符
        @param decrypted: 解密后的明文
        @return: 删除补位字符后的明文
        """
        pad = ord(decrypted[-1])
        if pad < 1 or pad > 32:
            pad = 0
        return decrypted[:-pad]


class Prpcrypt(object):
    """提供接收和推送给公众平台消息的加解密接口"""

    def __init__(self, key):
        # self.key = base64.b64decode(key+"=")
        self.key = key
        # 设置加解密模式为AES的CBC模式
        self.mode = AES.MODE_CBC

    def encrypt(self, text, appid):
        """对明文进行加密
        @param text: 需要加密的明文
        @return: 加密得到的字符串
        """
        # 16位随机字符串添加到明文开头
        text = self.get_random_str().encode() + struct.pack("I",
                                                            socket.htonl(len(text))) + text.encode() + appid.encode()
        pkcs7 = PKCS7Encoder()
        text = pkcs7.encode(text)
        # 加密
        cryptor = AES.new(self.key, self.mode, self.key[:16])
        try:
            ciphertext = cryptor.encrypt(text)
            # 使用BASE64对加密后的字符串进行编码
            return WXBizMsgCrypt_OK, base64.b64encode(ciphertext).decode()
        except Exception as e:
            print(e)
            return WXBizMsgCrypt_EncryptAES_Error, None

    def decrypt(self, text, appid):
        """对解密后的明文进行补位删除
        @param text: 密文
        @return: 删除填充补位后的明文
        """
        try:
            cryptor = AES.new(self.key, self.mode, self.key[:16])
            # 使用BASE64对密文进行解码，然后AES-CBC解密
            plain_text = cryptor.decrypt(base64.b64decode(text.encode()))
        except Exception as e:
            # print (e)
            return WXBizMsgCrypt_DecryptAES_Error, None
        try:
            pad = plain_text[-1]
            # 去掉补位字符串
            # pkcs7 = PKCS7Encoder()
            # plain_text = pkcs7.encode(plain_text)
            # 去除16位随机字符串
            content = plain_text[16:-pad]
            json_len = socket.ntohl(struct.unpack("I", content[: 4])[0])
            json_content = content[4: json_len + 4].decode()
            from_appid = content[json_len + 4:].decode()
        except Exception as e:
            print(e)
            return WXBizMsgCrypt_IllegalBuffer, None
        if from_appid != appid:
            return WXBizMsgCrypt_ValidateAppid_Error, None
        return 0, json_content

    def get_random_str(self):
        """ 随机生成16位字符串
        @return: 16位字符串
        """
        rule = string.ascii_letters + string.digits
        str = random.sample(rule, 16)
        return "".join(str)


class WXBizMsgCrypt(object):
    # 构造函数
    # @param sToken: 公众平台上，开发者设置的Token
    # @param sEncodingAESKey: 公众平台上，开发者设置的EncodingAESKey
    # @param sAppId: 企业号的AppId
    def __init__(self, sToken, sEncodingAESKey, sAppId):
        try:
            self.key = base64.b64decode(sEncodingAESKey + "=")
            assert len(self.key) == 32
        except:
            throw_exception("[error]: EncodingAESKey unvalid !", FormatException)
        # return WXBizMsgCrypt_IllegalAesKey)
        self.token = sToken
        self.appid = sAppId

    def EncryptMsg(self, sReplyMsg, sNonce, timestamp=None):
        # 将公众号回复用户的消息加密打包
        # @param sReplyMsg: 企业号待回复用户的消息，json格式的字符串
        # @param sTimeStamp: 时间戳，可以自己生成，也可以用URL参数的timestamp,如为None则自动用当前时间
        # @param sNonce: 随机串，可以自己生成，也可以用URL参数的nonce
        # sEncryptMsg: 加密后的可以直接回复用户的密文，包括msg_signature, timestamp, nonce, encrypt的json格式的字符串,
        # return：成功0，sEncryptMsg,失败返回对应的错误码None
        pc = Prpcrypt(self.key)
        ret, encrypt = pc.encrypt(sReplyMsg, self.appid)
        if ret != 0:
            return ret, None
        if timestamp is None:
            timestamp = str(int(time.time()))
        # 生成安全签名
        sha1 = SHA1()
        ret, signature = sha1.getSHA1(self.token, timestamp, sNonce, encrypt)
        if ret != 0:
            return ret, None
        jsonParse = JSONParse()
        return ret, jsonParse.generate(encrypt, signature, timestamp, sNonce)

    def DecryptMsg(self, sPostData, sMsgSignature, sTimeStamp, sNonce):
        # 检验消息的真实性，并且获取解密后的明文
        # @param sMsgSignature: 签名串，对应URL参数的msg_signature
        # @param sTimeStamp: 时间戳，对应URL参数的timestamp
        # @param sNonce: 随机串，对应URL参数的nonce
        # @param sPostData: 密文，对应POST请求的数据
        #  json_content: 解密后的原文，当return返回0时有效
        # @return: 成功0，失败返回对应的错误码
        # 验证安全签名
        jsonParse = JSONParse()
        ret, encrypt, touser_name = jsonParse.extract(sPostData)
        if ret != 0:
            return ret, None
        sha1 = SHA1()
        ret, signature = sha1.getSHA1(self.token, sTimeStamp, sNonce, encrypt)
        if ret != 0:
            return ret, None
        if not signature == sMsgSignature:
            return WXBizMsgCrypt_ValidateSignature_Error, None
        pc = Prpcrypt(self.key)
        ret, json_content = pc.decrypt(encrypt, self.appid)
        return ret, json_content


if __name__ == "__main__":
    """ 
    1.第三方回复加密消息给公众平台；
    2.第三方收到公众平台发送的消息，验证消息的安全性，并对消息进行解密。
    """
    encodingAESKey = "asfxwd8i2bVlSjPLDrHUju1BjAr7OCI6KXBge2KAfXI"
    to_json = "{\"ToUserName\":\"xxoo\";\"FromUserName\":\"xxoo\";\"CreateTime\":1701774202;\"MsgType\":\"event\";\"MiniGame\":{\"Payload\":\"xxoo\";\"PayEventSig\":\"xxoo\";\"IsMock\":false};\"Event\":\"xxoo\"}"
    token = "WY6zk8qFjf7fjKYcj75mjPmzaoq1Qpk6"
    nonce = "3160719712"
    timestamp = "1701774202"
    appid = "wx953sji00bad5916c"
    # 测试加密接口
    encryp_test = WXBizMsgCrypt(token, encodingAESKey, appid)
    ret, encrypt_json = encryp_test.EncryptMsg(to_json, nonce, timestamp)
    print(ret, encrypt_json)

    # 测试解密接口
    msg_sign = "53fffd78b2a9b9d7672786eac2eb850d7d7ed0b9"
    from_json = "{\"Encrypt\":\"MfR8Y/iphwad9qCYlUCJyeCVpgj096PXvXBCxJKZjjkdONbWRyiu50x3tz9CiperCGCCcFxFQGCDK1IwnizJANjMGMuMd600tNnvIZR0aSbgi7OJcCWnhVlzMadtwRZVfiwFR+0uNtSyXNdCtTtHndpNLEWS7SrY+d3WY/G9OZDRQHSl0Az8rm2HB5oTN2QSbTDmQJ5zUiypkwltnj6mJpjF8KaYtwFCQnQdVGF7LqAAU6YFky8gx4IkCakJ37KrrlQsai5OmxKQBo90FPoIrNFNRzUHxGA9KE6qtljiZzE=\", \"ToUserName\":\"gh_b12b34480e95\"}"
    decrypt_test = WXBizMsgCrypt(token, encodingAESKey, appid)
    ret, decryp_json = decrypt_test.DecryptMsg(from_json, msg_sign, timestamp, nonce)
    print(ret, decryp_json)
    res = json.loads(decryp_json)
    print(res, type(res))
