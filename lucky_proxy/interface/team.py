from sanic import Request

from lucky_proxy.base_api import ProxyAuthApi
from lucky_proxy.logic.proxy_summary import ProxySummary
from lucky_proxy.model_db.main import ProxyUser, GameUser, ProxyUserWallet, ProxyPromotionRelation
from nsanic.libs import tool_dt

"""
团队
"""


class TeamSummary(ProxyAuthApi):

    async def get(self, req: Request, **kwargs):
        proxy_id = kwargs.get("uid")
        team_info = await ProxyUserWallet.get_by_dict({"id": proxy_id}, field=["total_player", "level2_total_player"])
        partner = await ProxyPromotionRelation.exec_sql(f"select count(1) as cnt from proxy_promotion_relation where proxy_id={proxy_id} and upgrade_flag=1", query=True, for_one=True)
        partner_channel = await ProxyPromotionRelation.exec_sql(f"select count(1) as cnt from proxy_promotion_relation t join proxy_user s on s.id=t.channel_proxy_id and s.is_channel=1 where t.channel_proxy_id={proxy_id} and t.upgrade_flag=1", query=True, for_one=True)
        data = {}
        if team_info:
            data.update(team_info[0])
        if isinstance(partner, dict):
            data.update({"partner_count": partner.get("cnt", 0)})
        if isinstance(partner_channel, dict):
            data.update({"partner_channel_count": partner_channel.get("cnt", 0)})
        self.answer(self.sta_code.PASS, data, hint='查询成功!')


"""
查询推广码下绑定的玩家分页
"""


class Player(ProxyAuthApi):

    async def get(self, req: Request, **kwargs):
        proxy_id = kwargs.get("uid")
        page_size = self.check_int(req.args.get("page_size"), default=20, require=False, p_name="page_size", minval=10,
                                   maxval=100)
        page = self.check_int(req.args.get("page"), default=1, require=False, p_name="page_size")
        sort = self.check_int(req.args.get("sort"), default=0, require=False, p_name="sort", maxval=2, minval=1)
        promotion_player_page = await ProxySummary.query_player_page(proxy_id=proxy_id, page_size=page_size,
                                                                     page=page, sort=sort)
        return self.answer(self.sta_code.PASS, promotion_player_page, hint='查询成功!')


"""
团队成员分页查询
"""


class TeamMemberQuery(ProxyAuthApi):

    async def get(self, req: Request, **kwargs):
        proxy_id = kwargs.get("uid")
        page_size = self.check_int(req.args.get("page_size"), default=20, require=False, p_name="page_size", minval=10,
                                   maxval=100)
        page = self.check_int(req.args.get("page"), default=1, require=False, p_name="page_size")
        sort = self.check_int(req.args.get("sort"), default=1, require=False, p_name="sort", maxval=2, minval=1)
        promotion_player_page = await ProxySummary.query_team_member_page(level1_proxy_id=proxy_id, page_size=page_size,
                                                                          page=page,
                                                                          sort=sort)
        return self.answer(self.sta_code.PASS, promotion_player_page, hint='查询成功!')


class TeamMemberInfoDetailQuery(ProxyAuthApi):

    async def get(self, req: Request, **kwargs):
        proxy_id = kwargs.get("uid")
        member_id = self.check_int(req.args.get("member_id"), require=True, p_name="member_id")
        sql = f"select u.id,u.assistance_program_rate,u.room_card_rate,u.join_day,w.total_amount,w.total_income  from " \
              f"proxy_user u,proxy_user_wallet w where u.id=w.id and u.id={member_id} and u.level1_proxy_id={proxy_id}"
        detail = await  ProxyUser.exec_sql(sql, query=True, for_one=True)
        user: GameUser = await GameUser.get_by_pk(member_id, ["name", "phone", "avatar"])
        if user and isinstance(detail, dict):
            detail.update({"name": user.get("name")})
            detail.update({"phone": user.get("phone")})
            detail.update({"avatar": user.get("avatar")})
        self.answer(self.sta_code.PASS, detail, hint='查询成功!')


class PlayerVipQuery(ProxyAuthApi):
    async def get(self, req: Request, **kwargs):
        proxy_id = kwargs.get("uid")
        page_size = self.check_int(req.args.get("page_size"), default=20, require=False, p_name="page_size", minval=10, maxval=100)
        page = self.check_int(req.args.get("page"), default=1, require=False, p_name="page")
        sort = self.check_int(req.args.get("sort"), default=0, require=False, p_name="sort", maxval=2, minval=0)
        vip_state = self.check_int(req.args.get("vip_state"), default=None, require=False, p_name="vip_state")
        expired = self.check_int(req.args.get("expired"), default=None, require=False, p_name="expired", minval=0, maxval=1)
        now = tool_dt.cur_time()
        expire_start = None
        expire_end = None
        if vip_state is not None:
            if vip_state == 1:
                expire_start = now
            elif vip_state == 2:
                expire_end = now
        elif expired is not None:
            if expired == 0:
                expire_start = now
            elif expired == 1:
                expire_end = now
        rows = await ProxySummary.query_vip_player_page(proxy_id=proxy_id, page_size=page_size, page=page, sort=sort, expire_start=expire_start, expire_end=expire_end)
        return self.answer(self.sta_code.PASS, rows, hint='查询成功!')
