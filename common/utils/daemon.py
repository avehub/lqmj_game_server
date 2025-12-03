# coding:utf-8

import os
import sys

import atexit
import signal


def daemonize(pidfile, *, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null', on_exit=None):
    if os.path.exists(pidfile):
        raise RuntimeError('Already running')

    # First fork (detaches from parent)
    # 从父进程fork一个子进程出来
    try:
        if os.fork() > 0:
            raise SystemExit(0)  # Parent exit
    except OSError as e:
        print(e)
        raise RuntimeError('fork #1 failed.')

    # 子进程默认继承父进程的工作目录，最好是变更到根目录，否则回影响文件系统的卸载
    # os.chdir('/')
    # 子进程默认继承父进程的umask（文件权限掩码），重设为0（完全控制），以免影响程序读写文件
    os.umask(0)
    # 让子进程成为新的会话组长和进程组长
    os.setsid()

    # Second fork (relinquish session leadership)
    # 此时，孙子进程已经是守护进程了，接下来重定向标准输入、输出、错误的描述符(是重定向而不是关闭, 这样可以避免程序在 print 的时候出错)
    try:
        if os.fork() > 0:
            raise SystemExit(0)
    except OSError as e:
        raise RuntimeError('fork #2 failed.')

    # 刷新缓冲区先，小心使得万年船
    # Flush I/O buffers
    sys.stdout.flush()
    sys.stderr.flush()

    # Replace file descriptors for stdin, stdout, and stderr
    # dup2函数原子化地关闭和复制文件描述符，重定向到/dev/nul，即丢弃所有输入输出
    with open(stdin, 'rb', 0) as f:
        os.dup2(f.fileno(), sys.stdin.fileno())
    with open(stdout, 'ab', 0) as f:
        os.dup2(f.fileno(), sys.stdout.fileno())
    with open(stderr, 'ab', 0) as f:
        os.dup2(f.fileno(), sys.stderr.fileno())

    # Write the PID file
    with open(pidfile, 'w') as f:
        print(os.getpid(), file=f)

    # Arrange to have the PID file removed on exit/signal
    # 注册退出函数，进程异常退出时移除pid文件
    atexit.register(lambda: os.remove(pidfile))

    # Signal handler for termination (required)
    # 用于终止的信号处理程序(必需)
    def sigterm_handler(*agrs):
        raise SystemExit(1)

    signal.signal(signal.SIGTERM, on_exit if on_exit else sigterm_handler)