"""
邮件系统
"""
import asyncio
from sanic import Request
from tortoise.transactions import in_transaction
from lucky_game.base_api import GameAuthApi
from lucky_game.handler.up_assets import UpAssets, StatFlow
from lucky_game.model_db.main import Mails
from lucky_game.model_rc.base_mails import MailsRC
from common.public.enum_const import DbKey
from lucky_game.const import MailSta, PullSta, MailOpType, ReasonCostGold, ReasonCostDiamond
# # from lucky_game.model_rc.base_skin import UserSkinRC


class MailsListHandler(GameAuthApi):
    """获取邮件列表"""

    async def get(self, _, **kwargs):
        user = kwargs.get("u_info")
        uid = user.get("uid")

        mail_list = await MailsRC.get_mails_list(uid)
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
            sta = await opt_func(uid, mail_id, mail_data)
            self.log_info(uid, f'邮件{ot_enum.phrase}操作结果 {sta}')
            if sta:
                if opt_type == MailOpType.PULL:
                    self.answer(data=sta)
                else:
                    self.answer(hint='OK!')
            return self.answer(code=self.sta_code.FAIL)

    async def mails_read(self, _, mail_id, mail_data):
        if mail_data.get('mail_sta') == MailSta.READ:
            self.answer(code=self.sta_code.ALREADY_DO, hint="不能重复标记已读")

        new_data = {'mail_sta': MailSta.READ}
        read_sta = await Mails.update_by_pk(mail_id, new_data)
        (not read_sta) and self.answer(code=self.sta_code.FAIL, hint="已读失败，请稍后再试")

        return True

    async def mails_del(self, _, mail_id, mail_data):
        award_items = mail_data.get('attachment')
        if award_items and mail_data.get('attachment_sta') == PullSta.UN_PULL:
            self.answer(code=self.sta_code.FAIL, hint="还有奖励未领取，请领取后再尝试")

        new_data = {'mail_sta': MailSta.DELETED}
        drop_sta = await Mails.update_by_pk(mail_id, new_data)
        (not drop_sta) and self.answer(code=self.sta_code.FAIL, hint="删除失败，请稍后再试")

        return True

    async def mails_pull(self, uid, mail_id, mail_data):
        award_items = mail_data.get('attachment')
        if not award_items or mail_data.get('attachment_sta') == PullSta.PULLED:
            self.answer(code=self.sta_code.GOODS_NOT_FOUND, hint="没有需要领取的奖励")

        # 处理皮肤兑换
        for i in award_items:
            pass
            # await UserSkinRC.deal_hold_skin(uid, i)
        StatFlow.stat_common_flow(awards=award_items, d_reason=ReasonCostDiamond.MAILS_GIFT, g_reason=ReasonCostGold.MAILS_GIFT)

        new_data = {'attachment_sta': PullSta.PULLED, 'mail_sta': MailSta.READ}
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                await Mails.update_by_pk(mail_id, new_data)
                up_goods = await UpAssets.update_assets(uid, award_items, [], is_pack=True)
        except Exception as e:
            self.log_err(f"mails_pull 事务执行失败，原因：{e}")
            self.answer(code=self.sta_code.FAIL, hint="邮件奖励领取失败，请联系客服")

        return up_goods


class MailsOperateOneClick(GameAuthApi):
    """一键操作邮件领奖 / 删除"""

    async def post(self, req: Request, **kwargs):
        # 1.操作类型核验
        opt_type = self.check_int(req.json.get("opt_type"), require=True, p_name='opt_type')
        ot_enum = MailOpType.find_member_by_val(opt_type)
        (not ot_enum) and self.answer(code=self.sta_code.ERR_ARG, hint="不支持的操作类型")

        user = kwargs.get("u_info")
        uid = user.get("uid")

        # 2.查询标准邮件列表
        mail_data = await MailsRC.get_mails_list(uid)
        (not mail_data) and self.answer(code=self.sta_code.EMAIL_NOT_FOUND, hint="暂时没有邮件哦")

        map_func = {
            MailOpType.PULL.val: self.mails_pull_auto,
            MailOpType.DEL.val: self.mails_del_auto
        }
        opt_func = map_func.get(opt_type)
        if opt_func and callable(opt_func):
            sta = await opt_func(uid, mail_data)
            self.log_info(uid, f'邮件{ot_enum.phrase}一键操作结果 {sta}')
            if sta:
                if opt_type == MailOpType.PULL:
                    self.answer(data=sta)
                else:
                    self.answer(hint='邮件操作成功')
            return self.answer(code=self.sta_code.FAIL)

    async def mails_del_auto(self, _, mail_data):
        update_mail = []
        new_data = {'mail_sta': MailSta.DELETED}
        for item in mail_data:
            awards = item.get('attachment')
            mail_id = item.get('mail_id')
            if not awards or item.get('attachment_sta') == PullSta.PULLED:
                update_mail.append(Mails.update_by_pk(mail_id, new_data, item))

        (not update_mail) and self.answer(code=self.sta_code.EMAIL_NOT_FOUND, hint="还有奖励未领取，请领取后再尝试")
        await asyncio.gather(*update_mail)

        return True

    async def mails_pull_auto(self, uid, mail_data):
        award_items = []
        for g in mail_data:
            awards = g.get('attachment')
            if awards and g.get('attachment_sta') == PullSta.UN_PULL:
                award_items.extend(awards)
        (not award_items) and self.answer(code=self.sta_code.GOODS_NOT_FOUND, hint="没有可领取的奖励")

        # 处理皮肤兑换
        for i in award_items:
            pass
#             await UserSkinRC.deal_hold_skin(uid, i)
        StatFlow.stat_common_flow(awards=award_items, d_reason=ReasonCostDiamond.MAILS_GIFT , g_reason=ReasonCostGold.MAILS_GIFT)

        update_mail = []
        new_data = {'attachment_sta': PullSta.PULLED, 'mail_sta': MailSta.READ}
        for item in mail_data:
            mail_id = item.get('mail_id')
            update_mail.append(Mails.update_by_pk(mail_id, new_data, item))
        (not update_mail) and self.answer(code=self.sta_code.GOODS_NOT_FOUND, hint="没有可领取的奖励")

        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                update_mail and await asyncio.gather(*update_mail)
                up_goods = await UpAssets.update_assets(uid, award_items, [], is_pack=True)
        except Exception as e:
            self.log_err(f"mails_pull_auto 事务执行失败，原因：{e}")
            self.answer(code=self.sta_code.FAIL, hint="一键领取奖励失败，请联系客服")

        return up_goods