# coding=utf-8
from promising_admin.config.conf_start import ConfSrv

conf_srv = ConfSrv()
migrate_db = conf_srv.migrate_db()
