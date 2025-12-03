"""
斗地主休闲场
"""

from common.utils.init import start
from common.public.enum_const import ServiceEnum

if __name__ == '__main__':
    from c_services.cs_landlords.service import LandlordsServer
    start(LandlordsServer, ServiceEnum.C_LANDLORDS, __file__[0:-3])