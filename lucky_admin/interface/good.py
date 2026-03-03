from sanic import Request
from lucky_admin.base_api import AdminAuthApi
from lucky_game.model_rc.base_store import GoodRC


class Good(AdminAuthApi):
    async def post(self, req: Request, **kwargs):
        """ 创建商品 """
        currency = self.check_str(req.json.get("currency"), require=True, p_name="货币类型")
        good_type = self.check_int(req.json.get("type"), require=True, p_name="商品类型")
        sid = self.check_int(req.json.get("sid"), require=True, p_name="商店ID")
        name = self.check_str(req.json.get("name"), require=True, p_name="商品名称")
        img = self.check_str(req.json.get("img"), require=True, p_name="商品图片")
        original = self.check_float(req.json.get("original"), require=True, p_name="商品原价")
        price = self.check_float(req.json.get("price"), require=True, p_name="商品售价")
        content = self.check_str(req.json.get("content"), require=True, p_name="商品内容")
        status = self.check_int(req.json.get("status"), require=False, default=1, p_name="状态")
        desc = self.check_str(req.json.get("desc"), require=False, p_name="商品描述")
        purchase_limit = self.check_str(req.json.get("purchase_limit"), require=False, p_name="限购条件")
        total = self.check_int(req.json.get("total"), require=False, default=-1, p_name="商品库存")
        kind = self.check_int(req.json.get("kind"), require=False, default=0, p_name="商品类型")
        up_time = self.check_int(req.json.get("up_time"), require=False, p_name="上架时间")
        down_time = self.check_int(req.json.get("down_time"), require=False, p_name="下架时间")
        bag_type = self.check_int(req.json.get("bag_type"), require=False, default=0, p_name="背包类型")
        rank = self.check_int(req.json.get("rank"), require=False, default=0, p_name="商品等级")
        sta, new = await GoodRC.create_good(sid, good_type, currency, name, img, original, price, content, status=status, desc=desc,\
                                             purchase_limit=purchase_limit, total=total, kind=kind, up_time=up_time,\
                                            down_time=down_time, bag_type=bag_type, rank=rank)
        if not sta:
            return self.answer(self.sta_code.FAIL, hint=new)
        return self.answer(data={"award_id": new.award_id})

    async def get(self, req: Request, **kwargs):
        """ 商品列表 """
        good_id = self.check_str(req.args.get('good_id'), require=False, p_name='商品ID')
        sku = self.check_str(req.args.get("sku"), require=False, p_name="商品SKU")
        type_id = self.check_int(req.args.get("type"), require=False, p_name="商品类型")
        sid = self.check_int(req.args.get("sid"), require=False, p_name="商店ID")
        page = self.check_int(req.args.get('page'), require=False, default=1, p_name='页码')
        page_size = self.check_int(req.args.get('page_size'), require=False, default=10, p_name='每页数量')
        data, msg = await GoodRC.get_good_filter(good_id=good_id, sku=sku, sid=sid, type_id=type_id,
                                                      page=page, page_size=page_size)
        return self.answer(data=data, hint=msg)

    async def put(self, req: Request, **kwargs):
        """ 编辑商品 """
        good_id = self.check_str(req.json.get("good_id"), require=True, p_name="商品ID")
        currency = self.check_str(req.json.get("currency"), require=False, p_name="货币类型")
        good_type = self.check_int(req.json.get("type"), require=False, p_name="商品类型")
        sid = self.check_int(req.json.get("sid"), require=False, p_name="商店ID")
        name = self.check_str(req.json.get("name"), require=False, p_name="商品名称")
        img = self.check_str(req.json.get("img"), require=False, p_name="商品图片")
        original = self.check_float(req.json.get("original"), require=False, p_name="商品原价")
        price = self.check_float(req.json.get("price"), require=False, p_name="商品售价")
        content = self.check_str(req.json.get("content"), require=False, p_name="商品内容")
        status = self.check_int(req.json.get("status"), require=False, default=1, p_name="状态")
        desc = self.check_str(req.json.get("desc"), require=False, p_name="商品描述")
        purchase_limit = self.check_str(req.json.get("purchase_limit"), require=False, p_name="限购条件")
        total = self.check_int(req.json.get("total"), require=False, default=-1, p_name="商品库存")
        kind = self.check_int(req.json.get("kind"), require=False, default=0, p_name="商品类型")
        up_time = self.check_int(req.json.get("up_time"), require=False, p_name="上架时间")
        down_time = self.check_int(req.json.get("down_time"), require=False, p_name="下架时间")
        bag_type = self.check_int(req.json.get("bag_type"), require=False, default=0, p_name="背包类型")
        rank = self.check_int(req.json.get("rank"), require=False, default=0, p_name="商品等级")
        up_data = {}
        if currency:
            up_data["currency"] = currency
        if good_type is not None:
            up_data["type"] = good_type
        if sid is not None:
            up_data["sid"] = sid
        if name:
            up_data["name"] = name
        if img:
            up_data["img"] = img
        if original is not None:
            up_data["original"] = original
        if price is not None:
            up_data["price"] = price
        if content:
            up_data["content"] = content
        if status is not None:
            up_data["status"] = status
        if desc:
            up_data["desc"] = desc
        if purchase_limit:
            up_data["purchase_limit"] = purchase_limit
        if total is not None:
            up_data["total"] = total
        if kind:
            up_data["kind"] = kind
        if up_time is not None:
            up_data["up_time"] = up_time
        if down_time is not None:
            up_data["down_time"] = down_time
        if bag_type is not None:
            up_data["bag_type"] = bag_type
        if rank is not None:
            up_data["rank"] = rank
        sta, award = await GoodRC.update_good(good_id, **up_data)
        if not sta:
            return self.answer(self.sta_code.FAIL, hint=award)
        return self.answer()
