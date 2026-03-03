"""
麻将贵阳玩法服务
"""

from common.utils.init import start
from common.public.enum_const import ServiceEnum

if __name__ == '__main__':
    from c_services.cs_mahjong.service_guiyang import MahjongServerGy
    start(MahjongServerGy, ServiceEnum.C_MAHJONG_GY, __file__[0:-3])