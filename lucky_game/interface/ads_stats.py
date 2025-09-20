"""
广告统计
"""
from nsanic.libs import tool_dt
from sanic import Request
from common.proto.py_pb2.common import get_one_of_model
from common.public.enum_const import UserSource, Switch
from lucky_game.base_api import GameAuthApi
from lucky_game.const import AdEventType
from lucky_game.handler.decorator import GameChecker
from lucky_game.model_db.main import RecordsAdsEvent, RecordsAdsUser, RecordsAdsParams
from lucky_game.model_rc.base_ads import BaseAds


class JuLiangAdsMonitor(GameAuthApi):
    """
    巨量广告监测转化数据（来自平台）
    参考文档：https://open.oceanengine.com/labels/7/docs/1696710655781900?origin=left_nav
    """
    decorators = []

    async def get(self, req: Request):
        # todo:暂时不使用监测数据
        self.info_log("JuLiangAdsMonitor 监测转化数据:", req.args)

        promotion_id = req.args.get("promotion_id")
        self.check_str(promotion_id, minlen=1, require=True)
        project_id = req.args.get("project_id")
        self.check_str(project_id, minlen=1, require=True)
        advertiser_id = req.args.get("advertiser_id")
        self.check_str(advertiser_id, minlen=1, require=True)

        q_p = {"promotion_id": promotion_id, "project_id": project_id, "advertiser_id": advertiser_id}
        await RecordsAdsParams.get_or_create(**q_p, defaults=q_p)
        return self.answer(self.sta_code.PASS)

        # request_id = self.check_str(req.json.get("request_id"), require=True, p_name='request_id')
        # aid = req.args.get("aid") or ''
        # oaid = req.args.get("oaid") or ''
        # idfa = req.args.get("idfa") or ''
        # promotion_id = req.args.get("promotion_id") or ''
        # project_id = req.args.get("project_id") or ''
        # advertiser_id = req.args.get("advertiser_id") or ''
        # return self.answer(self.sta_code.PASS)


class DataNexusAdsMonitor(GameAuthApi):
    """
    腾讯广告监测转化数据（来自平台）
    参考文档：https://datanexus.qq.com/doc/develop/guider/interface/conversion/trackingcgi_api_minigame
    """
    decorators = []

    async def get(self, req: Request):
        # todo:暂时不使用监测数据
        self.info_log("DataNexusAdsMonitor 监测转化数据:", req.args)
        return self.answer(self.sta_code.PASS)

        # click_id = req.args.get("click_id") or ''  # 点击id
        # click_time = req.args.get("click_time") or ''
        # adgroup_id = req.args.get("adgroup_id") or ''  # 广告组id（实际为广告id）
        # account_id = req.args.get("account_id") or ''  # 广告主id
        # request_id = req.args.get("request_id") or ''  # 请求id
        #
        # ad_platform_type = req.args.get("ad_platform_type") or ''  # 广告投放平台
        # promoted_object_id = req.args.get("promoted_object_id") or ''  # 应用id
        # promoted_object_type = req.args.get("promoted_object_type") or ''  # 推广类型
        #
        # callback = req.args.get("callback") or ''  # 直接提供上报信息回传接口的url
        # return self.answer(self.sta_code.PASS)


