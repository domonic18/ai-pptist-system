"""
API路由聚合模块
将所有v1版本的路由统一注册

路由管理规范：
1. 所有路由文件内部使用相对路径（不以/开头）
2. 所有前缀统一在router.py中管理
3. 保持清晰的API层次结构
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    image_manager, image_upload, image_search, ai_model, generation,
    image_tags, tags, layout_optimization, image_proxy, tasks, annotation,
    banana_generation, image_parsing, image_editing
)

api_router = APIRouter()

# 注册各模块路由 - 统一前缀管理
api_router.include_router(image_manager.router, prefix="/images", tags=["图片管理"])
api_router.include_router(image_tags.router, prefix="/images", tags=["图片标签"])
api_router.include_router(image_upload.router, prefix="/images/upload", tags=["图片上传"])
api_router.include_router(image_search.router, prefix="/images/search", tags=["图片搜索"])
# image_proxy使用完全不同的前缀，彻底避免与image_manager路由冲突
# 避免使用/images前缀下的任何路径
api_router.include_router(image_proxy.router, prefix="/img-access", tags=["图片代理"])
api_router.include_router(tags.router, prefix="/tags", tags=["标签管理"])
api_router.include_router(ai_model.router, prefix="/ai-models", tags=["AI Models"])
api_router.include_router(generation.router, prefix="/generate", tags=["AI Generation"])
api_router.include_router(layout_optimization.router, prefix="/layout", tags=["布局优化"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["任务管理"])
api_router.include_router(annotation.router, prefix="/annotation", tags=["自动标注"])
# Banana PPT生成路由
api_router.include_router(banana_generation.router, prefix="/banana_generation", tags=["Banana PPT生成"])
# 图片解析路由
api_router.include_router(image_parsing.router, prefix="/image_parsing", tags=["图片解析"])
# 图片编辑路由（混合OCR + 文字去除）
api_router.include_router(image_editing.router, prefix="/image_editing", tags=["图片编辑"])