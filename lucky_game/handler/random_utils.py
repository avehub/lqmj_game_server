import random
import hashlib
import time
import string
from typing import Optional

def generate_natural_random(num_digits: int, salt: str = None) -> int:
    """
    生成指定位数的自然随机数
    
    Args:
        num_digits (int): 随机数的位数
        salt (str, optional): 用于增加随机性的盐值，默认为None
            如果未提供，将使用当前时间戳作为盐值
    
    Returns:
        int: 生成的随机数
    
    Raises:
        ValueError: 如果num_digits小于1或大于100
    """
    if num_digits < 1 or num_digits > 100:
        raise ValueError("num_digits必须在1到100之间")

    if salt is None:
        salt = str(int(time.time() * 1000))

    while True:
        base_random = random.randint(10 ** (num_digits - 1), 10 ** num_digits - 1)
        salted_str = f"{base_random}{salt}"
        salted_hash = hashlib.sha256(salted_str.encode()).hexdigest()

        # 将hash转换为整数，取前num_digits位
        hash_int_str = str(int(salted_hash, 16))
        if len(hash_int_str) < num_digits:
            continue  # 重新生成
        final_digits = hash_int_str[:num_digits]

        if len(final_digits) == num_digits:
            return int(final_digits)



def generate_random_string(length: int,
                           use_uppercase: bool = True,
                           use_lowercase: bool = True,
                           use_digits: bool = True,
                           custom_chars: Optional[str] = None) -> str:
    """
    生成指定长度的随机字符串

    Args:
        length: 生成字符串的长度
        use_uppercase: 是否包含大写字母
        use_lowercase: 是否包含小写字母
        use_digits: 是否包含数字
        custom_chars: 自定义字符集

    Returns:
        生成的随机字符串
    """
    if length <= 0:
        raise ValueError("字符串长度必须大于0")

    # 构建字符池
    chars = ""
    if custom_chars:
        chars = custom_chars
    else:
        if use_uppercase:
            chars += string.ascii_uppercase
        if use_lowercase:
            chars += string.ascii_lowercase
        if use_digits:
            chars += string.digits

    if not chars:
        raise ValueError("字符池为空，请至少选择一种字符类型或提供自定义字符集")

    return ''.join(random.choice(chars) for _ in range(length))
