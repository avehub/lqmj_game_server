"""
大富翁 / 漫漫西行路
"""
import random
from sanic import Request
from collections import defaultdict
from nsanic.libs.tool import json_encode
from tortoise.transactions import in_transaction
from c_services.const.cs_enum_const import CmdWorkers
from common.public.enum_const import DbKey, TaskId
from lucky_game.base_api import GameAuthApi
from lucky_game.handler.monopoly import Monopoly
from lucky_game.handler.up_assets import UpAssets, StatFlow
from lucky_game.model_rc.base_award import ConfAwardRC
from lucky_game.model_rc.base_bag import UserBagRC
from lucky_game.model_rc.base_goods import ItemsBaseRC
from lucky_game.model_rc.goods_manager import GoodsManagerRC
from lucky_game.model_rc.base_monopoly import MonopolyMapRC, UserMonopolyRC, MonopolyEventRC
from lucky_game.model_rc.base_skin import UserSkinRC
from lucky_game.const import AwardType, MagicType, GoodsItem, CellType, GoodsType, ReasonCostGold


class WestWayQueryMap(GameAuthApi):
    """西行路地图"""

    async def get(self, _, **kwargs):
        user = kwargs.get("u_info")
        uid = user.get("uid")

        # 1.获取西行路总地图
        map_conf = await MonopolyMapRC.get_monopoly_map(is_pack=True)
        (not map_conf) and self.answer(self.sta_code.NO_CONFIGURATION, hint="未找到西行路地图配置")

        # 2.获取玩家大富翁记录
        user_map = await UserMonopolyRC.cache_by_pk(uid)
        (not user_map) and self.answer(self.sta_code.NO_PLAYER_INFO, hint="玩家信息加载失败，请稍后再试")
        rand_award_map = user_map.get("map")

        # 3.判断是否首次进入
        if not rand_award_map or user_map.get("default_cache"):
            monopoly = await self.map_first_loading(uid, map_conf, user_map)
        else:
            monopoly = await self.map_normal_loading(uid, map_conf, user_map)

        # 4.打包总格子配置
        all_cell = monopoly.get_all_cell
        data = {
            "map_conf": all_cell,
            "position": monopoly.position
        }
        return self.answer(data=data)

    async def map_first_loading(self, uid, map_conf: list, user_map: dict):
        awards_conf = await ConfAwardRC.get_award_items(award_type=AwardType.MONOPOLY_RAND_AWARD, is_pack=True)
        (not awards_conf) and self.answer(self.sta_code.NO_CONFIGURATION, hint="奖励加载失败，请稍后再试")

        monopoly = Monopoly(map_conf=map_conf, awards_conf=awards_conf)
        award_map = monopoly.get_awards_map

        # 暂存用户随机奖映射字典 / 免费赠一颗骰子
        gift_dice = [{"goods_id": GoodsItem.DICE.val, "goods_count": 1, "goods_type": GoodsType.MAGIC}]
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                await UserMonopolyRC.update_user_monopoly(uid, update_info={"map": json_encode(award_map)}, old_info=user_map)
                await UserBagRC.update_user_bag(uid, gift_dice)
        except Exception as e:
            self.error_log(f"map_first_loading 事务执行失败，原因：{e}")
            self.answer(self.sta_code.FAIL, hint="首次加载地图失败，请稍后再试")

        self.info_log(uid, "WestWayQueryMap 西行路首次进入")
        return monopoly

    async def map_normal_loading(self, uid, map_conf: list, user_map: dict):
        position = user_map.get("position")
        rand_award_map = user_map.get("map")
        monopoly = Monopoly(position=position, map_conf=map_conf, awards_map=rand_award_map)

        self.info_log(uid, "WestWayQueryMap 西行路正常进入")
        return monopoly


