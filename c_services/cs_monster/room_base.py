import random
from lucky_game.const import ReasonCostGold
from .player import Player
from .room_comb import RoomComb
from .rule import Rule
from .poker import Poker, Cards
from .const import FlowStatus, YuYinUniqueTurn1, YuYinUniqueTurn2
from c_services.const.cs_enum_const import CmdRoom, RoomStatus, CmdRobotMethods
from common.proto.py_pb2.ws_leisure import S2CTurnTo13, S2CPlayCards, \
    S2CPlayerInfo04Monster, S2CRoomInfo03Monster, S2CPickCards
from common.public.enum_const import StaCode, ServiceEnum, TaskId, MonsterCardType


class Room(RoomComb):
    """ 房间类，专注玩法实现 """
    use_universal_card = False

    def __init__(self, tid, service, room_conf, **extra_room_info):
        super().__init__(tid, service, room_conf, extra_room_info, Poker)
        self.__pick_len = 0
        self.__played_shi_fu = False  # 师傅是否出了
        self.__str_turn_cards = ""  # 用于字符串记录出牌顺序，如："JQK510"
        self.__record_skill_index = 0  # 记录特效index
        self.__record_voice_index = 0  # 记录语音index
        self.__tribulation_val = 0  # 磨难值，记录场上的牌
        self.__is_picked = False  # 是否捡过牌

        # model params
        self.action_history = []
        self.position_maps = {0: "down", 1: "right", 2: "up", 3: "left"}
        self.played_cards_dict = {"down": [], "right": [], "up": [], "left": []}
        self.bust_infos = {"down": False, "right": False, "up": False, "left": False}  # 破产记录
        self.universal_map_values = {"down": None, "right": None, "up": None, "left": None}

    def add_tribulation_val(self, val):
        self.__tribulation_val += val

    def cal_tribulation_val(self):
        return self.__tribulation_val

    def last_player(self, seat_id, with_cards=True):
        return self.next_player_reverse(seat_id, with_cards)

    async def round_start(self, *args, **kwargs):
        """ 一局开始 """
        await super().round_start(*args, **kwargs)
        await self.delay_func(1, self.deal_cards, Cards.FK_J)

    def __get_time_by_voice_or_skill(self, wait_time: int):
        wait_time = wait_time
        if self.__record_voice_index:
            wait_time = 4
        if self.__record_skill_index:
            wait_time = 3
        return wait_time

    async def turn_to_someone(self, player):
        """ 轮到某人 """
        if not player:
            self.info_log("没有下一家了")
            await self.enter_round_over()
            return
        self.curr_seat_id = player.seat_id
        player.clear_operand()

        if self.turn_cards:
            yao_de_qi = Rule.yao_de_qi(self.turn_cards[-1][-1], player.cards)
        else:
            yao_de_qi = player.cards

        wait_sec = 20

        notify_data = {
            "seat_id": player.seat_id,
            "seconds": wait_sec,
        }
        data_model = S2CTurnTo13.pb_model(**notify_data)
        await self.inner_broadcast(CmdRoom.TURN_TO, data_model, exclude_uid=player.uid)
        data_model.yao_de_qi = bool(yao_de_qi)
        data_model.played_shi_fu = self.__played_shi_fu
        await self.inner_send(player, CmdRoom.TURN_TO, data_model)

        self.info_log("turn_to", player.uid, yao_de_qi)
        if not yao_de_qi:
            if len(player.cards) == 1:  # 最后一张系统自动捡
                rs = 1
            else:
                rs = random.randint(2, 5) if player.is_robot else 4
            code, hint = await self.delay_func(rs, self.player_pick_cards, player)
            self.info_log(player.uid, "要不起捡牌", code, hint)
            return
        # 最后一张
        if len(player.cards) == 1:
            await self.delay_func(0.5, self.do_play_cards, player, [player.cards[0]], "最后一张系统帮出")
            return

        if player.is_robot:
            # 计算机器人出牌
            wait_time = random.randint(1, 3)
            wait_time = self.__get_time_by_voice_or_skill(wait_time)
            self.call_flow_robot(wait_time, self.robot_auto_play_cards, player)

        trustee_time = 1
        trustee_time = self.__get_time_by_voice_or_skill(trustee_time)

        self.__record_voice_index = 0
        self.__record_skill_index = 0
        self.call_flow_trustee(trustee_time, self.time_out_play_card, player, "call trustee")
        self.call_flow(wait_sec, self.time_out_play_card, player, "call flow")

    async def robot_auto_play_cards_old(self, player):
        """
        机器人自动出牌
        """
        # 机器人首出方块J
        if not self.table_cards:
            # 1.首出方块J
            await self.do_play_cards(player, [Cards.FK_J], "首出")
            return

        # 判断机器人是否为首出
        legal_actions = self.get_legal_cards(player)
        if not legal_actions:
            return
        # 判断是否满足主动捡牌条件
        last_action = self.action_history[-1][-1] if self.action_history else None
        # if self.__played_shi_fu and last_action != 621:
        if last_action != 621:
            legal_actions.append(621)

        # 模型请求ID: 桌子号+玩家UID
        other_hand_cards_left, other_hand_cards = self.get_other_left_cards(player)
        position = self.position_maps.get(player.seat_id - 1)
        req_model_id = "".join([str(player.tid), str(player.uid)])
        state = {
            "cs_type": self.service.service_type,
            "position": position,
            "seat_id": player.seat_id - 1,
            "hand_cards": player.cards,
            # "played_cards": self.played_cards_dict[position],
            "last_action": self.action_history[-1] if self.action_history else [],
            "legal_actions": legal_actions,
            "round_cards": [turn_card[1] for turn_card in self.turn_cards],
            "other_hand_cards": other_hand_cards,
            "action_history": self.action_history,
            "other_left_cards": other_hand_cards_left,
            "other_played_cards": self.get_other_played_cards(player),
            "universal_map_values": self.universal_map_values,
            "bust_infos": self.bust_infos,
            "req_model_id": req_model_id,
        }
        # 使用rmq推送机器人预测出牌或捡牌
        self.info_log(player.uid, "推送打妖怪机器人-[出牌]: ", req_model_id, legal_actions)
        await self.cs2cs_by_rmq(
            cs_type=ServiceEnum.ROBOT_MONSTER,
            c_code=CmdRobotMethods.CAL_ACTION.val,
            msg=state,
            uid=player.uid,
        )

    async def robot_auto_play_cards(self, player):
        """
        机器人自动出牌
        """
        # 机器人首出方块J
        if not self.table_cards:
            # 1.首出方块J
            await self.do_play_cards(player, [Cards.FK_J], "首出")
            return

        # 判断机器人是否为首出
        legal_actions = self.get_legal_cards(player)
        # 判断是否满足主动捡牌条件
        last_action = self.action_history[-1][-1] if self.action_history else None
        # if self.__played_shi_fu and last_action != 621:
        if last_action != 621:
            legal_actions.append(621)

        # 模型请求ID: 桌子号+玩家UID
        other_hand_cards_left, other_hand_cards = self.get_other_left_cards(player)
        next_ybq_cards1, next_ybq_cards2, next_ybq_cards3 = self.get_next_yao_bu_qi_cards()

        req_model_id = "".join([str(player.tid), str(player.uid)])
        state = {
            "cs_type": self.service.service_type,
            "seat_id": player.seat_id,
            "hand_cards": player.cards,
            "last_action": self.action_history[-1] if self.action_history else [],
            "legal_actions": legal_actions,
            "round_actions": [turn_card[1] for turn_card in self.turn_cards],
            "other_hand_cards": other_hand_cards,
            "action_history": self.action_history,
            "bust_infos": self.bust_infos,
            "next_ybq": next_ybq_cards1,
            "next_next_ybq": next_ybq_cards2,
            "next_next_next_ybq": next_ybq_cards3,
            "t_val_multiple": self.get_t_val_multiple(self.__tribulation_val),
            "req_model_id": req_model_id,
        }
        # 使用rmq推送机器人预测出牌或捡牌
        self.info_log(player.uid, "推送打妖怪机器人-[出牌]: ", req_model_id, legal_actions)
        await self.cs2cs_by_rmq(
            cs_type=ServiceEnum.ROBOT_MONSTER,
            c_code=CmdRobotMethods.CAL_ACTION.val,
            msg=state,
            uid=player.uid,
        )

    def get_next_yao_bu_qi_cards(self):
        next_p2 = None
        next_p3 = None

        next_p1 = self.next_player(self.curr_seat_id)
        if next_p1:
            next_p2 = self.next_player(next_p1.seat_id)
        if next_p2:
            next_p3 = self.next_player(next_p2.seat_id)

        cards1 = []
        cards2 = []
        cards3 = []
        if next_p1:
            cards1 = next_p1.pass_cards
        if next_p2:
            cards2 = next_p2.pass_cards
        if next_p3:
            cards3 = next_p3.pass_cards
        return cards1, cards2, cards3

    def get_other_left_cards(self, player):
        """
        获取其他玩家的手牌
        """
        other_hand_cards_left = {"down": 0, "right": 0, "up": 0, "left": 0}
        other_hand_cards = []
        for other_p in self.seats:
            if other_p == player:
                continue
            other_hand_cards.extend(other_p.cards)
            other_hand_cards_left[self.position_maps.get(other_p.seat_id - 1)] = len(other_p.cards)
        return other_hand_cards_left, other_hand_cards

    def get_other_played_cards(self, player):
        """
        获取其他玩家的出牌
        """
        curr_position = self.position_maps.get(player.seat_id - 1)
        played_cards_dict = {
            position: cards for position, cards in self.played_cards_dict.items()
            if position != curr_position
        }
        return played_cards_dict

    def get_legal_cards(self, player):
        if len(self.turn_cards) == 0:
            # 2.没有上家随出
            return [card for card in player.cards]
        can_chu_cards = Rule.legal_cards(self.turn_cards, player.cards)
        # 4.出要得起的牌
        return can_chu_cards

    async def play_card_by_rand(self, player):
        """ 随机出一张牌 """
        if not self.table_cards:
            # 1.首出方块J
            cards = [Cards.FK_J]
        else:
            can_chu_cards = self.get_legal_cards(player)
            if not can_chu_cards:
                self.info_log(player.seat_id, "随机出牌无牌可出")
                return
            cards = [can_chu_cards[0]]
        # 具体出牌
        await self.do_play_cards(player, cards, "随机出牌")

    async def pick_and_calc_score(self, p: Player):
        """ 捡牌后算分 """
        pick_len = self.__tribulation_val
        p.add_pick_len(pick_len)
        p.curr_pick_len = pick_len
        self.__pick_len += pick_len

        mine, other = Rule.cal_score(pick_len, self.base_score, self.max_player_count - self.ren_shu_count)
        t_val_multiple = self.get_t_val_multiple(pick_len)

        mine = int(mine * t_val_multiple)
        other = int(other * t_val_multiple)

        # 携带护盾卡的系统照常帮出。未携带玩家不够时全部赔付，其它玩家平分
        if not p.free_loss and p.gold + mine < 0:
            # 玩家自身灵石不足扣除 捡牌玩家向上取整
            mine = -p.gold
            other = int(p.gold // (self.max_player_count - self.ren_shu_count - 1))  # 得分玩家向下取整

        notify_info = {
            'seat_id': p.seat_id,
            'player_pick_len': p.pick_len,
            'curr_pick_len': p.curr_pick_len
        }

        # todo: 即时结算，更新玩家灵石： 1.此处使用事务更新 2.启动一个新的专门用于更新玩家资产的服务
        await self.instant_checkout(p, mine, other, notify_info, ReasonCostGold.CHECK_OUT_MONSTER_FIRST)
        data_model = S2CPickCards.pb_model(**notify_info)
        await self.inner_broadcast(CmdRoom.PICK_CARDS, data_model)

        self.clear_turn_cards()
        self.__is_picked = True
        self.__tribulation_val = 0

    def surpass_last_card(self, uid, last_card):
        """ 赢过上一张牌 """
        task_id = 0
        if Rule.is_shi_fu(last_card):
            task_id = TaskId.SURPASS_SHIFU_4
        elif Rule.is_yao_guai(last_card):
            task_id = TaskId.SURPASS_MONSTER_6
        if not task_id:
            return
        data = {
            "task_id": task_id,
            "add_val": 1,
            "uid": uid
        }
        self.add_task(data)

    async def do_trustee(self, p: Player):
        await super().do_trustee(p)  # 如果此处修改玩家状态未托管，说明玩家此前出与未托管中
        if p.seat_id == self.curr_seat_id and self.flow_status_is_equal(FlowStatus.T_IN_TURN_TO):
            if p.trustee:
                self.info_log(p.uid, "玩家主动托管出牌")
                if self.turn_cards and not Rule.yao_de_qi(self.turn_cards[-1][-1], p.cards):
                    return await self.player_pick_cards(p)
                await self.play_card_by_rand(p)
            else:
                self.info_log(p.uid, "轮到玩家出牌但是取消托管")
                self.cancel_timer_trustee()  # 取消托管timer

    async def player_play_cards(self, p, cards: list):
        """ 玩家出牌 """
        if not self.room_status_is_equal(RoomStatus.T_PLAYING):
            return StaCode.FORBID, "桌子状态非游戏中"
        if not self.flow_status_is_equal(FlowStatus.T_IN_TURN_TO):
            return StaCode.FLOW_ERR, "现在还不能出牌"
        if p.seat_id != self.curr_seat_id:
            return StaCode.NOT_YOUR_TURN, "未轮到你"
        if p.operand > 0:
            return StaCode.FORBID, "请勿重复操作"
        if len(cards) != 1:
            return StaCode.ERR_ARG, "只能出一张"
        if not Rule.contain(p.cards, cards):
            return StaCode.ERR_ARG, "客户端请求数据错误，不符合即定格式"
        card = cards[0]
        if not self.table_cards:
            if cards[0] != Cards.FK_J:
                return StaCode.FORBID, "开局必须出方块J"

        card = Cards.find_member_by_val(card)

        card_value = card.val
        if self.turn_cards:
            if not Rule.compare(card_value, self.turn_cards[-1][-1]):
                return StaCode.FORBID, "出牌不符合规则"

            if not p.is_robot:
                self.surpass_last_card(p.uid, self.table_cards[-1][-1])

        p.add_operand()

        # 封装模型参数
        self.action_history.append([card])
        self.played_cards_dict[self.position_maps.get(p.seat_id - 1)].append(card)

        if Rule.is_universal_card(card_value):
            if not self.turn_cards:
                card_value = Rule.XIAO_YAO  # 捡牌后首出万能牌算小妖
            else:
                last_card_value = self.table_cards[-1][-1]
                card_value = Rule.trans_universal_card_by_last_card(last_card_value)
            self.universal_map_values[self.position_maps.get(p.seat_id - 1)] = card_value

        p.rm_cards(cards)
        turn = [p.seat_id, card, card_value]
        self.add_turn_cards(turn)
        self.add_tribulation_val(1)
        self.add_table_cards(turn)

        self.info_log(p.uid, "出牌成功: ", cards)

        card_str = Rule.get_card_str(card_value)
        self.__str_turn_cards += card_str
        voice_index = self.get_voice_index_by_case()
        skill_index, skin_info = self.get_skill_movie_index_by_player_equip(p, card_value)

        self.__record_voice_index = voice_index
        self.__record_skill_index = skill_index

        if not self.__played_shi_fu and card_value == Rule.SHI_FU:
            self.__played_shi_fu = True
            self.__str_turn_cards = ""

        data = {
            "case_index": voice_index,
            "skill_index": skill_index,
            "turn_card": turn,
            # "t_val_multiple": str(self.get_t_val_multiple(len(self.turn_cards))),
            "t_val_multiple": str(self.get_t_val_multiple(self.__tribulation_val)),
            "tribulation_val": self.__tribulation_val,
        }
        data_model = S2CPlayCards.pb_model(**data)
        await self.inner_broadcast(CmdRoom.PLAY_CARDS, data_model)

        await self.play_skin_equip_card_get_fairy_stone(p, skin_info)
        return StaCode.PASS, ''

    def get_voice_index_by_case(self):
        """
        根据情景获取语音的index
        """
        if self.__is_picked:  # 去掉万能牌后捡牌后语音不播放
            return -1
        if self.__played_shi_fu:
            yu_yin_data = YuYinUniqueTurn2  # 师傅出了就是第二轮
        else:
            yu_yin_data = YuYinUniqueTurn1  # 师傅未出就是第一轮
        turn_len = len(self.__str_turn_cards)

        for data in yu_yin_data:
            if len(data.phrase) < turn_len:
                continue
            if data.phrase[:turn_len] != self.__str_turn_cards:
                continue
            return data.val
        return -1

    def get_skill_movie_index_by_player_equip(self, p: Player, card_value):
        """ 根据玩家装备皮肤播放特效 """
        if not self.__played_shi_fu and not self.__is_picked:
            return 0, {}
        match card_value:
            case Rule.SHI_FU:
                idx = MonsterCardType.TANG_SANZANG.val
            case Rule.WU_KONG:
                idx = MonsterCardType.SUN_WUKONG.val
            case Rule.BA_JIE:
                idx = MonsterCardType.ZHU_BAJIE.val
            case Rule.SHA_SENG:
                idx = MonsterCardType.SHA_WUJING.val
            case _:
                return 0, {}

        skin_info = p.skin_equip_info.get(str(idx))
        if not skin_info:
            return 0, {}
        print("当前播放皮肤信息：", skin_info)
        skin_equip_id = skin_info.get("skin_id")
        if p.skin_movie_is_play(skin_equip_id):
            return 0, skin_info

        p.set_skin_movie_is_play(skin_equip_id, True)  # 只播一次
        # skill_id = SKIN_SKILL_MOVIE_MAP.get(skin_equip_id) or 0
        return skin_equip_id, skin_info

    async def play_skin_equip_card_get_fairy_stone(self, p: Player, skin_info: dict):
        """ 打出装备皮肤对应的牌，获得底注 * 加成灵石 """
        # todo: 打出牌是额外加成与特效是否会冲突？？？
        addition = skin_info.get("skin_addition") or 0
        if addition > 0:
            gold_count = int(self.base_score * addition)
            if not p.is_robot:
                await self.update_user_gold(p, gold_count, ReasonCostGold.SKIN_EQUIP_EFFECT)
            p.add_skin_addition_num(gold_count)
            notify_info = {
                "check_infos": [
                    {
                        "seat_id": p.seat_id,
                        "win_gold": gold_count,
                        "res_gold": p.gold
                    }
                ]
            }
            print("下发皮肤加成！！！", addition)
            data_model = S2CPickCards.pb_model(**notify_info)
            await self.inner_broadcast(CmdRoom.PICK_CARDS, data_model)

    async def pick_last_cards(self):
        """ 捡最后一次 """
        curr_player = self.curr_player()
        player_cards_len = len(curr_player.cards)
        # pick_len += player_cards_len

        self.add_tribulation_val(player_cards_len)
        await self.pick_and_calc_score(curr_player)
        await self.enter_round_over()
        return StaCode.PASS, ''

    async def player_pick_cards(self, p):
        """ 玩家捡牌 """
        # if not self.__played_shi_fu:
        #     return StaCode.RULE_ERR, "牌桌上必须出过师傅才能捡牌"
        if p.seat_id != self.curr_seat_id:
            return StaCode.FORBID, "未轮到你"
        if p.operand > 0:
            return StaCode.FORBID, "请勿重复操作"
        if not self.turn_cards:
            return StaCode.FORBID, "首出不能捡牌"

        p.add_operand()
        p.add_pass_cards(self.turn_cards[-1][-2])  # 记录捡牌前一张牌

        # 封装模型参数，[621]表示捡牌操作
        self.action_history.append([621])

        # pick_len = len(self.turn_cards)
        next_player = self.next_player(self.curr_seat_id)
        self.info_log(p.uid, "捡牌")
        if not next_player:  # 如果没有下一个玩家，捡完牌结束
            return await self.pick_last_cards()

        await self.pick_and_calc_score(p)

        if p.gold <= 0 and not p.free_loss:
            self.call_flow(0, self.notify_is_revenge, p)
        else:
            self.call_flow(2, self.turn_end, True)

        return StaCode.PASS, ''

    async def player_give_up(self, player):
        """ 玩家认输 """
        if player.is_out:
            return
        self.bust_infos[self.position_maps.get(player.seat_id - 1)] = True
        await super().player_give_up(player)

    def judge_is_win_or_lose(self, field: str = 'pick_len'):
        """
        根据实际输赢 判断 输赢
        2025/4/14修改
        """
        sort_player_list = []
        for p in self.seats:
            sort_player_list.append(p)
            if p.is_robot:
                continue
            if p.actual_score >= 0:
                p.is_win = 1
            else:
                p.is_win = 0

        sort_player_list.sort(key=lambda p: p.actual_score, reverse=True)

        if sort_player_list[0].actual_score == sort_player_list[1].actual_score:
            if getattr(sort_player_list[0], field) > getattr(sort_player_list[1], field):
                return sort_player_list[1].seat_id
        return sort_player_list[0].seat_id

    @staticmethod
    def serialize_player_info(room_player_info):
        return S2CPlayerInfo04Monster.pb_model(room_player_info)

    def serialize_room_info(self):
        room_info = self.room_info()
        return S2CRoomInfo03Monster.pb_model(**room_info)

    def room_info(self):
        """ 子类重写该方法 """
        data = super().room_info()
        data["turn_cards"] = self.turn_cards
        data["played_shi_fu"] = self.__played_shi_fu
        curr_player = self.curr_player()
        if (curr_player and not curr_player.is_robot and
                self.flow_status_is_equal(FlowStatus.T_IN_TURN_TO) and self.left_seconds() > 0):
            yao_de_qi = True
            if self.turn_cards:
                yao_de_qi = Rule.yao_de_qi(self.turn_cards[-1][-1], curr_player.cards)
            data["yao_de_qi"] = yao_de_qi
        data["t_val_multiple"] = str(self.get_t_val_multiple(self.__tribulation_val))
        data["tribulation_val"] = self.__tribulation_val
        data["mean_gold_base"] = self.mean_gold_base
        return data

    def clear_data_round_over(self):
        self.__is_picked = False
        self.clear_turn_cards()
        self.clear_table_cards()
        self.action_history.clear()

    def clear_room(self):
        """ 清理房间 """
        self.__pick_len = 0
        self.__played_shi_fu = False  # 师傅是否出了
        self.__str_turn_cards = ""  # 用于字符串记录出牌顺序，如："JQK510"
        self.__record_skill_index = 0  # 记录特效index
        self.__record_voice_index = 0
        self.__tribulation_val = 0
        self.__is_picked = False

        # model params
        self.action_history = []
        self.position_maps = {0: "down", 1: "right", 2: "up", 3: "left"}
        self.played_cards_dict = {"down": [], "right": [], "up": [], "left": []}
        self.bust_infos = {"down": False, "right": False, "up": False, "left": False}
        self.universal_map_values = {"down": None, "right": None, "up": None, "left": None}
        super().clear_room()
