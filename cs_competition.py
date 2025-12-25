"""
麻将比赛匹配玩法服务
"""
from common.utils.init import start
from common.public.enum_const import ServiceEnum

if __name__ == '__main__':
    from c_services.cs_competition.service import CompetitionServer
    start(CompetitionServer, ServiceEnum.C_COMPETITION, __file__[0:-3])