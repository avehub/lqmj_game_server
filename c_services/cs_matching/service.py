import asyncio
import random
from datetime import datetime
from typing import Dict
from nsanic.libs import tool_dt, tool
from nsanic.verify import vint

from common.proto.py_pb2.common import s2c_in_service_model
from common.proto.py_pb2.ws_c2s import C2SEnterLeisure
from common.utils.utils import UtilsTool
from lucky_game.const import SeasonStatus
# from lucky_game.model_rc.base_activity import UserActivityRC
# from lucky_game.model_rc.base_bag import UserBagRC
# from lucky_game.model_rc.base_prop import ItemsPropRC
# from lucky_game.model_rc.base_ranking import ConfRankingMatchTimeRc, ConfSeasonRC, UserRankingRC, ConfRankingRC
# from lucky_game.model_rc.base_skin import UserSkinRC, ItemsSkinRC
from lucky_game.model_rc.base_robot import BaseRobotRC
from lucky_game.model_rc.base_user import BaseUserRC
from common.utils.kit_async import DelayCall, delay_func
from c_services.const.cs_enum_const import CmdMatch, CmdRoom
from common.public.enum_const import ServiceEnum, StaCode, GameType, CacheKey
from common.public.conf import LIVE_SERVER, ROBOT_BATTLE, R_UID_THRESHOLD
from common.utils.kit_dt import KitDt
from c_services.cs_matching.const import MatchingMode
# from lucky_game.model_rc.player_game_times import PlayerGameTimesRC
# from lucky_game.model_rc.vip_level import UserVipRC, ConfVipRC
from c_services.cs_matching.player import Player
from c_services.cs_matching.session import Session
from typing import Iterable
from c_services.base.base_leisure_service import LeisureService
from c_services.base.base_server import BaseServer
from lucky_game.model_rc.conf_json import ConfJsonRC


