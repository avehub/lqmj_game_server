# coding=utf-8
import asyncio

from lucky_proxy.config.conf_start import ConfSrv
from lucky_proxy.script.timed_task import BaseTimed

conf_srv = ConfSrv()
migrate_db = conf_srv.migrate_db()
