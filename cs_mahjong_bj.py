"""
麻将毕节玩法服务
"""

from common.utils.init import start
from common.public.enum_const import ServiceEnum

if __name__ == '__main__':
    from c_services.cs_mahjong.service_bijie import MahjongServerBj
    start(MahjongServerBj, ServiceEnum.C_MAHJONG_BJ, __file__[0:-3])