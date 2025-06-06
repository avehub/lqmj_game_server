"""
Redis客户端封装
"""

from typing import Union, Set
from redis.asyncio import Redis, ConnectionPool
from redis.commands.core import SetCommands
from redis.asyncio.client import Pipeline
from nsanic.libs.rds_client import RdsClient
from common.public.conf import CONF_RDS


class RedisClient:
    """Redis客户端封装类"""

    def __init__(self):
        """初始化Redis客户端"""
        self.client = RdsClient.init(CONF_RDS['default'])
        self.set_commands = SetCommands(self.client)

    async def sadd(self, key: str, *values: Union[str, int]) -> int:
        """
        添加一个或多个成员到集合中，已经存在的成员将被忽略

        Args:
            key: 集合的键名
            *values: 要添加的成员

        Returns:
            被添加到集合的新成员的数量
        """
        return await self.set_commands.sadd(key, *values)

    async def srem(self, key: str, *values: Union[str, int]) -> int:
        """
        移除集合中的一个或多个成员

        Args:
            key: 集合的键名
            *values: 要移除的成员

        Returns:
            被成功移除的成员的数量
        """
        return await self.set_commands.srem(key, *values)

    async def smembers(self, key: str) -> Set[Union[str, int]]:
        """
        返回集合中的所有成员

        Args:
            key: 集合的键名

        Returns:
            集合中的所有成员
        """
        return await self.set_commands.smembers(key)

    async def sismember(self, key: str, value: Union[str, int]) -> bool:
        """
        判断成员是否是集合的成员

        Args:
            key: 集合的键名
            value: 要检查的成员

        Returns:
            如果是集合的成员，返回 True，否则返回 False
        """
        return await self.set_commands.sismember(key, value)

    async def scard(self, key: str) -> int:
        """
        获取集合的成员数量

        Args:
            key: 集合的键名

        Returns:
            集合的成员数量
        """
        return await self.set_commands.scard(key)

    async def spop(self, key: str) -> Union[str, int, None]:
        """
        移除并返回集合中的一个随机成员

        Args:
            key: 集合的键名

        Returns:
            被移除的成员，如果集合为空则返回 None
        """
        return await self.set_commands.spop(key)

    async def srandmember(self, key: str, count: int = 1) -> Union[Set[Union[str, int]], Union[str, int]]:
        """
        返回集合中一个或多个随机成员

        Args:
            key: 集合的键名
            count: 返回的随机成员数量

        Returns:
            如果count为1，返回单个随机成员
            如果count大于1，返回包含多个随机成员的集合
        """
        return await self.set_commands.srandmember(key, count)

    async def pipeline(self) -> Pipeline:
        """获取管道对象"""
        return self.client.pipeline()

    async def close(self):
        """关闭连接"""
        await self.client.close()
