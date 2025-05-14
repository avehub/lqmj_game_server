"""
任务启动服务
"""

from common.utils.init import start
from common.public.enum_const import ServiceEnum

if __name__ == '__main__':
    from c_services.cs_workers.service import WorkersServer
    start(WorkersServer, ServiceEnum.C_WORKERS, __file__[0:-3])