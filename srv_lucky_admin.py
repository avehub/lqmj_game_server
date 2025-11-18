# coding=utf-8
from nsanic.base_server import InitServer

from nsanic.exception import CatchExpt
from nsanic.middleware import CorsMiddle

from lucky_admin.config import conf_srv as conf
from lucky_admin.handler.middleware import RepMiddle
from lucky_admin.url_main import MainBp


signal_map = {}

main_server = InitServer(conf, middlewares=[CorsMiddle], bp_arr=[MainBp], exceptions=[CatchExpt])
main_server.add_signal(signal_map)

RepMiddle.set_conf(conf)
main_server.main.middleware(RepMiddle.main, 'response')


if __name__ == '__main__':
    main_server.run()
