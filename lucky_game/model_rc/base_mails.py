"""
邮件相关
"""
from datetime import datetime

from .base_rc import BaseRC
from tortoise.exceptions import OperationalError
from lucky_game.model_db.main import Mails
from nsanic.libs import tool_dt
from lucky_game.const import MailSta
from lucky_game.model_rc.base_award import AwardRC


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

    @classmethod
    async def get_mail_awards(cls, mail_list: list):
        """获取邮件奖励"""
        attachments = [i.get('attachment').get("award_ids") for i in mail_list]
        if attachments:
            award_ids = []
            for i in attachments:
                award_ids.extend(i)
            award_data, e = await AwardRC.get_award_by_filter(award_id=award_ids)
            if award_data:
                award_dict = {item['award_id']: item for item in award_data}
                for i in mail_list:
                    i_award_ids = i.get('attachment').get("award_ids")
                    i['attachment']['awards'] = []
                    for i_award_id in i_award_ids:
                        i_award = award_dict.get(i_award_id)
                        if i_award:
                            i['attachment']['awards'].extend(i_award.get("content")["rewards"])
        return mail_list


    @classmethod
    async def create_mail(cls, mail_type, sender, receiver, title, content, attachment, exp_time: int = None):
        """创建邮件"""
        try:
            now = int(datetime.now().timestamp())
            mail = await cls.db_model.add_one({
                "mail_type": mail_type,
                "sender": sender,
                "receiver": receiver,
                "title": title,
                "content": content,
                "attachment": attachment,
                "receive_time": now,
                "exp_time": exp_time if exp_time else now + 86400 * 30,
            })
        except OperationalError as e:
            return False, e
        return True, mail

    @classmethod
    async def update_mail(cls, mail_id, mail_type: int = None, sender: str = None, receiver: int =None, title: str = None,
                          content: str = None, attachment: str = None, exp_time: int = None):
        """更新邮件"""
        try:
            up_data = {}
            if mail_type:
                up_data["mail_type"] = mail_type
            if sender:
                up_data["sender"] = sender
            if title is not None:
                up_data["title"] = title
            if attachment:
                up_data["attachment"] = attachment
            if content is not None:
                up_data["content"] = content
            if receiver is not None:
                up_data["receiver"] = receiver
            if up_data:
                now = int(datetime.now().timestamp())
                up_data["exp_time"] = exp_time if exp_time else now + 86400 * 30

            mail = await cls.db_model.update_by_pk(mail_id, up_data)
        except OperationalError as e:
            return False, e
        return True, mail

