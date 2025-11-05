from nsanic.orm.db_model import DBModel
from tortoise import fields
from lucky_game.const import MailType
from lucky_admin.const import AdminStatus, AdminPermission, UserGroup, AnnouncementsStatus, WeightEnum, \
    BackTaskSta, MailSta


class Admins(DBModel):
    """ 后台管理员 """
    username = fields.CharField(max_length=20, unique=True, default='', description='玩家昵称')
    password = fields.CharField(max_length=64, default='', description='密码')
    updated = fields.BigIntField(null=True, default=0, description='更新时间')
    safe_key = fields.CharField(max_length=18, null=True, default='', description='安全密钥（不能泄密）')
    valid_key = fields.CharField(max_length=16, null=True, default='', description='验证密钥')
    status = fields.IntEnumField(
        enum_type=AdminStatus, defualt=AdminStatus.PENDING, description='表示管理员账户的状态，如启用、禁用、待审核等。')
    permission = fields.IntEnumField(
        enum_type=AdminPermission, defualt=AdminPermission.P1, description='管理员权限')


class RecordsAdminOperates(DBModel):
    """ 后台操作记录 """
    # _SPLIT_TYPE = 2
    username = fields.CharField(max_length=20, index=True, default='', description='操作者')
    route = fields.CharField(max_length=32, index=True, default='', description='路由')
    op_name = fields.CharField(max_length=16, default='', description='操作名（描述）')
    method = fields.CharField(max_length=8, default='', description='请求方法')
    params = fields.JSONField(null=True, default='', description='请求参数')
    status = fields.SmallIntField(description='状态码')
    hint = fields.CharField(max_length=32, default='', description='提示')

    class Meta:
        table = "records_admin_operates"

    @classmethod
    async def insert_one(cls, username, route, op_name, method, params, status, hint=''):
        data = {
            "username": username,
            "route": route,
            "op_name": op_name,
            "method": method,
            "params": params,
            "status": status,
            "hint": hint,
        }
        return await cls.add_one(data)


class RecordsAdminTimedTask(DBModel):
    """ 后台定时任务记录 """
    job_id = fields.CharField(max_length=32, pk=True, default='', description='任务id')
    cmd = fields.SmallIntField(description='命令号')
    name = fields.CharField(max_length=16, default='', description='任务名')
    start_time = fields.BigIntField(null=True, default=0, description='开始时间')
    params = fields.JSONField(null=True, default='', description='任务参数')
    status = fields.IntEnumField(enum_type=BackTaskSta, description='状态: 0已取消 1待执行 2已执行')

    class Meta:
        table = "records_admin_timed_task"

    @classmethod
    async def insert_one(cls, job_id, cmd, name, start_time, params, status):
        data = {
            "job_id": job_id,
            "cmd": cmd,
            "name": name,
            "start_time": start_time,
            "params": params,
            "status": status,
        }
        return await cls.add_one(data)


