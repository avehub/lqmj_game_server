import os
from typing import Type

from nsanic.libs.rds_client import RdsClient
from nsanic.libs.mult_log import NLogger
from nsanic.libs.mk_random import RngMaker
from common.public.conf import CONF_DB, CONF_RDS, CONF_AMQP, DEBUG_MODE, USE_OBJ_POOL, C_SERVICE_SECRET_KEY
from common.public.enum_const import DbKey
from common.utils.meta_class import SingleTon
from .rmq_client import Rmq
from common.utils.locker import ResourceLocker


class BaseConf(metaclass=SingleTon):
    SERVER_NAME = 'MAIN'
    '''服务名称'''
    SERVER_ID = 'G0003'
    '''服务ID，建议4-6个字符 不同的服务之间该标识定义必须不一致'''
    RUN_WORKER = 1
    '''工作进程，该项配置可依据CPU核心数配置，最佳值为CPU核心数'''

    DEBUG_MODE = DEBUG_MODE
    # 日志基础路径
    LOG_PATH = os.path.join(os.getcwd(), 'logs')

    MODEL_LIST = ['main']
    '''数据库迁移基础表 更换配置请重写'''
    MODEL_EXTRA = ['extra']
    '''只用模型而不需要在当前项目迁移的表，请配置到该目录'''
    PROC_NAME = ''

    CHILD_GATE_CHANNEL = "PUBSUB_lucky_wsC_G0003"
    SECRET_KEY = C_SERVICE_SECRET_KEY  # 消息验证密钥

    USE_OBJ_POOL = USE_OBJ_POOL

    # 默认Redis缓存配置 更换配置请重写
    CONF_RDS = CONF_RDS

    # tortoise-orm 默认数据库配置 更换配置请重写
    CONF_DB = CONF_DB
    CONF_AMQP = CONF_AMQP

    rng: Type[RngMaker] = None
    rds: RdsClient = None
    log: NLogger = NLogger
    rmq: Rmq = None

    locker = ResourceLocker()

    @classmethod
    def set_conf(cls, server_name, server_id):
        cls.SERVER_NAME = server_name
        cls.SERVER_ID = f"{server_name}_{server_id}"
        RngMaker.init(cls.SERVER_ID)
        cls.rng = RngMaker

        cls.PROC_NAME = cls.SERVER_ID
        cls.log.init_conf(base_path=cls.LOG_PATH, folder=cls.SERVER_NAME.lower(), log_split=2, proc_split=1, keeps=4,
                          proc_tab=cls.PROC_NAME)
        if cls.CONF_RDS:
            cls.rds = RdsClient.init(cls.CONF_RDS['default'], logs=cls.log)
        if cls.CONF_AMQP:
            cls.rmq = Rmq.init(cls.CONF_AMQP['default'], logs=cls.log)

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

    @classmethod
    def db_conf(cls):
        """数据库配置"""
        models = cls.MODEL_LIST + cls.MODEL_EXTRA
        model_list = [f'lucky_game.model_db.{item}' for item in models]
        return cls.makeup_db_conf(model_list) if cls.CONF_DB else None


base_conf = BaseConf()
