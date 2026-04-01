"""
路由模块
集中管理所有 API 路由
"""
from fastapi import APIRouter

from app.routes import auth, users, groups, messages, stats, websocket

# 创建主路由
api_router = APIRouter()

# 注册各模块路由（不添加额外前缀，前缀在 main.py 中统一添加）
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(users.router, prefix="/users", tags=["用户"])
api_router.include_router(groups.router, prefix="/groups", tags=["群组"])
api_router.include_router(messages.router, prefix="/messages", tags=["消息"])
api_router.include_router(stats.router, prefix="/stats", tags=["统计"])

# WebSocket 路由单独注册（不需要前缀）
# 在主应用中直接注册 websocket 路由
