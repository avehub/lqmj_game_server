from ..cs_monster.player_comb import PlayerComb


class Player(PlayerComb):
    def __init__(self, uid, is_robot):
        super().__init__(uid, is_robot)
        # self.__area_tribulation = []  # 磨难区
        self.__tribulation_val = 0  # 磨难值
        self.__mint_cards = []  # 从出牌区域补的牌算明牌

    @property
    def tribulation_val(self):
        return self.__tribulation_val

    def add_tribulation_val(self, val):
        self.__tribulation_val += val

    # def add_tribulation(self, cards):
    #     """ 添加牌到磨难区 """
    #     self.__area_tribulation.extend(cards)

    # def pop_tribulation(self):
    #     """ 从磨难区移除一张牌 """
    #     if self.__area_tribulation:
    #         return self.__area_tribulation.pop()
    #     return 0

    @property
    def mint_cards(self):
        return self.__mint_cards

    def add_mint_card(self, c):
        self.__mint_cards.append(c)

    def rm_cards(self, cards: list):
        super().rm_cards(cards)
        for c in cards:
            if c in self.__mint_cards:
                self.__mint_cards.remove(c)

    def player_info(self):
        p_info = super().player_info()
        # p_info["area_tribulation"] = self.area_tribulation
        p_info["is_give_up"] = self.is_out
        p_info["tribulation_val"] = self.__tribulation_val

        skin_id_list = []
        for _, s_info in self.skin_equip_info.items():  # 玩家装备皮肤信息
            skin_id_list.append(s_info.get("skin_id"))
        p_info["skin_id_list"] = skin_id_list
        return p_info

    def clear_player(self):
        """ 清理玩家 """
        self.__tribulation_val = 0  # 磨难值
        super().clear_player()
