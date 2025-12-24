from sanic import Request

from lucky_proxy.base_api import ProxyAuthApi
from lucky_proxy.logic.proxy_summary import ProxySummary
from lucky_proxy.model_db.main import ProxyUser, GameUser

"""
团队
"""


class TeamSummary(ProxyAuthApi):

    async def get(self, req: Request, **kwargs):
        proxy_id = kwargs.get("uid")
        team_info = await ProxyUser.get_by_pk(proxy_id, ["total_player", "level2_total_player"])
        self.answer(self.sta_code.PASS, team_info, hint='查询成功!')


"""
查询推广码下绑定的玩家分页
"""


class Player(ProxyAuthApi):

    async def get(self, req: Request, **kwargs):
        proxy_id = kwargs.get("uid")
        last_id = self.check_int(req.args.get("last_id"), require=False, p_name="last_id")
        sort = self.check_int(req.args.get("sort"), require=False, p_name="sort", maxval=2, minval=1)
        page_size = self.check_int(req.args.get("page_size"), default=20, require=False, p_name="page_size", minval=10,
                                   maxval=100)
        promotion_player_page = None
        promotion_player_page = await ProxySummary.query_player_page(proxy_id=proxy_id, page_size=page_size,
                                                                     last_id=last_id, sort=sort)
        return self.answer(self.sta_code.PASS, promotion_player_page, hint='查询成功!')


"""
团队成员分页查询
"""


class TeamMemberQuery(ProxyAuthApi):

    async def get(self, req: Request, **kwargs):
        proxy_id = kwargs.get("uid")
        last_id = self.check_int(req.args.get("last_id"), require=False, p_name="last_id")
        last_amount = self.check_int(req.args.get("last_amount"), require=False, p_name="last_amount")
        page_size = self.check_int(req.args.get("page_size"), default=20, require=False, p_name="page_size", minval=10,
                                   maxval=100)
        sort = self.check_int(req.args.get("sort"), require=False, p_name="sort", maxval=2, minval=1)
        promotion_player_page = await ProxySummary.query_team_member_page(level1_proxy_id=proxy_id, page_size=page_size,
                                                                          last_id=last_id,
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
        if user:
            detail["name"] = user.get("name")
            detail["phone"] = user.get("phone")
            detail["avatar"] = user.get("avatar")
        self.answer(self.sta_code.PASS, detail, hint='查询成功!')
