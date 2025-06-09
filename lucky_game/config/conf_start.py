# coding=utf-8
import os.path

from nsanic.base_conf import BaseConf
from c_services.base.rmq_client import Rmq
from common.public.enum_const import StaCode, DbKey
from common.public.conf import CONF_DB, CONF_RDS, CONF_AMQP, DEBUG_MODE, RUN_FAST, WeChatConf, SERVER_SECRET_KEY, \
    C_SERVICE_SECRET_KEY
from lucky_game.handler.sensitive_words import SensitiveWords


class ConfSrv(BaseConf):
    SERVER_NAME = 'lucky_game'
    SERVER_ID = 'G0001'
    RUN_PORT = 8988
    HOST = '0.0.0.0'
    DEBUG_MODE = DEBUG_MODE
    ACCESS_LOG = False

    RUN_FAST = RUN_FAST
    VER_CODE = None

    ALLOW_ORIGIN = ['*']
    ALLOW_HEADER = ['Authorization', 'Content-Type']
    RESP_TYPE = 'JSON'

    SECRET_KEY = C_SERVICE_SECRET_KEY  # 子游戏密钥（消息验证）
    SERVER_SECRET_KEY = SERVER_SECRET_KEY  # 服务器密钥（加密使用）
    STA_CODE = StaCode

    CONF_DB = CONF_DB
    CONF_RDS = CONF_RDS

    CONF_AMQP = CONF_AMQP

    rmq: Rmq = None

    # 敏感词检测
    SW_FILE: str = os.path.join(os.getcwd(), SERVER_NAME, 'const', 'sensitive_words.txt')
    sw: SensitiveWords = None

    @classmethod
    def set_conf(cls):
        super().set_conf()
        if cls.CONF_AMQP:
            cls.rmq = Rmq.init(cls.CONF_AMQP['default'], logs=cls.log)
            cls.rmq.init_pool()
        if cls.SW_FILE:
            cls.sw = SensitiveWords()
            cls.sw.init_ac(sw_file=cls.SW_FILE)

    @classmethod
    def makeup_db_conf(cls, model_list: list):
        return {
            'apps': {
                cls.SERVER_NAME: {'models': model_list},
                f'{cls.SERVER_NAME}_log': {'models': [f'{cls.SERVER_NAME}.model_db.log'],
                                           'default_connection': DbKey.LOG}
            },
            'connections': cls.CONF_DB,
            'use_tz': cls.USE_TZ,
            'timezone': cls.TIME_ZONE
        }

    @classmethod
    def log_conf(cls):
        return
