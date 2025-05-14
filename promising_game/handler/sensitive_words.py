"""
敏感词
"""
import asyncio

import ahocorasick_rs
import aiofiles

from common.utils.meta_class import SingleTon


class SensitiveWords(metaclass=SingleTon):
    _ac = None  # Aho-Corasick自动机实例
    _sensitive_words = None  # 默认敏感词列表

    @classmethod
    def init_ac(cls, sensitive_words=None, sw_file=None):
        """
        设置敏感词列表并重新初始化Aho-Corasick自动机
        :param sensitive_words: 新的敏感词列表
        :param sw_file: 敏感词文件
        """
        if cls._ac:
            return
        if sensitive_words:
            cls._sensitive_words = sensitive_words
        if sw_file:
            cls.load_keywords(sw_file)
        cls._ac = ahocorasick_rs.AhoCorasick(cls._sensitive_words)

    @classmethod
    def load_keywords(cls, file_path):
        """读取敏感词文件并返回列表"""
        with open(file_path, 'r', encoding="utf-8") as fo:
            cls._sensitive_words = [line.strip() for line in fo if line.strip()]  # 过滤空行

    @classmethod
    def filter(cls, content):
        """
        过滤给定文本中的敏感词
        :param content: 需要过滤的文本
        :return: 过滤后的文本
        """
        if not content:
            return content

        # 查找所有敏感词的位置
        content = content.strip()
        matches = list(cls._ac.find_matches_as_indexes(content, overlapping=False))

        # 将匹配到的敏感词替换为相同长度的星号
        result_content = list(content)
        for _, start, end in reversed(matches):  # 反向遍历以避免索引问题
            result_content[start:end] = '*' * (end - start)

        return ''.join(result_content)

    @classmethod
    def contain_sensitive_words(cls, content) -> str:
        """
        内容是否包含敏感词
        overlapping=True：允许「一个字符被多个敏感词同时使用」，适合需要全面检测的场景；
        overlapping=False：避免重复占用字符，适合高效替换或去重场景。
        """
        if not content:
            return ''
        content = content.strip()
        return cls._ac.find_matches_as_strings(content)


def main():
    sw = SensitiveWords()

    sw.init_ac(sw_file='../const/sensitive_words.txt')

    res1 = sw.filter("   习近平")
    res2 = sw.contain_sensitive_words("色情")

    print(res1)
    print(res2)


if __name__ == '__main__':
    main()
