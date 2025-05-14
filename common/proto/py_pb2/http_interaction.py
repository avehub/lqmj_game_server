from nsanic.libs.tool import json_encode
from common.proto.pb2 import http_interaction_pb2
from common.proto.py_pb2 import http_player_vault
from promising_game.const import AwardType


class PbSignInConf():

    @classmethod
    def pb_model(cls, data: dict, award_type=AwardType.SIGN_IN_RF):
        """ 消息模型(非序列化) """
        match award_type:
            case AwardType.SIGN_IN_RF:
                __proto = http_interaction_pb2.S2CRaffleSignConf()

                sa_list = data.get("sign_conf") or []
                for sa_data in sa_list:
                    sd = __proto.sign_in_conf.sign_conf.add()
                    pack_sign_conf(sd, **sa_data)

                si_list = data.get("sign_item") or []
                for si_data in si_list:
                    sd = __proto.sign_in_conf.sign_item.add()
                    pack_sign_conf(sd, **si_data)

                si_dict = data.get("sign_data") or {}
                pack_sign_data(__proto.sign_in_conf, **si_dict)

                ra_list = data.get("raffle_conf") or []
                for ra_data in ra_list:
                    rd = __proto.raffle_conf.add()
                    pack_raffle_conf(rd, **ra_data)

                lu_dict = data.get("luck_data") or {}
                pack_luck_data(__proto, **lu_dict)
                return __proto

            case _:
                __proto = http_interaction_pb2.S2CSignInConf()

                sa_list = data.get("sign_conf") or []
                for sa_data in sa_list:
                    sd = __proto.sign_conf.add()
                    pack_sign_conf(sd, **sa_data)

                si_dict = data.get("sign_data") or {}
                pack_sign_data(__proto, **si_dict)

                return __proto


def pack_raffle_conf(obj, **kwargs):
    obj.award_level = kwargs.get("award_level") or 0
    conf_items = kwargs.get("conf_items") or []

    for item in conf_items:
        if item:
            gd = obj.goods_items.add()
            http_player_vault.pack_goods_items(gd, **item)


def pack_sign_conf(obj, **kwargs):
    obj.achieve_value = kwargs.get("achieve_value") or 0
    obj.award_level = kwargs.get("award_level") or 0
    obj.img_url = kwargs.get("img_url") or ''

    conf_items = kwargs.get("conf_items") or []
    for item in conf_items:
        if item:
            gd = obj.goods_items.add()
            http_player_vault.pack_goods_items(gd, **item)


def pack_sign_data(obj, **kwargs):
    obj.sign_data.sign_achieved = kwargs.get("sign_achieved") or 0
    obj.sign_data.sign_status = kwargs.get("sign_status") or 0
    obj.sign_data.sign_awards_sta = kwargs.get("sign_awards_sta") or '[]'
    obj.sign_data.sign_in_date = kwargs.get("sign_in_date") or '[]'


def pack_luck_data(obj, **kwargs):
    obj.luck_data.yun_shi = kwargs.get("yun_shi") or 0
    obj.luck_data.yun_shi_desc = kwargs.get("yun_shi_desc") or ''


class PbMail():

    @classmethod
    def pb_model(cls, data: list):
        """ 消息模型(非序列化) """
        __proto = http_interaction_pb2.S2CMail()

        for ma_data in data or []:
            sd = __proto.mail_items.add()
            pack_mail_data(sd, **ma_data)
        return __proto


def pack_mail_data(obj, **kwargs):
    obj.mail_id = kwargs.get("mail_id") or 0
    obj.mail_type = kwargs.get("mail_type") or 0
    obj.title = kwargs.get("title") or ''
    obj.content = kwargs.get("content") or ''
    obj.sender = kwargs.get("sender") or ''
    obj.receiver = kwargs.get("receiver") or 0
    obj.mail_sta = kwargs.get("mail_sta") or 0
    obj.attachment_sta = kwargs.get("attachment_sta") or 0
    obj.receive_time = kwargs.get("receive_time") or 0
    obj.exp_time = kwargs.get("exp_time") or 0
    attachment = kwargs.get("attachment") or []
    for item in attachment:
        if item:
            gd = obj.goods_items.add()
            http_player_vault.pack_goods_items(gd, **item)


class PbRaffle():

    @classmethod
    def pb_model(cls, data: dict):
        """ 消息模型(非序列化) """
        __proto = http_interaction_pb2.RaffleConf()

        pack_raffle_conf(__proto, **data)
        return __proto


class PbTask():
    PB_TASK_MODEL = None

    @classmethod
    def task_model(cls):
        if PbTask.PB_TASK_MODEL:
            PbTask.PB_TASK_MODEL.Clear()
            return PbTask.PB_TASK_MODEL
        PbTask.PB_TASK_MODEL = http_interaction_pb2.TaskConf()
        return PbTask.PB_TASK_MODEL

    @classmethod
    def pb_model(cls, data: dict):
        """ 消息模型(非序列化) """
        __proto = http_interaction_pb2.S2CTask()

        tc_list = data.get("task_conf") or []
        for sa_data in tc_list:
            sd = __proto.task_conf.add()
            pack_task_data(sd, **sa_data)

        ac_list = data.get("active_conf") or []
        for ra_data in ac_list:
            rd = __proto.active_conf.add()
            pack_sign_conf(rd, **ra_data)

        ad_dict = data.get("active_data") or {}
        pack_active_data(__proto, **ad_dict)
        return __proto


