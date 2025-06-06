"""
斗地主休闲场
"""

from common.utils.init import start
from common.public.enum_const import ServiceEnum

if __name__ == '__main__':
    from c_services.cs_mahjong.service import MahjongServer
    start(MahjongServer, ServiceEnum.C_MAHJONG_XY, __file__[0:-3])