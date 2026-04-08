"""
任务数据验证 Schema
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class TaskBase(BaseModel):
    """任务基础 Schema"""
    name: str = Field(..., min_length=1, max_length=255, description="任务名称")
    description: Optional[str] = Field(None, max_length=1000, description="任务描述")
    task_type: str = Field(..., min_length=1, max_length=100, description="任务类型")
    priority: int = Field(default=5, ge=1, le=10, description="优先级(1-10)")
    payload: Optional[Dict[str, Any]] = Field(default={}, description="任务负载数据")


class TaskCreate(TaskBase):
    """创建任务 Schema"""
    pass


class TaskUpdate(BaseModel):
    """更新任务 Schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    priority: Optional[int] = Field(None, ge=1, le=10)
    payload: Optional[Dict[str, Any]] = None


class TaskResponse(TaskBase):
    """任务响应 Schema"""
    id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time: Optional[float] = None

    class Config:
        from_attributes = True


class TaskListRequest(BaseModel):
    """任务列表查询请求 Schema"""
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=10, ge=1, le=100, description="每页数量")
    task_id: Optional[str] = Field(None, description="任务ID精确匹配")
    name: Optional[str] = Field(None, description="任务名称模糊查询")
    status: Optional[str] = Field(None, description="任务状态过滤")
    task_type: Optional[str] = Field(None, description="任务类型过滤")
    priority_min: Optional[int] = Field(None, ge=1, le=10, description="最小优先级")
    priority_max: Optional[int] = Field(None, ge=1, le=10, description="最大优先级")
    created_after: Optional[datetime] = Field(None, description="创建时间起始")
    created_before: Optional[datetime] = Field(None, description="创建时间截止")


class TaskListResponse(BaseModel):
    """任务列表响应 Schema"""
    total: int
    page: int
    page_size: int
    items: list[TaskResponse]


class TaskStatistics(BaseModel):
    """任务统计 Schema"""
    total_tasks: int
    pending_count: int
    running_count: int
    completed_count: int
    failed_count: int
    cancelled_count: int
    success_rate: float
    average_execution_time: Optional[float] = None


class ApiResponse(BaseModel):
    """通用 API 响应 Schema"""
    success: bool
    message: str
    task_id: Optional[str] = None
    data: Optional[Any] = None
