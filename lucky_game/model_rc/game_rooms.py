"""
游戏房间模型
"""
from tortoise.exceptions import OperationalError
from lucky_game.model_db.main import GameRooms
from lucky_game.model_rc.base_rc import BaseCommonRC
from nsanic.libs.tool import json_encode, json_parse
from lucky_game.handler.random_utils import generate_natural_random
from tortoise.transactions import in_transaction
from common.public.enum_const import DbKey
from lucky_game.model_rc.base_clubs import BaseClubRC
from lucky_game.model_rc.base_user import BaseUserRC
from c_services.const.cs_enum_const import RoomStatus
from lucky_game.const.const import PlatForm


class GameRoomsRC(BaseCommonRC):
    db_model = GameRooms
    tb_name = db_model.sheet_name()

    KEY_ROOM_ID = 'room_id'
    KEY_CLUB_ID = 'club_id'
    SESSION_KEY = "room_player"
    SESSION_DISK_KEY = "room_player_uid"
    RULE_DETAILS = {
        "shang_xia_ji",
        "ben_ji",
        "wu_gu_ji",
        "man_tang_ji",
        "chong_feng_ji",
        "zhan_ji",
        "jian_gang_san",
        "bao_ting",
        "bi_men_yi_shou",
        "shang_ga",
        "gu_mai_score",
        "suo_de_jia_1",
        "hu_pai_ti_shi",
        "huang_zhuang_bu_huang_ji",
        "four_card_bao_ting",
        "xiao_pai_bi_men",
        "tui_zhang_can_hu",
        "bao_ting_bi_men",
        "exchange_three",
        "exchange_cards_type"
    }

    SHANG_XIA_JI = (0, 1)  #上下鸡选项 0未选 1选
    BEN_JI = (0, 1)  # 本鸡选项  0未选 1选
    WU_GU_JI = (0, 1)  # 乌骨鸡选项 0未选 1选
    MAN_TANG_JI = (0, 1)  # 满堂鸡选项 0未选 1选
    CHONG_FENG_JI = (0, 1)  # 冲锋鸡选项 0未选 1选
    ZHAN_JI = (0, 1)  # 站鸡选项 0未选 1选
    JIAN_GANG_SAN = (0, 1)  # 见杠三选项 0未选 1选
    BAO_TING = (0, 1)  # 报听选项 0未选 1选
    BI_MEN_YI_SHOU = (0, 1)  # 必闷一手选项 0未选 1选
    SHANG_GA = (0, 1)  # 估卖选项 0未选 1选
    GU_MAI_SCORE = (0, 1, 2, 3, 4, 5)  # 所选卖分 0自由分 1-5对应1-5分
    SUO_DE_JIA_1 = (0, 1)  # 所得加1选项 0未选 1选
    HU_PAI_TI_SHI = (0, 1)  # 胡牌提示  捡漏血流才有选项 0未选 1选  闷胡血流固定是1
    HUANG_ZHUANG_BU_HUANG_JI = (0, 1)  # 黄庄不黄鸡杠 0未选 1选
    FOUR_CARD_BAO_TING = (0, 4)  # 四张报听 0未选 4选
    XIAO_PAI_BI_MEN = (0, 1)  # 小牌必闷  闷胡血流才有 0未选 1选  捡漏血流固定是1
    TUI_ZHANG_CAN_HU = (0, 1)  # 退张可开  闷胡血流才有 0未选 1选  捡漏血流固定是0
    BAO_TING_BI_MEN = (0, 1)  # 报听必闷   闷胡血流才有 0未选 1选  捡漏血流固定是0
    EXCHANGE_THREE = (0, 1, 2, 3)  # 是否换三张  0不换 1换三张 2豹子换 3 黄牌换
    EXCHANGE_CARDS_TYPE = (1, 2)  # 换三张方式  1任意牌 2同色牌
    NULL_MEG = "房间不存在"


    @classmethod
    async def cache_room_player_up(cls, room_id, value=1):
        await cls.conf.rds.incr(f"{cls.SESSION_KEY}:{room_id}", value)

    @classmethod
    async def cache_room_player_get(cls, room_id):
        return await cls.conf.rds.get_item(f"{cls.SESSION_KEY}:{room_id}")

    @classmethod
    async def create_game_room(cls, platform: int, creator: int, rule_details: dict,
                               play_type: int, club_id: int = 0, **kwargs):
        total_round = kwargs.get("total_round", 0)
        """创建游戏房间"""
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                room_data = {
                    "club_id": club_id,
                    "room_id": generate_natural_random(6),
                    "creator": creator,
                    "platform": platform,
                    "play_type": play_type,
                    "total_round": total_round,
                    "rule_details": json_encode(rule_details) if rule_details else "{}",
                    "max_player": kwargs.get("max_player", 4),
                    "game_type": kwargs.get("game_type", 1),
                    "pay_type": kwargs.get("pay_type", 1),
                    "price": kwargs.get("price", 1),
                    "m_game_name": kwargs.get("m_game_name", 1),
                    "cs_type": kwargs.get("cs_type", 0)
                }
                new_room = await cls.db_model.add_one(room_data)
                if not new_room:
                    return None, "创建失败"
        except OperationalError as e:
            return None, f"房间创建失败: {str(e)}"
        return room_data["room_id"], "成功"

    @classmethod
    async def settle_game_room(cls, room_id: int, **kwargs):
        """结算房间"""
        try:
            room, e = await cls.get_game_room_by_room_id(room_id)
            if not room:
                return False, e
            if room['status'] != RoomStatus.T_PLAYING:
                return False, "房间状态异常"
            # 房卡结算
            room_card_sta, e = cls.settle_room_card(room)
            if not room_card_sta:
                return False, e
            # TODO 用户资源结算 需对接游戏服务器或根据战绩
            result = kwargs.get("result")
            for uid in result:
                user_resource_sta, e = cls.settle_user_resource(uid, **kwargs)
                if not room_card_sta:
                    return False, e
        except OperationalError as e:
            return False, f"房间结算失败: {str(e)}"
        return True, "成功"

    @classmethod
    async def settle_room_card(cls, room_data):
        """结算房卡"""
        # 扣除房卡
        key = "room_card"
        userinfo = await BaseUserRC.cache_by_pk(room_data["creator"])
        if room_data["club_id"] and room_data["club_id"] > 0:
            # 扣除茶馆基金
            if room_data["pay_type"] == 2:
                up_room_card = await BaseClubRC.update_club_int_field(room_data["club_id"], key, room_data["price"], "sub")
            else:
                room_card = userinfo[key] - room_data['price']
                up_room_card = await BaseUserRC.update_info(userinfo, {key: room_card})
        else:
            # 扣除普通房卡
            if room_data["platform"] == PlatForm.WECHAT_MINI_GAME:
                # 微信小程序
                key = "yellow_diamond"
            room_card = userinfo[key] - room_data['price']
            up_room_card = await BaseUserRC.update_info(userinfo, {key: room_card})
        if not up_room_card:
            return False, "房卡结算失败"
        return True, "成功"

    @classmethod
    async def settle_user_resource(cls, uid: int, **kwargs):
        """用户资源结算"""
        # 金币
        key = "gold"
        val = kwargs.get("gold", 0)
        operation = kwargs.get("operation")
        creator_info = await BaseUserRC.cache_by_pk(uid)
        up_user, e = await BaseUserRC.update_user_int_field(uid, key, val, operation)
        if not up_user:
            return False, "房卡结算失败"
        return True, "成功"


    @classmethod
    async def delete_game_room(cls, room_id: int):
        """删除游戏房间"""
        try:
            sta = await cls.db_model.filter(room_id=room_id).delete()
            if not sta:
                return False, cls.NULL_MEG
        except OperationalError as e:
            return False, f"房间删除失败: {str(e)}"
        return True, "成功"

    @classmethod
    async def update_game_room(cls, room_id: int, **kwargs):
        """更新房间信息"""
        try:
            room, e= await cls.get_game_room_by_room_id(room_id)
            if not room:
                return False, cls.NULL_MEG

            valid_fields = ["status", "player_count", "rule_details"]
            update_data = {k: v for k, v in kwargs.items() if k in valid_fields}

            if update_data:
                await cls.db_model.filter(room_id=room_id).update(**update_data)
        except OperationalError as e:
            return False, f"房间更新失败: {str(e)}"
        return True, "成功"

    @classmethod
    async def get_game_room_by_room_id(cls, room_id: int):
        """根据ID获取房间详情"""
        try:
            room = await cls.db_model.get_or_none(room_id=room_id)
            if not room:
                return None, cls.NULL_MEG
        except OperationalError as e:
            return None, f"查询失败: {str(e)}"
        return room, "成功"

    @classmethod
    async def get_game_rooms_by_filter(cls, club_id: int = None, status: int = None, creator: int = None):
        """多条件查询房间列表"""
        try:
            query = {}
            if club_id is not None:
                query["club_id"] = club_id
            if status is not None:
                query["status"] = status
            if creator is not None:
                query["creator"] = creator

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
            if room_data.status != 0:
                return False, "房间已满"
            room_id = room_data.room_id
            max_player = room_data.max_player
            disk_uid = await cls.conf.rds.smembers(f"{cls.SESSION_DISK_KEY}:{room_id}")
            if uid in disk_uid:
                return False, "用户已加入房间"
            sta = await cls.conf.rds.set_hash(f"{cls.SESSION_DISK_KEY}:{room_id}", uid)
            if sta == 0:
                return False, "用户已加入房间或加入房间失败"
            disk_uid = await cls.conf.rds.smembers(f"{cls.SESSION_DISK_KEY}:{room_id}")
            if len(disk_uid) > max_player:
                await cls.conf.rds.srem(f"{cls.SESSION_DISK_KEY}:{room_id}", uid)
                return False, "房间已满"
            elif len(disk_uid) == max_player:
                # 房间已满 可以直接开始 修改状态
                # await cls.update_game_room(room_id, status=RoomStatus.)
                pass
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
            if room_data['status'] in [RoomStatus.T_PLAYING, RoomStatus.T_RECHARGE_ING, RoomStatus.T_CHECK_OUT]:
                return False, "离开房间状态异常"
            sta = cls.conf.rds.srem(f"{cls.SESSION_DISK_KEY}:{room_id}", uid)
            if sta == 0:
                return False, "用户已离开房间或离开房间失败"
            elif room_data['creator'] == uid:
                # 关闭房间
                await cls.update_game_room(room_id, status=RoomStatus.T_CLOSED)
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
        except OperationalError as e:
            return None, f"获取房间玩家失败: {str(e)}"
        return player, "成功"

    @classmethod
    async def oriupper(cls, val: str):
        return val.upper()
