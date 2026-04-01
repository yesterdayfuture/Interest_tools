"""
认证路由模块
处理用户注册、登录、Token 验证等认证相关接口

主要接口：
- POST /register: 用户注册
- POST /token: 用户登录获取 Token
- GET /me: 获取当前登录用户信息
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from app.schemas import User, UserCreate, Token
from app.core.auth import (
    get_password_hash,
    create_token_for_user,
    authenticate_user,
    get_current_active_user
)
from app.services.user_service import create_user, get_user, update_user_last_login

router = APIRouter()

# OAuth2 认证方案配置
# tokenUrl 指定获取 token 的端点路径
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


@router.post("/register", response_model=User, summary="用户注册")
async def register_endpoint(user: UserCreate):
    """
    注册新用户
    
    接口说明：
    1. 接收用户名、密码和可选昵称
    2. 对密码进行哈希处理
    3. 创建用户并返回用户信息
    4. 如果用户名已存在返回 400 错误
    
    请求参数：
    - **username**: 用户名（3-50 字符，必须唯一）
    - **password**: 密码（至少 6 位）
    - **nickname**: 昵称（可选）
    
    返回：
    - 成功：User 对象（包含 id、username、nickname 等）
    - 失败：400（用户名已存在）
    """
    # 密码哈希处理
    hashed_password = get_password_hash(user.password)
    # 创建用户
    user_id = await create_user(user.username, hashed_password, user.nickname)
    if user_id == -1:
        raise HTTPException(status_code=400, detail="Username already registered")
    return await get_user(user_id)


@router.post("/token", response_model=Token, summary="用户登录")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    用户登录获取 JWT Token
    
    接口说明：
    1. 验证用户名和密码
    2. 如果验证通过，生成 JWT Token
    3. 更新用户最后登录时间
    4. 返回 Token 和类型
    
    请求参数：
    - **username**: 用户名（表单字段）
    - **password**: 密码（表单字段）
    
    返回：
    - 成功：{"access_token": "xxx", "token_type": "bearer"}
    - 失败：401（用户名或密码错误）
    """
    # 验证用户凭证
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # 生成 JWT Token
    access_token = create_token_for_user(user["id"], user["username"])
    # 更新最后登录时间
    await update_user_last_login(user["id"])
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=User, summary="获取当前用户信息")
async def read_users_me(token: str = Depends(oauth2_scheme)):
    """
    获取当前登录用户的信息
    
    接口说明：
    1. 从请求头中提取 JWT Token
    2. 验证 Token 有效性
    3. 解码 Token 获取用户信息
    4. 返回当前用户详细信息
    
    请求头：
    - Authorization: Bearer {token}
    
    返回：
    - 成功：User 对象
    - 失败：401（Token 无效或过期）
    """
    user = await get_current_active_user(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# 导出依赖函数供其他模块使用
get_current_user_dependency = get_current_active_user
