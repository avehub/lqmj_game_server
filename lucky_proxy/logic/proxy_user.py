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
                                    page_size: int = None, vip_start_time: int = None, vip_end_time: int = None,
                                    vip_level: int = None):
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
        if vip_start_time is not None:
            where += f" AND vip_expire_time >= '{vip_start_time}'"
        if vip_end_time is not None:
            where += f" AND vip_expire_time < '{vip_end_time}'"
        if vip_level is not None:
            where += f" AND vip_level = {vip_level}"
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
        valid_fields = {"proxy_name", "status", "proxy_level", "phone", "promotion_code", "is_deleted", "vip_level", "vip_expire_time", "is_channel", "channel_proxy_id"}
        for k, v in up_data.items():
            if k in valid_fields and v is not None:
                if update_data:
                    update_data += ", "
                if k == 'promotion_code':
                    v = f"'{v}'"
                update_data += f" {k}={v}"
        if update_data:
            sql = f"UPDATE {cls.table_name} SET {update_data} WHERE id={player_id}"

            sta = await ProxyUser.exec_sql(sql)
        return sta, "更新成功"

    @classmethod
    async def update_many_proxy_user(cls, player_ids: list, up_data: dict):
        """
        更新proxy_user
        """
        sta = False
        update_data = ""
        valid_fields = {"status", "proxy_level", "is_deleted", "vip_level", "vip_expire_time", "is_channel", "channel_proxy_id"}
        for k, v in up_data.items():
            if k in valid_fields and v is not None:
                if update_data:
                    update_data += ", "
                update_data += f" {k}={v}"
        if update_data:
            sql = f"UPDATE {cls.table_name} SET {update_data} WHERE id IN ({','.join(str(id) for id in player_ids)})"

            sta = await ProxyUser.exec_sql(sql)
        return sta, "更新成功"

    @classmethod
    async def set_channel(cls, channel_id: int, enable: int):
        user = await cls.get_proxy_user_filter(player_id=channel_id)
        if not user or user[0].get("proxy_level") != 1 or user[0].get("is_deleted") == 1:
            return False, "仅支持设置一级代理为渠道"
        await ProxyUser.exec_sql(f"UPDATE {cls.table_name} SET is_channel={1 if enable else 0} WHERE id={channel_id}")
        # if enable:
        #     sql = f"""
        #     UPDATE proxy_user a
        #     JOIN proxy_user l1 ON a.level1_proxy_id = l1.id
        #     SET a.channel_proxy_id = {channel_id}
        #     WHERE l1.level1_proxy_id = {channel_id} AND a.is_deleted=0
        #     """
        #     await ProxyUser.exec_sql(sql)
        # else:
        #     sql = f"UPDATE proxy_user SET channel_proxy_id=0 WHERE channel_proxy_id={channel_id}"
        #     await ProxyUser.exec_sql(sql)
        return True, "成功"

