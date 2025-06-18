import random
import hashlib
import time

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
