# coding=utf-8
from nsanic.base_conf import BaseConf
from c_services.base.rmq_client import Rmq
from common.public.enum_const import StaCode, DbKey
from common.public.conf import CONF_DB, CONF_RDS, CONF_AMQP, DEBUG_MODE, SERVER_SECRET_KEY, C_SERVICE_SECRET_KEY


class ConfSrv(BaseConf):
    SERVER_NAME = 'lucky_admin'
    SERVER_ID = 'A0001'
    RUN_PORT = 8990
    HOST = '0.0.0.0'
    DEBUG_MODE = DEBUG_MODE
    ACCESS_LOG = True

    RUN_FAST = False  # RUN_FAST
    VER_CODE = None

    ALLOW_ORIGIN = ['*']
    ALLOW_HEADER = ['Authorization', 'Content-Type']
    RESP_TYPE = 'JSON'

    SECRET_KEY = C_SERVICE_SECRET_KEY  # 子游戏密钥（消息验证）
    SERVER_SECRET_KEY = SERVER_SECRET_KEY  # 消息验证密钥
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
        db_conf = cls.makeup_db_conf(model_list) if cls.CONF_DB else None
        return db_conf

    @classmethod
    def makeup_db_conf(cls, model_list: list):
        # server_name = "lucky_game"
        # return {
        #     'apps': {
        #         server_name: {'models': model_list},
        #         f'{server_name}_log': {'models': [f'{server_name}.model_db.log'], 'default_connection': DbKey.LOG}
        #     },
        #     'connections': cls.CONF_DB,
        #     'use_tz': False,
        #     'timezone': "UTC"
        # }
        server_name = "lucky_game"
        return {
            'apps': {
                server_name: {'models': model_list},
                f'{server_name}_log': {'models': [f'{server_name}.model_db.log'],
                                           'default_connection': DbKey.LOG}
            },
            'connections': cls.CONF_DB,
            'use_tz': cls.USE_TZ,
            'timezone': cls.TIME_ZONE
        }
        # server_name = "lucky_game"
        # return {
        #     'apps': {
        #         server_name: {'models': model_list},
        #         f'{server_name}_log': {'models': [f'{server_name}.model_db.log'],
        #                                    'default_connection': DbKey.LOG}
        #     },
        #     'connections': cls.CONF_DB,
        #     'use_tz': cls.USE_TZ,
        #     'timezone': cls.TIME_ZONE
        # }
