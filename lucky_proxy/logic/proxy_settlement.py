from nsanic.libs.component import LogMeta

from lucky_proxy.config import ConfSrv, conf_srv
from lucky_proxy.model_db.main import ProxyPromotionRelation

"""
创建推广码
"""


class ProxySettlement(LogMeta):
    conf: ConfSrv = conf_srv
