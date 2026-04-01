"""
群组路由模块
处理群组创建、管理、成员操作、邀请等接口
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordBearer

from app.schemas import (
    Group, GroupCreate, GroupInvitationCreate, 
    GroupInvitationResponse, RespondRequest
)
from app.core.auth import get_current_active_user
from app.services.group_service import (
    create_group, get_group, get_user_groups, get_group_members,
    add_member_to_group, remove_member_from_group, is_group_member,
    is_group_creator, delete_group, send_group_invitation,
    respond_group_invitation, get_group_invitations
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


@router.post("", response_model=Group, summary="创建群组")
async def create_group_endpoint(
    group: GroupCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    创建新群组
    
    - **name**: 群组名称
    - **description**: 群组描述（可选）
    
    创建者自动成为群组成员，角色为 creator
    """
    group_id = await create_group(group.name, current_user["id"], group.description)
    return await get_group(group_id)


@router.get("", response_model=List[Group], summary="获取用户群组")
async def get_user_groups_endpoint(current_user: dict = Depends(get_current_user)):
    """
    获取当前用户所属的所有群组
    
    返回群组列表，包含成员数量
    """
    return await get_user_groups(current_user["id"])


@router.get("/{group_id}", response_model=Group, summary="获取群组详情")
async def get_group_endpoint(
    group_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    获取指定群组的详细信息
    
    - **group_id**: 群组ID
    
    需要是群组成员才能查看
    """
    if not await is_group_member(group_id, current_user["id"]):
        raise HTTPException(status_code=403, detail="Not a member of this group")
    return await get_group(group_id)


@router.get("/{group_id}/members", response_model=List[dict], summary="获取群组成员")
async def get_group_members_endpoint(
    group_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    获取群组成员列表
    
    - **group_id**: 群组ID
    
    需要是群组成员才能查看
    """
    if not await is_group_member(group_id, current_user["id"]):
        raise HTTPException(status_code=403, detail="Not a member of this group")
    return await get_group_members(group_id)


@router.post("/{group_id}/members", summary="添加群组成员")
async def add_group_member(
    group_id: int,
    user_id: int = Body(..., embed=True, description="用户ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    添加用户到群组
    
    - **group_id**: 群组ID
    - **user_id**: 要添加的用户ID
    
    需要是群组成员才能添加
    """
    if not await is_group_member(group_id, current_user["id"]):
        raise HTTPException(status_code=403, detail="Not a member of this group")
    
    success = await add_member_to_group(group_id, user_id, current_user["id"])
    if not success:
        raise HTTPException(status_code=400, detail="User already in group or user not found")
    return {"message": "Member added successfully"}


@router.delete("/{group_id}/members/{user_id}", summary="移除群组成员")
async def remove_group_member(
    group_id: int,
    user_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    从群组中移除成员
    
    - **group_id**: 群组ID
    - **user_id**: 要移除的用户ID
    
    需要是群组成员才能移除
    """
    if not await is_group_member(group_id, current_user["id"]):
        raise HTTPException(status_code=403, detail="Not a member of this group")
    
    success = await remove_member_from_group(group_id, user_id, current_user["id"])
    if not success:
        raise HTTPException(status_code=400, detail="Failed to remove member")
    return {"message": "Member removed successfully"}


@router.delete("/{group_id}", summary="解散群组")
async def delete_group_endpoint(
    group_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    解散群组
    
    - **group_id**: 群组ID
    
    只有群组创建者才能解散群组
    """
    success = await delete_group(group_id, current_user["id"])
    if not success:
        raise HTTPException(status_code=403, detail="Failed to delete group or you are not the creator")
    return {"message": "Group deleted successfully"}


# ==================== 群组邀请接口 ====================

@router.post("/{group_id}/invitations", response_model=dict, summary="发送群组邀请")
async def send_group_invitation_endpoint(
    group_id: int,
    invitation: GroupInvitationCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    向用户发送群组邀请
    
    接口说明：
    1. 只有群组成员才能发送邀请
    2. 同一用户对同一群组的未处理邀请只能有一个
    3. 邀请创建后状态为 'pending'
    
    请求参数：
    - **group_id**: 群组 ID（路径参数）
    - **to_user_id**: 被邀请用户 ID
    - **message**: 邀请消息（可选）
    
    返回：
    - 成功：{"message": "Group invitation sent successfully"}
    - 失败：403（不是群组成员）或 400（发送失败）
    """
    # 验证发送者是否为群组成员
    if not await is_group_member(group_id, current_user["id"]):
        raise HTTPException(status_code=403, detail="Not a member of this group")
    
    # 检查被邀请者是否已是群成员
    if await is_group_member(group_id, invitation.to_user_id):
        raise HTTPException(status_code=400, detail="User is already a group member")
    
    # 发送邀请
    success = await send_group_invitation(
        group_id,
        current_user["id"],
        invitation.to_user_id,
        invitation.message
    )
    if not success:
        raise HTTPException(
            status_code=400, 
            detail="User already has a pending invitation for this group"
        )
    return {"message": "Group invitation sent successfully"}


@router.get("/invitations/list", response_model=List[dict], summary="获取群组邀请列表")
async def get_group_invitations_endpoint(
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    获取收到的群组邀请列表
    
    接口说明：
    1. 返回当前用户收到的所有群组邀请
    2. 可选按状态筛选（pending/accepted/rejected）
    3. 返回信息包括群组详情和邀请者信息
    
    请求参数：
    - **status**: 状态筛选（可选）
      - 'pending': 待处理
      - 'accepted': 已接受
      - 'rejected': 已拒绝
      - None: 所有状态
    
    返回：
    - 邀请列表，包含群组信息和邀请者信息
    """
    return await get_group_invitations(current_user["id"], status)


@router.post("/invitations/{invitation_id}/respond", response_model=dict, summary="处理群组邀请")
async def respond_to_group_invitation_endpoint(
    invitation_id: int,
    respond: RespondRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    同意或拒绝群组邀请
    
    接口说明：
    1. 只有被邀请人可以响应邀请
    2. 每个邀请只能响应一次
    3. 接受邀请后会自动加入群组
    
    请求参数：
    - **invitation_id**: 邀请 ID（路径参数）
    - **accept**: true 表示同意，false 表示拒绝
    
    返回：
    - 成功：{"message": "Group invitation accepted/rejected successfully"}
    - 失败：400（响应失败，可能邀请不存在或已处理）
    """
    success = await respond_group_invitation(
        invitation_id,
        current_user["id"],
        respond.accept
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to respond to group invitation")
    return {
        "message": f"Group invitation {'accepted' if respond.accept else 'rejected'} successfully"
    }
