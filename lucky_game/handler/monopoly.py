"""
大富翁相关游戏格子生成处理类
"""
import random
from common.utils.utils import UtilsTool
from typing import List, Dict, Tuple
from lucky_game.const import CellType


class Monopoly():
    """
    漫漫西行路：

    地图格子总数：32
    固定奖励格：10
    随机奖励格：14，玩家进入后，随机产生，同一总类的奖励不能相邻
    特殊事件格：4
    通用事件格：3，玩家停留后，随机抽取通用事件
    起点：1，玩家每次经过或停留起点，地图上的奖励都会变化，变化结果按照奖励格配置决定
    """

    def __init__(self, position=0, map_conf=None, awards_map=None, awards_conf=None, total_cell=32):
        self.__position = 0 if position is None else position  # 当前位置
        self.__total_cell = total_cell  # 总格数

        self.__map_conf = map_conf or []  # 地图配置（未加载奖励）
        self.__awards_conf = awards_conf or []  # 随机奖池配置
        self.__awards_map = awards_map or {}  # 格子随机奖励ID映射
        self.__cell_map = {}

        self.__cell = []  # 所有格子（奖励加载完毕）
        self.__rand_cell_prob = {}  # 随机奖励格概率
        self.__init_cell_conf()

    @property
    def position(self):
        return self.__position

    @property
    def get_awards_map(self):
        return self.__awards_map

    @property
    def get_all_cell(self) -> List[Dict]:
        return self.__cell

    def __init_cell_conf(self):
        """ 初始化格子 """
        self.__cell = self.__map_conf
        # 有映射不是首次进入
        if self.__awards_map:
            self.__apply_rand_awards()  # 应用随机奖 self.__cell
        else:
            self.gen_rand_awards_conf()  # 重新生成随机奖映射 self.__awards_map
            self.__apply_rand_awards()  # 应用随机奖 self.__cell

    def __apply_rand_awards(self):
        """应用随机奖励到地图格子里"""
        for c in self.__cell:
            cell_id = c.get("cell_id")
            conf_items = self.__awards_map.get(str(cell_id))
            if conf_items:
                c["conf_items"] = conf_items

        return self.__cell

    def __build_cell_map(self):
        """构建格子映射表，将所有格子ID按类型分类"""
        self.__cell_map = {cell_type: [] for cell_type in CellType}
        for c in self.__map_conf:
            cell_type = c.get("cell_type")
            if cell_type in self.__cell_map:
                self.__cell_map[cell_type].append(c.get("cell_id"))

        return self.__cell_map

    def gen_rand_awards_conf(self):
        """ 通过奖励配置生成随机奖励格子（相邻格不能为同等级奖励） """
        rand_conf = {}  # 随机奖励全配置
        self.__build_cell_map()  # 创建格子ID映射 self.__cell_map
        rand_award_cell_ids = self.__cell_map.get(CellType.RAND_AWARD_CELL) or []  # 随机奖励类格子ID

        for i, idx in enumerate(rand_award_cell_ids):
            if i > 0 and idx - 1 == rand_award_cell_ids[i - 1]:
                # 获取上一个奖励格的配置
                last_award = rand_conf.get(rand_award_cell_ids[i - 1], {})
                last_award_level = last_award.get("award_level")

                # 过滤掉上一个格子的奖励等级
                new_awards_conf = [conf for conf in self.__awards_conf if conf.get("award_level") != last_award_level]
                weights = [conf.get("weight") for conf in new_awards_conf]
                select_idx = random.choices(range(len(new_awards_conf)), weights=weights, k=1)[0]
                rand_conf[idx] = new_awards_conf[select_idx]
            else:
                if not self.__rand_cell_prob:  # 初始化概率字典
                    self.__rand_cell_prob = {i: conf.get("weight") for i, conf in enumerate(self.__awards_conf)}

                select_idx = random.choices(list(self.__rand_cell_prob.keys()), weights=list(self.__rand_cell_prob.values()), k=1)[0]
                rand_conf[idx] = self.__awards_conf[select_idx]

        for idx, conf in rand_conf.items():
            self.__awards_map[str(idx)] = conf.get("conf_items") or {}

        self.__apply_rand_awards()  # 应用随机奖 self.__cell
        return self.__awards_map

    def play_steps(self, do_times: int = 1, fixed_steps: int = None) -> Tuple:
        """
        摇骰子
        do_times:摇骰子次数
        fixed_steps:固定点数
        """
        dice_res = []
        cross_start = None  # 存储起点格子配置
        cross_times = 0  # 经过起点的次数
        net_steps = 0  # 净前进步数（前进步数 - 后退步数）

        # 1.计算总步数
        if fixed_steps is not None:  # 如果提供了固定点数（例如使用道具），则使用该点数
            dice_res.append(fixed_steps)
            total_steps = fixed_steps
        else:
            dice_res = [random.randint(1, 6) for _ in range(do_times)]
            total_steps = sum(dice_res)

        # 2.处理移动之后的位置
        if total_steps != 0:
            for _ in range(abs(total_steps)):
                if total_steps > 0:
                    self.__position = (self.__position + 1) % self.__total_cell
                    # 处理正向经过起点的情况
                    if self.__position == 0:
                        self.gen_rand_awards_conf()
                        cross_start = self.__cell[0]  # 保存起点格子信息
                        cross_times += 1
                else:
                    self.__position = (self.__position - 1) % self.__total_cell

            net_steps += total_steps
            cell_res = self.__cell[self.__position]
        # 3.处理定在原地情况
        else:
            cell_res = self.__cell[self.__position] if self.__position != 0 else {}

        # 4. 特殊处理：如果最终停留在起点且经过了起点，以 cross_start 为主
        if self.__position == 0 and cross_start:
            cell_res = {}

        return cell_res, dice_res, net_steps, cross_start, cross_times

    def process_event_result(self, event_conf: dict, is_rookie_task=False):
        """
        处理事件结果
        执行事件前进/后退
        """
        # 根据概率选择一个结局（新手引导任务直接给最好结局）
        ending_odds = event_conf.get("ending_odds", {})
        if is_rookie_task:
            result = min(ending_odds, key=ending_odds.get)
        else:
            result = UtilsTool.select_element_by_prob(ending_odds, size=10000)

        # 初始化事件结果字典（全都有）
        event_res = {
            'event_name': event_conf.get("event_name", ''),
            'ending_type': event_conf.get("conf_ending", {}).get(result, 1),
            'ending_desc': event_conf.get("conf_desc", {}).get(result, ''),
            'desc': event_conf.get("desc", '')
        }

        # 获取 conf_execute（部分有）
        conf_execute = event_conf.get("conf_execute", {})
        if conf_execute:
            event_res['event_execute'] = conf_execute.get(result, 0)

        # 获取 conf_items（部分有）
        conf_items = event_conf.get("conf_items", [])
        if conf_items:
            event_res['event_awards'] = [item for item in conf_items if item.get("level") == int(result)]

        # 如果有执行步数，则进行额外的移动
        event_ex_res = {}
        event_execute = event_res.get("event_execute")
        if event_execute and event_execute != 0:
            cell_res, dice_res, net_steps, cross_start, cross_times = self.play_steps(fixed_steps=event_execute)
            event_ex_res = {
                **cell_res,
                "net_steps": net_steps,
                "cross_times": cross_times
            }

        return event_res, event_ex_res

    @staticmethod
    def stat_step_awards(steps_results):
        """
        统计所有奖励用于发货，添加流水
        """
        all_awards = []
        for s in steps_results:
            # 格子奖
            cell_res = s.get("cell_res")
            if cell_res and cell_res.get("conf_items") and cell_res.get("cell_type") != CellType.START_POINT:
                all_awards.extend(cell_res["conf_items"])

            # 轮回奖
            cross_start = s.get("cross_start")
            if cross_start and cross_start.get("conf_items") and cross_start.get("cell_type") == CellType.START_POINT:
                all_awards.extend(cross_start["conf_items"])

            # 事件格子奖
            event_res = s.get("event_res")
            if event_res and event_res.get("event_awards"):
                all_awards.extend(event_res["event_awards"])

            # 事件执行奖励（例如踩到事件之后，前进或后退踩到的奖励）
            event_ex_res = s.get("event_ex_res")
            if event_ex_res:
                # 执行格子奖
                ex_conf_items = event_ex_res.get("conf_items")
                if ex_conf_items and event_ex_res.get("cell_type") != CellType.START_POINT:
                    all_awards.extend(ex_conf_items)

                # 执行轮回奖（暂不嵌套轮回）
                # ex_cross_start = ex_cell_res.get("cross_start")
                # if ex_cross_start and ex_cross_start.get("conf_items") and ex_cross_start.get("cell_type") == CellType.START_POINT:
                #     all_awards.extend(ex_cross_start["conf_items"])

        return all_awards
