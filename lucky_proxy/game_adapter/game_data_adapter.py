from datetime import datetime
from nsanic.libs.component import LogMeta

from common.utils.utils import UtilsTool
from lucky_proxy.config import ConfSrv, conf_srv
from lucky_proxy.const import ProxyLevel
from lucky_proxy.logic.game_data_sync import GameDataSync, PromotionAddUserDTO, PromotionOrderDataDTO, Level1ProxyDTO
from lucky_proxy.model_db.main import ProxyPromotionCode, ProxyPromotionRelation, ProxyUser

"""
游戏数据同步适配器
"""


class GameDataAdapter(LogMeta):
    conf: ConfSrv = conf_srv

    """
    增加一级代理
    """

    @classmethod
    async def add_level1_proxy(cls, data: Level1ProxyDTO):
        proxy_user: ProxyUser = await  ProxyUser.get_by_pk(data.player_id, field=["id"])
        if proxy_user:
            return False, "EXISTS"
        return await GameDataSync.init_level1_proxy(Level1ProxyDTO)


    """
     同步分销订单数据
    """

    @classmethod
    async def sync_promotion_order_data(cls, data: PromotionOrderDataDTO):
        query_relation = {
            "player_id": data.player_id
        }
        relation: ProxyPromotionRelation = await ProxyPromotionRelation.get_by_dict(query_relation, limit=1)
        if not relation:
            cls.log_info(f"忽悠游戏同步代理订单数据uid={data.uid},order_id={data.order_id}")
            return 0
        proxy_id = relation.get("proxy_id")
        proxy_user: ProxyUser = await ProxyUser.get_by_pk(proxy_id,
                                                          ["level1_proxy_id", "room_card_rate",
                                                           "assistance_program_rate"])
        if not proxy_user:
            cls.log_info(
                f"忽悠游戏同步代理订单数据uid={data.uid},order_id={data.order_id},reason={proxy_id} 已被清退或者不存在")
            return 0

        await GameDataSync.save_dividend_records(data, relation, proxy_user)

    """
    同步邀请新增用户
    """

    @classmethod
    async def sync_promotion_user(cls, data: PromotionAddUserDTO):
        query = {
            "promotion_code": data.promotion_code,
            "is_deleted": 0
        }
        promotion_code: ProxyPromotionCode = await ProxyPromotionCode.get_by_dict(query, limit=1, with_del=False)
        if not promotion_code:
            cls.log_info(f"忽悠游戏同步邀请关系绑定uid={data.uid},promotion_code={data.promotion_code}"
                         f",promotion_type={data.promotion_type}")
            return 0
        query_relation = {
            "promotion_id": promotion_code.get("id")
        }
        exists_relation: ProxyPromotionRelation = await  ProxyPromotionRelation.get_by_dict(query_relation, limit=1)
        if exists_relation:
            cls.log_info(f"游戏同步邀请关系已被绑定uid={data.uid},promotion_code={data.promotion_code}"
                         f",promotion_type={data.promotion_type}")
            return 0
        data_date = datetime.fromtimestamp(data.promotion_time)
        relation = {
            "player_id": data.uid,
            "promotion_time": data.promotion_time,
            "promotion_year": data_date.strftime("%Y"),
            "promotion_month": data_date.strftime("%Y-%m"),
            "promotion_day": data_date.strftime("%Y-%m-%d"),
            "promotion_type": data.promotion_type,
            "promotion_id": promotion_code.get("id"),
            "proxy_id": promotion_code.get("proxy_id"),
            "level": promotion_code.get("level"),

        }
        # TODO 入库数据统计维度字段
        await ProxyPromotionRelation.add_one(relation)
        return 1


if __name__ == '__main__':
    pass
