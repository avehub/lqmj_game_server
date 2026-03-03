import logging
import os
from datetime import datetime
from functools import wraps
from pathlib import Path

# 创建日志目录
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
Path(LOG_DIR).mkdir(exist_ok=True)


# Tortoise ORM操作类型枚举
class TortoiseOperation(str):
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    QUERY = "QUERY"
    TRANSACTION = "TRANSACTION"


# Tortoise ORM日志装饰器
def tortoise_logger(func):
    """Tortoise ORM操作日志装饰器"""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        operation = ""  # 根据函数名确定操作类型
        try:
            # 获取操作类型
            if func.__name__.startswith("create"):
                operation = TortoiseOperation.CREATE
            elif func.__name__.startswith("get") or func.__name__.startswith("filter"):
                operation = TortoiseOperation.QUERY
            elif func.__name__.startswith("update"):
                operation = TortoiseOperation.UPDATE
            elif func.__name__.startswith("delete"):
                operation = TortoiseOperation.DELETE
            elif func.__name__.startswith("transaction"):
                operation = TortoiseOperation.TRANSACTION
            else:
                operation = TortoiseOperation.QUERY

            # 记录操作前日志
            tortoise_logger.info(f"Tortoise {operation} - Start: {func.__name__}")

            # 执行操作
            result = await func(*args, **kwargs)

            # 记录操作后日志
            tortoise_logger.info(f"Tortoise {operation} - Complete: {func.__name__}")
            return result
        except Exception as e:
            tortoise_logger.error(f"Tortoise {operation} - Error: {func.__name__}, Error: {str(e)}")
            raise

    return wrapper


# 在setup_logger函数中添加Tortoise ORM日志配置
def setup_logger():
    """配置日志系统"""
    # 创建日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )

    # 创建文件处理器
    log_file = os.path.join(LOG_DIR, f'app_{datetime.now().strftime("%Y%m%d")}.log')
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)

    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # 获取根日志器
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # 配置Tortoise ORM日志
    tortoise_logger = logging.getLogger('tortoise')
    tortoise_logger.setLevel(logging.INFO)
    tortoise_logger.addHandler(file_handler)
    tortoise_logger.addHandler(console_handler)

    # 配置SQL日志
    sql_logger = logging.getLogger('sqlalchemy.engine')
    sql_logger.setLevel(logging.INFO)
    sql_logger.addHandler(file_handler)
    sql_logger.addHandler(console_handler)

    return logger


# 初始化日志系统
logger = setup_logger()

# Tortoise ORM日志器
tortoise_logger = get_logger('tortoise')