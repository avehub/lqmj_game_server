"""
麻将发财捉鸡休闲场服务
"""

from common.utils.init import start
from common.public.enum_const import ServiceEnum

if __name__ == '__main__':
    from c_services.cs_mahjong.service_fczj import MahjongServerFc
    start(MahjongServerFc, ServiceEnum.C_MAHJONG_FC, __file__[0:-3])
