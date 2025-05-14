from nsanic.libs import tool_dt
from datetime import datetime, timedelta

from common.public.conf import GLOBAL_TZ
from promising_game.const import LimitPeriod


class KitDt:
    _SPLIT_SUFFIX = {1: 'str', 2: 'y%Y', 3: 'y%Ym%m', 4: 'y%Yw%w', 5: 'y%Ym%md%d'}

    @staticmethod
    def get_date_str(fmt='%Y%m%d'):
        """返回当前日期的字符串表示，格式为yyyyMMdd"""
        return datetime.now().strftime(fmt)

    @staticmethod
    def get_monday_of_week():
        """ 获取当前日期所在周的周一00:00 """
        current_date = datetime.now()
        year, week, _ = current_date.isocalendar()  # 返回年份、周数和星期几
        # 使用ISO周日期格式获取周一的日期
        str_time = f'{year}-W{week}-1'
        monday = datetime.strptime(str_time, "%Y-W%W-%w")
        return int(monday.timestamp())

    @staticmethod
    def timestamp_today():
        """ 返回当天0时的时间戳int型 """
        return tool_dt.day_begin(tz=GLOBAL_TZ)

    @staticmethod
    def cal_midnight_timestamp(timestamp: int):
        """计算给定时间戳的当天0点时间戳"""
        dt = datetime.fromtimestamp(timestamp)
        midnight = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        return int(midnight.timestamp())

    @staticmethod
    def last_month_split(split_type=3):
        """ 上一个月 """
        now = datetime.now()
        last_month_date = now - timedelta(days=now.day)
        return tool_dt.dt_str(last_month_date, KitDt._SPLIT_SUFFIX.get(split_type))

    @staticmethod
    def last_year_split(split_type=2):
        """ 上一年 """
        now = datetime.now()
        last_year = now.year - 1
        last_year_date = now.replace(year=last_year)
        return tool_dt.dt_str(last_year_date, KitDt._SPLIT_SUFFIX.get(split_type))

    @staticmethod
    def timestamp_2_time_str(timestamp, fmt='%Y-%m-%d %H:%M:%S'):
        """将时间戳转换为datetime对象"""
        dt_object = datetime.fromtimestamp(timestamp)
        time_string = dt_object.strftime(fmt)
        return time_string

    @classmethod
    def cal_deadline(cls, day_limit: int, start_time=None):
        """计算截至时间（天数）"""
        if not start_time:
            start_time = datetime.now()
        else:
            start_time = datetime.fromtimestamp(start_time)

        deadline = start_time + timedelta(days=day_limit)
        return int(deadline.timestamp())

    @classmethod
    def cal_period_deadline(cls, period: int, cur_time=None) -> int:
        """ 计算周期截至时间 """
        if not cur_time:
            cur_datetime = datetime.now()
        else:
            cur_datetime = datetime.fromtimestamp(cur_time)

        if period == LimitPeriod.WEEKLY:
            # 下周一的00:00:00
            days_until_next_monday = 7 - cur_datetime.weekday() if cur_datetime.weekday() < 6 else 1
            end_time = (cur_datetime + timedelta(days=days_until_next_monday)).replace(hour=0, minute=0, second=0,
                                                                                       microsecond=0)
        elif period == LimitPeriod.MONTH:
            # 下个月第一天的00:00:00
            next_month = cur_datetime.replace(day=28) + timedelta(days=4)
            end_time = (next_month - timedelta(days=next_month.day)).replace(hour=0, minute=0, second=0,
                                                                             microsecond=0) + timedelta(days=1)
        elif period == LimitPeriod.QUARTERLY:
            # 下一季度第一天的00:00:00
            current_month = cur_datetime.month
            end_month = (current_month - 1) // 3 * 3 + 4
            if end_month > 12:
                end_month = 1
                next_quarter = datetime(cur_datetime.year + 1, end_month, 1)
            else:
                next_quarter = datetime(cur_datetime.year, end_month, 1)
            end_time = next_quarter.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == LimitPeriod.YEAR:
            # 下一年第一天的00:00:00
            end_time = datetime(cur_datetime.year + 1, 1, 1, 0, 0, 0, 0)
        else:
            # 默认为第二天的00:00:00
            end_time = (cur_datetime + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

        return int(end_time.timestamp())

    @classmethod
    def get_daily_timespan(cls, timestamp=None):
        """
        获取指定日期的开始和结束时间戳（当日00:00:00到当日23:59:59）

        Args:timestamp (int, optional): 指定日期的时间戳。如果为None，则返回前一天的时间段
        Returns:tuple: (start_timestamp, end_timestamp) 指定日期的开始和结束时间戳
        """
        # 1.确定日期对象
        if timestamp is None:
            date_obj = datetime.now() - timedelta(days=1)  # 默认前一天
        else:
            date_obj = datetime.fromtimestamp(timestamp)  # 指定日期

        # 2.计算当天00:00:00的时间戳
        start_date = datetime(date_obj.year, date_obj.month, date_obj.day)
        start_timestamp = int(start_date.timestamp())

        # 3.计算当天23:59:59的时间戳
        end_date = datetime(date_obj.year, date_obj.month, date_obj.day, 23, 59, 59)
        end_timestamp = int(end_date.timestamp())

        return start_timestamp, end_timestamp
        
    @staticmethod
    def get_timestamp_of_days_ago(days):
        """ 获取days前的0点时间戳 """
        # 获取当前日期时间
        now = datetime.now()
        # 计算days天前的日期时间
        target_date = now - timedelta(days=days)
        # 将时间设置为当天的0点
        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        # 转换为时间戳
        timestamp = start_of_day.timestamp()
        return int(timestamp)


if __name__ == '__main__':
    print(KitDt.timestamp_today())
    print(tool_dt.day_begin())
