"""用户参与活动相关"""
import decimal
from datetime import datetime
import random
from typing import Type, Union, Tuple, List, Dict, Any
from tortoise.exceptions import OperationalError

from lucky_game.model_rc.base_rc import BaseCommonRC
from lucky_game.model_db.main import AppVersions


class AppVersionsRC(BaseCommonRC):
    db_model = AppVersions
    tb_name = db_model.sheet_name()
    APP_STATUS = 1  # 1:正常

    @classmethod
    async def add_app(cls, app_id: int, version_code: int, build_number: int, platform: int,
                        download_url: str, file_size: int, file_hash: str, min_support_version: int,
                        force_update_version: int, release_notes: str, release_time: int,  status: int = None,
                        created_by: int = None, updated_by: int = None):
        """新增订单"""
        try:
            data = {
                "app_id": app_id,
                "version_code": version_code,
                "build_number": build_number,
                "platform": platform,
                "status": status,
                "download_url": download_url,
                "file_size": file_size,
                "file_hash": file_hash,
                "min_support_version": min_support_version,
                "force_update_version": force_update_version,
                "release_notes": release_notes,
                "release_time": release_time,
                "created_by": created_by,
                "updated_by": updated_by,
            }
            cls.conf.log.info("插入订单表信息: ", data)
            new = await cls.db_model.add_one(data)
            if not new:
                return False, "添加失败"
        except OperationalError as e:
            return None, f"失败:{e}"
        return new, "成功"

    @classmethod
    async def get_app_info(cls, platform: int):
        """获取订单信息"""
        try:
            data = await cls.db_model.filter(status=cls.APP_STATUS, platform=platform).order_by("-id").first().values()
        except OperationalError as e:
            return None, f"查询失败:{e}"
        return data, "成功"

    @classmethod
    async def compare_versions(cls, install_version: str, new_version: str) -> int:
        """
        比较两个版本号的大小
        Args:
            install_version: 安装版本号 (e.g. "1.2.3")
            new_version: 服务器最新版本号 (e.g. "1.0.1")
        Returns:
            int:
                1 if install_version < new_version
                0 if install_version == new_version
        """
        def parse_version(ver: str) -> List[int]:
            return [int(num) for num in ver.split('.')]

        v1 = parse_version(install_version)
        v2 = parse_version(new_version)
        max_len = max(len(v1), len(v2))
        v1 = v1 + [0] * (max_len - len(v1))
        v2 = v2 + [0] * (max_len - len(v2))

        for i in range(max_len):
            if v1[i] < v2[i]:
                return 1
        return 0


