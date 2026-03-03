# -*- coding: utf-8 -*-

import time

from collections import Counter

from c_services.base.base_server import JsonBaseServer
from c_services.const.cs_enum_const import CmdRobotCal
from c_services.cs_robot_mahjong.lpy_xts import LpyMoveGenerator
from c_services.cs_robot_mahjong.yxp import calc_best_cards_by_lpy_uid, calc_best_cards_by_lpy
from common.public.conf import C_SERVICE_SECRET_KEY
from common.public.enum_const import ServiceEnum


class RobotMahjongServer(JsonBaseServer):
    SUBSCRIBE_FANOUT = None

    def __init__(self):
        super().__init__()
        self.add_handlers({
            CmdRobotCal.CAL_ACTION.val: self.cal_action,
            CmdRobotCal.CAL_PONG.val: self.cal_pong,
            CmdRobotCal.CAL_GANG.val: self.cal_gang,
        })

    async def cal_action(self, _, data):
        """
        计算出牌动作
        """
        self.log_info("出牌", data)  # 日志记录

        # print("计算时间: {}, 从队列中读取数据: {}".format(self.calc_receive_time(), data))
        # print("######-> AI开始计算预测动作 <-######")
        cs_type = data.get("cs_type", None)
        cs_enum = ServiceEnum.find_member_by_val(cs_type)
        uid = data.get("uid", 1)
        cmd = data.get("cmd", None)
        if cs_type == ServiceEnum.C_MAHJONG_FC:
            # 血流红中🀄
            action = self.calc_lpy_xl_actions(data)
        else:
            # 贵阳麻将
            action = None

        # todo: 解析动作, 包装数据
        send_data = self.parse_receive_data(data)
        send_data["card"] = action
        self.log_info(f"计算出牌, tid: {send_data.get('tid')}, uid: {uid}, action: {action}")
        # print("输出封装预测后的数据: ", send_data)
        # print('当前预测玩家ID为: {}'.format(data['seat_id']))
        # print('AI输出预测打牌动作: {}'.format(action))
        # print()
        # print("%##############<< 预测下一位玩家出牌动作 >>##################%")
        await self.cs2cs_by_rmq(cs_enum, cmd, send_data, uid)

    async def cal_pong(self, _, data):
        """
        计算是否碰
        """
        self.log_info("碰牌", data)  # 日志记录

        cs_type = data.get("cs_type", None)
        cs_enum = ServiceEnum.find_member_by_val(cs_type)
        uid = data.get("uid", 1)
        cmd = data.get("cmd", None)

        # print("计算时间: {}, 从队列中读取数据: {}".format(self.calc_receive_time(), data))
        # print("######-> AI开始计算预测动作 <-######")

        mg = LpyMoveGenerator()
        # 计算剩余卡牌并更新卡牌属性
        remain_cards = self.calc_remain_cards(data.get("curr_hand_cards") or [], data.get("remain_cards") or {})
        mg.update_attr(
            hand_cards=data.get("curr_hand_cards"),
            piles=data.get("piles"),
            left_count=data.get("left_count"),
            others_hand_cards=data.get("others_hand_cards"),
            remain_cards=remain_cards,
            magic_card=data.get("magic_card", None),
        )

        # 判断小七对是否进行碰操作
        action = mg.calc_can_xqd_pong(data.get("curr_card"))
        # todo: 解析动作, 包装数据
        send_data = self.parse_receive_data(data)
        send_data["card"] = action
        self.log_info(f"计算碰, tid: {send_data.get('tid')}, uid: {uid}, action: {action}")
        # print("输出封装预测后的数据: ", send_data)
        # print('当前预测玩家ID为: {}'.format(data['seat_id']))
        # print('AI输出预测碰牌动作: {}'.format(action))
        # print()
        # print("%##############<< 预测下一位玩家出牌动作 >>##################%")

        await self.cs2cs_by_rmq(cs_enum, cmd, send_data, uid)

    async def cal_gang(self, _, data):
        """
        计算是否杠
        """
        self.log_info("杠牌", data)
        uid = data.get("uid", 1)
        cmd = data.get("cmd", None)
        cs_type = data.get("cs_type", None)
        cs_enum = ServiceEnum.find_member_by_val(cs_type)

        # print("计算时间: {}, 从队列中读取数据: {}".format(self.calc_receive_time(), data))
        # print("######-> AI开始计算预测动作 <-######")

        mg = LpyMoveGenerator()
        remain_cards = self.calc_remain_cards(data.get("curr_hand_cards") or [], data.get("remain_cards") or {})
        mg.update_attr(
            hand_cards=data.get("curr_hand_cards"),
            piles=data.get("piles"),
            left_count=data.get("left_count"),
            others_hand_cards=data.get("others_hand_cards"),
            remain_cards=remain_cards,
            magic_card=data.get("magic_card", None),
        )

        # print("当前杠牌操作类型: {}".format(data.get("gang_type")))
        action = mg.calc_can_gang(data.get("can_gang_cards"), data.get("gang_type"))
        # todo: 解析动作, 包装数据
        send_data = self.parse_receive_data(data)
        send_data["card"] = action
        send_data["gang_type"] = data.get("gang_type", 0)
        self.log_info(f"计算杠, tid: {send_data.get('tid')}, uid: {uid}, action: {action}")
        # print("输出封装预测后的数据: ", send_data)
        # print('预测玩家ID为: {}'.format(data['seat_id']))
        # print('AI输出预测杠牌动作: {}'.format(action))
        # print()
        # print("%##############<< 预测下一位玩家出牌动作 >>##################%")

        await self.cs2cs_by_rmq(cs_enum, cmd, send_data, uid)

    async def cal_yxp(self, _, data):
        """
        计算机器人摸好牌
        """
        self.log_info(data)  # 日志记录

        # print("计算时间: {}, 从队列中读取数据: {}".format(self.calc_receive_time(), data))
        # print("######-> AI开始计算预测最佳有效牌 <-######")

        trigger = data.get('trigger', False)
        if trigger:
            action, hu_cards = calc_best_cards_by_lpy_uid(data)
        else:
            action, hu_cards = calc_best_cards_by_lpy(data)

        send_data = self.parse_receive_data(data)
        send_data["card"] = action
        send_data["hu_cards"] = hu_cards  # 添加能胡卡牌

        self.log_info(f"计算有效牌, tid: {send_data.get('tid')}, uid: {send_data.get('uid')}, action: {action}")
        # print("输出封装预测后的数据: ", send_data)
        # print('当前预测摸牌ID为: {}'.format(send_data['self']))
        # print('AI输出预测摸牌: {}'.format(action))
        # print()
        # print("%##############<< 预测下一位摸好牌 >>##################%")

        # await self.send_child_name_lpy(send_data, action)

    @staticmethod
    def calc_receive_time():
        """
        记录当前计算时间
        """
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))

    @staticmethod
    def parse_receive_data(data):
        """
        解析接收数据
        """
        send_data = {
            "tid": data.pop("tid", 0),
            "cmd": data.pop("cmd", 0),
            "secret": C_SERVICE_SECRET_KEY,
        }
        return send_data

    @staticmethod
    def calc_remain_cards(curr_hand_cards, remain_cards):
        """
        统计剩余卡牌
        """
        # 出牌、碰牌、杠牌已经减去，此处不再计算
        if not remain_cards:
            return None
        cards_dict = Counter(curr_hand_cards)
        for card, nums in cards_dict.items():
            if remain_cards.get(str(card), 0):
                remain_cards[str(card)] -= nums
        return {int(key): value for key, value in remain_cards.items()}

    def calc_lpy_xl_actions(self, data):
        """
        todo: 老牌友血流红中🀄麻将
        """
        # print("============计算发财捉鸡出牌============")
        mg = LpyMoveGenerator()
        remain_cards = self.calc_remain_cards(data.get("curr_hand_cards") or [], data.get("remain_cards") or {})
        mg.update_attr(
            hand_cards=data.get("curr_hand_cards"),
            piles=data.get("piles"),
            left_count=data.get("left_count"),
            others_hand_cards=data.get("others_hand_cards"),
            remain_cards=remain_cards,
            magic_card=data.get("magic_card", None),
        )
        action = mg.calc_xts_by_max_hu_type(data.get("others_cards_and_piles") or None)
        return action
