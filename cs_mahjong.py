"""
麻将闷胡血流服务
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

    # 不做激进过滤，保留所有（稍后分类）
    stats = snapshot.statistics('lineno')

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"memory_snapshot_{timestamp}.txt"

    with open(filename, "w") as f:
        f.write(f"Memory Snapshot at {datetime.now()}\n")
        f.write("=" * 60 + "\n\n")

        # ===== 第一部分：代码部分 =====
        my_stats = []
        for stat in stats:
            for frame in stat.traceback:
                if "/www/lucky_game/" in frame.filename:
                    my_stats.append(stat)
                    break

        if my_stats:
            my_stats.sort(key=lambda x: x.size, reverse=True)
            f.write(">>> YOUR CODE (Top 20 by size) <<<\n")
            for stat in my_stats[:20]:
                f.write(f"{stat}\n")
            f.write(f"\n[INFO] Your code: {len(my_stats)} sites, top shown.\n\n")
        else:
            f.write(">>> YOUR CODE: No allocations found <<<\n\n")

        # ===== 第二部分：全局 Top 20（含第三方） =====
        f.write(">>> GLOBAL TOP 20 (including third-party) <<<\n")
        global_top = sorted(stats, key=lambda x: x.size, reverse=True)[:20]
        for stat in global_top:
            f.write(f"{stat}\n")

    print(f"[MEMORY] Saved snapshot to {filename}")


# 注册信号：发送 SIGUSR1 时保存快照
import signal

signal.signal(signal.SIGUSR1, lambda sig, frame: dump_memory_snapshot())

from common.utils.init import start
from common.public.enum_const import ServiceEnum

if __name__ == '__main__':
    from c_services.cs_mahjong.service import MahjongServer
    start(MahjongServer, ServiceEnum.C_MAHJONG_XY, __file__[0:-3])