"""
周期排行榜表
"""
from nsanic.libs import tool_dt
from nsanic.libs.tool import json_encode, json_parse
from tortoise.transactions import in_transaction

from common.model_rc.base_rc import BaseCommonRC
from common.public.enum_const import DbKey
from lucky_game.model_db.main import TournamentCycleLeaderboard
from tortoise.exceptions import OperationalError


def get_diff_index(now_index, data):
    if now_index == 0:
        return now_index
    new_data = data[:now_index]
    total = len(new_data)
    for index, item in enumerate(new_data):
        total -= 1
        if item["total_points"] < data[total]["total_points"]:
            return index+1

class TournamentCycleLeaderboardRC(BaseCommonRC):
    db_model = TournamentCycleLeaderboard
    tb_name = db_model.sheet_name()
    expired_mode = 0


    @classmethod
    async def cache_session_set(cls, query, value):
        return await cls.conf.rds.set_item(f"{cls.tb_name}:{query}", value)

    @classmethod
    async def cache_session_get(cls, query):
        data = await cls.conf.rds.get_item(f"{cls.tb_name}:{query}")
        if isinstance(data, bytes):
            data = json_parse(data.decode())
        return data

    @classmethod
    async def cache_session_del(cls, query):
        return await cls.conf.rds.del_item(f"{cls.tb_name}:{query}")

    @classmethod
    async def add_leaderboard(cls, cycle_id, uid, total_points, participated_rounds: int = 1):
        """新增排行榜"""
        try:
            data = {
                "cycle_id": cycle_id,
                "uid": uid,
                "total_points": total_points,
                "participated_rounds": participated_rounds,
            }
            new = await cls.db_model.add_one(data)
            if not new:
                return False, "添加失败"
        except OperationalError as e:
            return None, f"失败:{e}"
        return True, new

    @classmethod
    async def bulk_add_leaderboard(cls, new_data: list):
        """批量写入排行榜数据"""
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                instances = [cls.db_model(**data) for data in new_data]
                await cls.db_model.bulk_create(instances)
        except OperationalError as e:
            return False, f"入库失败, 原数据: {new_data}, 失败原因:{str(e)}"
        return True, "成功"

    @classmethod
    async def update_leaderboard(cls, leaderboard_id, up_data: dict):
        """更新排行榜"""
        try:
            query = {"id": leaderboard_id}
            valid_fields = {"cycle_id", "uid", "total_points", "updated", "participated_rounds"}
            update_data = {k: v for k, v in up_data.items() if k in valid_fields}
            if update_data:
                await cls.db_model.filter(**query).update(**update_data)
        except OperationalError as e:
            return None, f"失败:{e}"
        return True, "成功"

    @classmethod
    async def get_leaderboard_filter(cls, cycle_id: int = None, total_points: int = None, uid: int = None, page: int = None,
                                     page_size: int = None):
        """获取排行榜记录"""
        try:
            query = {}
            if total_points is not None:
                query["total_points__gle"] = total_points
            if cycle_id is not None:
                query["cycle_id"] = cycle_id
            if uid is not None:
                query["uid"] = uid
            order_field = "-total_points"
            if page and page_size:
                total = await cls.db_model.filter(**query).count()
                data = []
                if total > 0:
                    offset = (page - 1) * page_size
                    data = await cls.db_model.filter(**query).order_by(order_field).offset(
                        offset).limit(page_size).values()
                result = await cls.page_result(page, page_size, total, data)
            else:
                result = data = await cls.db_model.filter(**query).order_by(order_field).values()
            if not data:
                return False, result
        except OperationalError as e:
            return None, f"查询失败:{e}"
        return True, result

    @classmethod
    async def get_uid_leaderboard(cls, cycle_id: int, uid: int = None):
        """获取用户在赛事周期内的排行榜信息"""
        result = None
        try:
            sta, data = await cls.get_leaderboard_filter(cycle_id=cycle_id, uid=uid)
        except OperationalError as e:
            return None, f"查询失败:{e}"
        if data:
            result = data[0]
        return True if result else False, result

    @classmethod
    async def get_uid_rank_position(cls, cycle_id: int, uid: int):
        """获取用户在赛事周期内的排行榜信息"""
        sql = f"SELECT t1.uid,t1.total_points,(SELECT COUNT(*) + 1 FROM tournament_cycle_leaderboard t2 WHERE t2.cycle_id = t1.cycle_id AND t2.total_points > t1.total_points) as rank_position FROM tournament_cycle_leaderboard t1 WHERE t1.cycle_id = {cycle_id} AND t1.uid = {uid}"
        result = await cls.db_model.exec_query(sql)
        return True if result else False, result

    @classmethod
    async def get_uid_rank_and_difference(cls, cycle_id: int, uid: int) -> dict:
        """获取用户在赛事周期内的排行及同上一名差额信息"""
        result = {
            "uid": uid,
            "total_points": 0,  # 总积分
            "rank_position": 0,  # 排名
            "difference": 0,  # 同上名积分差
        }
        sta, data = await cls.get_leaderboard_filter(cycle_id=cycle_id)
        if data:
            for item in data:
                if uid == item["uid"]:
                    result["total_points"] = item["total_points"]
                    result["rank_position"] = data.index(item) + 1
                    now_index = data.index(item)
                    if now_index > 0:
                        last_index = get_diff_index(now_index, data)
                        result["difference"] = data[last_index]["total_points"] - item["total_points"]
                    break
            # 如果用户不在排行榜中取最后一名积分
            if result["total_points"] == 0:
                result["difference"] = data[-1]["total_points"]



        return result