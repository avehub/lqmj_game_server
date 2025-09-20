"""
数据统计
"""
import asyncio
from sanic import Request
from datetime import datetime
from lucky_admin.base_api import AdminAuthApi
from lucky_admin.handler.stats_expert import StatsExpert
from lucky_game.model_rc.base_ads import BaseAds
from lucky_game.model_db.main import StatsUserDataAnalysis, StatsGameTimes, StatsRetentionOwnUser, RecordsAdsParams


class DataStats(AdminAuthApi):

    def verify_time_range(self, start_time, end_time, max_range_days=90):
        """验证并获取时间范围，自定义限制最大时间跨度"""
        start_time = int(start_time) if start_time else 0
        if start_time > 0:
            start_time = self.check_int(start_time, default=0, p_name='start_time 开始时间')

        end_time = int(end_time) if end_time else 0
        if end_time > 0:
            end_time = self.check_int(end_time, minval=start_time, p_name='end_time 截至时间')

        # 验证时间范围是否超过3个月
        if start_time > 0 and end_time > 0:
            max_allowed_end = start_time + max_range_days * 86400  # 90天的秒数
            if end_time > max_allowed_end:
                self.answer(code=self.sta_code.ERR_ARG, hint=f"时间范围不得超过{max_range_days}天")

        return start_time, end_time

    def verify_page(self, page, limit=10):
        """验证并获取分页配置"""
        page = self.check_int(page, require=True, minval=1, p_name='page 分页')
        offset = (page - 1) * limit

        return limit, offset

    async def check_promotion_id(self, req):
        advertiser_id = req.args.get("advertiser_id")
        project_id = req.args.get("project_id")
        promotion_id = req.args.get("promotion_id")
        promotion_id_list = []
        if advertiser_id:
            advertiser_id = self.check_str(advertiser_id, require=True, p_name="advertiser_id")
            values_list = await RecordsAdsParams.filter(advertiser_id=advertiser_id).values_list('promotion_id')
            promotion_id_list = []
            for values in values_list:
                promotion_id_list.append(values[0])
            promotion_id_list = list(set(promotion_id_list))
        elif project_id:
            project_id = self.check_str(project_id, require=True, p_name="project_id")
            values_list = await RecordsAdsParams.filter(project_id=project_id).values_list('promotion_id')
            promotion_id_list = []
            for values in values_list:
                promotion_id_list.append(values[0])
            promotion_id_list = list(set(promotion_id_list))
            promotion_id_list = list(set(promotion_id_list))
        elif promotion_id:
            promotion_id = self.check_str(promotion_id, require=True, p_name="promotion_id")
            promotion_id_list = [promotion_id]

        return promotion_id_list


class GetAdsEventStats(DataStats):
    """
    获取广告事件统计
    """

    async def get(self, req: Request, **_):
        user_source = self.check_int(req.args.get("user_source"), require=True, p_name="user_source 用户来源")

        start_time, end_time = req.args.get("start_time"), req.args.get("end_time")
        start_time, end_time = self.verify_time_range(start_time, end_time)
        limit, offset = self.verify_page(req.args.get("page"))

        promotion_id_list = await self.check_promotion_id(req)

        stats_info, count = await BaseAds.get_ads_event(
            promotion_id_list, user_source, start_time, end_time, limit=limit, offset=offset)
        data = {"ads_result": [], "count": 0}
        if stats_info:
            data = {"ads_result": stats_info, "count": count}

        return self.answer(self.sta_code.PASS, data=data)


class GetAdsUserStats(DataStats):
    """
    获取广告用户统计
    *目前只是抖音广告用户做统计
    """

    async def get(self, req: Request, **_):
        user_source = self.check_int(req.args.get("user_source"), require=True, p_name="user_source 用户来源")

        start_time, end_time = req.args.get("start_time"), req.args.get("end_time")
        start_time, end_time = self.verify_time_range(start_time, end_time)

        limit, offset = self.verify_page(req.args.get("page"))

        promotion_id_list = await self.check_promotion_id(req)

        try:
            # 并行获取数据和统计
            records_task = BaseAds.get_ads_user_records(
                start_time, end_time, user_source, promotion_id_list, limit, offset)

            stats_task = BaseAds.get_ads_user_stats(start_time, end_time, user_source, promotion_id_list)

            (records, total_count, e1), (stats, e2) = await asyncio.gather(records_task, stats_task)

            # 错误处理
            if e1 != "OK" or e2 != "OK":
                error_msg = f"获取广告用户统计错误：记录>>{e1}, 统计>>{e2}"
                return self.answer(self.sta_code.FAIL, hint=error_msg)

            # 格式化记录数据
            formatted_records = [
                {
                    "openid": r.openid,
                    "promotion_id": r.promotion_id,
                    "first_active_time": r.first_active_time,
                    "first_open_time": r.first_open_time,
                    "total_cost": r.total_cost,
                    "max_cost": r.max_cost,
                    "ad_open_count": r.ad_open_count,
                    "cost_open_count": r.cost_open_count,
                    "avg_ecpm": r.avg_ecpm,
                    "user_type": r.user_type,  # 用户类型（0新/1老）
                    "is_active": r.is_active,
                    "pay_amount": r.pay_amount,
                }
                for r in records
            ]
        except Exception as e:
            return self.answer(self.sta_code.FAIL, hint=f"系统错误: {str(e)}")

        # 构建响应
        return self.answer(self.sta_code.PASS, data={
            "all_records": formatted_records,
            "count": total_count,
            "all_stats": stats
        })


