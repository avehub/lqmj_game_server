from nsanic.libs import tool_dt
from nsanic.orm.rc_model import RCModel
from tortoise.expressions import Q

from promising_admin.const import MailSta
from promising_admin.handler.decorator import filter_not_out_of_date_data
from promising_admin.model_db.main import RecordsAdminMails


class RecordsAdminMailsRC(RCModel):
    """ 邮件记录 """
    db_model = RecordsAdminMails
    tb_name = db_model.sheet_name()

    @classmethod
    async def get_active_mails(cls):
        """
        获取当前邮件
        """
        async def from_db():
            db_info = await cls.db_model.filter(
                Q(status=MailSta.NORMAL),
                Q(start_time__lte=cur_time),
                Q(end_time__gte=cur_time)
            ).values()
            await cls.conf.rds.set_item(cls.tb_name, db_info)
            return db_info

        cur_time = tool_dt.cur_time()
        info_list = await cls.conf.rds.get_item(cls.tb_name, jsparse=True)
        if isinstance(info_list, list):
            # 过滤
            info_list, update = filter_not_out_of_date_data(info_list, cur_time)
            if update:
                await cls.db_model.filter(end_time__lt=cur_time).update(status=MailSta.OUT_OF_DATE)
                await cls.conf.rds.set_item(cls.tb_name, info_list)
            return info_list
        return await cls.conf.rds.locked(cls.tb_name, from_db)

    @classmethod
    async def insert_one(
            cls, mail_type, title, content, attachment, sender, start_time, end_time, status=1, job_id=None):
        data = {
            "mail_type": mail_type,
            "title": title,
            "content": content,
            "attachment": attachment,
            "sender": sender,
            "start_time": start_time,
            "end_time": end_time,
            "status": status,
            "job_id": job_id,
        }
        sta = await cls.db_model.add_one(data)
        if sta:
            data["id"] = sta.id
            info_list = await cls.conf.rds.get_item(cls.tb_name, jsparse=True)
            if isinstance(info_list, list):
                info_list.append(data)
            else:
                info_list = [data]
            await cls.conf.rds.set_item(cls.tb_name, info_list)
            return sta

    @classmethod
    async def cancel_mail(cls, job_id):
        """ 更新邮件信息 """
        sta = await cls.db_model.update_by_cond({"job_id": job_id}, {"status": MailSta.CANCELED})
        if sta:
            info_list = await cls.conf.rds.get_item(cls.tb_name, jsparse=True)
            new_info_list = []
            for info in info_list or []:
                if job_id == info.get("job_id"):
                    continue
                new_info_list.append(info)
            await cls.conf.rds.set_item(cls.tb_name, new_info_list)

    @classmethod
    async def update_info(cls, pk_val, up_info: dict):
        """ 更新信息 """
        sta = await cls.db_model.update_by_pk(pk_val, up_info)
        if sta:
            info_list = await cls.conf.rds.get_item(cls.tb_name, jsparse=True)
            for info in info_list or []:
                if pk_val == info.get("id"):
                    info.update(up_info)
                    break
            await cls.conf.rds.set_item(cls.tb_name, info_list)


