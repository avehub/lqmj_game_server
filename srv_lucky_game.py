# coding=utf-8
from nsanic.base_server import InitServer
from lucky_game.handler.exception import RCatchExpt
from nsanic.middleware import CorsMiddle
from lucky_game.config import conf_srv as conf
from lucky_game.handler.middleware import logging_middleware
from lucky_game.url_main import MainBp
from sanic import Sanic
from common.utils.exceptions import global_exception_handler
import sys
import logging
import asyncio
import os

signal_map = {}

print("正在初始化服务器...")
main_server = InitServer(conf, middlewares=[CorsMiddle, logging_middleware], bp_arr=[MainBp], exceptions=[RCatchExpt])
main_server.add_signal(signal_map)
# 获取Sanic应用实例并注册静态路由
if conf.FILE_UPLOAD.LOCAL_STORAGE['enable']:
    app = Sanic.get_app()
    app.static(f'/{conf.RESOURCE_PATH}', conf.STATIC_ROOT)

if __name__ == '__main__' or 'pydevd' in sys.modules:
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

