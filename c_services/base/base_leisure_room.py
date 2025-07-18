import asyncio
import random

from nsanic.libs.tool import json_encode

from c_services.base.base_room import BaseRoom
from c_services.const.cs_enum_const import RoomStatus, CmdRoom, CmdWorkers, GameAnnouncement
from common.proto.py_pb2.ws_leisure import S2CDealCards, s2c_tickets_model, S2CBrokeBroad, \
    s2c_trustee_model, s2c_gold_model, s2c_one_of_model, s2c_recharge_model
from common.public.conf import LIVE_SERVER
from common.public.enum_const import TaskId, StaCode
from common.utils.utils import UtilsTool
from lucky_admin.const import WeightEnum
from lucky_game.const import ReasonCostGold, SeasonStatus, GiftType
# from lucky_game.model_rc.base_activity import ConfActivityRC


class BaseLeisureRoom(BaseRoom):
    def __init__(self, tid, service, room_conf, extra_room_info, poker):
        super().__init__(tid, service, room_conf, poker)
        self.__record_ori_gold = {}  # 记录玩家金币信息
        self.__task_collect = {}  # 任务收集器
        self.__season_status = extra_room_info.get("ranking_info", {}).get("season_status") or SeasonStatus.OFF_SEASON
        self.__gift_conf = room_conf.get("gift_conf") or []

        robot_interact = room_conf.get("rule_conf", {}).get("robot_interact", {})
        self.__robot_interact = {int(key): value for key, value in robot_interact.items()}
        self.__ann_threshold_multiple = room_conf.get("threshold_multiple") or 0  # 公告阈值倍率

    @property
    def record_ori_gold(self):
        return self.__record_ori_gold

    @property
    def ren_shu_count(self):
        count = 0
        for p in self.seats:
            if p and p.is_out:
                count += 1
        return count

    @property
    def in_play_count(self):
        count = 0
        for p in self.seats:
            if p and p.is_out:
                count += 1
        return count

    @property
    def season_status(self):
        return self.__season_status

    @property
    def gift_conf(self):
        return self.__gift_conf

    @property
    def robot_interact(self):
        return self.__robot_interact

    @property
    def ann_threshold_multiple(self):
        return self.__ann_threshold_multiple

    def add_task(self, task_info: dict):
        """
        收集任务
        将同一个人的 相同task_id收集
        """
        task_id = task_info.get("task_id")
        uid = task_info.get("uid")
        key = f'{uid}_{task_id}'
        old_task = self.__task_collect.get(key)
        if old_task:
            old_task["add_val"] += task_info.get("add_val") or 0
        else:
            self.__task_collect[key] = task_info

    async def round_start(self, is_cut_tickets=True):
        """ 一局开始 """
        self.set_room_status(RoomStatus.T_PLAYING)
        if is_cut_tickets:
            await self.deduct_tickets()
            await self.update_player_bag_prop_used()  # 更新道具使用

        seat2uid = {}
        for p in self.seats:
            self.__record_ori_gold[p.seat_id] = p.gold
            seat2uid[p.seat_id] = p.uid
        self.log_info("游戏开始", seat2uid, self.__record_ori_gold)
        await self.inner_broadcast(CmdRoom.ROUND_START)

    async def do_trustee(self, player):
        is_trustee = False if player.trustee else True
        player.trustee = is_trustee
        tm = s2c_trustee_model(player.seat_id, is_trustee)
        await self.inner_broadcast(CmdRoom.TRUSTEE, tm)

    def try_round_start(self, rs: int = 0, is_cut_tickets=True):
        """ 尝试开始游戏 """
        if not self.room_status_is_equal(RoomStatus.T_IDLE):
            self.log_info("房间必须在空闲中才能开始游戏，当前流程为：", self.flow_status)
            return False
        if self.in_room_count != self.max_player_count:
            self.log_info("人数不够开始游戏")
            return False
        self.call_flow(rs, self.round_start, is_cut_tickets)

    def try_next_round(self, rs: int = 0):
        """ 尝试开始游戏 """
        self.try_round_start(rs, False)

    async def player_quit_room(self, player, req_id):
        """ 玩家离开房间 """
        super().player_quit_room(player, ...)
        # 已经认输的玩家退出房间时，删除玩家房间缓存，让其能够匹配其它房间
        await self.inner_send(player, CmdRoom.QUIT_ROOM, req_id=req_id)
        # todo: 只剩机器人时是否解散房间？
        if player.is_out:
            # self.__seats[player.seat_id - 1] = None
            player.tid = 0  # 清除玩家房间号 防止check in table时房间号错乱
            self.log_info(player.uid, "玩家认输退出房间", id(player))
            await self.service.del_player_in_service(player.uid)
            await self.try_round_over()

    async def try_round_over(self):
        """ 尝试解散房间 """
        for player in self.seats:
            if player.is_robot:
                continue
            if not (player.is_out and player.offline):
                return  # 但凡有真实玩家 没有 破产和离线则不解散房间
        self.log_info("房间内已经没有真人玩家，enter force_dismiss")
        await self.delay_func(0.5, self.force_dismiss)

    async def deduct_tickets(self):
        """ 扣除门票 """
        price = self.room_conf.get("price") or 0
        if not price:
            return
        update_task = []
        gold_info = []
        for player in self.seats:
            if not player.is_robot:
                if player.free_loss:  # 免门票
                    continue
                update_task.append(self.update_user_gold(player, -price, ReasonCostGold.TICKETS_LEISURE))

            player.update_gold(-price, accumulate=False)
            gold_info.append({"seat_id": player.seat_id, "gold": player.gold})

        tickets_model = s2c_tickets_model(gold_info)
        update_task.append(self.inner_broadcast(CmdRoom.DEDUCT_TICKETS, tickets_model))
        update_task and await asyncio.gather(*update_task)

    async def player_join_room(self, players):
        """ 玩家加入房间 """
        await super().player_join_room(players)

        real_player_gold = 0
        real_count = 0
        for player in players:
            if not player.is_robot:
                real_player_gold += player.gold
                real_count += 1

        mean_real_player_gold = real_player_gold // real_count
        for player in players:
            if player.is_robot:
                self.set_robot_random_gold(player, mean_real_player_gold)

    async def do_deal_cards(self, all_cards, set_dealer_card=None, extra_data=None):
        send_list = []
        for i, player in enumerate(self.seats):
            player.cards = all_cards[i]
            if not player.is_out and set_dealer_card and set_dealer_card in player.cards:
                self.dealer_id = player.seat_id
                self.log_info("设置庄为：", self.dealer_id, player.uid)

            self.log_info(player.uid, player.seat_id, "玩家发牌：", player.cards)
            if player.is_robot:
                continue
            data = {"cards": player.cards, "seat_id": player.seat_id}
            if extra_data:
                data.update(extra_data)
            data_model = S2CDealCards.pb_model(**data)
            send_list.append(self.inner_send(player, CmdRoom.DEALER_CARDS, data_model))
        await asyncio.gather(*send_list)

    async def play_card_by_rand(self, player):
        """ 随机出牌 """

    def set_robot_random_gold(self, player, mean_real_player_gold):
        """ 设置机器人随机金币 """
        min_take = self.room_conf.get("min_take")
        max_take = self.room_conf.get("max_take")

        if max_take == -1:
            max_take = mean_real_player_gold * 2 or min_take * 5

        if mean_real_player_gold == 0:
            mean_real_player_gold = max_take

        min_real_player = int(mean_real_player_gold * 0.5)
        max_real_player = int(mean_real_player_gold * 2)

        # RANDOM(MAX(场次携带下限，玩家平均携带*0.5)，MIN(场次携带上限，玩家平均携带*2))
        a = max(min_take, min_real_player)
        b = min(max_take, max_real_player)

        if a > b:
            self.log_info("机器人随机设置金币数错误：", self.level_desc, min_take, max_take, mean_real_player_gold)
            a, b = b, a
        gold = random.randint(a, b)

        # 从场次门槛到准入上限中间取随机值，为了更趋向于正态分布，这里取两次随机值相加除以2
        # gold1 = random.randint(min_take, max_take)
        # gold2 = random.randint(min_take, max_take)
        # gold = int((gold1 + gold2) / 2)
        player.gold = gold

    async def update_user_gold(self, player, win_score, reason: ReasonCostGold):
        await self.service.update_user_gold(player, win_score, reason)
        # todo: 保险箱补足
        # await self.safe_box_auto_complement(player)

    async def do_check_gold(self, gold_info: dict, reason: ReasonCostGold):
        """ 结算金币 """
        update_task = []
        self.log_info("结算信息：", gold_info)
        for player in self.seats:
            if player.is_out:
                continue
            score = gold_info.get(player.seat_id)
            player.update_gold(score)
            if not player.is_robot:
                update_task.append(self.update_user_gold(player, score, reason))

        if update_task:
            await asyncio.gather(*update_task)

    async def game_over(self, is_force=False):
        """ 游戏结束 """
        self.set_room_status(RoomStatus.T_DISMISS)
        await self.inner_broadcast(CmdRoom.GAME_OVER)
        not is_force and await self.round_over_check_gold_enough_or_not()  # 检测金币是否足够6下发礼包等
        await self.update_game_states()  # 更新游戏胜场/总场等
        await self.send_task()  # 发送任务
        await self.tigger_big_win_announcement()
        await super().game_over()

    async def tigger_big_win_announcement(self):
        """
        触发大赢公告
        玩家子游戏结束时，玩家赢取金币数>=阈值倍率*底注，则触发大赢公告
        """
        threshold_score = self.__ann_threshold_multiple * self.base_score
        data_list = []
        for p in self.seats:
            self.log_info("大赢公告", p.uid, p.total_score, threshold_score)
            if p.total_score >= threshold_score:
                content = {
                    "sentence_pattern": GameAnnouncement.rand_choice_member(),
                    "uid": p.uid,
                    "cs_type": self.service.service_type,
                    "level_desc": self.level_desc,
                    "win_gold": p.total_score
                }
                data = {
                    "weight": WeightEnum.W1,
                    "content": json_encode(content, log_fun=self.err_log)
                }

                data_list.append(data)

        if data_list:
            data = {"ann_list": data_list}
            await self.send_task_to_worker(CmdWorkers.NOTIFY_ANNOUNCEMENT, data)

    def room_win_lose_data(self):
        """ 一局结束输赢情况 """
        player_info = []
        for p in self.seats:
            player_info.append(p.round_over_info())
        return player_info

    async def update_game_states(self):
        """ 更新游戏情况：游戏次数、胜场、战绩等 """
        send_list = []
        grade_data = []
        for p in self.seats:
            if not p.is_robot:
                data = {
                    "cs_type": self.service.service_type,
                    "play_type": self.play_type,
                    # "win_count": 1 if p.round_score > 0 else 0,
                    "win_count": p.is_win,
                    "total_count": 1
                }
                send_list.append(self.send_task_to_worker(CmdWorkers.UPDATE_GAME_TIMES, data, p.uid))

                grade_data.append({
                    "uid": p.uid,
                    "cs_type": self.service.service_type,
                    "play_type": self.play_type,
                    "tid": str(self.tid),
                    "score": p.round_score,
                    "rank_score": p.ranking_score,  # todo: 段位分
                    "level_desc": self.level_desc,
                    "is_win": p.is_win
                })

                self.complete_game_task(p.uid)

        if grade_data:
            grade_data = {'up_rank': self.__season_status == SeasonStatus.ACTIVE_SEASON, 'data': grade_data}
            send_list.append(self.send_task_to_worker(CmdWorkers.INSERT_GAME_GRADE, grade_data))

        send_list and await asyncio.gather(*send_list)

    def complete_game_task(self, uid):
        """ 完成游戏 """
        task_list = (
            TaskId.COMPLETE_GAME_6,
            TaskId.COMPLETE_GAME_12,
            TaskId.COMPLETE_GAME_18,

            TaskId.MONOPOLY_COMPLETE_GAME_1,
            TaskId.MONOPOLY_COMPLETE_GAME_3,
        )
        for task_id in task_list:
            data = {
                "task_id": task_id,
                "add_val": 1,
                "uid": uid
            }
            self.add_task(data)

    async def send_task(self):
        for task_id, data in self.__task_collect.items():
            uid = data.pop("uid")
            await self.send_task_to_worker(CmdWorkers.UPDATE_GAME_TASK, data, uid)

    async def update_player_bag_prop_used(self):
        """ 更新玩家背包使用 """
        send_list = []
        for p in self.seats:
            if not p.is_robot:
                prop_info = p.get_update_take_prop_info()
                if prop_info:
                    data = {"prop": prop_info}
                    send_list.append(self.send_task_to_worker(CmdWorkers.UPDATE_BAG_PROP, data, p.uid))
        if send_list:
            await asyncio.gather(*send_list)

    async def __do_resurgence(self, player, solid_time=0):
        for gift in self.__gift_conf:
            if gift.get("gift_type") == GiftType.REVENGE:
                activity_id = gift.get("activity_id")
                # data = await ConfActivityRC.get_activity_item_by_id(activity_id)
                data = {}
                conf_items = data.get("conf_items")
                if conf_items:
                    gold = conf_items[0].get("goods_count")
                    self.log_info(player.uid, "机器人复活", activity_id, gold)
                    sale_limit = data.get("sale_limit")
                    multiple = sale_limit.get("multiple") or 1
                    if multiple > 1:
                        gold *= multiple

                    if not player.is_robot:
                        await self.update_user_gold(player, gold, ReasonCostGold.ACT_PACKAGE)

                    player.gold = gold
                    if solid_time:
                        self.call_flow_robot(solid_time, self.notify_resurgence, player)
                        return
                    self.call_flow_robot(random.randint(10, 15), self.notify_resurgence, player)
                    return

    async def robot_go_broke(self, player):
        """ 机器人概率复活 """
        flag = UtilsTool.random_choice_num([0, 1], [0.5, 0.5])
        # flag = UtilsTool.random_choice_num([0, 1], [0, 1])
        if flag:
            return await self.__do_resurgence(player)
        return self.call_flow_robot(random.randint(2, 5), self.player_give_up, player)

    async def notify_resurgence(self, player):
        """ 通知复活 """
        rm = s2c_recharge_model(player.seat_id, str(player.gold))
        await self.inner_broadcast(CmdRoom.RECHARGE, rm)
        await self.turn_end(after_pick=True)

    async def notify_buy_gift_pack(self, player, cmd=CmdRoom.GO_BROKE, seconds=30):
        """ 通知购买礼包 """
        result = {
            "seconds": seconds,
            "seat_id": player.seat_id,
            "gift_conf": self.room_conf.get("gift_conf")
        }
        # todo: 下发复仇礼包
        ori_gold = self.record_ori_gold.get(player.seat_id) or ""  # 开局前的金币
        result["ori_gold"] = str(ori_gold)
        data_model = S2CBrokeBroad.pb_model(**result)
        if cmd == CmdRoom.GO_BROKE:
            if not LIVE_SERVER:
                flag = await self.service.conf.rds.conn.sismember('resurgence_white_list', player.uid)
                if flag:
                    print("白名单复活！！！", player.uid)
                    return await self.__do_resurgence(player, 1)

            await self.inner_broadcast(cmd, data_model)
            if player.is_robot:
                # return self.call_flow_robot(random.randint(2, 5), self.player_give_up, player)
                return await self.robot_go_broke(player)
        else:
            await self.inner_send(player, cmd, data_model)

    async def notify_is_revenge(self, player):
        """ 判断是否复仇"""
        # 判断破产玩家，弹出充值，充值继续，不充值认输
        self.set_room_status(RoomStatus.T_RECHARGE_ING)
        self.log_info(player.uid, player.seat_id, "进入是否复仇")
        sec = 30
        await self.notify_buy_gift_pack(player, seconds=sec)
        self.call_flow(sec, self.player_give_up, player)

    async def player_give_up(self, player):
        player.is_out = True
        m = s2c_one_of_model()
        m.seat_id = player.seat_id

        # 更新破产玩家并从剩余卡牌中将其移除
        await self.inner_broadcast(CmdRoom.GIVE_UP, m)
        self.log_info(player.uid, player.seat_id, "放弃")
        await self.turn_end()

    async def player_recharge_ing(self, player):
        """ 充值中回调 """
        if not self.room_status_is_equal(RoomStatus.T_RECHARGE_ING):
            return
        if player.seat_id != self.curr_seat_id:
            return
        left_sec = self.left_seconds()
        left_sec += 30

        result = {
            "seconds": left_sec,
            "seat_id": player.seat_id,
        }
        data_model = S2CBrokeBroad.pb_model(**result)
        await self.inner_broadcast(CmdRoom.RECHARGE_ING, data_model)
        self.call_flow(left_sec, self.player_give_up, player)

    async def player_recharge(self, player):
        """ 玩家充值回调 """
        if player.seat_id != self.curr_seat_id:
            return
        await self.service.init_player(player)
        if player.gold <= 0:
            return await self.inner_send(player, CmdRoom.RECHARGE, code=StaCode.GOLD_NOT_ENOUGH)
        if player.is_out:
            return await self.inner_send(player, CmdRoom.RECHARGE, code=StaCode.RULE_ERR, hint="玩家已经认输")
        await self.notify_resurgence(player)

    async def turn_end(self, after_pick=False):
        """ 一轮结束 """
        await self.inner_broadcast(CmdRoom.TURN_END)
        if after_pick:
            # 捡完牌应该继续打牌(包括破产后充值)
            next_player = self.curr_player()
        else:
            next_player = self.next_player(self.curr_seat_id)
        self.set_room_status(RoomStatus.T_PLAYING)
        await self.turn_start(next_player)

    async def turn_start(self, player):
        pass

    async def round_over_check_gold_enough_or_not(self):
        """ 游戏结束检测是否下发 礼包 """
        send_list = []
        for player in self.seats:
            if not player.is_robot:
                if player.gold < self.room_conf.get("min_take"):
                    self.log_info(player.uid, "游戏结束下发返还礼包")
                    send_list.append(self.notify_buy_gift_pack(player, CmdRoom.GOLD_NOT_ENOUGH))
        send_list and await asyncio.gather(*send_list)

    # async def safe_box_auto_complement(self, player):
    #     """ 保险箱自动补足 """
    #     status = await self.service.safe_box_auto_complement(player)
    #     if status:
    #         m = s2c_gold_model(player.seat_id, player.gold)
    #         await self.inner_broadcast(CmdRoom.SAFE_BOX_AUTO_COMPLEMENT, m)

    @staticmethod
    def get_player_info(player):
        """ 子类实现 """

    def clear_room(self):
        """ 清理房间 """
        self.__record_ori_gold.clear()
        self.__task_collect.clear()
        super().clear_room()

    def refresh_room_conf(self, service, room_conf, **extra_room_info):
        self.__season_status = extra_room_info.get("ranking_info", {}).get("season_status") or SeasonStatus.OFF_SEASON
        self.__gift_conf = room_conf.get("gift_conf") or []
        robot_interact = room_conf.get("rule_conf", {}).get("robot_interact", {})
        self.__robot_interact = {int(key): value for key, value in robot_interact.items()}
        self.__ann_threshold_multiple = room_conf.get("threshold_multiple") or 0  # 公告阈值倍率

        super().refresh_room_conf(service, room_conf)