class WestWayQueryGoods(GameAuthApi):
    """
    西行路物资：五蕴丹 / 骰子 / 法宝等
    """

    async def get(self, _, **kwargs):
        user = kwargs.get("u_info")
        uid = user.get("uid")

        data = {}
        # 1.用户数据 五蕴丹 / 骰子
        user_bag = await UserBagRC.get_user_bag_by_type(uid, goods_types=[GoodsType.MAGIC.val, GoodsType.G_ASSET.val])
        magic_data = []
        if user_bag:
            for m in user_bag or []:
                goods_id = m.get("goods_id")
                goods_type = m.get("goods_type")
                if goods_type == GoodsType.MAGIC:
                    magic_data.append(m)

                if goods_id == GoodsItem.DICE.val:
                    data['dice_count'] = m.get("goods_count")
                elif goods_id == GoodsItem.FIVE_AGGREGATES.val:
                    data['five_count'] = m.get("goods_count")

        # 2.西行路法宝配置
        magic_ids = [mt.val for mt in MagicType if mt.val]
        magic_conf = await ItemsBaseRC.get_goods_item_by_id_list(magic_ids)
        (not magic_conf) and self.answer(self.sta_code.NO_CONFIGURATION, hint="没有法宝配置，请稍后再试")

        # 3.用户数据 法宝
        user_magic = UserBagRC.check_bag_data(magic_data, magic_conf)
        (not user_magic) and self.answer(self.sta_code.ERR_CONF, hint="没有法宝数据，请稍后再试")
        data['magic_conf'] = user_magic

        self.info_log(uid, "WestWayMapMagic 西行路物资加载成功")
        return self.answer(data=data)


