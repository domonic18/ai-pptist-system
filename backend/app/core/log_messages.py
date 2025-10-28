"""
日志消息模板模块
统一管理所有业务日志消息模板，便于维护和国际化
"""

from typing import Dict, Any


class LogMessages:
    """日志消息模板类"""

    # ==================== 通用日志消息 ====================
    START_OPERATION = "开始执行操作: {operation_name}"
    OPERATION_SUCCESS = "操作成功完成: {operation_name}"
    OPERATION_FAILED = "操作执行失败: {operation_name}"

    # ==================== 图片管理相关 ====================
    IMAGE_LIST_START = "开始获取图片列表"
    IMAGE_LIST_SUCCESS = "成功获取图片列表"
    IMAGE_LIST_FAILED = "获取图片列表失败"

    IMAGE_DETAIL_START = "开始获取图片详情"
    IMAGE_DETAIL_SUCCESS = "成功获取图片详情"
    IMAGE_DETAIL_FAILED = "获取图片详情失败"
    IMAGE_NOT_FOUND = "图片不存在"

    IMAGE_UPDATE_START = "开始更新图片信息"
    IMAGE_UPDATE_SUCCESS = "图片更新成功"
    IMAGE_UPDATE_FAILED = "更新图片失败"

    IMAGE_DELETE_START = "开始删除图片"
    IMAGE_DELETE_SUCCESS = "图片删除成功"
    IMAGE_DELETE_FAILED = "删除图片失败"

    # ==================== 文件上传相关 ====================
    FILE_UPLOAD_START = "开始文件上传"
    FILE_UPLOAD_SUCCESS = "文件上传成功"
    FILE_UPLOAD_FAILED = "文件上传失败"
    FILE_VALIDATION_FAILED = "文件验证失败"

    # ==================== 数据库操作相关 ====================
    DB_QUERY_START = "开始数据库查询"
    DB_QUERY_SUCCESS = "数据库查询成功"
    DB_QUERY_FAILED = "数据库查询失败"
    DB_UPDATE_START = "开始数据库更新"
    DB_UPDATE_SUCCESS = "数据库更新成功"
    DB_UPDATE_FAILED = "数据库更新失败"

    # ==================== 业务验证相关 ====================
    VALIDATION_PASSED = "验证通过"
    VALIDATION_FAILED = "验证失败"

    @classmethod
    def format_message(cls, message_template: str, **kwargs: Any) -> str:
        """格式化日志消息模板"""
        return message_template.format(**kwargs)

    @classmethod
    def get_structured_data(cls, **kwargs: Any) -> Dict[str, Any]:
        """获取结构化日志数据"""
        return kwargs


# 全局实例
log_messages = LogMessages()