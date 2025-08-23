#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移框架
支持复杂的多对多关系数据迁移
"""

import logging
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Tuple, Callable
from datetime import datetime
import pymysql
import json

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """数据库配置"""
    host: str
    port: int
    username: str
    password: str
    database: str
    charset: str = 'utf8mb4'


@dataclass
class MigrationResult:
    """迁移结果"""
    success_count: int = 0
    error_count: int = 0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class DatabaseManager:
    """数据库连接管理器"""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.connection = None

    def connect(self):
        """建立数据库连接"""
        try:
            self.connection = pymysql.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.username,
                password=self.config.password,
                database=self.config.database,
                charset=self.config.charset,
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False
            )
            logger.info(f"Connected to database: {self.config.database}")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def disconnect(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")

    def execute_query(self, sql: str, params: tuple = None) -> List[Dict]:
        """执行查询"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Query execution failed: {sql}, Error: {e}")
            raise

    def execute_insert(self, sql: str, params: tuple = None) -> int:
        """执行插入操作"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Insert execution failed: {sql}, Error: {e}")
            raise

    def execute_batch_insert(self, sql: str, params_list: List[tuple]) -> int:
        """批量插入"""
        try:
            with self.connection.cursor() as cursor:
                return cursor.executemany(sql, params_list)
        except Exception as e:
            logger.error(f"Batch insert failed: {sql}, Error: {e}")
            raise

    def commit(self):
        """提交事务"""
        if self.connection:
            self.connection.commit()

    def rollback(self):
        """回滚事务"""
        if self.connection:
            self.connection.rollback()


class BaseMigrator(ABC):
    """基础迁移器抽象类"""

    def __init__(self, old_db: DatabaseManager, new_db: DatabaseManager):
        self.old_db = old_db
        self.new_db = new_db
        self.name = self.__class__.__name__
        self.result = MigrationResult()

    @abstractmethod
    def extract_data(self) -> List[Dict]:
        """从旧数据库提取数据"""
        pass

    @abstractmethod
    def transform_data(self, old_data: List[Dict]) -> List[Dict]:
        """转换数据格式"""
        pass

    @abstractmethod
    def load_data(self, transformed_data: List[Dict]) -> None:
        """加载数据到新数据库"""
        pass

    def validate_data(self, data: List[Dict]) -> bool:
        """数据验证（可选重写）"""
        return True

    def pre_migrate_hook(self) -> None:
        """迁移前钩子（可选重写）"""
        pass

    def post_migrate_hook(self) -> None:
        """迁移后钩子（可选重写）"""
        pass

    def migrate(self) -> MigrationResult:
        """执行迁移流程"""
        logger.info(f"Starting migration: {self.name}")

        try:
            # 迁移前钩子
            self.pre_migrate_hook()

            # 提取数据
            logger.info(f"Extracting data from old database...")
            old_data = self.extract_data()
            logger.info(f"Extracted {len(old_data)} records")

            if not old_data:
                logger.warning("No data to migrate")
                return self.result

            # 转换数据
            logger.info("Transforming data...")
            transformed_data = self.transform_data(old_data)
            logger.info(f"Transformed {len(transformed_data)} records")

            # 验证数据
            if not self.validate_data(transformed_data):
                raise ValueError("Data validation failed")

            # 加载数据
            logger.info("Loading data to new database...")
            self.load_data(transformed_data)

            # 迁移后钩子
            self.post_migrate_hook()

            logger.info(f"Migration completed: {self.name}")

        except Exception as e:
            self.result.error_count += 1
            error_msg = f"Migration failed for {self.name}: {str(e)}"
            self.result.errors.append(error_msg)
            logger.error(error_msg)
            logger.error(traceback.format_exc())

        return self.result


class UserMigrator(BaseMigrator):
    """用户数据迁移器示例"""

    def extract_data(self) -> List[Dict]:
        """从旧用户表提取数据"""
        sql = """
        SELECT 
            user_id,
            username,
            nickname,
            email,
            phone,
            avatar,
            level,
            coins,
            diamonds,
            vip_level,
            vip_expire_time,
            created_time,
            updated_time,
            status
        FROM users 
        WHERE status = 1
        """
        return self.old_db.execute_query(sql)

    def transform_data(self, old_data: List[Dict]) -> List[Dict]:
        """转换用户数据"""
        transformed = []

        for user in old_data:
            # 基础用户信息
            user_data = {
                'old_user_id': user['user_id'],
                'username': user['username'],
                'nickname': user['nickname'],
                'email': user['email'],
                'phone': user['phone'],
                'avatar': user['avatar'],
                'coins': user['coins'],
                'diamonds': user['diamonds'],
                'created_time': user['created_time'],
                'updated_time': user['updated_time'],
                'status': user['status']
            }

            # VIP信息（如果VIP等级 > 0）
            vip_data = None
            if user['vip_level'] > 0:
                vip_data = {
                    'vip_level': user['vip_level'],
                    'expire_time': user['vip_expire_time'],
                    'created_time': user['created_time']
                }

            transformed.append({
                'user': user_data,
                'vip': vip_data
            })

        return transformed

    def load_data(self, transformed_data: List[Dict]) -> None:
        """加载用户数据到新数据库"""
        user_sql = """
        INSERT INTO users (
            old_user_id, username, nickname, email, phone, avatar,
            coins, diamonds, created_time, updated_time, status
        ) VALUES (
            %(old_user_id)s, %(username)s, %(nickname)s, %(email)s, 
            %(phone)s, %(avatar)s, %(coins)s, %(diamonds)s, 
            %(created_time)s, %(updated_time)s, %(status)s
        )
        """

        vip_sql = """
        INSERT INTO user_vip (
            user_id, vip_level, expire_time, created_time
        ) VALUES (
            %(user_id)s, %(vip_level)s, %(expire_time)s, %(created_time)s
        )
        """

        for data in transformed_data:
            try:
                # 插入用户基础信息
                user_id = self.new_db.execute_insert(user_sql, data['user'])

                # 插入VIP信息（如果存在）
                if data['vip']:
                    vip_data = data['vip'].copy()
                    vip_data['user_id'] = user_id
                    self.new_db.execute_insert(vip_sql, vip_data)

                self.result.success_count += 1

            except Exception as e:
                self.result.error_count += 1
                error_msg = f"Failed to migrate user {data['user']['username']}: {str(e)}"
                self.result.errors.append(error_msg)
                logger.error(error_msg)


class GameRecordMigrator(BaseMigrator):
    """游戏战绩迁移器示例"""

    def extract_data(self) -> List[Dict]:
        """提取房间战绩和详情数据"""
        sql = """
        SELECT 
            r.record_id,
            r.room_id,
            r.room_name,
            r.game_type,
            r.total_rounds,
            r.created_time,
            r.finished_time,
            d.detail_id,
            d.user_id,
            d.username,
            d.round_num,
            d.score,
            d.final_score
        FROM room_records r
        LEFT JOIN record_details d ON r.record_id = d.record_id
        WHERE r.status = 1
        ORDER BY r.record_id, d.round_num
        """
        return self.old_db.execute_query(sql)

    def transform_data(self, old_data: List[Dict]) -> List[Dict]:
        """转换战绩数据结构"""
        # 按record_id分组
        grouped_records = {}

        for row in old_data:
            record_id = row['record_id']

            if record_id not in grouped_records:
                grouped_records[record_id] = {
                    'room_record': {
                        'old_record_id': record_id,
                        'room_id': row['room_id'],
                        'room_name': row['room_name'],
                        'game_type': row['game_type'],
                        'total_rounds': row['total_rounds'],
                        'created_time': row['created_time'],
                        'finished_time': row['finished_time']
                    },
                    'total_records': {},  # 用户总战绩
                    'round_records': []  # 子局战绩
                }

            # 处理详情数据
            if row['detail_id']:
                user_id = row['user_id']

                # 累计总战绩
                if user_id not in grouped_records[record_id]['total_records']:
                    grouped_records[record_id]['total_records'][user_id] = {
                        'user_id': user_id,
                        'username': row['username'],
                        'total_score': 0,
                        'final_score': row['final_score']
                    }

                grouped_records[record_id]['total_records'][user_id]['total_score'] += row['score']

                # 子局战绩
                grouped_records[record_id]['round_records'].append({
                    'user_id': user_id,
                    'username': row['username'],
                    'round_num': row['round_num'],
                    'score': row['score']
                })

        return list(grouped_records.values())

    def load_data(self, transformed_data: List[Dict]) -> None:
        """加载战绩数据"""
        room_sql = """
        INSERT INTO room_records (
            old_record_id, room_id, room_name, game_type, total_rounds,
            created_time, finished_time
        ) VALUES (
            %(old_record_id)s, %(room_id)s, %(room_name)s, %(game_type)s,
            %(total_rounds)s, %(created_time)s, %(finished_time)s
        )
        """

        total_sql = """
        INSERT INTO total_records (
            record_id, user_id, username, total_score, final_score
        ) VALUES (
            %(record_id)s, %(user_id)s, %(username)s, %(total_score)s, %(final_score)s
        )
        """

        round_sql = """
        INSERT INTO round_records (
            record_id, user_id, username, round_num, score
        ) VALUES (
            %(record_id)s, %(user_id)s, %(username)s, %(round_num)s, %(score)s
        )
        """

        for record_data in transformed_data:
            try:
                # 插入房间战绩
                new_record_id = self.new_db.execute_insert(room_sql, record_data['room_record'])

                # 批量插入总战绩
                total_params = []
                for total_record in record_data['total_records'].values():
                    params = total_record.copy()
                    params['record_id'] = new_record_id
                    total_params.append(params)

                if total_params:
                    self.new_db.execute_batch_insert(total_sql, [tuple(p.values()) for p in total_params])

                # 批量插入子局战绩
                round_params = []
                for round_record in record_data['round_records']:
                    params = round_record.copy()
                    params['record_id'] = new_record_id
                    round_params.append(params)

                if round_params:
                    self.new_db.execute_batch_insert(round_sql, [tuple(p.values()) for p in round_params])

                self.result.success_count += 1

            except Exception as e:
                self.result.error_count += 1
                error_msg = f"Failed to migrate record {record_data['room_record']['old_record_id']}: {str(e)}"
                self.result.errors.append(error_msg)
                logger.error(error_msg)


class MigrationOrchestrator:
    """迁移编排器"""

    def __init__(self, old_db_config: DatabaseConfig, new_db_config: DatabaseConfig):
        self.old_db = DatabaseManager(old_db_config)
        self.new_db = DatabaseManager(new_db_config)
        self.migrators: List[BaseMigrator] = []
        self.overall_result = MigrationResult()

    def add_migrator(self, migrator_class) -> None:
        """添加迁移器"""
        migrator = migrator_class(self.old_db, self.new_db)
        self.migrators.append(migrator)

    def run_migration(self) -> MigrationResult:
        """运行所有迁移"""
        logger.info("Starting database migration...")

        try:
            # 连接数据库
            self.old_db.connect()
            self.new_db.connect()

            # 执行迁移
            for migrator in self.migrators:
                logger.info(f"Running migrator: {migrator.name}")

                try:
                    result = migrator.migrate()
                    self.overall_result.success_count += result.success_count
                    self.overall_result.error_count += result.error_count
                    self.overall_result.errors.extend(result.errors)

                    # 提交当前迁移器的事务
                    self.new_db.commit()
                    logger.info(f"Migrator {migrator.name} completed successfully")

                except Exception as e:
                    # 回滚当前迁移器的事务
                    self.new_db.rollback()
                    error_msg = f"Migrator {migrator.name} failed: {str(e)}"
                    self.overall_result.errors.append(error_msg)
                    logger.error(error_msg)

            logger.info("Database migration completed")

        except Exception as e:
            logger.error(f"Migration orchestrator failed: {str(e)}")
            self.overall_result.errors.append(str(e))

        finally:
            # 断开数据库连接
            self.old_db.disconnect()
            self.new_db.disconnect()

        return self.overall_result

    def generate_report(self) -> str:
        """生成迁移报告"""
        report = f"""
