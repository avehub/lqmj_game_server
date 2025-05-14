from c_services.base.base_leisure_player import BaseLeisurePlayer


class Player(BaseLeisurePlayer):
    def __init__(self, uid, is_robot):
        super().__init__(uid, is_robot)
        self.__bet = 0
        self.__sp_status = 0  # 撒扑状态

    @property
    def bet(self):
        return self.__bet

    @bet.setter
    def bet(self, bet: int):
        self.__bet = bet

    @property
    def sp_status(self):
        return self.__sp_status

    @sp_status.setter
    def sp_status(self, sp: int):
        self.__sp_status = sp

    def clear_round_data(self):
        """ 清理回合数据 """
        self.__bet = 0
        self.__sp_status = 0  # 撒扑状态
