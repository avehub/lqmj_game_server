"""阿里云验证码服务"""
import time
import logging
from typing import Dict, Optional, Tuple
from lucky_game.handler.random_utils import generate_natural_random
from lucky_game.config import conf_srv, ConfSrv
from common.aliyun.sms_service import sms_service
logger = logging.getLogger('verification')


class AliVerification:
    conf: ConfSrv = conf_srv
    # Redis键前缀
    REDIS_PREFIX = "verification:code:"
    # 默认验证码有效期(秒)
    DEFAULT_EXPIRE_SECONDS = 300
    # 默认验证码长度
    DEFAULT_CODE_LENGTH = 6
    # 默认验证码重发等待时间(秒)
    DEFAULT_RESEND_WAIT = 60

    @classmethod
    async def generate_code(cls, length: int = DEFAULT_CODE_LENGTH) -> int:
        """生成随机验证码"""
        return generate_natural_random(length)

    @classmethod
    async def send_code(cls,
                        phone_number: str,
                        scene: str = 'login',
                        expire_seconds: int = DEFAULT_EXPIRE_SECONDS,
                        resend_wait: int = DEFAULT_RESEND_WAIT
                        ) -> Tuple[bool, str]:
        """
        发送验证码

        Args:
            phone_number: 手机号
            scene: 场景标识(login:登录, register:注册, reset:重置密码等)
            expire_seconds: 验证码有效期(秒)
            resend_wait: 重发等待时间(秒)

        Returns:
            Dict: 发送结果
        """
        # 构建Redis键
        redis_key = f"{cls.REDIS_PREFIX}{scene}:{phone_number}"

        # 检查是否可以发送验证码(防止频繁发送)
        last_send_time = await cls.conf.rds.get_hash(redis_key, "send_time")
        if last_send_time:
            elapsed = int(time.time()) - int(last_send_time)
            if elapsed < resend_wait:
                wait_time = resend_wait - elapsed
                return False, f'请等待{wait_time}秒后再重新获取验证码'

        # 生成验证码
        code = await cls.generate_code()
        expire_minutes = expire_seconds

        # 发送短信
        sms_result = await sms_service.send_verification_code(
            phone_number=phone_number,
            code=code,
            expire_minutes=expire_minutes
        )

        if sms_result['success']:
            # 保存验证码信息到Redis
            current_time = int(time.time())
            await cls.conf.rds.set_hash_bulk(redis_key, {
                "code": code,
                "send_time": current_time,
                "expire_time": current_time + expire_seconds,
                "verified": 0,  # 0:未验证 1:已验证
                "attempts": 0  # 验证尝试次数
            })
            await cls.conf.rds.expired(redis_key, expire_seconds)

            return True, '验证码发送成功'
        else:
            return False, '验证码发送失败'

    @classmethod
    async def verify_code(cls, phone_number: str, code: str, scene: str = 'login',
                          max_attempts: int = 5) -> Tuple[bool, str]:
        """
        验证验证码

        Args:
            phone_number: 手机号
            code: 用户输入的验证码
            scene: 场景标识
            max_attempts: 最大尝试次数

        Returns:
            Tuple[bool, str]: (是否验证成功, 消息)
        """
        redis_key = f"{cls.REDIS_PREFIX}{scene}:{phone_number}"

        # 获取验证码信息
        code_info = await cls.conf.rds.get_hash_all(redis_key)
        if not code_info:
            return False, "验证码不存在或已过期"

        # 检查是否已验证
        if int(code_info.get('verified', 0)) == 1:
            return False, "验证码已使用"

        # 检查是否过期
        current_time = int(time.time())
        expire_time = int(code_info.get('expire_time', 0))
        if current_time > expire_time:
            await cls.conf.rds.drop_hash_bulk(redis_key, ['code', 'send_time', 'expire_time', 'verified', 'attempts'])
            return False, "验证码已过期"

        # 检查尝试次数
        attempts = int(code_info.get('attempts', 0))
        if attempts >= max_attempts:
            await cls.conf.rds.drop_hash_bulk(redis_key, ['code', 'send_time', 'expire_time', 'verified', 'attempts'])
            return False, f"验证码尝试次数过多，请重新获取"

        # 验证码比对
        stored_code = code_info.get('code', '')
        if code == stored_code:
            # 标记为已验证
            await cls.conf.rds.set_hash(redis_key, "verified", 1)
            return True, "验证成功"
        else:
            # 增加尝试次数
            await cls.conf.rds.set_hash(redis_key, "attempts", attempts + 1)
            remaining = max_attempts - attempts - 1
            return False, f"验证码错误，还有{remaining}次尝试机会"


# 创建单例实例
verification_service = AliVerification()
