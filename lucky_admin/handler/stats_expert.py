"""
统计专家
"""
import asyncio
from datetime import datetime, timedelta

from nsanic.libs.component import LogMeta
from tortoise.transactions import in_transaction
from common.public.enum_const import UserSource, ServiceEnum, DbKey
from common.utils.kit_dt import KitDt
from lucky_game.config import conf_srv, ConfSrv
from lucky_game.const import OrderStatus, EventTracking, AdEventType, QUERY_EVENT
from lucky_game.model_db.log import RecordsGameUserLogin
from lucky_game.model_db.extra import RecordsUserEvent, RecordsGameGrade
from lucky_game.model_db.main import RecordsTradeOrder, StatsUserDataAnalysis, User, StatsRetentionAdsUser, \
    RecordsAdsEvent, StatsGameTimes, StatsRetentionOwnUser


class StatsExpert(LogMeta):
    conf: ConfSrv = conf_srv

    RETENTION_DAYS = [1, 3, 7, 14, 30]
    GAME_TYPES = (ServiceEnum.C_MONSTER_SEQUEL.val, ServiceEnum.C_MONSTER_MANY.val)  # 参与统计的游戏类型
    USER_FIELDS = ['new_user_count', 'active_user_count', 'pay_user_count', 'first_pay_times', 'pay_amount',
                   'avg_pay_amount']
    GAME_FIELDS = ['game_times', 'avg_game_times']

    @classmethod
    def safe_calculate(cls, numerator, denominator, round_digits=2, default=0.0):
        """
        终极安全计算方法
        - numerator: 分子
        - denominator: 分母（<=0 时直接返回默认值）
        - round_digits: 小数位数（默认2位）
        - default: 默认值（默认0.0）
        """
        # 先检查分母有效性
        if float(denominator) <= 0:  # 包含0和负数
            return default
        try:
            return round(float(numerator) / float(denominator), round_digits)
        except (TypeError, ValueError):
            return round(float(default), round_digits)

    @staticmethod
    def build_time_range(query_params, time_field, start_time, end_time):
        """根据时间字段名称调整查询参数"""
        query_params = query_params.copy()
        if start_time > 0 and end_time > 0:
            query_params[f'{time_field}__gte'] = start_time
            query_params[f'{time_field}__lte'] = end_time
        elif start_time > 0:
            query_params[f'{time_field}__gte'] = start_time
        elif end_time > 0:
            query_params[f'{time_field}__lte'] = end_time

        return query_params

    @classmethod
    async def stats_user_data_analysis(cls):
        """ 用户数据分析（优化版）"""
        start, end = KitDt.get_daily_timespan()

        # 1.并行获取基础数据
        new_user_query = User.filter(created__gte=start, created__lte=end).distinct().values_list('uid', flat=True)
        login_query = RecordsGameUserLogin.get_by_dict({"created__gte": start, "created__lte": end}, field=["uid"],
                                                       groups=["uid"])
        paid_order_query = RecordsTradeOrder.filter(trade_time__gte=start, trade_time__lte=end,
                                                    order_status=OrderStatus.PAID).all()
        previous_paid_query = RecordsTradeOrder.filter(order_status=OrderStatus.PAID,
                                                       trade_time__lte=start).distinct().values_list('uid', flat=True)

        new_records, login_records, paid_orders, previous_paid = await asyncio.gather(
            new_user_query,
            login_query,
            paid_order_query,
            previous_paid_query
        )

        # 2.处理用户数据
        new_user_count = len(new_records)
        active_user_count = len(login_records) if isinstance(login_records, list) else 0

        # 3.处理付费数据
        pay_user_ids = {order.uid for order in paid_orders}
        pay_user_count = len(pay_user_ids)
        pay_amount = sum(order.trade_amount for order in paid_orders)

        paid_users_set = set(previous_paid)
        first_pay_times = sum(1 for uid in pay_user_ids if uid not in paid_users_set)
        avg_pay_amount = cls.safe_calculate(pay_amount, pay_user_count)

        stats_res = {
            'new_user_count': new_user_count,
            'pay_user_count': pay_user_count,
            'active_user_count': active_user_count,
            'pay_amount': pay_amount,
            'first_pay_times': first_pay_times,
            'avg_pay_amount': avg_pay_amount
        }
        # 4. 单次写入
        await StatsUserDataAnalysis.update_or_create(time_node=start, defaults=stats_res)
        cls.log_info(f"{start} 用户数据分析（优化版）{stats_res}")

    @classmethod
    async def _get_active_user_by_date(cls, target_date):
        """
        获取特定日期的活跃用户ID列表（优化版）
        :param target_date: 查询的目标日期对象
        :return: 活跃用户的ID集合
        """
        start = int(datetime.combine(target_date, datetime.min.time()).timestamp())
        end = start + 86400  # 24小时秒数

        # 分页查询避免内存问题
        batch_size = 10000
        all_uids = set()
        while True:
            records = await RecordsGameUserLogin.get_by_dict({"created__gte": start, "created__lte": end},
                                                             field=["uid"], groups=["uid"], limit=batch_size,
                                                             offset=len(all_uids))
            if not records:
                break
            all_uids.update(r['uid'] for r in records)
        return all_uids

    @classmethod
    async def _filter_retention_user_by_ids(cls, target_date, user_ids):
        """
        根据日期和用户ID集查询目标日期内的登录记录（优化版）
        :param target_date: 查询的目标日期
        :param user_ids: 用户ID集合
        :return: 登录的用户ID集合
        """
        if not user_ids:  # 空集合直接返回
            return set()

        start = int(datetime.combine(target_date, datetime.min.time()).timestamp())
        end = start + 86400

        # 分批查询避免IN语句过长（每批1000个用户ID）
        batch_size = 1000
        user_id_list = list(user_ids)
        batches = [user_id_list[i:i + batch_size] for i in range(0, len(user_id_list), batch_size)]

        # 并行查询各批次
        results = await asyncio.gather(*[
            RecordsGameUserLogin.get_by_dict({"uid__in": b, "created__gte": start, "created__lte": end}, field=["uid"])
            for b in batches
        ])
        # 合并结果
        return {r['uid'] for batch in results for r in batch} if results else set()

    @classmethod
    async def stats_retention_user_own(cls):
        """
        留存统计（优化版）

        公式和数据解释：
        1. N日留存率 = N天前的留存用户 / N天前的初始用户
        2. 基础日期 = 一般是统计定时任务运行的前一天
        3. 老用户数 = 活跃用户数 - 新注册用户数
        4. N天前的留存用户 = 基础日期的老用户中在N天前也登录过的用户数
        5. N天前的初始用户 = 基础日期N天前的所有登录用户数
        """
        async with in_transaction(connection_name=DbKey.DEFAULT):
            start, end = KitDt.get_daily_timespan()
            base_date = datetime.fromtimestamp(start)

            # 1.并行获取基础数据
            new_users, active_users = await asyncio.gather(
                User.filter(created__gte=start, created__lte=end).distinct().values_list('uid', flat=True),
                cls._get_active_user_by_date(base_date)  # 使用分页查询版本
            )

            # 2.检查活跃用户
            main_record, _ = await StatsRetentionOwnUser.get_or_create(time_node=start)
            if not active_users:
                cls.log_info(f"{start} 留存统计（优化版）, 无活跃用户")
                return

            # 4.并行计算各留存指标
            old_users = {uid for uid in active_users if uid not in new_users}
            results = await asyncio.gather(*[
                cls._cal_single_retention(base_date - timedelta(days=day), old_users)
                for day in cls.RETENTION_DAYS
            ])

            # 5.更新表
            updates = {}
            for day, (count, rate) in zip(cls.RETENTION_DAYS, results):
                updates[f'day_{day}_count'] = count
                updates[f'day_{day}_retention'] = rate

            # 执行更新
            await StatsRetentionOwnUser.filter(id=main_record.id).update(**updates)
        cls.log_info(f"{start} 留存统计（优化版）, 新增用户数: {len(new_users)}, 活跃用户数: {len(active_users)}")

    @classmethod
    async def _cal_single_retention(cls, target_date, old_user_ids):
        """计算单个留存日的数据"""
        # 并行获取初始用户和留存用户
        initial_users, retained_users = await asyncio.gather(
            cls._get_active_user_by_date(target_date),
            cls._filter_retention_user_by_ids(target_date, old_user_ids)
        )

        # 计算留存指标
        r_count = len(retained_users & initial_users)
        r_rate = cls.safe_calculate(r_count, len(initial_users), round_digits=4)

        return r_count, r_rate

    @classmethod
    async def stats_retention_user_ads(cls, user_source: UserSource):
        """留存统计"""
        # 默认统计前一天的数据
        start_of_yesterday, end_of_yesterday = KitDt.get_daily_timespan()

        # 1.统计昨日新注册用户数
        new_user_ids = await RecordsAdsEvent.filter(
            created__gte=start_of_yesterday,
            created__lte=end_of_yesterday,
            event_type=AdEventType.AD_ACTIVE_REGISTER.val,
            user_source=user_source
        ).distinct().values_list('uid', flat=True)
        new_user_count = len(set(new_user_ids))

        # 获取用户登陆数，RecordsGameUserLogin表created在昨天
        login_records = await RecordsGameUserLogin.get_by_dict({
            "created__gte": start_of_yesterday,
            "created__lt": end_of_yesterday}, field=["uid"])
        login_ids = {r['uid'] for r in login_records}

        # 获取所有之前来自广告的注册用户（排除昨天注册的用户）
        from_juliang_ids = await RecordsAdsEvent.filter(
            created__lte=start_of_yesterday,  # 注册时间早于昨天
            event_type=AdEventType.AD_ACTIVE_REGISTER.val,
            user_source=user_source
        ).distinct().values_list('uid', flat=True)

        # 2.统计昨日登录用户中来自广告的用户数
        retained_user_ids = set(login_ids).intersection(set(from_juliang_ids))
        retained_user_count = len(retained_user_ids)

        # 3.统计昨日付费用户数
        pay_user_ids = await RecordsAdsEvent.filter(
            created__gte=start_of_yesterday,
            created__lte=end_of_yesterday,
            event_type=AdEventType.AD_ACTIVE_PAY.val,
            user_source=user_source
        ).distinct().values_list('uid', flat=True)
        pay_user_count = len(set(pay_user_ids))

        # 创建或更新留存统计记录
        await StatsRetentionAdsUser.update_or_create(time_node=start_of_yesterday,
                                                     defaults={
                                                         'new_user_count': new_user_count,
                                                         'old_user_count': retained_user_count,
                                                         'pay_user_count': pay_user_count,
                                                         'user_source': UserSource.JuLiang.val
                                                     }
                                                     )

    @classmethod
    async def get_user_event_records(cls, start_time, end_time, uid=None, limit=0, offset=0):
        """
        获取用户事件记录
        事件/游戏/付费
        返回：当前页记录, 总记录数, 错误信息
        """
        if uid:
            query_params = {'uid': uid}
            # 根据不同的表动态构建时间查询参数
            order_query_params = cls.build_time_range(query_params, "finish_time", start_time, end_time)
            order_query_params['order_status'] = OrderStatus.PAID.val
            event_query_params = cls.build_time_range(query_params, "event_time", start_time, end_time)

            game_grade_query_params = cls.build_time_range(query_params, "created", start_time, end_time)

            # 并行查询（包含游戏类型）
            order_records, event_records, game_records = await asyncio.gather(
                RecordsTradeOrder.get_by_dict(order_query_params, limit=limit, offset=offset),
                RecordsUserEvent.get_by_dict(event_query_params, limit=limit, offset=offset),
                RecordsGameGrade.get_by_dict(
                    {**game_grade_query_params, "cs_type__in": cls.GAME_TYPES}, limit=limit, offset=offset)
            )

            # 获取总数（区分游戏类型）
            order_count, event_count, game_counts = await asyncio.gather(
                RecordsTradeOrder.get_count(order_query_params),
                RecordsUserEvent.get_count(event_query_params),
                RecordsGameGrade.get_count({**game_grade_query_params, "cs_type__in": cls.GAME_TYPES})
            )

            # 计算总记录数（所有类型的记录条数之和）
            total = order_count + event_count + game_counts
        else:
            table_a = RecordsUserEvent.sheet_name()
            order_records_sql = """
                SELECT 
                    b.* 
                FROM 
                    {0} b 
                INNER JOIN 
                    {1} a
                ON 
                    b.uid=a.uid 
                WHERE 
                     b.finish_time BETWEEN {2} AND {3} AND b.order_status={4} AND a.event_tracking={5}
                ORDER BY
                    created DESC
                LIMIT {6}
                OFFSET {7}
            """.format(
                RecordsTradeOrder.sheet_name(),
                table_a,
                start_time,
                end_time,
                OrderStatus.PAID.val,
                EventTracking.AFTER_REGISTER.val,
                limit,
                offset
            )

            order_records = await RecordsTradeOrder.exec_query(order_records_sql)

            event_records_sql = """
                    SELECT 
                        b.* 
                    FROM 
                        {0} b 
                    INNER JOIN 
                        {1} a
                    ON 
                        b.uid=a.uid 
                    WHERE 
                         b.event_time BETWEEN {2} AND {3} AND a.event_tracking={4}
                    ORDER BY
                        created DESC
                    LIMIT {5}
                    OFFSET {6}
                """.format(
                RecordsUserEvent.sheet_name(),
                table_a,
                start_time,
                end_time,
                EventTracking.AFTER_REGISTER.val,
                limit,
                offset
            )

            event_records = await RecordsUserEvent.exec_query(event_records_sql)

            game_records_sql = """
                    SELECT 
                        b.* 
                    FROM 
                        {0} b 
                    INNER JOIN 
                        {1} a
                    ON 
                        b.uid=a.uid 
                    WHERE 
                         b.created BETWEEN {2} AND {3} AND b.cs_type in {4} AND a.event_tracking={5}
                    ORDER BY
                        created DESC
                    LIMIT {6}
                    OFFSET {7}
                """.format(
                RecordsGameGrade.sheet_name(),
                table_a,
                start_time,
                end_time,
                cls.GAME_TYPES,
                EventTracking.AFTER_REGISTER.val,
                limit,
                offset
            )

            game_records = await RecordsGameGrade.exec_query(game_records_sql)

            order_count_sql = """
                            SELECT 
                                COUNT(*) AS count 
                            FROM 
                                {0} b 
                            INNER JOIN 
                                {1} a
                            ON 
                                b.uid=a.uid 
                            WHERE 
                                 b.finish_time BETWEEN {2} AND {3} AND b.order_status={4} AND a.event_tracking={5}
                            LIMIT 1
                        """.format(
                RecordsTradeOrder.sheet_name(),
                table_a,
                start_time,
                end_time,
                OrderStatus.PAID.val,
                EventTracking.AFTER_REGISTER.val,
            )

            order_count = await RecordsTradeOrder.exec_query(order_count_sql)

            event_count_sql = """
                    SELECT 
                        COUNT(*) AS count 
                    FROM 
                        {0} b 
                    INNER JOIN 
                        {1} a
                    ON 
                        b.uid=a.uid 
                    WHERE 
                         b.event_time BETWEEN {2} AND {3} AND a.event_tracking={4}
                    LIMIT 1
                """.format(
                RecordsUserEvent.sheet_name(),
                table_a,
                start_time,
                end_time,
                EventTracking.AFTER_REGISTER.val,
            )

            event_count = await RecordsUserEvent.exec_query(event_count_sql)

            game_count_sql = """
                                SELECT 
                                    COUNT(*) AS count 
                                FROM 
                                    {0} b 
                                INNER JOIN 
                                    {1} a
                                ON 
                                    b.uid=a.uid 
                                WHERE 
                                     b.created BETWEEN {2} AND {3} AND b.cs_type in {4} AND a.event_tracking={5}
                                LIMIT 1
                            """.format(
                RecordsGameGrade.sheet_name(),
                table_a,
                start_time,
                end_time,
                cls.GAME_TYPES,
                EventTracking.AFTER_REGISTER.val,
            )

            game_count = await RecordsGameGrade.exec_query(game_count_sql)

            total = 0
            if order_count:
                total += order_count[0].get("count")

            if event_count:
                total += event_count[0].get("count")

            if game_count:
                total += game_count[0].get("count")

        combined_records = []
        for record in event_records or []:
            combined_records.append({
                'event_time': record.get('event_time'),
                'uid': record.get('uid'),
                'event_tracking': record.get('event_tracking'),
                'event_desc': record.get('event_desc')
            })
        # 处理游戏记录（区分类型）
        for record in game_records or []:
            combined_records.append({
                'event_time': record.get('created'),
                'uid': record.get('uid'),
                'event_tracking': EventTracking.AFTER_GAME.val,
                'cs_type': record.get("cs_type"),  # 新增游戏类型字段
                'score': record.get('score'),
                'rank_score': record.get('rank_score'),
                'event_desc': EventTracking.AFTER_GAME.phrase
            })

        for record in order_records or []:
            combined_records.append({
                'event_time': record.get('finish_time'),
                'uid': record.get('uid'),
                'event_tracking': EventTracking.AFTER_PAY.val,
                'trade_item': record.get('trade_item'),
                'trade_amount': record.get('trade_amount'),
                'event_desc': EventTracking.AFTER_PAY.phrase
            })

        combined_records.sort(key=lambda x: x['event_time'], reverse=True)

        print("combined_records", combined_records)
        print("total", total)

        return combined_records, total, 'OK'

    @classmethod
    async def get_user_event_records_old(cls, start_time, end_time, uid=None, limit=0, offset=0):
        """
        获取用户事件记录
        事件/游戏/付费
        返回：当前页记录, 总记录数, 错误信息
        """
        try:
            if uid:
                query_params = {'uid': uid}
            else:
                register_records = await RecordsUserEvent.get_by_dict(
                    param={"event_tracking": EventTracking.AFTER_REGISTER.val},
                    field=["uid"], groups=["uid"])  # 查询注册记录
                tracking_uids = list(set(r["uid"] for r in register_records))
                query_params = {'uid__in': tracking_uids}  # 限制查询范围为追踪用户

            # 根据不同的表动态构建时间查询参数
            order_query_params = cls.build_time_range(query_params, "finish_time", start_time, end_time)
            order_query_params['order_status'] = OrderStatus.PAID.val
            event_query_params = cls.build_time_range(query_params, "event_time", start_time, end_time)

            game_grade_query_params = cls.build_time_range(query_params, "created", start_time, end_time)

            # 并行查询（包含游戏类型）
            order_records, event_records, game_records = await asyncio.gather(
                RecordsTradeOrder.get_by_dict(order_query_params, limit=limit, offset=offset),
                RecordsUserEvent.get_by_dict(event_query_params, limit=limit, offset=offset),
                RecordsGameGrade.get_by_dict(
                    {**game_grade_query_params, "cs_type__in": cls.GAME_TYPES}, limit=limit, offset=offset)
            )

            combined_records = []
            for record in event_records or []:
                combined_records.append({
                    'event_time': record.get('event_time'),
                    'uid': record.get('uid'),
                    'event_tracking': record.get('event_tracking'),
                    'event_desc': record.get('event_desc')
                })
            # 处理游戏记录（区分类型）
            for record in game_records or []:
                combined_records.append({
                    'event_time': record.get('created'),
                    'uid': record.get('uid'),
                    'event_tracking': EventTracking.AFTER_GAME.val,
                    'cs_type': record.get("cs_type"),  # 新增游戏类型字段
                    'score': record.get('score'),
                    'rank_score': record.get('rank_score'),
                    'event_desc': EventTracking.AFTER_GAME.phrase
                })

            for record in order_records or []:
                combined_records.append({
                    'event_time': record.get('finish_time'),
                    'uid': record.get('uid'),
                    'event_tracking': EventTracking.AFTER_PAY.val,
                    'trade_item': record.get('trade_item'),
                    'trade_amount': record.get('trade_amount'),
                    'event_desc': EventTracking.AFTER_PAY.phrase
                })

            # 获取总数（区分游戏类型）
            order_count, event_count, game_counts = await asyncio.gather(
                RecordsTradeOrder.get_count(order_query_params),
                RecordsUserEvent.get_count(event_query_params),
                RecordsGameGrade.get_count({**game_grade_query_params, "cs_type__in": cls.GAME_TYPES})
            )

            # 计算总记录数（所有类型的记录条数之和）
            total = order_count + event_count + game_counts

            combined_records.sort(key=lambda x: x['event_time'], reverse=True)
            return combined_records, total, 'OK'
        except Exception as e:
            return [], 0, e

    @classmethod
    async def get_user_event_stats(cls, start_time, end_time, uid=None):
        """
        获取用户事件统计
        数据库层面直接统计（优化版）
        事件完成率/平均次数/平均金额
        """
        # 构建基础条件
        if uid:
            base_param = {"uid": uid}
            # 1.查询总用户数
            event_records = await RecordsUserEvent.get_by_dict(
                param={**base_param, "event_time__gte": start_time, "event_time__lte": end_time},
                field=["uid"], groups=["uid"])

            total_users = len(event_records)

            # 2.各类统计查询（使用现有get_count方法）
            behavior_stats = {}
            if total_users > 0:
                for event in EventTracking:
                    if event in (EventTracking.AFTER_GAME, EventTracking.AFTER_PAY):
                        continue
                    count = await RecordsUserEvent.get_count(
                        param={**base_param,
                               "event_time__gte": start_time,
                               "event_time__lte": end_time,
                               "event_tracking": event.val}
                    )
                    behavior_stats[f"behavior_{event.val}"] = {
                        "rate": cls.safe_calculate(count * 100, total_users), "count": count}

            # 3.游戏统计（按类型区分）
            game_stats = {}
            for cs_type in cls.GAME_TYPES:
                # 游戏次数统计
                game_count = await RecordsGameGrade.get_count(
                    param={**base_param,
                           "created__gte": start_time,
                           "created__lte": end_time,
                           "cs_type": cs_type}
                )
                game_stats[f"avg_game_count_{cs_type}"] = cls.safe_calculate(game_count, total_users)

            # 4. 付费统计（金额统计需要单独处理）
            pay_records = await RecordsTradeOrder.get_by_dict(
                param={**base_param,
                       "finish_time__gte": start_time,
                       "finish_time__lte": end_time,
                       "order_status": OrderStatus.PAID.val},
                field=["uid", "trade_amount"],
            )
        else:
            table_a = RecordsUserEvent.sheet_name()
            event_records_sql = """
                SELECT 
                    COUNT(DISTINCT b.uid) AS count
                FROM 
                    {0} b
                INNER JOIN 
                    {1} a
                ON 
                    b.uid=a.uid 
                WHERE 
                     a.event_tracking={2} AND b.event_time BETWEEN {3} AND {4} 
            """.format(
                table_a,
                table_a,
                EventTracking.AFTER_REGISTER.val,
                start_time,
                end_time,
            )

            event_records = await RecordsUserEvent.exec_query(event_records_sql)
            total_users = 0
            if event_records:
                total_users = event_records[0].get("count")

            # 2.各类统计查询（使用现有get_count方法）
            behavior_stats = {}
            if total_users > 0:
                event_count_sql = """
                    SELECT 
                        b.event_tracking AS event, COUNT(*) AS count 
                    FROM 
                        {0} b 
                    WHERE 
                         b.event_time BETWEEN {2} AND {3} AND b.event_tracking IN {4}
                    GROUP BY b.event_tracking
                """.format(
                    table_a,
                    table_a,
                    start_time,
                    end_time,
                    QUERY_EVENT,
                )
                event_count_list = await RecordsUserEvent.exec_query(event_count_sql)
                for ec in event_count_list:
                    e = ec.get("event")
                    count = ec.get("count")
                    behavior_stats[f"behavior_{e}"] = {
                        "rate": cls.safe_calculate(count * 100, total_users), "count": count}

                # 补充未查出来的事件
                for e in QUERY_EVENT:
                    key = f"behavior_{e}"
                    if not behavior_stats.get(key):
                        behavior_stats[key] = {
                            "rate": cls.safe_calculate(0, total_users), "count": 0}

            # 3.游戏统计（按类型区分）
            game_count_sql = """
                SELECT 
                    b.cs_type, COUNT(*) AS count
                FROM 
                    {0} b 
                INNER JOIN 
                    {1} a
                ON 
                    b.uid=a.uid 
                WHERE 
                     b.created BETWEEN {2} AND {3} AND b.cs_type IN {4} AND a.event_tracking={5}
                GROUP BY `cs_type`
                """.format(
                RecordsGameGrade.sheet_name(),
                table_a,
                start_time,
                end_time,
                cls.GAME_TYPES,
                EventTracking.AFTER_REGISTER.val,
            )
            game_count_list = await RecordsGameGrade.exec_query(game_count_sql)
            game_stats = {}
            for game_count in game_count_list or []:
                cs_type = game_count.get("cs_type")
                count = game_count.get("count")
                game_stats[f"avg_game_count_{cs_type}"] = cls.safe_calculate(count, total_users)

            # 4. 付费统计（金额统计需要单独处理）
            pay_records_sql = """
                SELECT 
                    b.* 
                FROM 
                    {0} b 
                INNER JOIN 
                    {1} a
                ON 
                    b.uid=a.uid 
                WHERE 
                     b.finish_time BETWEEN {2} AND {3} AND b.order_status={4} AND a.event_tracking={5}
            """.format(
                RecordsTradeOrder.sheet_name(),
                table_a,
                start_time,
                end_time,
                OrderStatus.PAID.val,
                EventTracking.AFTER_REGISTER.val,
            )
            pay_records = await RecordsTradeOrder.exec_query(pay_records_sql)

        pay_users = len({r['uid'] for r in pay_records})
        pay_count = len(pay_records)
        pay_amount = sum(r.get('trade_amount', 0) for r in pay_records)

        return {
                   "total_users": total_users,
                   "completion_rates": behavior_stats,
                   "game_stats": game_stats,
                   "avg_pay_count": cls.safe_calculate(pay_count, total_users),
                   "avg_pay_amount": cls.safe_calculate(pay_amount, pay_users)
               }, 'OK'

    @classmethod
    async def get_user_event_stats_old(cls, start_time, end_time, uid=None):
        """
        获取用户事件统计
        数据库层面直接统计（优化版）
        事件完成率/平均次数/平均金额
        """
        try:
            # 构建基础条件
            if uid:
                base_param = {"uid": uid}
            else:
                register_records = await RecordsUserEvent.get_by_dict(
                    param={"event_tracking": EventTracking.AFTER_REGISTER.val},
                    field=["uid"])
                tracking_uids = list(set(r["uid"] for r in register_records))
                base_param = {'uid__in': tracking_uids}

            # 1.查询总用户数
            event_records = await RecordsUserEvent.get_by_dict(
                param={**base_param, "event_time__gte": start_time, "event_time__lte": end_time},
                field=["uid"], groups=["uid"])

            total_users = len(event_records)

            # 2.各类统计查询（使用现有get_count方法）
            behavior_stats = {}
            if total_users > 0:
                for event in EventTracking:
                    if event in (EventTracking.AFTER_GAME, EventTracking.AFTER_PAY):
                        continue
                    count = await RecordsUserEvent.get_count(
                        param={**base_param,
                               "event_time__gte": start_time,
                               "event_time__lte": end_time,
                               "event_tracking": event.val}
                    )
                    behavior_stats[f"behavior_{event.val}"] = {
                        "rate": cls.safe_calculate(count * 100, total_users), "count": count}

            # 3.游戏统计（按类型区分）
            game_stats = {}
            for cs_type in cls.GAME_TYPES:
                # 游戏次数统计
                game_count = await RecordsGameGrade.get_count(
                    param={**base_param,
                           "created__gte": start_time,
                           "created__lte": end_time,
                           "cs_type": cs_type}
                )
                game_stats[f"avg_game_count_{cs_type}"] = cls.safe_calculate(game_count, total_users)

            # 4. 付费统计（金额统计需要单独处理）
            pay_records = await RecordsTradeOrder.get_by_dict(
                param={**base_param,
                       "finish_time__gte": start_time,
                       "finish_time__lte": end_time,
                       "order_status": OrderStatus.PAID.val},
                field=["uid", "trade_amount"],
            )
            pay_users = len({r['uid'] for r in pay_records})
            pay_count = len(pay_records)
            pay_amount = sum(r.get('trade_amount', 0) for r in pay_records)

            return {
                       "total_users": total_users,
                       "completion_rates": behavior_stats,
                       "game_stats": game_stats,
                       "avg_pay_count": cls.safe_calculate(pay_count, total_users),
                       "avg_pay_amount": cls.safe_calculate(pay_amount, pay_users)
                   }, 'OK'
        except Exception as e:
            return {}, str(e)

    @classmethod
    async def stats_game_times(cls):
        """统计游戏总量（优化版）"""
        start, end = KitDt.get_daily_timespan()

        # 1.并行获取基础数据
        login_task = RecordsGameUserLogin.get_by_dict({"created__gte": start, "created__lte": end}, field=["uid"],
                                                      groups=["uid"])
        game_tasks = [
            RecordsGameGrade.get_by_dict({"created__gte": start, "created__lte": end, "cs_type": cs_type},
                                         field=["uid"])
            for cs_type in cls.GAME_TYPES
        ]
        login_records, *game_records_list = await asyncio.gather(login_task, *game_tasks)

        # 2.计算活跃用户（login_count已经是去重后的数值）
        active_user_count = len(login_records) if isinstance(login_records, list) else 0

        # 3.无活跃用户时直接返回
        if not active_user_count:
            await asyncio.gather(*[
                StatsGameTimes.update_or_create(time_node=start, cs_type=cs_type,
                                                defaults={"game_times": 0, "avg_game_times": 0})
                for cs_type in cls.GAME_TYPES
            ])
            cls.log_info(f"{start} 统计游戏总量（优化版）, 活跃用户 {active_user_count}")
            return

        # 4.计算各游戏类型数据
        updates = []
        for cs_type, records in zip(cls.GAME_TYPES, game_records_list):
            # 总游戏局数
            game_times = len(records) if isinstance(records, list) else 0

            # 平均局数 = 该游戏总次数 / 活跃用户数
            avg_game_times = cls.safe_calculate(game_times, active_user_count)

            updates.append({
                "time_node": start,
                "cs_type": cs_type,
                "game_times": game_times,
                "avg_game_times": avg_game_times  # 使用活跃用户数作为基数
            })

        # 5. 批量更新
        await asyncio.gather(*[
            StatsGameTimes.update_or_create(time_node=start, cs_type=u.get("cs_type"), defaults=u)
            for u in updates
        ])
        cls.log_info(f"{start} 统计游戏总量（优化版）, {updates}")

    @classmethod
    def cal_and_process_ring_ratio(cls, current_data, previous_data):
        """
        环比计算和数据处理（优化版）
        :param current_data: 当期数据
        :param previous_data: 往期数据
        """
        # 1.初始化结果结构
        result = {
            "total_data": {field: 0 for field in cls.USER_FIELDS},
            "ring_ratio": {},
            "daily_data": []
        }

        # 2.初始化游戏数据统计
        for cs_type in cls.GAME_TYPES:
            for field in cls.GAME_FIELDS:
                result["total_data"][f"{field}_{cs_type}"] = 0
        total_previous = result["total_data"].copy()

        # 3.处理当前数据
        cur_retentions = current_data.get("retentions") or []
        cur_games = current_data.get("game_datas") or []
        for time_node in set(item.get('time_node') for item in cur_retentions + cur_games):
            day_data = {"time_node": time_node}

            # 用户数据
            current_retention = next((r for r in cur_retentions if r.get('time_node') == time_node), {})
            for field in cls.USER_FIELDS:
                value = current_retention.get(field, 0)
                day_data[field] = value
                result["total_data"][field] += value

            # 游戏数据
            for cs_type in cls.GAME_TYPES:
                current_game = next(
                    (g for g in cur_games if g.get('time_node') == time_node and g.get('cs_type') == cs_type), {})
                for field in cls.GAME_FIELDS:
                    key = f"{field}_{cs_type}"
                    value = current_game.get(field, 0)
                    day_data[key] = value
                    result["total_data"][key] += value

            result["daily_data"].append(day_data)

        # 4.处理往期数据
        prev_retentions = previous_data.get("retentions") or []
        prev_games = previous_data.get("game_datas") or []
        for time_node in set(item.get('time_node') for item in prev_retentions + prev_games):
            # 用户数据
            prev_retention = next((r for r in prev_retentions if r.get('time_node') == time_node), {})
            for field in cls.USER_FIELDS:
                total_previous[field] += prev_retention.get(field, 0)

            # 游戏数据
            for cs_type in cls.GAME_TYPES:
                prev_game = next(
                    (g for g in prev_games if g.get('time_node') == time_node and g.get('cs_type') == cs_type), {})
                for field in cls.GAME_FIELDS:
                    key = f"{field}_{cs_type}"
                    total_previous[key] += prev_game.get(field, 0)

        # 5.计算环比（保持原有写法）
        for field in cls.USER_FIELDS:
            prev = total_previous[field]
            curr = result["total_data"][field]
            result["ring_ratio"][f"ring_{field}"] = cls.safe_calculate((curr - prev) * 100, prev)

        for cs_type in cls.GAME_TYPES:
            for field in cls.GAME_FIELDS:
                key = f"{field}_{cs_type}"
                prev = total_previous[key]
                curr = result["total_data"][key]
                result["ring_ratio"][f"ring_{key}"] = cls.safe_calculate((curr - prev) * 100, prev)

        return result
