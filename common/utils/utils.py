import asyncio
import string
from datetime import datetime
from typing import AnyStr
import hashlib
import hmac

import aiofiles
import httpx
import math
import numpy as np
import orjson
import random
import re
import traceback
import ujson
from nsanic.libs.tool import http_get, json_parse

from .meta_class import NoInstances
import base64
import binascii
from typing import Optional


class UtilsTool(metaclass=NoInstances):
    @staticmethod
    def generate_invite_code(cls, length=10):
        # 定义可能出现的字符，包括大小写字母和数字
        characters = string.ascii_letters + string.digits
        # 生成指定长度的随机字符串
        invite_code = ''.join(random.choice(characters) for _ in range(length))
        return invite_code

    @staticmethod
    def filter_emoji(input_str, replace='*'):
        """
        过滤表情
        replace: 未匹配到的替换为
        滤掉非中文、中文字符、英文大小写、数字和常规符号之外的字符
        """
        filtered_str = re.sub(r"[^\u4e00-\u9fa5\w.。,;:'\"?？!！()\-+=@#&<>/]", replace, input_str)
        return filtered_str

    @staticmethod
    def check_id_card(id_number: str):
        """
        :param id_number: 字符串，待验证的身份证号码
        :return: 布尔值，如果身份证号码合法返回True，否则返回False
        只接受1900-1999年或2000-2099年之间的出生日期
        """
        # 1.身份证号码正则表达式，基本格式验证
        pattern = r'^\d{6}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])\d{3}(\d|X)$'
        if not re.match(pattern, id_number):
            return False  # 格式不匹配

        # 2.身份证号码转为全数字，X替换为10
        end_num = id_number[-1]
        id_number = id_number.upper().replace('X', '10')

        # 3.计算校验码
        # 分配权重：对身份证号码的前17位数字，分别赋予不同的权重因子，从第一位到第十七位的权重依次为：
        weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
        # 将每一位身份证号码数字与其对应的权重因子相乘，然后求所有乘积的和再与11取余数
        check_sum = sum(int(id_number[i]) * weights[i] for i in range(17)) % 11
        # 4.身份证最后一位校验码的字符序列'10X98765432'，这个序列是按照模11运算规则预先设定好的映射关系
        check_digit = '10X98765432'[check_sum]

        # 5.检查计算的校验码是否与身份证最后一位相符
        return check_digit == end_num

    @staticmethod
    def validate_name(name):
        """
        验证输入的姓名是否只包含汉字。
        :param name: 字符串，待验证的姓名
        :return: 布尔值，如果姓名只包含汉字返回True，否则返回False
        """
        # 正则表达式，匹配全是汉字的字符串
        pattern = re.compile(r'^[\u4e00-\u9fa5]+$')
        return bool(pattern.match(name))

    @staticmethod
    def contains_keywords(text, keywords):
        """ text中是否包含关键字 """
        pattern = '|'.join(map(re.escape, keywords))
        if re.search(pattern, text):
            return True
        else:
            return False

    @staticmethod
    def determine_gender(id_number):
        """ 根据身份证识别性别 """
        sex_num = id_number[-2]
        if int(sex_num) % 2 == 0:
            return 2  # 女
        return 1  # 男

    @staticmethod
    def determine_age(id_number):
        """ 根据身份证识别年龄 """
        # 提取出生日期
        birth_year = int(id_number[6:6 + 4])
        birth_month = int(id_number[10:10 + 2])
        birth_day = int(id_number[12:12 + 2])

        # 获取当前日期
        today = datetime.today()
        current_year = today.year
        current_month = today.month
        current_day = today.day

        # 计算年龄
        age = current_year - birth_year
        if (current_month, current_day) < (birth_month, birth_day):
            age -= 1

        return age

    @staticmethod
    def mask_id_card(id_number: str):
        if not id_number:
            return id_number
        mask_id_card = "*" * 6 + id_number[6:14] + '*' * 4
        return mask_id_card

    @staticmethod
    def get_percent(float_num: float or int, keep_digit=".2f"):
        """
        获取百分数: 去除尾部0，当无小数点时去除.
        keep_digit: 保留位数
        """
        num_str = f"{float_num: {keep_digit}}".rstrip('0').rstrip('.')
        num_str = num_str.strip()
        return f"{num_str}%"

    @staticmethod
    def to_py(data: AnyStr, default=None, log_fun=None):
        if isinstance(data, (dict, list, tuple)):
            return data
        try:
            info = orjson.loads(data)
            return info
        except (SyntaxError, ValueError, TypeError):
            err_info = f'解析数据出错, 原数据:{data}, {type(data)}'
            log_fun(err_info) if callable(log_fun) else print(err_info)
        return default

    @staticmethod
    def to_json(item, _type=1) -> AnyStr:
        """
        转换为Json字符串
        `ensure_ascii` 是 一个可选参数，用于控制是否将非 ASCII 字符转义为 ASCII 码。
        _type: 1使用ujson, 2使用orjson
        """
        if isinstance(item, bytes):
            item = item.decode('utf-8')
        try:
            if _type == 1:
                return orjson.dumps(item)
            return ujson.dumps(item, ensure_ascii=False)
        except (SyntaxError, ValueError, TypeError):
            return ""

    @staticmethod
    def packet_command(service_type, cmd, digit=3):
        """
        打包command命令
        :param service_type:服务类型
        :param cmd:指令
        :param digit:表示 服务类型 与 指令 可以支持的位数
        :return:通过服务类型对cmd命令进行打包传送
        """
        assert service_type > 0 and cmd >= 0
        num = 10 ** digit
        return service_type * num + cmd

    @staticmethod
    def explode_command(command, digit=3):
        """
        解析command命令
        :param command: 指令
        :param digit: 表示 服务类型 与 指令 可以支持的位数
        :return: 返回解析结果
        """
        num = 10 ** digit
        cmd = int(command)
        return cmd // num, cmd % num

    @staticmethod
    def get_hash_secrets(key: str, msg: str, extra_str: str = None, secrets_type="md5"):
        """
        获取hash加密值,默认需要密钥和消息作为输入
        用于计算消息 身份 验证代码。
        :param key: 密钥
        :param msg: 主体数据
        :param extra_str:额外数据
        :param secrets_type:默认md5
            支持的哈希算法包括：md5、sha1、sha224、sha256、sha384和`sha512`。
        :return:
        """
        key = key.encode("utf-8")
        md5 = hmac.new(key, msg.encode("utf-8"), digestmod=secrets_type)
        extra_str and md5.update(str(extra_str).encode("utf-8"))
        return md5.hexdigest()

    @staticmethod
    def calc_hash(val: (str, bytes), htype='sha3-256'):
        hash_map = {
            'md5': hashlib.md5,
            'sha1': hashlib.sha1,
            'sha256': hashlib.sha256,
            'sha384': hashlib.sha3_384,
            'sha512': hashlib.sha512,
            'sha3-224': hashlib.sha3_224,
            'sha3-256': hashlib.sha3_256,
            'sha3-384': hashlib.sha3_384,
            'sha3-512': hashlib.sha3_512,
        }
        if not isinstance(val, (str, bytes)):
            val = str(val)
        if isinstance(val, str):
            val = val.encode('utf-8')
        hb = hash_map.get(htype) or hashlib.sha3_256
        return hb(val).hexdigest()

    @staticmethod
    def int_to_bytes(num: int) -> (bytes, int):
        """
        ASCII 使用一个字节（8位）来表示一个字符
        (num.bit_length() + 7): 获取整数 num 的位数
        为什么要加上 7：当除以 8 时，除法的结果会向下取整到最接近的整数。在位数上加上7 是为了确保计算能够向上取整到最接近的 8 的倍数
        主要是为了保证能够得到足够容纳整数二进制表示的字节数。
        digit: 要使用的字节长度
        """
        if num < 1:
            raise OverflowError(f"can't convert negative int to unsigned: {num}")
        digit = (num.bit_length() + 7) // 8
        num_bytes = num.to_bytes(digit, byteorder='big')
        return num_bytes, digit

    @staticmethod
    def bytes_to_int_by_bytes_len(b_data: bytes) -> int:
        """
        根据bytes_len从字节中将int转回
        """
        return int.from_bytes(b_data, byteorder='big')

    @staticmethod
    def num_is_digit(num: int):
        """ 求一个数值有几位，十进制 """
        assert isinstance(num, int) and num > 0
        return int(math.log10(num) + 1)

    @staticmethod
    def parse_msg_by_bytes_old(msg: bytes, log_fun=None) -> (int, int, bytes):
        """ 解析字节消息 """
        # 长度标识固定用1位
        # 长度标识：标识cmd占用多少字节长度
        try:
            cmd_bytes_len = UtilsTool.bytes_to_int_by_bytes_len(msg[:1])
            cmd = UtilsTool.bytes_to_int_by_bytes_len(msg[1:1 + cmd_bytes_len])
            msg = msg[1 + cmd_bytes_len:]
            return UtilsTool.explode_command(cmd), msg
        except Exception as err:
            log_fun(f'{msg}消息解析出错：{err}') if log_fun else print(f'{msg}消息解析出错：{err}')
            return (0, 0), b''

    @staticmethod
    def parse_msg_by_bytes(msg: bytes, log_fun=None) -> tuple[tuple[int, int], bytes]:
        """
        解析内部消息格式：
          [cmd_len:1B][cmd:cmd_len B][uid_len:1B][uid:uid_len B][payload...]

        返回: ((code, uid), payload)
        """
        if len(msg) < 1:  # 至少需要 cmd_len + uid_len 两个字节
            err = "Message too short (<2 bytes)"
            if log_fun:
                log_fun(f"{msg!r} 消息解析出错：{err}")
            else:
                print(f"{msg!r} 消息解析出错：{err}")
            return (0, 0), b''

        mv = memoryview(msg)
        try:
            # 1. 读取 cmd 长度（1字节）
            cmd_len = mv[0]
            if cmd_len == 0:
                raise ValueError("cmd length cannot be zero")
            # 可选：限制最大长度（如 8 或 16），防止恶意数据
            if cmd_len > 16:
                raise ValueError(f"cmd length too large: {cmd_len}")
            # 2. 检查是否有足够字节读取 cmd
            cmd_end = 1 + cmd_len
            # 3. 读取 cmd 并转为 int
            cmd = int.from_bytes(mv[1:cmd_end], 'big')

            # 7. 剩余为 payload
            payload = bytes(mv[cmd_end:])  # 转回 bytes（必要时）
            return UtilsTool.explode_command(cmd), payload

        except (ValueError, IndexError) as e:
            err_msg = f"Parse error: {e}"
            if log_fun:
                log_fun(f"{msg!r} 消息解析出错：{err_msg}")
            else:
                print(f"{msg!r} 消息解析出错：{err_msg}")
            return (0, 0), b''

    @staticmethod
    def pack_msg_by_bytes_old(c_type: int, c_code: int, msg: bytes) -> bytes:
        """ 解析字节消息 """
        # 长度标识固定用1位
        # 长度标识：标识cmd占用多少字节长度
        cmd = UtilsTool.packet_command(c_type, c_code)
        # 1.先获取命令的字节形式、字节长度
        cmd_bytes, use_bytes_len = UtilsTool.int_to_bytes(cmd)
        # 2.再获取命令的 字节长度的 字节形式和长度（一般占1位）
        cmd_len_bytes, cmd_use_bytes_len = UtilsTool.int_to_bytes(use_bytes_len)
        assert cmd_use_bytes_len == 1
        return cmd_len_bytes + cmd_bytes + msg

    @staticmethod
    def pack_msg_by_bytes(c_type: int, c_code: int, msg: bytes) -> bytes:
        cmd = UtilsTool.packet_command(c_type, c_code)
        if cmd < 0:
            raise ValueError("cmd and uid must be non-negative")
        # 1. 转换 cmd 为最小 big-endian bytes
        cmd_bytes = cmd.to_bytes((cmd.bit_length() + 7) // 8 or 1, 'big')
        cmd_len = len(cmd_bytes)
        if cmd_len > 255:
            raise ValueError("cmd too large (exceeds 255 bytes)")
        # 2. 构造消息：长度用单字节表示
        return (
                bytes([cmd_len]) +
                cmd_bytes +
                msg
        )

    @staticmethod
    def pack_inner_msg_old(cmd: int, uid: int, msg: bytes) -> bytes:
        """
        内部消息频道传输
        解析字节消息
        return: cmd字节占用长度 + cmd字节 + uid字节占用长度 + uid字节 + msg字节
        """
        # 长度标识固定用1位
        # 长度标识：标识cmd占用多少字节长度
        # 1.先获取命令的字节形式、字节长度
        cmd_bytes, use_bytes_len = UtilsTool.int_to_bytes(cmd)
        # 2.再获取命令的 字节长度的 字节形式和长度（一般占1位）
        cmd_len_bytes, cmd_len_bytes_len = UtilsTool.int_to_bytes(use_bytes_len)
        assert cmd_len_bytes_len == 1

        # 1.先获取uid的字节形式、字节长度
        uid_bytes, uid_bytes_len = UtilsTool.int_to_bytes(uid)
        # 2.第二个是第一个的 字节长度的 字节形式和长度（一般占1位）
        uid_len_bytes, uid_len_bytes_len = UtilsTool.int_to_bytes(uid_bytes_len)
        assert uid_len_bytes_len == 1

        # cmd字节占用长度 + cmd字节 + uid字节占用长度 + uid字节 + msg字节
        if msg:
            return cmd_len_bytes + cmd_bytes + uid_len_bytes + uid_bytes + msg
        return cmd_len_bytes + cmd_bytes + uid_len_bytes + uid_bytes

    @staticmethod
    def pack_inner_msg(cmd: int, uid: int, msg: bytes) -> bytes:
        """
        打包内部消息：
          [cmd_len:1B][cmd:cmd_len B][uid_len:1B][uid:uid_len B][payload]
        """
        if cmd < 0 or uid < 0:
            raise ValueError("cmd and uid must be non-negative")

        # 1. 转换 cmd 为最小 big-endian bytes
        cmd_bytes = cmd.to_bytes((cmd.bit_length() + 7) // 8 or 1, 'big')
        cmd_len = len(cmd_bytes)
        if cmd_len > 255:
            raise ValueError("cmd too large (exceeds 255 bytes)")

        # 2. 转换 uid 为最小 big-endian bytes
        uid_bytes = uid.to_bytes((uid.bit_length() + 7) // 8 or 1, 'big')
        uid_len = len(uid_bytes)
        if uid_len > 255:
            raise ValueError("uid too large (exceeds 255 bytes)")

        # 3. 构造消息：长度用单字节表示
        return (
                bytes([cmd_len]) +
                cmd_bytes +
                bytes([uid_len]) +
                uid_bytes +
                msg
        )

    @staticmethod
    def parse_inner_msg_old(msg: bytes, log_fun=None) -> (int, int, bytes):
        """
        内部消息频道传输
        解析字节消息
        msg：cmd字节占用长度 + cmd字节 + uid字节占用长度 + uid字节 + msg字节
        """
        # 长度标识固定用1位
        # 长度标识：标识cmd占用多少字节长度
        try:
            # 解码code
            cmd_bytes_len = UtilsTool.bytes_to_int_by_bytes_len(msg[0:1])
            code = UtilsTool.bytes_to_int_by_bytes_len(msg[1: 1 + cmd_bytes_len])

            # 解码uid
            start = 1 + cmd_bytes_len
            end = start + 1
            uid_bytes_len = UtilsTool.bytes_to_int_by_bytes_len(msg[start:end])  # uid字节长度
            uid = UtilsTool.bytes_to_int_by_bytes_len(msg[end:end + uid_bytes_len])
            msg = msg[end + uid_bytes_len:]
            return (code, uid), msg
        except Exception as err:
            log_fun(f'{msg}消息解析出错：{err}') if log_fun else print(f'{msg}消息解析出错：{err}')
            return (0, 0), b''

    @staticmethod
    def parse_inner_msg(msg: bytes, log_fun=None) -> tuple[tuple[int, int], bytes]:
        """
        解析内部消息格式：
          [cmd_len:1B][cmd:cmd_len B][uid_len:1B][uid:uid_len B][payload...]

        返回: ((code, uid), payload)
        """
        if len(msg) < 2:  # 至少需要 cmd_len + uid_len 两个字节
            err = "Message too short (<2 bytes)"
            if log_fun:
                log_fun(f"{msg!r} 消息解析出错：{err}")
            else:
                print(f"{msg!r} 消息解析出错：{err}")
            return (0, 0), b''

        mv = memoryview(msg)
        try:
            # 1. 读取 cmd 长度（1字节）
            cmd_len = mv[0]
            if cmd_len == 0:
                raise ValueError("cmd length cannot be zero")
            # 可选：限制最大长度（如 8 或 16），防止恶意数据
            if cmd_len > 16:
                raise ValueError(f"cmd length too large: {cmd_len}")

            # 2. 检查是否有足够字节读取 cmd
            cmd_end = 1 + cmd_len
            if len(mv) < cmd_end + 1:  # +1 是为了至少有 uid_len 字节
                raise ValueError("Message too short for cmd and uid_len")

            # 3. 读取 cmd 并转为 int
            code = int.from_bytes(mv[1:cmd_end], 'big')

            # 4. 读取 uid 长度
            uid_len = mv[cmd_end]
            if uid_len == 0:
                raise ValueError("uid length cannot be zero")
            if uid_len > 16:
                raise ValueError(f"uid length too large: {uid_len}")

            # 5. 检查是否有足够字节读取 uid
            uid_end = cmd_end + 1 + uid_len
            if len(mv) < uid_end:
                raise ValueError("Message too short for uid")

            # 6. 读取 uid 并转为 int
            uid = int.from_bytes(mv[cmd_end + 1:uid_end], 'big')

            # 7. 剩余为 payload
            payload = bytes(mv[uid_end:])  # 转回 bytes（必要时）

            return (code, uid), payload

        except (ValueError, IndexError) as e:
            err_msg = f"Parse error: {e}"
            if log_fun:
                log_fun(f"{msg!r} 消息解析出错：{err_msg}")
            else:
                print(f"{msg!r} 消息解析出错：{err_msg}")
            return (0, 0), b''

    @staticmethod
    def haversine(lon1, lat1, lon2, lat2) -> int:
        """
        Calculate the great circle distance between two points
        on the earth (specified in decimal degrees)
        计算两个给定的坐标之间的物理距离
        两组经纬度中, 有任意一个值不正确, 则直接返回 -1 为未知距离
        :param lon1: 经度1
        :param lat1: 纬度1
        :param lon2: 经度2
        :param lat2: 纬度2
        :return: number 米
        """
        if lon1 is None or lat1 is None or lon2 is None or lat2 is None:
            return -1
        if lon1 > 180 or lon2 > 180:  # 经度最大值只有180
            return -1
        if lat1 > 90 or lat2 > 90:  # 纬度最大值只有90
            return -1
        # convert decimal degrees to radians（将十进制度数转换为弧度）
        lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])

        # haversine formula（半正矢公式）
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))
        r = 6371.393  # 地球平均半径，单位为公里
        # return c * r
        return int(c * r * 1000)  # 返回单位：meter

    @staticmethod
    def random_choice_num(num_arr: list, rate_arr=None):
        """ 抽取随机数 """
        if not rate_arr:
            rate_arr = []
        if not num_arr:
            return
        if rate_arr:
            extra_num = len(num_arr) - len(rate_arr)
            extra_num > 0 and rate_arr.extend([0 for _ in range(extra_num)])
            if extra_num < 0:
                for _ in range(-1 * extra_num):
                    rate_arr.pop()
        if sum(rate_arr) != 1:
            rate_arr = None
        return np.random.choice(a=num_arr, size=1, replace=True, p=rate_arr)[0]

    @staticmethod
    def select_element_by_prob(prob: dict, size=100):
        """
        按概率取值，各概率值之间相加必须等于size
        elements_prob：ps -> {"element1": 10, "element2": 90}
        size：控制概率总和，一定程度可度量元素重要性
        return: dict key
        """
        if sum(prob.values()) != size:
            raise ValueError(f"请检查概率配比: {prob}")
        for key, val in prob.items():
            if not key:
                raise KeyError(f"参数错误，字典键不能为None、0、False等: {prob}")
            if 0 < val < 1:
                raise ValueError(f"参数错误，概率配比必须为大于1的自然数: {prob}")

        x = random.randint(0, size)
        init_prob = 0
        default_item = None
        sort_elements = sorted(prob.items(), key=lambda e: e[1])
        for item, item_pro in sort_elements:
            init_prob += item_pro
            if init_prob >= x:
                default_item = item
                break
        return default_item or max(prob, key=prob.get)

    @staticmethod
    def remove_by_value(card_data: list, value: int, remove_count=1):
        """
        为-1的时候表示删除全部, 默认为1
        :return: already_remove_count: int
        """
        data_len = len(card_data)
        count = remove_count == -1 and data_len or remove_count

        already_remove_count = 0

        for i in range(0, count):
            if value in card_data:
                card_data.remove(value)
                already_remove_count += 1
            else:
                break
        return already_remove_count

    @staticmethod
    async def get_ip_geo(ip: str, log_fun=None):
        """
        获取IP地址
        文档地址：https://market.aliyun.com/apimarket/detail/cmapi00041272
        """
        # appcode = 'f82d927911064281987670f75d9408ab'  # 欢聚
        # url = 'https://hcapi22.market.alicloudapi.com/ip?ip={0}'.format(ip)

        appcode = 'f82d927911064281987670f75d9408ab'
        url = 'https://ab19.api.huachen.cn/ip?ip={0}'.format(ip)
        header = {"Authorization": 'APPCODE ' + appcode}
        try:
            req_data = await http_get(url, headers=header, log_fun=log_fun)
            data = json_parse(req_data, log_fun=log_fun)
            res = data.get("data") or {}
            return res
        except httpx.ConnectError as e:
            err_info = f"获取ip源失败：{traceback.format_exc()}"
            log_fun(err_info) if callable(log_fun) else print(err_info)
            return {}

    @staticmethod
    def cal_time_old(func):
        """
        计算func耗时
        example:
            @cal_time
            def func():
                ...
            func()
        """

        import time
        if asyncio.iscoroutinefunction(func):
            async def inner(*args, **kwargs):
                s = time.time()
                await func(*args, **kwargs)
                print(f"{func.__name__}耗时：{time.time() - s}")

            return inner

        def inner(*args, **kwargs):
            s = time.time()
            func(*args, **kwargs)
            print(f"{func.__name__}耗时：{time.time() - s}")

        return inner

    @staticmethod
    def cal_time(log_fun=None):
        def out_runtime(func):
            import time
            if asyncio.iscoroutinefunction(func):
                async def inner(*args, **kwargs):
                    s = time.time()
                    await func(*args, **kwargs)
                    if log_fun:
                        return log_fun(f"{func.__name__}耗时：{time.time() - s}")
                    print(f"{func.__name__}耗时：{time.time() - s}")

                return inner

            def inner(*args, **kwargs):
                s = time.time()
                func(*args, **kwargs)
                if log_fun:
                    return log_fun(f"{func.__name__}耗时：{time.time() - s}")
                print(f"{func.__name__}耗时：{time.time() - s}")

            return inner

        return out_runtime

    @staticmethod
    def binary_search(
            li,
            target,
            _property: str = None,
            inner=False,
            min_field='',
            max_field='',
            max_field_inf=False
    ) -> int or None:
        """
        二分查找, x时间复杂度logn, 比普通循环更高效。但若li序列较短，不宜采取该算法
        限制：序列必须有序
        max_field_inf: 最大值为-1时True
        """
        left = 0
        right = len(li) - 1
        if inner:
            if not min_field or not max_field:
                raise ValueError("search inner min_field and max_field must have value")
            while left <= right:
                mid = (left + right) // 2
                min_element = li[mid].get(min_field)
                max_element = li[mid].get(max_field)
                if min_element <= target and (max_element >= target or (max_field_inf and max_element == -1)):
                    return mid
                elif max_element > target:
                    right = mid - 1
                else:
                    left = mid + 1
            return

        if _property:
            while left <= right:
                mid = (left + right) // 2
                cur_element = li[mid].get(_property)
                if cur_element == target:
                    return mid
                elif cur_element > target:
                    right = mid - 1
                else:
                    left = mid + 1
            return

        while left <= right:
            mid = (left + right) // 2
            if li[mid] == target:
                return mid
            elif li[mid] > target:
                right = mid - 1
            else:
                left = mid + 1
        return

    @staticmethod
    def check_float(data):
        # 从字符串转换成double
        if not data:
            return 0.0
        try:
            return float(data)
        except Exception as data:
            print(data)
        return 0.0

    @staticmethod
    def base64_to_bytes(base64_string: str,
                        handle_data_url: bool = True,
                        log_fun: Optional[callable] = None) -> Optional[bytes]:
        """将 Base64 字符串转换回原始的 bytes 数据"""
        if not base64_string:
            error_msg = "Base64 字符串不能为空"
            if log_fun:
                log_fun(error_msg)
            else:
                print(error_msg)
            return None

        try:
            # 处理可能的数据URL前缀
            if handle_data_url and ',' in base64_string:
                # 分离MIME类型和实际的Base64数据
                header, actual_base64 = base64_string.split(',', 1)
                base64_string = actual_base64

            # 移除可能存在的空白字符
            base64_string = base64_string.strip()

            # 进行Base64解码
            decoded_bytes = base64.b64decode(base64_string)

            return decoded_bytes

        except binascii.Error as e:
            error_msg = f"Base64 解码错误: {e}"
            if log_fun:
                log_fun(error_msg)
            else:
                print(error_msg)
            return None
        except Exception as e:
            error_msg = f"解码过程发生意外错误: {e}"
            if log_fun:
                log_fun(error_msg)
            else:
                print(error_msg)
            return None
