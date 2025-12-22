"""
玩家背包
基础物品 / 道具 / 装扮
"""
from sanic import Request
from nsanic.libs import tool_dt
from nsanic.libs.tool import json_parse
from common.model_rc.user_good_exchange import UserGoodExchangeRC
from lucky_game.base_api import GameAuthApi
from lucky_game.model_rc.base_bag import UserBagRC
from lucky_game.model_rc.base_store import GoodRC
from lucky_game.model_rc.base_user import BaseUserRC


class BagList(GameAuthApi):
    """获取背包全部"""

    async def get(self, _: Request, **kwargs):
        user = kwargs.get("u_info")
        uid = user.get("uid")

        data = await UserBagRC.get_user_bag_by_type(uid=uid)
        if data:
            UserBagRC.organize_bag_data(data)
            # 排序逻辑
            data = sorted(data, key=lambda x: (
                x.get('goods_type', 0),
                -(x.get('game_prop_type', 0)),
                x.get('goods_id', 0)
            ))

        return self.answer(data=data)


class DropBagItem(GameAuthApi):
    """通过bag_id删除背包过期项目"""

    async def post(self, req: Request, **kwargs):
        bag_id = self.check_int(req.json.get("bag_id"), require=True, minval=1, p_name="bag_id")
        user = kwargs.get("u_info")
        uid = user.get("uid")

        bag_item = await UserBagRC.get_user_bag_by_id(uid, bag_id)
        (not bag_item) and self.answer(self.sta_code.GOODS_NOT_FOUND, hint="没找到物品")

        exp_time = bag_item.get("exp_time")
        (exp_time > tool_dt.cur_time()) and self.answer(self.sta_code.CONDITION_NOT_MET, hint="物品没有过期，不允许删除")

        all_bag = await UserBagRC.drop_user_bag_by_id(uid, bag_id)
        (not all_bag) and self.answer(self.sta_code.FAIL, hint="删除物品失败")

        new_bag = await BaseUserRC.deal_user_update_goods(uid, key_name=UserBagRC.KEY_NEWLY)
        data = {
            "all_bag": all_bag,
            "new_bag": [] if not new_bag else json_parse(new_bag)
        }
        self.log_info(uid, f"DropBagItem 背包删除物品{bag_id}成功")
        return self.answer(data=data)


class UserInformationGather(GameAuthApi):
    """道具兑换/信息收集"""

    async def post(self, req: Request, **kwargs):
        real_name = self.check_str(req.json.get("real_name"), require=True, p_name="真实姓名")
        phone = self.check_phone_number(req.json.get("phone"), require=True)
        region = self.check_str(req.json.get("region"), require=True, p_name="所在地区")
        address = self.check_int(req.json.get("address"), require=True, p_name="详细地址")
        good_id = self.check_int(req.json.get("good_id"), require=True, p_name="兑换ID")
        good_num = self.check_int(req.json.get("good_num"), require=True, p_name="兑换数量")
        platform = self.check_str(req.args.get("platform"), require=True, p_name="平台")
        user = kwargs.get("u_info")
        uid = user.get("uid")
        good_info = await GoodRC.get_good_by_id(good_id)
        sta, new = await UserGoodExchangeRC.add_exchange(uid, phone, real_name, good_id, good_info.get("goods_type"),
                                                          platform, region, address, num=good_num)

        if not sta:
            return self.answer(self.sta_code.FAIL, hint="添加兑换信息失败")
        return self.answer()


class UserExchangeList(GameAuthApi):
    """获取用户兑换列表"""

    async def get(self, req: Request, **kwargs):
        status = self.check_int(req.args.get("status"), require=True, p_name="兑换状态")
        page = self.check_int(req.args.get("page"), require=False, default=1, p_name="页码")
        page_size = self.check_int(req.args.get("amount"), require=False, default=10, p_name="每页数量")
        user = kwargs.get("u_info")
        uid = user.get("uid")
        sta, data = await UserGoodExchangeRC.get_exchange_filter(uid=uid, status=status, page=page, page_size=page_size)
        return self.answer(data=data)
