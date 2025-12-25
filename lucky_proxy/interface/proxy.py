# coding=utf-8
import decimal
from datetime import datetime

from tortoise.transactions import in_transaction

from common.public.enum_const import DbKey
from common.utils.utils import UtilsTool
from lucky_proxy.base_api import BaseApi, ProxyAuthApi
from sanic import Request
from lucky_proxy.logic.promotion_code import PromotionCode
from lucky_proxy.model_db.main import ProxyUser, ProxyUserBankCard, ProxyPromotionRelation, GameUser, ProxyUserWallet

"""
代理设置相关控制器
"""

"""
设置二级代理
"""


class AddLevel2Proxy(ProxyAuthApi):

    async def post(self, req: Request, **kwargs):
        proxy_id = kwargs.get("uid")
        member_id = self.check_int(req.json.get("uid"), require=True, p_name="uid")
        proxy_user: ProxyUser = await ProxyUser.get_by_pk(proxy_id)
        if not proxy_user and proxy_user.get("proxy_level") != 1:
            self.answer(self.sta_code.FAIL, {}, hint='无权限操作!')
        proxy_user_level2: ProxyUser = await ProxyUser.get_by_pk(req.json.get("uid"))
        if proxy_user_level2:
            self.answer(self.sta_code.FAIL, {}, hint='请勿重复绑定!')

        query_relation = {
            "player_id": member_id,
            "proxy_id": proxy_id,
        }
        # 自己邀请的才能绑定为二级代理
        relation: ProxyPromotionRelation = await ProxyPromotionRelation.get_by_dict(query_relation, limit=1)
        if not relation:
            self.answer(self.sta_code.FAIL, {}, hint='关系不存在!')
            # 自己邀请的才能绑定为二级代理
        query_user = {
            "uid": member_id
        }
        user: GameUser = await GameUser.get_by_dict(query_user, ["uid", "phone", "unionid"], limit=1)
        if not user:
            self.answer(self.sta_code.FAIL, {}, hint='用户不存在!')
        promotion_code = UtilsTool.generate_invite_code(10)
        exists_user = ProxyUser.get_by_pk({"promotion_code": promotion_code}, field=["id"])
        # 重试一次
        if exists_user:
            promotion_code = UtilsTool.generate_invite_code(10)

        level2_proxy = {
            "id": member_id,
            "level1_proxy_id": proxy_id,
            "auth_status": 0,
            "total_player": 0,
            "phone": user.get("phone"),
            "unionid": user.get("unionid"),
            "room_card_rate": self.check_float(req.json.get("room_card_rate"), keep_val=2, minval=0.01, require=True,
                                               maxval=0.90,
                                               p_name="room_card_rate"),
            "assistance_program_rate": self.check_float(req.json.get("assistance_program_rate"), keep_val=2,
                                                        require=True, minval=0.01,
                                                        maxval=0.90, p_name="assistance_program_rate"),
            "proxy_level": 2,
            "create_by": proxy_id,
            "promotion_code": UtilsTool.generate_invite_code(10),
            "join_day": datetime.now().strftime("%Y-%m-%d")
        }
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                await ProxyUser.add_one(level2_proxy)
                await ProxyUserWallet.add_one({"id": member_id})
        except Exception as e:
            self.log_err(f"设置二级代理出错err={e}")
            self.answer(self.sta_code.FAIL, {}, hint='设置失败，请重试!')
        self.answer(self.sta_code.PASS, {}, hint='设置成功!')


"""
修改二级代理的分成比例
"""


class ModifyLevel2ProxyRate(ProxyAuthApi):

    async def post(self, req: Request, **kwargs):
        proxy_id = kwargs.get("uid")
        room_card_rate = self.check_float(req.json.get("room_card_rate"), keep_val=2, minval=0.01, require=True,
                                          maxval=0.90,
                                          p_name="room_card_rate"),
        assistance_program_rate = self.check_float(req.json.get("assistance_program_rate"), keep_val=2,
                                                   require=True, minval=0.01,
                                                   maxval=1, p_name="assistance_program_rate"),
        member_id = req.json.get("member_id")
        update_param = {
            "id": member_id,
            "level1_proxy_id": proxy_id
        }
        update_column = {
            "room_card_rate": round(room_card_rate[0], 2),
            "assistance_program_rate": round(assistance_program_rate[0], 2)
        }
        res = await ProxyUser.update_by_cond(update_param, update_column)
        sta, hint = [self.sta_code.PASS, '操作成功'] if res else [self.sta_code.FAIL, '操作失败']
        self.answer(sta, {}, hint=hint)


"""
删除代理
"""


