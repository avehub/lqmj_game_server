"""
用户登录记录表
"""
from datetime import datetime
from typing import Union

from tortoise import Tortoise
from tortoise.exceptions import OperationalError
from typing_extensions import List

from lucky_game.model_db.log import RecordsGameUserLogin
from lucky_game.model_rc.base_rc import BaseCommonRC


class RecordsAdEventRC(BaseCommonRC):
    db_alias = "log"
    now_year = datetime.now().year
    db_model = RecordsGameUserLogin
    tb_name = db_model.sheet_name()

    @classmethod
    def get_table_name(cls, year=None):
        """获取带年份后缀的表名
        Args:
            year: 年份，默认为当前年份
        Returns:
            str: 格式为 records_game_user_login_y{year} 的表名
        """
        year = year or datetime.now().year
        return f"records_game_user_login_y{year}"

    @classmethod
    async def get_queryset(cls, year=None, **filters):
        """获取查询集，自动处理分表逻辑
        Args:
            year: 指定年份的分表
            **filters: 查询过滤条件
        Returns:
            QuerySet: Tortoise ORM 查询集
        """
        year = year or datetime.now().year
        table_name = cls.get_table_name(year)
        db = Tortoise.get_connection(cls.db_alias)
        return cls.db_model.filter(**filters).using_db(db)

    @classmethod
    async def get_uid_login_last(cls, uid: Union[int, List[int]], platform: int = None, year: int = None):
        """根据用户ID获取最近登录记录
        Args:
            uid: 用户ID，支持单个ID或ID列表
            platform: 平台ID，可选
            year: 指定年份查询，可选
        Returns:
            tuple: (结果列表, 消息字符串)
        """
        sql = f"SELECT DISTINCT ON (uid) * FROM {cls.tb_name} ORDER BY uid, id DESC"
        print(sql)
        query = {}
        if uid is not None:
            query["uid__in" if isinstance(uid, list) else "uid"] = uid
        if platform is not None:
            query["platform"] = platform
        # if year is not None:
        #     query["year"] = year
        # else:
        #     query["year"] = cls.now_year
        # queryset = await cls.get_queryset(**query)
        db = Tortoise.get_connection(cls.db_alias)
        result = await db.filter(**query).order_by("uid", "-id").distinct().values()

        # result = await cls.db_model.exec_query(sql)
        msg = "暂无登录记录" if not result else "成功"
        return result, msg

    @classmethod
    async def get_uid_login_list(cls, uid: int, start_time: int = None, end_time: int = None, platform: int = None):
        """根据用户ID获取登录记录"""
        query = {}
        if uid is not None:
            query["uid"] = uid
        if start_time is not None:
            query["created__gte"] = start_time
        if end_time is not None:
            query["created__lte"] = end_time
        if platform is not None:
            query["platform"] = platform
        result = records = await cls.db_model.filter(**query, year=cls.now_year).using_db(cls.tb_name).order_by("-id").values()
        if not records:
            return result, "暂无登录记录"
        return result, "成功"