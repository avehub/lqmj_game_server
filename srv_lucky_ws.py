# coding=utf-8
from nsanic.base_server import InitServer
from nsanic.exception import CatchExpt
from nsanic.middleware import CorsMiddle
from nsanic.libs.manager import WsRdsConnector
from nsanic.base_ws import WsProtocol
from lucky_ws.config.conf_start import conf_srv as conf
from lucky_ws.url_main import MainBp

signal_map = {}
WsProtocol.connector_map = {
    WsRdsConnector.__name__: WsRdsConnector
}
main_server = InitServer(conf, mws=[CorsMiddle], bps=[MainBp], excps=[CatchExpt])
main_server.add_signal(signal_map)

if __name__ == '__main__':
    main_server.run(protocol=WsProtocol)
