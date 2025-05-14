"""
匹配服务启动
"""
from common.utils.init import start
from common.public.enum_const import ServiceEnum

if __name__ == '__main__':
    from c_services.cs_matching.service import MatchServer
    start(MatchServer, ServiceEnum.C_MATCHING, __file__[0:-3])
