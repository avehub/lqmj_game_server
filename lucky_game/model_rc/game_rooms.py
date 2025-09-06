"""
游戏房间模型
"""
from tortoise.exceptions import OperationalError
from lucky_game.model_db.main import GameRooms
from lucky_game.model_rc.base_rc import BaseCommonRC
from nsanic.libs.tool import json_parse
from lucky_game.handler.random_utils import generate_natural_random
from tortoise.transactions import in_transaction
from common.public.enum_const import DbKey
from common.public.common_class import CommonApi
from lucky_game.model_rc.base_clubs import BaseClubRC
from lucky_game.model_rc.base_user import BaseUserRC
from c_services.const.cs_enum_const import RoomStatus
from lucky_game.const.const import PlatForm, ReasonCostGold
from lucky_game.model_rc.extra_user_resource_changes import ExtraUserResourceChangesRC
from lucky_game.model_rc.extra_club_event import ExtraClubEventRC
from nsanic.libs import tool_dt
from common.public.enum_const import CacheKey
from lucky_game.model_rc.club_group import ClubGroupRC
from tortoise.expressions import F
from c_services.cs_mahjong.const import PlayType


class GameRoomsRC(BaseCommonRC):
    db_model = GameRooms
    tb_name = db_model.sheet_name()

    KEY_ROOM_ID = 'room_id'
    KEY_CLUB_ID = 'club_id'
    SESSION_KEY = "room_player"
    SESSION_DISK_KEY = "room_player_uid"  # 单个游戏房间号内的用户ID集合
    SESSION_ROOM_KEY = "game_room"  # 游戏房间信息缓存
    SESSION_ROOM_USER_KEY = "game_room_user"  # 游戏房间中的用户ID集合
    SESSION_ROOM_NUMBER_KEY = "game_room_number"  # 游戏中的房间ID集合
    SESSION_USER_JOIN_ROOM_KEY = "user_join_room"  # 用户加入的房间ID集合
    NULL_MEG = "房间已解散"
    RULE_DETAILS = {
        "shang_xia_ji": {0, 1},  #上下鸡选项 0未选 1选
        "ben_ji": {0, 1},  # 本鸡选项  0未选 1选
        "wu_gu_ji": {0, 1},  #乌骨鸡选项 1选 0未选
        "man_tang_ji": {0, 1},  #满堂鸡选项 0未选 1选
        "chong_feng_ji": {0, 1},  #冲锋鸡选项 0未选 1选
        "zhan_ji": {0, 1},  #站鸡选项 0未选 1选
        "jian_gang_san": {0, 1},  #见杠三选项 0未选 1选
        "bao_ting": {0, 1},  #报听选项 0未选 1选
        "bi_men_yi_shou": {0, 1},  #必闷一手选项 0未选 1选
        "shang_ga": {0, 1},  #估卖选项 0未选 1选
        "gu_mai_score": {0, 1, 2, 3, 4, 5},  #所选卖分 0自由分 1-5对应1-5分
        "suo_de_jia_1": {0, 1},  #所得加1选项 0未选 1选
        "hu_pai_ti_shi": {0, 1},  #胡牌提示  捡漏血流才有选项 0未选 1选  闷胡血流固定是1
        "huang_zhuang_bu_huang_ji": {0, 1},  #黄庄不黄鸡杠 0未选 1选
        "four_card_bao_ting": {0, 4},  #四张报听 0未选 4选
        "xiao_pai_bi_men": {0, 1},  #小牌必闷  闷胡血流才有 0未选 1选  捡漏血流固定是1
        "tui_zhang_can_hu": {0, 1},  #退张可开  闷胡血流才有 0未选 1选  捡漏血流固定是0
        "bao_ting_bi_men": {0, 1},  #报听必闷   闷胡血流才有 0未选 1选  捡漏血流固定是0
        "exchange_three": {0, 1, 2, 3},  #是否换三张  0不换 1换三张 2豹子换 3 黄牌换
        "exchange_cards_type": {0, 1, 2},  # 换三张方式  1任意牌 2同色牌
        "exchange_first": {0, 1},  # 是否换三张优先 0否 1是
    }
    # 毕节麻将
    RULE_DETAILS_BJMJ = RULE_DETAILS | {
        "yuan_bao": {0, 1},  #原报 0未勾选 1勾选
        "qing_yi_se_extra_add": {0, 1},  #清一色额外+5 0未选 1选
        "yin_ji": {0, 1},  #银鸡 0未勾选 1勾选
        "lian_zhuang": {0, 1},  #连庄 0未勾选 1勾选
    }
    # 贵阳麻将（两丁拐、三丁拐）
    RULE_DETAILS_GYMJ = RULE_DETAILS | {
        "yuan_bao": {0, 1},  #原报 0未勾选 1勾选
        "shu_zi_ji": {0, 1},  #数字鸡 0未勾选 1勾选
        "yin_ji": {0, 1},  #银鸡 0未勾选 1勾选
    }
    # 遵义麻将（玄同麻将）
    RULE_DETAILS_ZYMJ = RULE_DETAILS | {
        "yuan_bao": {0, 1},  #原报 0未勾选 1勾选
        "yi_wan_ji": {0, 1},  #一万鸡 0未勾选 1勾选
        "xi_pai_score": {25, 100},  #喜牌100分 25未勾选 100勾选
        "wu_gu_ji_score": {2, 3},  #乌骨鸡3分 2未勾选 3勾选
        "after_peng_can_bao_ting": {0, 1},  #碰牌报听 0未勾选 1勾选
        "lian_zhuang": {0, 1},  #连庄 0未勾选 1勾选
    }

    @classmethod
    async def get_play_rule(cls, play_type: int):
        if play_type in [PlayType.JIAN_LOU_XUE_LIU, PlayType.AN_LONG_XUE_ZHAN]:
            return cls.RULE_DETAILS
        elif play_type in [PlayType.GUI_YANG_4, PlayType.GUI_YANG_3, PlayType.GUI_YANG_2]:
            return cls.RULE_DETAILS_GYMJ
        elif PlayType.BI_JIE_MJ == play_type:
            return cls.RULE_DETAILS_BJMJ
        elif PlayType.ZUN_YI_LAI_ZI == play_type:
            return cls.RULE_DETAILS_ZYMJ

    @classmethod
    async def cache_room_player_up(cls, room_id, value=1):
        return await cls.conf.rds.incr(f"{cls.SESSION_KEY}:{room_id}", value)

    @classmethod
    async def cache_room_player_get(cls, room_id):
        data = await cls.conf.rds.get_item(f"{cls.SESSION_KEY}:{room_id}")
        if isinstance(data, bytes):
            data = json_parse(data.decode())
        return data

    @classmethod
    async def cache_room_set(cls, room_id, value):
        return await cls.conf.rds.set_item(f"{cls.SESSION_ROOM_KEY}:{room_id}", value)

    @classmethod
    async def cache_room_get(cls, room_id):
        data = await cls.conf.rds.get_item(f"{cls.SESSION_ROOM_KEY}:{room_id}")
        if isinstance(data, bytes):
            data = json_parse(data.decode())
        return data

    @classmethod
    async def cache_user_room_get(cls, uid):
        data = await cls.conf.rds.smembers(f"{cls.SESSION_USER_JOIN_ROOM_KEY}:{uid}")
        return [p.decode('utf-8') for p in data]

    @classmethod
    async def cache_room_drop(cls, room_id):
        return await cls.conf.rds.del_item(f"{cls.SESSION_ROOM_KEY}:{room_id}")

    @classmethod
    async def unique_room_id(cls, num: int = 6):
        """生成唯一房间ID"""
        while True:
            room_id = generate_natural_random(num)
            has = await cls.conf.rds.sismember(cls.SESSION_ROOM_NUMBER_KEY, room_id)
            if not has:
                await cls.conf.rds.sadd(cls.SESSION_ROOM_NUMBER_KEY, room_id)
                return room_id

    @classmethod
    async def before_room(cls, club_id: int, uid: int):
        """可以在加入房间前做一些操作"""
        # 获取除隔离组用户以外的房间
        not_join_room = set()
        on_line_ids = await cls.get_online_user_group(uid, club_id)
        if not on_line_ids:
            return not_join_room
        # 过滤出在房间内的用户
        u_ids = await cls.get_room_user_group(on_line_ids)
        cls.conf.log.info("获取当前在房间内用户ID", u_ids)
        if not u_ids:
            return not_join_room
        for uid in u_ids:
            room_id = await cls.cache_user_room_get(uid)
            if room_id:
                not_join_room.update(room_id)
        cls.conf.log.info("获取用户所在隔离组房间ID", not_join_room)
        return not_join_room

    @classmethod
    async def get_online_user_group(cls, uid: int, club_id: int = 0):
        """获取当前用户所在隔离组的其他在线用户ID"""
        # 获取用户所在的所有隔离组关联用户ID
        sta, group_ids = await ClubGroupRC.check_uid_by_club(
            uid=uid,
            club_id=club_id,
        )
        cls.conf.log.info("获取用户所在所有隔离组关联用户ID", sta, group_ids)
        if not sta:
            return []
        # 过滤隔离组内在线用户
        on_line_ids = await BaseUserRC.get_online_uid(group_ids)
        cls.conf.log.info("获取用户所在隔离组在线的用户ID", on_line_ids)
        return on_line_ids


    @classmethod
    async def create_game_room(cls, platform: int, creator: int, rule_details: dict,
                               play_type: int, club_id: int = 0, **kwargs):
        total_round = kwargs.get("total_round", 0)
        """创建游戏房间"""
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                room_data = {
                    "club_id": club_id,
                    "room_id": await cls.unique_room_id(6),
                    "creator": creator,
                    "platform": platform,
                    "play_type": play_type,
                    "total_round": total_round,
                    "rule_details": rule_details,
                    "max_player": kwargs.get("max_player"),
                    "pay_type": kwargs.get("pay_type"),
                    "price": kwargs.get("price"),
                    "cs_type": kwargs.get("cs_type"),
                    "is_location": kwargs.get("is_location"),
                    "is_friend": kwargs.get("is_friend"),
                    "room_type": kwargs.get("room_type"),
                    "status": kwargs.get("status", 0),
                    "round_num": kwargs.get("round_num", 0),
                }
                new_room = await cls.db_model.add_one(room_data)
                if not new_room:
                    return None, "创建失败"
                # 预扣除房卡
                room_card_sta, e = await cls.settle_room_card(room_data)
                if not room_card_sta:
                    return False, e
        except OperationalError as e:
            return None, f"房间创建失败: {str(e)}"
        return room_data["room_id"], "成功"

    @classmethod
    async def settle_room_card(cls, room_data):
        """结算房卡"""
        key = "room_card"
        userinfo = await BaseUserRC.cache_by_pk(room_data["creator"])
        if room_data["club_id"] and room_data["club_id"] > 0:
            # 扣除茶馆基金
            if room_data["pay_type"] == 2:
                up_room_card = await BaseClubRC.update_club_int_field(
                    room_data["club_id"],
                    key,
                    room_data["price"],
                    "sub"
                )
            else:
                up_room_card = await ExtraUserResourceChangesRC.change_user_resource(
                    room_data["creator"],
                    key,
                    room_data['price'],
                    "sub",
                    reason=ReasonCostGold.CLUB_ROOM_CARD_TICKETS
                )
            # 记录茶馆事件
            event_type = ExtraClubEventRC.EVENT_TYPE["FUND_CONSUME"]
            event_msg = ExtraClubEventRC.EVENT_MSG[event_type].format(
                name=userinfo["name"],
                uid=userinfo["uid"],
                price=room_data["price"],
                play_type=room_data["play_type"],
                room_id=room_data["room_id"],
            )
            add_club_behavior, _ = await ExtraClubEventRC.create_event(
                room_data["club_id"],
                event_type,
                room_data["creator"],
                event_msg,
            )
        else:
            # 扣除黄钻
            if room_data["platform"] == PlatForm.WECHAT_MINI_GAME:
                key = "yellow_diamond"
            up_room_card = await ExtraUserResourceChangesRC.change_user_resource(
                room_data["creator"],
                key,
                room_data['price'],
                "sub",
                reason=ReasonCostGold.CLUB_YELLOW_DIAMOND_TICKETS
            )
        if not up_room_card:
            return False, "房卡结算失败"
        return True, "成功"

    @classmethod
    async def refund_room_card(cls, room_id: int, **kwargs):
        """回退房卡"""
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                room_data, e = await cls.get_game_room_by_room_id(room_id)
                if not room_data or room_data["status"]:
                    return False, e
                key = "room_card"
                if room_data["club_id"] and room_data["club_id"] > 0:
                    # 退还茶馆基金
                    if room_data["pay_type"] == 2:
                        up_room_card = await BaseClubRC.update_club_int_field(
                            room_data["club_id"],
                            key,
                            room_data["price"],
                            "add"
                        )
                    else:
                        up_room_card = await ExtraUserResourceChangesRC.change_user_resource(
                            room_data["creator"],
                            key,
                            room_data['price'],
                            "add",
                            reason=ReasonCostGold.CLUB_ROOM_CARD
                        )
                    # 删除茶馆事件记录
                    event_type = ExtraClubEventRC.EVENT_TYPE["FUND_CONSUME"]
                    add_club_behavior, _ = await ExtraClubEventRC.delete_event(
                        room_data["club_id"],
                        event_type,
                        room_data["creator"],
                    )
                else:
                    # 退还黄钻
                    if room_data["platform"] == PlatForm.WECHAT_MINI_GAME:
                        key = "yellow_diamond"
                    up_room_card = await ExtraUserResourceChangesRC.change_user_resource(
                        room_data["creator"],
                        key,
                        room_data['price'],
                        "add",
                        reason=ReasonCostGold.CLUB_YELLOW_DIAMOND
                    )
                if not up_room_card:
                    return False, "房卡回退失败"
        except OperationalError as e:
            return False, f"房卡回退失败: {str(e)}"
        return True, "成功"

    @classmethod
    async def delete_game_room(cls, room_id: int, delete: bool = False):
        """删除游戏房间"""
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                if delete:
                    await cls.db_model.filter(room_id=room_id).delete()
                    sta = True
                else:
                    sta, _ = await cls.update_game_room(room_id, status=RoomStatus.T_CLOSED)
                if not sta:
                    return False, cls.NULL_MEG
                # TODO 游戏战绩标记

                # 删除缓存
                uids = await cls.conf.rds.smembers(f"{cls.SESSION_DISK_KEY}:{room_id}")
                if uids:
                    uids = await CommonApi.bytes_by_int_list(uids)
                    for uid in uids:
                        await cls.conf.rds.srem(cls.SESSION_ROOM_USER_KEY, uid)
                        await cls.conf.rds.drop_hash(CacheKey.IN_SERVICE, uid)
                        await cls.conf.rds.srem(cls.SESSION_USER_JOIN_ROOM_KEY, uid)
                await cls.conf.rds.del_item(f"{cls.SESSION_DISK_KEY}:{room_id}")
                await cls.conf.rds.srem(cls.SESSION_ROOM_NUMBER_KEY, room_id)
                await cls.cache_room_drop(room_id)
        except OperationalError as e:
            return False, f"房间删除失败: {str(e)}"
        return True, "成功"

    @classmethod
    async def update_game_room(cls, room_id: int, **kwargs):
        """更新房间信息"""
        try:
            room, e = await cls.get_game_room_by_room_id(room_id)
            if not room:
                return False, e
            valid_fields = ["status", "player_count", "rule_details", "play_type", "max_player", "pay_type", "price",
                            "cs_type", "round_num"]
            update_data = {k: v for k, v in kwargs.items() if k in valid_fields}
            if update_data:
                await cls.db_model.filter(room_id=room_id).update(**update_data)
            # 删除缓存
            await cls.cache_room_drop(room_id)
        except OperationalError as e:
            return False, f"房间更新失败: {str(e)}"
        return True, "成功"

    @classmethod
    async def get_game_room_by_room_id(cls, room_id: int):
        """根据ID获取房间详情"""
        try:
            room = await cls.cache_room_get(room_id)
            if not room:
                room = await cls.db_model.get_or_none(room_id=room_id).values()
                if not room:
                    return None, cls.NULL_MEG
                await cls.cache_room_set(room_id, room)
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return room, "成功"

    @classmethod
    async def get_game_rooms_by_filter(cls, club_id: int = None, status: any = None, creator: int = None,
                                       cs_type: int = None, not_room_id: any = None, play_type: any = None,
                                       full: bool = False):
        """多条件查询房间列表"""
        try:
            query = {}
            if club_id is not None:
                query["club_id"] = club_id
            if status is not None:
                if isinstance(status, list):
                    query["status__in"] = status
                else:
                    query["status"] = status
            if creator is not None:
                query["creator"] = creator
            if play_type is not None:
                if isinstance(play_type, list):
                    query["play_type__in"] = play_type
                else:
                    query["play_type"] = play_type
            if cs_type is not None:
                query["cs_type"] = cs_type
            if not_room_id is not None:
                query["room_id__not_in"] = not_room_id
            if full:
                query["round_num"] = F("total_round")
            rooms = await cls.db_model.filter(**query).order_by("status").values()
            if not rooms:
                return [], "未找到符合条件的房间"
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return rooms, "成功"

    @classmethod
    async def join_room(cls, room_data: dict, uid: int):
        """加入房间"""
        try:
            if room_data["status"] != 0:
                return False, "房间已满"
            room_id = room_data["room_id"]
            max_player = room_data["max_player"]
            sta = await cls.conf.rds.sadd(f"{cls.SESSION_DISK_KEY}:{room_id}", uid)
            if sta == 0:
                return False, "用户已加入房间或加入房间失败"
            disk_uid = await cls.conf.rds.smembers(f"{cls.SESSION_DISK_KEY}:{room_id}")
            if len(disk_uid) > max_player:
                await cls.conf.rds.srem(f"{cls.SESSION_DISK_KEY}:{room_id}", uid)
                return False, "房间已满"
            await cls.conf.rds.sadd(cls.SESSION_ROOM_USER_KEY, uid)
            await cls.conf.rds.sadd(f"{cls.SESSION_USER_JOIN_ROOM_KEY}:{uid}", room_id)
        except OperationalError as e:
            return False, f"加入房间失败: {str(e)}"
        return True, "成功"

    @classmethod
    async def leave_room(cls, room_id: int, uid: int):
        """离开（解散）房间"""
        try:
            room_data, e = await cls.get_game_room_by_room_id(room_id)
            if not room_data:
                return False, e
            if room_data['status'] in [RoomStatus.T_PLAYING, RoomStatus.T_RECHARGE_ING]:
                return False, "离开房间状态异常"
            sta = await cls.conf.rds.srem(f"{cls.SESSION_DISK_KEY}:{room_id}", uid)
            if sta == 0:
                return False, "用户已离开房间或离开房间失败"
            if room_data['creator'] == uid:
                # 关闭房间
                await cls.update_game_room(room_id, status=RoomStatus.T_CLOSED)
                await cls.conf.rds.srem(cls.SESSION_ROOM_NUMBER_KEY, room_id)
                await cls.cache_room_drop(room_id)
            await cls.conf.rds.srem(cls.SESSION_ROOM_USER_KEY, uid)
            await cls.conf.rds.drop_hash(CacheKey.IN_SERVICE, uid)
            await cls.conf.rds.srem(cls.SESSION_USER_JOIN_ROOM_KEY, uid)
        except OperationalError as e:
            return False, f"离开房间失败: {str(e)}"
        return True, "成功"

    @classmethod
    async def get_room_player(cls, room_id: int):
        """获取房间玩家"""
        try:
            room_data, e = await cls.get_game_room_by_room_id(room_id)
            if not room_data:
                return None, e
            player = await cls.conf.rds.smembers(f"{cls.SESSION_DISK_KEY}:{room_id}")
            if player:
                player = await CommonApi.bytes_by_int_list(player)
        except OperationalError as e:
            return None, f"获取房间玩家失败: {str(e)}"
        return player, "成功"

    @classmethod
    async def get_room_user_all(cls):
        """获取所有在房间用户"""
        try:
            data = await cls.conf.rds.smembers(cls.SESSION_ROOM_USER_KEY)
            if data:
                data = [p.decode('utf-8') for p in data]
        except OperationalError as e:
            return None, f"获取房间玩家失败: {str(e)}"
        return data

    @classmethod
    async def get_room_user_group(cls, u_ids: list):
        """过滤隔离组内所有在房间用户"""
        ids = set()
        data = await cls.get_room_user_all()
        cls.conf.log.info("当前Redis中在房间内的用户ID:", data)
        if data:
            for uid in u_ids:
                if str(uid) in data or uid in data:
                    ids.add(uid)
        return ids


    @classmethod
    async def check_uid_room_user(cls, uid: int):
        """检查用户是否在房间"""
        try:
            sta = await cls.conf.rds.sismember(cls.SESSION_ROOM_USER_KEY, uid)
        except OperationalError as e:
            return None, f"获取房间玩家失败: {str(e)}"
        return sta, "成功"

    @classmethod
    async def abnormal_room(cls, room_id: int, msg: str = "房间异常"):
        """房间异常情况处理"""
        try:
            # 退还房卡
            await cls.refund_room_card(room_id)
            # 关闭房间
            await cls.delete_game_room(room_id)
            # 记录日志
            # cls.conf.info_log(msg + f"房间ID: {room_id}")
        except OperationalError as e:
            return None, f"房间处理失败: {str(e)}"
        return True, "成功"

    @classmethod
    async def abnormal_cs_type(cls, cs_type: int, msg: str = "服务异常"):
        """服务异常情况处理"""
        try:
            room_data, _ = await cls.get_game_rooms_by_filter(
                cs_type=cs_type,
                status=[
                    RoomStatus.T_IDLE,
                    RoomStatus.T_READY,
                    RoomStatus.T_PLAYING,
                    RoomStatus.T_RECHARGE_ING,
                    RoomStatus.T_CHECK_OUT,
                ]
            )
            failed_ids = []
            if room_data:
                for room in room_data:
                    sta, e = await cls.abnormal_room(room["room_id"], msg)
                    if not sta:
                        failed_ids.append(room["room_id"])
                        continue
        except OperationalError as e:
            return None, f"服务处理失败: {str(e)}"
        return True, failed_ids
