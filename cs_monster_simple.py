"""
简单版打妖怪启动服务
"""

from common.utils.init import start
from common.public.enum_const import ServiceEnum

if __name__ == '__main__':
    from c_services.cs_monster.service import MonsterServer
    start(MonsterServer, ServiceEnum.C_MONSTER, __file__[0:-3])
