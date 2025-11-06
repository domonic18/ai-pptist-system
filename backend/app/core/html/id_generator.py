"""
PPT元素ID生成器
生成符合前端规范的唯一元素ID，基于nanoid库
"""

from typing import Set, List
from nanoid import generate
import random


class PPTIDGenerator:
    """
    PPT元素ID生成器，完全兼容前端nanoid实现

    前端配置参考：
    - import { nanoid } from 'nanoid'
    - customAlphabet('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz')
    - nanoid(10) 用于PPT元素ID
    """

    # 与前端完全一致的字符集
    ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'

    # PPT元素ID长度（与前端一致）
    ELEMENT_ID_LENGTH = 10

    def __init__(self, existing_ids: Set[str] = None):
        """
        初始化ID生成器

        Args:
            existing_ids: 已存在的ID集合，用于避免重复
        """
        # 创建副本以避免修改原始集合
        self.existing_ids = set(existing_ids) if existing_ids else set()

    def generate_id(self, length: int = ELEMENT_ID_LENGTH) -> str:
        """
        生成符合前端规范的元素ID

        Args:
            length: ID长度，默认为10位（与前端一致）

        Returns:
            str: 唯一的元素ID

        Example:
            >>> generator = PPTIDGenerator()
            >>> element_id = generator.generate_id()
            >>> print(element_id)  # 输出: "XyZ123AbCd" (10位字符)
        """
        while True:
            # 使用与前端相同的nanoid配置生成ID
            new_id = generate(self.ALPHABET, length)

            # 确保生成的ID不在现有集合中
            if new_id not in self.existing_ids:
                self.existing_ids.add(new_id)
                return new_id

    def generate_multiple_ids(self, count: int, length: int = ELEMENT_ID_LENGTH) -> List[str]:
        """
        批量生成多个唯一ID

        Args:
            count: 需要生成的ID数量
            length: 每个ID的长度，默认为10位

        Returns:
            List[str]: 唯一ID列表

        Example:
            >>> generator = PPTIDGenerator()
            >>> ids = generator.generate_multiple_ids(3)
            >>> print(ids)  # 输出: ["XyZ123AbCd", "A1b2C3d4E5", "Z9y8X7w6V5"]
        """
        return [self.generate_id(length) for _ in range(count)]

    def add_existing_id(self, element_id: str):
        """
        添加已存在的ID到集合中

        Args:
            element_id: 已存在的元素ID
        """
        self.existing_ids.add(element_id)

    def add_existing_ids(self, element_ids: Set[str]):
        """
        批量添加已存在的ID到集合中

        Args:
            element_ids: 已存在的元素ID集合
        """
        self.existing_ids.update(element_ids)

    def is_valid_id(self, element_id: str) -> bool:
        """
        验证ID是否符合前端规范

        Args:
            element_id: 待验证的元素ID

        Returns:
            bool: 是否有效

        Example:
            >>> generator = PPTIDGenerator()
            >>> generator.is_valid_id("ABC123defg")  # True
            >>> generator.is_valid_id("abc-123")     # False (包含连字符)
            >>> generator.is_valid_id("ABC123!")     # False (包含特殊字符)
        """
        if not element_id or len(element_id) != self.ELEMENT_ID_LENGTH:
            return False

        # 检查所有字符是否都在允许的字符集中
        return all(char in self.ALPHABET for char in element_id)

    def get_stats(self) -> dict:
        """
        获取生成器统计信息

        Returns:
            dict: 统计信息
        """
        return {
            'existing_ids_count': len(self.existing_ids),
            'alphabet_length': len(self.ALPHABET),
            'id_length': self.ELEMENT_ID_LENGTH,
            'total_possible_combinations': len(self.ALPHABET) ** self.ELEMENT_ID_LENGTH
        }


# 全局实例，用于在整个应用中生成一致的ID
_global_generator = None


def get_id_generator(existing_ids: Set[str] = None) -> PPTIDGenerator:
    """
    获取全局ID生成器实例

    Args:
        existing_ids: 已存在的ID集合（仅在首次调用时使用）

    Returns:
        PPTIDGenerator: ID生成器实例
    """
    global _global_generator

    if _global_generator is None:
        _global_generator = PPTIDGenerator(existing_ids)

    return _global_generator


def generate_ppt_element_id(existing_ids: Set[str] = None) -> str:
    """
    便捷函数：生成PPT元素ID

    Args:
        existing_ids: 已存在的ID集合

    Returns:
        str: 新的唯一元素ID
    """
    generator = PPTIDGenerator(existing_ids)
    return generator.generate_id()