"""
跑得快服务
"""

from common.utils.init import start
from common.public.enum_const import ServiceEnum

if __name__ == '__main__':
    from c_services.cs_run_fast.service import RunFastServer
    start(RunFastServer, ServiceEnum.C_RUN_FAST, __file__[0:-3])