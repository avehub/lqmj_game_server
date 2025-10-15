"""
茶馆日常事件记录
"""
from tortoise.exceptions import OperationalError
from lucky_game.model_db.main import ExtraClubEvent
from lucky_game.model_rc.base_rc import BaseCommonRC


class ExtraClubEventRC(BaseCommonRC):
    db_model = ExtraClubEvent
    tb_name = db_model.sheet_name()

    KEY_EVENT_ID = 'event_id'

    EVENT_TYPE = {
        'FUND_RECHARGE': 1,  # 基金充值
        'FUND_CONSUME': 2,   # 基金消耗
        'APPROVAL_LOG': 3,    # 入馆审批
        'CLOSE_LOG': 4    # 茶馆解散
    }
    EVENT_MSG = {
        1: "茶馆基金充值 {price}",
        2: "茶馆基金消耗 {price}, 创建房间（ID: {room_id}）",
        3: "管理员（ID：{check_uid}）审批（ID：{uid}）加入茶馆",
        4: "茶馆基金消耗 {price}, 解散茶馆",
    }

    @classmethod
    async def create_event(cls, club_id: int, event_type: int, uid: int, explain: str):
        """创建茶馆事件记录"""
        try:
            event_data = {
                "club_id": club_id,
                "type": event_type,
                "uid": uid,
                "explain": explain
            }
            
            new_event = await cls.db_model.add_one(event_data)
            return new_event, None
        except OperationalError as e:
            return None, f"事件记录创建失败: {str(e)}"

    @classmethod
    async def delete_event(cls, club_id: int, event_type: int, uid: int):
        """删除茶馆事件记录"""
        try:
            query = {
                "club_id": club_id,
                "type": event_type,
                "uid": uid,
            }
            event = await cls.db_model.filter(**query).order_by("id").first()
            if not event:
                return True, "未找到相关事件"
            return await cls.delete_event_by_id(event.id)
        except OperationalError as e:
            return None, f"事件记录创建失败: {str(e)}"

    @classmethod
    async def delete_event_by_id(cls, event_id: int):
        """通过ID删除茶馆事件记录"""
        try:
            sta = await cls.db_model.del_by_pk(event_id)
            if not sta:
                return sta, "删除失败"
        except OperationalError as e:
            return None, f"事件记录创建失败: {str(e)}"
        return sta, "成功"

    @classmethod
    async def get_by_filter(cls, club_id: int = None, event_type: int = None, uid: int = None, start_time: int = None,
                            end_time: int = None,
                            page_size: int = None, page: int = None, order_field: str = None, order_type: str = "DESC"):
        """根据条件获取茶馆列表"""
        try:
            query = {}
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
            if start_time is not None:
                query["created__gte"] = start_time
            if end_time is not None:
                query["created__lt"] = end_time
            if event_type is not None:
                query["event_type"] = event_type
            if order_field is None:
                order_field = "-id"
            if page and page_size:
                total, _ = await cls.count_record_total(**query)
                records = []
                if total > 0:
                    offset = (page - 1) * page_size
                    records = await cls.db_model.filter(**query).order_by(order_field).offset(offset).limit(
                        page_size).values()
                result = await cls.page_result(page, page_size, total, records)
            else:
                result = records = await cls.db_model.filter(**query).order_by(order_field).values()
            if not records:
                return result, "暂无记录"
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return result, "成功"

    @classmethod
    async def count_record_total(cls, **kwargs):
        """获取记录总数"""
        try:
            total = await cls.db_model.filter(**kwargs).count()
        except OperationalError as e:
            return 0, f"查询失败: {str(e)}"
        return total, "成功"
