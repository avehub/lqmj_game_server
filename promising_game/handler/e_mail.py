import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Union
from nsanic.libs import tool


class EmailSMTP:
    SRV_MAP = {}

    def __init__(self, conf: dict, logs=None):
        self.__log = logs
        self.__conf = conf
        self.__smtp_srv = None
        self.__send_acc = self.__conf['account']
        self.__connect_init()

    def log_err(self, err: str):
        self.__log.error(err) if self.__log else print(err)

    def log_info(self, info: str):
        self.__log.info(info) if self.__log else print(info)

    @classmethod
    def init(cls, conf: dict, logs=None):
        key_arr = ['smtp_host', 'port', 'account', 'password']
        val_arr = [str(conf.get(key)) for key in key_arr if (key in conf)]
        if (len(val_arr) != 4) or ('None' in val_arr):
            raise Exception(f'无效的配置：{conf}')
        key = tool.calc_hash(''.join(val_arr), 'md5')
        if key in cls.SRV_MAP:
            return cls.SRV_MAP.get(key)
        smtp_obj = cls(conf, logs=logs)
        cls.SRV_MAP[key] = smtp_obj
        return smtp_obj

    def __connect_init(self):
        self.__smtp_srv = smtplib.SMTP(self.__conf['smtp_host'], self.__conf['port'])
        self.__smtp_srv.starttls()
        self.__smtp_srv.login(self.__conf['account'], self.__conf['password'])

    async def send_msg(self, target: Union[str, list[str], tuple[str]], context: str, title: str = None):
        mail_msg = MIMEMultipart()
        mail_msg['From'] = self.__send_acc
        mail_msg['Subject'] = title or '系统邮件(请勿回复)'
        if isinstance(target, (list, tuple)):
            target = ';'.join(target)
        mail_msg['To'] = target
        mail_msg.attach(MIMEText(context, 'plain'))
        loop = asyncio.get_running_loop()
        fut = loop.run_in_executor(None, self.__smtp_srv.sendmail, self.__send_acc, target, mail_msg.as_string())
        return await fut
