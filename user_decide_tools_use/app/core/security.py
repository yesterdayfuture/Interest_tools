"""
安全工具模块

提供密码哈希、JWT 令牌生成和验证等安全相关功能。
"""

import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict
from jose import JWTError, jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """
    对密码进行 SHA256 哈希

    Args:
        password: 明文密码

    Returns:
        str: 64 位十六进制哈希值
    """
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码是否匹配

    Args:
        plain_password: 明文密码
        hashed_password: 存储的哈希值

    Returns:
        bool: 密码匹配返回 True
    """
    return hash_password(plain_password) == hashed_password


def create_access_token(user_id: str, username: str) -> str:
    """
    创建 JWT 访问令牌

    Args:
        user_id: 用户唯一标识符
        username: 用户名

    Returns:
        str: 编码后的 JWT token
    """
    expire = datetime.utcnow() + timedelta(days=settings.JWT_ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "sub": user_id,  # subject - 令牌主题（用户ID）
        "username": username,
        "exp": expire    # expiration - 过期时间
    }
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[Dict]:
    """
    解码并验证 JWT token

    Args:
        token: JWT 令牌字符串

    Returns:
        Dict: 解码后的 payload
        None: 令牌无效或过期时返回 None
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None
