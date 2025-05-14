"""
启动聊天服务
"""

from common.utils.init import start
from common.public.enum_const import ServiceEnum

if __name__ == '__main__':
    from c_services.cs_chat.service import ChatServer
    start(ChatServer, ServiceEnum.C_CHAT, __file__[0:-3])