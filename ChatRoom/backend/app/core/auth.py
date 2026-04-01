"""
认证相关功能
包括密码哈希、JWT Token 生成和验证
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
import os

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 配置
SECRET_KEY = os.environ.get("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码
    
    Args:
        plain_password: 明文密码
        hashed_password: 哈希密码
        
    Returns:
        bool: 验证结果
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    获取密码哈希
    
    Args:
        password: 明文密码
        
    Returns:
        str: 哈希后的密码
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建访问令牌
    
    Args:
        data: 要编码的数据
        expires_delta: 过期时间增量
        
    Returns:
        str: JWT Token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """
    解码 Token
    
    Args:
        token: JWT Token
        
    Returns:
        Optional[dict]: 解码后的数据或 None
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def create_token_for_user(user_id: int, username: str) -> str:
    """
    为用户创建 Token
    
    Args:
        user_id: 用户ID
        username: 用户名
        
    Returns:
        str: JWT Token
    """
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": username, "user_id": user_id, "exp": expire}
    return create_access_token(to_encode)


# 这些函数需要在导入 user_service 后定义
# 避免循环导入

async def authenticate_user(username: str, password: str) -> Optional[dict]:
    """
    验证用户
    
    Args:
        username: 用户名
        password: 密码
        
    Returns:
        Optional[dict]: 用户信息或 None
    """
    from app.services.user_service import get_user_by_username
    user = await get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user["password"]):
        return None
    return user


async def get_current_user(token: str) -> Optional[dict]:
    """
    获取当前用户
    
    Args:
        token: JWT Token
        
    Returns:
        Optional[dict]: 用户信息或 None
    """
    from app.services.user_service import get_user_by_username
    payload = decode_token(token)
    if payload is None:
        return None
    username: str = payload.get("sub")
    if username is None:
        return None
    user = await get_user_by_username(username)
    return user


async def get_current_active_user(token: str) -> Optional[dict]:
    """
    获取当前活跃用户
    
    Args:
        token: JWT Token
        
    Returns:
        Optional[dict]: 用户信息或 None
    """
    user = await get_current_user(token)
    if user is None:
        return None
    if user.get("is_active", 1) == 0:
        return None
    return user
