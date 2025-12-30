"""
通知相关类
"""
from nsanic.libs import tool_dt
from sanic import Request
from tortoise.transactions import in_transaction
from c_services.const.cs_enum_const import CmdWorkers, CmdWs
from common.public.conf import R_UID_THRESHOLD
from common.public.enum_const import DbKey, ServiceEnum
from lucky_admin.base_api import AdminAuthApi
from lucky_admin.handler.pack_msg import pack_background_timed_task
from lucky_admin.model_db.main import RecordsAdminTimedTask
from lucky_admin.model_rc.conf_announcements import ConfAnnouncementsRC
from lucky_admin.model_rc.mails_manage import RecordsAdminMailsRC
from lucky_game.const import MailSender, MailType, GoodsType
from lucky_game.model_db.main import UserBag
from lucky_game.model_rc.base_bag import UserBagRC
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.model_rc.goods_manager import GoodsManagerRC
from lucky_admin.const import AnnouncementsStatus, UserGroup, WeightEnum, BackTaskSta


class BanHandler(AdminAuthApi):
    """ 封禁处理 """

    async def post(self, req: Request, **_b):
        uid = req.json.get('uid')
        self.check_int(uid, require=True, minval=R_UID_THRESHOLD + 1, p_name='uid')

        ban_time = req.json.get('ban_time')
        self.check_int(ban_time, require=True, minval=-1, p_name='ban_time')

        if 0 < ban_time < tool_dt.cur_time():
            self.answer(code=self.sta_code.FAIL, hint='封禁时间有误，请检查！')

        u_info = await BaseUserRC.cache_by_uid(uid)
        if not u_info:
            self.answer(hint="封禁玩家失败，没有玩家信息")

        await BaseUserRC.update_info(u_info, {"ban_time": ban_time})
        data = {
            "uid": uid,
            "ban_time": ban_time,
        }
        await self.inner_cs2ws(ServiceEnum.WS_HALL, CmdWs.BAN_PLAYER, 1, data)

        self.log_info("封禁玩家：", uid, ban_time)
        self.answer(hint="ok")


class AnnouncementsHandler(AdminAuthApi):
    """ 公告相关 """

    async def get(self, _a: Request, **_b):
        data = await ConfAnnouncementsRC.get_current_announcement()
        self.answer(data=data)

    def __verify_announcement(self, req):
        cur_time = tool_dt.cur_time()
        start_time = self.check_int(req.json.get('start_time'), require=True, p_name='start_time')
        end_time = self.check_int(req.json.get('end_time'), require=True, minval=start_time, p_name='end_time')

        interval_timestamp = 5
        if end_time - start_time < interval_timestamp * 60:
            self.answer(hint=f"开始时间与结束数据间隔不能小于{interval_timestamp}分钟")

        title = req.json.get('title')
        self.check_str(title, require=True, maxlen=64, p_name='title')

        content = req.json.get('content')
        self.check_str(content, require=True, maxlen=255, p_name='content')

        carousel_count = self.check_int(
            req.json.get('carousel_count'), require=True, maxval=10, p_name='carousel_count')

        target_group = req.json.get('target_group') or UserGroup.USER_ALL

        status = req.json.get('status')
        if status:
            status = self.check_int(status, require=True, maxval=AnnouncementsStatus.OUT_OF_TIME, p_name='status')
        else:
            status = AnnouncementsStatus.DRAFT if start_time > cur_time else AnnouncementsStatus.CURRENT

        weight = req.json.get('weight') or WeightEnum.W2
        self.check_int(weight, require=True, minval=WeightEnum.W1, maxval=WeightEnum.W5, p_name='carousel_count')
        return start_time, end_time, title, content, carousel_count, target_group, status, weight

    async def post(self, req: Request, **_b):
        """ 新增公告 """
        start_time, end_time, title, content, carousel_count, target_group, status, weight = self.__verify_announcement(
            req)
        data = await ConfAnnouncementsRC.add_announcement(
            title, content, start_time, end_time, carousel_count, target_group, status)
        if data:
            # 广播给当前在线玩家
            data = {"ann_list": data}
            await self.push_task2worker(CmdWorkers.NOTIFY_ANNOUNCEMENT, data, uid=1)
            self.answer(hint='ok')
        self.answer(code=self.sta_code.FAIL, hint='新增失败！')

    async def put(self, req: Request, **_b):
        id_ = req.json.get('id')
        self.check_int(id_, require=True, minval=1, p_name='id')
        announcement = await ConfAnnouncementsRC.db_model.filter(id=id_).first()
        if not announcement:
            self.answer(code=self.sta_code.ERR_ARG, hint="修改项不存在")
        start_time, end_time, title, content, carousel_count, target_group, status, weight = self.__verify_announcement(
            req)
        announcement.start_time = start_time
        announcement.end_time = end_time
        announcement.title = title
        announcement.content = content
        announcement.carousel_count = carousel_count
        announcement.target_group = target_group
        announcement.status = status
        announcement.weight = weight
        await announcement.save()
        data_list = await ConfAnnouncementsRC.get_current_announcement()
        for data in data_list:
            if data.get('id') == id_:
                data['start_time'] = start_time
                data['end_time'] = end_time
                data['title'] = title
                data['content'] = content
                data['carousel_count'] = carousel_count
                data['target_group'] = target_group
                data['status'] = status
                data['weight'] = weight

        await self.conf.rds.set_item(ConfAnnouncementsRC.tb_name, data_list)
        self.answer(data=data_list)


