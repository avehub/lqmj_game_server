import asyncio
from datetime import datetime, timedelta
from nsanic.libs import tool_dt
from tortoise.transactions import in_transaction
from c_services.base.base_conf import BaseConf
from common.public.conf import LIVE_SERVER
from common.public.enum_const import ServiceEnum, DbKey, UserSource
from common.utils.utils import UtilsTool
from lucky_admin.const import BackTaskSta
from lucky_admin.model_db.main import RecordsAdminTimedTask
from lucky_game.const import SeasonStatus
from lucky_admin.handler.stats_expert import StatsExpert
from lucky_game.handler.douyin import DouYin
from lucky_game.model_db.main import RecordsUserRankingHistory
from lucky_game.model_rc.base_ads import BaseAds, JuLiangAdsRC
from lucky_game.model_rc.base_ranking import ConfSeasonRC, UserRankingRC
from lucky_game.model_rc.base_robot import BaseRobotRC
from lucky_game.model_rc.conf_json import ConfJsonRC
from lucky_game.model_rc.player_game_times import PlayerGameTimesRC
from lucky_game.script.timed_task import BaseTimed


class TimedService():
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
        self.__scheduler.add_cron_job(self.__order_do_tasks, hour='*/1')  # 每小时
        self.__scheduler.add_cron_job(self.__reset_ranking_score, minute='*/3')  # 每3分钟执行一次

        # self.__scheduler.add_cron_job(self.__stats_juliang_ads_data, minute='*/3')  # 每3分钟执行一次测试

        # 3.段位重置时，重置玩家排行主表相关信息
        # 从00:00点，40分钟刷新排行榜数据：00: 40, 01:20, 02:00...
        # start_date = self.interval_minute_execute_once_from_zero(40)
        # self.__scheduler.add_interval_job(self.__reset_ranked_score, minutes=40, start_date=start_date)
        # self.__scheduler.add_interval_job(self.__reset_ranked_score, seconds=5)

        # 4.刷新机器人排位分数分  2小时刷新一次
        # 0-23/2 表示从0点到23点的每一小时，每隔2小时执行一次任务。
        # self.__scheduler.add_cron_job(self.__refresh_robot_ranking_info, hour='0-23/2')
        self.__scheduler.add_cron_job(self.__refresh_robot_ranking_info, hour='0-23', minute='0/30')  # 半小时刷一次
        # self.__scheduler.add_interval_job(self.__refresh_robot_ranking_info, seconds=5)

        # 5.数据统计任务，每天0点过后执行
        self.__scheduler.add_cron_job(self.__stats_data_tasks, hour=0, minute=0)  # 每天执行一次
        # self.__scheduler.add_cron_job(self.__stats_data_tasks, minute='*/3')  # 每5分钟执行一次 测试

    async def __stats_data_tasks(self):
        """ 数据统计任务 """
        now_time = datetime.now()
        self.log_info(f"数据统计任务开始 {now_time}")
        self.__scheduler.add_date_job(StatsExpert.stats_game_times, run_date=now_time + timedelta(minutes=5))
        self.__scheduler.add_date_job(StatsExpert.stats_user_data_analysis, run_date=now_time + timedelta(minutes=10))
        self.__scheduler.add_date_job(StatsExpert.stats_retention_user_own, run_date=now_time + timedelta(minutes=15))
        self.__scheduler.add_date_job(StatsExpert.stats_retention_user_ads, args=[UserSource.JuLiang], run_date=now_time + timedelta(minutes=20))
        self.__scheduler.add_date_job(StatsExpert.stats_retention_user_ads, args=[UserSource.DataNexus], run_date=now_time + timedelta(minutes=25))

    async def __order_do_tasks(self):
        """ 顺序执行任务 """
        # 半小时刷新排行榜
        await self.__refresh_ranking_list()

        now_time = datetime.now()
        # 5分钟后执行历史写入数据
        self.__scheduler.add_date_job(self.__move_to_ranked_history, run_date=now_time + timedelta(minutes=5))

        # 10分钟后开始统计抖音用户广告数据
        if LIVE_SERVER:
            self.__scheduler.add_date_job(self.__stats_juliang_ads_data, run_date=now_time + timedelta(minutes=10))

        # 20分钟后执行邮件发奖
        self.__scheduler.add_date_job(self.__season_check_out, run_date=now_time + timedelta(minutes=20))

    @classmethod
    @UtilsTool.cal_time()
    async def __refresh_ranking_list(cls):
        """
        刷新排行榜
        严格从0点，半小时执行一次
        """
        # 1.休赛期排行榜不刷新了
        curr_season = await ConfSeasonRC.get_current_season()
        if curr_season.get("status") != SeasonStatus.ACTIVE_SEASON:
            cls.log_info(f"非开赛期，刷新排行榜失败: {curr_season.get('status')}")
            return
        cls.log_info("刷新世界、地区排行榜")
        season_id = curr_season.get("season_id")
        await UserRankingRC.refresh_ranking_list_group_by_region(season_id)  # 地区排行榜

    @classmethod
    @UtilsTool.cal_time()
    async def __reset_ranking_score(cls):
        """
        重置排位分
        ◆1601以上，全部扣除
        ◆851~1600部分，扣除75%
        ◆351~850部分，扣除50%
        ◆350以下，不扣除
        COALESCE返回参数列表中的第一个非NULL表达式。如果所有参数都是NULL，那么将返回NULL。
        重置分需要在写入历史数据后面
        """
        curr_season = await cls.__check_season_status(SeasonStatus.OFF_SEASON)
        if not curr_season:
            # cls.log_info("非休赛期，无法重置排位分数")
            return

        next_season_conf = await ConfSeasonRC.db_model.filter(status=SeasonStatus.NEXT_SEASON).first()
        if not next_season_conf:
            # cls.log_info("下个赛季还未配置，暂不重置玩家排位分数")
            return
        cur_time = tool_dt.cur_time()
        diff_time = next_season_conf.start_time - cur_time
        if diff_time >= 60 * 10:  # 默认10分钟
            cls.log_info(f"下个赛季开始时间还差{diff_time}s, 不重置玩家修为！")
            return

        curr_season_id = curr_season.get('season_id')
        data = await RecordsUserRankingHistory.filter(season_id=curr_season_id).first()
        # if not data or not data.season_achieved:
        if not data:
            cls.log_info(f"历史数据还未迁移，此时不能重置玩家修为分")
            return
        # 2.将user_ranking的分数按公式递减
        # 3.更新user_ranking的ranking_id
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                await UserRankingRC.ranking_reset_before_next_season(next_season_conf.season_id)
                await BaseRobotRC.ranking_reset_before_next_season()

            await BaseRobotRC.refresh_robot_cache()
            await cls.scan_all_string_key_del(f'{UserRankingRC.tb_name}:*')
            await ConfSeasonRC.update_season_info(
                curr_season_id, {'status': SeasonStatus.DAN_RESET}, curr_season)
            cls.log_info("重置玩家排位分数")
        except Exception as e:
            cls.log_info(f"事务执行失败，原因：{e}")

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

    @classmethod
    @UtilsTool.cal_time()
    async def __move_to_ranked_history(cls):
        """ 排位数据写入历史表 """
        curr_season = await cls.__check_season_status(SeasonStatus.OFF_SEASON)
        if not curr_season:
            cls.log_info("非休赛期，无法开始迁移到历史表")
            return
        curr_season_id = curr_season.get("season_id")
        data = await RecordsUserRankingHistory.filter(season_id=curr_season_id).first()
        if data:
            cls.log_info(f"S{curr_season_id}赛季历史数据已写入，不再重复迁移")
            return

        cls.log_info(f"S{curr_season_id}赛季主表迁移到历史表开始")
        # 事务：1.将user_ranking数据写入新表
        current_season_data = await UserRankingRC.query_all()

        curr_time = tool_dt.cur_time()
        # 准备新的记录列表
        new_records = []
        for user_ranking in current_season_data:
            # 创建新的记录对象
            user_ranking["season_id"] = curr_season_id
            user_ranking["created"] = curr_time
            user_ranking["uid"] = user_ranking.pop("user_id", 0)
            new_records.append(
                RecordsUserRankingHistory(
                    **user_ranking
                )
            )
        # 批量插入新的记录
        if new_records:
            sta = await RecordsUserRankingHistory.bulk_create(new_records, batch_size=1000)
            cls.log_info("迁移主表到历史表 结果: ", sta)

    @classmethod
    @UtilsTool.cal_time()
    async def __refresh_robot_ranking_info(cls):
        """ 刷新机器人排位分 """
        curr_season = await ConfSeasonRC.get_current_season()
        if not curr_season:
            return
        season_id = curr_season.get("season_id")
        all_data_list, _ = await UserRankingRC.get_ranking_list_group_by_region_by_player(season_id)
        all_data_list.sort(key=lambda d: d['cur_score'])
        if len(all_data_list) >= 2:
            # todo 最高/最低 排行玩家总场|胜场
            min_uid = all_data_list[0].get("uid")
            max_uid = all_data_list[-1].get("uid")
            _, min_uid_data = await PlayerGameTimesRC.get_game_time_info(min_uid, ServiceEnum.C_MONSTER)
            _, max_uid_data = await PlayerGameTimesRC.get_game_time_info(max_uid, ServiceEnum.C_MONSTER)
            min_game_count = min_uid_data.get("total_count") or 0
            max_game_count = max_uid_data.get("total_count") or 500
            min_game_win_count = min_uid_data.get("win_count") or 0
            max_game_win_game_count = max_uid_data.get("win_count") or 300
        else:
            min_game_count = 1
            max_game_count = 100
            min_game_win_count = 1
            max_game_win_game_count = 60

        if curr_season.get("status") == SeasonStatus.ACTIVE_SEASON:
            r_info = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_RANKING)
            init_score = r_info.get("initial_score") or 100
            defend_score = r_info.get("defend_score") or 850

            if len(all_data_list) >= 2:
                max_r_score = 0  # 平均值
                for data in all_data_list:
                    max_r_score += data.get("cur_score")
                max_r_score = max_r_score // len(all_data_list) or 200
                min_r_score = max(init_score, int(max_r_score * 0.7))  # 平均值最低的70%
            else:
                min_r_score = init_score
                max_r_score = init_score * 2
            await BaseRobotRC.refresh_ranking_info(
                min_r_score,
                max_r_score,
                defend_score,
                min_game_count,
                max_game_count,
                min_game_win_count,
                max_game_win_game_count,
            )
            cls.log_info(
                "刷新机器人排位分数！",
                curr_season.get("status"),
                min_r_score,
                max_r_score,
                min_game_count,
                max_game_count,
                min_game_win_count,
                max_game_win_game_count
            )
        else:
            await BaseRobotRC.refresh_game_count_info(
                min_game_count,
                max_game_count,
                min_game_win_count,
                max_game_win_game_count,
            )

            cls.log_info(
                "刷新机器人游戏局数",
                min_game_count,
                max_game_count,
                min_game_win_count,
                max_game_win_game_count
            )
        await BaseRobotRC.refresh_robot_cache()

    @classmethod
    async def __check_season_status(cls, status):
        curr_season = await ConfSeasonRC.get_current_season()
        if curr_season:
            if curr_season.get("status") != status:
                return None
            return curr_season
        return None

    async def __season_check_out(self):
        """ 赛季结算 邮件发奖 / 更新领奖状态 """
        curr_season = await self.__check_season_status(SeasonStatus.OFF_SEASON)
        if not curr_season:
            self.log_info("非休赛期，无法开始赛季结算")
            return

        curr_season_id = curr_season.get("season_id")
        data = await RecordsUserRankingHistory.filter(season_id=curr_season_id).first()
        if not data:
            self.log_info(f"S{curr_season_id}赛季历史数据还未迁移，无法颁奖")
            return
        if data.season_achieved:
            self.log_info(f"S{curr_season_id}赛季已经结算过，无法重复颁奖")
            return

        self.log_info(f"S{curr_season_id}赛季结算正式开始")
        # 颁奖、起草邮件、更新状态
        await self.__main_service.season_settle_mails(..., data=curr_season)
        self.log_info(f"赛季结算已完成")

    async def __stats_juliang_ads_data(self):
        """ 统计抖音小游戏巨量平台用户信息（每小时） """
        self.log_info(f"{tool_dt.cur_time()} 即将开始统计抖音小游戏巨量平台投流用户信息")
        errcode, access_token = await DouYin.douyin_get_access_token()
        if errcode:
            return

        res_code, res_data = await JuLiangAdsRC.juliang_get_ecpm(access_token)
        self.log_info(f"{tool_dt.cur_time()} 巨量平台投流用户信息查询结果：{res_code}, 数据列表：{res_data}")
        if res_data and res_code == 0:
            await BaseAds.stats_and_update_ad_revenue(res_data)

    def start(self):
        self.__scheduler = BaseTimed.new()
        self.__scheduler.start()
        self.__add_default_jobs()

    def close(self):
        self.__scheduler.close()