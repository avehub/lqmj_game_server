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
    snapshot = tracemalloc.take_snapshot()

    # 先过滤掉明显无关的
    snapshot = snapshot.filter_traces((
        tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
        tracemalloc.Filter(False, "<frozen importlib._bootstrap_external>"),
        tracemalloc.Filter(False, "<frozen abc>"),
        tracemalloc.Filter(False, "lib/python"),
        tracemalloc.Filter(False, "site-packages"),
    ))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"memory_snapshot_{timestamp}.txt"

    with open(filename, "w") as f:
        f.write(f"Memory Snapshot at {datetime.now()}\n")
        f.write("=" * 60 + "\n")

        # 获取所有统计
        stats = snapshot.statistics('lineno')
        my_count = 0

        # 优先输出 /www/lucky_game/ 的分配
        for stat in stats:
            trace_str = str(stat.traceback)
            if "/www/lucky_game/" in trace_str:
                f.write(f"{stat}\n")
                my_count += 1

        if my_count == 0:
            f.write(">>> NO ALLOCATIONS FOUND IN /www/lucky_game/ <<<\n")
            f.write("Top 10 overall (may include third-party):\n")
            for stat in stats[:10]:
                f.write(f"{stat}\n")
        else:
            f.write(f"\n[INFO] Found {my_count} allocation sites in your code.\n")

    print(f"[MEMORY] Saved snapshot to {filename}")


# 注册信号：发送 SIGUSR1 时保存快照
import signal

signal.signal(signal.SIGUSR1, lambda sig, frame: dump_memory_snapshot())

from common.utils.init import start
from common.public.enum_const import ServiceEnum


if __name__ == '__main__':
    from c_services.cs_mahjong.service_xingyi_match import MahjongServerXyMatch
    start(MahjongServerXyMatch, ServiceEnum.C_MAHJONG_XY_MATCH, __file__[0:-3])
