import sys, os, asyncio, argparse

from common.public.conf import LIVE_SERVER
from common.utils.daemon import daemonize
from common.public.enum_const import ServiceEnum

OUTPUT_PATH_DAEMON = os.path.join(os.getcwd(), 'logs', 'daemon')


async def _do_start(server_class, server_type, server_name, server_id):
    await server_class.share_server().setup(server_id, server_type, server_name)
    await server_class.share_server().start_server()


def start(server_class, server_type: ServiceEnum, file_name):
    assert server_class
    assert file_name

    args = init_args()

    if os.name == "nt":  # win
        file_name = file_name.replace("\\", "/")
    print("分割：", file_name.split("/"))
    file_name = file_name.split("/")[-1]  # win下不支持转换???

    if not args.stop:
        print(f"Start: python3 {file_name}.py {server_class.__name__}")

    def on_exit(*params):
        asyncio.create_task(server_class.share_server().on_signal_stop())

    server_id = args.sid or 1
    server_name = server_type.phrase
    if args.stop:
        return stop(server_name, server_id, file_name, server_class)
    if args.d:  # daemon启动
        start_daemon(server_name, server_id, on_exit)
    elif args.restart:  # todo: 此处有问题（暂时别用）
        stop(server_name, server_id, file_name, server_class)
        start_daemon(server_name, server_id, on_exit)
    asyncio.run(_do_start(server_class, server_type, server_name, server_id))


def init_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--h', action='store_true')
    parser.add_argument('--d', action='store_true', help="后台启动")
    parser.add_argument('--sid', type=int, default=1, help="服务系列号index")
    parser.add_argument('--stop', action='store_true', help="停止服务")
    parser.add_argument('--restart', action='store_true', help="重启")
    args = parser.parse_args()
    if args.d and args.stop:
        raise RuntimeError("--d and --stop can't at the same time")
    if args.d and args.restart:
        raise RuntimeError("--d and --restart can't at the same time")
    if args.stop and args.restart:
        raise RuntimeError("--stop and --restart can't at the same time")
    return args


def start_daemon(server_name, server_id, on_exit):
    try:
        pid_file = os.path.join(OUTPUT_PATH_DAEMON, f"{server_name}.pid_{server_id}")
        core_dump_file = os.path.join(OUTPUT_PATH_DAEMON, f"{server_name}.log")
        if not os.path.exists(OUTPUT_PATH_DAEMON):
            os.mkdir(OUTPUT_PATH_DAEMON)
        print("dump_file", core_dump_file, pid_file)
        daemonize(pid_file, stderr=core_dump_file, on_exit=on_exit)
    except RuntimeError as e:
        print(e, file=sys.stderr)
        raise SystemExit(1)


def stop(server_name, server_id, file_name, server_class):
    import signal
    pid_file = os.path.join(OUTPUT_PATH_DAEMON, f"{server_name}.pid_{server_id}")
    if os.path.exists(pid_file):
        with open(pid_file) as f:
            process_id = int(f.read())
            if LIVE_SERVER:
                os.kill(process_id, signal.SIGTERM)
            else:
                os.kill(process_id, signal.SIGKILL)
            print(f"Stop: python3 {file_name}.py {server_class.__name__}, {pid_file}, {process_id}")
    else:
        print('Not running', file=sys.stderr)
        raise SystemExit(1)
