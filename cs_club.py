"""
匹配服务启动
"""
from common.utils.init import start
from common.public.enum_const import ServiceEnum

if __name__ == '__main__':
    from c_services.cs_club.service import ClubServer
    start(ClubServer, ServiceEnum.C_CLUB, __file__[0:-3])