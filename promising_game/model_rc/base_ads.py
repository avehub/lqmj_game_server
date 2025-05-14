"""
广告统计
"""
import asyncio
from datetime import datetime, timedelta
from nsanic.libs import tool_dt
from tortoise.functions import Count, Avg
from tortoise.transactions import in_transaction
from common.public.conf import DouYinConf
from common.utils.kit_dt import KitDt
from nsanic.libs.tool import http_post, json_encode, json_parse, http_get
from common.public.enum_const import UserSource, Switch, DbKey
from promising_game.config import ConfSrv, conf_srv
from promising_game.model_db.main import StatsAdsEvent, RecordsTradeOrder, RecordsAdsUser
from promising_game.model_rc.base_rc import BaseRC
from promising_game.const import AdEventType, AD_EVENT_FIELD_MAP, OrderStatus


class BaseAds(BaseRC):
    conf: ConfSrv = conf_srv

    @classmethod
    async def stats_ads_event(
            cls,
            u_info,
            promotion_id: str,
            event_type: AdEventType,
            user_source=UserSource.Own,
            product_price=0):
        """
        统计广告事件
        """
        if not promotion_id:
            return

        time_node = KitDt.timestamp_today()
        add_field = AD_EVENT_FIELD_MAP[event_type] or ''
        if not add_field:
            return {'status': '暂无须统计字段'}

        # 如果是付费事件，先检查是否首次付费
        is_first_pay = False
        if event_type == AdEventType.AD_ACTIVE_PAY:
            uid = u_info.get("uid")
            has_paid = await RecordsTradeOrder.filter(uid=uid, order_status=OrderStatus.PAID.val).exists()
            if not has_paid:
                is_first_pay = True

        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                # 尝试处理潜在的唯一键冲突
                # record = await StatsAdsEvent.get_or_none(promotion_id=promotion_id, time_node=time_node, user_source=user_source)

                # select_for_update是一种用于在事务中锁定选定行的机制，以防止其他并发事务修改这些行，直到当前事务完成（提交或回滚）
                record = await StatsAdsEvent.filter(
                    promotion_id=promotion_id, time_node=time_node, user_source=user_source).select_for_update().first()
                # -- snip --
                openid = u_info.get("openid")
                if openid and add_field == 'pay_times':
                    record_ads_user, created = await RecordsAdsUser.get_or_create(
                        openid=openid, promotion_id=promotion_id,
                        defaults={"pay_amount": product_price}
                    )
                    if not created:
                        record_ads_user.pay_amount += product_price
                        await record_ads_user.save()
                # -- snip --

                if not record:
                    new_data = {
                        'promotion_id': promotion_id,
                        'time_node': time_node,
                        'user_source': user_source,
                        add_field: 1
                    }
                    if add_field == 'pay_times':
                        new_data['pay_amount'] = product_price

                    if is_first_pay:  # 如首次付费，增加首次付费次数
                        new_data['first_pay_times'] = 1

                    await StatsAdsEvent.add_one(new_data)
                else:
                    up_data = {add_field: getattr(record, add_field, 0) + 1}
                    if add_field == 'pay_times':
                        up_data['pay_amount'] = record.pay_amount + product_price

                    if is_first_pay:  # 如首次付费，增加首次付费次数
                        up_data['first_pay_times'] = getattr(record, 'first_pay_times', 0) + 1

                    await record.update_from_dict(up_data)
                    await record.save()
        except Exception as e:
            cls.conf.error_log(f"stats_ads_event 事务执行失败，原因：{e}")

        return {'is_first_pay': Switch.OPEN.val if is_first_pay else Switch.CLOSE.val}

    @classmethod
    async def get_ads_event(
            cls,
            promotion_id_list: list = None,
            user_source=UserSource.Own,
            start_time=0,
            end_time=0,
            limit=0,
            offset=0):
        """获取广告事件统计"""
        query_params = {'user_source': user_source}
        # if promotion_id and promotion_id != '__PROMOTION_ID__':
        # query_params['promotion_id__in'] = promotion_id
        if promotion_id_list:
            query_params['promotion_id__in'] = promotion_id_list

        if start_time != 0 and end_time != 0:
            query_params['time_node__gte'] = start_time
            query_params['time_node__lte'] = end_time
        elif start_time != 0:
            query_params['time_node__gte'] = start_time
        elif end_time != 0:
            query_params['time_node__lte'] = end_time

        stats_info = await StatsAdsEvent.get_by_dict(query_params, orders=['-time_node'], limit=limit, offset=offset)
        count = await StatsAdsEvent.filter(**query_params).count()
        return stats_info, count

    @classmethod
    async def stats_and_update_ad_revenue(cls, records):
        """处理并聚合用户的广告收益数据（抖音小游戏信息流投放用户粒度ecpm统计）"""
        if not records:
            return

        # 1.预处理数据：按openid聚合统计
        user_updates = {}
        for r in records:
            openid = r.get("open_id")
            cost = round(float(r.get("cost", 0)) / 100000, 4)  # 十万分之一元 → 元，保留4位小数

            # 初始化用户数据
            if openid not in user_updates:
                user_updates[openid] = {"total_cost": 0.0, "max_cost": 0.0}

            # 累加统计
            user_updates[openid]["total_cost"] += cost
            user_updates[openid]["max_cost"] = max(user_updates[openid]["max_cost"], cost)

        # 2.批量更新数据库
        async with in_transaction(connection_name=DbKey.DEFAULT):
            update_tasks = []
            for openid, stats in user_updates.items():
                # 获取该openid对应的所有用户记录
                users = await RecordsAdsUser.filter(openid=openid).all()
                if not users:
                    continue

                # 对每条记录都应用相同的更新
                for u in users:
                    updates = {}
                    # 更新最大消耗（只更新更大的值）
                    if stats["max_cost"] > u.max_cost:
                        updates["max_cost"] = stats["max_cost"]

                    # 累加总消耗（保留4位小数）
                    new_total = round(u.total_cost + stats["total_cost"], 4)
                    updates["total_cost"] = new_total

                    # 计算平均ECPM（cost_open_count为0时不更新），公式：平均ECPM = (广告总收益×1000) / 有消耗广告次数
                    if u.cost_open_count > 0:
                        updates["avg_ecpm"] = round((new_total * 1000) / u.cost_open_count, 4)

                    if updates:
                        update_tasks.append(RecordsAdsUser.filter(id=u.id).update(**updates))

            # 并行执行所有更新
            if update_tasks:
                await asyncio.gather(*update_tasks)

        cls.conf.info_log("处理单条收益记录（抖音广告用户统计）结束", records)

    @classmethod
    async def get_ads_user_records(
            cls,
            start_time: int,
            end_time: int,
            user_source: int = None,
            promotion_id_list: list = None,
            limit: int = 10,
            offset: int = 0):
        """
        获取广告用户记录（分页）
        """
        qp = {
            "first_active_time__gte": start_time,
            "first_active_time__lte": end_time,
            "user_source": user_source
        }
        if promotion_id_list:
            qp["promotion_id__in"] = promotion_id_list
        query = RecordsAdsUser.filter(**qp)

        records = await query.offset(offset).limit(limit).all()
        total_count = await query.count()

        return records, total_count, 'OK'

    @classmethod
    async def get_ads_user_stats(
            cls, start_time: int, end_time: int, user_source: int = None, promotion_id_list: list = None):
        """
        获取广告用户统计（聚合数据）
        """
        qp = {
            "first_active_time__gte": start_time,
            "first_active_time__lte": end_time,
            "user_source": user_source
        }
        if promotion_id_list:
            qp["promotion_id__in"] = promotion_id_list

        query = RecordsAdsUser.filter(**qp)

        # 使用annotate进行聚合查询
        stats = await query.annotate(
            avg_cost=Avg('total_cost'),
            avg_ecpm_total=Avg('avg_ecpm'),
            avg_ad_open_count=Avg('ad_open_count'),
            avg_cost_open_count=Avg('cost_open_count'),
        ).first()

        if not stats:
            return {
                       "avg_cost": 0,  # 平均广告消耗（元）
                       "avg_ecpm_total": 0,  # 平均ECPM（总的）
                       "avg_ad_open_count": 0,  # 平均广告打开次数
                       "avg_cost_open_count": 0,  # 平均有消耗广告打开次数
                   }, "OK"

        # 格式化保留两位小数
        result = {
            "avg_cost": round(float(stats.avg_cost or 0), 2),
            "avg_ecpm_total": round(float(stats.avg_ecpm_total or 0), 2),
            "avg_ad_open_count": round(float(stats.avg_ad_open_count or 0), 2),
            "avg_cost_open_count": round(float(stats.avg_cost_open_count or 0), 2),
        }

        return result, 'OK'


