from sanic import Request
from lucky_admin.base_api import AdminAuthApi
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.model_rc.extra_club_event import ExtraClubEventRC
from lucky_game.model_rc.base_award import AwardRC


class Award(AdminAuthApi):
    async def post(self, req: Request, **kwargs):
        """ 创建奖励 """
        name = self.check_str(req.json.get("name"), require=True, minlen=2, maxlen=10, p_name="奖励名称")
        type = self.check_int(req.json.get("type"), require=True, p_name="奖励类型")
        level = self.check_int(req.json.get("level"), require=True, p_name="奖励等级")
        content = self.check_str(req.json.get("content"), require=True, p_name="奖励内容")
        sta, new = await AwardRC.create_award(name=name, level=level, type=type, content=content)
        if not sta:
            return self.answer(self.sta_code.FAIL, hint=new)
        return self.answer(data={"award_id": new.award_id})

    async def get(self, req: Request):
        """ 奖励列表 """
        award_id = self.check_int(req.args.get('award_id'), require=False, p_name='奖励ID')
        name = self.check_str(req.args.get("name"), require=False, minlen=2, maxlen=10, p_name="奖励名称")
        award_type = self.check_int(req.args.get("type"), require=False, p_name="奖励类型")
        level = self.check_int(req.args.get("level"), require=False, p_name="奖励等级")
        page = self.check_int(req.args.get('page'), require=False, default=1, p_name='页码')
        page_size = self.check_int(req.args.get('page_size'), require=False, default=10, p_name='每页数量')
        data, msg = await AwardRC.get_award_by_filter(award_id=award_id, name=name, level=level, award_type=award_type,
                                                      page=page, page_size=page_size)
        return self.answer(data=data)

    async def put(self, req: Request):
        """ 编辑奖励 """
        award_id = self.check_int(req.json.get('award_id'), require=True, p_name='奖励ID')
        name = self.check_str(req.json.get("name"), require=False, minlen=2, maxlen=10, p_name="奖励名称")
        type = self.check_int(req.json.get("type"), require=False, p_name="奖励类型")
        level = self.check_int(req.json.get("level"), require=False, p_name="奖励等级")
        content = self.check_str(req.json.get("content"), require=False, p_name="奖励内容")
        sta, award = await AwardRC.update_award(award_id, name=name, type=type, level=level, content=content)
        if not sta:
            return self.answer(self.sta_code.FAIL, hint=award)
        return self.answer()


