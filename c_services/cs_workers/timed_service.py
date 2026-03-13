import asyncio
import time
from datetime import datetime, timedelta
from nsanic.libs import tool_dt
from tortoise.transactions import in_transaction
from c_services.base.base_conf import BaseConf
from common.aliyun.dingtalk_service import DingTalkRobotService, DingTalkNotifier, DingTalkConfig
from common.model_rc.tournament_cycle import TournamentCycleRC
from common.public.conf import LIVE_SERVER, CertificationConf, DINGTALK_STATISTICS_WEBHOOK, ENV
from common.public.enum_const import ServiceEnum, DbKey, UserSource
from common.utils.utils import UtilsTool
from lucky_admin.const import BackTaskSta
from lucky_game.logic.tournament import TournamentLogic
from lucky_game.model_db.main import RecordsAdminTimedTask
from lucky_admin.handler.stats_expert import StatsExpert
from lucky_game.model_rc.base_records_game import BaseRecordsGameRC
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.model_rc.conf_competition import ConfCompetitionRC
from lucky_game.model_rc.logout_user import LogoutUserRC
from lucky_game.model_rc.order import OrderRC
from lucky_game.model_rc.records_game_room import RecordsGameRoomRC
from lucky_game.script.timed_task import BaseTimed
from lucky_proxy.logic.proxy_settlement import ProxysJobExecutor
from lucky_proxy.logic.proxy_user import ProxyUserLogic
from nsanic.libs.mult_log import NLogger



