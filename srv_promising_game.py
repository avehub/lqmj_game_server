# coding=utf-8
from nsanic.base_server import InitServer
from promising_game.handler.exception import RCatchExpt
from nsanic.middleware import CorsMiddle
from promising_game.config import conf_srv as conf
from promising_game.url_main import MainBp


signal_map = {}

main_server = InitServer(conf, mws=[CorsMiddle], bps=[MainBp], excps=[RCatchExpt])
main_server.add_signal(signal_map)


if __name__ == '__main__':
    main_server.run()
