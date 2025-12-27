"""
定时任务服务
"""
import asyncio
import datetime
# from common.public.conf import CONF_RDS
# from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.executors.asyncio import AsyncIOExecutor

from lucky_proxy.logic.proxy_settlement import ProxysJobExecutor


class Triggers:
    """定时触发器"""
    DATE = 'date'  # 特定时间只触发一次
    CRON = 'cron'  # 根据类Unix cron表达式执行任务，支持复杂的 周期性 任务。
    INTERVAL = 'interval'  # 固定时间间隔触发


class BaseTimed:
    """
    定时任务类
    不配置任何JobStore，APScheduler会默认使用MemoryJobStore。
    参考文档：https://mp.weixin.qq.com/s/75fnk5nlFSBQSYeY4cPQug
    """

    def __init__(self):
        self.__scheduler = AsyncIOScheduler(
            # jobstores={'persistent': RedisJobStore(**CONF_RDS["task_timed"]), },
            executors={'default': AsyncIOExecutor(), }  # 执行器：负责执行任务
        )

    def add_date_job(self, func, run_date, args=None, kwargs=None, jobstore='default', id=None):
        """
        run_date (datetime|str) – the date/time to run the job at
        timezone (datetime.tzinfo|str) – time zone for run_date if it doesn’t have one already
        example:
            s.add_job(my_job, 'date', run_date=date(2009, 11, 6), args=['text'])
            s.add_job(my_job, 'date', run_date=datetime(2019, 7, 6, 16, 30, 5), args=['text'])
        """
        return self.__scheduler.add_job(
            func,
            Triggers.DATE,
            args=args,
            kwargs=kwargs,
            jobstore=jobstore,
            run_date=run_date,
            id=id,
        )

    def add_interval_job(self, task_func, **kwargs):
        """
        weeks (int) –  间隔几周
        days (int) –  间隔几天
        hours (int) –  间隔几小时
        minutes (int) –  间隔几分钟
        seconds (int) –  间隔多少秒
        start_date (datetime|str) –  开始日期
        end_date (datetime|str) –  结束日期
        timezone (datetime.tzinfo|str) –  时区
        :return:
        """
        return self.__scheduler.add_job(task_func, Triggers.INTERVAL, **kwargs)

    def add_cron_job(self, task_func, **kwargs):
        """
        (int|str) 表示参数既可以是int类型，也可以是str类型
        (datetime | str) 表示参数既可以是datetime类型，也可以是str类型
        year (int|str) – 4-digit year -（表示四位数的年份，如2008年）
        month (int|str) – month (1-12) -（表示取值范围为1-12月）
        day (int|str) – day of the (1-31) -（表示取值范围为1-31日）
        week (int|str) – ISO week (1-53) -（格里历2006年12月31日可以写成2006年-W52-7（扩展形式）或2006W527（紧凑形式））
        day_of_week (int|str) – number or name of weekday (0-6 or mon,tue,wed,thu,fri,sat,sun) – （表示一周中的第几天，既可以用0-6表示也可以用其英语缩写表示）
        hour (int|str) – hour (0-23) – （表示取值范围为0-23时）
        minute (int|str) – minute (0-59) – （表示取值范围为0-59分）
        second (int|str) – second (0-59) – （表示取值范围为0-59秒）
        start_date (datetime|str) – earliest possible date/time to trigger on (inclusive) – （表示开始时间）
        end_date (datetime|str) – latest possible date/time to trigger on (inclusive) – （表示结束时间）
        timezone (datetime.tzinfo|str) – time zone to use for the date/time calculations (defaults to scheduler timezone) -（表示时区取值）
        *	所有	通配符。例：minutes=*即每分钟触发
        * / a	所有	每隔时长a执行一次。例：minutes=”* / 3″ 即每隔3分钟执行一次
        a – b	所有	a – b的范围内触发。例：minutes=“2-5”。即2到5分钟内每分钟执行一次
        a – b / c	所有	a – b范围内，每隔时长c执行一次。
        在 CronTrigger 中，minute 部分可以使用以下几种格式：
            单个值：例如 minute='0' 表示只在每小时的0分钟执行。
            范围：例如 minute='0-30' 表示从0分钟到30分钟之间的每一分钟都执行。
            列表：例如 minute='0,15,30,45' 表示在每小时的0、15、30和45分钟执行。
            步长：例如 minute='0/30' 表示从0分钟开始，每隔30分钟执行一次。

        xth y	日	第几个星期几触发。x为第几个，y为星期几
        last x	日	一个月中，最后一个星期的星期几触发
        last	日	一个月中的最后一天触发
        x, y, z	所有	组合表达式，可以组合确定值或上述表达式
        example:
            # 6-8,11-12月第三个周五 00:00, 01:00, 02:00, 03:00运行
            s.add_job(job_function, 'cron', month='6-8,11-12', day='3rd fri', hour='0-3')
            # 每周一到周五运行 直到2024-05-30 00:00:00
            s.add_job(job_function, 'cron', day_of_week='mon-fri', hour=5, minute=30, end_date='2024-05-30'
        """
        return self.__scheduler.add_job(task_func, Triggers.CRON, **kwargs)

    def __add_default_jobs(self):
         # 每月1号凌晨1点执行
        self.__scheduler.add_cron_job(self.every_month_proxy_summary, month="*", day=1, hour=1)
        #self.add_cron_job(self.every_month_proxy_summary,second="*/1")

    def rm_job(self, job_id):
        self.__scheduler.remove_job(job_id)

    def close(self):
        self.__scheduler.shutdown()  # 关闭scheduler

    async def start(self,*args):
        self.__scheduler.start()
        self.__add_default_jobs()
        await asyncio.Future()


    @classmethod
    def new(cls):
        return cls()

    async def every_month_proxy_summary(self):
        await ProxysJobExecutor.every_month_summary()
