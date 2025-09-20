"""
排位接口
"""
from nsanic.libs import tool_dt
from sanic import Request
from common.public.conf import R_UID_THRESHOLD
from common.public.enum_const import DbKey
from common.utils.utils import UtilsTool
from lucky_game.base_api import GameAuthApi
from tortoise.transactions import in_transaction
from lucky_game.handler.up_assets import StatFlow, UpAssets
from lucky_game.model_rc.base_robot import BaseRobotRC
from lucky_game.model_rc.base_skin import UserSkinRC
from lucky_game.model_rc.conf_json import ConfJsonRC
from nsanic.libs.tool import json_parse, json_encode
from common.proto.py_pb2.http_player_vault import PbGoods
from lucky_game.model_rc.base_ranking import ConfRankingRC, UserRankingRC, ConfSeasonRC
from lucky_game.const import ReasonCostDiamond, ReasonCostGold, SeasonStatus
from common.proto.py_pb2.http_match import PbUserRankingInfo, S2CRankingList, PbSeasonRankingConf, PbPlayerRankingInfo


class GetUserRankingInfo(GameAuthApi):
    """获取用户排位信息"""

    async def get(self, _: Request, **kwargs):
        # 1.获取当前赛季配置
        season_conf = await ConfSeasonRC.get_current_season()
        (not season_conf) and self.answer(self.sta_code.NOT_WITHIN_VALID_PERIOD, hint="赛季即将开放，敬请期待！")
        season_id = season_conf.get("season_id")

        # 2.获取当前排位配置
        ranking_conf = await ConfRankingRC.get_ranking_items(season_id)
        (not ranking_conf) and self.answer(self.sta_code.NO_CONFIGURATION, hint="排位配置数据不存在")

        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")

        # 3.获取用户排位数据
        ur_data = await UserRankingRC.cache_by_unique(uid, u_info=u_info) or {}
        u_ranking_id = ur_data.get("ranking_id") or 1
        cur_score = ur_data.get("cur_score") or 100
        top_score = ur_data.get("top_score") or 100
        old_level_achieved = ur_data.get("level_achieved")
        level_achieved = [] if not old_level_achieved else json_parse(old_level_achieved)

        ranking_data = {
            "ranking_id": u_ranking_id,
            "cur_score": cur_score,
            "top_score": top_score,
            "region": ur_data.get('region', 0),
            "game_count": ur_data.get('game_count', 0)
        }
        cur_ranking_conf = ConfRankingRC.get_ranking_data_by_score(ranking_conf, top_score)
        if cur_ranking_conf:
            ranking_data['top_ranking_id'] = cur_ranking_conf.get("id")
            ranking_data['top_level'] = cur_ranking_conf.get("level")

        # 4.寻找下一个等级
        next_ranking = None
        for r_conf in ranking_conf:
            if r_conf.get("id") > u_ranking_id and r_conf.get("min_score") > cur_score:
                next_ranking = r_conf
                break

        # 5.统计等级奖励状态
        all_level = [i.get('level') if i.get('level_awards') else None for i in ranking_conf]
        level_awards_sta = ConfJsonRC.stat_of_completion(ranking_data.get("top_level", 1), level_achieved, all_level)
        ranking_data['level_awards_sta'] = json_encode(level_awards_sta)

        # 6.获取赛季各奖励项
        return_data = {
            'self_ranking_data': ranking_data,  # 自己排位信息
            'next_ranking_id': next_ranking.get("id") if next_ranking else 0,  # 此处给id，客户端可在all_ranking_data中取到
            'all_ranking_data': ranking_conf  # 所有排位信息
        }
        proto_data = PbUserRankingInfo.pb_model(return_data)
        self.info_log(uid, "GetUserRankingInfo 获取排位配置 / 用户排位数据 成功")
        return self.answer(data=proto_data)


class GetSeasonRankingConf(GameAuthApi):
    """获取排位赛季配置"""

    async def get(self, _: Request, **kwargs):
        # 1.获取当前赛季配置
        season_conf = await ConfSeasonRC.get_current_season()
        (not season_conf) and self.answer(self.sta_code.NOT_WITHIN_VALID_PERIOD, hint="赛季即将开放，敬请期待！")
        season_id = season_conf.get("season_id")

        # 2.获取赛季各奖励项
        season_awards_items, _ = await ConfRankingRC.get_season_awards_items(season_id)
        (not season_awards_items) and self.answer(self.sta_code.NO_CONFIGURATION, hint="赛季奖励配置数据不存在")

        return_data = {
            'season_conf': season_conf,  # 赛季信息
            'season_awards_items': season_awards_items  # 赛季奖励（段位奖/结算奖）
        }
        proto_data = PbSeasonRankingConf.pb_model(return_data)
        self.info_log(f"GetSeasonRankingConf 获取S{season_id}赛季配置 成功")
        return self.answer(data=proto_data)


