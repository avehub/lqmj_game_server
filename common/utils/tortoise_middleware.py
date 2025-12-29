import logging

from tortoise import Tortoise
from tortoise.signals import post_save, post_delete
from ..public.logging_config import tortoise_logger
from common.public.conf import ENV


async def log_model_creation(sender, instance, created, using_db, update_fields):
    """记录模型创建日志"""
    if created:
        tortoise_logger.info(
            f"Tortoise CREATE - Model: {sender.__name__}, ID: {instance.pk}, "
            f"Fields: {update_fields if update_fields else 'all'}"
        )
    else:
        # 记录更新操作
        tortoise_logger.info(
            f"Tortoise UPDATE - Model: {sender.__name__}, ID: {instance.pk}, "
            f"Updated Fields: {update_fields}"
        )


async def log_model_delete(sender, instance, using_db):
    """记录模型删除日志"""
    tortoise_logger.info(
        f"Tortoise DELETE - Model: {sender.__name__}, ID: {instance.pk}"
    )


async def setup_tortoise_logging():
    """设置Tortoise ORM日志"""
    # 注册信号处理器
    await post_save.connect(log_model_creation)
    await post_delete.connect(log_model_delete)

    # 配置SQL查询日志
    Tortoise._log = tortoise_logger
    if ENV in ['test', 'dev']:
        Tortoise._log.addHandler(logging.StreamHandler())
    return tortoise_logger
