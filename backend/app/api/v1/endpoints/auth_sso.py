"""
SAML SSO 认证 API 端点
处理SSO登录、登出、元数据等API
"""

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.auth.saml_auth_service import SAMLAuthService
from app.schemas.auth_sso import SSOInitRequest, SSOLogoutRequest
from app.schemas.auth import UserResponse
from app.schemas.common import StandardResponse
from app.core.middleware.auth import get_current_user
from app.core.auth.jwt_handler import jwt_handler
from app.core.exceptions.saml import SAMLValidationError, SAMLMetadataError
from app.core.log_utils import get_logger
import json

logger = get_logger(__name__)

router = APIRouter(prefix="/auth/sso", tags=["SSO认证"])


@router.post(
    "/init",
    response_model=StandardResponse,
    summary="发起SSO登录",
    description="生成SAML AuthNRequest并返回IdP登录URL"
)
async def initiate_sso(
    request: Request,
    req_body: SSOInitRequest = None,
    db: AsyncSession = Depends(get_db)
):
    """
    发起SSO登录

    Args:
        request: FastAPI Request对象
        req_body: SSO初始化请求（包含可选的return_to参数）
        db: 数据库会话

    Returns:
        JSON响应，包含IdP登录URL，前端需要使用window.location.href跳转
    """
    saml_service = SAMLAuthService(db)

    # 获取return_to参数
    return_to = None
    if req_body:
        return_to = req_body.return_to

    # 生成IdP登录URL
    idp_login_url = await saml_service.initiate_sso_login(
        request=request,
        return_to=return_to
    )

    logger.info(f"生成IdP登录URL: {idp_login_url}")

    # 返回JSON响应（不使用302重定向，避免CORS问题）
    return JSONResponse(
        content={
            "status": "success",
            "message": "SSO登录URL生成成功",
            "data": {
                "redirect_url": idp_login_url
            }
        }
    )


