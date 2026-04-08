"""
Pydantic 模型定义

定义请求和响应的数据模型。
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any


# ========== 认证相关模型 ==========

class RegisterRequest(BaseModel):
    """用户注册请求"""
    username: str
    password: str


class LoginRequest(BaseModel):
    """用户登录请求"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """登录成功响应"""
    access_token: str
    token_type: str
    username: str


class UserResponse(BaseModel):
    """用户信息响应"""
    user_id: str
    username: str
    created_at: str


# ========== 任务相关模型 ==========

class StartTaskRequest(BaseModel):
    """启动任务请求"""
    user_message: str


class TaskResponse(BaseModel):
    """任务创建响应"""
    task_id: str
    status: str
    message: str


class ConfirmInteractionRequest(BaseModel):
    """确认交互请求"""
    interaction_id: str
    approved: bool
    user_input: Optional[str] = None


class ConfirmInteractionResponse(BaseModel):
    """确认交互响应"""
    success: bool
    message: str


class PendingInteractionResponse(BaseModel):
    """待确认交互查询响应"""
    has_pending: bool
    interaction_id: Optional[str] = None
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    prompt: Optional[str] = None
    task_id: Optional[str] = None