class MailsManagerSend(AdminAuthApi):
    """后台单发 / 群发 / 全员发邮件"""
    decorators = []

    async def post(self, req: Request, **_b):
        title = self.check_str(req.json.get("title"), require=True, minlen=2, maxlen=20, p_name='title（标题）')
        content = self.check_str(req.json.get("content"), require=True, maxlen=240, p_name='content（内容）')
        start_time = req.json.get("start_time") or 0
        if start_time > 0:
            start_time = self.check_int(start_time, minval=tool_dt.cur_time(), p_name='start_time（开始发送时间）')
        end_time = req.json.get("end_time") or 0
        if end_time > 0:
            end_time = self.check_int(end_time, minval=start_time, p_name='end_time（结束发送时间）')

        # 附件:[{"goods_id": 1002, "goods_type": 2, "time_limit": 0, "goods_count": 1880000}, {"goods_id": 1003, ......]
        attachment = req.json.get("attachment") or []
        if attachment and isinstance(attachment, list):
            if len(attachment) > 20:
                self.log_info(len(attachment), "附件最多不能超过20项")
                self.answer(code=self.sta_code.ERR_ARG, hint="附件最多不能超过20项")
            try:
                await GoodsManagerRC.pack_goods_list(attachment)
            except Exception as _:
                self.answer(code=self.sta_code.ERR_ARG, hint="附件格式错误，请检查！")

        # 发/收件人
        sd_enum = MailSender.find_member_by_val(MailSender.SYSTEM)
        (not sd_enum) and self.answer(code=self.sta_code.ERR_ARG, hint="发件人错误")

        # 全员群发:{"type": "all"} / 指定群发(需要名单):{"type": "group", "uid_list": [1, 2, 3, 4, 5]}
        receiver = req.json.get("receiver") or {}
        if receiver.get('type') == "group":
            uid_list = receiver.get('uid_list')
            if 1 > len(uid_list) or len(uid_list) > 100:
                self.answer(code=self.sta_code.ERR_ARG, hint="批量推送用户数量必须在1-100之间")

            for uid in uid_list:
                if uid <= R_UID_THRESHOLD:
                    self.answer(code=self.sta_code.FAIL, hint="uid错误，请检查")

        self.log_info(f"即将{receiver.get('type')}群发邮件，定时:{start_time}")
        mails_data = {
            "mails": [
                {
                    'mail_type': MailType.SYS,
                    'title': title,
                    'content': content,
                    'attachment': attachment,
                    'sender': sd_enum.phrase
                }
            ],
            "receiver": receiver,
        }

        sta = await RecordsAdminMailsRC.insert_one(
            MailType.SYS, title, content, attachment, sd_enum.phrase, start_time, end_time)
        if sta:
            if start_time:
                mails_data["m_id"] = sta.id
                pack_background_timed_task(mails_data, start_time, '定时发送邮件', CmdWorkers.MANAGER_SEND_MAILS)
                await self.push_task2worker(CmdWorkers.BACKGROUND_SCHEDULED_TASK, mails_data)
            else:
                await self.push_task2worker(CmdWorkers.MANAGER_SEND_MAILS, mails_data)
            self.answer(hint='OK')
        self.answer(code=self.sta_code.FAIL, hint='发送失败')


class BackgroundRecordsTaskHandler(AdminAuthApi):
    async def get(self, _a, **_b):
        """ 获取所有后台新增的定时任务 """
        data_list = await RecordsAdminTimedTask.all().values()
        self.answer(data=data_list)

    async def put(self, req: Request, **_b):
        """ 修改后台定时任务状态（撤销） """
        job_id = req.json.get("job_id")
        self.check_str(job_id, require=True, maxlen=32, p_name="job_id")
        status = req.json.get("status")
        self.check_int(status, require=True, minval=0, p_name="status")
        if status != BackTaskSta.CANCELED:
            self.answer(code=self.sta_code.FAIL, hint='状态不对不能取消！')
        data = await RecordsAdminTimedTask.filter(job_id=job_id).first()
        if not data:
            self.answer(code=self.sta_code.FAIL, hint='任务存在')
        if data.status == BackTaskSta.CANCELED:
            self.answer(code=self.sta_code.FAIL, hint='任务已取消，请勿重复操作')
        if data.status == BackTaskSta.FINISHED:
            self.answer(code=self.sta_code.FAIL, hint='操作有误，任务已完成')
        if data.start_time <= tool_dt.cur_time():
            self.answer(code=self.sta_code.FAIL, hint='任务已经开始，不能取消')
        if data.start_time - 5 < tool_dt.cur_time():
            self.answer(code=self.sta_code.FAIL, hint='任务即将开始，不能取消')

        msg = {
            "job_id": job_id,
            "cmd": data.cmd,
            "start_time": data.start_time,
        }
        await self.push_task2worker(CmdWorkers.CANCEL_BACKGROUND_SCHEDULED_TASK, msg)
        self.answer(hint='ok')


