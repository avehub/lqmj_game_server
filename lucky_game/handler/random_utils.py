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
    
    # 如果没有提供salt，使用当前时间戳作为salt
    if salt is None:
        salt = str(int(time.time() * 1000))
    
    # 生成基本随机数
    base_random = random.randint(10**(num_digits-1), 10**num_digits - 1)
    
    # 使用salt增加随机性
    salted_str = f"{base_random}{salt}"
    salted_hash = hashlib.sha256(salted_str.encode()).hexdigest()
    
    # 将hash转换为整数并取模
    final_random = int(salted_hash, 16) % (10**num_digits)
    
    # 确保生成的数字有指定的位数
    if len(str(final_random)) < num_digits:
        final_random = int(f"{10**(num_digits-1)}{final_random}") % (10**num_digits)
    
    return final_random
