"""
文本预处理器 - 处理MetaInsight搜索文本的优化
实现60字符限制的文本预处理和关键词提取
"""

import re
from typing import List, Optional
import jieba
import jieba.analyse
from app.core.log_utils import get_logger

logger = get_logger(__name__)


class TextPreprocessor:
    """文本预处理器 - 优化MetaInsight搜索文本"""

    # MetaInsight API文本长度限制
    MAX_TEXT_LENGTH = 60

    def __init__(self):
        # 初始化jieba分词
        try:
            # 加载自定义词典（如果有）
            jieba.initialize()
        except Exception:
            # 如果初始化失败，使用默认配置
            pass

    def preprocess_search_text(self, text: str, strategy: str = "smart_truncate") -> str:
        """
        预处理搜索文本，确保符合MetaInsight API限制

        Args:
            text: 原始搜索文本
            strategy: 预处理策略
                - "smart_truncate": 智能截断（默认）
                - "keywords_extract": 关键词提取
                - "simple_truncate": 简单截断

        Returns:
            处理后的文本，长度不超过MAX_TEXT_LENGTH
        """
        if not text or len(text.strip()) == 0:
            return ""

        # 清理文本
        cleaned_text = self._clean_text(text)

        # 检查是否需要处理
        if len(cleaned_text) <= self.MAX_TEXT_LENGTH:
            return cleaned_text

        logger.info(
            "文本长度超过限制，进行预处理",
            extra={
                "original_length": len(text),
                "cleaned_length": len(cleaned_text),
                "max_allowed": self.MAX_TEXT_LENGTH,
                "strategy": strategy
            }
        )

        # 根据策略选择处理方法
        if strategy == "keywords_extract":
            return self._extract_keywords(cleaned_text)
        elif strategy == "simple_truncate":
            return self._simple_truncate(cleaned_text)
        else:  # smart_truncate
            return self._smart_truncate(cleaned_text)

    def _clean_text(self, text: str) -> str:
        """清理文本：去除多余空格、特殊字符等"""
        if not text:
            return ""

        # 去除首尾空格
        cleaned = text.strip()

        # 替换多个连续空格为单个空格
        cleaned = re.sub(r'\s+', ' ', cleaned)

        # 移除特殊字符（保留中英文、数字、基本标点）
        cleaned = re.sub(r'[^\w\s\u4e00-\u9fff\u3000-\u303f\uff00-\uffef.,!?;:\-\u2013\u2014]', '', cleaned)

        return cleaned

    def _smart_truncate(self, text: str) -> str:
        """智能截断：在完整单词或中文词语处截断"""
        if len(text) <= self.MAX_TEXT_LENGTH:
            return text

        # 尝试在句子边界处截断
        sentence_endings = ['.', '!', '?', '。', '！', '？']
        for ending in sentence_endings:
            if ending in text:
                # 找到最后一个句子结束符
                last_ending_pos = text.rfind(ending)
                if last_ending_pos > 0 and last_ending_pos <= self.MAX_TEXT_LENGTH:
                    truncated = text[:last_ending_pos + 1]
                    if len(truncated) <= self.MAX_TEXT_LENGTH:
                        return truncated

        # 尝试在逗号或分号处截断
        comma_positions = [',', ';', '，', '；']
        for comma in comma_positions:
            if comma in text:
                # 找到最后一个逗号位置
                last_comma_pos = text.rfind(comma)
                if last_comma_pos > 0 and last_comma_pos <= self.MAX_TEXT_LENGTH:
                    truncated = text[:last_comma_pos + 1]
                    if len(truncated) <= self.MAX_TEXT_LENGTH:
                        return truncated

        # 在空格处截断
        if ' ' in text:
            # 找到最后一个空格位置
            last_space_pos = text.rfind(' ', 0, self.MAX_TEXT_LENGTH)
            if last_space_pos > 0:
                truncated = text[:last_space_pos]
                if len(truncated) <= self.MAX_TEXT_LENGTH:
                    return truncated

        # 如果以上都不行，直接截断
        return text[:self.MAX_TEXT_LENGTH]

    def _simple_truncate(self, text: str) -> str:
        """简单截断：直接截取前N个字符"""
        return text[:self.MAX_TEXT_LENGTH]

    def _extract_keywords(self, text: str) -> str:
        """提取关键词：使用TF-IDF提取最重要的关键词"""
        try:
            # 使用jieba提取关键词
            keywords = jieba.analyse.extract_tags(
                text,
                topK=10,  # 最多提取10个关键词
                withWeight=False,
                allowPOS=('n', 'ns', 'nr', 'nt', 'nz', 'v', 'a', 'eng')  # 名词、动词、形容词、英文
            )

            if not keywords:
                return self._smart_truncate(text)

            # 构建关键词字符串
            keyword_text = ' '.join(keywords)

            # 如果关键词文本仍然太长，进行截断
            if len(keyword_text) > self.MAX_TEXT_LENGTH:
                keyword_text = self._smart_truncate(keyword_text)

            logger.info(
                "关键词提取完成",
                extra={
                    "original_text": text[:100],
                    "extracted_keywords": keywords,
                    "final_text": keyword_text,
                    "final_length": len(keyword_text)
                }
            )

            return keyword_text

        except Exception as e:
            logger.warning(
                "关键词提取失败，使用智能截断",
                extra={
                    "error": str(e),
                    "text": text[:100]
                }
            )
            return self._smart_truncate(text)

    def get_text_statistics(self, text: str) -> dict:
        """获取文本统计信息"""
        cleaned = self._clean_text(text)

        return {
            "original_length": len(text),
            "cleaned_length": len(cleaned),
            "needs_processing": len(cleaned) > self.MAX_TEXT_LENGTH,
            "max_allowed": self.MAX_TEXT_LENGTH,
            "can_be_processed": len(cleaned) > 0
        }


# 全局预处理器实例
preprocessor = TextPreprocessor()