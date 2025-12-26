from sanic import Request

from common.public.enum_const import StaCode
from lucky_admin.base_api import AdminAuthApi
from common.model_rc.tournament_template import TournamentTemplateRC
from lucky_game.model_rc.game_rooms import GameRoomsRC
from lucky_game.model_rc.base_clubs import BaseClubRC


class TournamentTemplate(AdminAuthApi):
    async def get(self, req: Request):
        """ 获取模板列表 """
        page = self.check_int(req.args.get('page'), require=False, default=1, p_name='页码')
        page_size = self.check_int(req.args.get('page_size'), require=False, default=10, p_name='每页数量')
        sta, data = await TournamentTemplateRC.get_template_filter(page=page, page_size=page_size)
        return self.answer(data=data)

    async def post(self, req: Request):
        """ 创建模板 """
        template_name = self.check_str(req.json.get('template_name'), require=True, p_name='模板名称')
        template_type = self.check_int(req.json.get('template_type'), require=True, p_name='模板类型')
        cycle_type = self.check_int(req.json.get('cycle_type'), require=True, p_name='周期类型')
        rounds_per_cycle = self.check_int(req.json.get('rounds_per_cycle'), require=True,p_name='每周期场次')
        online_rounds = self.check_int(req.json.get('online_rounds'), require=True, p_name='线上场次数')
        final_round_offline = self.check_int(req.json.get('final_round_offline'), require=True, p_name='总决赛是否线下')
        qualifier_count = self.check_int(req.json.get('qualifier_count'), require=True, p_name='晋级总决赛人数')
        status = self.check_int(req.json.get('status'), require=False, default=1, p_name='模板状态')
        sta, data = await TournamentTemplateRC.add_template(template_name=template_name, template_type=template_type,
                                                            cycle_type=cycle_type, rounds_per_cycle=rounds_per_cycle,
                                                            online_rounds=online_rounds, final_round_offline=final_round_offline,
                                                            qualifier_count=qualifier_count, status=status)
        if not sta:
            return self.answer(code=StaCode.FAIL, hint=data)
        return self.answer(data=data)

    async def put(self, req: Request):
        """ 更新模板 """
        template_id = self.check_int(req.json.get('template_id'), require=True, p_name='模板ID')
        template_name = self.check_str(req.json.get('template_name'), require=False, p_name='模板名称')
        template_type = self.check_int(req.json.get('template_type'), require=False, p_name='模板类型')
        cycle_type = self.check_int(req.json.get('cycle_type'), require=False, p_name='周期类型')
        rounds_per_cycle = self.check_int(req.json.get('rounds_per_cycle'), require=False,p_name='每周期场次')
        online_rounds = self.check_int(req.json.get('online_rounds'), require=False, p_name='线上场次数')
        final_round_offline = self.check_int(req.json.get('final_round_offline'), require=False, p_name='总决赛是否线下')
        qualifier_count = self.check_int(req.json.get('qualifier_count'), require=False, p_name='晋级总决赛人数')
        status = self.check_int(req.json.get('status'), require=False, p_name='模板状态')
        up_data = {}
        if template_name is not None:
            up_data['template_name'] = template_name
        if template_type is not None:
            up_data['template_type'] = template_type
        if cycle_type is not None:
            up_data['cycle_type'] = cycle_type
        if rounds_per_cycle is not None:
            up_data['rounds_per_cycle'] = rounds_per_cycle
        if online_rounds is not None:
            up_data['online_rounds'] = online_rounds
        if final_round_offline is not None:
            up_data['final_round_offline'] = final_round_offline
        if qualifier_count is not None:
            up_data['qualifier_count'] = qualifier_count
        if status is not None:
            up_data['status'] = status
        sta, data = await TournamentTemplateRC.update_template(template_id, up_data)

        if not sta:
            return self.answer(code=StaCode.FAIL, hint=data)
        return self.answer(data=data)

    async def delete(self, req: Request):
        """ 删除模板 """
        template_id = self.check_int(req.json.get('template_id'), require=True, p_name='模板ID')
        sta, msg = await TournamentTemplateRC.del_template(template_id)
        if not sta:
            return self.answer(code=StaCode.FAIL, hint=msg)
        return self.answer(hint=msg)
