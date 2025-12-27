from sanic import Request

from lucky_proxy.base_api import ProxyAuthApi
from lucky_proxy.logic.promotion_code import PromotionCode
from lucky_proxy.model_db.main import ProxyOrderDividendRecords

"""
创建推广码
"""


class PromotionCreator(ProxyAuthApi):

    async def post(self, req: Request, **kwargs):
        promotion_code_name = req.json.get("promotion_code_name")
        promotion_code = await PromotionCode.create_promotion_code(proxy_id=kwargs.get("uid"),
                                                                   promotion_code_name=promotion_code_name)
        if not promotion_code:
            self.answer(self.sta_code.FAIL, {}, hint="创建失败请重试!")
        self.answer(self.sta_code.PASS, promotion_code, hint="创建成功!")


"""
推广码查询
"""


class PromotionCodeQuery(ProxyAuthApi):
    async def get(self, req: Request, **kwargs):
        last_id = self.check_int(req.args.get("last_id"), require=False, p_name="last_id")
        promotion_page = await PromotionCode.query_promotion_code(proxy_id=kwargs.get("uid"),
                                                                  last_id=last_id, page_size=20)
        for promotion in promotion_page:
            promotion["total_players"] = 0
            promotion["total_income"] = 0.00
        self.answer(self.sta_code.PASS, promotion_page, hint="查询成功!")


"""
查询某个推广链接下的充值明细
"""


class PromotionCodeDetailQuery(ProxyAuthApi):
    async def get(self, req: Request, **kwargs):
        last_id = self.check_int(req.args.get("last_id"), require=False, p_name="last_id")
        promotion_id = self.check_int(req.args.get("promotion_id"), require=True, p_name="promotion_id")
        sql = f"select t.id,t.proxy_income,t.order_amount from proxy_order_dividend_records  t where t.promotion_id={promotion_id}"
        if last_id:
            sql = sql + f" and t.id <{last_id}"
        sql += " order by t.id  desc "
        detail_page = await ProxyOrderDividendRecords.exec_sql(sql, query=True)
        self.answer(self.sta_code.PASS, detail_page, hint="查询成功!")