class JuLiangAdsRC(BaseRC):
    """巨量广告相关"""
    conf: ConfSrv = conf_srv

    @staticmethod
    async def juliang_date_upload(callback, event_type, pay_amount=0):
        """
        巨量API回传
        参考文档：https://event-manager.oceanengine.com/docs/8650/api_docs
        """
        url = "https://analytics.oceanengine.com/api/v2/conversion"
        params = {
            "event_type": event_type,
            "context": {
                "ad": {
                    "callback": callback
                },
            },
            "properties": {
                "pay_amount": pay_amount
            },
            "timestamp": tool_dt.cur_time() * 1000
        }
        req_data = await http_post(url, param=json_encode(params))
        return req_data

    @classmethod
    async def juliang_get_ecpm(cls, access_token: str, query_time=None, open_id=None):
        """
        获取信息流投放用户粒度ecpm
        参考文档：https://bytedance.larkoffice.com/docx/Vg4yd0RDSovZINxJDyIc6THhnod
        """
        url = "https://minigame.zijieapi.com/mgplatform/api/apps/data/get_ecpm"
        query_time = query_time or datetime.now() - timedelta(hours=1)
        page_no = 1  # 查询的页码，页码从1开始（当不指定 OpenID 或者查询时间范围为天时，必须带上两个分页参数）
        page_size = 500  # 单页的大小，最大支持500

        # 构建基础参数
        params = {
            "open_id": '' if open_id is None else open_id,
            "mp_id": DouYinConf.DOUYIN_APP_ID,
            "date_hour": query_time.strftime("%Y-%m-%d %H"),
            # 2023-11-01 18 则查询 [2023-11-01 18:00:00, 2023-11-01 19:00:00) 区间的所有数据
            "access_token": access_token,
            "page_size": page_size
        }

        all_data = []
        while True:
            # 切换页码
            params["page_no"] = page_no
            req_data = await http_get(url, param=params)
            res = json_parse(req_data)

            err_no = res.get("err_no") or 0
            if err_no != 0:
                err_msg = res.get("err_msg") or ''
                cls.conf.error_log(f'juliang_get_ecpm 第{page_no}页请求失败: {err_msg}')
                return err_no, err_msg  # 任何一页出错都直接返回错误

            page_data = res.get("data") or {}
            page_records = page_data.get("records") or []
            all_data.extend(page_records)

            # 如果获取的数据量小于page_size，说明已经是最后一页
            if len(page_records) < page_size:
                break

            page_no += 1  # 继续获取下一页
            await asyncio.sleep(0.2)  # 200毫秒，巨量要求添加延迟防止QPS过高

        return err_no, all_data
