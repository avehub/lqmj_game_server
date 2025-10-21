from common.public.enum_const import ServiceEnum


class Player:
    """ 仅真人 """

    def __init__(self, uid):
        self.__uid = uid
        self.__s_key = ''
        self.__enter_time = 0  # 进入匹配时间
        self.__max_wait_time = 0  # 最大等待时间
        self.__free_loss = 0  # 免输（也免门票）
        self.__checkout_multiple = 1  # 结算倍数
        self.__take_prop_id_list = []  # 携带道具id
        self.__skin_equip_info: dict = {}  # 皮肤装备信息
        self.__skin_movie_is_play: dict[int, bool] = {}  # 记录特效是否播放（需要清理）

        # 修为相关
        self.__ranking_score_free_loss = 0  # 段位分免输（道具：保分卡）
        self.__ranking_addition = 0  # 段位加成（道具：加修卡）

        self.__ranking_level = 0  # 段位等级

        self.__ranking_win_score = 0  # 赢了段位分赢多少
        self.__ranking_lose_score = 0  # 输了段位分扣多少
        self.__ranking_defend = 0  # 段位保护类型

        self.__win_streak = 0  # 连胜
        self.__ranking_addition_vip = 0  # vip加成
        self.__ranking_addition_lifetime_card = 0  # 终生卡加成

    @property
    def uid(self):
        return self.__uid

    @property
    def s_key(self):
        return self.__s_key

    @s_key.setter
    def s_key(self, s_key):
        self.__s_key = s_key

    @property
    def enter_time(self):
        return self.__enter_time

    @enter_time.setter
    def enter_time(self, _time):
        self.__enter_time = _time

    @property
    def max_wait_time(self):
        return self.__max_wait_time

    @max_wait_time.setter
    def max_wait_time(self, _time):
        self.__max_wait_time = _time

    @property
    def free_loss(self):
        return self.__free_loss

    @property
    def checkout_multiple(self):
        return self.__checkout_multiple

    @property
    def skin_equip_info(self):
        return self.__skin_equip_info

    def skin_movie_is_play(self, skin_id) -> bool:
        return self.__skin_movie_is_play.get(skin_id) or False

    def set_skin_movie_is_play(self, skin_id, play: bool):
        self.__skin_movie_is_play[skin_id] = play

    @property
    def ranking_score_free_loss(self):
        return self.__ranking_score_free_loss

    @property
    def ranking_addition(self):
        return self.__ranking_addition

    @property
    def ranking_level(self):
        return self.__ranking_level

    @ranking_level.setter
    def ranking_level(self, level):
        self.__ranking_level = level

    @property
    def ranking_win_score(self):
        return self.__ranking_win_score

    @property
    def ranking_lose_score(self):
        return self.__ranking_lose_score

    def set_ranking_game_score(self, data, cs_type):
        """ 设置排位输赢获得的分 """
        if cs_type in (ServiceEnum.C_MONSTER, ServiceEnum.C_MONSTER_MANY):
            self.__ranking_win_score = data.get("win_gain_score") or 0
            self.__ranking_lose_score = data.get("lose_deduct_score") or 0
        elif cs_type == ServiceEnum.C_MONSTER_SEQUEL:
            self.__ranking_win_score = data.get("win_gain_score_seq") or 0
            self.__ranking_lose_score = data.get("lose_deduct_score_seq") or 0

    @property
    def ranking_defend(self):
        return self.__ranking_defend

    @ranking_defend.setter
    def ranking_defend(self, defend):
        self.__ranking_defend = defend

    @property
    def win_streak(self):
        return self.__win_streak

    @win_streak.setter
    def win_streak(self, count: int):
        self.__win_streak = count

    @property
    def ranking_addition_vip(self):
        return self.__ranking_addition_vip

    @ranking_addition_vip.setter
    def ranking_addition_vip(self, addition):
        self.__ranking_addition_vip = addition

    @property
    def ranking_addition_lifetime_card(self):
        return self.__ranking_addition_lifetime_card

    @ranking_addition_lifetime_card.setter
    def ranking_addition_lifetime_card(self, addition):
        self.__ranking_addition_lifetime_card = addition

    def get_update_take_prop_info(self):
        """ 获取更新的道具信息 """
        prop_list = []
        for prop_id in self.__take_prop_id_list:
            prop_list.append({"goods_id": prop_id, "goods_count": -1})
        return prop_list

    def init_prop_info(self, info: dict):
        """
        初始化道具信息：跟匹配有关
        金币：护盾卡、翻倍卡、保分卡
        修为相关：固分卡、加速卡
        """
        self.__free_loss = info.get("free_loss")
        self.__checkout_multiple = info.get("checkout_multiple") or 1
        self.__take_prop_id_list = info.get("prop_id_list") or []
        self.__ranking_score_free_loss = info.get("ranking_score_free_loss") or 0
        self.__ranking_addition = info.get("ranking_addition") or 0

    def init_skin_info(self, info: dict):
        """ 初始化皮肤信息 """
        self.__skin_equip_info = info

    def user_data(self):
        """ 发送到房间的玩家对象data """
        base_data = {"uid": self.uid, "is_robot": 0}
        data = {
            **base_data,
            **self.additional_info()
        }
        return data

    def additional_info(self):
        """ 匹配附属信息 """
        return {
            # 道具信息
            "free_loss": self.__free_loss,
            "checkout_multiple": self.__checkout_multiple,
            "prop_id_list": self.__take_prop_id_list,

            # 皮肤信息
            "skin_equip_info": self.__skin_equip_info,

            # 修为相关
            "ranking_score_free_loss": self.__ranking_score_free_loss,
            "ranking_addition": self.__ranking_addition,
            "ranking_addition_vip": self.__ranking_addition_vip,
            "ranking_addition_lifetime_card": self.__ranking_addition_lifetime_card,

            "ranking_win_score": self.__ranking_win_score,
            "ranking_lose_score": self.__ranking_lose_score,
            "ranking_defend": self.__ranking_defend,

            "win_streak": self.__win_streak,
        }

    def init_additional_info(self, info: dict):
        """ 初始化附属信息 """
        self.__free_loss = info.get("free_loss")
        self.__checkout_multiple = info.get("checkout_multiple") or 1
        self.__take_prop_id_list = info.get("prop_id_list") or []

        self.__skin_equip_info = info.get("skin_equip_info") or {}  # 装备皮肤

        # 修为
        self.__ranking_score_free_loss = info.get("ranking_score_free_loss") or 0
        self.__ranking_addition = info.get("ranking_addition") or 0
        self.__ranking_addition_vip = info.get("ranking_addition_vip") or 0
        self.__ranking_addition_lifetime_card = info.get("ranking_addition_lifetime_card") or 0

        self.__ranking_win_score = info.get("ranking_win_score") or 0
        self.__ranking_lose_score = info.get("ranking_lose_score") or 0
        self.__ranking_defend = info.get("ranking_defend") or 0  # 段位保护类型

        self.__win_streak = info.get("win_streak") or 0

    def clear_player(self):
        """ 清理玩家状态 """
        self.__skin_equip_info.clear()
        self.__skin_movie_is_play.clear()
