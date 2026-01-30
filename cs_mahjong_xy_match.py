"""
麻将闷胡比赛玩法服务
"""

import tracemalloc
import linecache
import os
import asyncio
from datetime import datetime

# ========== 启动内存追踪 ==========
tracemalloc.start(25)  # 保留最近 25 层堆栈


def dump_memory_snapshot():
    """保存当前内存快照，并过滤标准库"""
    snapshot = tracemalloc.take_snapshot()

    # 过滤掉 Python 标准库和 CPython 内部
    snapshot = snapshot.filter_traces((
        tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
        tracemalloc.Filter(False, "<frozen importlib._bootstrap_external>"),
        tracemalloc.Filter(False, "<frozen importlib._abc>"),
        tracemalloc.Filter(False, "lib/python*"),
        tracemalloc.Filter(False, "site-packages/"),
        tracemalloc.Filter(True, "/www/lucky_game/"),  # 只看你的业务代码
    ))

    # 保存到文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"memory_snapshot_{timestamp}.txt"
    with open(filename, "w") as f:
        f.write(f"Memory Snapshot at {datetime.now()}\n")
        f.write("=" * 60 + "\n")
        for stat in snapshot.statistics('lineno')[:10]:
            f.write(f"{stat}\n")

    print(f"[MEMORY] Saved snapshot to {filename}")


# 注册信号：发送 SIGUSR1 时保存快照
import signal

signal.signal(signal.SIGUSR1, lambda sig, frame: dump_memory_snapshot())

from common.utils.init import start
from common.public.enum_const import ServiceEnum


if __name__ == '__main__':
    from c_services.cs_mahjong.service_xingyi_match import MahjongServerXyMatch
    start(MahjongServerXyMatch, ServiceEnum.C_MAHJONG_XY_MATCH, __file__[0:-3])
