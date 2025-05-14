"""
休闲场相关
"""
from nsanic.orm.rc_model import RCModel
from promising_game.model_db.main import ConfLeisure


class LeisureConfRC(RCModel):
    expired_mode = 1
    expired_sec = 2 * 86400

    db_model = ConfLeisure
    cache_key = "conf_leisure"

    @classmethod
    async def cache_all_by_cs_type(cls, cs_type=5):
        """ 根据子服务类型 """
        async def from_db():
            filter_condition = {"cs_type": cs_type, "status": 1}
            db_info = await cls.db_model.filter(**filter_condition).select_related("rule_conf")
            data_list = []
            if db_info:
                for one_model in db_info:
                    data = {
                        'min_take': one_model.min_take,
                        'base_score': one_model.base_score,
                        'price': one_model.price,
                        'max_take': one_model.max_take,
                        'status': one_model.status,
                        'desc': one_model.desc,
                        'level_desc': one_model.level_desc,
                        'cs_type': one_model.cs_type,
                        'play_type': one_model.play_type,
                        'id': one_model.id,
                        'level': one_model.level,
                        'gift_conf': one_model.gift_conf,
                        'ranking_addition': one_model.ranking_addition,
                        'threshold_multiple': one_model.threshold_multiple,
                    }
                    rule_conf = one_model.rule_conf.conf
                    data.update({"rule_conf": rule_conf})
                    data_list.append(data)
                await cls.conf.rds.set_hash(cls.cache_key, cs_type, data_list)
            return data_list

        tb_name = cls.db_model.sheet_name()
        info = await cls.conf.rds.get_hash(cls.cache_key, cs_type, jsparse=True)
        if info:
            return info
        p_info = await cls.conf.rds.locked(tb_name, from_db)
        return p_info
