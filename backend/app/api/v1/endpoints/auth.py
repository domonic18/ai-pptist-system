"""
认证 API 端点
处理用户登录、注册、Token刷新、登出等API
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.auth.auth_service import AuthService
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenRefreshRequest,
    LoginResponse,
    RegisterResponse,
    TokenRefreshResponse,
    LogoutResponse,
    UserResponse,
    SessionsListResponse
)
from app.schemas.common import StandardResponse
from app.core.middleware.auth import get_current_user
from app.core.auth.jwt_handler import jwt_handler
from app.core.log_utils import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post(
    "/login",
    response_model=StandardResponse,
    summary="用户登录",
    description="通过邮箱和密码进行用户登录"
)
async def login(
    request: LoginRequest,
    req: Request,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    用户登录

    Args:
        request: 登录请求
        req: FastAPI Request 对象（用于获取客户端信息）
        db: 数据库会话

    Returns:
        包含访问令牌和用户信息的响应
    """
    # 获取客户端信息
    user_agent = req.headers.get("user-agent")
    ip_address = req.client.host

    # 使用认证服务处理登录
    auth_service = AuthService(db)
    result = await auth_service.authenticate_by_password(
        email=request.email,
        password=request.password,
        ip_address=ip_address,
        user_agent=user_agent
    )

    # 构建响应
    user_response = UserResponse.model_validate(result["user"])

    login_response = LoginResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        expires_at=result["expires_at"],
        refresh_expires_at=result["refresh_expires_at"],
        user=user_response
    )

    return StandardResponse(
        status="success",
        message="登录成功",
        data=login_response.model_dump()
    )


@router.post(
    "/register",
    response_model=StandardResponse,
    summary="用户注册",
    description="创建新用户账户"
)
async def register(
    request: RegisterRequest,
    req: Request,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    用户注册

    Args:
        request: 注册请求
        req: FastAPI Request 对象
        db: 数据库会话

    Returns:
        包含访问令牌和用户信息的响应
    """
    # 获取客户端信息
    user_agent = req.headers.get("user-agent")
    ip_address = req.client.host

    # 使用认证服务处理注册
    auth_service = AuthService(db)
    result = await auth_service.register_user(
        email=request.email,
        name=request.name,
        password=request.password,
        ip_address=ip_address,
        user_agent=user_agent
    )

    # 构建响应
    user_response = UserResponse.model_validate(result["user"])

    register_response = RegisterResponse(
        user=user_response,
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        expires_at=result["expires_at"],
        refresh_expires_at=result["refresh_expires_at"]
    )

    return StandardResponse(
        status="success",
        message="注册成功",
        data=register_response.model_dump()
    )


@router.post(
    "/refresh",
    response_model=StandardResponse,
    summary="刷新访问令牌",
    description="使用刷新令牌获取新的访问令牌"
)
async def refresh_token(
    request: TokenRefreshRequest,
    req: Request,
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    刷新访问令牌

    Args:
        request: Token刷新请求
        req: FastAPI Request 对象
        db: 数据库会话

    Returns:
        包含新访问令牌的响应
    """
    import time
    start_time = time.time()

    logger.info("[REFRESH-START] 开始处理Token刷新请求")

    # 获取客户端信息
    user_agent = req.headers.get("user-agent")
    ip_address = req.client.host

    logger.info(f"[REFRESH-CLIENT] 客户端信息 - IP: {ip_address}, UA: {user_agent}")
    logger.info(f"[REFRESH-TOKEN] Token长度: {len(request.refresh_token)} 字符")

    # 使用认证服务刷新token
    auth_service = AuthService(db)

    service_start = time.time()
    logger.info(f"[REFRESH-SERVICE-START] 调用 AuthService.refresh_access_token, 耗时: {service_start - start_time:.3f}s")

    result = await auth_service.refresh_access_token(
        refresh_token=request.refresh_token,
        ip_address=ip_address,
        user_agent=user_agent
    )

    service_end = time.time()
    logger.info(f"[REFRESH-SERVICE-END] AuthService 返回, 耗时: {service_end - service_start:.3f}s")

    refresh_response = TokenRefreshResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        expires_at=result["expires_at"],
        refresh_expires_at=result["refresh_expires_at"]
    )

    logger.info(f"[REFRESH-SUCCESS] Token刷新成功, 总耗时: {time.time() - start_time:.3f}s")

    return StandardResponse(
        status="success",
        message="Token刷新成功",
        data=refresh_response.model_dump()
    )


