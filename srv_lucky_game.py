# coding=utf-8
from nsanic.base_server import InitServer
from lucky_game.handler.exception import RCatchExpt
from nsanic.middleware import CorsMiddle
from lucky_game.config import conf_srv as conf
from lucky_game.handler.middleware import logging_middleware
from lucky_game.url_main import MainBp
from sanic import Sanic
import sys


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


