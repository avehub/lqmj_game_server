import asyncio
import random
from collections import Counter
from datetime import datetime

from nsanic.libs import tool_dt
from nsanic.verify import vint

from c_services.base.base_server import BaseServer
from c_services.const.cs_enum_const import CallCheck, CmdFanOut, CmdCompetition, CmdRoom, CmdWorkers
from c_services.cs_competition.const import GameRoomStatus
from c_services.cs_competition.room import CompetitionRoom
from common.model_rc.tournament_cycle import TournamentCycleRC
from common.model_rc.tournament_cycle_leaderboard import TournamentCycleLeaderboardRC
from common.model_rc.tournament_user_point import TournamentUserPointRC
from common.proto.py_pb2.ws_c2s import join_competition_model
from common.proto.py_pb2.ws_leisure import S2CCompetitionOver, S2CJoinCompetition, S2CStartCompetition, S2CGameRoomFinish, \
    S2CCompetitionInfo
from common.public.conf import ROBOT_BATTLE, R_UID_THRESHOLD
from common.public.enum_const import StaCode, ServiceEnum, CacheKey
from common.utils.utils import UtilsTool
from lucky_game.const import CompetitionStatus, PriceType
from lucky_game.handler.random_utils import generate_natural_random
from lucky_game.model_rc.base_robot import BaseRobotRC
from lucky_game.model_rc.conf_competition import ConfCompetitionRC
from common.utils.kit_async import DelayCall, delay_func
from lucky_game.model_rc.conf_json import ConfJsonRC