class GetAdsParams(AdminAuthApi):
    async def get(self, _a, **_b):
        data = await RecordsAdsParams.all().values()
        self.answer(data=data)


class GetUserRetentionStats(DataStats):
    """
    获取用户留存统计
    """

    async def get(self, req: Request, **kwargs):
        start_time, end_time = req.args.get("start_time"), req.args.get("end_time")
        start_time, end_time = self.verify_time_range(start_time, end_time)

        # 获取并验证留存天数参数
        retention_day = self.check_int(req.args.get("retention_day"), require=True, p_name="retention_day（留存天数）")
        (retention_day not in StatsExpert.RETENTION_DAYS) and self.answer(self.sta_code.ERR_ARG, hint="未曾参与统计的留存天数")

        # 安全获取字段名
        day_fields = {"count": f'day_{retention_day}_count', "rate": f'day_{retention_day}_retention'}

        # 关键修改点：查询统计日对应的初始日记录
        retentions = await StatsRetentionOwnUser.filter(
            time_node__gte=start_time,
            time_node__lte=end_time
        ).values('time_node', *day_fields.values())

        # 结果格式化
        results = [{
            "stat_date": r.get('time_node', 0) - retention_day * 86400,  # 展示日期（统计的目标日期，例如3日，那就是time_node前3日）
            # "time_node": r.get('time_node', 0),  # 统计日期
            "retention_day": retention_day,
            "retention_count": r.get(day_fields['count'], 0),
            "retention_rate": round(r.get(day_fields['rate'], 0.0) * 100, 2)  # 前端%即可
        } for r in retentions]

        return self.answer(self.sta_code.PASS, data=sorted(results, key=lambda x: x['stat_date']))


class GetFunnelAnalysis(DataStats):
    """
    获取漏斗分析结果
    """

    async def get(self, req: Request, **_):
        start_time, end_time = req.args.get("start_time"), req.args.get("end_time")
        start_time, end_time = self.verify_time_range(start_time, end_time)
        limit, offset = self.verify_page(req.args.get("page"))

        uid = self.check_int(req.args.get('uid'), default=0, p_name='uid')
        try:
            # 2. 并行获取数据和统计（使用优化后的方法）
            import time
            s = time.time()
            records, total_count, e1 = await StatsExpert.get_user_event_records(
                start_time, end_time, uid=uid, limit=limit, offset=offset)

            end_time = time.time()
            self.conf.info_log("漏斗分析1耗时：", end_time - s)
            stats, e2 = await StatsExpert.get_user_event_stats(start_time, end_time, uid=uid)

            self.conf.info_log("漏斗分析2耗时：", time.time() - end_time)
            # 3. 错误处理
            if e1 != "OK" or e2 != "OK":
                error_msg = f"获取漏斗分析结果错误：记录>>{e1}, 统计>>{e2}"
                return self.answer(self.sta_code.FAIL, hint=error_msg)
        except Exception as e:
            return self.answer(self.sta_code.FAIL, hint=f"系统错误: {str(e)}")

        # 4. 构建响应数据（不再需要内存分页）
        return self.answer(self.sta_code.PASS, data={
            "all_records": records,  # 已经是分页后的数据
            "count": total_count,  # 总记录数
            "all_stats": stats  # 统计结果
        })


class GetUserDataAnalysis(DataStats):
    """
    获取用户数据分析
    1.活跃
    2.新增
    3.付费金额/付费人数/首次付费人数/人均付费金额
    4.总游戏局数/平均游戏局数（分上下篇）
    5.以上数据都需要显示环比 =（今日活跃-昨日活跃）/昨日活跃
    """

    async def get(self, req: Request, **_):
        start_time, end_time = req.args.get("start_time"), req.args.get("end_time")
        start_time, end_time = self.verify_time_range(start_time, end_time)

        # 将时间戳转换为datetime对象
        start_time_dt = datetime.fromtimestamp(start_time)
        end_time_dt = datetime.fromtimestamp(end_time)

        # 计算前一个相同长度的时间段
        prev_start_time_dt = start_time_dt - (end_time_dt - start_time_dt)
        prev_end_time_dt = start_time_dt

        # 并行查询当前时间段和前一个时间段的数据
        current_data = await self.__query_data(start_time_dt, end_time_dt)

        if not current_data.get("retentions") and not current_data.get("game_datas"):
            return self.answer(self.sta_code.PASS, hint="没有任何数据")

        # 处理数据并计算环比
        previous_data = await self.__query_data(prev_start_time_dt, prev_end_time_dt)
        result = StatsExpert.cal_and_process_ring_ratio(current_data, previous_data)
        return self.answer(self.sta_code.PASS, data=result)

    @staticmethod
    async def __query_data(start_time: datetime, end_time: datetime):
        """
        查询指定时间段内的所有相关统计数据
        """
        start_ts = int(start_time.timestamp())
        end_ts = int(end_time.timestamp())

        retentions = await StatsUserDataAnalysis.filter(
            time_node__gte=start_ts,
            time_node__lt=end_ts
        ).values()

        game_datas = await StatsGameTimes.filter(
            time_node__gte=start_ts,
            time_node__lt=end_ts
        ).values()
        return {'retentions': list(retentions), 'game_datas': list(game_datas)}
