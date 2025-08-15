""" 订单相关逻辑处理 """
import decimal
import random
import time

from nsanic.libs.mk_random import RngMaker
from sanic import Request
from nsanic.libs import tool_dt
from nsanic.libs.tool import json_parse
from tortoise.transactions import in_transaction
from common.proto.py_pb2.common import switch_enum, get_one_of_model, switch_type_enum
from common.public.enum_const import DbKey, ServiceEnum
from common.public.common_class import CommonApi
from lucky_game.base_api import GameAuthApi
from lucky_game.handler.up_assets import UpAssets
from lucky_game.model_rc.base_bag import UserBagRC
from lucky_game.model_rc.order import OrderRC
from lucky_game.model_rc.base_store import StoreRC, GoodRC
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.const import PayType, GoodsItem, ReasonCostDiamond, ReasonCostGold, GoodsType, StoreType, \
    BossType, HeldSta, PlatForm, CurrencyType, PayMode, OrderStatus, GainStatus, RandType, OperatingSystem
from nsanic.libs.mult_log import NLogger
from common.public.conf import WeChatConf, HuiFuConf, PROD_SERVER_ADDR, LIVE_SERVER, TEST_SERVER_ADDR
from lucky_game.handler.douyin import DouYin
from lucky_game.handler.huifu import DouGongPay
from dg_sdk import DGTools
from lucky_game.handler.wechat import WeChat
from lucky_game.model_rc.base_activity import ConfActivityRC, UserActivityRC
from lucky_game.model_rc.extra_user_resource_changes import ExtraUserResourceChangesRC
from lucky_game.handler.ios_pay import ios_payment_service
from common.aliyun.pay_service import AlipayPayment


class OrderLogic:
    def __init__(self):
        pass

    async def gain_order(self, order: dict, u_info: dict):
        """ 领取订单 """
