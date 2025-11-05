from nsanic.libs import tool_jwt, tool_dt
from sanic import Request
from common.public.enum_const import JWType
from lucky_admin.base_api import AdminAuthApi
from lucky_admin.const import AdminPermission
from lucky_game.model_rc.base_mails import MailsRC
from common.utils.utils import UtilsTool

class Email(AdminAuthApi):
    """ 新增单条邮件 """
    decorators = []

    async def post(self, req: Request):
        title = self.check_str(req.json.get('title'), require=True, maxlen=64, p_name='标题')
        content = self.check_str(req.json.get('content'), require=True, maxlen=255, p_name='内容')
        attachment = self.check_str(req.json.get('attachment'), require=True, p_name='附件')
        sender = self.check_str(req.json.get('sender'), require=True, p_name='发送者')
        receiver = self.check_int(req.json.get('receiver'), require=True, p_name='接收者')
        mail_type = self.check_int(req.json.get('mail_type'), require=True, p_name='邮件类型')
        exp_time = self.check_int(req.json.get('exp_time'), require=False, p_name='过期时间')
        sta, email = await MailsRC.create_mail(mail_type, sender, receiver, title, content, attachment, exp_time)
        if not sta:
            self.answer(self.sta_code.FAIL, hint='创建邮件失败')

        self.answer(data={'mail_id': email.mail_id})

    async def put(self, req: Request):
        title = self.check_str(req.json.get('title'), require=False, maxlen=64, p_name='标题')
        content = self.check_str(req.json.get('content'), require=False, maxlen=255, p_name='内容')
        attachment = self.check_str(req.json.get('attachment'), require=False, p_name='附件')
        sender = self.check_str(req.json.get('sender'), require=False, p_name='发送者')
        receiver = self.check_int(req.json.get('receiver'), require=False, p_name='接收者')
        mail_type = self.check_int(req.json.get('mail_type'), require=False, p_name='邮件类型')
        exp_time = self.check_int(req.json.get('exp_time'), require=False, p_name='过期时间')
        mail_id = self.check_int(req.json.get('mail_id'), require=True, p_name='邮件ID')
        sta, email = await MailsRC.update_mail(mail_id, mail_type, sender, receiver, title, content, attachment, exp_time)
        if not sta:
            self.answer(self.sta_code.FAIL, hint='更新邮件失败')

        self.answer(data={'mail_id': email.mail_id})

    async def get(self, req: Request):
        title = self.check_str(req.json.get('title'), require=True, maxlen=64, p_name='标题')
        content = self.check_str(req.json.get('content'), require=True, maxlen=255, p_name='内容')
        attachment = self.check_str(req.json.get('attachment'), require=True, p_name='附件')
        sender = self.check_str(req.json.get('sender'), require=True, p_name='发送者')
        receiver = self.check_int(req.json.get('receiver'), require=True, p_name='接收者')
        mail_type = self.check_int(req.json.get('mail_type'), require=True, p_name='邮件类型')
        exp_time = self.check_int(req.json.get('exp_time'), require=False, p_name='过期时间')
        sta, email = await MailsRC.create_mail(mail_type, sender, receiver, title, content, attachment, exp_time)
        if not sta:
            self.answer(self.sta_code.FAIL, hint='创建邮件失败')

        self.answer(data={'mail_id': email.mail_id})

