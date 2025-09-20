"""
聊天文本
"""
from nsanic.orm.rc_model import RCModel
from lucky_game.model_db.main import ConfQuickChat
from lucky_game.const import QuickChatType


class ConfQuickChatRC(RCModel):
    expired_mode = 1
    expired_sec = 2 * 86400

    db_model = ConfQuickChat
    cache_key = "conf_quick_chat"

    @classmethod
    async def cache_by_chat_type(cls, chat_type=QuickChatType.HU_DONG.val):
        async def from_db():
            filter_condition = {"chat_type": chat_type, "status": 1}
            db_info = await cls.db_model.filter(**filter_condition)
            data_list = []
            if db_info:
                for one_model in db_info:
                    data = {
                        'chat_id': one_model.chat_id,
                        'chat_name': one_model.chat_name,
                        'chat_type': one_model.chat_type,
                        'prop_type': one_model.prop_type,
                        'pay_type': one_model.pay_type,  # 支付方式
                        'price': one_model.price,  # 和leisure_rate只能同时配置一个，两者为0则免费
                        'leisure_rate': one_model.leisure_rate,  # 休闲场底分 * leisure_rate = 价格，和price只能同时配置一个，涉及到底分则货币一定是灵石
                        'cool_down': one_model.cool_down,  # 冷却时间（秒）
                        'img_url': one_model.img_url,
                        'level': one_model.level,
                        'free_act_type': one_model.free_act_type,  # 可免费使用的活动类型
                    }
                    data_list.append(data)
                await cls.conf.rds.set_hash(cls.cache_key, chat_type, data_list)
            return data_list

        tb_name = cls.db_model.sheet_name()
        info = await cls.conf.rds.get_hash(cls.cache_key, chat_type, jsparse=True)
        if info:
            return info

        p_info = await cls.conf.rds.locked(tb_name, from_db)
        return p_info