@router.post(
    "/logout",
    response_model=StandardResponse,
    summary="用户登出",
    description="登出当前用户并撤销会话"
)
async def logout(
    req: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    用户登出

    Args:
        current_user: 当前登录用户
        req: FastAPI Request 对象
        db: 数据库会话

    Returns:
        登出成功响应
    """
    # 从请求头获取token
    authorization = req.headers.get("authorization")
    if not authorization:
        return StandardResponse(
            status="success",
            message="登出成功（无会话）"
        )

    try:
        token = authorization.replace("Bearer ", "")
        token_jti = jwt_handler.get_token_jti(token)

        # 使用认证服务处理登出
        auth_service = AuthService(db)
        await auth_service.logout(token_jti, current_user["id"])

    except Exception as e:
        logger.warning(f"登出时处理token失败: {str(e)}")

    return StandardResponse(
        status="success",
        message="登出成功",
        data={"message": "登出成功"}
    )


@router.get(
    "/me",
    response_model=StandardResponse,
    summary="获取当前用户信息",
    description="获取当前登录用户的详细信息"
)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user)
) -> StandardResponse:
    """
    获取当前用户信息

    Args:
        current_user: 当前登录用户

    Returns:
        包含用户信息的响应
    """
    return StandardResponse(
        status="success",
        message="获取用户信息成功",
        data=current_user
    )


@router.get(
    "/sessions",
    response_model=StandardResponse,
    summary="获取用户所有会话",
    description="获取当前用户的所有活跃登录会话"
)
async def get_user_sessions(
    req: Request,
    skip: int = 0,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    获取用户所有会话

    Args:
        skip: 跳过的记录数
        limit: 返回的记录数限制
        current_user: 当前登录用户
        req: FastAPI Request 对象
        db: 数据库会话

    Returns:
        包含会话列表的响应
    """
    # 获取当前token的JTI
    authorization = req.headers.get("authorization")
    token_jti = None
    if authorization:
        try:
            token = authorization.replace("Bearer ", "")
            token_jti = jwt_handler.get_token_jti(token)
        except Exception:
            pass

    # 使用认证服务获取会话列表
    auth_service = AuthService(db)
    result = await auth_service.get_user_sessions(
        user_id=current_user["id"],
        current_token_jti=token_jti,
        skip=skip,
        limit=limit
    )

    return StandardResponse(
        status="success",
        message="获取会话列表成功",
        data=result
    )


@router.post(
    "/sessions/{session_id}/revoke",
    response_model=StandardResponse,
    summary="撤销指定会话",
    description="撤销用户在指定设备上的登录会话"
)
async def revoke_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    撤销指定会话

    Args:
        session_id: 会话ID
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        撤销结果响应
    """
    auth_service = AuthService(db)
    await auth_service.revoke_session(session_id, current_user["id"])

    return StandardResponse(
        status="success",
        message="会话已撤销",
        data={"session_id": session_id}
    )


@router.post(
    "/logout-all",
    response_model=StandardResponse,
    summary="登出所有设备",
    description="撤销用户在所有设备上的登录会话"
)
async def logout_all(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> StandardResponse:
    """
    登出所有设备

    Args:
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        登出结果响应
    """
    auth_service = AuthService(db)
    count = await auth_service.logout_all(current_user["id"])

    return StandardResponse(
        status="success",
        message=f"已撤销 {count} 个设备的登录会话",
        data={"revoked_count": count}
    )
