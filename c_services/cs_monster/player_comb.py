from c_services.base.base_leisure_player import BaseLeisurePlayer


class PlayerComb(BaseLeisurePlayer):
    def __init__(self, uid, is_robot):
        super().__init__(uid, is_robot)

    def round_over_info(self):
        """ 游戏结束下发信息 """
        info = super().round_over_info()
        child_info = {
            "skin_addition_num": self.skin_addition_num,
            "multiple_card_addition_num": self.multiple_card_addition_num,
            "free_loss_num": self.free_loss_num,
            "multiple": self.checkout_multiple,
        }
        ranking_info = {
            "ranking_info": self.check_info_ranking()
        }
        info.update(child_info)
        info.update(ranking_info)
        return info
