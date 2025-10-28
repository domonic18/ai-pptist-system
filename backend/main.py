"""
AI PPTist - FastAPI主应用
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.router import api_router
from app.core.log_utils import setup_logging, get_logger
from app.core.mlflow_tracker import ensure_mlflow_initialized

# 初始化日志系统
setup_logging()

# 在导入其他模块之前完成日志设置
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("应用启动中...")

    # 数据库初始化现在由PostgreSQL容器自动完成
    # 通过docker-entrypoint-initdb.d目录中的SQL脚本
    logger.info("数据库初始化由PostgreSQL容器自动处理")

    # 初始化MLflow追踪
    mlflow_enabled = ensure_mlflow_initialized()
    if mlflow_enabled:
        logger.info("MLflow追踪已启用 - 将自动捕获AI调用的request/response内容")
    else:
        logger.warning("MLflow追踪未启用，AI调用将不会被追踪")

    logger.info("应用启动完成")

    yield

    # 关闭时执行
    logger.info("应用关闭")


# 创建FastAPI应用实例
app = FastAPI(
    title=settings.project_name,
    version=settings.app_version,
    description="基于AI的在线PPT编辑和生成系统",
    openapi_url=f"{settings.api_v1_str}/openapi.json",
    docs_url=f"{settings.api_v1_str}/docs",
    redoc_url=f"{settings.api_v1_str}/redoc",
    lifespan=lifespan
)

# 添加CORS中间件 - 确保在所有路由之前添加
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有头部
    expose_headers=["*"]  # 暴露所有头部
)

# 注册API路由
app.include_router(api_router, prefix=settings.api_v1_str)


@app.get("/")
def read_root():
    """根路径"""
    return {
        "message": "AI PPTist API",
        "version": settings.app_version,
        "docs": f"{settings.api_v1_str}/docs"
    }


@app.get("/health")
def health_check():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug,
        log_level=settings.log_level.lower()
    )
