"""
游戏任务相关接口
每日 / 每周 / 每月 / 战令 / 竞猜 / 新手
类型：配置 Conf / 记录 Records
"""
from common.public.enum_const import TaskId
from .active_behaviors import UserBehaviorsRC
from .goods_manager import GoodsManagerRC
from .base_rc import BaseRC
from nsanic.libs import tool_dt
from common.utils.kit_dt import KitDt
from lucky_game.const import TaskType, CompleteSta, PlatForm
from nsanic.libs.tool import json_encode, json_parse
from lucky_game.model_db.main import ConfTask, RecordsUserTask


class ConfTaskRC(BaseRC):
    db_model = ConfTask
    tb_name = db_model.sheet_name()

    expired_mode = 0
    expired_sec = 2 * 86400

    @classmethod
    async def get_task_item_by_id(cls, task_id):
        """按ID获取任务配置"""
        return await cls.cache_conf_by_pk(task_id)

    @classmethod
    async def get_task_items(cls, task_type=None, platform='', is_pack=False):
        """按指定task_type和platform获取/缓存任务配置+打包"""
        info = await cls.cache_all_conf_item()
        if not info:
            return []

        task_conf = []
        default_tasks = []
        for i in info:
            if task_type and i.get('task_type') != task_type:
                continue

            i_platform = i.get('platform')
            if i_platform == PlatForm.DEFAULT:
                default_tasks.append(i)
            else:
                # 根据传入的平台短语转换为对应的枚举值并进行匹配
                p_enum = PlatForm.get_val_by_phrase(platform)
                if i_platform == p_enum:  # 根据platform进行过滤
                    task_conf.append(i)

        task_conf.extend(default_tasks)
        if is_pack and task_conf:
            await GoodsManagerRC.pack_goods_conf(task_conf)
        return task_conf

    @staticmethod
    def get_task_time_node(task_type: TaskType, task_item=None):
        """通过TaskType获取任务统计周期"""
        match task_type:
            case TaskType.DAILY_TASK | TaskType.MONOPOLY_TASK:
                time_node = KitDt.timestamp_today()
            case TaskType.WARFARE_TASK:
                end_time = task_item.get("end_time")
                if end_time and end_time < tool_dt.cur_time():
                    time_node = 0
                else:
                    time_node = task_item.get("start_time", 0) if task_item else 0
            case _:
                time_node = -1

        return time_node


