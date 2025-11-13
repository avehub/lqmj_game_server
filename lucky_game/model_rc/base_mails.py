"""
邮件相关
"""
import json
from datetime import datetime

from tortoise.transactions import in_transaction

from common.public.enum_const import DbKey
from .base_rc import BaseCommonRC
from tortoise.exceptions import OperationalError
from lucky_game.model_db.main import Mails
from nsanic.libs import tool_dt
from lucky_game.const import MailSta
from lucky_game.model_rc.base_award import AwardRC
from nsanic.libs.tool import json_parse, json_encode


class MailsRC(BaseCommonRC):
    """ 邮件模型 """
    db_model = Mails
    tb_name = db_model.sheet_name()

    MAX_SHOW_AMOUNT = 20  # 最多显示邮件数量

    @classmethod
    async def get_mails_list(cls, uid: int = None, start_time: int = None, end_time: int = None, page: int = None,
                             page_size: int = None, order_field: str = None, exp_time: int = None, mail_sta: any = None,
                             attachment_sta: any = None):
        """获取邮件列表"""
        try:
            query = {}
            if uid is not None:
                query["receiver"] = uid
            if start_time is not None:
                query["created__gte"] = start_time
            if end_time is not None:
                query["created__lt"] = end_time
            if mail_sta is not None:
                if isinstance(mail_sta, list):
                    query["mail_sta__in"] = mail_sta
                else:
                    query["mail_sta"] = mail_sta
            if attachment_sta is not None:
                if isinstance(attachment_sta, list):
                    query["attachment_sta__in"] = attachment_sta
                else:
                    query["attachment_sta"] = attachment_sta
            if order_field is None:
                order_field = "-mail_id"

            if exp_time is None:
                query["exp_time__gte"] = int(datetime.now().timestamp())
            else:
                query["exp_time__gte"] = exp_time
            if page and page_size:
                total, _ = await cls.count_mail_total(**query)
                mails = []
                if total > 0:
                    offset = (page - 1) * page_size
                    mails = await cls.db_model.filter(**query).order_by(order_field).offset(
                        offset).limit(page_size).values()
                result = await cls.page_result(page, page_size, total, mails)
            else:
                result = mails = await cls.db_model.filter(**query).order_by(order_field).values()
            if not mails:
                return False, result
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return True, result

    @classmethod
    async def count_mail_total(cls, **perms):
        """获取邮件数量"""
        try:
            count = await cls.db_model.filter(**perms).count()
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return True, count

    @classmethod
    async def get_mail_by_mail_id(cls, mail_id: int):
        """获取邮件"""
        mails = await cls.db_model.get_by_pk(mail_id)
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
    async def create_mail(cls, mail_type: int, sender: str, receiver: str, title: str, content: str, attachment: str, exp_time: int = None):
        """创建邮件"""
        try:
            receiver_list = json_parse(receiver)
            attachment_data = json_parse(attachment)
            now = int(datetime.now().timestamp())
            if isinstance(receiver_list, list):
                data_list = []
                for val in receiver_list:
                    data_list.append({
                        "mail_type": mail_type,
                        "sender": sender,
                        "receiver": val,
                        "title": title,
                        "content": content,
                        "attachment": attachment_data,
                        "receive_time": now,
                        "created": now,
                        "exp_time": exp_time if exp_time else now + 86400 * 30,
                    })
                sta, mail = await cls.bulk_create_mails(data_list)
                if not sta:
                    return False, mail
            else:
                mail = await cls.db_model.add_one({
                    "mail_type": mail_type,
                    "sender": sender,
                    "receiver": receiver,
                    "title": title,
                    "content": content,
                    "attachment": attachment_data,
                    "receive_time": now,
                    "exp_time": exp_time if exp_time else now + 86400 * 30,
                })
        except OperationalError as e:
            return False, e
        return True, mail

    @classmethod
    async def bulk_create_mails(cls, new_data: list):
        """批量写入邮件"""
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                instances = [cls.db_model(**data) for data in new_data]
                await cls.db_model.bulk_create(instances)
        except OperationalError as e:
            return False, f"子战绩入库失败, 原数据: {new_data}, 失败原因:{str(e)}"
        return True, "成功"

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
            if exp_time is not None:
                up_data["exp_time"] = exp_time

            mail = await cls.db_model.update_by_pk(mail_id, up_data)
        except OperationalError as e:
            return False, e
        return True, mail

    @classmethod
    async def del_mail(cls, mail_id: any):
        """删除邮件"""
        try:
            query = {}
            if mail_id is not None:
                if isinstance(mail_id, list):
                    query["mail_id__in"] = [str(i) for i in mail_id]
                else:
                    query["mail_id"] = str(mail_id)
                await cls.db_model.filter(**query).delete()
        except OperationalError as e:
            return False, e
        return True, mail_id


