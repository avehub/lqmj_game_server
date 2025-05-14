"""
简单版打妖怪启动服务3局模式
"""

from common.utils.init import start
from common.public.enum_const import ServiceEnum

if __name__ == '__main__':
    from c_services.cs_monster.service_blood_flow import MonsterBfServer
    start(MonsterBfServer, ServiceEnum.C_MONSTER_MANY, __file__[0:-3])
