"""
API 依赖注入
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db


async def get_db_session():
    """获取数据库会话依赖"""
    async for session in get_db():
        yield session


# 常用依赖类型
DBSession = Depends(get_db_session)
