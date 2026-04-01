"""
用户路由模块
处理用户查询、搜索、好友关系等接口
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordBearer

from app.schemas import User, FriendRequestCreate, FriendRequestResponse, RespondRequest
from app.core.auth import get_current_active_user
from app.services.user_service import (
    get_all_users,
    get_online_users,
    get_user_friends,
    search_users_by_username,
    send_friend_request,
    respond_friend_request,
    get_friend_requests,
    get_user
)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """获取当前用户的依赖函数"""
    user = await get_current_active_user(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


@router.get("", response_model=List[User], summary="获取所有用户")
async def get_all_users_endpoint(current_user: dict = Depends(get_current_user)):
    """
    获取所有活跃用户列表
    
    返回包含所有激活状态用户的基本信息
    """
    return await get_all_users()


@router.get("/online", response_model=List[dict], summary="获取在线用户")
async def get_online_users_endpoint(current_user: dict = Depends(get_current_user)):
    """
    获取当前在线的用户列表
    
    返回在线用户的 ID、用户名、昵称和最后活动时间
    """
    return await get_online_users()


@router.get("/friends", response_model=List[dict], summary="获取好友列表")
async def get_friends_endpoint(current_user: dict = Depends(get_current_user)):
    """
    获取当前用户的好友列表
    
    返回好友的 ID、用户名和昵称
    """
    return await get_user_friends(current_user["id"])


@router.get("/search", summary="搜索用户")
async def search_users_endpoint(
    username: str,
    current_user: dict = Depends(get_current_user)
):
    """
    根据用户名搜索用户（模糊匹配）
    
    - **username**: 搜索关键词
    
    返回匹配的用户列表（不包含当前用户）
    """
    users = await search_users_by_username(username, current_user["id"])
    return {"users": users}


# ==================== 好友申请接口 ====================

@router.post("/friend-requests", response_model=FriendRequestResponse, summary="发送好友申请")
async def send_friend_request_endpoint(
    request: FriendRequestCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    向指定用户发送好友申请
    
    - **to_user_id**: 目标用户ID
    - **message**: 申请消息（可选）
    """
    # 不能向自己发送好友申请
    if request.to_user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot send friend request to yourself")
    
    # 检查目标用户是否存在
    target_user = await get_user(request.to_user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")
    
    # 检查是否已经是好友
    friends = await get_user_friends(current_user["id"])
    if any(friend["id"] == request.to_user_id for friend in friends):
        raise HTTPException(status_code=400, detail="You are already friends")
    
    success = await send_friend_request(
        current_user["id"],
        request.to_user_id,
        request.message
    )
    if not success:
        raise HTTPException(status_code=400, detail="Friend request already sent")
    
    from datetime import datetime
    return {
        "request_id": 1,
        "from_user_id": current_user["id"],
        "to_user_id": request.to_user_id,
        "status": "pending",
        "message": request.message,
        "created_at": datetime.now(),
        "responded_at": None
    }


@router.get("/friend-requests", response_model=List[dict], summary="获取好友申请列表")
async def get_friend_requests_endpoint(
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    获取收到的好友申请列表
    
    - **status**: 状态筛选（可选：pending/accepted/rejected）
    
    返回申请列表，包含申请者信息
    """
    return await get_friend_requests(current_user["id"], status)


@router.post("/friend-requests/{request_id}/respond", summary="处理好友申请")
async def respond_to_friend_request(
    request_id: int,
    respond: RespondRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    同意或拒绝好友申请
    
    - **request_id**: 申请ID
    - **accept**: true 表示同意，false 表示拒绝
    """
    success = await respond_friend_request(
        request_id,
        current_user["id"],
        respond.accept
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to respond to friend request")
    
    return {
        "message": f"Friend request {'accepted' if respond.accept else 'rejected'} successfully"
    }
