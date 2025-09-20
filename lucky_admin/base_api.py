# coding=utf-8
from nsanic.handler_http import BaseHttpApi
from common.public.common_class import CommonApi
from lucky_admin.config import conf_srv, ConfSrv
from lucky_admin.handler.decorator import AdminChecker
from lucky_admin.model_rc.base_admin import BaseAdminRC
from lucky_admin.model_rc.conf_announcements import ConfAnnouncementsRC
from lucky_admin.model_rc.mails_manage import RecordsAdminMailsRC
from lucky_game.model_rc.base_activity import ConfActivityRC
from lucky_game.model_rc.base_bag import UserBagRC
from lucky_game.model_rc.base_cosmetic import ItemsCosmeticRC, UserCosmeticRC
from lucky_game.model_rc.base_goods import ItemsBaseRC
from lucky_game.model_rc.base_prop import ItemsPropRC
from lucky_game.model_rc.base_ranking import ConfSeasonRC, ConfRankingRC, ConfRankingMatchTimeRc, UserRankingRC
from lucky_game.model_rc.base_skin import ItemsSkinRC, UserSkinRC
from lucky_game.model_rc.base_store import ConfStoreRC
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.model_rc.goods_manager import GoodsManagerRC


class BaseApi(BaseHttpApi, CommonApi):
    conf: ConfSrv = conf_srv

    init_model = [
        BaseAdminRC, BaseUserRC, ConfSeasonRC, ConfRankingRC, UserRankingRC, ConfRankingMatchTimeRc, ConfAnnouncementsRC,
        ItemsBaseRC, ItemsCosmeticRC, ItemsPropRC, ItemsSkinRC, GoodsManagerRC, UserBagRC, UserCosmeticRC, UserSkinRC,
        RecordsAdminMailsRC, ConfActivityRC, ConfStoreRC
    ]
    for m in init_model:
        m.conf = conf


class AdminAuthApi(BaseApi):
    decorators = [AdminChecker]
