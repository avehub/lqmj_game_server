from common.public.enum_const import ServiceEnum
from common.utils.utils import UtilsTool


def pack_data(channel, cs_type: ServiceEnum, cmd, msg):
    data = UtilsTool.pack_inner_msg(cmd, 1, msg)
    exchange_name = f"{channel}_{cs_type.val}"
    routing_key = f"{cs_type.phrase}_{cs_type.val}"
    return data, exchange_name, routing_key
