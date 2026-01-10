"""
赛事奖励配置表
"""
from nsanic.libs import tool_dt
from nsanic.libs.tool import json_encode, json_parse
from common.model_rc.base_rc import BaseCommonRC
from lucky_game.model_db.main import TournamentRewards
from tortoise.exceptions import OperationalError

from lucky_game.model_rc.base_award import AwardRC


class TournamentRewardRC(BaseCommonRC):
    db_model = TournamentRewards
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
    async def add_reward(cls, round_type, rank_start, rank_end, reward_content, reward_description):
        """新增赛事奖励"""
        try:
            data = {
                "round_type": round_type,
                "rank_start": rank_start,
                "rank_end": rank_end,
                "reward_content": reward_content,
                "reward_description": reward_description,
            }
            new = await cls.db_model.add_one(data)
            if not new:
                return False, "添加失败"
        except OperationalError as e:
            return None, f"失败:{e}"
        return True, new

    @classmethod
    async def update_reward(cls, reward_id, up_data: dict):
        """更新赛事奖励"""
        try:
            query = {"id": reward_id}
            valid_fields = {"round_type", "rank_start", "rank_end", "updated", "reward_content", "reward_description"}
            update_data = {k: v for k, v in up_data.items() if k in valid_fields}
            if update_data:
                await cls.db_model.filter(**query).update(**update_data)
                await cls.cache_session_del(reward_id)
        except OperationalError as e:
            return None, f"失败:{e}"
        return True, "成功"

    @classmethod
    async def get_reward_filter(cls, round_type: int = None, status: int = None, rank_start: int = None, rank_end: int = None,
                                  count: bool = False, reward_id: int = None, page: int = None, page_size: int = None):
        """获取赛事奖励记录"""
        try:
            query = {}
            if reward_id is not None:
                query["id"] = reward_id
            if status is not None:
                query["status"] = status
            if round_type is not None:
                query["round_type"] = round_type
            if rank_start is not None:
                query["rank_start__gte"] = rank_start
            if rank_end is not None:
                query["rank_end__lte"] = rank_end
            order_field = "id"
            if count:
                result = await cls.db_model.filter(**query).count()
            else:
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
    async def get_reward_info(cls, reward_id: int):
        """获取赛事奖励信息"""
        try:
            result = await cls.cache_session_get(reward_id)
            if result:
                return True, result
            sta, data = await cls.get_reward_filter(reward_id=reward_id)
        except OperationalError as e:
            return None, f"查询失败:{e}"
        if sta and data:
            result = data[0]
            if result["reward_content"]:
                for x in result["reward_content"]:
                    x["award_content"] = []
                    award_ids = set()
                    for x_id in x["award_ids"]:
                        if x_id not in award_ids:
                            award_ids.add(x_id)
                            award_content, _ = await AwardRC.get_award_info(award_id=x_id, is_content=False)
                            x["award_content"].append(award_content)
            await cls.cache_session_set(reward_id, result)
        return True if result else False, result

    @classmethod
    async def del_reward(cls, reward_id: int):
        """删除赛事奖励"""
        try:
            await cls.db_model.filter(id=reward_id).delete()
            await cls.cache_session_del(reward_id)
        except OperationalError as e:
            return None, f"操作失败:{e}"
        return True, "成功"
