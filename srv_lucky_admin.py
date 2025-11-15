# coding=utf-8
from nsanic.base_server import InitServer

from nsanic.exception import CatchExpt
from nsanic.middleware import CorsMiddle

from lucky_admin.config import conf_srv as conf
from lucky_admin.handler.middleware import RepMiddle
from lucky_admin.url_main import MainBp

import logging
import asyncio
import os

signal_map = {}

main_server = InitServer(conf, middlewares=[CorsMiddle], bp_arr=[MainBp], exceptions=[CatchExpt])
main_server.add_signal(signal_map)

RepMiddle.set_conf(conf)
main_server.main.middleware(RepMiddle.main, 'response')


if __name__ == '__main__':
    main_server.run()


def setup_debug_logging(logfile: str = "tortoise_debug.log"):
    # 根 logger
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(logfile, encoding="utf-8")
        ],
    )
    # 明确开启这几个 logger 的 DEBUG
    logging.getLogger("tortoise").setLevel(logging.DEBUG)
    logging.getLogger("tortoise.db_client").setLevel(logging.DEBUG)
    logging.getLogger("tortoise.queryset").setLevel(logging.DEBUG)
    logging.getLogger("aiomysql").setLevel(logging.DEBUG)
    logging.getLogger("asyncmy").setLevel(logging.DEBUG)
    logging.getLogger("pymysql").setLevel(logging.DEBUG)  # 若用 pymysql
    # asyncio debug
    os.environ.setdefault("PYTHONASYNCIODEBUG", "1")
    try:
        # 在运行时也可以开启
        asyncio.get_event_loop().set_debug(True)
    except Exception:
        pass

# 在 app 启动时调用
setup_debug_logging()