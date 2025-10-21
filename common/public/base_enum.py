import random
from enum import IntEnum


class BaseEnum(IntEnum):
    def __new__(cls, value, phrase, description=''):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.val = value
        obj.phrase = phrase  # 原因短语
        obj.desc = description  # 描述
        return obj

    @classmethod
    def find_member_by_val(cls, value):
        """是否包含指定值"""
        return cls._value2member_map_.get(value)

    @classmethod
    def find_member_by_phrase(cls, phrase):
        """是否包含指定值"""
        for member in cls._member_map_.values():
            if member.phrase == phrase:
                return member

    @classmethod
    def get_member_name_by_index(cls, idx=None):
        """ 根据idx获取成员str，没有传idx随机取 """
        if not idx:
            return random.choice(cls._member_names_)
        return cls._member_names_[idx]

    @classmethod
    def get_value_by_member_name(cls, name):
        enum_member = getattr(cls, name)
        return enum_member.value

    @classmethod
    def rand_choice_member(cls):
        return random.choice(list(cls._value2member_map_.values()))

    @classmethod
    def map_list(cls):
        """以value -- label map的方式返回类型映射"""
        all_list = []
        for v in cls._value2member_map_.values():
            all_list.append({'value': v.val, "phrase": v.phrase, 'desc': v.desc})
        return all_list

    @classmethod
    def all_values(cls):
        all_list = []
        for v in cls._value2member_map_.values():
            all_list.append(v.val)
        return all_list


class BaseCode(IntEnum):
    def __new__(cls, value, http, msg=''):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.val = value
        obj.http = http  # 原因短语
        obj.msg = msg  # 描述
        return obj
