# -*- coding: utf-8 -*-

# todo: 贵阳麻将发好牌接口
#    1.游戏开局时，向指定ID玩家发一副好牌
#    2.游戏对局摸牌时，向指定ID玩家发一张好牌

import random
import itertools

from enum import IntEnum
from collections import defaultdict

from c_services.cs_robot_mahjong.const import HuPaiType, CardType
from common.utils.utils import UtilsTool


class TypeScore(IntEnum):
	"""
	TODO: 卡牌类型分数
	"""
	EDGE_CARD = 19  # 边张
	GAP_CARD = 20  # 坎张
	PAIR = 35  # 对子
	XIAO_SHUN = 40  # 二顺
	SHUN_ZI = 100  # 三顺
	KE_ZI = 115  # 刻子


class Card2Type(IntEnum):
	"""
	TODO: 拆牌之后的最小组合
	"""
	SINGLE_ONE = 0  # 单张
	EDGE_CARD = 1  # 边张
	GAP_CARD = 2  # 坎张
	PAIR = 3  # 对子
	XIAO_SHUN = 4  # 两面(小顺)
	SHUN_ZI = 5  # 顺子
	KE_ZI = 6  # 刻子


# TODO: 牌组合能减少向听数的多少
# 组合能减少的向听数map,卡张|一对|小顺 减少1向听，顺子|刻子减少 2向听
# 不同组合卡牌，能减去有效向听的数量
COMB_REMOVE_XTS = {
	Card2Type.GAP_CARD: 1,  # 减去向听1
	Card2Type.EDGE_CARD: 1,  # 减去向听1
	Card2Type.PAIR: 1,  # 减去向听1
	Card2Type.XIAO_SHUN: 1,  # 减去向听1
	Card2Type.SHUN_ZI: 2,  # 减去向听(三连顺)2
	Card2Type.KE_ZI: 2,  # 减去向听(刻子)2
}