class CompetitionServer(BaseServer):
    def __init__(self):
        super().__init__()
        self.add_handlers({
            CmdCompetition.MATCH_COMPETITION: self.__match_competition,
            CmdCompetition.MATCH_BY_INNER: self.__match_competition,
            CmdCompetition.QUIT_COMPETITION: self.__quit_competition,
            CmdCompetition.ROOM_FINISH: self.__room_finish,
            CmdCompetition.MATCH_FINISH: self.__match_finish,
            CmdCompetition.BACK_COMPETITION: self.__back_competition,
            CmdCompetition.UPDATE_SCORE: self.__update_score,
        })

        self.__rooms = {}
        self.__wait_player = {}
        self.__robot_cursor = 0
        self.__current_cycle_id = 0
        self.__player_info = {}

        DelayCall(0.5, self.__init_data).start()
        DelayCall(2, self.__loop_match_competition).loop_start()

    def get_room(self, cid):
        return self.__rooms.get(cid)

    def create_room(self, cid):
        room = CompetitionRoom(cid, self)
        self.__rooms[cid] = room
        self.log_info("创建比赛房间", cid)
        return room

    def remove_room(self, cid):
        if cid in self.__rooms:
            self.__rooms.pop(cid)

    def get_or_create_room(self, cid):
        return self.get_room(cid) or self.create_room(cid)

    async def __init_data(self):
        """ 初始化数据 """
        # 读取机器人数据
        await self.__read_robot_data()
        # 读取当前赛事周期
        self.__current_cycle_id = await TournamentCycleRC.get_current_cycle_id()

    @UtilsTool.cal_time()
    async def __read_robot_data(self):
        """ 读取机器人数据 """
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

    async def __loop_match_competition(self):
        """ 循环匹配比赛 """
        if not self.__wait_player:
            return
        value_counts = Counter(self.__wait_player.values())
        for value, count in value_counts.items():
            conf_data = await ConfCompetitionRC.cache_conf_data_by_pk(value)
            max_match_player = conf_data.get("max_match_player")
            if count < max_match_player:
                robot_data = await self.__rand_robot_data()
                uid = robot_data.get("uid")
                await self.conf.locker.locked(value, self.__join_competition, (uid, value, conf_data))

    async def __match_competition(self, uid, data):
        """ 进入 """

        req_id = ""
        if isinstance(data, dict):
            competition_id = data.get("competition_id")
            self.log_info("内部进入比赛信息", uid, data)
        else:
            join_competition_model.ParseFromString(data)
            competition_id = join_competition_model.competition_id
            req_id = join_competition_model.req_id
            self.log_info("进入比赛信息", uid, competition_id, req_id)

        conf = await ConfJsonRC.cache_conf_data_by_pk(ConfJsonRC.CONF_ROOM_STOP)
        if conf and conf.get("status"):
            hint = "游戏玩法正在维护，喝杯茶，休息一下!"
            return await self.cs2ws_by_rmq(CmdCompetition.MATCH_COMPETITION, uid, StaCode.FORBID, hint, req_id=req_id)

        result, competition_id = vint(competition_id, require=True, minval=1)
        if not result:
            return await self.cs2ws_by_rmq(CmdCompetition.MATCH_COMPETITION, uid, StaCode.FAIL, "比赛id有误")
        await self.conf.locker.locked(competition_id, self.__do_match_competition, (uid, competition_id, req_id))

    async def __do_match_competition(self, uid, competition_id, req_id):
        """ 匹配比赛 """
        conf_data = await ConfCompetitionRC.cache_conf_data_by_pk(competition_id)
        if not conf_data:
            return await self.cs2ws_by_rmq(CmdCompetition.MATCH_COMPETITION, uid, StaCode.FAIL, "比赛不存在", req_id=req_id)
        if conf_data.get("status") == CompetitionStatus.CLOSED:
            return await self.cs2ws_by_rmq(CmdCompetition.MATCH_COMPETITION, uid, StaCode.FAIL, "比赛已关闭", req_id=req_id)
        start_time = conf_data.get("start_time")
        end_time = conf_data.get("end_time")
        daily_start_time = conf_data.get("daily_start_time")
        daily_end_time = conf_data.get("daily_end_time")
        curr_time = tool_dt.cur_time()
        if start_time > 0 and curr_time < start_time:
            return await self.cs2ws_by_rmq(CmdCompetition.MATCH_COMPETITION, uid, StaCode.FAIL, "比赛未开始", req_id=req_id)
        if 0 < end_time < curr_time:
            return await self.cs2ws_by_rmq(CmdCompetition.MATCH_COMPETITION, uid, StaCode.FAIL, "比赛已结束", req_id=req_id)
        is_in_match_time = self.check_match_begin_time(curr_time, daily_start_time, daily_end_time)
        if not is_in_match_time:
            return await self.cs2ws_by_rmq(CmdCompetition.MATCH_COMPETITION, uid, StaCode.FAIL, "比赛时间未到", req_id=req_id)
        join_info = await self.__get_player_in_match(uid)
        if join_info:
            return await self.cs2ws_by_rmq(CmdCompetition.MATCH_COMPETITION, uid, StaCode.FAIL, "玩家已加入比赛", req_id=req_id)
        cs_type = conf_data.get("cs_type")
        cs_enum = ServiceEnum.find_member_by_val(cs_type)
        if not isinstance(cs_enum, ServiceEnum):
            return await self.cs2ws_by_rmq(CmdCompetition.MATCH_COMPETITION, uid, StaCode.FAIL, "比赛类型有误", req_id=req_id)

        price = conf_data.get("price")
        price_type = conf_data.get("price_type")
        if price_type == PriceType.BY_POINT:
            sta, user_point = await TournamentUserPointRC.get_user_point(self.__current_cycle_id, uid)
            if not sta:
                return await self.cs2ws_by_rmq(CmdCompetition.MATCH_COMPETITION, uid, StaCode.FAIL, "玩家暂未参赛", req_id=req_id)
            if user_point.get("ticket") < price:
                return await self.cs2ws_by_rmq(CmdCompetition.MATCH_COMPETITION, uid, StaCode.FAIL, "玩家积分不足", req_id=req_id)
            # 扣费
            user_point["ticket"] -= price
            self.__player_info[uid] = user_point
            await TournamentUserPointRC.update_int_field(uid, "ticket", price, "sub")

        await self.__join_competition(uid, competition_id, conf_data, req_id)

    async def __join_competition(self, uid, competition_id, conf_data, req_id=""):
        """ 加入比赛 """
        await self.__save_player_in_match(uid, competition_id)
        self.__wait_player[uid] = competition_id
        max_player = conf_data.get("max_player")
        max_match_player = conf_data.get("max_match_player")
        self.log_info("competition_id", competition_id, "玩家加入比赛", uid)
        if uid <= R_UID_THRESHOLD:
            sta, user_point = await TournamentUserPointRC.get_user_point(self.__current_cycle_id, uid)
            if sta:
                self.__player_info[uid] = user_point
            else:
                self.__player_info[uid] = {"score": 0, "ticket": 99}
        value_counts = Counter(self.__wait_player.values())
        send_list = []
        if value_counts[competition_id] <= max_match_player:
            players = [p_uid for p_uid, comp_id in self.__wait_player.items() if comp_id == competition_id]
            for p_uid in players:
                data = {"players": players, "max_match_player": max_match_player}
                data_model = S2CJoinCompetition.pb_model(**data)
                await self.cs2ws_by_rmq(CmdCompetition.MATCH_COMPETITION, p_uid, msg=data_model, req_id=req_id)
        if send_list:
            await asyncio.gather(*send_list)
        if value_counts[competition_id] >= max_match_player:
            players = [p_uid for p_uid, comp_id in self.__wait_player.items() if comp_id == competition_id]
            player_list = players[:max_match_player]
            match_room_id = await self.unique_match_room_id()
            if self.get_room(match_room_id):
                return await self.cs2ws_by_rmq(CmdCompetition.MATCH_COMPETITION, uid, StaCode.FAIL, "比赛房间已存在", req_id=req_id)
            room = self.get_or_create_room(match_room_id)
            if uid in room.members:
                return await self.cs2ws_by_rmq(CmdCompetition.MATCH_COMPETITION, uid, StaCode.FAIL, "玩家已在比赛中", req_id=req_id)
            if uid <= 0:
                return await self.cs2ws_by_rmq(CmdCompetition.MATCH_COMPETITION, uid, StaCode.FAIL, "玩家uid有误", req_id=req_id)
            room.max_player = max_player
            room.max_match_player = max_match_player
            room.competition_id = competition_id
            room.total_match_round = conf_data.get("total_match_round")
            for p_uid in player_list:
                self.__wait_player.pop(p_uid)
                score = self.__player_info[p_uid].get("score", 0)
                room.player_join_competition_room(p_uid, score)
                await self.__save_match_room_id(p_uid, match_room_id)

            await self.__competition_before_start(conf_data, room, req_id)

    async def __back_competition(self, uid, data):
        join_competition_model.ParseFromString(data)
        competition_id = join_competition_model.competition_id
        req_id = join_competition_model.req_id
        self.log_info("返回比赛", uid, competition_id, req_id)
        conf_data = await ConfCompetitionRC.cache_conf_data_by_pk(competition_id)
        if not conf_data:
            return await self.cs2ws_by_rmq(CmdCompetition.MATCH_COMPETITION, uid, StaCode.FAIL, "比赛不存在", req_id=req_id)
        if conf_data.get("status") == CompetitionStatus.CLOSED:
            return await self.cs2ws_by_rmq(CmdCompetition.MATCH_COMPETITION, uid, StaCode.FAIL, "比赛已关闭", req_id=req_id)
        join_info = await self.__get_player_in_match(uid)
        if not join_info:
            return await self.cs2ws_by_rmq(CmdCompetition.MATCH_COMPETITION, uid, StaCode.FAIL, "玩家未加入比赛", req_id=req_id)
        max_match_player = conf_data.get("max_match_player")
        players = [p_uid for p_uid, comp_id in self.__wait_player.items() if comp_id == competition_id]
        for p_uid in players:
            data = {"players": players, "max_match_player": max_match_player}
            data_model = S2CJoinCompetition.pb_model(**data)
            await self.cs2ws_by_rmq(CmdCompetition.MATCH_COMPETITION, p_uid, msg=data_model, req_id=req_id)
        match_room_id = join_info.get("match_room_id")
        if not match_room_id:
            return await self.cs2ws_by_rmq(CmdCompetition.MATCH_COMPETITION, uid, StaCode.FAIL, "玩家未加入比赛房间", req_id=req_id)
        await self.__competition_info(match_room_id)

    async def __competition_before_start(self, conf_data, room, req_id=""):
        """ 比赛开始前 """
        self.log_info(room.match_room_id,"比赛开始前准备")
        data = {
            "cs_type": conf_data.get("cs_type"),
            "total_round": conf_data.get("total_round"),
            "max_player": room.max_player,
            "rule_details": conf_data.get("rule_detail"),
            "room_type": 2,
            "play_type": conf_data.get("play_type"),
            "match_room_id": room.match_room_id,
            "match_round": room.match_round,
            "total_match_round": room.total_match_round,
            "secret": self.conf.SECRET_KEY,
        }
        cs_type = conf_data.get("cs_type")
        room.cs_type = cs_type
        cs_enum = ServiceEnum.find_member_by_val(cs_type)
        comp_data = {"competition_id": room.competition_id, "cs_type": cs_type}
        data_model = S2CStartCompetition.pb_model(**comp_data)

        group_list = room.get_players_by_score()
        player_list = list(room.members)
        room_num = 1
        is_init = room.match_round == 1
        for group in group_list:
            data["room_id"] = await self.unique_room_id()
            game_room_info = {
                "status": GameRoomStatus.PLAYING,
                "players": group,
                "room_num": room_num,
            }
            room.set_game_room_info(data["room_id"], game_room_info)
            room_num += 1
            send_list = []
            for p_uid in group:
                data["player_score"] = 0 if is_init else room.get_player_score(p_uid)
                send_list.append(self.cs2cs_by_rmq(cs_enum, CmdRoom.NEW_MATCH, data, p_uid))

            if send_list:
                await asyncio.gather(*send_list)

        await delay_func(0.5, self.__start_competition, player_list, data_model, req_id)
        if is_init:
            await self.__competition_info(room.match_room_id, is_init)

    async def __start_competition(self, player_list, data_model, req_id=""):
        """ 开始比赛 """
        self.log_info("比赛开始")
        for p_uid in player_list:
            if p_uid > R_UID_THRESHOLD:
                await self.cs2ws_by_rmq(CmdCompetition.START_COMPETITION, p_uid, msg=data_model, req_id=req_id)

    async def __room_finish(self, _, data):
        """ 房间结束 """
        match_room_id = data.get("match_room_id")
        room_id = data.get("room_id")
        room = self.get_room(match_room_id)
        if not room:
            self.log_info("match_room_id", match_room_id, "比赛房间不存在")
        room.add_finish_room_count()
        is_all_room_finish = room.finish_room_count == room.game_room_count
        data = {"need_wait": not is_all_room_finish}
        room_info = room.game_room_info[room_id]
        sta = GameRoomStatus.PLAYING
        if not is_all_room_finish:
            sta = GameRoomStatus.WAITING
        players = room_info.get("players") or []
        room_num = room_info.get("room_num") or 0
        room.set_game_room_info(room_id, {"status": sta, "players": players, "room_num": room_num})
        s2c_game_room_finish = S2CGameRoomFinish.pb_model(**data)
        await self.conf.rds.srem("game_room_number", room_id)
        self.log_info(match_room_id,"room_id", room_id, "该房间已结束")
        send_list = []
        if players:
            for uid in players:
                if uid > R_UID_THRESHOLD:
                    send_list.append(self.cs2ws_by_rmq(CmdCompetition.ROOM_FINISH, uid, msg=s2c_game_room_finish))
        if send_list:
            await asyncio.gather(*send_list)
        is_competition_finish = False
        if is_all_room_finish:
            if room.match_round == room.total_match_round:
                is_competition_finish = True
            else:
                room.finish_room_count = 0
                room.game_room_info.clear()
                room.add_match_round()
                conf_data = await ConfCompetitionRC.cache_conf_data_by_pk(room.competition_id)
                await delay_func(10, self.__competition_before_start, conf_data, room, "")

        await self.__competition_info(match_room_id, is_finish=is_competition_finish)
        if is_competition_finish:
            await self.__match_finish(match_room_id, room)

    async def __match_finish(self, match_room_id, room):
        """ 比赛结束 """
        rank_by_score = room.get_rank_by_score()
        self.log_info( match_room_id, "该比赛已结束","排名", rank_by_score)
        competition_result = []
        send_work_list = []
        total_players = len(room.members)
        for rank, uid, score in rank_by_score:
            points = total_players - rank + 1
            ticket = self.__player_info[uid].get("ticket", 0)
            score = 0 if score >= 0 else score
            competition_result.append({
                "uid": uid,
                "rank": rank,
                "score": score,
                "points": points,
                "ticket": ticket if score >= 0 else ticket + score
            })
            self.__player_info.pop(uid)

            # send_data = {
            #     "cycle_id": self.__current_cycle_id,
            #     "up_data": {
            #         "score": points,
            #         "ticket": score  # 正分不扣门票，负分输多少扣多少门票
            #     }
            # }
            # send_work_list.append(self.send_task_to_worker(CmdWorkers.UPDATE_COMPETITION_RESULT, send_data, uid))

            #暂时不通过worker更新
            up_data = {
                    "score": points,
                    "ticket": score  # 正分不扣门票，负分输多少扣多少门票
                }
            sta, result = await TournamentUserPointRC.up_user_point(self.__current_cycle_id, uid, up_data)
            self.log_info(f"更新比赛结果：{sta} 玩家{uid}")
        data = {
            "competition_result": competition_result,
        }
        if send_work_list:
            await asyncio.gather(*send_work_list)
        for item in competition_result:
            uid = item.get("uid")
            if uid > R_UID_THRESHOLD:
                rank_info = await TournamentCycleLeaderboardRC.get_uid_rank_and_difference(self.__current_cycle_id, uid)
                now_rank = rank_info.get("rank_position", 0)
                last_rank_info = await self.__get_player_in_match(uid)
                last_rank = last_rank_info.get("rank", 0)
                item["difference"] = rank_info.get("difference", 0)
                item["last_rank"] = last_rank
                item["now_rank"] = now_rank

        print("competition_result", competition_result)
        s2c_competition_over = S2CCompetitionOver.pb_model(**data)
        await room.inner_broadcast(CmdCompetition.MATCH_FINISH, s2c_competition_over)
        await self.__delete_player_in_match(list(room.members))
        room.clear_competition()
        await self.conf.rds.srem("match_room_number", match_room_id)
        self.remove_room(match_room_id)

    async def __update_score(self, uid, data):
        """ 更新比赛积分 """
        match_room_id = data.get("match_room_id")
        room_id = data.get("room_id")
        room = self.get_room(match_room_id)
        if not room:
            self.log_info("match_room_id", match_room_id, "比赛房间不存在")
            return
        player_score = data.get("player_score")
        if player_score:
            for uid, score in player_score.items():
                room.update_player_score(int(uid), score)
        self.log_info( match_room_id, "room_id", room_id, "更新积分", player_score)
        await self.__competition_info(match_room_id)

    async def __competition_info(self, match_room_id, is_init=False, is_finish=False):
        room = self.get_room(match_room_id)
        if not room:
            self.log_info("match_room_id", match_room_id, "比赛房间不存在")
            return
        player_rank = []
        award_list = []
        total_players = len(room.members)
        player_in_room_num = {}
        game_room_list = []
        for room_id, info in room.game_room_info.items():
            game_room_status = {
                "room_num": info.get("room_num", 0),
                "status": GameRoomStatus.FINISH if is_finish else info.get("status", GameRoomStatus.PLAYING),
                "tid": room_id,
            }
            game_room_list.append(game_room_status)
            #
            for uid in info.get("players", []):
                player_in_room_num.setdefault(uid, info.get("room_num", 0))

        data = {
            "player_rank": player_rank,
            "award_list": award_list,
            "game_room_list": game_room_list,
        }

        for rank, uid, score in room.get_rank_by_score():
            rank_info = {
                "rank": rank,
                "uid": uid,
                "score": 0 if is_init else score,
                "room_num": player_in_room_num.get(uid, 0),
            }
            points = total_players - rank + 1
            player_rank.append(rank_info)
            award_list.append({
                "rank": rank,
                "points": points,
            })


        print("比赛信息", data)
        s2c_competition_info = S2CCompetitionInfo.pb_model(**data)
        await room.inner_broadcast(CmdCompetition.COMPETITION_INFO, s2c_competition_info)

    async def __save_player_in_match(self, uid, competition_id):
        if uid > R_UID_THRESHOLD:
            rank_info = await TournamentCycleLeaderboardRC.get_uid_rank_and_difference(self.__current_cycle_id, uid)
            rank = rank_info.get("rank_position", 0)
        else:
            rank = 0
        info = {
            "competition_id": competition_id,
            "timestamp": tool_dt.cur_time(),
            "rank":rank
        }
        await self.conf.rds.set_hash(CacheKey.IN_MATCH, uid, info)

    async def __save_match_room_id(self, uid, match_room_id):
        """
        为玩家追加保存比赛房间ID
        """
        match_info = await self.conf.rds.get_hash(CacheKey.IN_MATCH, uid, jsparse=True)
        if match_info:
            match_info["match_room_id"] = match_room_id
        await self.conf.rds.set_hash(CacheKey.IN_MATCH, uid, match_info)

    async def __delete_player_in_match(self, uid_list):
        await self.conf.rds.drop_hash_bulk(CacheKey.IN_MATCH, uid_list)

    async def __delete_all_player_in_match(self):
        """ 删除所有比赛中的玩家 """
        await self.conf.rds.del_item(CacheKey.IN_MATCH)

    async def __get_player_in_match(self, uid):
        return await self.conf.rds.get_hash(CacheKey.IN_MATCH, uid, jsparse=True)

    async def __quit_competition(self, uid, data):
        """ 退出 """
        join_competition_model.ParseFromString(data)
        competition_id = join_competition_model.competition_id
        req_id = join_competition_model.req_id
        if not self.__wait_player.get(uid):
            return await self.cs2ws_by_rmq(CmdCompetition.QUIT_COMPETITION, uid, StaCode.FAIL, "玩家不在比赛中或者已经在游戏中",
                                           req_id=req_id)
        self.__wait_player.pop(uid)
        delete_players = []
        players = [p_uid for p_uid, comp_id in self.__wait_player.items() if comp_id == competition_id]
        if players and all(uid < R_UID_THRESHOLD for uid in players):
            delete_players.extend(players)
            players = []
        for p_uid in delete_players:
            self.__wait_player.pop(p_uid)
        delete_players.append(uid)
        await self.__delete_player_in_match(delete_players)
        self.log_info("玩家退出比赛", uid)
        data = {"players": players}
        data_model = S2CJoinCompetition.pb_model(**data)
        await self.cs2ws_by_rmq(CmdCompetition.QUIT_COMPETITION, uid, msg=data_model, req_id=req_id)
        send_list = []
        for p_uid in players:
            if p_uid < R_UID_THRESHOLD:
                continue
            send_list.append(self.cs2ws_by_rmq(CmdCompetition.QUIT_COMPETITION, p_uid, msg=data_model))
        if send_list:
            await asyncio.gather(*send_list)

    @staticmethod
    def check_match_begin_time(curr_time, daily_start_time, daily_end_time):
        dt_object = datetime.fromtimestamp(curr_time)
        current_time = dt_object.time()

        start_time = datetime.strptime(daily_start_time, "%H:%M:%S").time()
        end_time = datetime.strptime(daily_end_time, "%H:%M:%S").time()
        return start_time <= current_time <= end_time

    async def unique_room_id(self, num: int = 6):
        """生成唯一房间ID"""
        while True:
            room_id = generate_natural_random(num)
            has = await self.conf.rds.sismember("game_room_number", room_id)
            if not has:
                await self.conf.rds.sadd("game_room_number", room_id)
                return room_id

    async def unique_match_room_id(self, num: int = 7):
        """生成唯一匹配房间ID"""
        while True:
            match_room_id = generate_natural_random(num)
            has = await self.conf.rds.sismember("match_room_number", match_room_id)
            if not has:
                await self.conf.rds.sadd("match_room_number", match_room_id)
                return match_room_id

    async def check_in_room(self, cmd, uid, competition_id):
        room = self.get_room(competition_id)
        if not room:
            await self.cs2ws_by_rmq(cmd, uid, StaCode.FAIL, hint='比赛不存在')
        elif not room.check_player_in_competition(uid):
            await self.cs2ws_by_rmq(cmd, uid, StaCode.FAIL, hint='玩家未在比赛服务')
            return None
        return room

    async def call_handler(self, cmd, uid, data):
        """
        uid: uid or ws
        注意顺序
        """
        func = self.cmd2func.get(cmd)
        if not func or not callable(func):
            return
        c_enum = CmdCompetition.find_member_by_val(cmd)
        if not c_enum:
            c_enum = CmdFanOut.find_member_by_val(cmd)
        check_inner = c_enum.desc == CallCheck.INNER
        if check_inner:
            data = self.check_inner_call(data)
            if not data:
                return
            data.pop("secret")
            return await func(uid, data) if asyncio.iscoroutinefunction(func) else func(uid, data)
        return await func(uid, data) if asyncio.iscoroutinefunction(func) else func(uid, data)

    async def clear_in_service(self):
        await self.clear_all_match_room_cache()
        await self.__delete_all_player_in_match()
        await super().clear_in_service()

    async def clear_all_match_room_cache(self):
        """清除所有比赛房间ID缓存"""
        await self.conf.rds.del_item("match_room_number")
        self.log_info("已清除所有比赛房间ID缓存")

    async def send_task_to_worker(self, cmd, data, uid=1):
        """ 发送任务到worker消费 """
        await self.push_task2worker(cmd, data, uid)
