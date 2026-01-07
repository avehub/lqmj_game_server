"""
代理用户相关逻辑

"""
from lucky_proxy.model_db.main import ProxyUser
from lucky_game.model_rc.base_rc import BaseCommonRC
from nsanic.libs.component import LogMeta


class ProxyUserLogic(LogMeta):
    table_name = "proxy_user"

    @classmethod
    async def get_proxy_user_filter(cls, player_id: int = None, status: int = None, proxy_level: int = None,
                                    phone: str = None, promotion_code: str = None, page: int = None,
                                    page_size: int = None):
        """
        获取proxy_user列表页
        """
        where = "1=1"
        if player_id is not None:
            where += f" AND id = {player_id}"
        if status is not None:
            where += f" AND status = {status}"
        if proxy_level is not None:
            where += f" AND proxy_level = {proxy_level}"
        if phone is not None:
            where += f" AND phone = {phone}"
        if promotion_code is not None:
            where += f" AND promotion_code = '{promotion_code}'"
        try:
            sql = f"SELECT * FROM {cls.table_name} WHERE {where}"
            total = 0
            if page and page_size:
                total = await ProxyUser.exec_sql(f"SELECT COUNT(*) as total FROM {cls.table_name} WHERE {where}", query=True)
                if total:
                    total = total[0]["total"]
                if total > 0:
                    offset = (page - 1) * page_size
                    sql += f" LIMIT {page_size} OFFSET {offset}"
            result = await ProxyUser.exec_sql(sql, query=True)
            if page and page_size and result:
                result = await BaseCommonRC.page_result(page, page_size, total, result)
        except Exception as ex:
            cls.log_err(f"查询代理ID失败: {ex}")
            raise
        return result

    @classmethod
    async def update_proxy_user(cls, player_id: int, up_data: dict):
        """
        更新proxy_user
        """
        sta = False
        proxy_user = await cls.get_proxy_user_filter(player_id=player_id)
        if not proxy_user:
            return sta, "更新的代理不存在"
        update_data = ""
        valid_fields = {"proxy_name", "status", "proxy_level", "phone", "promotion_code", "is_deleted", "vip_level", "vip_expire_time"}
        for k, v in up_data.items():
            if k in valid_fields and v is not None:
                if update_data:
                    update_data += ", "
                if k == 'promotion_code':
                    v = f"'{v}'"
                update_data += f" {k}={v}"
        if update_data:
            sql = f"UPDATE {cls.table_name} SET {update_data} WHERE id={player_id}"
            cls.log_info(f"代理SQL: {sql}")

            sta = await ProxyUser.exec_sql(sql)
        return sta, "更新成功"


