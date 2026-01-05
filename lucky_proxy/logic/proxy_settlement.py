import decimal
import time
import traceback

from nsanic.libs.component import LogMeta
import pymysql
from typing import List, Tuple, Optional
import logging
from datetime import datetime

from lucky_proxy.model_db.main import ProxyUser, ProxyMonthSettlement, ProxySettlementLog

"""
月结算处理器
"""


class ProxysJobExecutor(LogMeta):

    @classmethod
    async def every_month_summary(cls):
        try:
            cls.log_info(f"开始执行每月结算统计date={datetime.now()}")
            month_processor = ProxySettlementProcessor(
                batch_size=100,
                target_month=_get_default_month()
            )
            await month_processor.process_monthly_settlement()
        except Exception as ex:
            cls.log_err(f"查询代理ID失败: {ex}")
            raise


def _get_default_month() -> str:
    """获取默认月份（上个月）"""
    today = datetime.now()
    # 获取上个月
    if today.month == 1:
        last_month = 12
        year = today.year - 1
    else:
        last_month = today.month - 1
        year = today.year

    return f"{year}-{last_month:02d}"


class ProxySettlementProcessor(LogMeta):
    def __init__(self, batch_size: int, target_month: str):
        self.batch_size = batch_size
        self.target_month = target_month
        self.log_info(f"初始化结算处理器: batch_size={batch_size}, target_month={target_month}")

    async def fetch_proxy_ids_batch(self, last_id: int = 0) -> List[int]:
        """
        分批次获取proxy_user的id

        Args:
            last_id: 上一批次的最大id

        Returns:
            当前批次的id列表
        """
        sql = f"""
            SELECT id 
            FROM proxy_user 
            WHERE id > {last_id} 
            ORDER BY id  asc
            LIMIT {self.batch_size}
        """
        try:
            users = await ProxyUser.exec_sql(sql, query=True)
            ids = [item["id"] for item in users]
            return ids
        except Exception as ex:
            self.log_err(f"查询代理ID失败: {ex}")
            raise

    async def calculate_monthly_settlement_batch(self, proxy_ids: List[int]) -> List[Tuple]:
        """
        批量计算指定代理的月度结算数据（优化版，使用JOIN）

        Args:
            proxy_ids: 代理id列表

        Returns:
            结算数据列表，每个元素为(proxy_id, month, total_amount, total_income)
        """
        if not proxy_ids:
            return []
        try:
            id_placeholders = ','.join(map(str, proxy_ids))

            sql = f"""
                    SELECT
                        b.proxy_id,
                        b.month,
                        sum( total_amount ) total_amount,
                        sum( total_income ) total_income ,
                        sum( total_order ) total_order 
                    FROM
                        (
                        SELECT
                            pu.id AS proxy_id,
                            '{self.target_month}' month,
                            COALESCE ( SUM( podr.order_amount ), 0 ) total_amount,
                            COALESCE ( SUM( podr.proxy_income ), 0 ) total_income,
                            COUNT( podr.id ) total_order 
                        FROM
                            proxy_user pu
                            LEFT JOIN proxy_order_dividend_records podr ON pu.id = podr.proxy_id 
                            AND podr.order_month = '{self.target_month}' 
                        WHERE
                            pu.id IN ( {id_placeholders} ) 
                        GROUP BY
                            pu.id UNION ALL
                        SELECT
                            podr.level1_proxy_id AS proxy_id,
                            '{self.target_month}' month,
                            COALESCE ( SUM( podr.order_amount ), 0 ) total_amount,
                            COALESCE ( SUM( podr.level1_proxy_income ), 0 ) total_income,
                            COUNT( podr.id ) total_order 
                        FROM
                            proxy_user pu
                            LEFT JOIN proxy_order_dividend_records podr ON pu.id = podr.proxy_id 
                            AND podr.order_month = '{self.target_month}' 
                        WHERE
                            podr.level1_proxy_id IN ( {id_placeholders}) 
                        GROUP BY
                            podr.level1_proxy_id 
                        ) b 
                    GROUP BY
                        b.proxy_id,
                        b.month
                """
            settlements = await ProxyUser.exec_sql(sql, query=True)

            self.log_info(f"计算完成: {len(settlements)} 个代理的结算数据")
            return settlements
        except pymysql.Error as ex:
            self.log_err(f"计算月度结算数据失败: {ex}")
            raise

    async def batch_upsert_settlements(self, settlements: List[Tuple]):
        if not settlements:
            return
        try:
            # 使用批量插入和更新
            sql = """
                    INSERT INTO proxy_month_settlement 
                    (proxy_id, month, total_amount, total_income, total_order,created)
                    VALUES (%s, %s, %s, %s, %s,10000)
                """
            now = time.time()
            for s in settlements:
                s["created"] = now
                s.update({"year": s["month"][:4]})
            instances = [ProxyMonthSettlement(**data) for data in settlements]
            await ProxyMonthSettlement.bulk_create(instances, batch_size=len(instances))
            self.log_info(f"成功处理 {len(settlements)} 条结算记录data={settlements}")
        except Exception as ex:
            self.log_err(f"批量插入结算数据失败: {ex},data={settlements}")
            raise

    async def process_monthly_settlement(self):
        """
        主处理流程：分批次处理所有代理的月度结算
        """
        self.log_info(f"开始处理 {self.target_month} 月的代理结算数据...")

        total_processed = 0
        total_settlements = 0
        last_id = 0
        batch_count = 0
        total_amount = decimal.Decimal("0.00")
        total_income = decimal.Decimal("0.00")
        total_order_count = decimal.Decimal("0.00")

        # 记录开始时间
        start_time = time.time()
        status = 1
        while True:
            batch_count += 1
            self.log_info(f"处理第 {batch_count} 批次...")
            try:
                # 1. 分批次获取代理id
                proxy_ids = await  self.fetch_proxy_ids_batch(last_id)

                if not proxy_ids:
                    self.log_info("所有代理数据已处理完成")
                    break

                # 更新last_id为当前批次的最大id
                last_id = max(proxy_ids)
                total_processed += len(proxy_ids)

                # 2. 可选：检查已有记录，跳过已处理的代理
                # existing_ids = self.check_existing_settlements(proxy_ids)
                # remaining_ids = [pid for pid in proxy_ids if pid not in existing_ids]
                # 这里我们选择重新计算所有代理，所以不跳过
                remaining_ids = proxy_ids

                if not remaining_ids:
                    self.log_info(f"批次 {batch_count} 的所有代理已有结算记录，跳过")
                    continue

                # 3. 批量计算月度结算数据（使用优化查询）
                settlements = await  self.calculate_monthly_settlement_batch(remaining_ids)

                # 4. 批量插入或更新结算数据
                if settlements:
                    await  self.batch_upsert_settlements(settlements)
                    total_settlements += len(settlements)
                    # 使用sum函数统计
                    total_amount += sum(item['total_amount'] for item in settlements)
                    total_income += sum(item['total_income'] for item in settlements)
                    total_order_count += sum(item['total_order'] for item in settlements)
                self.log_info(
                    f"批次 {batch_count} 完成: 处理 {len(proxy_ids)} 个代理，生成 {len(settlements)} 条结算记录")
                if len(proxy_ids) < self.batch_size:
                    self.log_info("已到达最后一批数据...")
                    break

            except Exception as e:
                traceback.print_exc()
                self.log_err(f"处理批次 {batch_count} 时发生错误: {e}")
                self.log_err(f"严重错误 {self.target_month} 月的代理结算数据失败，失败批次=[{proxy_ids}]")
                status = 2
                break

        # 记录结束时间
        self.log_info(f"""
                     {self.target_month}结算数据：
                         total_income={total_income}
                         total_amount= {total_amount}
                         total_order_count={total_order_count}
                """)
        settlement_log = {
            "total_amount": total_amount,
            "total_income": total_income,
            "total_order": total_order_count,
            "month": self.target_month,
            "year": self.target_month[:4],
            "start_time": start_time,
            "end_time": time.time(),
            "settlement_status": status,
            "total_order_count": total_order_count
        }
        await ProxySettlementLog.add_one(settlement_log)


# 使用示例
if __name__ == "__main__":
    # 创建优化处理器实例
    processor = ProxySettlementProcessor(
        batch_size=100,  # 每批处理100个代理
        target_month='2023-12'  # 处理2023年12月的数据，
    )
    processor.process_monthly_settlement()
