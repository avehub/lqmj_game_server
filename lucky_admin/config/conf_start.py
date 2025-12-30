# coding=utf-8
import os.path
from nsanic.base_conf import BaseConf
from c_services.base.rmq_client import Rmq
from common.public.enum_const import StaCode, DbKey
from common.public.conf import CONF_DB, CONF_RDS, CONF_AMQP, DEBUG_MODE, SERVER_SECRET_KEY, C_SERVICE_SECRET_KEY, FileUploadConf
from lucky_game.handler.sensitive_words import SensitiveWords


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

    # 敏感词检测
    SW_FILE: str = os.path.join(os.getcwd(), 'lucky_game', 'const', 'sensitive_words.txt')
    sw: SensitiveWords = None

    # 文件上传配置
    FILE_UPLOAD = FileUploadConf
    # 添加上传目录路径
    RESOURCE_PATH = "resource"
    RESOURCE_CHAIN_PATH = "uploaded"
    UPLOAD_ROOT_PATH = os.path.join(os.getcwd(), RESOURCE_PATH, RESOURCE_CHAIN_PATH)
    STATIC_ROOT = os.path.join(os.getcwd(), RESOURCE_PATH)
    @classmethod
    def set_conf(cls):
        super().set_conf()
        if cls.CONF_AMQP:
            cls.rmq = Rmq.init(cls.CONF_AMQP['default'], logs=cls.log)
            cls.rmq.init_pool()
        if cls.SW_FILE:
            cls.sw = SensitiveWords()
            cls.sw.init_ac(sw_file=cls.SW_FILE)
        # 确保上传目录存在
        if cls.FILE_UPLOAD.LOCAL_STORAGE['enable']:
            os.makedirs(cls.UPLOAD_ROOT_PATH, exist_ok=True)

    @classmethod
    def log_conf(cls):
        return

    @classmethod
    def db_conf(cls):
        """数据库配置"""
        models = cls.MODEL_LIST + cls.MODEL_EXTRA
        model_list = [f'{cls.SERVER_NAME}.model_db.{item}' for item in models]
        db_conf = cls.makeup_db_conf(model_list) if cls.CONF_DB else None
        return db_conf

    @classmethod
    def makeup_db_conf(cls, model_list: list):
        model_list.append("lucky_proxy.model_db.main")
        model_list.append("lucky_game.model_db.main")
        return {
            'apps': {
                cls.SERVER_NAME: {'models': model_list},
            },
            'connections': cls.CONF_DB,
            'use_tz': cls.USE_TZ,
            'timezone': cls.TIME_ZONE
        }
