"""
麻将遵义玩法服务
"""

from common.utils.init import start
from common.public.enum_const import ServiceEnum

if __name__ == '__main__':
    from c_services.cs_mahjong.service_zunyi import MahjongServerZy
    start(MahjongServerZy, ServiceEnum.C_MAHJONG_ZY, __file__[0:-3])
