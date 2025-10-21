# coding=utf-8
from nsanic.base_conf import BaseConf
from c_services.base.rmq_client import Rmq
from common.public.enum_const import StaCode, ServiceEnum, DbKey, CacheKey, Channel
from common.public.conf import CONF_DB, CONF_RDS, CONF_AMQP, DEBUG_MODE, RUN_FAST, SERVER_SECRET_KEY, \
    C_SERVICE_SECRET_KEY


class ConfSrv(BaseConf):
    SERVER_ENUM = ServiceEnum.WS_HALL
    SERVER_NAME = 'lucky_ws'
    SERVER_ID = 'W0001'
    RUN_PORT = 8885
    HOST = "0.0.0.0"
    DEBUG_MODE = DEBUG_MODE
    ACCESS_LOG = False
    RUN_FAST = RUN_FAST

    WS_ONLINE_INFO = CacheKey.WS_ONLINE_INFO
    CHANNEL_SYSTEM = Channel.CHANNEL_SYSTEM_MSG
    VER_CODE = None

    SECRET_KEY = C_SERVICE_SECRET_KEY  # 子游戏密钥（消息验证）
    SERVER_SECRET_KEY = SERVER_SECRET_KEY  # 服务器密钥（加密使用）
    STA_CODE = StaCode

    CONF_DB = CONF_DB
    CONF_RDS = CONF_RDS
    CONF_AMQP = CONF_AMQP

    rmq: Rmq = None

    @classmethod
    def set_conf(cls):
        super().set_conf()
        if cls.CONF_AMQP:
            cls.rmq = Rmq.init(cls.CONF_AMQP['default'], logs=cls.log)
            cls.rmq.init_pool()

    @classmethod
    def log_conf(cls):
        return

    @classmethod
    def db_conf(cls):
        """数据库配置"""
        models = cls.MODEL_LIST + cls.MODEL_EXTRA
        model_list = [f'lucky_game.model_db.{item}' for item in models]
        return cls.makeup_db_conf(model_list) if cls.CONF_DB else None

    @classmethod
    def makeup_db_conf(cls, model_list: list):
        return {
            'apps': {
                "lucky_game": {'models': model_list},
                f'lucky_game_log': {'models': ['lucky_game.model_db.log'], 'default_connection': DbKey.LOG}
            },
            'connections': cls.CONF_DB,
            'use_tz': False,
            'timezone': "UTC"
        }


conf_srv = ConfSrv()