=== 数据库迁移报告 ===
迁移时间: {datetime.now()}
成功记录数: {self.overall_result.success_count}
失败记录数: {self.overall_result.error_count}
总记录数: {self.overall_result.success_count + self.overall_result.error_count}

"""
        if self.overall_result.errors:
            report += "错误详情:\n"
            for i, error in enumerate(self.overall_result.errors, 1):
                report += f"{i}. {error}\n"

        return report


def main():
    """主函数示例"""
    # 数据库配置
    old_db_config = DatabaseConfig(
        host='localhost',
        port=3306,
        username='root',
        password='password',
        database='old_database'
    )

    new_db_config = DatabaseConfig(
        host='localhost',
        port=3306,
        username='root',
        password='password',
        database='new_database'
    )

    # 创建迁移编排器
    orchestrator = MigrationOrchestrator(old_db_config, new_db_config)

    # 添加迁移器（按依赖顺序）
    orchestrator.add_migrator(UserMigrator)
    orchestrator.add_migrator(GameRecordMigrator)

    # 执行迁移
    result = orchestrator.run_migration()

    # 生成报告
    report = orchestrator.generate_report()
    print(report)

    # 保存报告到文件
    with open(f'migration_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt', 'w') as f:
        f.write(report)


if __name__ == "__main__":
    main()