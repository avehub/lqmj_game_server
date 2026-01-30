"""
邮件系统
"""
import asyncio
import traceback

from sanic import Request
from tortoise.transactions import in_transaction

from common.model_rc.tournament_rewards import TournamentRewardRC
from lucky_game.base_api import GameAuthApi
from lucky_game.handler.up_assets import UpAssets, StatFlow
from lucky_game.model_db.main import Mails
from lucky_game.model_rc.base_mails import MailsRC
from lucky_game.model_rc.base_award import AwardRC
from common.public.enum_const import DbKey
from lucky_game.const import MailSta, PullSta, MailOpType, ReasonCostGold, ReasonCostDiamond
from lucky_game.logic.activity import Base


class MailsListHandler(GameAuthApi):
    """获取邮件列表"""

    async def get(self, req, **kwargs):
        user = kwargs.get("u_info")
        uid = user.get("uid")
        sta, mail_list = await MailsRC.get_mails_list(uid=uid, mail_sta=[MailSta.UNREAD, MailSta.READ])
        if sta:
            mail_list = await MailsRC.get_mail_awards(mail_list)
        return self.answer(data=mail_list)


class MailsOperateUser(GameAuthApi):
    """指定邮件标记已读 / 领奖 / 删除"""

    async def post(self, req: Request, **kwargs):
        mail_id = self.check_int(req.json.get("mail_id"), require=True, p_name='mail_id')

        # 1.操作类型核验
        opt_type = self.check_int(req.json.get("opt_type"), require=True, p_name='opt_type')
        ot_enum = MailOpType.find_member_by_val(opt_type)
        (not ot_enum) and self.answer(code=self.sta_code.ERR_ARG, hint="不支持的操作类型")

        user = kwargs.get("u_info")
        uid = user.get("uid")

        # 2.查询需要操作的邮件
        mail_data = await Mails.get_by_pk(mail_id)
        (not mail_data) and self.answer(code=self.sta_code.EMAIL_NOT_FOUND, hint="找不到指定邮件")

        map_func = {
            MailOpType.READ.val: self.mails_read,
            MailOpType.PULL.val: self.mails_pull,
            MailOpType.DEL.val: self.mails_del
        }
        opt_func = map_func.get(opt_type)
        if opt_func and callable(opt_func):
            sta, msg, up_goods = await opt_func(uid, mail_id, mail_data)
            self.log_info(uid, f'邮件{ot_enum.phrase}操作结果 {sta}')
            if not sta:
                return self.answer(code=self.sta_code.FAIL, hint=msg)
            return self.answer(data=up_goods if opt_type == MailOpType.PULL else [])

    async def mails_read(self, _, mail_id, mail_data):
        if mail_data.get('mail_sta') == MailSta.READ:
            return False, "不能重复标记已读", []

        new_data = {'mail_sta': MailSta.READ}
        read_sta = await Mails.update_by_pk(mail_id, new_data)
        if not read_sta:
            return False, "已读失败，请稍后再试", []

        return True, "已读成功", []

    async def mails_del(self, _, mail_id, mail_data):
        award_items = mail_data.get('attachment')
        if award_items and mail_data.get('attachment_sta') == PullSta.UN_PULL:
            return False, "还有奖励未领取，请领取后再尝试", []

        new_data = {'mail_sta': MailSta.DELETED}
        drop_sta = await Mails.update_by_pk(mail_id, new_data)
        if not drop_sta:
            return False, "删除失败，请稍后再试", []

        return True, "删除成功", []

    async def mails_pull(self, uid, mail_id, mail_data):
        up_goods = []
        award_items = mail_data.get('attachment')
        if not award_items or mail_data.get('attachment_sta') == PullSta.PULLED:
            return False, "没有需要领取的奖励", up_goods

        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                # 处理邮件附件奖励
                mail_list = await MailsRC.get_mail_awards([mail_data])
                award_ids = mail_data.get("attachment")["award_ids"]
                award_data, e = await AwardRC.get_award_by_filter(award_id=award_ids)
                award_dict = {item['award_id']: item for item in award_data}
                for k, award_id in enumerate(award_ids):
                    await Base().gain_awards(uid, award_id=award_id, reward_type=3, awards=award_dict[award_id].get("content")["rewards"])
                    # 热身赛奖励等到下个周赛才可领取
                    # if award_id not in TournamentRewardRC.WARM_UP_REWARD:
                    await Base().give_awards(uid, award_id)
                    up_goods.extend(award_dict[award_id].get("content")["rewards"])
                new_data = {'attachment_sta': PullSta.PULLED, 'mail_sta': MailSta.READ}
                await Mails.update_by_pk(mail_id, new_data)
        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            for frame in tb:
                self.logerr(f"File: {frame.filename}, Line: {frame.lineno}, Function: {frame.name}")
            self.log_err(f"mails_pull 事务执行失败，原因：{e}")
            return False, "邮件奖励领取失败，请联系客服", up_goods
        return True, "邮件领取成功", up_goods


