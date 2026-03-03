from nsanic.orm.rc_model import RCModel
from lucky_game.config import conf_srv
from lucky_game.model_db.main import ConfServerAddr


class ServerAddrRC(RCModel):
    conf = conf_srv
    db_model = ConfServerAddr
    tb_name = db_model.sheet_name()

    @classmethod
    async def cache_all(cls):
        async def from_db():
            info = await cls.db_model.get_by_dict(field=["addr", "path", "status"])
            if info:
                await cls.conf.rds.set_item(f'{key_name}', info)
                return info
            return

        key_name = cls.tb_name
        res = await cls.conf.rds.get_item(key_name, jsparse=True)
        if res:
            return res
        return await cls.conf.rds.locked(f"{key_name}_lock", fun=from_db)