class TimedService:
    """ 定时任务服务 """
    conf: BaseConf

    def __init__(self, conf, main_service):
        TimedService.conf = conf
        self.__main_service = main_service
        self.__scheduler = None

    def log_info(self, *data):
        self.__main_service.log_info("定时任务：", *data)

    @property
    def scheduler(self):
        return self.__scheduler

    async def add_appointed_time_job(self, func, args=None, kwargs=None, jobstore='default'):
        """
        注意：
            args的第一个参数必须为uid
            kwargs中必须有cmd和start_time
        """

        async def inner_func():
            if asyncio.iscoroutinefunction(func):
                await func(*args)
            else:
                func(*args)
            h_key = self.__main_service.task_h_key(uid, start_time)
            await self.conf.rds.drop_hash(self.__main_service.TASK_DATE_KEY, h_key)
            await RecordsAdminTimedTask.update_by_pk(job_id, {"status": BackTaskSta.FINISHED.val})  # 更新任务为已执行

        uid = args[0]
        cmd = kwargs["cmd"]
        start_time = kwargs["start_time"]
        name = kwargs["name"]
        run_date = datetime.fromtimestamp(start_time)

        params = args[1]
        old_job_id = params.pop("job_id", None)
        job = self.__scheduler.add_date_job(inner_func, run_date, jobstore=jobstore, id=old_job_id)
        job_id = job.id

        params["job_id"] = job_id
        if old_job_id == job_id:
            self.log_info('worker服务重启，旧后台任务不插入表！', job_id)
            return

        await self.__main_service.save_date_task(uid, start_time, params)
        sta = await RecordsAdminTimedTask.insert_one(job_id, cmd, name, start_time, args[1], BackTaskSta.PENDING.val)
        if sta:
            self.log_info('后台任务启动成功！', job_id)
            return job_id

    def __add_default_jobs(self):
        """ 默认定时任务写在此 """
        # 周一到周五凌晨2点半
        # self.__scheduler.add_cron_job(self.__refresh_ranking_list, day_of_week='mon-fri', hour=2, minute=30)

        # 1.从00:00点，30分钟刷新排行榜数据：00: 30, 01:00, 01:30...
        # self.__scheduler.add_cron_job(self.__order_do_tasks, hour='0-23', minute='0/30')
        # self.__scheduler.add_cron_job(self.__order_do_tasks, hour='*/1')  # 每小时
        # self.__scheduler.add_cron_job(self.__reset_ranking_score, minute='*/3')  # 每3分钟执行一次

        # self.__scheduler.add_cron_job(self.__stats_juliang_ads_data, minute='*/3')  # 每3分钟执行一次测试

        # 3.段位重置时，重置玩家排行主表相关信息
        # 从00:00点，40分钟刷新排行榜数据：00: 40, 01:20, 02:00...
        # start_date = self.interval_minute_execute_once_from_zero(40)
        # self.__scheduler.add_interval_job(self.__reset_ranked_score, minutes=40, start_date=start_date)
        # self.__scheduler.add_interval_job(self.__reset_ranked_score, seconds=5)

        # 4.刷新机器人排位分数分  2小时刷新一次
        # 0-23/2 表示从0点到23点的每一小时，每隔2小时执行一次任务。
        # self.__scheduler.add_cron_job(self.__refresh_robot_ranking_info, hour='0-23/2')
        # self.__scheduler.add_cron_job(self.__refresh_robot_ranking_info, hour='0-23', minute='0/30')  # 半小时刷一次
        # self.__scheduler.add_interval_job(self.__refresh_robot_ranking_info, seconds=5)

        # 5.数据统计任务，每天0点过后执行
        # self.__scheduler.add_cron_job(self.__stats_data_tasks, hour=0, minute=0)  # 每天执行一次
        # self.__scheduler.add_cron_job(self.__stats_data_tasks, minute='*/3')  # 每5分钟执行一次 测试

        # 每日一次任务
        self.__scheduler.add_cron_job(self.__every_day_tasks, hour=0, minute=0)
        # 每小时一次任务
        self.__scheduler.add_cron_job(self.__order_do_tasks, hour='*/1')
        # 测试任务
        # self.__scheduler.add_cron_job(self.__test_tasks, minute='*/1')


    async def __test_tasks(self):
        # 统计数据推送
        now_time = datetime.now()
        # self.__scheduler.add_date_job(self.send_ding_statistics, run_date=now_time)
        self.__scheduler.add_date_job(self.check_tournament_cycle, run_date=now_time + timedelta(minutes=2))



    async def __every_day_tasks(self):
        """ 每日一次任务 """
        now_time = datetime.now()
        self.log_info(f"每日一次任务开始 {now_time}")
        # 防沉迷过期时间检查
        self.__scheduler.add_date_job(self.check_certification_useful_time, run_date=now_time + timedelta(hours=9))
        # 赛季状态检查更新
        self.__scheduler.add_date_job(self.check_tournament_cycle, run_date=now_time + timedelta(hours=0))
        # 代理商状态检查
        self.__scheduler.add_date_job(self.check_proxy_vip, run_date=now_time + timedelta(hours=0))
        # 更新赛季状态到比赛配置
        self.__scheduler.add_date_job(self.update_tournament_cycle_to_competition, run_date=now_time + timedelta(minutes=10))
        # # 统计数据推送
        self.__scheduler.add_date_job(self.send_ding_statistics, run_date=now_time + timedelta(hours=9))
        # 处理已注销用户
        self.__scheduler.add_date_job(self.clean_logout_user, run_date=now_time + timedelta(hours=0))

   

    async def __stats_data_tasks(self):
        """ 数据统计任务 """
        now_time = datetime.now()
        self.log_info(f"数据统计任务开始 {now_time}")
        self.__scheduler.add_date_job(StatsExpert.stats_game_times, run_date=now_time + timedelta(minutes=5))
        self.__scheduler.add_date_job(StatsExpert.stats_user_data_analysis, run_date=now_time + timedelta(minutes=10))
        self.__scheduler.add_date_job(StatsExpert.stats_retention_user_own, run_date=now_time + timedelta(minutes=15))
        self.__scheduler.add_date_job(StatsExpert.stats_retention_user_ads, args=[UserSource.JuLiang],
                                      run_date=now_time + timedelta(minutes=20))
        self.__scheduler.add_date_job(StatsExpert.stats_retention_user_ads, args=[UserSource.DataNexus],
                                      run_date=now_time + timedelta(minutes=25))

    async def __order_do_tasks(self):
        """ 顺序执行任务 """
        now_time = datetime.now()
        # 删除历史战绩（7天外）
        self.__scheduler.add_date_job(self.__del_to_game_record_history, run_date=now_time)





    @classmethod
    async def scan_all_string_key_del(cls, pattern='user_ranking:*', count=100):
        """ 删除所有键 str """
        cursor = '0'
        keys_to_delete = []
        try:
            while cursor != 0:
                # 使用 SCAN 查找所有匹配的键
                cursor, keys = await cls.conf.rds.conn.scan(cursor=int(cursor), match=pattern, count=count)
                if keys:
                    keys_to_delete.extend(keys)

            if keys_to_delete:
                # 使用 Pipeline 批量删除
                async with cls.conf.rds.conn.pipeline() as pipe:
                    for key in keys_to_delete:
                        # await pipe.unlink(key)  # 非阻塞，异步删除。（后台删除）
                        # DEL 命令是同步的，会阻塞 Redis 服务器直到删除操作完成。如果要删除的是大对象或者大量的键，可能会导致Redis暂时无法响应其他请求。
                        pipe.delete(key)
                    # 执行管道中的所有命令
                    await pipe.execute()
                cls.log_info("del_string_all_key suc!")
        except Exception as e:
            cls.log_info("del_string_all_key fail", e)

    def check_certification_useful_time(self):
        """ 检查实名认证secret key是否过期 """
        useful_life = datetime.strptime(CertificationConf.USEFUL_TIME, "%Y-%m-%d %H:%M:%S")
        useful_time = int(useful_life.timestamp()) - 86400 * 7
        if int(datetime.now().timestamp()) > useful_time:
            ding_server = DingTalkNotifier().get_service()
            ding_server.send_link_message(
                title="防沉迷实名认证系统SecretKey过期",
                text=f"过期时间：{CertificationConf.USEFUL_TIME} 请及时登录网络游戏防沉迷实名认证系统进行更新，否则将无法使用实名认证功能。",
                message_url=CertificationConf.DOMAIN,
            )

    @classmethod
    async def __del_to_game_record_history(cls):
        """ 删除历史战绩（7天外） """
        await BaseRecordsGameRC.del_history_game_record()

    @classmethod
    async def check_tournament_cycle(self):
        """ 检查赛季周期是否过期 """
        cycle_id = await TournamentCycleRC.get_current_cycle_id()
        _, cycle_data = await TournamentCycleRC.get_cycle_info(cycle_id)
        if cycle_data:
            now = tool_dt.cur_time()
            end_time = datetime.strptime(cycle_data["cycle_end_date"] + " 23:59:59", "%Y-%m-%d %H:%M:%S")
            end_time_tamp = int(end_time.timestamp())
            if now > end_time_tamp:
                await TournamentLogic().cycle_settle(cycle_id, cycle_data["reward_id"])
                await TournamentLogic().up_cycle_status(cycle_id)

    @classmethod
    async def update_tournament_cycle_to_competition(self):
        cycle_id = await TournamentCycleRC.get_current_cycle_id()
        _, cycle_data = await TournamentCycleRC.get_cycle_info(cycle_id)
        if cycle_data and cycle_data["reward_id"] != 2:
            start_time = datetime.strptime(cycle_data["cycle_start_date"], "%Y-%m-%d")
            end_time = datetime.strptime(cycle_data["cycle_end_date"] + " 23:59:59", "%Y-%m-%d %H:%M:%S")
            end_time_tamp = int(end_time.timestamp())
            start_time_tamp = int(start_time.timestamp())
            await ConfCompetitionRC.update_competition_time(2, start_time_tamp, end_time_tamp, cycle_id)

    @classmethod
    def interval_minute_execute_once_from_zero(cls, minute=35):
        """ 从0点每个多少分钟执行一次 """
        now = datetime.now()
        start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if now > start_time:
            next_run_time = start_time + timedelta(minutes=minute)
            while next_run_time <= now:
                next_run_time += timedelta(minutes=minute)
        else:
            next_run_time = start_time
        return next_run_time

    def start(self):
        self.__scheduler = BaseTimed.new()
        self.__scheduler.start()
        self.__add_default_jobs()

    def close(self):
        self.__scheduler.close()

    @classmethod
    async def send_ding_statistics(cls):
        """ 每日统计房间订单数据发送至钉钉 """
        if ENV != "prod":
            return
        order_sum_data = await OrderRC.statistics_order_by_sum_amount()
        order_count_data = await OrderRC.statistics_order_by_count()
        group_data = await RecordsGameRoomRC.statistics_game_room_by_group_count()
        count_data = await RecordsGameRoomRC.statistics_game_room_by_count()
        ding_server = DingTalkNotifier().get_service()
        ding_server.config.webhook_url = DINGTALK_STATISTICS_WEBHOOK
        # ding_server.config.secret = DINGTALK_STATISTICS_SECRET
        now = tool_dt.cur_time()
        content = f"时间：{tool_dt.dt_str(now, fmt='%Y-%m-%d')}\n" \
                   f"订单数：{order_count_data}\n" \
                   f"订单金额：{order_sum_data}\n" \
                   f"房间总数：{count_data}\n" \
                   f"多个玩法房间数：{group_data}"
        ding_server.send_text_message(content)

    async def check_proxy_vip(self):
        # 检查代理vip是否过期
        today = int(datetime.now().replace(hour=0, minute=0, second=0).timestamp())
        data = await ProxyUserLogic.get_proxy_user_filter(status=1, vip_end_time=today)
        if data:
            u_ids = [d["id"] for d in data]
            await BaseUserRC.many_update_user(u_ids, discount=1)
            await ProxyUserLogic.update_many_proxy_user(u_ids, {"status": 0})


    @classmethod
    async def clean_logout_user(cls):
        """ 清理已注销用户 """
        now = tool_dt.cur_time()
        end_time = now - 15 * 86400
        sta, data = await LogoutUserRC.get_logout_user_by_filter(status=1, end_time=end_time)
        if sta and data:
            for i in data:
                await LogoutUserRC.delete_logout_user(i["uid"])
                NLogger.info(f"成功注销用户: {i['uid']}")
