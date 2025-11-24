"""
水鱼休闲场
"""

from common.utils.init import start
from common.public.enum_const import ServiceEnum

if __name__ == '__main__':
    from c_services.cs_water_fish.service import WaterFishServer
    start(WaterFishServer, ServiceEnum.C_WATER_FISH, __file__[0:-3])