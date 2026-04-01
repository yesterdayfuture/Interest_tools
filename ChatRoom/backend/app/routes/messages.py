"""
消息路由模块
处理消息历史查询、会话列表等接口
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordBearer

from app.schemas import Message
from app.core.auth import get_current_active_user
from app.services.message_service import (
    get_personal_messages,
    get_group_messages,
    get_conversation_list
)

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


@router.get("/history/personal", summary="获取私聊消息历史")
async def get_personal_messages_endpoint(
    other_user_id: int = Query(..., description="对方用户ID"),
    limit: int = Query(50, ge=1, le=100, description="消息数量限制"),
    current_user: dict = Depends(get_current_user)
):
    """
    获取与指定用户的私聊消息历史
    
    - **other_user_id**: 对方用户ID
    - **limit**: 返回消息数量（默认50，最大100）
    
    按时间倒序返回消息列表
    """
    messages = await get_personal_messages(
        current_user["id"],
        other_user_id,
        limit
    )
    return {"messages": messages}


@router.get("/history/group", summary="获取群组消息历史")
async def get_group_messages_endpoint(
    group_id: int = Query(..., description="群组ID"),
    limit: int = Query(50, ge=1, le=100, description="消息数量限制"),
    current_user: dict = Depends(get_current_user)
):
    """
    获取指定群组的消息历史
    
    - **group_id**: 群组ID
    - **limit**: 返回消息数量（默认50，最大100）
    
    按时间倒序返回消息列表
    """
    from app.services.group_service import is_group_member
    if not await is_group_member(group_id, current_user["id"]):
        raise HTTPException(status_code=403, detail="Not a member of this group")
    
    messages = await get_group_messages(group_id, limit)
    return {"messages": messages}


@router.get("/conversations", response_model=List[dict], summary="获取会话列表")
async def get_conversations_endpoint(
    current_user: dict = Depends(get_current_user)
):
    """
    获取用户的会话列表
    
    返回与用户有过消息往来的所有用户列表，按最后消息时间倒序排列
    """
    conversations = await get_conversation_list(current_user["id"])
    return conversations
