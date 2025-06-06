# coding=utf-8
from nsanic.base_server import InitServer
from lucky_game.handler.exception import RCatchExpt
from nsanic.middleware import CorsMiddle
from lucky_game.config import conf_srv as conf
from lucky_game.url_main import MainBp


signal_map = {}

main_server = InitServer(conf, middlewares=[CorsMiddle], bp_arr=[MainBp], exceptions=[RCatchExpt])
main_server.add_signal(signal_map)


if __name__ == '__main__':
    main_server.run()