class MailsOperateOneClick(GameAuthApi):
    """一键操作邮件领奖 / 删除"""

    async def post(self, req: Request, **kwargs):
        # 1.操作类型核验
        opt_type = self.check_int(req.json.get("opt_type"), require=True, p_name='opt_type')
        ot_enum = MailOpType.find_member_by_val(opt_type)
        (not ot_enum) and self.answer(code=self.sta_code.ERR_ARG, hint="不支持的操作类型")
        user = kwargs.get("u_info")
        uid = user.get("uid")
        mail_sta = None
        attachment_sta = None
        if opt_type == MailOpType.READ:
            mail_sta = MailSta.UNREAD
        elif opt_type == MailOpType.PULL:
            attachment_sta = PullSta.UN_PULL
        # 2.查询标准邮件列表
        sta, mail_data = await MailsRC.get_mails_list(uid=uid, mail_sta=mail_sta, attachment_sta=attachment_sta)
        (not sta) and self.answer(code=self.sta_code.EMAIL_NOT_FOUND, hint="暂时没有邮件哦")

        map_func = {
            MailOpType.PULL.val: self.mails_pull_auto,
            MailOpType.DEL.val: self.mails_del_auto
        }
        opt_func = map_func.get(opt_type)
        data = []
        if opt_func and callable(opt_func):
            sta, msg, data = await opt_func(uid, mail_data)
            self.log_info(uid, f'邮件{ot_enum.phrase}一键操作结果 {sta}')
            if not sta:
                return self.answer(code=self.sta_code.FAIL, hint=msg)
        return self.answer(data=data if opt_type == MailOpType.PULL else [])

    async def mails_del_auto(self, _, mail_data):
        update_mail = []
        new_data = {'mail_sta': MailSta.DELETED}
        for item in mail_data:
            awards = item.get('attachment')
            mail_id = item.get('mail_id')
            if not awards or item.get('attachment_sta') == PullSta.PULLED:
                update_mail.append(Mails.update_by_pk(mail_id, new_data, item))

        if not update_mail:
            return False, "没有可删除的邮件", update_mail
        await asyncio.gather(*update_mail)

        return True, "一键删除成功", update_mail

    async def mails_pull_auto(self, uid, mail_data):
        award_items = []
        up_goods = []
        # 1. 收集需要更新的邮件
        for g in mail_data:
            awards = g.get('attachment')
            if awards and g.get('attachment_sta') == PullSta.UN_PULL:
                award_items.append(g)

        if not award_items:
            return False, "没有可领取的奖励", up_goods

        # 2. 准备更新操作
        new_data = {'attachment_sta': PullSta.PULLED, 'mail_sta': MailSta.READ}
        update_operations = []

        for item in award_items:
            mail_id = item.get('mail_id')
            if mail_id:
                update_operations.append(
                    Mails.filter(pk=mail_id).update(**new_data)
                )

        if not update_operations:
            return False, "没有可领取的奖励", up_goods

        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                # 3. 处理邮件附件奖励
                mail_list = await MailsRC.get_mail_awards(award_items)
                for mail in mail_list:
                    awards = mail.get('attachment', {}).get('awards', [])
                    if awards:
                        award_id = mail.get("attachment")["award_ids"][0]
                        await Base().gain_awards(uid, awards=awards, award_id=award_id, reward_type=3)
                        # 热身赛奖励等到下个周赛才可领取
                        # if award_id not in TournamentRewardRC.WARM_UP_REWARD:
                        await Base().give_awards(uid, award_id)
                        up_goods.extend(awards)

                # 4. 执行批量更新
                if update_operations:
                    await asyncio.gather(*update_operations)

        except Exception as e:
            self.log_err(f"mails_pull_auto 事务执行失败，原因：{e}")
            return False, "一键领取奖励失败，请联系客服", up_goods
        return True, "一键领取成功", up_goods
