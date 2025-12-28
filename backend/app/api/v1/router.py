"""
API路由聚合模块
将所有v1版本的路由统一注册

路由管理规范：
1. 所有路由文件内部使用相对路径（不以/开头）
2. 所有前缀统一在router.py中管理
3. 保持清晰的API层次结构
4. Tags统一使用中文，与端点文件定义保持一致
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    annotation,
    ai_model,
    banana_generation,
    celery_queue_manager,
    generation,
    image_editing,
    image_manager,
    image_parsing,
    image_proxy,
    image_search,
    image_tags,
    image_upload,
    layout_optimization,
    tags,
    url_cache_refresh,
)

api_router = APIRouter()

# ==================== 图片管理相关路由 ====================
api_router.include_router(image_manager.router, prefix="/images", tags=["图片管理"])
api_router.include_router(image_tags.router, prefix="/images", tags=["图片标签"])
api_router.include_router(image_upload.router, prefix="/images/upload", tags=["图片上传"])
api_router.include_router(image_search.router, prefix="/images/search", tags=["图片搜索"])
# image_proxy使用完全不同的前缀，彻底避免与image_manager路由冲突
api_router.include_router(image_proxy.router, prefix="/img-access", tags=["图片代理"])

# ==================== 标签管理路由 ====================
api_router.include_router(tags.router, prefix="/tags", tags=["标签管理"])

# ==================== AI模型管理路由 ====================
api_router.include_router(ai_model.router, prefix="/ai-models", tags=["AI模型管理"])

# ==================== AI生成路由 ====================
api_router.include_router(generation.router, prefix="/generate", tags=["AI生成"])

# ==================== 布局优化路由 ====================
api_router.include_router(layout_optimization.router, prefix="/layout", tags=["布局优化"])

# ==================== 任务管理路由 ====================
# URL缓存刷新和Celery队列管理
api_router.include_router(url_cache_refresh.router, prefix="/tasks", tags=["URL缓存刷新"])
api_router.include_router(celery_queue_manager.router, prefix="/tasks", tags=["Celery队列管理"])

# ==================== 自动标注路由 ====================
api_router.include_router(annotation.router, prefix="/annotation", tags=["自动标注"])

# ==================== Banana PPT生成路由 ====================
api_router.include_router(banana_generation.router, prefix="/banana_generation", tags=["Banana生成"])

# ==================== 图片解析路由 ====================
api_router.include_router(image_parsing.router, prefix="/image_parsing", tags=["图片解析"])

# ==================== 图片编辑路由 ====================
api_router.include_router(image_editing.router, prefix="/image_editing", tags=["图片编辑"])