class GetActiveMails(AdminAuthApi):
    async def get(self, _, **_b):
        data = await RecordsAdminMailsRC.db_model.all().values()
        # data = await RecordsAdminMailsRC.get_active_mails()
        self.answer(data=data)


class ItemRemovalCompensator(AdminAuthApi):
    """物品删除补偿器（物品删除后补偿玩家）"""
    # decorators = []

    async def post(self, _, **_b):
        """
        1.统计玩家持有删除物品的数量；
        2.计算玩家获得补偿数（持有数量 * 单价）；
        3.草拟邮件发送，改变物品在背包里的状态（改为已删除）；
        """

        # todo:声明一个兑换映射（物品ID:商城单价）/删除物品列表/兑换物品/兑换类型
        goods_compensator = {
            1600: 5,
            1601: 200,
            1602: 92,
            1603: 300,
            1604: 1280,
            1605: 4800,
            1606: 500,
            1607: 800
        }
        goods_ids_to_process = list(goods_compensator.keys())
        compensation_goods_id = 1001
        compensation_goods_type = GoodsType.V_ASSET

        # 1.查询背包里的持有数量
        bag_records = await UserBag.filter(goods_id__in=goods_ids_to_process)
        self.log_info("1.查询背包记录，总记录数:", len(bag_records))

        # 2.遍历记录，计算每个uid的补偿总额
        compensation_dict = {}  # 创建一个字典用于保存每个uid的补偿总和
        for record in bag_records:
            uid = record.uid
            goods_id = record.goods_id
            goods_count = record.goods_count

            price = goods_compensator.get(goods_id, 0)  # 根据goods_id找到对应的单价

            if uid not in compensation_dict:
                compensation_dict[uid] = 0
            compensation_dict[uid] += goods_count * price
        self.log_info("2.计算每个玩家的补偿总额:", compensation_dict)

        # 预先打包补偿物品信息（仅需执行一次）
        compensation_goods = {
            "goods_id": compensation_goods_id,
            "goods_type": compensation_goods_type
        }
        compensation_goods_list = [compensation_goods]
        await GoodsManagerRC.pack_goods_list(compensation_goods_list)
        self.log_info("3.补偿物品信息打包:", compensation_goods_list)

        # 3.构建邮件数据
        mails = []
        rev_uid_list = []  # 获得所有需要接收邮件的用户UID列表
        detailed_goods_info = compensation_goods_list[0]  # 获取第一个也是唯一的一个补偿物品详细信息

        for uid, total_compensation in compensation_dict.items():
            # 根据用户补偿数量修改固定补偿物品模板
            attachments = {
                **detailed_goods_info,  # 使用模板
                "goods_count": total_compensation  # 设置正确的补偿数量
            }
            mail_data = {
                'receiver': uid,
                'mail_type': MailType.SYS.val,
                'title': '道具删除补偿',
                'content': '由于部分游戏道具删除，您获得了以下补偿物品。',
                'attachment': [attachments],  # 将修改后的附件添加到邮件中
                'sender': 'system'
            }
            mails.append(mail_data)
            rev_uid_list.append(uid)

        # 4.发送邮件并通知
        receiver = {'type': 'group', 'uid_list': rev_uid_list}
        mails_data = {
            "mails": mails,
            "receiver": receiver,
        }
        await self.push_task2worker(CmdWorkers.MANAGER_SEND_MAILS, mails_data)

        # 6.批量更新背包状态为已删除
        async with in_transaction(connection_name=DbKey.DEFAULT):  # 使用事务确保数据一致性
            # 删除受影响用户的缓存
            for r in rev_uid_list:
                key = f'{UserBagRC.tb_name}:{r}'
                await UserBagRC.conf.rds.drop_item(key)  # 直接删除缓存键
            await UserBag.filter(goods_id__in=goods_ids_to_process).delete()

        remaining_records_exist = await UserBag.filter(goods_id__in=goods_ids_to_process).exists()
        if remaining_records_exist:
            result = {"status": "ERR", "message": "还有未删除的背包记录。"}
        else:
            result = {"status": "SUC", "message": "所有用户持有记录已删除。"}

        self.log_info("4.补偿邮件已发，数据删除结果:", result)
        self.answer(data={'result': result}, hint='OK')