class RankingPullAwards(GameAuthApi):
    """
    排位赛领取奖励（等级奖）
    :ranking_id 段位ID
    """

    async def post(self, req: Request, **kwargs):
        # 1.获取当前赛季配置
        season_conf = await ConfSeasonRC.get_current_season()
        if not season_conf or season_conf.get("status") == SeasonStatus.NEXT_SEASON:
            self.answer(self.sta_code.NOT_WITHIN_VALID_PERIOD, hint="赛季即将开放，敬请期待！")
        season_id = season_conf.get("season_id")

        # 2.获取排位配置和验证配置id
        ranking_conf = await ConfRankingRC.get_ranking_items(season_id)
        (not ranking_conf) and self.answer(self.sta_code.NO_CONFIGURATION, hint="排位配置数据不存在")
        cur_ranking_id = self.check_int(req.json.get('ranking_id') or 0, require=True, p_name="req_ranking_id",
                                        minval=ranking_conf[0].get('id'),
                                        maxval=ranking_conf[-1].get('id')
                                        )

        # 3.用户排位数据
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")
        ur_data = await UserRankingRC.cache_by_unique(uid, u_info=u_info)
        (not ur_data or ur_data.get("default_cache")) and self.answer(self.sta_code.CONDITION_NOT_MET)

        # 4.找出玩家当前要领取的排位配置
        cur_ranking_conf = {}
        idx = UtilsTool.binary_search(ranking_conf, cur_ranking_id, "id")
        if isinstance(idx, int):
            cur_ranking_conf = ranking_conf[idx]
        cur_ranking_level = cur_ranking_conf.get('level') or 1

        # 5.通过玩家最高排位分找到达到过的最高段位id
        top_score = ur_data.get("top_score") or 0
        top_ranking_conf = ConfRankingRC.get_ranking_data_by_score(ranking_conf, top_score)
        top_ranking_level = top_ranking_conf.get("level") or 1
        # top_ranking_id = top_ranking_conf.get("id") or 0

        # 6.查询等级奖励状态
        old_level_achieved = ur_data.get("level_achieved")
        level_achieved = [] if not old_level_achieved else json_parse(old_level_achieved)
        (cur_ranking_level > top_ranking_level) and self.answer(self.sta_code.FAIL, hint='该排位等级还未达成，请继续加油吧')
        if level_achieved and cur_ranking_level in level_achieved:
            self.answer(self.sta_code.ALREADY_DO, hint='该排位等级奖励已经领取')

        # 7.计算可领取的所有等级奖励
        awards = []
        for r_conf in ranking_conf:
            r_level = r_conf.get("level")
            if r_level <= top_ranking_level:
                if level_achieved and r_level in level_achieved:
                    continue
                r_awards = r_conf.get("level_awards")
                if r_awards:
                    level_achieved.append(r_level)
                    awards.extend(r_awards)
        (not awards) and self.answer(self.sta_code.GOODS_NOT_FOUND, hint="排位赛等级奖励缺货，请联系客服")

        # 9.发奖/改写记录
        StatFlow.stat_common_flow(
            awards=awards,
            d_reason=ReasonCostDiamond.RANKING_LEVEL_AWARDS,
            g_reason=ReasonCostGold.RANKING_LEVEL_AWARDS
        )
        # 10.处理皮肤兑换
        for a in awards:
            await UserSkinRC.deal_hold_skin(uid, a)
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                pull_info = {"level_achieved": json_encode(level_achieved)}
                await UserRankingRC.update_user_ranking(uid, pull_info, ur_data)
                up_goods = await UpAssets.update_assets(uid, awards, [], is_pack=True)
        except Exception as e:
            self.error_log(f"RankingPullAwards 事务执行失败，原因：{e}")
            self.answer(code=self.sta_code.FAIL, hint="排位赛等级奖励领取失败，请联系客服")

        pro_data = PbGoods.pb_model(up_goods)
        self.info_log(uid, f"RankingPullAwards 排位赛等级奖励领奖 成功")
        return self.answer(data=pro_data)


