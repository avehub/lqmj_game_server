from nsanic.libs import tool_jwt, tool_dt
from sanic import Request
from common.public.enum_const import JWType
from lucky_admin.base_api import AdminAuthApi
from lucky_admin.const import AdminPermission
from lucky_admin.model_rc.base_admin import BaseAdminRC
from common.utils.utils import UtilsTool
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.model_rc.extra_user_resource_changes import ExtraUserResourceChangesRC


class IndexBaseData(AdminAuthApi):
    """ 顶部基础数据 """
    async def get(self, req: Request):
        start_time, end_time = self.get_time_range(period="day")
        yesterday_start_time = start_time - 86400
        yesterday_end_time = end_time - 86400
        _, yesterday_total_user = await BaseUserRC.count_user_total(start_time=yesterday_start_time, end_time=yesterday_end_time)
        _, total_user = await BaseUserRC.count_user_total()
        
        data = {
            "today_consumer_gold": 0,
            "yesterday_consumer_gold": 0,
            "today_consumer_discount": 0,
            "yesterday_consumer_discount": 0,
            "today_online_user": 0,
            "yesterday_online_user": 0,
            "today_total_user": total_user,
            "yesterday_total_user": yesterday_total_user,
        }
        return self.answer(data=data)


class IndexUserData(AdminAuthApi):
    """ 用户基础数据 """
    async def get(self, req: Request):
        title = self.check_str(req.json.get('title'), require=True, maxlen=64, p_name='标题')
        content = self.check_str(req.json.get('content'), require=True, maxlen=255, p_name='内容')
        attachment = self.check_str(req.json.get('attachment'), require=True, p_name='附件')
        sender = self.check_str(req.json.get('sender'), require=True, p_name='发送者')
        receiver = self.check_int(req.json.get('receiver'), require=True, p_name='接收者')
        mail_type = self.check_int(req.json.get('mail_type'), require=True, p_name='邮件类型')
        exp_time = self.check_int(req.json.get('exp_time'), require=False, p_name='过期时间')
        data = {
            "today_add_user": 0,
            "yesterday_add_user": 0,
            "week_add_user": 0,
            "today_login_user": 0,
            "yesterday_login_user": 0,
            "week_login_user": 0,
            "today_activate_user": 0,
            "yesterday_activate_user": 0,
            "week_activate_user": 0,
            "today_pay_money": 0,
            "yesterday_pay_money": 0,
            "week_pay_money": 0,
        }
        return self.answer(data=data)

class IndexBaseTable(AdminAuthApi):
    """ 基础数据报表 """

    async def get(self, req: Request):
        data = {
            "date": 0,
            "add_user": 0,
            "activate_user": 0,
            "pay_money": 0,
            "pay_user": 0,
            "pay_rate": 0,
            "arpu": 0,
            "arppu": 0,
        }
        return self.answer(data=data)