class CommonAdsMatchedData(GameAuthApi):
    """
    通用广告匹配转化数据（来自客户端）
    """
    decorators = []

    async def post(self, req: Request, **_):
        user_source = self.check_int(req.json.get("user_source"), require=True, p_name='user_source 用户来源')
        us_enum = UserSource.find_member_by_val(user_source)
        (not isinstance(us_enum, UserSource)) and self.answer(self.sta_code.ERR_ARG, hint="暂未接入的用户来源")

        event_type = req.json.get("event_type") or ''
        et_enum = AdEventType.find_member_by_phrase(event_type)
        (not isinstance(et_enum, AdEventType)) and self.answer(code=self.sta_code.ERR_ARG, hint="广告事件类型不支持")

        promotion_id = self.check_str(req.json.get("promotionid"), require=True, p_name='promotionid')

        self.info_log(f"CommonAdsMatchedData 通用广告点击匹配转化 {us_enum.phrase}数据:", req.json)
        u_info = await self.__verify_user(et_enum, req)

        # match user_source:
        #     case UserSource.JuLiang:
        #         res, hint = await self.ad_of_juliang(uid, us_enum, et_enum, req)
        #     case UserSource.DataNexus:
        #         res, hint = await self.ad_of_datanexus(uid, us_enum, et_enum, req)
        #     case _:
        #         res, hint = False, "平台暂未加入统计"

        if user_source == UserSource.JuLiang:
            res1, hint1 = await self.ad_by_user(u_info, us_enum, et_enum, promotion_id, req)
            if not res1:
                self.error_log(f"广告用户记录更新失败: {hint1}")

        res, hint = await self.ad_by_event(u_info, us_enum, et_enum, promotion_id, req)
        if res:
            is_first_pay = res.get('is_first_pay') or Switch.CLOSE.val
            one_of_model = get_one_of_model()
            one_of_model.switch = is_first_pay
            return self.answer(self.sta_code.PASS, data=one_of_model)
        return self.answer(self.sta_code.FAIL, hint=f"{hint}")

    async def __verify_user(self, et_enum: AdEventType, req: Request):
        if et_enum != AdEventType.AD_ACTIVE:
            # 非AD_ACTIVE事件保持原有验证逻辑
            u_info, data = await GameChecker.verify_token(req)
            if not u_info:
                self.answer(self.sta_code.ERR_AUTH, hint=data)
            return u_info

        # AD_ACTIVE事件处理逻辑
        try:
            # 尝试获取用户信息，但不报错
            u_info, _ = await GameChecker.verify_token(req)
            return u_info or {}  # 老用户返回用户信息，新用户返回空字典
        except Exception as e:
            self.info_log(f"AD_ACTIVE事件获取用户信息异常(可能为新用户): {str(e)}")
            return {}  # 出现异常也返回空字典

    async def ad_by_event(self, u_info, us_enum, et_enum, promotion_id, req: Request):
        """通用广告处理"""
        self.info_log(f"CommonAdsMatchedData {et_enum.phrase} 事件处理")
        click_id = self.check_str(req.json.get("clickid"), require=True, p_name='clickid')
        (click_id == '__CLICKID__') and self.answer(self.sta_code.ERR_ARG, hint="非点击事件不保存和统计")

        request_id = req.json.get("requestid") or ''
        os = req.json.get("platform") or ''  # 0:android/1:ios/3:other
        product_price = req.json.get("product_price") or 0
        uid = u_info.get("uid") or 0

        data = {
            'user_source': UserSource.JuLiang.val,
            'click_id': click_id,
            'promotion_id': promotion_id,
            'request_id': request_id,
            'os': os,
            'uid': uid,
            'event_type': et_enum,
        }
        try:
            await RecordsAdsEvent.add_one(data)
            res = await BaseAds.stats_ads_event(u_info, promotion_id, et_enum, user_source=us_enum, product_price=product_price)
            return res, 'OK'
        except Exception as e:
            self.error_log(f"通用广告处理失败，原因：{e}")
            return {}, e

    async def ad_by_user(self, u_info, us_enum, et_enum, promotion_id, _):
        """广告用户记录"""
        self.info_log(f"CommonAdsMatchedData {et_enum.phrase} 用户处理")
        # promotion_id = '' if promotion_id == 'undefined' or not promotion_id else promotion_id

        openid = u_info.get("openid") or ''
        current_time = tool_dt.cur_time()

        record, created = await RecordsAdsUser.get_or_create(
            openid=openid, promotion_id=promotion_id,
            defaults={
                'user_source': us_enum.val,
                'first_active_time': current_time,
                'user_type': 0,  # 默认新用户
                'is_active': 1   # 默认激活
            }
        )
        update_fields = {}
        # 处理首次激活和用户类型
        if created:
            if et_enum != AdEventType.AD_ACTIVE:
                update_fields['is_active'] = 0
            if u_info and u_info.get('uid'):
                update_fields['user_type'] = 1

        if et_enum == AdEventType.AD_ACTIVE_REGISTER:
            update_fields['user_type'] = 0

        # 广告打开事件处理
        if et_enum == AdEventType.AD_CLICK_AD:
            update_fields['ad_open_count'] = record.ad_open_count + 1
            if not record.first_open_time:
                update_fields['first_open_time'] = current_time

        # 有消耗的打开处理
        elif et_enum == AdEventType.AD_ACTIVE_AD:
            update_fields['cost_open_count'] = record.cost_open_count + 1

        # 执行更新（如果有需要更新的字段）
        if update_fields:
            await RecordsAdsUser.update_by_pk(record.id, update_fields)

        return {'status': 'success'}, 'OK'

