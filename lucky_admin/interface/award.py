from sanic import Request
from lucky_admin.base_api import AdminAuthApi
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.model_rc.extra_club_event import ExtraClubEventRC
from lucky_game.model_rc.base_clubs import BaseClubRC


class Award(AdminAuthApi):
    async def post(self, req: Request, **kwargs):
        """ 创建奖励 """
        name = self.check_str(req.json.get("name"), require=True, minlen=2, maxlen=10, p_name="奖励名称")
        uid = self.check_int(req.json.get("uid"), require=True, p_name="馆主ID")
        room_card = self.check_int(req.json.get("room_card"), require=True, p_name="奖励基金")
        other = self.check_str(req.json.get("other"), require=True, p_name="其他信息")
        notice = self.check_str(req.json.get("notice"), require=True, p_name="公告")
        status = self.check_int(req.json.get("status"), require=True, p_name="状态")
        record_status = self.check_int(req.json.get("record_status"), require=True, p_name="战绩状态")
        check_sta, e = await BaseClubRC.check_club_name(name)
        if not check_sta:
            return self.answer(self.sta_code.FAIL, hint=e)
        new, e = await BaseClubRC.create_club(name, uid, room_card=room_card, other=other, notice=notice,
                                              status=status, record_status=record_status)
        if not new:
            return self.answer(self.sta_code.FAIL, hint=e)
        return self.answer(data={"club_id": new.id})

    async def get(self, req: Request):
        """ 奖励列表 """
        club_id = self.check_int(req.args.get('club_id'), require=False, p_name='奖励ID')
        uid = self.check_int(req.args.get('uid'), require=False, p_name='馆主ID(玩家ID)')
        status = self.check_int(req.args.get('status'), require=False, p_name='状态')
        page = self.check_int(req.args.get('page'), require=False, default=1, p_name='页码')
        page_size = self.check_int(req.args.get('page_size'), require=False, default=10, p_name='每页数量')
        sta, data = await BaseClubRC.get_club_filter(uid=uid, club_id=club_id, status=status, page=page, page_size=page_size)
        return self.answer(data=data)

    async def put(self, req: Request):
        """ 编辑奖励 """
        club_id = self.check_int(req.json.get('club_id'), require=True, p_name='奖励ID')
        name = self.check_str(req.json.get("name"), require=False, minlen=2, maxlen=10, p_name="奖励名称")
        room_card = self.check_int(req.json.get("room_card"), require=False, p_name="奖励基金")
        other = self.check_str(req.json.get("other"), require=False, p_name="其他信息")
        notice = self.check_str(req.json.get("notice"), require=False, p_name="公告")
        status = self.check_int(req.json.get("status"), require=False, p_name="状态")
        record_status = self.check_int(req.json.get("record_status"), require=False, p_name="战绩状态")
        club, msg = await BaseClubRC.get_club_by_id(club_id)
        if not club:
            return self.answer(self.sta_code.FAIL, hint=msg)
        data, msg = await BaseClubRC.update_club(club_id, name=name, other=other, notice=notice, status=status,
                                            room_card=room_card, record_status=record_status)
        if not data:
            return self.answer(self.sta_code.FAIL, hint=msg)
        return self.answer()

    async def delete(self, req: Request):
        """ 更新奖励信息 """
        club_id = self.check_int(req.json.get('club_id'), require=True, p_name='奖励ID')
        club, msg = await BaseClubRC.get_club_by_id(club_id)
        if not club:
            return self.answer(self.sta_code.FAIL, hint=msg)
        u_info = await BaseUserRC.cache_by_pk(club.get('uid'))
        sta, data = await BaseClubRC.delete_club(club_id, u_info)
        if not sta:
            return self.answer(self.sta_code.FAIL, hint="删除失败")
        return self.answer()
