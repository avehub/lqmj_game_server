"""
赛季相关
"""
from nsanic.libs import tool_dt
from sanic import Request

from lucky_admin.base_api import AdminAuthApi
from lucky_game.const import SeasonStatus
from lucky_game.model_rc.base_ranking import ConfSeasonRC, ConfRankingRC, ConfRankingMatchTimeRc


class SeasonInfoHandler(AdminAuthApi):
    """ 处理赛季信息添加赛季 """

    async def get(self, _a: Request, **_b):
        """ 获取未过期的赛季 """
        data = await ConfSeasonRC.db_model.filter(status__not=SeasonStatus.OUT_OF_TIME).values()
        self.answer(data=data)

    @staticmethod
    async def reuse_last_ranking(last_season_id: int, add_season_id):
        """ 复用上一个赛季的修为 """
        data_list = await ConfRankingRC.get_ranking_items(last_season_id)
        if not data_list:
            return False
        model_list = []
        for one_data in data_list:
            one_data['season_id'] = add_season_id
            one_data.pop('id', None)
            model_list.append(ConfRankingRC.db_model(**one_data))

        return await ConfRankingRC.db_model.bulk_create(model_list)

    def __verify_season(self, req: Request):
        season_desc = req.json.get("season_desc")
        self.check_str(season_desc, require=True, p_name="season_desc")
        cur_time = tool_dt.cur_time()

        start_time = req.json.get("start_time")
        self.check_int(start_time, require=True, minval=cur_time, p_name="start_time")

        end_time = req.json.get("end_time")
        self.check_int(end_time, require=True, minval=start_time, p_name="end_time")

        off_season_time = req.json.get("off_season_time") or 60 * 60 * 4
        self.check_int(off_season_time, require=True, minval=60 * 60 * 4, p_name="off_season_time")

        # off_season_time = off_season_time // 2
        condition = req.json.get("condition") or 30
        self.check_int(condition, require=True, minval=0, p_name="condition")
        return season_desc, start_time, end_time, off_season_time, condition

    async def post(self, req: Request, **_):
        """ 添加赛季 """
        season_desc, start_time, end_time, off_season_time, condition = self.__verify_season(req)
        is_reuse_last_ranking = req.json.get('is_reuse_last_ranking') or True

        data = {
            "season_desc": season_desc,
            "start_time": start_time,
            "end_time": end_time,
            "off_season_time": off_season_time,
            "condition": condition,
            "status": SeasonStatus.NEXT_SEASON
        }

        sta, msg = await ConfSeasonRC.add_season(**data)
        if sta:
            last_season_id = msg.season_id if msg else 0
            if is_reuse_last_ranking and last_season_id:
                await self.reuse_last_ranking(last_season_id, sta.season_id)
            self.answer(hint='添加成功！')
        self.answer(self.sta_code.FAIL, hint=msg)

    async def put(self, req: Request, **_):
        season_id = req.json.get('season_id')
        self.check_int(season_id, require=True, minval=1, p_name='season_id')
        sea_info = await ConfSeasonRC.db_model.get_by_dict({'season_id': season_id}, limit=1)
        not sea_info and self.answer(code=self.sta_code.FAIL, hint="赛季不存在！")
        if sea_info.get('status') == SeasonStatus.ACTIVE_SEASON:
            self.answer(code=self.sta_code.FAIL, hint="赛季进行中，不能修改！")
        season_desc, start_time, end_time, off_season_time, condition = self.__verify_season(req)
        data = {
            "season_desc": season_desc,
            "start_time": start_time,
            "end_time": end_time,
            "off_season_time": off_season_time,
            "condition": condition,
        }
        await ConfSeasonRC.db_model.update_by_pk(season_id, data)
        self.answer(hint="ok")


