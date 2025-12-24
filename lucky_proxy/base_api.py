# coding=utf-8
from nsanic.handler_http import BaseHttpApi
from nsanic.orm.rc_model import RCModel

from common.public.common_class import CommonApi
from lucky_proxy.config import conf_srv, ConfSrv
from lucky_proxy.handler.decorator import ProxyChecker


class BaseApi(BaseHttpApi, CommonApi):
    conf: ConfSrv = conf_srv
    RCModel.set_conf(conf)


class ProxyAuthApi(BaseApi):
    decorators = [ProxyChecker]
    #decorators = []
