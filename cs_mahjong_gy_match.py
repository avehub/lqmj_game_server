"""
麻将贵阳比赛玩法服务
"""
import tracemalloc
from common.utils.init import start
from common.public.enum_const import ServiceEnum

# 启动内存跟踪
tracemalloc.start()

if __name__ == '__main__':
    from c_services.cs_mahjong.service_guiyang_match import MahjongServerGyMatch
    start(MahjongServerGyMatch, ServiceEnum.C_MAHJONG_GY_MATCH, __file__[0:-3])