class GetRankingList(GameAuthApi):
    """获取 地区/世界 排行榜"""

    async def get(self, req: Request, **kwargs):
        # 1.获取当前赛季配置
        season_conf = await ConfSeasonRC.get_current_season()
        (not season_conf) and self.answer(self.sta_code.NOT_WITHIN_VALID_PERIOD, hint="赛季即将开放，敬请期待！")
        season_id = season_conf.get("season_id")

        # 首次开始前1小时不该有排行
        if season_id == 1 and tool_dt.cur_time() - season_conf.get('start_time', 0) < 60 * 60:
            proto_data = S2CRankingList.pb_model()
            self.answer(data=proto_data)

        region = self.check_int(req.args.get("region") or 0, require=True, default=0, minval=0, maxval=34)
        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")

        # 2.世界/地区 排名
        ur_data = await UserRankingRC.cache_by_unique(uid, u_info=u_info)
        if region == 0:  # 世界榜
            data = await UserRankingRC.get_ranking_list(season_id)
        else:  # 地区榜
            data = await UserRankingRC.get_ranking_list_by_region(season_id, region)
            if ur_data.get("region") != region:  # 不属于该地区直接返回
                proto_data = S2CRankingList.pb_model(**{"ranking_list": data})
                self.answer(data=proto_data)

        return_data = {"ranking_list": data}
        # 3.自己的排名，判断是否上榜
        if data:
            cur_score = ur_data.get("cur_score", 0)
            if cur_score >= data[-1].get("cur_score"):  # todo:这里可能存在分数一样但自己未上榜的现象
                for idx, one_data in enumerate(data):
                    if one_data.get('uid') == uid:
                        return_data["self_ranking"] = idx + 1
                        break

        proto_data = S2CRankingList.pb_model(**return_data)
        self.info_log(uid, f"GetRankingList 获取 {region} 排行榜成功")
        self.answer(data=proto_data)


class ModifyUserRankingInfo(GameAuthApi):
    """ 更新用户排位信息（地区） """

    async def post(self, req: Request, **kwargs):
        region = self.check_int(req.json.get("region") or 0, require=True, default=0, minval=0, maxval=34)

        u_info = kwargs.get("u_info")
        uid = u_info.get("uid")

        ur_data = await UserRankingRC.cache_by_unique(uid, u_info=u_info)
        is_unrated = False
        if not ur_data or ur_data.get("default_cache"):
            is_unrated = True

        # 检查传入的 region 是否与当前的 region 相同
        cur_region = ur_data.get("region")
        if cur_region == region:
            return self.answer(hint='OK!')

        new_info = {"region": region}
        sta = await UserRankingRC.update_user_ranking(uid, new_info, ur_data, is_unrated=is_unrated)
        (not sta) and self.answer(self.sta_code.FAIL, hint='系统忙，请稍后重试！')

        self.info_log(uid, "ModifyUserRankingInfo suc:", sta)
        return self.answer(hint='OK!')


class GetPlayerRankingInfo(GameAuthApi):
    """
    批量获取玩家排位信息（游戏内）
    """

    async def get(self, req: Request, **kwargs):
        query_uid_list = req.args.get("query_uid_list")
        query_uid_list = json_parse(query_uid_list) if query_uid_list else []

        is_with_conf = self.check_int(
            req.args.get("is_with_conf", 0), require=True, default=0, p_name='is_with_conf')  # 是否带配置

        u_info = kwargs.get("u_info")
        if not query_uid_list:
            query_uid_list.append(u_info.get("uid", 0))

        for uid in query_uid_list:
            if not isinstance(uid, int):
                self.info_log(f"Invalid UID detected: {uid}, UIDs: {query_uid_list}")
                return self.answer(self.sta_code.ERR_ARG, hint=f"非法的用户ID: {uid}")

        # 1.获取当前赛季配置
        season_conf = await ConfSeasonRC.get_current_season()
        (not season_conf) and self.answer(self.sta_code.NOT_WITHIN_VALID_PERIOD, hint="赛季即将开放，敬请期待！")

        # 2.获取当前排位配置
        ranking_conf = await ConfRankingRC.get_ranking_items(season_conf.get("season_id"))
        (not ranking_conf) and self.answer(self.sta_code.NO_CONFIGURATION, hint="排位配置数据不存在")

        # 3.获取用户排位数据
        ranking_data = []
        for uid in query_uid_list:
            if uid > R_UID_THRESHOLD:  # 真人
                user_data = await UserRankingRC.cache_by_unique(uid, u_info=u_info) or {}
                cur_score = user_data.get("cur_score") or 100
                ranking_id = user_data.get("ranking_id") or 1

            else:  # 机器人
                robot_data = await BaseRobotRC.cache_by_pk(uid)
                cur_score = robot_data.get("r_score") or 1
                # 查找匹配的 ranking_id
                ranking_id = None
                cur_ranking_conf = ConfRankingRC.get_ranking_data_by_score(ranking_conf, cur_score)
                if cur_ranking_conf:
                    ranking_id = cur_ranking_conf.get("id")

            ranking_data.append({"uid": uid, "ranking_id": ranking_id, "cur_score": cur_score})

        return_data = {
            'season_conf': season_conf,  # 赛季信息
            'player_ranking_data': ranking_data,  # 排位信息（只含ID）
            'all_ranking_data': ranking_conf if is_with_conf else []  # 所有排位信息
        }
        proto_data = PbPlayerRankingInfo.pb_model(return_data)
        self.info_log("GetPlayerRankingInfo 批量获取玩家排位信息 成功", is_with_conf)
        return self.answer(data=proto_data)