@router.post(
    "/acs",
    summary="处理SAML响应",
    description="接收IdP的SAML Response并完成认证"
)
@router.get(
    "/acs",
    summary="处理SAML响应（GET）",
    description="接收IdP的SAML Response并完成认证（GET方法）"
)
async def handle_acs(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    处理SAML ACS (Assertion Consumer Service) 响应

    Args:
        request: FastAPI Request对象（包含SAML Response）
        db: 数据库会话

    Returns:
        包含Token的JSON响应（前端需要处理）
    """
    # 获取客户端信息
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host

    logger.info(f"[SSO-ACS-API] 收到ACS请求 - method: {request.method}, ip: {ip_address}, user_agent: {user_agent}")
    logger.info(f"[SSO-ACS-API] 请求URL: {request.url}")
    logger.info(f"[SSO-ACS-API] 查询参数: {dict(request.query_params)}")

    # 预先读取body（避免重复读取）
    body_data = None
    relay_state = None

    # 记录POST数据（如果有的话）并获取RelayState
    if request.method == "POST":
        try:
            body_data = await request.body()
            logger.info(f"[SSO-ACS-API] POST body长度: {len(body_data)} bytes")
            # 不记录完整的SAML Response，只记录关键字段
            if b"SAMLResponse" in body_data:
                logger.info("[SSO-ACS-API] 检测到SAMLResponse字段")
            if b"RelayState" in body_data:
                logger.info("[SSO-ACS-API] 检测到RelayState字段")
                # 提取RelayState
                from urllib.parse import parse_qs
                post_data = parse_qs(body_data.decode('utf-8'))
                relay_state = post_data.get('RelayState', [None])[0]
        except Exception as e:
            logger.warning(f"[SSO-ACS-API] 读取body失败: {e}")
    else:
        # GET方法从查询参数获取RelayState
        relay_state = request.query_params.get('RelayState')

    saml_service = SAMLAuthService(db)

    try:
        # 处理SAML响应并完成认证
        result = await saml_service.process_acs_response(
            request=request,
            ip_address=ip_address,
            user_agent=user_agent
        )

        logger.info(f"[SSO-ACS-API] 构建响应 - user_id: {result['user'].id}")

        # 构建响应
        user_response = UserResponse.model_validate(result["user"])

        # 使用model_dump(mode='json')来正确序列化datetime
        sso_response = {
            "access_token": result["access_token"],
            "refresh_token": result["refresh_token"],
            "token_type": "bearer",
            "expires_at": result["expires_at"].isoformat() if result["expires_at"] else None,
            "refresh_expires_at": result["refresh_expires_at"].isoformat() if result["refresh_expires_at"] else None,
            "user": user_response.model_dump(mode='json')  # 使用json模式序列化datetime
        }

        logger.info(f"[SSO-ACS-API] 响应构建完成，准备返回")

        # 如果RelayState存在，使用它作为重定向目标
        redirect_url = relay_state if relay_state else "/"

        logger.info(f"[SSO-ACS-API] 准备重定向到: {redirect_url}")

        # 使用URL参数传递token（最可靠的方式，避免跨域localStorage问题）
        from urllib.parse import urlencode, urlparse, urlunparse

        # 将token添加到重定向URL的查询参数中
        parsed_url = urlparse(redirect_url)
        query_params = {
            'access_token': sso_response['access_token'],
            'refresh_token': sso_response['refresh_token'],
        }

        # 合并现有的查询参数（如redirect）
        from urllib.parse import parse_qs
        existing_params = parse_qs(parsed_url.query)
        for key, values in existing_params.items():
            if key not in query_params:
                query_params[key] = values[0]

        new_query = urlencode(query_params)
        final_redirect_url = urlunparse(parsed_url._replace(query=new_query))

        logger.info(f"[SSO-ACS-API] 最终重定向URL长度: {len(final_redirect_url)}")

        # 直接重定向（不使用HTML，避免localStorage跨域问题）
        return RedirectResponse(url=final_redirect_url, status_code=302)

    except SAMLValidationError as e:
        logger.error(f"SSO ACS处理失败: {str(e)}")
        return JSONResponse(
            status_code=401,
            content={
                "status": "error",
                "message": e.message,
                "data": {"details": e.details}
            }
        )
    except Exception as e:
        logger.error(f"SSO ACS处理时发生未知错误: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"SSO认证失败: {str(e)}",
                "data": None
            }
        )


@router.post(
    "/slo",
    summary="发起单点登出",
    description="生成SAML LogoutRequest并重定向到IdP"
)
async def initiate_slo(
    request: Request,
    req_body: SSOLogoutRequest = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    发起单点登出

    Args:
        request: FastAPI Request对象
        req_body: SLO请求
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        重定向到IdP登出页面
    """
    saml_service = SAMLAuthService(db)

    # 撤销本地会话
    try:
        authorization = request.headers.get("authorization")
        if authorization:
            token = authorization.replace("Bearer ", "")
            token_jti = jwt_handler.get_token_jti(token)

            from app.services.auth.auth_service import AuthService
            auth_service = AuthService(db)
            await auth_service.logout(token_jti, current_user["id"])
    except Exception as e:
        logger.warning(f"撤销本地会话失败: {str(e)}")

    # 获取用户的SAML信息
    saml_name_id = None
    saml_session_index = None
    if req_body:
        saml_name_id = req_body.saml_name_id
        saml_session_index = req_body.saml_session_index

    # 生成IdP登出URL
    idp_logout_url = await saml_service.initiate_slo(
        request=request,
        saml_name_id=saml_name_id,
        saml_session_index=saml_session_index
    )

    # 重定向到IdP
    return RedirectResponse(url=idp_logout_url, status_code=302)


@router.get(
    "/sls",
    summary="处理SLO响应",
    description="接收IdP的SLO响应并完成登出"
)
async def handle_sls(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    处理SAML SLS (Single Logout Service) 响应

    Args:
        request: FastAPI Request对象（包含SAML LogoutResponse）
        db: 数据库会话

    Returns:
        登出成功响应
    """
    saml_service = SAMLAuthService(db)

    # 定义会话删除回调
    def delete_session_callback():
        # 这里可以添加额外的会话清理逻辑
        pass

    # 处理SLO响应
    success = await saml_service.process_slo_response(
        request=request,
        delete_session_cb=delete_session_callback
    )

    if success:
        return JSONResponse(
            content={
                "status": "success",
                "message": "单点登出成功",
                "data": None
            }
        )
    else:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": "单点登出失败",
                "data": None
            }
        )


@router.get(
    "/metadata",
    response_class=JSONResponse,
    summary="获取SP元数据",
    description="生成并返回Service Provider的SAML元数据XML"
)
async def get_metadata(
    db: AsyncSession = Depends(get_db)
):
    """
    获取SP元数据

    Args:
        db: 数据库会话

    Returns:
        SP元数据XML
    """
    saml_service = SAMLAuthService(db)

    try:
        metadata_xml = saml_service.get_sp_metadata()

        # 返回XML响应
        return Response(
            content=metadata_xml,
            media_type="application/xml",
            headers={
                "Content-Disposition": 'attachment; filename="metadata.xml"'
            }
        )
    except SAMLMetadataError as e:
        logger.error(f"生成SP元数据失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": e.message,
                "data": {"details": e.details}
            }
        )
    except Exception as e:
        logger.error(f"生成SP元数据时发生未知错误: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"生成元数据失败: {str(e)}",
                "data": None
            }
        )
