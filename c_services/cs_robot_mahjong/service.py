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

        self.__move_gen = LpyMoveGenerator()

    async def cal_action(self, _, data):
        """
        计算出牌动作
        """
        self.log_info("出牌", data)  # 日志记录

        # print("计算时间: {}, 从队列中读取数据: {}".format(self.calc_receive_time(), data))
        # print("######-> AI开始计算预测动作 <-######")
        cs_type = data.get("cs_type", None)
        cs_enum = ServiceEnum.find_member_by_val(cs_type)
        match cs_enum:
            case ServiceEnum.C_MAHJONG_FC:
                # 血流红中🀄
                action = self.calc_lpy_xl_actions(data)
            case _:
                return

        uid = data.get("uid", 1)
        cmd = data.get("cmd", None)
        # todo: 解析动作, 包装数据
        send_data = self.parse_receive_data(data)
        send_data["card"] = action
        self.log_info(f"计算出牌, tid: {send_data.get('tid')}, uid: {uid}, action: {action}")
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

        # 计算剩余卡牌并更新卡牌属性
        self.update_move_gen_attr(data)

        # 判断小七对是否进行碰操作
        action = self.__move_gen.calc_can_xqd_pong(data.get("curr_card"))
        # todo: 解析动作, 包装数据
        send_data = self.parse_receive_data(data)
        send_data["card"] = action
        self.log_info(f"计算碰, tid: {send_data.get('tid')}, uid: {uid}, action: {action}")
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

        self.update_move_gen_attr(data)

        # print("当前杠牌操作类型: {}".format(data.get("gang_type")))
        action = self.__move_gen.calc_can_gang(data.get("can_gang_cards"), data.get("gang_type"))
        # todo: 解析动作, 包装数据
        send_data = self.parse_receive_data(data)
        send_data["card"] = action
        send_data["gang_type"] = data.get("gang_type", 0)
        self.log_info(f"计算杠, tid: {send_data.get('tid')}, uid: {uid}, action: {action}")
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

    def calc_lpy_xl_actions(self, data):
        """
        todo: 老牌友血流红中🀄麻将
        """
        # print("============计算发财捉鸡出牌============")
        self.update_move_gen_attr(data)
        action = self.__move_gen.calc_xts_by_max_hu_type(data.get("others_cards_and_piles") or None)
        return action

    def update_move_gen_attr(self, data):
        self.__move_gen.update_attr(
            hand_cards=data.get("curr_hand_cards"),
            piles=data.get("piles"),
            left_count=data.get("left_count"),
            others_hand_cards=data.get("others_hand_cards"),
            remain_cards=data.get("remain_cards"),
            magic_card=data.get("magic_card", None),
        )
