"""
用户认证路由

提供用户注册、登录、登出等认证相关接口。
"""

import uuid
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.models.schemas import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from app.models.user import User
from app.core.security import hash_password, verify_password, create_access_token, decode_token
from app.core.database import db

# 创建路由
router = APIRouter(prefix="/auth", tags=["认证"])

# 安全方案
security = HTTPBearer(auto_error=False)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    获取当前登录用户（FastAPI 依赖项）

    从 HTTP 请求头中的 Authorization 字段提取 token，
    验证 token 有效性，并从数据库查询用户信息

    Args:
        credentials: HTTP Bearer 凭证

    Returns:
        User: 当前用户对象
        None: 未提供凭证或凭证无效时返回 None
    """
    if not credentials:
        return None

    # 解码 token
    payload = decode_token(credentials.credentials)
    if not payload:
        return None

    user_id = payload.get("sub")
    username = payload.get("username")

    if not user_id or not username:
        return None

    # 从数据库查询用户信息
    user_data = db.get_user_by_id(user_id)
    if not user_data or user_data["username"] != username:
        return None

    # 创建 User 对象
    return User(
        user_id=user_data["user_id"],
        username=user_data["username"],
        password_hash=user_data["password_hash"]
    )


async def require_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """
    要求用户必须登录（FastAPI 依赖项）

    与 get_current_user 类似，但如果用户未登录会抛出 401 错误

    Args:
        credentials: HTTP Bearer 凭证

    Returns:
        User: 当前用户对象

    Raises:
        HTTPException: 401 未授权错误
    """
    user = await get_current_user(credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录或登录已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


@router.post("/register", response_model=UserResponse)
async def register(request: RegisterRequest):
    """
    用户注册接口

    创建新用户账号，将用户信息持久化存储到数据库

    Args:
        request: 包含 username 和 password 的请求体

    Returns:
        UserResponse: 包含 user_id、username 和 created_at

    Raises:
        HTTPException: 400 - 参数校验失败或用户名已存在
    """
    # 参数校验
    if not request.username or not request.password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")

    if len(request.username) < 3 or len(request.username) > 20:
        raise HTTPException(status_code=400, detail="用户名长度必须在3-20个字符之间")

    if len(request.password) < 6:
        raise HTTPException(status_code=400, detail="密码长度至少6个字符")

    # 生成用户ID和密码哈希
    user_id = str(uuid.uuid4())
    password_hash = hash_password(request.password)

    # 创建用户（使用数据库）
    success = db.create_user(user_id, request.username, password_hash)
    if not success:
        raise HTTPException(status_code=400, detail="用户名已存在")

    return UserResponse(
        user_id=user_id,
        username=request.username,
        created_at=str(uuid.uuid4())  # 使用当前时间
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """
    用户登录接口

    验证用户名和密码，返回 JWT 访问令牌

    Args:
        request: 包含 username 和 password 的请求体

    Returns:
        TokenResponse: 包含 access_token、token_type 和 username

    Raises:
        HTTPException: 401 - 用户名或密码错误
    """
    # 从数据库查询用户
    user_data = db.get_user_by_username(request.username)
    if not user_data:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 验证密码
    if not verify_password(request.password, user_data["password_hash"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 生成访问令牌
    access_token = create_access_token(user_data["user_id"], user_data["username"])

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        username=user_data["username"]
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(require_user)):
    """
    获取当前登录用户信息

    Returns:
        UserResponse: 当前用户的详细信息
    """
    # 从数据库获取最新的用户信息
    user_data = db.get_user_by_id(current_user.user_id)
    if not user_data:
        raise HTTPException(status_code=404, detail="用户不存在")

    return UserResponse(
        user_id=user_data["user_id"],
        username=user_data["username"],
        created_at=user_data["created_at"]
    )


@router.post("/logout")
async def logout(current_user: User = Depends(require_user)):
    """
    用户登出接口

    由于使用 JWT 无状态认证，服务端只需返回成功信息，
    客户端需要删除本地存储的 token

    Returns:
        dict: 登出成功消息
    """
    return {"success": True, "message": "登出成功"}