class MatchServer(BaseServer, LeisureService):
    """
    匹配服务(作为中转，匹配前的所有计算在该服务完成)
    包括：等待匹配、匹配中、匹配完成、离开匹配
    """
    enable_rpc = False
    SUBSCRIBE_FANOUT = None


    def __init__(self):
        BaseServer.__init__(self)
        LeisureService.__init__(self)
        self.__secret = r"eFSvMBklwiWoVbv85KzPjEM_jjHJ7d-TIishQaGlR8w"
        self.__max_wait: int = 5 if LIVE_SERVER else 0  # 最大等待时常
        self.__wait_session: Dict[str, Session] = {}
        self.__players_map = {}
        self.__forbid_match_set: Dict[int, str] = {}
        self.__timer = None
        self.__all_robot = []
        self.__robot_cursor = 0
        self.__robot_count = 0
        self.__platform = 0

        self.__matching_mode = MatchingMode.RAND_TIME
        self.__match_search_extension_time: Dict[int, Dict[str, int]] = {}  # 赛季搜索扩展时间
        DelayCall(0.5, self.__init_data).start()
        DelayCall(2, self.__loop_match_by_type).loop_start()
        self.add_handlers({
            CmdMatch.MATCH_LEISURE.val: self.__rev_match_leisure,
            CmdMatch.QUIT_MATCH.val: self.__quit_match,
            CmdMatch.ADD_FORBID_SERVICE.val: self.__add_forbid_match,
            CmdMatch.RM_FORBID_SERVICE.val: self.__rm_forbid_match,
        })

    async def test_rpc(self):
        req_data = {"cs_type": self.service_type, "secret": self.conf.SECRET_KEY}
        print("开始测试请求")
        import time
        s = time.time()
        res = await self.req_by_rpc(ServiceEnum.C_MONSTER, CmdRoom.QUERY_PLAYER_IN_SERVICE, 123, req_data)
        print("请求结果", res, "耗时：", time.time() - s)

    @property
    def match_search_extension_time(self):
        return self.__match_search_extension_time

    def __rm_player(self, uid):
        self.__players_map.pop(uid, None)

    async def __create_session(self, cs_type, level, play_type=1):
        """ 创建场次对象 """
        data = await self.leisure_conf(cs_type, play_type)
        if not data:
            return
        level_conf = data[int(level) - 1]
        session = Session(self, cs_type, level, level_conf)

        self.__wait_session[f"{cs_type}_{play_type}_{level}"] = session
        return session

    async def __get_session(self, cs_type, level, play_type=1):
        return self.__wait_session.get(f"{cs_type}_{play_type}_{level}") or \
                await self.__create_session(cs_type, level, play_type)

    def call_flow(self, seconds, func, *params, **kwargs):
        """ 正常延时 """
        if self.__timer:
            self.__timer.cancel()
            self.__timer = None
        self.__timer = DelayCall(seconds, func, *params, **kwargs, log_handler=self.log_err)
        self.__timer.start()

    async def __init_data(self):
        """ 初始化数据 """
        # 读取机器人数据
        await self.__read_robot_data()
        # 读取匹配扩展时间
        # await self.__read_rank_info()

    @UtilsTool.cal_time()
    async def __read_robot_data(self):
        """ 读取机器人数据 """
        # self.__all_robot = await BaseRobotRC.cache_all_robot()
        # 此处改为100001 - 120000为战斗机器人（但目前该阶段只有2100个机器人）
        start_ruid = ROBOT_BATTLE[0] + 1
        end_ruid = start_ruid + 2100
        r_list = list(range(start_ruid, end_ruid))
        self.__all_robot = await BaseRobotRC.cache_part_robot(r_list)
        self.__robot_count = len(self.__all_robot)
        random.shuffle(self.__all_robot)

    async def __rand_robot_data(self) -> dict:
        """ 随机一个机器人数据 """
        if not self.__all_robot:
            await self.__read_robot_data()
        one_robot = self.__all_robot[self.__robot_cursor]
        if self.__robot_cursor == self.__robot_count - 1:
            # 当取到 最后一个 机器人 时游标置为0 且 打乱机器人列表
            self.__robot_cursor = 0
            random.shuffle(self.__all_robot)
        else:
            self.__robot_cursor += 1

        return {"uid": one_robot.get("uid"), "is_robot": 1}

    # async def __read_rank_info(self):
    #     """ 读取排位信息 """
    #     season_conf = await ConfSeasonRC.get_current_season()
    #     if not season_conf:
    #         print("没有赛季信息")
    #         return
    #     self.__match_search_extension_time = await ConfRankingMatchTimeRc.cache_all_ranking_match_time(
    #         season_conf.get("season_id"))

    def __add_wait_player(self, session, p: Player):
        old_p = self.__players_map.get(p.uid)
        if old_p:
            del p
            self.log_info('重复匹配拦截！')
            return
        p.enter_time = tool_dt.cur_time()
        self.__players_map[p.uid] = p
        session.add_wait_player(p, self.__matching_mode)

    async def __loop_match_by_type(self):
        """ 通过段位匹配 """
        for _, session in self.__wait_session.items():
            cs_type, level = session.cs_type, session.level
            cs_enum = ServiceEnum.find_member_by_val(cs_type)
            max_player = session.player_num

            if self.__matching_mode == MatchingMode.COMMON:
                comb_players = session.match_players_common(self.__max_wait)
            elif self.__matching_mode == MatchingMode.RAND_TIME:
                comb_players = session.match_players_rand_time()
            else:
                comb_players = session.match_players_by_rank()

            for players in comb_players:
                all_uid_list = [p.uid for p in players]
                ing_player_list = [p.user_data() for p in players]
                if len(players) != max_player:
                    r_data_list = [await self.__rand_robot_data() for _ in range(max_player - len(players))]
                    all_uid_list.extend([rd.get("uid") for rd in r_data_list])
                    ing_player_list.extend(r_data_list)

                await self.__notify_match_succeed(cs_type, players, all_uid_list)
                # todo: 发送到目标子服务
                await self.__notify_cs_before(cs_enum, ing_player_list, session)

    async def __notify_match_succeed(self, cs_type, player_list: Iterable[Player], all_uid_list: list):
        """
        通知玩家匹配成功
        all_uid_list: 匹配完成的同房间uid
        """
        self.log_info("匹配成功：", all_uid_list)
        data_model = s2c_in_service_model(cs_type=cs_type, uid_list=all_uid_list)
        send_task = []
        for player in player_list:
            send_task.append(self.cs2ws_by_rmq(CmdMatch.MATCH_SUC, player.uid, StaCode.PASS, "ok", data_model))
        if send_task:
            await asyncio.gather(*send_task)

    async def __notify_cs_before(self, cs_enum, ing_player_list, session: Session):
        """ 通知子游戏之前 """
        # await self.__init_skin_info_batch(cs_enum, ing_player_list, session.level)
        await delay_func(2, self.__notify_cs_match_succeed, cs_enum, ing_player_list, session)

    async def __notify_cs_match_succeed(self, cs_enum, ing_player_list, session):
        """ 通知子游戏匹配成功 """
        season = {} #await ConfSeasonRC.get_current_season() or {}
        season_status = season.get("status") or SeasonStatus.OFF_SEASON
        data = {
            "u_list": ing_player_list,
            "level": session.level,
            "pt": session.play_type,
            "platform": self.__platform,
            "secret": self.conf.SECRET_KEY,
            # 房间信息（类似于开房选项）
            "extra_room_info": {
                # 排行榜信息
                "ranking_info": {
                    "season_status": season_status
                }
            }
        }
        for p_info in ing_player_list:
            uid = p_info.get('uid')
            if uid > R_UID_THRESHOLD:
                self.__rm_player(uid)
        await self.cs2cs_by_rmq(cs_enum, CmdRoom.NEW_MATCH, msg=data)

    async def __rev_match_leisure(self, uid, data):
        """ 收到匹配休闲场 """
        parse_data = C2SEnterLeisure.decode(data)
        cs_type = parse_data.data.cs_type
        req_id = parse_data.req_id
        self.__platform = parse_data.platform
        info = await self.get_player_in_service(uid)
        cmd = CmdMatch.MATCH_LEISURE
        if info:
            tid = info.get("tid") or 0
            cs_type = info.get("cs_type") or 0
            timestamp = info.get("timestamp") or 0
            data_model = s2c_in_service_model(tid=tid, cs_type=cs_type, timestamp=timestamp)
            return await self.cs2ws_by_rmq(cmd, uid, StaCode.ALREADY_IN_SERVICE, msg=data_model, req_id=req_id)

        conf = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_ROOM_STOP)
        if conf and conf.get("status"):
            hint = "游戏玩法正在维护，喝杯茶，休息一下!"
            return await self.cs2ws_by_rmq(cmd, uid, StaCode.FORBID, hint, req_id=req_id)

        match_info = await self.conf.rds.get_hash(CacheKey.IN_MATCH, uid, jsparse=True)
        if match_info:
            hint = "您已在比赛匹配中"
            return await self.cs2ws_by_rmq(cmd, uid, StaCode.FORBID, hint, req_id=req_id)

        forbid_str = self.__forbid_match_set.get(cs_type) or ""
        if forbid_str:
            hint = f'亲爱的玩家，该游戏正维护, 预计：{forbid_str}开放，敬请谅解！'
            return await self.cs2ws_by_rmq(cmd, uid, StaCode.FORBID, hint, req_id=req_id)

        play_type = parse_data.data.play_type or 1
        if self.__players_map.get(uid):
            p = self.__players_map.get(uid)
            cs_type, play_type, level_id = p.s_key.split('_')
            cs_type, play_type, level_id = int(cs_type), int(play_type), int(level_id)
            session = await self.__get_session(cs_type, level_id, play_type)
            self.log_info("重复匹配", p.uid, p.enter_time, p.s_key, session.players_ranking_pool)
            return await self.cs2ws_by_rmq(cmd, uid, StaCode.ALREADY_DO, hint='已在匹配中，请勿重复操作', req_id=req_id)

        cs_enum = ServiceEnum.find_member_by_val(cs_type)
        # 1.检测是否有该服务以及是否为休闲场
        if not cs_enum:
            return await self.cs2ws_by_rmq(cmd, uid, StaCode.ERR_ARG, 'c_type error', req_id=req_id)
        if cs_enum.desc != GameType.LEISURE:
            return await self.cs2ws_by_rmq(
                cmd, uid, StaCode.FAIL, 'The game genre is not a leisure', req_id=req_id)

        data = await self.leisure_conf(cs_type, play_type)
        if not data:
            return await self.cs2ws_by_rmq(
                cmd, uid, StaCode.FAIL, 'This leisure field is not configured', req_id=req_id)
        level = parse_data.data.level
        if level:
            flag, val = vint(level, minval=1, maxval=len(data))
            if not flag:
                return await self.cs2ws_by_rmq(cmd, uid, StaCode.FAIL, 'Wrong level', req_id=req_id)
        user_info = await BaseUserRC.cache_by_uid(uid)
        if not user_info:
            return await self.cs2ws_by_rmq(cmd, uid, StaCode.FAIL, "illegal user", req_id=req_id)

        # ranking_conf, free_loss = await self.__get_ranking_info(uid)


        # bag_id_list = parse_data.data.bag_id_list
        # if bag_id_list:
        #     level_id, hint, prop_info = await self.__check_session_by_use_prop(
        #         uid, user_info.get("gold"), data, level, bag_id_list, free_loss)
        #     if not level_id:
        #         return await self.cs2ws_by_rmq(cmd, uid, StaCode.FAIL, hint, req_id=req_id)
        #     p = Player(uid)
        #     p.init_prop_info(prop_info)
        # else:
        level_id = await self.__find_suitable_leisure(level, user_info.get("gold"), cs_type, play_type)
        if not level_id:
            return await self.cs2ws_by_rmq(cmd, uid, StaCode.GOLD_NOT_ENOUGH, req_id=req_id)
        p = Player(uid)

        # 初始化修为信息
        # await self.__init_ranking_info(p, ranking_conf, cs_type, play_type)

        # 将玩家保存到匹配队列
        session = await self.__get_session(cs_type, level_id, play_type)
        self.__add_wait_player(session, p)
        await self.cs2ws_by_rmq(cmd, uid, StaCode.PASS, 'ok', req_id=req_id)

    async def __find_suitable_leisure(self, level_id, take_gold: int, target_cs, play_type=1) -> int:
        """ 寻找合适的休闲场 """
        data = await self.leisure_conf(target_cs, play_type)
        target_info = data[level_id - 1]
        if (target_info.get("min_take") <= take_gold and
                (target_info.get("max_take") == -1 or take_gold <= target_info.get("max_take"))):
            return target_info.get("level")
        for info in reversed(data):
            min_take = info.get("min_take")
            max_take = info.get("max_take")
            if min_take <= take_gold and (max_take == -1 or take_gold <= max_take):
                return info.get("level")
        return 0

    # @staticmethod
    # async def __check_session_by_use_prop(
    #         uid,
    #         take_gold,
    #         data,
    #         level,
    #         bag_id_list: list,
    #         rank_free_loss: bool
    # ):
    #     """ 根据道具匹配合适场次 """
    #     # 1.查询玩家道具
    #     bag_item_list = await UserBagRC.cache_user_bag(uid) or []
    #     goods_id_list = []
    #     for bag_info in bag_item_list:
    #         if bag_info.get(UserBagRC.KEY_GOODS_ID) in set(bag_id_list):
    #             if bag_info.get("goods_count", 0) <= 0:
    #                 g_name = "相关道具"
    #                 return 0, f"您不具备{g_name}, 请检查！", None
    #             goods_id_list.append(bag_info.get(UserBagRC.KEY_GOODS_ID))
    #
    #     if not goods_id_list:
    #         return 0, "道具选择有误！", None
    #
    #     prop_item_list = await ItemsPropRC.get_goods_item_by_id_list(goods_id_list)
    #     prop_info = {}
    #     match_position = [0, 0]  # 护盾卡、翻倍卡
    #
    #     target_info = data[level - 1]
    #     for i, prop_item in enumerate(prop_item_list):
    #         if not prop_item:
    #             return 0, f"道具配置不存在, goods_id: {goods_id_list[i]}", None
    #         target_level = prop_item.get("target_data", {}).get("level") or 0
    #         # if level_id != level:
    #         if target_level and target_level != level:  # 这里调整主要为了翻倍卡后来调整不区分场次了2024/11/25
    #             return 0, f"道具使用场次与不符", None
    #
    #         match prop_item.get("game_prop_type"):
    #             # 2025/4/15护盾卡 翻倍卡暂时取消
    #             # 护盾卡：只判断金币是否超过准入上限，不判断玩家金币>=门槛
    #             # case GamePropType.SHIELD_CARD:
    #             #     if target_info.get("max_take") != -1 and target_info.get("max_take") < take_gold:
    #             #         return 0, "您的金币超过了该场次的最高携带，请选择更高场次吧~", None
    #             #     prop_info["free_loss"] = 1  # 免输
    #             #     prop_info.setdefault("prop_id_list", []).append(prop_item.get("goods_id"))
    #             #     match_position[0] = 1
    #             # case GamePropType.MULTIPLIER_CARD:
    #             #     # 翻倍卡：需要判断是否满足勾选翻倍卡适配的场次
    #             #     prop_info["checkout_multiple"] = prop_item.get("extra_info", {}).get("multiple") or 1
    #             #     prop_info.setdefault("prop_id_list", []).append(prop_item.get("goods_id"))
    #             case GamePropType.PROTECT_SCORE_CARD:
    #                 # 固元丹(保段卡)
    #                 if not rank_free_loss:
    #                     prop_info["ranking_score_free_loss"] = 1
    #                     prop_info.setdefault("prop_id_list", []).append(prop_item.get("goods_id"))
    #             case GamePropType.BOOST_SCORE_CARD:
    #                 # 聚气丹（加修卡）
    #                 prop_info["ranking_addition"] = prop_item.get("extra_info", {}).get("ranking_addition") or 0
    #                 prop_info.setdefault("prop_id_list", []).append(prop_item.get("goods_id"))
    #
    #     # 翻倍卡不适配当前场次（优先护盾卡）
    #     # if match_position[0] == 0 and match_position[1] == -1:  # 这里调整主要为了翻倍卡后来调整不区分场次了2024/11/25
    #     if match_position[0] == 0:
    #         # 如果没有护盾卡时，需要严格判断的场次条件
    #         if (target_info.get("min_take") > take_gold or
    #                 (target_info.get("max_take") != -1 and take_gold > target_info.get("max_take"))):
    #             return 0, "您的金币不满足当前场次，请选择合适的场次吧~", None
    #
    #     return level, '', prop_info

    # @staticmethod
    # async def __init_skin_info_batch(cs_type, player_list: List[Dict], level):
    #     """ 初始化当前所有人的皮肤装备 """
    #     uid_list = [p.get("uid") for p in player_list]
    #     # todo: 临时调整鏖战模式用单局模式查询（解决好之后删除下面这行 ⬇ ）
    #     cs_type = ServiceEnum.C_MONSTER.val if cs_type == ServiceEnum.C_MONSTER_MANY else cs_type
    #     skin_info = await UserSkinRC.get_batch_user_used_skin(uid_list, cs_type, level)
    #     for i, uid in enumerate(uid_list):
    #         s_info = skin_info.get(uid)
    #         if s_info:
    #             skin_map = {}
    #             for s_conf in s_info:
    #                 match_card = s_conf.get("match_card")
    #                 skin_map[str(match_card)] = {
    #                     "skin_id": s_conf.get("skin_item_id"),
    #                     "skin_addition": s_conf.get("skin_addition"),
    #                     "sr_addition": s_conf.get("sr_addition"),
    #                 }
    #             player_list[i]["skin_equip_info"] = skin_map

    # @staticmethod
    # async def __get_ranking_info(uid):
    #     season_conf = await ConfSeasonRC.get_current_season() or {}
    #     season_id = season_conf.get("season_id") or 1
    #     ranking_conf = await ConfRankingRC.get_ranking_items(season_id)
    #     ur_data = await UserRankingRC.cache_by_unique(uid)
    #
    #     cur_ranking_conf = {}
    #     idx = UtilsTool.binary_search(ranking_conf, ur_data.get("ranking_id"), "id")
    #     if isinstance(idx, int):
    #         cur_ranking_conf = ranking_conf[idx]
    #
    #     lv_defend = cur_ranking_conf.get("lv_defend")
    #     # 判断玩家当前修为分是否是免输
    #     free_loss = False
    #     if lv_defend == LvDefendType.DEFEND_WHOLE:
    #         free_loss = True
    #     elif lv_defend == LvDefendType.DEFEND_FLOOR and \
    #             ur_data.get("cur_score") <= cur_ranking_conf.get("min_score", 0):
    #         free_loss = True
    #
    #     return cur_ranking_conf, free_loss

    # @staticmethod
    # async def __init_ranking_info(p: Player, cur_ranking_conf, cs_type, play_type=1):
    #     """ 初始用户排位信息 """
    #     p.ranking_level = cur_ranking_conf.get("level") or 1
    #     p.ranking_defend = cur_ranking_conf.get("lv_defend") or 0
    #     p.set_ranking_game_score(cur_ranking_conf, cs_type)
    #     _, p_game_info = await PlayerGameTimesRC.get_game_time_info(p.uid, cs_type, play_type)  # 连胜
    #     p.win_streak = p_game_info.get("curr_win_streak") or 0
    #     await MatchServer.__init_privilege_info(p)  # 特权信息

    # @staticmethod
    # async def __init_privilege_info(p):
    #     # vip加成
    #     vip_info = await UserVipRC.get_vip_conf_by_uid(p.uid)
    #     vip_r_addition = vip_info.get("ranking_addition") or 0
    #     p.ranking_addition_vip = vip_r_addition
    #     # 终生卡加成
    #     lifetime_card_info = await UserActivityRC.check_top_lifetime_card(p.uid)
    #     lifetime_card_r_addition = lifetime_card_info.get("ranking_addition") or 0
    #     p.ranking_addition_lifetime_card = lifetime_card_r_addition

    async def __quit_match(self, uid, data):
        """ 离开匹配 """
        parse_data = C2SEnterLeisure.decode(data)
        req_id = parse_data.req_id
        cmd = CmdMatch.QUIT_MATCH
        player = self.__players_map.get(uid)
        if not player:
            return await self.cs2ws_by_rmq(cmd, uid, StaCode.NO_PLAYER_INFO, '取消失败，请稍后再试~', req_id=req_id)
        session = self.__wait_session.get(player.s_key)
        if not session:
            return await self.cs2ws_by_rmq(cmd, uid, StaCode.FAIL, '取消失败，请稍后再试~', req_id=req_id)
        session.rm_wait_player(player, self.__matching_mode)
        self.__rm_player(uid)
        self.log_info(uid, "取消匹配成功！")
        return await self.cs2ws_by_rmq(cmd, uid, StaCode.PASS, 'ok', req_id=req_id)

    def __add_forbid_match(self, _, data):
        """ 增加禁止匹配：针对整个服务 """
        data = tool.json_parse(data, self.log_err)
        secret = data.get("secret") or ""
        if secret != self.__secret:
            return
        time_str = data.get("time_str") or ""
        time_obj = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        exp_timestamp = time_obj.timestamp()
        seconds = exp_timestamp - tool_dt.cur_time()
        if seconds < 0:
            return
        cs_type = data.get("cs_type")
        cs_enum = ServiceEnum.find_member_by_val(cs_type)
        if not isinstance(cs_enum, ServiceEnum):
            return
        exp_str = KitDt.timestamp_2_time_str(exp_timestamp)
        self.log_info(f"增加禁止匹配服务：{cs_enum}, 直到：{exp_str}", )
        self.__forbid_match_set[cs_type] = exp_str
        self.call_flow(seconds, self.__rm_forbid_match, 0, {"cs_type": cs_type})

    def __rm_forbid_match(self, _, data):
        """ 移除禁止匹配：针对整个服务 """
        cs_type = data.get("cs_type")
        cs_enum = ServiceEnum.find_member_by_val(cs_type)
        if not isinstance(cs_enum, ServiceEnum):
            return
        self.log_info("移除禁止匹配服务：", cs_type)
        self.__forbid_match_set.pop(cs_type, None)
