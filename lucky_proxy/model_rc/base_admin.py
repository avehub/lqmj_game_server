from nsanic.libs.tool import json_encode
from nsanic.orm.rc_model import RCModel

from lucky_proxy.model_db.main import Admins


class BaseAdminRC(RCModel):
    db_model = Admins
    tb_name = db_model.sheet_name()

    expired_mode = 1
    expired_sec = 172800  # 2 * 86400

    KEY_USERNAME = 'username'

    @classmethod
    async def update_info(cls, pk_val, info: dict, new_info: dict):
        """更新玩家信息，必须是玩家在线的情况下"""
        sta = await cls.db_model.update_by_pk(pk_val, new_info, old_data=info)
        if sta:
            info.update(new_info)
            if cls.expired_mode:
                key = f"{cls.tb_name}:{pk_val}"
                await cls.conf.rds.set_item(key, json_encode(info), ex_time=cls.expired_sec)
            else:
                await cls.conf.rds.set_hash(cls.tb_name, pk_val, json_encode(info))
            return info
        return

    @classmethod
    async def admin_info(cls, username):
        """获取管理员信息"""
        info = await cls.db_model.filter(username=username).first().values()
        print("info", info)
        if info:
            return True, info
        return False, "用户不存在"
