"""
修改玩家资产
"""
from common.public.conf import R_UID_THRESHOLD
from lucky_admin.base_api import AdminAuthApi
from lucky_admin.const import AssetEnum
from lucky_game.handler.up_assets import UpAssets
from lucky_game.model_rc.base_skin import ItemsSkinRC, UserSkinRC
from lucky_game.model_rc.base_user import BaseUserRC
from lucky_game.const import ReasonCostGold, GoodsType


class QueryAssetsEnum(AdminAuthApi):
    """ 查询资产枚举 """

    async def get(self, _, **_b):
        data = AssetEnum.map_list()
        self.answer(data=data)


class ModifyUserAssets(AdminAuthApi):
    """ 修改玩家资产 """

    async def post(self, req, **_):
        uid = self.check_int(req.json.get("uid"), default=0, minval=R_UID_THRESHOLD + 1, p_name="uid")
        u_info = await BaseUserRC.cache_by_uid(uid)
        (not u_info) and self.answer(code=self.sta_code.FAIL, hint=f'操作对象不存在 {uid}')

        goods_id = self.check_int(req.json.get("goods_id"), require=True, p_name="goods_id（物品ID）")
        goods_count = self.check_int(req.json.get("goods_count"), default=1, p_name="goods_count（物品数量）")
        time_limit = self.check_int(req.json.get("time_limit"), default=0, p_name="time_limit（物品时效）")
        goods_type = self.check_int(req.json.get("goods_type"), require=True, default=0, p_name="goods_type（物品类型）")
        g_enum = GoodsType.find_member_by_val(goods_type)
        (not g_enum) and self.answer(code=self.sta_code.ERR_ARG, hint=f'添加失败，请检查物品类型：{goods_type}')
        goods = {
            "goods_id": goods_id,
            "goods_count": goods_count,
            "time_limit": time_limit,
            "goods_type": goods_type,
            "reason": ReasonCostGold.TEST_ADD
        }
        if goods_count < 0:
            if goods_type in (GoodsType.COSMETIC.val, GoodsType.CARD_SKIN.val):
                self.answer(code=self.sta_code.FAIL, hint='加期限的物品类型不允许扣数量')
        elif goods_count == 0:
            self.answer(code=self.sta_code.FAIL, hint='只能对物品进行加减操作')
        else:
            if goods_type == GoodsType.CARD_SKIN.val:
                skin_conf = await ItemsSkinRC.get_skin_items_by_id(goods_id)
                (not skin_conf) and self.answer(self.sta_code.NO_CONFIGURATION, hint='缺少当前法相配置')
                (skin_conf.get("star_level") != 1) and self.answer(code=self.sta_code.FAIL, hint='法相星级不合法')

                _, convert_goods = await UserSkinRC.deal_skin_convert(uid, skin_conf)
                if convert_goods:
                    goods.update(convert_goods)

        await UpAssets.update_assets(uid, [goods], [], is_pack=True, is_notice=False)
        return self.answer(hint=f"修改玩家{g_enum.phrase}成功")