class YxpGenerator:
	"""
	todo: 计算对一个牌型向听数和有效牌
	"""
	# 定义一个变量__slots__，它的作用是阻止在实例化类时为实例分配dict
	# 默认情况下每个类都会有一个dict, 通过__dict__访问，这个dict维护了这个实例的所有属性
	__slots__ = [
		"piles",
		"hand_cards",
		"remain_cards",
		"hand_cards_len",
		"cards_count",
		"qys_flag_len",
		"xqd_flag_len",
		"ddz_flag_len",
		"most_hand_cards_len",
		"others_hand_cards_and_piles",
		"the_worst_xts_by_hu_type",
	]

	def __init__(self):
		"""
		初始化属性参数
		"""
		self.piles = []  # 碰、杠
		self.hand_cards = []  # 手牌
		self.remain_cards = {}  # 剩余卡牌
		self.hand_cards_len = 0  # 手牌数量
		self.cards_count = {}
		self.qys_flag_len = 8  # 清一色标识(手牌同一种花色卡牌数量大于9)
		self.xqd_flag_len = 4  # 小七对标识(当前手牌对子数量大于4)
		self.ddz_flag_len = 3  # 大队子标识(当前手牌对子数大于3)
		self.most_hand_cards_len = 14  # 最大手牌数量
		self.others_hand_cards_and_piles = []
		self.the_worst_xts_by_hu_type = ...  # 胡牌类型最坏向听数

	def update_attr(self, hand_cards=None, piles=None, other_cards_and_piles=None, remain_cards=None):
		"""
		更新卡牌参数属性
		"""
		self.piles = piles or []
		self.others_hand_cards_and_piles = other_cards_and_piles or []
		self.remain_cards = {int(key): value for key, value in self.cards_to_count(remain_cards).items()} or {}
		self.hand_cards = hand_cards or []
		self.hand_cards_len = len(hand_cards)

		# todo: 胡牌类型 -> 平胡、大对子、小七对、龙七对、清一色
		pong_gong_nums = 4 - self.hand_cards_len // 3

		self.the_worst_xts_by_hu_type = {
			HuPaiType.PING_HU: (self.most_hand_cards_len - 5 - 1) - pong_gong_nums * 2,
			HuPaiType.DA_DUI_ZI: (self.most_hand_cards_len - 5 - 1) - pong_gong_nums * 2
		}
		# todo: 手牌数量为14张时，计算小七对、龙七对
		if self.hand_cards_len == self.most_hand_cards_len:
			self.the_worst_xts_by_hu_type[HuPaiType.QI_DUI] = (self.most_hand_cards_len // 2) - 1
			self.the_worst_xts_by_hu_type[HuPaiType.LONG_QI_DUI] = (self.most_hand_cards_len // 2) - 1

		# todo: 手牌数量为11张时，计算地龙七
		if self.hand_cards_len == 11:
			self.the_worst_xts_by_hu_type[HuPaiType.DI_LONG_QI] = (self.most_hand_cards_len // 2) - 2

	def calc_cards_to_count(self, cards=None) -> dict:
		"""
		计算出手牌每张牌的数量
		已经去除癞子
		cards: 如果不传则就计算手牌
		"""
		if not cards:
			if not self.cards_count:
				cards = self.hand_cards[:]
				self.remove_by_value(cards, CardType.LAI_ZI, -1)
				self.cards_count = self.cards_to_count(cards)
			return self.cards_count
		else:
			self.remove_by_value(cards, CardType.LAI_ZI, -1)
			return self.cards_to_count(cards)

	def calc_cards_list_by_count(self):
		""" 计算不同数量的cards """
		one_list = []  # 单张卡牌
		two_list = []  # 对子
		three_list = []  # 刻子
		four_list = []  # 四张
		cards_to_count = self.calc_cards_to_count()
		for card, count in cards_to_count.items():
			if count == 1:
				one_list.append(card)
			elif count == 2:
				two_list.append(card)
			elif count == 3:
				three_list.append(card)
			else:
				four_list.append(card)

		return one_list, two_list, three_list, four_list

	@staticmethod
	def remove_by_value(data, value, remove_count=1):
		"""
		删除列表data中的value
		:param data: list
		:param value:
		:param remove_count: 为-1的时候表示删除全部, 默认为1
		:return: already_remove_count: int
		"""
		data_len = len(data)
		count = remove_count == -1 and data_len or remove_count

		already_remove_count = 0

		for i in range(0, count):
			if value in data:
				data.remove(value)
				already_remove_count += 1
			else:
				break

		return already_remove_count

	@staticmethod
	def gen_serial_moves(single_cards, min_serial=2, max_serial=3, repeat=1, solid_num=0):
		"""
		减去 对子/刻子 后的所有搭子（两面，坎张，顺子）
		params: cards 输入牌
		params: min_serial  最小连数
		params: max_serial  最大连数
		params: repeat  重复牌数
		params: solid_num  固定连数
		拆牌：坎张|两面|
		"""
		seq_records = list()
		result = list()

		cards_len = len(single_cards)

		# 至少重复数是最小序列
		if solid_num < min_serial:
			solid_num = 0

		# 顺子（最少2张）
		start = i = 0
		longest = 1
		while i < cards_len:
			# 判断连续两张牌
			if i + 1 < cards_len and single_cards[i + 1] - single_cards[i] == 1:
				longest += 1
				i += 1
			else:
				# 记录索引
				seq_records.append((start, longest))
				i += 1
				start = i
				longest = 1

		for seq in seq_records:
			if seq[1] < min_serial:
				continue
			start, longest = seq[0], seq[1]
			longest_list = single_cards[start: start + longest]

			if solid_num == 0:  # No limitation on how many sequences
				steps = min_serial  # 最小连数
				while steps <= longest:
					index = 0
					while steps + index <= longest:
						target_moves = sorted(longest_list[index: index + steps] * repeat)
						result.append(target_moves)
						index += 1
					steps += 1  # 递增
					if steps > max_serial:
						break
			else:
				if longest < solid_num:
					continue
				index = 0
				while index + solid_num <= longest:
					target_moves = sorted(longest_list[index: index + solid_num] * repeat)
					result.append(target_moves)
					index += 1
		# 坎张
		i = 0
		while i < cards_len:
			# 连续的两张坎张
			start_val = single_cards[i] % 10
			if start_val > 7:
				i += 1
				continue
			if i + 1 < cards_len and single_cards[i] + 2 == single_cards[i + 1]:
				result.append(single_cards[i: i + min_serial])
			# 间隔的两张坎张
			if i + 2 < cards_len and single_cards[i] + 2 == single_cards[i + 2]:
				result.append([single_cards[i], single_cards[i + 2]])
			i += 1

		return result

	@staticmethod
	def get_repeat_cards(cards):
		"""
		params: cards 输入牌
		params: min_num  最小连数
		params: max_serial  最大连数
		params: solid_num  固定连数
		找出相同的牌，如：22,22 | 22,22,22
		找出坎张，如：11,13| 22,24
		"""
		result = []
		card_to_count = YxpGenerator.cards_to_count(cards)

		for card, count in card_to_count.items():
			if count <= 1:
				continue
			if count == 4:
				result.append([card] * 2)
				result.append([card] * 3)
				result.append([card] * 4)
			elif count == 3:
				result.append([card] * 2)
				result.append([card] * 3)
			else:
				result.append([card] * 2)
		return result

	@staticmethod
	def get_value(card):
		return card % 10

	@staticmethod
	def cards_to_count(cards):
		"""
		统计卡牌数量(dict)
		"""
		card_to_count = dict()
		for c in cards:
			card_to_count[c] = card_to_count.get(c, 0) + 1
		return card_to_count

	@staticmethod
	def judge_cards_type(cards: list):
		"""
		判断卡牌组合类型
		"""
		cards_len = len(cards)

		# TODO: 单张(长度为1)
		if cards_len == 1:
			return Card2Type.SINGLE_ONE

		# TODO: 两张(长度为2)
		if cards_len == 2:
			# 对子
			if cards[0] == cards[1]:
				return Card2Type.PAIR
			# 边张
			elif cards[0] + 1 == cards[1]:
				if cards[0] == 1 or cards[0] == 8:
					return Card2Type.EDGE_CARD
				# 两张，顺子
				return Card2Type.XIAO_SHUN
			# 坎张(间隔顺子)
			elif cards[0] + 2 == cards[1]:
				return Card2Type.GAP_CARD

		# TODO: 顺子，刻子(长度为3)
		elif cards_len == 3:
			# 三连顺
			if cards[0] == cards[1] == cards[2]:
				return Card2Type.SHUN_ZI
			# 刻子(三同)
			elif cards[0] + 1 == cards[1] and cards[1] + 1 == cards[2]:
				return Card2Type.KE_ZI

	def cal_xts_ping_hu(self, *args, need_mz=None):
		"""
		计算平胡向听数判断平胡
		"""
		# 胡牌类型(平胡)
		# 参数解析(单张、两张、三张、四张)
		one_list, two_list, three_list, four_list = args

		# 面子(顺子、刻子)
		# 平胡: 1个对子 + 4个面子 -> (2 + 3 x 4) = 14
		need_mz = need_mz or self.hand_cards_len // 3
		need_heap = need_mz if need_mz > 0 else 0  # 需要多少堆
		optimal_path = []

		record_lowest_xts = 8  # 最小的向听数（仅平胡）用于全局记录最低的向听数
		the_worst_xts = self.the_worst_xts_by_hu_type.get(HuPaiType.PING_HU)  # 当前牌的最坏向听数（减去了碰杠）
		jiang_list = two_list + three_list + four_list  # 不添单张(计算大于两张的卡牌)

		# if not two_list:
		jiang_list += one_list
		for pair in jiang_list:  # 列表相加得到新实例
			new_hand_cards = self.hand_cards[:]
			self.remove_by_value(new_hand_cards, pair, 2)  # 减去对子（平胡只能有一个将）
			# 当做将的对子不是从刻子中取的，则先拆刻子
			if pair in one_list:
				split_path = [[pair]]
			else:
				split_path = [[pair] * 2]

			# print(f"对子(将牌): {pair}, 所需搭子数: {need_heap}")

			def optimal_split_cards(hand_cards):
				"""
				TODO: 最优拆牌
				params: new_hand_cards  去掉对子/刻子的手牌
				params: optimal_path 最优路径
				params: all_split_cards 所有组合
				params: need_heap  需要堆数
				"""
				nonlocal self
				nonlocal optimal_path
				nonlocal record_lowest_xts
				nonlocal need_heap
				nonlocal split_path

				# 减去 对子/刻子 后的所有搭子
				# todo: 遍历找出顺子
				all_split_cards = []
				hand_cards_copy = hand_cards[:]
				count = 0
				extra_shun = []
				while hand_cards_copy:
					# 此操作为了找出所有的顺子（包含小顺）
					single_cards = sorted(list(set(hand_cards_copy)))
					for sc in single_cards:
						hand_cards_copy.remove(sc)

					# 计算所有顺子(三连顺，二连顺，咔张)
					all_shun = self.gen_serial_moves(single_cards)
					if count > 0:
						# all_shun = [shun for shun in all_shun if len(shun) == 3]
						extra_shun.extend(all_shun)
					if not all_shun:
						break
					all_split_cards.extend(all_shun)
					count += 1

				# 计算每一张手牌对应的数量(统计当前卡牌数量)
				new_cards_to_count = self.calc_cards_to_count(hand_cards)
				if not all_split_cards:
					if record_lowest_xts < the_worst_xts:
						return
					record_lowest_xts = the_worst_xts
					res_split_cards = split_path[:]
					for card, count in new_cards_to_count.items():
						count > 0 and res_split_cards.append([card] * count)
					optimal_path.append(res_split_cards)
				else:
					all_can_comb_shun_cards = []
					for shun in all_split_cards:
						all_can_comb_shun_cards.extend(shun)
					all_can_comb_shun_cards = list(set(all_can_comb_shun_cards))
					if extra_shun:
						es_shun_cards = []
						for es in extra_shun:
							es_shun_cards.extend(es)
						all_can_comb_shun_cards.extend(list(set(es_shun_cards)))

					new_cards_to_count_copy = new_cards_to_count.copy()
					for s in all_can_comb_shun_cards:
						if s in new_cards_to_count:
							new_cards_to_count_copy[s] -= 1
					extra_comb = []

					# 计算刻子
					for card, count in new_cards_to_count_copy.items():
						if count > 0:
							# 刻子统一在下面添加，此处可能原本刻子被拆了
							if count == 3 and card in three_list:
								continue
							extra_comb.append([card] * count)

					extra_pair = []
					for two in two_list:
						if two == pair:
							continue
						two_val = self.get_value(two)
						if two_val == 1:
							if new_cards_to_count_copy.get(two + 1) or new_cards_to_count_copy.get(two + 2):
								extra_pair.append([two] * 2)
						elif two_val == 2:
							if new_cards_to_count_copy.get(two - 1) or new_cards_to_count_copy.get(
									two + 1) or new_cards_to_count_copy.get(two + 2):
								extra_pair.append([two] * 2)
						elif two_val == 8:
							if new_cards_to_count_copy.get(two + 1) or new_cards_to_count_copy.get(
									two - 1) or new_cards_to_count_copy.get(two - 2):
								extra_pair.append([two] * 2)
						elif two_val == 9:
							if new_cards_to_count_copy.get(two - 1) or new_cards_to_count_copy.get(two - 2):
								extra_pair.append([two] * 2)
						else:
							if new_cards_to_count_copy.get(two - 1) or new_cards_to_count_copy.get(two - 2) or \
									new_cards_to_count_copy.get(two + 1) or new_cards_to_count_copy.get(two + 2):
								extra_pair.append([two] * 2)

					all_split_cards.extend(extra_pair)
					ke_zi = [[card] * 3 for card in three_list + four_list if card != pair]  # 刻子也添加进去
					all_split_cards.extend(ke_zi)
					all_split_cards.extend(extra_comb)

					# 先拆顺子
					# TODO: 再计算搭子(二连顺、间隔顺)
					curr_heap_idx = 0  # 当前堆的索引
					record_comb = ...
					all_comb = itertools.combinations(range(len(all_split_cards)), need_heap)
					# all_comb_list = list(all_comb)
					# print("所有组合长度：", len(all_comb_list), all_comb_list)
					for comb in all_comb:
						if comb[:curr_heap_idx + 1] == record_comb:
							continue
						# 统计每一张手牌数量
						cards_to_count_copy = new_cards_to_count.copy()
						comb_list = []
						curr_heap_idx = 0
						record_comb = ...
						flag = True
						# 根据所需的搭子数，计算搭子
						for i in range(need_heap):
							curr_heap_idx = i
							one_comb = all_split_cards[comb[i]]
							for c in one_comb:
								if cards_to_count_copy.get(c, 0) <= 0:
									flag = False
									record_comb = comb[:i + 1]
									break
								cards_to_count_copy[c] -= 1
							if not flag:
								comb_list.clear()
								break
							comb_list.append(one_comb)

						if comb_list:
							res_split_cards = []
							res_split_cards.extend(split_path)
							res_split_cards.extend(comb_list)

							# 平胡拆牌后，计算向听数 注意：res_split_cards就是根据需要堆数的组合，所以不用考虑多个对子的向听数问题
							xts = the_worst_xts
							for sc in res_split_cards:
								comb_type = self.judge_cards_type(sc)
								comb_xts = COMB_REMOVE_XTS.get(comb_type, 0)
								xts -= comb_xts

							for card, count in cards_to_count_copy.items():
								count > 0 and res_split_cards.append([card] * count)

							if xts < record_lowest_xts:
								optimal_path.clear()
								optimal_path.append(res_split_cards)
								record_lowest_xts = xts

							elif xts == record_lowest_xts:
								optimal_path.append(res_split_cards)

			optimal_split_cards(new_hand_cards)

		# 去重
		deduplicate = []
		for op in optimal_path:
			if op in deduplicate:
				continue
			deduplicate.append(op)

		mo_yxp = self.calc_ping_hu_by_yxp(optimal_path)

		return record_lowest_xts, mo_yxp

	def calc_ping_hu_by_yxp(self, optimal_paths):
		"""
		计算一轮结束后，真人玩家叫牌后所听的牌
		"""
		yxp = []
		for idx, optimal_path in enumerate(optimal_paths):
			for cards in optimal_path:
				if len(cards) == 1:
					yxp.extend(cards)
				if len(cards) == 2:
					result = self.calc_two_cards_by_yxp(cards)
					yxp.extend(result)

		return list(set(yxp))

	def calc_two_cards_by_yxp(self, cards):
		"""
		计算卡牌为两张时，有效听牌
		"""
		yxp = []
		if cards[0] == cards[-1]:
			yxp.append(cards[0])

		elif cards[0] + 1 == cards[-1]:
			if 0 < self.get_value(cards[0]) - 1 <= 9:
				yxp.append(cards[0] - 1)

			if 0 < self.get_value(cards[-1]) + 1 <= 9:
				yxp.append(cards[-1] + 1)

		elif cards[-1] - cards[0] == 2:
			if 0 < self.get_value(cards[0]) + 1 <= 9:
				yxp.append(cards[0] + 1)

		return yxp

	def cal_xts_da_dui_zi(self, *args):
		""" 大对子 """
		the_worst_xts = self.the_worst_xts_by_hu_type.get(HuPaiType.DA_DUI_ZI)
		one_list, two_list, three_list, four_list = args
		need_heap = self.hand_cards_len // 3 + 1  # 刻子数 + 一对
		two_len = len(two_list)
		real_xts = the_worst_xts - two_len if two_len <= need_heap else the_worst_xts - need_heap
		real_xts -= len(three_list + four_list) * 2

		extra_one = []
		optimal_split_cards = []
		for four in four_list:
			optimal_split_cards.append([four] * 3)
			extra_one.append(four)
		for three in three_list:
			optimal_split_cards.append([three] * 3)
		for two in two_list:
			optimal_split_cards.append([two] * 2)

		tmp_yxp_cards = set()
		two_list_len = len(two_list)
		for path in optimal_split_cards:
			if len(path) == 3:
				continue
			# 添加一张有效对子牌
			if two_list_len != 1:
				tmp_yxp_cards.add(path[0])

		extra_one.extend(one_list)
		record_chu_pai = {}
		if extra_one:
			optimal_split_cards.extend([[one] for one in extra_one])
			for c in extra_one:
				yxp_copy = tmp_yxp_cards.copy()
				yxp_copy.update(set(extra_one))
				yxp_copy.remove(c)
				record_chu_pai[c] = yxp_copy
		else:
			if len(two_list) > 1:
				for c in tmp_yxp_cards:
					yxp_copy = tmp_yxp_cards.copy()
					yxp_copy.remove(c)
					record_chu_pai[c] = yxp_copy

		# 从出牌中，计算有利的有效牌
		yxp_cards = []
		for chu_pai, tmp_yxp in record_chu_pai.items():
			yxp_cards.extend(tmp_yxp)

		if not yxp_cards:
			yxp_cards += one_list + two_list

		return real_xts, list(set(yxp_cards))

	def cal_xts_by_qi_dui(self, *args):
		""" 计算当前手牌按七对胡牌类型的向听数 """
		the_worst_xts = self.the_worst_xts_by_hu_type.get(HuPaiType.QI_DUI)  # 最坏向听数
		one_list, two_list, three_list, four_list = args  # self.calc_cards_list_by_count()
		reduce_one_xts = len(two_list + three_list)
		reduce_two_xts = len(four_list) * 2
		real_xts = the_worst_xts - reduce_one_xts - reduce_two_xts  # 真实向听数
		extra_one = []
		optimal_split_cards = []
		for four in four_list:
			optimal_split_cards.append([four] * 4)
		for three in three_list:
			optimal_split_cards.append([three] * 2)
			extra_one.append(three)
		for two in two_list:
			optimal_split_cards.append([two] * 2)

		extra_one.extend(one_list)  # 单牌
		optimal_split_cards.extend([[one] for one in extra_one])
		record_chu_pai = {}
		for c in extra_one:
			tmp_yxp_cards = set(extra_one)
			tmp_yxp_cards.remove(c)
			record_chu_pai[c] = tmp_yxp_cards

		# 从出牌中，计算有利的有效牌
		yxp_cards = []
		for chu_pai, tmp_yxp in record_chu_pai.items():
			yxp_cards.extend(tmp_yxp)

		if not yxp_cards:
			yxp_cards += one_list

		return real_xts, list(set(yxp_cards))

	def cal_xts_by_long_qi_dui(self, *args):
		"""
		龙七对
		"""
		return self.cal_xts_by_qi_dui(*args)

	def cal_xts_by_di_long_qi(self, *args):
		""" 计算当前手牌按地龙七胡牌类型的向听数 """
		the_worst_xts = self.the_worst_xts_by_hu_type.get(HuPaiType.DI_LONG_QI)  # 最坏向听数
		one_list, two_list, three_list, four_list = args
		real_xts = the_worst_xts - len(two_list)
		extra_one = []
		optimal_split_cards = []
		for four in four_list:
			optimal_split_cards.append([four] * 4)
		for three in three_list:
			optimal_split_cards.append([three] * 2)
			extra_one.append(three)
		for two in two_list:
			optimal_split_cards.append([two] * 2)

		extra_one.extend(one_list)  # 单牌
		optimal_split_cards.extend([[one] for one in extra_one])
		record_chu_pai = {}
		for c in extra_one:
			tmp_yxp_cards = set(extra_one)
			tmp_yxp_cards.remove(c)
			record_chu_pai[c] = tmp_yxp_cards

		# 从出牌中，计算有利的有效牌
		yxp_cards = []
		for chu_pai, tmp_yxp in record_chu_pai.items():
			yxp_cards.extend(tmp_yxp)

		return real_xts, list(set(yxp_cards))

	def get_mo_cards_before_by_xts(self):
		"""
		计算摸牌之前各种牌型向听数大小
		"""
		print("根据手牌计算摸牌前摸到有利的摸牌: {}，手牌数量为: {}".format(self.hand_cards, len(self.hand_cards)))
		args = self.calc_cards_list_by_count()

		# 添加卡牌参数
		all_xts_yxp = []  # 存储向听数和有效牌
		all_yxp_cards = []  # 存储所有有效牌
		xts_hu_cards = []  # 向听数为0时，所需要的有效卡牌

		# 平胡
		xts1, ph_yxp = self.cal_xts_ping_hu(*args)
		print("平胡向听数: {}, 有利摸牌: {}".format(xts1, ph_yxp))
		print()
		all_yxp_cards.extend(ph_yxp)
		all_xts_yxp.append((xts1, 'ph', ph_yxp))
		# 形成胡牌时，则加能胡的卡牌
		if xts1 == 0:
			xts_hu_cards.extend(ph_yxp)

		# 大对子
		xts2, ddz_yxp = self.cal_xts_da_dui_zi(*args)
		if xts2 < self.xqd_flag_len:
			print("大对子向听数: {}, 有利摸牌: {}".format(xts2, ddz_yxp))
			print()
			all_yxp_cards.extend(ddz_yxp)
			all_xts_yxp.append((xts2, 'ddz', ddz_yxp))
		# 形成胡牌时，则加能胡的卡牌
		if xts2 == 0:
			xts_hu_cards.extend(ddz_yxp)

		if len(args[2]) > self.ddz_flag_len and self.hand_cards_len == 14:
			# 小七对
			xts3, qd_yxp = self.cal_xts_by_qi_dui(*args)
			if xts3 < self.xqd_flag_len:
				print("小七对向听数: {}, 有利摸牌: {}".format(xts3, qd_yxp))
				print()
				all_yxp_cards.extend(qd_yxp)
				all_xts_yxp.append((xts3, 'xqd', qd_yxp))
			# 形成胡牌时，则加能胡的卡牌
			if xts3 == 0:
				xts_hu_cards.extend(qd_yxp)

		# 龙七对
		if len(args[3]) > 1 and self.hand_cards_len == 14:
			# 龙七对
			xts4, lqd_yxp = self.cal_xts_by_long_qi_dui(*args)
			if xts4 < self.xqd_flag_len:
				print("龙七对向听数: {}, 有利摸牌: {}".format(xts4, lqd_yxp))
				print()
				all_yxp_cards.extend(lqd_yxp)
				all_xts_yxp.append((xts4, 'lqd', lqd_yxp))
			# 形成胡牌时，则加能胡的卡牌
			if xts4 == 0:
				xts_hu_cards.extend(lqd_yxp)

		# 添加游戏随机性，不对平胡和大牌做限制处理
		return self.calc_remain_cards_contain_yxp(list(set(all_yxp_cards))), list(set(all_yxp_cards)), list(set(xts_hu_cards))

	def calc_qing_yi_se(self):
		"""
		检查手牌是否都是同一颜色
		"""
		tmp_hand_cards = self.hand_cards[:]
		cards_by_type = defaultdict(list)
		# 计算卡牌花色和牌值
		for card in tmp_hand_cards:
			# 处理手牌中的癞子牌
			if card == CardType.LAI_ZI:
				continue
			card_type = card // 10
			cards_by_type[card_type].append(card)
		for card_type, card_value in cards_by_type.items():
			if len(card_value) < self.qys_flag_len:
				continue
			return True, card_value
		return False, []

	def qing_yi_se_condition(self):
		"""
		检查手牌是否都是同一颜色
		"""
		tmp_hand_cards = self.hand_cards[:]
		cards_by_type = defaultdict(list)
		# 计算卡牌花色和牌值
		for card in tmp_hand_cards:
			# 处理手牌中的癞子牌
			if card == CardType.LAI_ZI:
				continue
			card_type = card // 10
			cards_by_type[card_type].append(card)
		# 返回卡牌类型和牌值
		return cards_by_type

	def count_pg_types(self, card_type):
		"""
		判断当前手牌与碰杠牌是否为同一种花色
		"""
		pg_cards = sum([pile[1:-1] for pile in self.piles], [])
		count_type = list(self.calc_same_card_type(pg_cards).keys())
		if len(count_type) == 1:
			if count_type[0] == card_type:
				return pg_cards
		return []

	@staticmethod
	def calc_same_card_type(cards):
		"""
		计算当前手牌花色情况
		"""
		cards_type = defaultdict(list)
		for card in cards:
			# 不计算癞子牌
			if card == CardType.LAI_ZI:
				continue
			tmp_type = card // 10
			cards_type[tmp_type].append(card)
		return cards_type

	def calc_round_qing_yi_se(self):
		"""
		TODO: 计算其他两位玩家是否与自己作同一花色牌型
		"""
		self_qys_type = False
		self_cards_type = self.qing_yi_se_condition()
		for self_type, self_cards in self_cards_type.items():
			pg_cards = self.count_pg_types(self_type)
			if pg_cards:
				if len(pg_cards) + len(self_cards) > self.qys_flag_len:
					self_qys_type = self_type
					break
			if len(self_cards) > self.qys_flag_len:
				self_qys_type = self_type
				break
		if len(list(self_cards_type.keys())) == 1 or self_qys_type:
			for cards_piles in self.others_hand_cards_and_piles:
				pg_cards = sum([pile[1:-1] for pile in cards_piles[-1]], [])
				pg_cards_type = self.calc_same_card_type(pg_cards)
				hd_cards_type = self.calc_same_card_type(cards_piles[0])
				if pg_cards and self_qys_type:
					hd_cards = hd_cards_type[self_qys_type]
					if hd_cards and list(pg_cards_type.keys())[0] == self_qys_type:
						if len(pg_cards) + len(hd_cards) > self.qys_flag_len + 1:
							return False
				for hd_type, hd_cards in hd_cards_type.items():
					if hd_type == self_qys_type and len(hd_cards) > self.qys_flag_len:
						return False
		if self_qys_type or len(list(self_cards_type.keys())) == 1:
			return self_qys_type
		return False

	def get_mo_cards_by_big_cards(self):
		"""
		添加真人玩家摸大牌
		"""
		all_yxp_cards = []
		xts_hu_cards = []

		# 计算参数
		args = self.calc_cards_list_by_count()

		# 判断清一色
		is_qys_flag = self.calc_round_qing_yi_se()
		xts1, ph_yxp = self.cal_xts_ping_hu(*args)
		all_yxp_cards.extend(ph_yxp)
		if xts1 == 0:
			xts_hu_cards.extend(ph_yxp)

		# 清一色
		if is_qys_flag:
			qing_yi_se_yxp_cards = list(set(all_yxp_cards))
			all_qys_yxp = list(set(all_yxp_cards))
			hu_cards = list(set(xts_hu_cards))
			return self.calc_remain_cards_contain_yxp(qing_yi_se_yxp_cards), all_qys_yxp, hu_cards

		# 大对子
		xts2, ddz_yxp = self.cal_xts_da_dui_zi(*args)
		if xts2 < self.xqd_flag_len:
			all_yxp_cards.extend(ddz_yxp)
			if xts2 == 0:
				xts_hu_cards.extend(ddz_yxp)
			all_qys_yxp = list(set(all_yxp_cards))
			hu_cards = list(set(xts_hu_cards))
			return self.calc_remain_cards_contain_yxp(ddz_yxp), all_qys_yxp, hu_cards

		# 七对或龙七对
		if self.hand_cards_len == 14:
			# 七对
			if len(args[2]) > self.ddz_flag_len:
				xts3, qd_yxp = self.cal_xts_by_qi_dui(*args)
				if xts3 < self.xqd_flag_len:
					all_yxp_cards.extend(qd_yxp)
					if xts3 == 0:
						xts_hu_cards.extend(qd_yxp)
					all_qys_yxp = list(set(all_yxp_cards))
					hu_cards = list(set(xts_hu_cards))
					return self.calc_remain_cards_contain_yxp(qd_yxp), all_qys_yxp, hu_cards

			# 龙七对
			if len(args[3]) > 1:
				xts4, lqd_yxp = self.cal_xts_by_long_qi_dui(*args)
				if xts4 < self.xqd_flag_len:
					all_yxp_cards.extend(lqd_yxp)
					if xts4 == 0:
						xts_hu_cards.extend(lqd_yxp)
					all_qys_yxp = list(set(all_yxp_cards))
					hu_cards = list(set(xts_hu_cards))
					return self.calc_remain_cards_contain_yxp(lqd_yxp), all_qys_yxp, hu_cards

		# 大对子
		elif self.hand_cards_len == 11:
			if len(args[1]) + len(args[2]) > 2 or len(args[1]) > 2:
				xts5, ddz_11 = self.cal_xts_da_dui_zi(*args)
				all_yxp_cards.extend(ddz_11)
				if xts5 == 0:
					xts_hu_cards.extend(ddz_11)
				all_qys_yxp = list(set(all_yxp_cards))
				hu_cards = list(set(xts_hu_cards))
				return self.calc_remain_cards_contain_yxp(ddz_11), all_qys_yxp, hu_cards

		# 大对子
		elif self.hand_cards_len < 11:
			if self.count_pg_types(self.hand_cards[0] // 10):
				if len(args[1]) + len(args[2]) > 2 or \
						len(args[1]) + len(self.piles) > 2 or \
						len(args[1]) + len(args[2]) + len(self.piles) > 3:
					xts6, ddz_lt_11 = self.cal_xts_da_dui_zi(*args)
					all_yxp_cards.extend(ddz_lt_11)
					if xts6 == 0:
						xts_hu_cards.extend(ddz_lt_11)
					all_qys_yxp = list(set(all_yxp_cards))
					hu_cards = list(set(xts_hu_cards))
					return self.calc_remain_cards_contain_yxp(ddz_lt_11), all_qys_yxp, hu_cards

		# 平胡
		ph_yxp_cards = list(set(all_yxp_cards))
		all_qys_yxp = list(set(all_yxp_cards))
		hu_cards = list(set(xts_hu_cards))
		return self.calc_remain_cards_contain_yxp(ph_yxp_cards), all_qys_yxp, hu_cards

	def calc_remain_cards_contain_yxp(self, remain_yxp):
		"""
		计算剩余卡牌中包含的有效卡牌
		"""
		count = 0
		best_yxp = []
		for tmp_yxp in remain_yxp:
			tmp_count = 0
			# 计算剩余卡牌中有效牌最多的卡牌
			if tmp_yxp in list(self.remain_cards.keys()):
				tmp_count += self.remain_cards[tmp_yxp]
			# 剩余卡牌数量相同时，也将其添加至
			# if tmp_count == count and tmp_count != 0:
			# 	best_yxp.append(tmp_yxp)
			if tmp_count > count:
				best_yxp.clear()
				count = tmp_count
				best_yxp.append(tmp_yxp)

		# 处理异常情况
		if not best_yxp:
			return remain_yxp

		return best_yxp

def calc_best_cards_by_hfc(data):
	"""
	todo: 计算机器人摸最好牌(话费场真人或机器人摸好牌控制)
	"""
	yxp_gen = YxpGenerator()
	yxp_gen.update_attr(
		data.get("curr_hand_cards"),
		data.get("piles"),
		data.get("others_cards_and_piles"),
		data.get("remain_cards")
	)
	choice_pro = [0.5]
	best_yxp, all_yxp, hu_cards = yxp_gen.get_mo_cards_before_by_xts()
	remain_cards = remove_best_cards_by_remain_cards(best_yxp, all_yxp, data.get("remain_cards"))
	if not remain_cards:
		return random.choice(best_yxp)

	# 控制机器人摸好牌的概率
	if remain_cards and len(remain_cards) > 1:
		best_yxp.extend(random.sample(remain_cards, 1))

	# 摸好牌概率分布
	if len(best_yxp) == 2:
		if data.get("is_robot", 0):
			choice_pro = [0.35, 0.65]
		else:
			choice_pro = [0.6, 0.4]
	elif len(best_yxp) == 3:
		if data.get("is_robot", 0):
			choice_pro = [0.3, 0.4, 0.4]
		else:
			choice_pro = [0.4, 0.3, 0.3]

	choice_card = UtilsTool.random_choice_num(best_yxp, choice_pro)
	print("计算当前是否为机器人: {}, 选择最佳摸牌: {}".format(data["is_robot"], choice_card))

	return int(choice_card), hu_cards

def calc_best_cards_by_xxc(data):
	"""
	todo: 计算机器人摸最好牌(休闲场真人或机器人摸好牌控制)
	"""
	yxp_gen = YxpGenerator()
	yxp_gen.update_attr(
		data.get("curr_hand_cards"),
		data.get("piles"),
		data.get("others_cards_and_piles"),
		data.get("remain_cards")
	)
	choice_pro = [0.5]
	best_yxp, all_yxp, hu_cards = yxp_gen.get_mo_cards_by_big_cards()
	remain_cards = remove_best_cards_by_remain_cards(best_yxp, all_yxp, data.get("remain_cards"))
	if not remain_cards:
		return random.choice(best_yxp)

	# 控制机器人摸好牌的概率
	if remain_cards and len(remain_cards) > 1:
		best_yxp.extend(random.sample(remain_cards, 1))

	# 摸好牌概率分布
	if len(best_yxp) == 2:
		if data.get("is_robot", 0):
			choice_pro = [0.35, 0.65]
		else:
			choice_pro = [0.5, 0.5]
	elif len(best_yxp) == 3:
		if data.get("is_robot", 0):
			choice_pro = [0.3, 0.4, 0.4]
		else:
			choice_pro = [0.4, 0.3, 0.3]

	choice_card = UtilsTool.random_choice_num(best_yxp, choice_pro)
	print("计算当前是否为机器人: {}, 选择最佳摸牌: {}".format(data["is_robot"], choice_card))

	return int(choice_card), hu_cards

def calc_best_cards_by_lpy(data):
	"""
	todo: 计算机器人摸最好牌(休闲场真人或机器人摸好牌控制)
	"""
	yxp_gen = YxpGenerator()
	yxp_gen.update_attr(
		data.get("curr_hand_cards"),
		data.get("piles"),
		data.get("others_cards_and_piles"),
		data.get("remain_cards")
	)
	choice_pro = [0.5]
	best_yxp, all_yxp, hu_cards = yxp_gen.get_mo_cards_by_big_cards()
	remain_cards = remove_best_cards_by_remain_cards(best_yxp, all_yxp, data.get("remain_cards"))
	if not remain_cards:
		return random.choice(best_yxp)

	# 控制机器人摸好牌的概率
	if remain_cards and len(remain_cards) > 1:
		best_yxp.extend(random.sample(remain_cards, 1))

	# 摸好牌概率分布
	if len(best_yxp) == 2:
		if data.get("is_robot", 0):
			choice_pro = [0.4, 0.6]
		else:
			choice_pro = [0.5, 0.5]

	elif len(best_yxp) == 3:
		if data.get("is_robot", 0):
			choice_pro = [0.3, 0.4, 0.4]
			if data.get("match_id", 0) == 5:
				choice_pro = [0.2, 0.4, 0.4]
		else:
			choice_pro = [0.4, 0.3, 0.3]

	choice_card = UtilsTool.random_choice_num(best_yxp, choice_pro)
	print("计算当前是否为机器人: {}, 选择最佳摸牌: {}".format(data["is_robot"], choice_card))

	return int(choice_card), hu_cards

def calc_best_cards_by_lpy_uid(data):
	"""
	todo: 计算机器人摸最好牌(休闲场真人或机器人摸好牌控制)
	"""
	yxp_gen = YxpGenerator()
	yxp_gen.update_attr(
		data.get("curr_hand_cards"),
		data.get("piles"),
		data.get("others_cards_and_piles"),
		data.get("remain_cards")
	)
	choice_pro = [0.5]
	best_yxp, all_yxp, hu_cards = yxp_gen.get_mo_cards_by_big_cards()
	remain_cards = remove_best_cards_by_remain_cards(best_yxp, all_yxp, data.get("remain_cards"))
	if not remain_cards:
		return random.choice(best_yxp)

	# 控制机器人摸好牌的概率
	if remain_cards and len(remain_cards) > 1:
		best_yxp.extend(random.sample(remain_cards, 1))

	# 摸好牌概率分布
	if len(best_yxp) == 2:
		if data.get("is_robot", 0):
			choice_pro = [0.65, 0.35]
		else:
			choice_pro = [0.5, 0.5]

	elif len(best_yxp) == 3:
		if data.get("is_robot", 0):
			choice_pro = [0.3, 0.4, 0.4]
			if data.get("match_id", 0) == 5:
				choice_pro = [0.2, 0.4, 0.4]
		else:
			choice_pro = [0.4, 0.3, 0.3]

	choice_card = UtilsTool.random_choice_num(best_yxp, choice_pro)
	print("计算当前是否为机器人: {}, 选择最佳摸牌: {}".format(data["is_robot"], choice_card))

	return int(choice_card), hu_cards

def remove_best_cards_by_remain_cards(best_yxp, all_yxp, remain_cards):
	"""
	计算非有效牌，添加至可选摸牌中采样
	"""
	tmp_remain_cards = remain_cards[:] + best_yxp[:]
	for card in tmp_remain_cards:
		if card in all_yxp:
			tmp_remain_cards.remove(card)
	return tmp_remain_cards