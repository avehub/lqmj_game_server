from nsanic.orm.db_model import DBModel
from tortoise import fields
from promising_game.const import MailType
from promising_admin.const import AdminStatus, AdminPermission, UserGroup, AnnouncementsStatus, WeightEnum, \
    BackTaskSta, MailSta


class Admins(DBModel):
    """ 后台管理员 """
    username = fields.CharField(max_length=20, unique=True, default='', description='玩家昵称')
    password = fields.CharField(max_length=64, default='', description='密码')
    # phone = fields.CharField(max_length=18, null=True, index=True, description='手机号码')
    # email = fields.CharField(max_length=128, null=True, index=True, description='邮箱')
    updated = fields.BigIntField(null=True, default=0, description='更新时间')
    safe_key = fields.CharField(max_length=18, null=True, default='', description='安全密钥（不能泄密）')
    valid_key = fields.CharField(max_length=16, null=True, default='', description='验证密钥')
    status = fields.IntEnumField(
        enum_type=AdminStatus, defualt=AdminStatus.PENDING, description='表示管理员账户的状态，如启用、禁用、待审核等。')
    permission = fields.IntEnumField(
        enum_type=AdminPermission, defualt=AdminPermission.P1, description='管理员权限')


class ConfAnnouncements(DBModel):
    """ 公告表 """
    title = fields.CharField(max_length=64, default='', description="主题/标题")
    content = fields.CharField(max_length=255, default='', description='公告内容')
    start_time = fields.IntField(max_length=28, null=False, default=0, description='公告开始时间')
    end_time = fields.IntField(max_length=28, null=False, default=0, description='公告结束时间')
    target_group = fields.IntEnumField(
        enum_type=UserGroup, default=UserGroup.USER_ALL, description='目标用户群, 如普通用户、VIP用户等')
    carousel_count = fields.SmallIntField(default=1, description='轮播次数')
    status = fields.IntEnumField(
        enum_type=AnnouncementsStatus, index=True, default=1, description='状态, 例如: 草稿、已发布、已过期')
    weight = fields.IntEnumField(enum_type=WeightEnum, default=WeightEnum.W2, description="权重")

    class Meta:
        table = "conf_announcements"
        indexes = (('start_time', 'end_time'),)


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


class RecordsAdminMails(DBModel):
    """ 记录后台邮件 """
    mail_type = fields.IntEnumField(enum_type=MailType, index=True, default=MailType.SYS, description='邮件类型')
    title = fields.CharField(max_length=64, default='', description="主题/标题")
    content = fields.CharField(max_length=255, default='', description="邮件内容")
    attachment = fields.JSONField(null=True, description="附件信息：如奖励ID和数量等")
    sender = fields.CharField(max_length=28, default='', description="发送者")
    start_time = fields.BigIntField(null=True, index=True, default=0, description='开始时间')
    end_time = fields.BigIntField(
        null=True, index=True, default=0, description='结束时间 0只发在开始时间时的所有显存玩家，大于0一段时间内的现存玩家')
    status = fields.IntEnumField(enum_type=MailSta, index=True, description="管理邮件状态")
    job_id = fields.CharField(max_length=32, unique=True, null=True, description='任务id')

    class Meta:
        table = "records_admin_mails"
        indexes = (("start_time", "end_time"),)
