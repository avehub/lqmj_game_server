# coding=utf-8
from lucky_game.config.conf_start import ConfSrv

conf_srv = ConfSrv()
migrate_db = conf_srv.migrate_db()
