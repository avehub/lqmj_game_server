import asyncio
from typing import Any, Optional


class ResourceLocker:
    """按资源 ID 提供带超时的互斥锁，支持自动清理未使用的锁。"""

    def __init__(self) -> None:
        self.__locks = {}  # resource_id -> asyncio.Lock
        self.__ref_counts = {}  # resource_id -> int

    @property
    def locks(self):
        return self.__locks

    @property
    def ref_counts(self):
        return self.__ref_counts

    def __call__(
            self,
            resource_id: Any,
            *,
            timeout: Optional[float] = None
    ) -> "ResourceLockContext":
        """
        返回一个异步上下文管理器，用于锁定指定资源 ID。

        :param resource_id: 可哈希的资源标识符。
        :param timeout: 获取锁的超时时间（秒），None 表示永不超时。
        """
        return ResourceLockContext(self, resource_id, timeout)

    async def locked(self, resource_id, func, func_params=(), timeout=None):
        async with ResourceLockContext(self, resource_id, timeout):
            return await func(*func_params)


class ResourceLockContext:
    """内部类：实现带超时的异步上下文管理器。"""

    def __init__(
            self,
            locker: ResourceLocker,
            resource_id: Any,
            timeout: Optional[float]
    ) -> None:
        self._locker = locker
        self._resource_id = resource_id
        self._timeout = timeout
        self._lock = None
        self._acquired = False  # 标记是否成功获取了锁

    async def __aenter__(self) -> "ResourceLockContext":
        # 增加引用计数（表示有协程开始尝试使用该资源）
        self._locker.ref_counts[self._resource_id] = self._locker.ref_counts.get(self._resource_id, 0) + 1

        # 获取或创建锁
        if self._resource_id not in self._locker.locks:
            self._locker.locks[self._resource_id] = asyncio.Lock()
        self._lock = self._locker.locks[self._resource_id]

        # 尝试获取锁（支持超时）
        try:
            if self._timeout is None:
                await self._lock.acquire()
            else:
                await asyncio.wait_for(self._lock.acquire(), timeout=self._timeout)
            self._acquired = True
        except (asyncio.TimeoutError, Exception):
            # 获取锁失败：需清理引用计数，并可能删除锁
            self._acquired = False  # ← 明确当前对象状态
            self._decrement_ref_and_cleanup()
            raise

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._acquired:
            # 正常释放锁
            self._lock.release()
            self._acquired = False

            # 减少引用计数并尝试清理
            self._decrement_ref_and_cleanup()
        else:
            # 锁未被获取（例如超时），已在 __aenter__ 中清理，此处无需操作
            pass

    def _decrement_ref_and_cleanup(self) -> None:
        """当获取锁失败时，回滚引用计数并尝试清理资源。"""
        self._locker.ref_counts[self._resource_id] -= 1
        if self._locker.ref_counts[self._resource_id] == 0:
            # 没有人再等待这个资源，可以安全删除
            del self._locker.ref_counts[self._resource_id]
            del self._locker.locks[self._resource_id]
