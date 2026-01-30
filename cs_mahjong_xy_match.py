"""
麻将闷胡比赛玩法服务
"""

# ========== 安全内存监控（带异常保护）==========
import tracemalloc
import signal
import os
import sys
import datetime

def _safe_print(msg):
    """安全地向 stderr 输出，避免因 stdout 问题导致崩溃"""
    try:
        sys.stderr.write(msg + "\n")
        sys.stderr.flush()
    except:
        pass  # 静默失败，绝不让日志写入杀死进程

def _print_memory_top(signum=None, frame=None):
    try:
        if not tracemalloc.is_tracing():
            _safe_print("[MEMORY] tracemalloc not active")
            return

        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')

        lines = [
            "=" * 60,
            f"[MEMORY SNAPSHOT] PID={os.getpid()} | Time={datetime.datetime.now()}",
            "=" * 60
        ]
        for i, stat in enumerate(top_stats[:10], 1):
            lines.append(f"{i:2}. {stat}")
        lines.append("=" * 60)

        _safe_print("\n".join(lines))

    except Exception as e:
        # 捕获所有异常，确保信号处理不会杀死进程
        _safe_print(f"[ERROR] Memory dump failed: {type(e).__name__}: {e}")

# 启动 tracemalloc 并注册信号
try:
    tracemalloc.start()
    _safe_print(f"[MEMORY] tracemalloc started. Use 'kill -USR1 {os.getpid()}' to dump memory.")
except Exception as e:
    _safe_print(f"[WARNING] Failed to start tracemalloc: {e}")

signal.signal(signal.SIGUSR1, _print_memory_top)
# ============================================

from common.utils.init import start
from common.public.enum_const import ServiceEnum


if __name__ == '__main__':
    from c_services.cs_mahjong.service_xingyi_match import MahjongServerXyMatch
    start(MahjongServerXyMatch, ServiceEnum.C_MAHJONG_XY_MATCH, __file__[0:-3])
