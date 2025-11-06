"""
PPT元素ID生成器单元测试
测试ID生成器的各种功能和边界情况
"""

import pytest
from app.core.html.id_generator import PPTIDGenerator, generate_ppt_element_id


@pytest.mark.unit
@pytest.mark.id_generator
class TestPPTIDGenerator:
    """PPT元素ID生成器测试类"""

    def test_generate_single_id(self):
        """测试生成单个ID"""
        generator = PPTIDGenerator()
        element_id = generator.generate_id()

        # 验证ID长度和格式
        assert len(element_id) == 10, f"ID长度应为10，实际为{len(element_id)}"
        assert element_id.isalnum(), "ID应只包含字母和数字"
        assert not '_' in element_id, "ID不应包含下划线"
        assert not '-' in element_id, "ID不应包含连字符"

    def test_generate_multiple_ids(self):
        """测试批量生成ID"""
        generator = PPTIDGenerator()
        ids = generator.generate_multiple_ids(100)

        # 验证数量
        assert len(ids) == 100, f"应生成100个ID，实际生成了{len(ids)}个"

        # 验证唯一性
        assert len(ids) == len(set(ids)), "所有ID应该是唯一的"

        # 验证格式
        for element_id in ids:
            assert len(element_id) == 10, f"ID {element_id} 长度应为10"
            assert element_id.isalnum(), f"ID {element_id} 应只包含字母和数字"

    def test_id_uniqueness_with_existing_ids(self):
        """测试与现有ID的唯一性"""
        # 使用简单的有效ID来避免特殊冲突
        existing_ids = {"1111111111", "2222222222", "3333333333"}
        generator = PPTIDGenerator(existing_ids)

        # 生成新ID不应与现有ID重复
        new_id = generator.generate_id()
        assert new_id not in existing_ids, f"新ID {new_id} 不应与现有ID重复"

        # 批量生成也不应重复
        new_ids = generator.generate_multiple_ids(10)
        for new_id in new_ids:
            assert new_id not in existing_ids, f"新ID {new_id} 不应与现有ID重复"

        # 验证批量生成的ID之间也不重复
        assert len(new_ids) == len(set(new_ids)), "批量生成的ID之间不应重复"

    def test_add_existing_ids(self):
        """测试添加现有ID"""
        generator = PPTIDGenerator()

        # 初始状态
        assert len(generator.existing_ids) == 0

        # 添加单个ID
        generator.add_existing_id("Test123ID45")
        assert "Test123ID45" in generator.existing_ids

        # 批量添加ID
        more_ids = {"ABC123defg", "XYZ987abcde"}
        generator.add_existing_ids(more_ids)
        assert len(generator.existing_ids) == 3

    def test_is_valid_id_positive_cases(self):
        """测试有效ID验证（正面案例）"""
        generator = PPTIDGenerator()

        # 有效的ID示例
        valid_ids = [
            "ABC123defg",
            "XyZ987abCd",
            "A1b2C3d4E5",
            "1234567890",
            "abcdefghij",
            "ABCDEFGHIJ",
            "aB1cD2eF3g"
        ]

        for element_id in valid_ids:
            assert generator.is_valid_id(element_id), f"ID {element_id} 应该是有效的"

    def test_is_valid_id_negative_cases(self):
        """测试无效ID验证（负面案例）"""
        generator = PPTIDGenerator()

        # 无效的ID示例
        invalid_ids = [
            "custom-bg-1",     # 包含连字符
            "arrow_2",         # 包含下划线
            "invalid-id!",     # 包含特殊字符
            "short",           # 长度不足
            "way_too_long_for_this_id",  # 长度过长
            "",                # 空字符串
            None,              # None值
            "ABC@123#def",     # 特殊字符
            "123 456 789",     # 空格
            "12.34.56.78"      # 点号
        ]

        for element_id in invalid_ids:
            assert not generator.is_valid_id(element_id), f"ID {element_id} 应该是无效的"

    def test_generate_custom_length_id(self):
        """测试生成自定义长度的ID"""
        generator = PPTIDGenerator()

        # 测试不同长度
        for length in [1, 5, 10, 15, 20]:
            element_id = generator.generate_id(length)
            assert len(element_id) == length, f"ID长度应为{length}，实际为{len(element_id)}"
            assert element_id.isalnum(), f"ID {element_id} 应只包含字母和数字"

    def test_get_stats(self):
        """测试获取统计信息"""
        existing_ids = {"ABC123defg", "XYZ987abcde", "Test123ID45"}
        generator = PPTIDGenerator(existing_ids)

        stats = generator.get_stats()

        assert stats['existing_ids_count'] == 3
        assert stats['alphabet_length'] == len(PPTIDGenerator.ALPHABET)
        assert stats['id_length'] == PPTIDGenerator.ELEMENT_ID_LENGTH
        assert stats['total_possible_combinations'] == len(PPTIDGenerator.ALPHABET) ** PPTIDGenerator.ELEMENT_ID_LENGTH

    def test_alphabet_composition(self):
        """测试字母表组成"""
        expected_chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
        assert PPTIDGenerator.ALPHABET == expected_chars, "字母表应包含预期的字符"
        assert len(PPTIDGenerator.ALPHABET) == 62, "字母表应包含62个字符"

    def test_convenience_function(self):
        """测试便捷函数"""
        # 测试不带参数的便捷函数
        element_id1 = generate_ppt_element_id()
        assert len(element_id1) == 10
        assert element_id1.isalnum()

        # 测试带现有ID的便捷函数
        existing_ids = {"ABC123defg"}
        element_id2 = generate_ppt_element_id(existing_ids)
        assert element_id2 != "ABC123defg"
        assert len(element_id2) == 10
        assert element_id2.isalnum()

    def test_large_scale_uniqueness(self):
        """测试大规模ID生成的唯一性"""
        generator = PPTIDGenerator()
        large_id_set = generator.generate_multiple_ids(1000)

        # 验证唯一性
        assert len(large_id_set) == len(set(large_id_set)), "1000个ID应该全部唯一"

        # 验证格式
        for element_id in large_id_set:
            assert generator.is_valid_id(element_id), f"ID {element_id} 格式应有效"

    def test_id_character_distribution(self):
        """测试ID字符分布合理性"""
        generator = PPTIDGenerator()
        ids = generator.generate_multiple_ids(100)

        # 收集所有字符
        all_chars = ''.join(ids)
        char_count = len(all_chars)

        # 验证字符分布（至少应该包含数字、大写字母、小写字母）
        has_digits = any(c.isdigit() for c in all_chars)
        has_upper = any(c.isupper() for c in all_chars)
        has_lower = any(c.islower() for c in all_chars)

        assert has_digits, "生成的ID应包含数字"
        assert has_upper, "生成的ID应包含大写字母"
        assert has_lower, "生成的ID应包含小写字母"

    def test_edge_case_single_character_alphabet(self):
        """测试边缘情况：单字符字母表"""
        # 创建一个只有两个字符的字母表用于测试
        class MiniIDGenerator(PPTIDGenerator):
            ALPHABET = 'AB'

        generator = MiniIDGenerator()
        ids = generator.generate_multiple_ids(4, length=2)

        # 验证所有可能的组合都被生成
        possible_combinations = {'AA', 'AB', 'BA', 'BB'}
        generated_set = set(ids)

        assert len(generated_set) == 4, "应该生成所有4种可能的组合"
        assert generated_set == possible_combinations, "生成的组合应该是所有可能的组合"