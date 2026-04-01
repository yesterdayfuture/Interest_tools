"""
Pydantic 模型定义
用于数据验证和序列化
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ==================== 用户相关模型 ====================

class UserBase(BaseModel):
    """用户基础模型"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")


class UserCreate(UserBase):
    """用户创建模型"""
    password: str = Field(..., min_length=6, description="密码")


class UserLogin(BaseModel):
    """用户登录模型"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class User(UserBase):
    """用户完整模型"""
    id: int = Field(..., description="用户ID")
    created_at: datetime = Field(..., description="创建时间")
    last_login: Optional[datetime] = Field(None, description="最后登录时间")
    is_active: int = Field(1, description="是否激活")
    
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """用户更新模型"""
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    password: Optional[str] = Field(None, min_length=6, description="密码")


# ==================== 群组相关模型 ====================

class GroupBase(BaseModel):
    """群组基础模型"""
    name: str = Field(..., min_length=1, max_length=100, description="群组名称")
    description: Optional[str] = Field(None, max_length=500, description="群组描述")


class GroupCreate(GroupBase):
    """群组创建模型"""
    pass


class Group(GroupBase):
    """群组完整模型"""
    id: int = Field(..., description="群组ID")
    creator_id: int = Field(..., description="创建者ID")
    created_at: datetime = Field(..., description="创建时间")
    member_count: Optional[int] = Field(0, description="成员数量")
    
    class Config:
        from_attributes = True


class GroupMember(BaseModel):
    """群组成员模型"""
    id: int = Field(..., description="记录ID")
    group_id: int = Field(..., description="群组ID")
    user_id: int = Field(..., description="用户ID")
    joined_at: datetime = Field(..., description="加入时间")
    role: str = Field("member", description="角色")
    
    class Config:
        from_attributes = True


class GroupInvitationCreate(BaseModel):
    """群组邀请创建模型"""
    to_user_id: int = Field(..., description="被邀请用户ID")
    message: Optional[str] = Field(None, description="邀请消息")


class GroupInvitationResponse(BaseModel):
    """群组邀请响应模型"""
    invitation_id: int = Field(..., description="邀请ID")
    group_id: int = Field(..., description="群组ID")
    from_user_id: int = Field(..., description="邀请者ID")
    to_user_id: int = Field(..., description="被邀请者ID")
    status: str = Field(..., description="状态")
    message: Optional[str] = Field(None, description="邀请消息")
    created_at: datetime = Field(..., description="创建时间")
    responded_at: Optional[datetime] = Field(None, description="响应时间")


# ==================== 好友相关模型 ====================

class Friendship(BaseModel):
    """好友关系模型"""
    id: int = Field(..., description="记录ID")
    user_id: int = Field(..., description="用户ID")
    friend_id: int = Field(..., description="好友ID")
    created_at: datetime = Field(..., description="创建时间")
    
    class Config:
        from_attributes = True


class FriendRequestCreate(BaseModel):
    """好友申请创建模型"""
    to_user_id: int = Field(..., description="目标用户ID")
    message: Optional[str] = Field(None, description="申请消息")


class FriendRequestResponse(BaseModel):
    """好友申请响应模型"""
    request_id: int = Field(..., description="申请ID")
    from_user_id: int = Field(..., description="申请者ID")
    to_user_id: int = Field(..., description="目标用户ID")
    status: str = Field(..., description="状态")
    message: Optional[str] = Field(None, description="申请消息")
    created_at: datetime = Field(..., description="创建时间")
    responded_at: Optional[datetime] = Field(None, description="响应时间")


# ==================== 消息相关模型 ====================

class MessageBase(BaseModel):
    """消息基础模型"""
    content: str = Field(..., min_length=1, max_length=1000, description="消息内容")
    message_type: str = Field("text", description="消息类型")


class MessageCreate(MessageBase):
    """消息创建模型"""
    receiver_id: Optional[int] = Field(None, description="接收者ID")
    group_id: Optional[int] = Field(None, description="群组ID")


class Message(MessageBase):
    """消息完整模型"""
    id: int = Field(..., description="消息ID")
    sender_id: int = Field(..., description="发送者ID")
    receiver_id: Optional[int] = Field(None, description="接收者ID")
    group_id: Optional[int] = Field(None, description="群组ID")
    created_at: datetime = Field(..., description="创建时间")
    
    class Config:
        from_attributes = True


class MessageSend(BaseModel):
    """消息发送模型（WebSocket）"""
    type: str = Field(..., description="消息类型: personal/group")
    content: str = Field(..., description="消息内容")
    receiver_id: Optional[int] = Field(None, description="接收者ID（私聊）")
    group_id: Optional[int] = Field(None, description="群组ID（群聊）")


# ==================== 在线用户模型 ====================

class OnlineUser(BaseModel):
    """在线用户模型"""
    id: int = Field(..., description="记录ID")
    user_id: int = Field(..., description="用户ID")
    session_id: str = Field(..., description="会话ID")
    connected_at: datetime = Field(..., description="连接时间")
    last_activity: datetime = Field(..., description="最后活动时间")
    
    class Config:
        from_attributes = True


# ==================== 认证相关模型 ====================

class Token(BaseModel):
    """Token模型"""
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field("bearer", description="令牌类型")


class TokenData(BaseModel):
    """Token数据模型"""
    username: Optional[str] = Field(None, description="用户名")


# ==================== 请求模型 ====================

class DisconnectRequest(BaseModel):
    """断开连接请求模型"""
    session_id: str = Field(..., description="会话ID")


class KickUserRequest(BaseModel):
    """踢出用户请求模型"""
    user_id: int = Field(..., description="用户ID")
    reason: Optional[str] = Field(None, description="原因")


class RespondRequest(BaseModel):
    """响应请求模型"""
    accept: bool = Field(..., description="是否同意")


# ==================== 统计模型 ====================

class ChatRoomInfo(BaseModel):
    """聊天室统计信息模型"""
    total_users: int = Field(..., description="总用户数")
    online_users: int = Field(..., description="在线用户数")
    total_groups: int = Field(..., description="总群组数")
    total_messages: int = Field(..., description="总消息数")


class UserStatistics(BaseModel):
    """用户统计信息模型"""
    messages_sent: int = Field(..., description="发送消息数")
    messages_received: int = Field(..., description="接收消息数")
    groups_joined: int = Field(..., description="加入群组数")


# ==================== 搜索模型 ====================

class UserSearchResult(BaseModel):
    """用户搜索结果模型"""
    users: List[User] = Field(..., description="用户列表")


class GroupStats(BaseModel):
    """群组统计模型"""
    member_count: int = Field(..., description="成员数")
    message_count: int = Field(..., description="消息数")
