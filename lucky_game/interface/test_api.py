# coding=utf-8
from sanic import Request, json

from c_services.const.cs_enum_const import CmdRoom
from common.public.conf import C_SERVICE_SECRET_KEY
from lucky_game.base_api import GameAuthApi
from common.public.enum_const import StaCode, ServiceEnum
from lucky_game.handler.huifu import DouGongPay
from lucky_game.model_rc.base_records_game import RecordsGameTotalRC
from lucky_game.model_rc.distribution_settle_conf import DistributionSettleConfRC
from lucky_game.model_rc.game_rooms import GameRoomsRC
from lucky_game.model_rc.records_game_segment import RecordsGameSegmentRC
from common.aliyun.dingtalk_service import dingtalk_exception_handler


class TestApi(GameAuthApi):
    decorators = []

    async def get(self, req: Request):
        return self.answer(StaCode.DEFAULT)


class TestCreatData(GameAuthApi):
    """测试模拟数据"""
    decorators = []
    async def post(self, req: Request):

        data = await DistributionSettleConfRC.get_profit_ratio(50)
        return self.answer(data=data)


class TestLeaveRoom(GameAuthApi):
    decorators = []

    async def get(self, req: Request, cs_type=22):
        cs_enum = ServiceEnum.find_member_by_val(cs_type)
        room_data = {"room_id": 272294, "club_id": 100333, "secret": C_SERVICE_SECRET_KEY}
        await self.cs2cs_by_rmq(
            cs_enum,
            CmdRoom.CLUB_OWNER_DISMISS,
            room_data,
            1,
        )
        return self.answer()

