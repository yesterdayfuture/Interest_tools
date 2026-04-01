"""
统计信息路由模块
处理聊天室统计信息、用户统计等接口
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from app.schemas import ChatRoomInfo, UserStatistics
from app.core.auth import get_current_active_user
from app.core.connection_manager import connection_manager
from app.services.user_service import get_user_chat_statistics

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """获取当前用户的依赖函数"""
    user = await get_current_active_user(token)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


@router.get("/chatroom", response_model=ChatRoomInfo, summary="获取聊天室统计")
async def get_chatroom_stats(current_user: dict = Depends(get_current_user)):
    """
    获取聊天室的总体统计信息
    
    返回：
    - **total_users**: 总用户数
    - **online_users**: 在线用户数
    - **total_groups**: 总群组数
    - **total_messages**: 总消息数
    """
    stats = await connection_manager.get_user_statistics()
    return ChatRoomInfo(
        total_users=stats.get("total_users", 0),
        online_users=stats.get("online_users", 0),
        total_groups=stats.get("total_groups", 0),
        total_messages=stats.get("total_messages", 0)
    )


@router.get("/user", response_model=UserStatistics, summary="获取用户统计")
async def get_user_stats(current_user: dict = Depends(get_current_user)):
    """
    获取当前用户的统计信息
    
    返回：
    - **messages_sent**: 发送消息数
    - **messages_received**: 接收消息数
    - **groups_joined**: 加入群组数
    """
    stats = await get_user_chat_statistics(current_user["id"])
    return UserStatistics(
        messages_sent=stats.get("messages_sent", 0),
        messages_received=stats.get("messages_received", 0),
        groups_joined=stats.get("groups_joined", 0)
    )
