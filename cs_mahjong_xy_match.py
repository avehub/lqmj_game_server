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

    snapshot = snapshot.filter_traces((
        tracemalloc.Filter(False, "<frozen"),
        tracemalloc.Filter(False, "lib/python"),
        tracemalloc.Filter(False, "site-packages"),
    ))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"memory_snapshot_{timestamp}.txt"

    with open(filename, "w") as f:
        f.write(f"Memory Snapshot at {datetime.now()}\n")
        f.write("=" * 60 + "\n")

        stats = snapshot.statistics('lineno')

        # 收集所有属于你项目的分配
        my_stats = []
        for stat in stats:
            # 更精准：检查 traceback 中是否有你的路径
            for frame in stat.traceback:
                if "/www/lucky_game/" in frame.filename:
                    my_stats.append(stat)
                    break  # 找到一个就跳出

        if my_stats:
            # 按内存大小降序排序，取 top 20
            my_stats.sort(key=lambda x: x.size, reverse=True)
            for stat in my_stats[:20]:
                f.write(f"{stat}\n")
            f.write(f"\n[INFO] Found {len(my_stats)} allocation sites in your code. Showing top 20 by size.\n")
        else:
            f.write(">>> NO ALLOCATIONS FOUND IN /www/lucky_game/ <<<\n")
            f.write("Top 10 overall (may include third-party):\n")
            for stat in stats[:10]:
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
