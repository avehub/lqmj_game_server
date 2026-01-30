"""
麻将闷胡比赛玩法服务
"""

# ====== 新增：内存监控支持 ======
import tracemalloc
import signal
import logging
import os

def _print_memory_top(signum=None, frame=None):
    """打印当前内存分配 Top 10"""
    if not tracemalloc.is_tracing():
        print("[Memory] tracemalloc not active")
        return

    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')

    print(f"\n{'='*60}")
    print(f"[MEMORY SNAPSHOT] PID={os.getpid()} | Time={__import__('datetime').datetime.now()}")
    print(f"{'='*60}")
    for i, stat in enumerate(top_stats[:10], 1):
        print(f"{i:2}. {stat}")
    print("="*60 + "\n")

# 启动内存追踪（开销很小，可长期开启）
tracemalloc.start()
print(f"[MEMORY] tracemalloc started. Use 'kill -USR1 {os.getpid()}' to dump top allocators.")

# 注册信号：发送 SIGUSR1 时打印内存快照
signal.signal(signal.SIGUSR1, _print_memory_top)
# ==============================

from common.utils.init import start
from common.public.enum_const import ServiceEnum


if __name__ == '__main__':
    from c_services.cs_mahjong.service_xingyi_match import MahjongServerXyMatch
    start(MahjongServerXyMatch, ServiceEnum.C_MAHJONG_XY_MATCH, __file__[0:-3])