def pack_task_data(obj, **kwargs):
    obj.task_id = kwargs.get("task_id") or 0
    obj.task_type = kwargs.get("task_type") or 0
    obj.task_name = kwargs.get("task_name") or ''
    obj.achieve_value = kwargs.get("achieve_value") or 0
    obj.active_score = kwargs.get("active_score") or 0
    obj.task_sta = kwargs.get("task_sta") or 1
    obj.cur_value = kwargs.get("cur_value") or 0

    obj.jump_target = kwargs.get("jump_target") or 0
    target_data = kwargs.get("target_data") or ''
    obj.target_data = json_encode(target_data) if target_data else ''

    conf_items = kwargs.get("conf_items") or []
    for item in conf_items:
        if item:
            gd = obj.goods_items.add()
            http_player_vault.pack_goods_items(gd, **item)
    return obj


def pack_active_data(obj, **kwargs):
    obj.active_data.cur_active_score = kwargs.get("cur_active_score") or 0
    obj.active_data.active_awards_sta = kwargs.get("active_awards_sta") or '[]'


class PbRelief():

    @classmethod
    def pb_model(cls, data: dict):
        """ 消息模型(非序列化) """
        __proto = http_interaction_pb2.S2CRelief()

        pack_relief_conf(__proto, **data)
        return __proto


def pack_relief_conf(obj, **kwargs):
    obj.relief_count = kwargs.get("relief_count") or 1000000
    obj.relief_limit_count = kwargs.get("relief_limit_count") or 100000
    obj.relief_multiple = kwargs.get("relief_multiple") or 1
    obj.relief_times = kwargs.get("relief_times") or 0
    obj.relief_used_times = kwargs.get("relief_used_times") or 0


class PbAwards():

    @classmethod
    def pb_model(cls, data: dict):
        """ 消息模型(非序列化) """
        __proto = http_interaction_pb2.S2CAwards()

        pack_award_data(__proto, **data)
        return __proto


def pack_award_data(obj, **kwargs):
    obj.award_data.award_id = kwargs.get("award_id") or 0
    obj.award_data.award_type = kwargs.get("award_type") or 0
    obj.award_data.award_name = kwargs.get("award_name") or ''
    obj.award_data.receive_limit = kwargs.get("receive_limit") or 0
    obj.award_data.img_url = kwargs.get("img_url") or ''
    obj.award_data.receive_times = kwargs.get("receive_times") or 0
    conf_items = kwargs.get("conf_items") or []
    for item in conf_items:
        if item:
            gd = obj.award_data.goods_items.add()
            http_player_vault.pack_goods_items(gd, **item)


class PbMonopoly():

    @classmethod
    def pb_model(cls, data: dict, is_map=False, is_goods=False):
        """ 消息模型(非序列化) """
        if is_map:  # 地图返回
            __proto = http_interaction_pb2.S2CMonopolyMap()

            map_conf = data.get("map_conf") or []
            for i in map_conf:
                if i:
                    mc = __proto.map_conf.add()
                    pack_monopoly_map(mc, **i)

            __proto.position = data.get("position") or 0

        elif is_goods:  # 物资返回
            __proto = http_interaction_pb2.S2CMonopolyGoods()

            __proto.dice_count = data.get("dice_count") or 0
            __proto.five_count = data.get("five_count") or 0

            magic_conf = data.get("magic_conf") or []
            for i in magic_conf:
                if i:
                    mc = __proto.magic_conf.add()
                    http_player_vault.pack_goods_items(mc, **i)

        else:  # 行进返回
            __proto = http_interaction_pb2.S2CMonopolyPlayStep()

            steps_res = data.get("steps_res") or []
            for s in steps_res:
                if s:
                    sr = __proto.steps_res.add()
                    pack_monopoly_res(sr, **s)

            map_conf = data.get("map_conf") or []
            for i in map_conf:
                if i:
                    mc = __proto.monopoly_map.map_conf.add()
                    pack_monopoly_map(mc, **i)

            __proto.monopoly_map.position = data.get("position") or 0
            __proto.net_steps = data.get("net_steps") or 0
            __proto.cross_times = data.get("cross_times") or 0

        return __proto


def pack_monopoly_map(obj, **kwargs):
    obj.cell_id = kwargs.get("cell_id") or 0
    obj.cell_name = kwargs.get("cell_name") or ''
    obj.cell_type = kwargs.get("cell_type") or 0
    obj.event_id = kwargs.get("event_id") or 0
    obj.desc = kwargs.get("desc") or ''

    conf_items = kwargs.get("conf_items") or []
    for item in conf_items:
        if item:
            gd = obj.conf_items.add()
            http_player_vault.pack_goods_items(gd, **item)

def pack_monopoly_event(obj, **kwargs):
    obj.event_name = kwargs.get("event_name") or ''
    obj.ending_type = kwargs.get("ending_type") or 0
    obj.ending_desc = kwargs.get("ending_desc") or ''
    obj.desc = kwargs.get("desc") or ''
    obj.event_execute = kwargs.get("event_execute") or 0

    event_awards = kwargs.get("event_awards") or []
    for item in event_awards:
        if item:
            gd = obj.event_awards.add()
            http_player_vault.pack_goods_items(gd, **item)

def pack_monopoly_res(obj, **kwargs):
    cell_res = kwargs.get("cell_res") or {}
    pack_monopoly_map(obj.cell_res, **cell_res)

    dice_res = kwargs.get("dice_res") or []
    obj.dice_res.extend(dice_res)

    cross_start = kwargs.get("cross_start") or {}
    pack_monopoly_map(obj.cross_start, **cross_start)

    event_res = kwargs.get("event_res") or {}
    pack_monopoly_event(obj.event_res, **event_res)

    event_ex_res = kwargs.get("event_ex_res") or {}
    pack_monopoly_map(obj.event_ex_res, **event_ex_res)