class WestWayPlaySteps(GameAuthApi):
    """西行路行进"""

    async def post(self, req: Request, **kwargs):
        magic_type = self.check_int(req.json.get("magic_type") or 0, require=True, p_name="magic_type")
        mt_enum = MagicType.find_member_by_val(magic_type)
        (not isinstance(mt_enum, MagicType)) and self.answer(self.sta_code.ERR_ARG, hint="不支持的操作类型")

        user = kwargs.get("u_info")
        uid = user.get("uid")

        # 1.获取西行路总地图
        map_conf = await MonopolyMapRC.get_monopoly_map(is_pack=True)
        (not map_conf) and self.answer(self.sta_code.NO_CONFIGURATION, hint="未找到西行路地图配置")

        # 2.获取随机奖池配置
        awards_conf = await ConfAwardRC.get_award_items(award_type=AwardType.MONOPOLY_RAND_AWARD, is_pack=True)
        (not awards_conf) and self.answer(self.sta_code.NO_CONFIGURATION, hint="奖励加载失败，请稍后再试")

        # 2.获取玩家大富翁记录
        user_map = await UserMonopolyRC.cache_by_pk(uid)
        (not user_map) and self.answer(self.sta_code.NO_PLAYER_INFO, hint="玩家信息加载失败，请稍后再试")

        # 3.初始化地图
        position = user_map.get("position")
        rand_award_map = user_map.get("map")
        monopoly = Monopoly(position=position, map_conf=map_conf, awards_map=rand_award_map, awards_conf=awards_conf)

        # 4.处理不同的行进方式
        steps_res, cost_items = await self.process_step_modes(uid, req, mt_enum, monopoly)

        # 5.统计所有奖励和开销用于发货
        all_awards = monopoly.stat_step_awards(steps_res)
        StatFlow.stat_common_flow(awards=all_awards, g_reason=ReasonCostGold.MONOPOLY_AWARDS)

        # 6.修改最新位置，轮回则修改玩家奖池
        update_info = {"position": monopoly.position}
        for s in steps_res:
            if s.get("cross_times", 0) > 0:
                new_awards_map = monopoly.get_awards_map
                update_info['map'] = json_encode(new_awards_map)
                break
        try:
            async with in_transaction(connection_name=DbKey.DEFAULT):
                await UpAssets.update_assets(uid, all_awards, [])
                await UserBagRC.update_user_bag(uid, cost_items)  # 更新剩余法宝
                await UserMonopolyRC.update_user_monopoly(uid, update_info=update_info, old_info=user_map)
                if magic_type == MagicType.DEFAULT:
                    task_data = {"task_id": TaskId.MONOPOLY_ROLL_DICE_1, "add_val": 1}
                    await self.push_task2worker(CmdWorkers.UPDATE_GAME_TASK, task_data, uid)
        except Exception as e:
            self.error_log(f"WestWayPlaySteps 事务执行失败，原因：{e}")
            self.answer(self.sta_code.FAIL, hint="行进错误，请稍后再试")

        # 累积 总步数net_steps 和 总圈数cross_times
        total_net_steps = sum(res.get('net_steps', 0) for res in steps_res)
        total_cross_times = sum(res.get('cross_times', 0) for res in steps_res)

        final_data = {
            "steps_res": steps_res,
            "map_conf": monopoly.get_all_cell,
            "position": monopoly.position,
            "net_steps": total_net_steps,
            "cross_times": total_cross_times
        }
        self.info_log(uid, f"WestWayPlaySteps 西行路行进{total_net_steps}成功，使用{mt_enum.phrase}")
        return self.answer(data=final_data)

    async def process_step_modes(self, uid, req: Request, magic_type: MagicType, monopoly: Monopoly):
        """处理手动摇骰子方式"""
        fixed_steps = self.check_int(req.json.get("fixed_steps", 0), require=True, minval=0, maxval=6, p_name='fixed_steps')
        is_rookie_task = self.check_int(req.json.get("is_rookie_task", 0), require=True, default=0, p_name='is_rookie_task')

        match magic_type:
            case MagicType.WIND_STILLING_PEARL:
                await self.check_required_count(uid, MagicType.WIND_STILLING_PEARL.val)
                res_data = await self.settle_after_step(uid, monopoly, fixed_steps=0)
                cost_items = [{"goods_id": MagicType.WIND_STILLING_PEARL.val, "goods_count": -1, "goods_type": GoodsType.MAGIC.val}]
                return [res_data], cost_items

            case MagicType.THOUSAND_FORMS_DICE:
                await self.check_required_count(uid, MagicType.THOUSAND_FORMS_DICE.val)
                res_data = await self.settle_after_step(uid, monopoly, fixed_steps=fixed_steps)
                cost_items = [{"goods_id": MagicType.THOUSAND_FORMS_DICE.val, "goods_count": -1, "goods_type": GoodsType.MAGIC.val}]
                return [res_data], cost_items

            case MagicType.SOMERSAULT_CLOUD:
                await self.check_required_count(uid, MagicType.SOMERSAULT_CLOUD.val)
                res_data = await self.settle_after_step(uid, monopoly, do_times=2)
                cost_items = [{"goods_id": MagicType.SOMERSAULT_CLOUD.val, "goods_count": -1, "goods_type": GoodsType.MAGIC.val}]
                return [res_data], cost_items

            case _:
                do_times = self.check_int(req.json.get("do_times") or 1, minval=1, maxval=10, p_name='do_times')
                (do_times not in (1, 10)) and self.answer(self.sta_code.ERR_ARG, hint="投掷次数错误")

                if not is_rookie_task:
                    await self.check_required_count(uid, GoodsItem.DICE.val, required_count=do_times)
                    fixed_steps = None
                # todo:测试参数
                test_steps = req.json.get("test_steps") or []
                if test_steps and isinstance(test_steps, list):
                    (len(test_steps) > 10) and self.answer(code=self.sta_code.ERR_ARG, hint="每次最多不能超过10步")

                if len(test_steps) > 0:
                    steps_res = [await self.settle_after_step(uid, monopoly, fixed_steps=sp) for sp in test_steps]
                    cost_items = [{"goods_id": GoodsItem.DICE.val, "goods_count": -len(test_steps), "goods_type": GoodsType.MAGIC.val}]
                else:
                    steps_res = [await self.settle_after_step(uid, monopoly, fixed_steps=fixed_steps, is_rookie_task=is_rookie_task) for _ in range(do_times)]
                    cost_items = [{"goods_id": GoodsItem.DICE.val, "goods_count": -do_times, "goods_type": GoodsType.MAGIC.val}]

                return steps_res, cost_items

    async def settle_after_step(self, uid, monopoly: Monopoly, do_times=1, fixed_steps=None, is_rookie_task=False):
        """处理踩格子结果，手动摇骰子结果后调用"""
        cell_res, dice_res, net_steps, cross_start, cross_times = monopoly.play_steps(do_times=do_times, fixed_steps=fixed_steps)
        event_res = event_ex_res = {}

        cell_type = cell_res.get("cell_type")
        if cell_type in (CellType.SPECIAL_EVENT_CELL, CellType.COMMON_EVENT_CELL):
            if cell_type == CellType.SPECIAL_EVENT_CELL:
                event_conf = await MonopolyEventRC.cache_conf_by_pk(cell_res.get("event_id", 0))
            else:
                event_conf = await MonopolyEventRC.randomly_gen_event()
            (not event_conf) and self.answer(self.sta_code.NO_CONFIGURATION, hint="事件加载失败，请稍后再试")

            event_res, event_ex_res = monopoly.process_event_result(event_conf, is_rookie_task)
            event_awards = event_res.get("event_awards")
            if event_awards:
                await self.process_special_awards(uid, event_awards)

            # 更新步数和圈数
            if event_ex_res:
                net_steps += event_ex_res.get("net_steps", 0)
                cross_times += event_ex_res.get("cross_times", 0)

        elif cell_type in (CellType.SOLID_AWARD_CELL, CellType.RAND_AWARD_CELL):
            (not cell_res.get("conf_items")) and self.answer(self.sta_code.GOODS_NOT_FOUND, hint="奖励缺货，请联系客服")

        data = {
            "cell_res": cell_res,
            "dice_res": dice_res,
            "net_steps": net_steps,
            "cross_start": cross_start,
            "cross_times": cross_times,
            "event_res": event_res,
            "event_ex_res": event_ex_res
        }
        return data

    async def check_required_count(self, uid, goods_id, required_count=1):
        """检查法宝/骰子等是否充足"""
        user_bag = await UserBagRC.get_user_bag_by_id(uid, goods_id=goods_id)
        if not user_bag or user_bag.get("goods_count") < required_count:
            self.answer(self.sta_code.CONDITION_NOT_MET, hint="骰子数量不足")
        return user_bag

    async def process_special_awards(self, uid, awards, is_rank=True):
        """处理特殊奖励，包括法相满级检查和随机法宝抽取"""
        for item in awards:
            if item.get('goods_type') == GoodsType.MAGIC and item.get('goods_id') == GoodsItem.RAND_MAGIC:
                # 从指定的法宝类型中 随机/挨个 抽取
                magic_types = [mt.value for mt in MagicType if mt != MagicType.DEFAULT]
                if is_rank:
                    selected_magics = random.choices(magic_types, k=item.get('goods_count', 1))
                else:
                    selected_magics = random.sample(magic_types, min(len(magic_types), item.get('goods_count', 1)))

                # 使用字典来跟踪每个法宝的数量
                magic_counts = defaultdict(int)
                for magic in selected_magics:
                    magic_counts[magic] += 1

                # 将字典转换为列表格式
                new_rewards = [
                    {'goods_id': magic_id, 'goods_type': GoodsType.MAGIC, 'goods_count': count}
                    for magic_id, count in magic_counts.items()
                ]
                # 替换原有的随机法宝奖励
                index = awards.index(item)
                awards[index:index + 1] = new_rewards

            # 处理皮肤兑换
            await UserSkinRC.deal_hold_skin(uid, item)

        await GoodsManagerRC.pack_goods_list(awards, is_all=True)
