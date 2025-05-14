"""
打妖怪下篇启动服务
"""

from common.utils.init import start
from common.public.enum_const import ServiceEnum

if __name__ == '__main__':
    from c_services.cs_monster_sequel.service import MonsterSeqServer
    start(MonsterSeqServer, ServiceEnum.C_MONSTER_SEQUEL, __file__[0:-3])
