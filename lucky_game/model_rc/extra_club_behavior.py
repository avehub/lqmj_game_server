"""
茶馆行为记录信息
"""

from tortoise.exceptions import OperationalError
from lucky_game.model_db.main import ExtraClubBehavior
from lucky_game.model_rc.base_rc import BaseCommonRC
from tortoise.transactions import in_transaction
from common.public.enum_const import DbKey
from lucky_game.model_rc.base_user import BaseUserRC


class ExtraClubBehaviorRC(BaseCommonRC):
    db_model = ExtraClubBehavior
    tb_name = db_model.sheet_name()

    BEHAVIOR_APPLY_INDEX = 1
    BEHAVIOR_BLACK_INDEX = 2
    BEHAVIOR_ISOLATION_INDEX = 3
    BEHAVIOR_OUT_INDEX = 4
    BEHAVIOR_MANAGE_INDEX = 5
    BEHAVIOR_TEMPLATE_INDEX = 6
    BEHAVIOR_TYPE = {
        1: "加入茶馆申请",
        2: "小黑屋",
        3: "隔离",
        4: "退出茶馆",
        5: "管理员",
        6: "玩法"
    }

    BEHAVIOR_STATUS_DEFAULT = 0
    BEHAVIOR_STATUS_REFUSE = 1
    BEHAVIOR_STATUS_CANCEL = 2
    BEHAVIOR_STATUS_ALTER = 3
    BEHAVIOR_STATUS_SUCCEED = 99
    BEHAVIOR_STATUS = {
        0: "未审批",
        1: "拒绝",
        2: "取消",
        3: "更新",
        99: "通过"
    }

    @classmethod
    async def _type_re_status(cls, behavior_type):
        """类型和状态对应关系"""
        status = cls.BEHAVIOR_STATUS_DEFAULT
        if behavior_type in [cls.BEHAVIOR_BLACK_INDEX, cls.BEHAVIOR_ISOLATION_INDEX]:
            status = cls.BEHAVIOR_STATUS_SUCCEED
        return status

    @classmethod
    async def create_club_behavior(cls, behavior_type: int, uid: int, club_id: int, check_uid: int = 0, status: int = None):
        """新增茶馆行为"""
        try:
            if status is None:
                status = await cls._type_re_status(behavior_type)
            row = await cls.db_model.add_one({
                "uid": uid,
                "club_id": club_id,
                "type": behavior_type,
                "status": status,
                "check_uid": check_uid,
            })
            if not row:
                return False, "创建失败"
        except OperationalError as e:
            return False, f"失败：{str(e)}"
        return row.id, "成功"

    @classmethod
    async def bulk_create_club_behavior(cls, new_data: list):
        """批量新增茶馆行为"""
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                instances = [cls.db_model(**data) for data in new_data]
                await cls.db_model.bulk_create(instances)
        except OperationalError as e:
            return False, f"失败：{str(e)}"
        return True, "成功"

    @classmethod
    async def update_club_behavior(cls, behavior_id: int, up_data: dict):
        """更新茶馆行为"""
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                data, e = await cls.get_behavior_by_id(behavior_id)
                if not data:
                    return False, e
                up_status = up_data.get("status")
                if up_status in [cls.BEHAVIOR_STATUS_REFUSE, cls.BEHAVIOR_STATUS_CANCEL]:
                    sta, e = await cls.delete_club_behavior(behavior_id)
                    if not sta:
                        return False, "更新失败"
                else:
                    sta = await cls.db_model.update_by_pk(behavior_id, up_data, data)
                    if not sta:
                        return False, "更新失败"
                    sta_after, e = await cls._behavior_after(data, up_status)
                    if not sta_after:
                        return False, e
        except OperationalError as e:
            return False, f"失败：{str(e)}"
        return True, data

    @classmethod
    async def delete_club_behavior(cls, behavior_id: int):
        """删除茶馆行为"""
        try:
            await cls.db_model.filter(id=behavior_id).delete()
        except OperationalError as e:
            return False, f"失败：{str(e)}"
        return True, "成功"

    @classmethod
    async def more_delete_club_behavior(cls, **kwargs):
        """批量删除茶馆行为"""
        try:
            query = {}
            behavior_id = kwargs.get("behavior_id")
            club_id = kwargs.get("club_id")
            uid = kwargs.get("uid")
            behavior_type = kwargs.get("type")
            status = kwargs.get("status")
            if behavior_id is not None:
                if isinstance(behavior_id, list):
                    query["id__in"] = behavior_id
                else:
                    query["id"] = behavior_id
            if club_id is not None:
                if isinstance(club_id, list):
                    query["club_id__in"] = club_id
                else:
                    query["club_id"] = club_id
            if uid is not None:
                if isinstance(uid, list):
                    query["uid__in"] = uid
                else:
                    query["uid"] = uid
            if behavior_type is not None:
                query["type"] = behavior_type
            if status is not None:
                query["status"] = status
            await cls.db_model.filter(**query).delete()
        except OperationalError as e:
            return False, f"失败：{str(e)}"
        return True, "成功"

    @classmethod
    async def get_behavior_by_id(cls, behavior_id: int):
        """根据ID获取茶馆行为"""
        try:
            result = await cls.db_model.get_by_pk(behavior_id)
            if not result:
                return result, "茶馆行为不存在"
        except OperationalError as e:
            return False, f"失败：{str(e)}"
        return result, "成功"

    @classmethod
    async def get_behavior_by_filter(cls, club_id: any = None, type: int = None, uid: int = None, status: int = None,
                                     page: int = None, page_size: int = None, status_range: int = None):
        """多条件查询茶馆操作行为列表"""
        try:
            query = {}
            if club_id is not None:
                if isinstance(club_id, list):
                    query["club_id__in"] = club_id
                else:
                    query["club_id"] = club_id
            if status is not None:
                query["status"] = status
            if status_range is not None:
                query["status__gte"] = status_range
            if uid is not None:
                query["uid"] = uid
            if type is not None:
                query["type"] = type
            if page and page_size:
                total = await cls.db_model.get_count(query)
                data = []
                if total > 0:
                    offset = (page - 1) * page_size
                    data = await cls.db_model.filter(**query).order_by("-id").offset(offset).limit(page_size).values()
                result = await cls.page_result(page, page_size, total, data)
            else:
                result = data = await cls.db_model.filter(**query).order_by("-id").values()
            if not data:
                return result, "暂无数据"
        except OperationalError as e:
            return False, f"查询失败: {str(e)}"
        return result, "成功"

    @classmethod
    async def _behavior_after(cls, behavior_data: dict, up_status: int = 0):
        """根据茶馆行为进行之后的操作"""
        try:
            from lucky_game.model_rc.base_clubs import BaseClubRC  # 延迟导入
            from lucky_game.model_rc.club_users import ClubUsersRC
            club_id = behavior_data.get("club_id")
            uid = behavior_data.get("uid")
            behavior_type = behavior_data.get("type")
            if up_status == cls.BEHAVIOR_STATUS_SUCCEED or behavior_type == cls.BEHAVIOR_APPLY_INDEX:
                # 加入茶馆用户关系
                up_club_user = await ClubUsersRC.create_club_user(uid, club_id)
                if not up_club_user:
                    return False, "更新茶馆用户关系失败"
                # 更新茶馆玩家数
                up_club = await BaseClubRC.update_club_int_field(club_id, "num", 1, "add")
                if not up_club:
                    return False, "更新茶馆信息失败"
        except OperationalError as e:
            return False, f"失败：{str(e)}"
        return True, "成功"

    @classmethod
    async def club_behavior_explain(cls, data: list):
        """茶馆行为说明"""
        if not data:
            return data

        for item in data:
            explain = ""
            u_info = await BaseUserRC.cache_by_pk(item["uid"])
            check_info = await BaseUserRC.cache_by_pk(item["check_uid"])
            if u_info and len(u_info["name"]) > 6:
                u_info["name"] = u_info['name'][0:6] + "..."
            if check_info and len(check_info["name"]) > 6:
                check_info["name"] = check_info['name'][0:6] + "..."
            # 茶馆申请
            if item["type"] == cls.BEHAVIOR_APPLY_INDEX:
                msg = "同意"
                if item["status"] == cls.BEHAVIOR_STATUS_REFUSE:
                    msg = "拒绝"
                explain = f"{check_info['name']}{msg}了{u_info['name']}的加入申请"
            # 黑名单
            elif item["type"] == cls.BEHAVIOR_BLACK_INDEX:
                msg = "加入"
                if item["status"] == cls.BEHAVIOR_STATUS_CANCEL:
                    msg = "移除"
                explain = f"{check_info['name']}将{u_info['name']}{msg}黑名单"
            # 隔离组
            elif item["type"] == cls.BEHAVIOR_ISOLATION_INDEX:
                msg = "加入"
                if item["status"] == cls.BEHAVIOR_STATUS_CANCEL:
                    msg = "移出"
                if item["status"] == cls.BEHAVIOR_STATUS_ALTER:
                    msg = "更新至"
                explain = f"{check_info['name']}将{u_info['name']}{msg}隔离组"
            # 退出茶馆
            elif item["type"] == cls.BEHAVIOR_OUT_INDEX:
                msg = "退出"
                explain = f"{u_info['name']}{msg}了茶馆"
                if item["check_uid"]:
                    msg = "移出"
                    explain = f"{check_info['name']}将{u_info['name']}{msg}了茶馆"
            elif item["type"] == cls.BEHAVIOR_MANAGE_INDEX:
                msg = "设为了管理员"
                if item["status"] == cls.BEHAVIOR_STATUS_CANCEL:
                    msg = "设为了普通成员"
                explain = f"{check_info['name']}将{u_info['name']}{msg}"
            elif item["type"] == cls.BEHAVIOR_TEMPLATE_INDEX:
                msg = "新增"
                if item["status"] == cls.BEHAVIOR_STATUS_CANCEL:
                    msg = "删除"
                elif item["status"] == cls.BEHAVIOR_STATUS_ALTER:
                    msg = "修改"
                explain = f"{u_info['name']}{msg}了模板"
            item["explain"] = explain
        return data
