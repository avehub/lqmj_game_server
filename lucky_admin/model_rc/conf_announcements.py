from nsanic.libs import tool_dt
from nsanic.orm.rc_model import RCModel
from tortoise.expressions import Q

from lucky_admin.const import UserGroup, AnnouncementsStatus, WeightEnum
from lucky_admin.handler.decorator import filter_not_out_of_date_data
from lucky_game.model_db.main import ConfAnnouncements


class ConfAnnouncementsRC(RCModel):
    """ 公告模型 """
    db_model = ConfAnnouncements
    tb_name = db_model.sheet_name()

    expired_mode = 1
    expired_sec = 172800  # 2 * 86400

    @classmethod
    async def get_current_announcement(cls):
        """
        获取当前公告
        目前简单这样做
        """
        async def from_db():
            db_info = await cls.db_model.filter(
                ~Q(status=AnnouncementsStatus.OUT_OF_TIME),
                # Q(start_time__lte=cur_time),
                # Q(end_time__gte=cur_time)
            ).values()
            await cls.conf.rds.set_item(cls.tb_name, db_info)
            return db_info

        cur_time = tool_dt.cur_time()
        info_list = await cls.conf.rds.get_item(cls.tb_name, jsparse=True)
        if isinstance(info_list, list):
            # 过滤
            info_list, update = filter_not_out_of_date_data(info_list, cur_time, AnnouncementsStatus.OUT_OF_TIME)
            if update:
                await cls.db_model.filter(end_time__lt=cur_time).update(status=AnnouncementsStatus.OUT_OF_TIME)
                await cls.conf.rds.set_item(cls.tb_name, info_list)
            return info_list
        return await cls.conf.rds.locked(cls.tb_name, from_db)

    @classmethod
    async def add_announcement(
            cls,
            title,
            content,
            start_time,
            end_time,
            carousel_count,
            target_group=UserGroup.USER_ALL,
            status=AnnouncementsStatus.DRAFT,
            weight=WeightEnum.W2
    ):
        """ 添加公告 """
        row_data = {
            "title": title,
            "content": content,
            "start_time": start_time,
            "end_time": end_time,
            "carousel_count": carousel_count,
            "target_group": target_group,
            "status": status,
            "weight": weight
        }
        model_sta = await cls.db_model.add_one(row_data)
        if model_sta:
            row_data['id'] = model_sta.id
            info_list = await cls.conf.rds.get_item(cls.tb_name, jsparse=True)
            if isinstance(info_list, list):
                info_list.append(row_data)
            else:
                info_list = [row_data]
            await cls.conf.rds.set_item(cls.tb_name, info_list)
            return [row_data]
        return None