class SeasonRankingHandler(AdminAuthApi):
    """ 赛季修为处理 """

    async def get(self, req: Request, **_b):
        """ 获取赛季修为信息 """
        season_id = req.args.get("season_id") or ""
        if season_id and season_id.isdigit():
            season_id = int(season_id)
        else:
            season = await ConfSeasonRC.get_current_season()
            if not season:
                self.answer(code=self.sta_code.FAIL, hint="没有赛季信息")
            season_id = season.get('season_id')

        data_list = await ConfRankingRC.get_ranking_items(season_id)
        matching_time = await ConfRankingMatchTimeRc.cache_all_ranking_match_time(season_id)
        data = {
            "ranking_list": data_list,
            "matching_time": matching_time,
        }
        self.answer(data=data)

    async def put(self, req: Request, **_b):
        """ 添加新赛季（暂时未用） """
        season_id = req.json.get('season_id')
        data_list = await ConfRankingRC.get_ranking_items(season_id)
        if data_list:
            self.answer(code=self.sta_code.FAIL, data='赛季修为数据已存在，无须重复添加')
        data_list = req.json.get('ranking_list')
        if not data_list and not isinstance(data_list, list):
            self.answer(code=self.sta_code.FAIL, data='赛季数据错误，请检查！')
        data_list.sort(key=lambda x: x['level'])
        for i in range(len(data_list) - 1):
            next_level_min_score = data_list[i + 1].get('min_score')
            last_level_min_score = data_list[i].get('max_score')
            if next_level_min_score - last_level_min_score != 1:
                self.answer(code=self.sta_code.FAIL, hint='修为等级最高分与最低分有重叠，请检查')

        try:
            await ConfRankingRC.db_model.bulk_create(data_list)
        except Exception as e:
            self.error_log(f'创建失败：{e}')
            self.answer(code=self.sta_code.FAIL, hint="创建失败")

    async def post(self, req: Request, **_b):
        """ 部分修改 """
        season_id = req.json.get("season_id")
        self.check_int(season_id, require=True, minval=0, p_name="season_id")
        season_data = await ConfSeasonRC.db_model.filter(season_id=season_id).first()
        not season_data and self.answer(hint='赛季信息不存在！')
        # if season_data.status != SeasonStatus.NEXT_SEASON:
        #     self.answer(hint='只能修改还未开始的赛季修为配置！')

        id_ = req.json.get("id")
        self.check_int(id_, require=True, minval=0, p_name="id")
        rank_data = await ConfRankingRC.db_model.filter(id=id_).first()
        not rank_data and self.answer(hint='修为配置不存在！')

        if rank_data.season_id != season_id:
            self.answer(hint='赛季id与当前修改的修为配置对应的赛季id不匹配！')
        update_data = req.json.get('update_data')
        not update_data and self.answer(hint='没有修改任何信息！')

        if rank_data.level == 1:  # 等级1不配奖励
            update_data["display_awards"] = None
            update_data["season_awards"] = None
            update_data["level_awards"] = None

        for reward in update_data.get("display_awards") or []:
            if not isinstance(reward.get("goods_count"), int):
                self.answer(code=self.sta_code.FAIL, hint='显示奖励goods_count应为整型，请检查')

        for reward in update_data.get("season_awards") or []:
            if not isinstance(reward.get("goods_count"), int):
                self.answer(code=self.sta_code.FAIL, hint='赛季奖励goods_count应为整型，请检查')

        for reward in update_data.get("level_awards") or []:
            if not isinstance(reward.get("goods_count"), int):
                self.answer(code=self.sta_code.FAIL, hint='段位奖励goods_count应为整型，请检查')

        sta = await ConfRankingRC.db_model.update_by_pk(id_, update_data)
        if sta:
            key = f'{ConfRankingRC.tb_name}:{season_id}'
            update_data['season_id'] = season_id
            update_data['id'] = id_
            await self.conf.rds.set_hash(key, id_, update_data)
            self.answer(hint='更新成功！')
        self.answer(hint='更新失败！')
