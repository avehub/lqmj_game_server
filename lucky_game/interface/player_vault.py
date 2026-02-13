"""
玩家背包
基础物品 / 道具 / 装扮
"""
import math

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
        data = await UserBagRC.cache_user_bag(uid)
        if data:
            good_ids = [i.get("good_id") for i in data]
            good_data, msg = await GoodRC.get_good_filter(good_id=good_ids)
            good_dict = {i.get("good_id"): i for i in good_data}
            now = tool_dt.cur_time()
            for i in data:
                good_id = i.get("good_id")
                i.update({
                    "good_type": good_dict[good_id]["type"],
                    "sku": good_dict[good_id]["sku"],
                    "kind": good_dict[good_id]["kind"],
                    "name": good_dict[good_id]["name"],
                    "img": good_dict[good_id]["img"],
                    "desc": good_dict[good_id]["desc"],
                    "bag_type": good_dict[good_id]["bag_type"],
                    "content": good_dict[good_id]["content"],
                    "rest_of_day": math.ceil((i["end_time"] - now) / 86400) if i["end_time"] > 0 else 0,
                })
        return self.answer(data=data)


class DropBagItem(GameAuthApi):
    """通过bag_id删除背包过期项目"""

    async def post(self, req: Request, **kwargs):
        bag_id = self.check_int(req.json.get("bag_id"), require=True, minval=1, p_name="bag_id")
        user = kwargs.get("u_info")
        uid = user.get("uid")
        bag_item = await UserBagRC.get_user_bag_by_id(uid, bag_id)
        (not bag_item) and self.answer(self.sta_code.GOODS_NOT_FOUND, hint="没找到物品")
        end_time = bag_item.get("end_time")
        (end_time > tool_dt.cur_time()) and self.answer(self.sta_code.CONDITION_NOT_MET, hint="物品没有过期，不允许删除")
        all_bag = await UserBagRC.drop_user_bag_by_id(uid, bag_id)
        (not all_bag) and self.answer(self.sta_code.FAIL, hint="删除物品失败")
        return self.answer()


class UserInformationGather(GameAuthApi):
    """道具兑换/信息收集"""

    async def post(self, req: Request, **kwargs):
        phone = self.check_phone_number(req.json.get("phone"), require=True)
        good_id = self.check_int(req.json.get("good_id"), require=True, p_name="兑换ID")
        select_good_id = self.check_int(req.json.get("select_good_id"), require=False, p_name="选择的兑换商品ID")
        good_info = await GoodRC.get_good_by_id(good_id)
        if select_good_id:
            good_info = await GoodRC.get_good_by_id(select_good_id)
        if not good_info:
            return self.answer(self.sta_code.GOODS_NOT_FOUND, hint="兑换商品已下架")
        check_sta = True
        if good_info.get("kind") == 2:
            check_sta = False
        real_name = self.check_str(req.json.get("real_name"), require=check_sta, minlen=2, maxlen=10, p_name="真实姓名")
        good_num = self.check_int(req.json.get("good_num"), require=check_sta, p_name="兑换数量")
        platform = self.check_int(req.args.get("platform"), require=check_sta, p_name="平台")
        region = self.check_str(req.json.get("region"), require=check_sta, p_name="所在地区")
        address = self.check_str(req.json.get("address"), require=check_sta, p_name="详细地址")
        user = kwargs.get("u_info")
        uid = user.get("uid")
        good_info = await GoodRC.get_good_by_id(good_id)
        sta, new = await UserGoodExchangeRC.add_exchange(uid, phone, real_name, good_id, good_info.get("type"),
                                                          platform, region, address, num=good_num)

        if not sta:
            return self.answer(self.sta_code.FAIL, hint="添加兑换信息失败")
        return self.answer()


class UserExchangeList(GameAuthApi):
    """获取用户兑换列表"""

    async def get(self, req: Request, **kwargs):
        status = self.check_int(req.args.get("status"), require=False, p_name="状态")
        page = self.check_int(req.args.get("page"), require=False, default=1, p_name="页码")
        page_size = self.check_int(req.args.get("amount"), require=False, default=10, p_name="每页数量")
        user = kwargs.get("u_info")
        uid = user.get("uid")
        sta, data = await UserGoodExchangeRC.get_exchange_filter(uid=uid, status=status, page=page, page_size=page_size)
        if sta and data["list"]:
            good_ids = [i.get("good_id") for i in data["list"]]
            good_data, msg = await GoodRC.get_good_filter(good_id=good_ids)
            good_dict = {i.get("good_id"): i for i in good_data}
            for i in data["list"]:
                good_id = i.get("good_id")
                if good_id not in good_dict:
                    continue
                i.update({
                    "sku": good_dict[good_id]["sku"],
                    "kind": good_dict[good_id]["kind"],
                    "name": good_dict[good_id]["name"],
                    "img": good_dict[good_id]["img"],
                    "desc": good_dict[good_id]["desc"],
                    "bag_type": good_dict[good_id]["bag_type"],
                    "content": good_dict[good_id]["content"],
                })
        return self.answer(data=data)

