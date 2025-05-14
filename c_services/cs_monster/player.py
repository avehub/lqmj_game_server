from c_services.cs_monster.player_comb import PlayerComb


class Player(PlayerComb):
    def __init__(self, uid, is_robot):
        super().__init__(uid, is_robot)
        self.__pick_len = 0
        self.__curr_pick_len = 0

        self.__pass_cards = []  # 要不起的牌（选择捡的牌）

    @property
    def pick_len(self):
        return self.__pick_len

    def add_pick_len(self, pick_len):
        self.__pick_len += pick_len

    @property
    def curr_pick_len(self):
        return self.__curr_pick_len

    @curr_pick_len.setter
    def curr_pick_len(self, pick_len):
        self.__curr_pick_len = pick_len

    @property
    def pass_cards(self):
        return self.__pass_cards

    def add_pass_cards(self, card):
        self.__pass_cards.append(card)

    def player_info(self):
        p_info = super().player_info()
        p_info["pick_len"] = self.pick_len
        p_info["is_give_up"] = self.is_out
        skin_id_list = []
        for _, s_info in self.skin_equip_info.items():  # 玩家装备皮肤信息
            skin_id_list.append(s_info.get("skin_id"))
        p_info["skin_id_list"] = skin_id_list
        return p_info

    def clear_data_round_over(self):
        super().clear_data_round_over()
        self.__pass_cards.clear()

    def clear_player(self):
        """ 清理玩家 """
        self.__pick_len = 0
        self.__curr_pick_len = 0
        self.__pass_cards = []

        super().clear_player()
