"""
任务启动服务
"""

from common.utils.init import start
from common.public.enum_const import ServiceEnum

if __name__ == '__main__':
    from c_services.cs_robot_mahjong.service import RobotMahjongServer
    start(RobotMahjongServer, ServiceEnum.ROBOT_MAHJONG_FC, __file__[0:-3])