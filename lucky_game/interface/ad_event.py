"""
广告事件类接口
"""
import traceback
from sanic import Request
from common.public.enum_const import StaCode
from lucky_game.base_api import GameAuthApi
from lucky_game.model_rc.records_ad_event import RecordsAdEventRC


class CreateAdRecord(GameAuthApi):
    """
    添加广告记录
    """
    async def post(self, req: Request, **kwargs):
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        campaign_type = self.check_int(req.json.get("campaign_type"), require=True, p_name="广告类型")
        type_id = self.check_int(req.json.get("type_id"), require=True, p_name="广告类型ID")
        platform = self.check_int(req.args.get("platform"), require=True, p_name="平台")
        os = self.check_str(req.args.get("c_os"), require=True, p_name="操作系统")
        status = self.check_int(req.json.get("status"), require=False, p_name="状态")
        ip = self.ori_ip(req)
        record, msg = await RecordsAdEventRC.create_record_ad(uid, campaign_type, type_id, platform, os, ip, status)
        if not record:
            return self.answer(StaCode.FAIL, hint=msg)
        return self.answer()
