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
    image_tags, tags, layout_optimization, image_proxy
)

api_router = APIRouter()

# 注册各模块路由 - 统一前缀管理
api_router.include_router(image_manager.router, prefix="/images", tags=["图片管理"])
api_router.include_router(image_tags.router, prefix="/images", tags=["图片标签"])
api_router.include_router(image_upload.router, prefix="/images/upload", tags=["图片上传"])
api_router.include_router(image_search.router, prefix="/images/search", tags=["图片搜索"])
api_router.include_router(image_proxy.router, prefix="/images", tags=["图片代理"])
api_router.include_router(tags.router, prefix="/tags", tags=["标签管理"])
api_router.include_router(ai_model.router, prefix="/ai-models", tags=["AI Models"])
api_router.include_router(generation.router, prefix="/generate", tags=["AI Generation"])
api_router.include_router(layout_optimization.router, prefix="/layout", tags=["布局优化"])