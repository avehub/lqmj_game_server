# -*- coding: utf-8 -*-


class MahjongCard:
	"""
	麻将卡牌类型
	"""
	def __init__(self, card_type, card_value):
		"""
		初始化麻将卡牌属性参数
		"""
		self.card_type = card_type
		self.card_value = card_value
		self.index_num = 0

	def set_index_num(self, index_num):
		"""
		卡牌索引
		"""
		self.index_num = index_num

	def get_card_type(self):
		"""
		卡牌类型
		"""
		return self.card_type

	def get_card_value(self):
		"""
		卡牌值
		"""
		return self.card_value