class UserTaskRC(BaseRC):
    db_model = RecordsUserTask
    tb_name = db_model.sheet_name()

    expired_mode = 1
    expired_sec = 2 * 86400

    ALLOW_UPDATE_TASKS = (TaskId.ROOKIE_PART_FIRST.val, TaskId.DOUYIN_REVISIT.val,
                          TaskId.ROOKIE_PART_MONOPOLY.val, TaskId.ROOKIE_PART_SECOND_1.val,
                          TaskId.ROOKIE_PART_SECOND_2.val, TaskId.FIRST_SHARE_AL.val,
                          TaskId.FIRST_SHARE_WX.val, TaskId.FIRST_SHARE_DY.val)

    @classmethod
    async def cache_task_records(cls, uid):
        """ 获取用户任务记录 """

        async def from_db():
            db_info = await cls.db_model.get_by_dict({"uid": uid})
            if db_info:
                cache_db_info_dict = {}
                for o in db_info:
                    _id = o.get("task_id")
                    cache_db_info_dict[str(_id)] = json_encode(o)
                await cls.conf.rds.set_hash_bulk(key_name, cache_db_info_dict)
                return db_info
            return []

        key_name = f'{cls.tb_name}:{uid}'
        info_list = await cls.conf.rds.get_hash_val(key_name)
        if info_list:
            info_list = [json_parse(one, cls.logerr) for one in info_list]
            return info_list
        return await from_db()

    @classmethod
    async def cache_task_record_by_id(cls, uid, task_id):
        """ 获取用户任务记录 """

        # 防止缓存击穿，使用双重检查锁（DCL）
        async def from_cache():
            info = await cls.conf.rds.get_hash(key_name, task_id)
            if info:
                return json_parse(info, cls.logerr)

        async def cache_all_from_db():
            cache_data = await from_cache()
            if cache_data:
                return cache_data
            data_list = await cls.cache_task_records(uid)
            return next((i for i in data_list if i.get('task_id') == task_id), {})

        key_name = f'{cls.tb_name}:{uid}'
        return await from_cache() or await cls.conf.rds.locked(f"{key_name}:{task_id}", fun=cache_all_from_db)

    @classmethod
    async def get_task_unclaimed(cls, uid, task_type: TaskType):
        """获取是否有任务完成/活跃达成"""
        today_time_node = KitDt.timestamp_today()

        if task_type == TaskType.DAILY_TASK:
            active_awards_sta, _ = await UserBehaviorsRC.stat_active_achieve_award(uid, today_time_node)
            if CompleteSta.COMPLETED.val in active_awards_sta:
                return True

        condition = {
            "uid": uid,
            "time_node": today_time_node,
            "task_type": task_type,
            "task_sta": CompleteSta.COMPLETED
        }
        task_record = await cls.db_model.get_by_dict(condition, limit=1)
        if task_record:
            return True
        return False

    @classmethod
    async def check_task_data(cls, uid, task_type: TaskType, task_items):
        """ 检查用户任务数据 """
        task_record = await cls.cache_task_records(uid)
        if not task_record:
            return task_items

        task_record_map = {t_data.get("task_id"): t_data for t_data in task_record}

        task_info = []
        for t_conf in task_items:
            if t_conf.get("task_type") != task_type:
                continue
            t_conf["target_data"] = json_encode(t_conf.get("target_data"))

            time_node = ConfTaskRC.get_task_time_node(task_type, t_conf)
            t_data = task_record_map.get(t_conf.get("task_id"))
            if t_data and t_data.get("time_node") == time_node:
                t_conf["task_sta"] = t_data.get('task_sta')
                t_conf["cur_value"] = t_data.get('cur_value')

            task_info.append(t_conf)
        return task_info

    @classmethod
    async def update_user_task_records(cls, uid, update_info: dict, is_pull=False, is_sum=False):
        """
        用户任务更新
        :params update_info 更新内容
        :params is_pull 是否为领奖更新
        :params is_sum 是否更新值已累加过
        """

        async def update_cache(new_info):
            await cls.conf.rds.set_hash(f'{cls.tb_name}:{uid}', task_id, new_info)

        async def insert_task():
            is_finished = True if add_val >= achieve_value else False
            insert_data = {
                'uid': uid,
                'task_type': task_type,
                'time_node': time_node,
                'task_sta': CompleteSta.COMPLETED.val if is_finished else CompleteSta.INCOMPLETE.val,
                'cur_value': add_val,
                'task_id': task_id,
                'finish_time': tool_dt.cur_time() if is_finished else 0
            }
            insert_obj = await cls.db_model.add_one(insert_data)
            if insert_obj:
                insert_data["id"] = insert_obj.id
                await update_cache(insert_data)
            return is_finished, insert_data

        finish_flag = False  # 任务完成标识
        task_id = update_info.get("task_id")  # 主键，无需查询已知

        # 1.查询任务配置
        task_item = await ConfTaskRC.get_task_item_by_id(task_id)
        if not task_item:
            return finish_flag, {}

        add_val = update_info.get("add_val", 0)  # 当前更新的完成数值
        achieve_value = task_item.get("achieve_value", 1)  # 任务完成目标值
        task_type = task_item.get("task_type")  # 类型，决定统计周期
        time_node = ConfTaskRC.get_task_time_node(task_type, task_item)

        # 2.查询当前任务完成情况
        old_task = await cls.cache_task_record_by_id(uid, task_id)
        if not old_task:
            return await insert_task()

        if is_pull:
            if old_task.get("task_sta") == CompleteSta.CLAIMED and old_task.get('cur_value', 0) >= achieve_value:
                return finish_flag, old_task
            # 领奖状态变化
            new_task = {'task_sta': CompleteSta.CLAIMED.val}
        else:
            if old_task.get("time_node") == time_node \
                    and (old_task.get("task_sta") in (CompleteSta.COMPLETED, CompleteSta.CLAIMED)
                         and old_task.get('cur_value', 0) >= achieve_value):
                return finish_flag, old_task
            if old_task.get("time_node") != time_node:
                cur_value = add_val
            else:
                # 检查任务完成情况
                if old_task.get('cur_value', 0) >= achieve_value:
                    cur_value = achieve_value
                else:
                    if is_sum:
                        cur_value = add_val
                    else:
                        cur_value = old_task.get('cur_value', 0) + add_val

            new_task = {'cur_value': cur_value, 'time_node': time_node}
            if cur_value >= achieve_value:
                new_task['task_sta'] = CompleteSta.COMPLETED
                new_task['finish_time'] = tool_dt.cur_time()
                finish_flag = True
            else:
                new_task['task_sta'] = CompleteSta.INCOMPLETE

        await cls.db_model.update_by_pk(old_task.get('id'), new_task, old_task, update_cache)
        return finish_flag, old_task

    @classmethod
    async def get_douyin_revisit_chance(cls, uid):
        """获取抖音侧边栏复访机会/奖励"""
        condition = {
            "uid": uid,
            "time_node": KitDt.timestamp_today(),
            "task_type": TaskType.DAILY_TASK.val,
            "task_id": TaskId.DOUYIN_REVISIT.val
        }
        task_record = await cls.db_model.get_by_dict(condition, limit=1)
        if task_record and task_record.get("task_sta") == CompleteSta.COMPLETED.val:
            return True
        if not task_record:
            return True
        return False