class RemoveLevel2Proxy(ProxyAuthApi):

    async def post(self, req: Request, **kwargs):
        proxy_id = kwargs.get("uid")
        member_id = req.json.get("member_id")
        res = await  ProxyUser.del_by_cond({"id": member_id, "level1_proxy_id": proxy_id})
        sta, hint = [self.sta_code.PASS, '操作成功'] if res else [self.sta_code.FAIL, '操作失败']
        self.answer(sta, {}, hint=hint)


"""
基础资料设置
"""


class ProxyBaseInfoSetting(BaseApi):

    async def post(self, req: Request, **kwargs):
        proxy_id = kwargs.get("uid")
        proxy_user: ProxyUser = await ProxyUserBankCard.get_by_pk(proxy_id)
        if not proxy_user and proxy_user.get("proxy_level") != 1:
            self.answer(self.sta_code.FORBID, {}, hint='无权限操作!')
        level2_proxy = {
            "proxy_id": self.check_int(req.json.get("uid")),
            "level1_proxy_id": proxy_id,
            "auth_status": 0,
            "promotion_code": PromotionCode.generate_invite_code(10)
        }
        await ProxyUser.add_one(level2_proxy)
        self.answer(self.sta_code.PASS, {}, hint='设置成功!')


"""
查询代理信息
"""


class ProxyInfoQuery(ProxyAuthApi):

    async def get(self, req: Request, **kwargs):
        proxy_id = kwargs.get("uid")
        proxy_user: ProxyUser = await ProxyUser.get_by_pk(proxy_id, field=["auth_status", "proxy_level",
                                                                           "assistance_program_rate", "room_card_rate"])
        user: GameUser = await GameUser.get_by_pk(proxy_id, ["name", "avatar"])
        info = {
            "auth_status": proxy_user.get("auth_status"),
            "proxy_level": proxy_user.get("proxy_level"),
            "assistance_program_rate": proxy_user.get("assistance_program_rate"),
            "room_card_rate": proxy_user.get("room_card_rate"),
            "name": user.get("name"),
            "name": user.get("name"),
            "name": user.get("name"),
            "avatar": user.get("avatar"),
        }
        self.answer(self.sta_code.PASS, info, hint='查询成功!')


"""
代理推广码查询
"""


class ProxyPromotionCodeQuery(ProxyAuthApi):

    async def get(self, req: Request, **kwargs):
        proxy_id = kwargs.get("uid")
        proxy_user: ProxyUser = await ProxyUser.get_by_pk(proxy_id, field=["promotion_code"])
        promotion_info = {
            "promotion_code": proxy_user.get("promotion_code"),
            "link": "https://xxx.xxx.com"
        }
        self.answer(self.sta_code.PASS, promotion_info, hint='查询成功!')


"""
代理银行卡信息查询
"""


class ProxyBankQuery(ProxyAuthApi):

    async def get(self, req: Request, **kwargs):
        proxy_id = kwargs.get("uid")
        query = {
            "proxy_id": proxy_id
        }
        proxy_user: ProxyUser = await ProxyUserBankCard.get_by_dict(query, limit=1)
        self.answer(self.sta_code.PASS, proxy_user, hint='查询成功!')


"""
银行卡设置
"""


class ProxyBankCardSetting(ProxyAuthApi):

    async def post(self, req: Request, **kwargs):
        proxy_id = kwargs.get("uid")
        info = req.json
        bank_card = {
            # 银行卡id(没有新增 有为更新)
            "id": self.check_phone_number(info.get('id'), require=False),
            # 电话号码
            "phone": self.check_phone_number(info.get('phone'), require=True),
            "proxy_id": proxy_id,
            # 姓名
            "name": self.check_str(info.get('name'), maxlen=12, minlen=2, require=True, p_name="name"),
            # 银行卡号
            "bank_card_no": self.check_str(info.get('bank_card_no'), maxlen=20, minlen=16, require=True,
                                           p_name="bank_card_no"),
            # 户名
            "card_name": self.check_str(info.get('card_name'), maxlen=12, minlen=2, require=True, p_name="card_name"),
            # 支行
            "sub_branch": self.check_str(info.get('sub_branch'), maxlen=32, minlen=2, require=True,
                                         p_name="sub_branch"),
        }
        proxy_user: ProxyUser = await ProxyUser.get_by_pk(proxy_id, field=["auth_status"])
        if proxy_user.get("auth_status") == 1:
            self.answer(self.sta_code.FAIL, {}, hint='不能重复设置!')
        user_bank_card: ProxyUserBankCard = await ProxyUserBankCard.add_one(bank_card)
        if not user_bank_card:
            self.answer(self.sta_code.FAIL, {}, hint='设置失败!')
        await ProxyUser.update_by_pk(proxy_id, {"auth_status": 1})
        self.answer(self.sta_code.PASS, {"id": user_bank_card.id}, hint='设置成功!')
