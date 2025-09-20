"""
邮件相关
"""
from .base_rc import BaseRC
from lucky_game.model_db.main import Mails
from nsanic.libs import tool_dt
from lucky_game.const import MailSta


class MailsRC(BaseRC):
    """ 邮件模型 """
    db_model = Mails
    tb_name = db_model.sheet_name()

    MAX_SHOW_AMOUNT = 20  # 最多显示邮件数量

    @classmethod
    async def get_mails_list(cls, uid, amount=MAX_SHOW_AMOUNT):
        """获取邮件列表"""
        condition = {
            'receiver': uid,
            'mail_sta__gte': MailSta.UNREAD.val,  # 联合索引要使用大于等于，否则索引失效
            'exp_time__gte': tool_dt.cur_time()
        }
        orders = ['attachment_sta', 'mail_sta', '-receive_time']  # 排序规则
        mails = await cls.db_model.get_by_dict(condition, orders=orders, limit=amount)
        return mails

    @classmethod
    async def get_unread_mails(cls, uid):
        """获取是否有未读"""
        condition = {
            'receiver': uid,
            'mail_sta': MailSta.UNREAD.val,
            'exp_time__gte': tool_dt.cur_time()
        }
        mails_info = await cls.db_model.get_by_dict(condition, limit=1)
        if mails_info:
            return True
        return False
