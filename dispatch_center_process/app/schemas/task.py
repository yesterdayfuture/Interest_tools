"""任务相关 Pydantic Schema."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.task import TaskStatus


class TaskBase(BaseModel):
    """任务基础 Schema."""

    name: str = Field(..., min_length=1, max_length=255, description="任务名称")
    description: Optional[str] = Field(None, max_length=1000, description="任务描述")
    task_type: str = Field(default="default", max_length=50, description="任务类型")
    priority: int = Field(default=5, ge=1, le=10, description="优先级(1-10)")
    payload: Optional[Dict[str, Any]] = Field(None, description="任务负载数据")


class TaskCreate(TaskBase):
    """任务创建 Schema."""

    pass


class TaskUpdate(BaseModel):
    """任务更新 Schema."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    priority: Optional[int] = Field(None, ge=1, le=10)
    payload: Optional[Dict[str, Any]] = None


class TaskResponse(BaseModel):
    """任务响应 Schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str]
    task_type: str
    status: TaskStatus
    priority: int
    payload: Optional[Dict[str, Any]]
    result: Optional[Dict[str, Any]]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    execution_time: Optional[float]
    retry_count: int


class TaskListRequest(BaseModel):
    """任务列表查询请求 Schema."""

    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=10, ge=1, le=100, description="每页数量")
    task_id: Optional[str] = Field(None, description="任务ID精确匹配")
    name: Optional[str] = Field(None, description="任务名称模糊查询")
    status: Optional[TaskStatus] = Field(None, description="任务状态过滤")
    task_type: Optional[str] = Field(None, description="任务类型过滤")
    priority_min: Optional[int] = Field(None, ge=1, le=10, description="最小优先级")
    priority_max: Optional[int] = Field(None, ge=1, le=10, description="最大优先级")
    created_after: Optional[datetime] = Field(None, description="创建时间之后")
    created_before: Optional[datetime] = Field(None, description="创建时间之前")

    @field_validator("priority_max")
    @classmethod
    def validate_priority_range(cls, v: Optional[int], info) -> Optional[int]:
        """验证优先级范围."""
        values = info.data
        if v is not None and values.get("priority_min") is not None:
            if v < values["priority_min"]:
                raise ValueError("priority_max must be >= priority_min")
        return v


class TaskListResponse(BaseModel):
    """任务列表响应 Schema."""

    items: List[TaskResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class TaskSubmitResponse(BaseModel):
    """任务提交响应 Schema."""

    success: bool
    message: str
    task_id: str
    data: TaskResponse


class TaskStatistics(BaseModel):
    """任务统计 Schema."""

    total_tasks: int
    pending_count: int
    running_count: int
    completed_count: int
    failed_count: int
    cancelled_count: int
    success_rate: float
    average_execution_time: Optional[float]


class TaskStatisticsResponse(BaseModel):
    """任务统计响应 Schema."""

    success: bool
    data: TaskStatistics


class APIResponse(BaseModel):
    """通用 API 响应 Schema."""

    success: bool
    message: str
    data: Optional[Any] = None


class WorkerStatusInfo(BaseModel):
    """工作进程状态信息 Schema."""

    worker_id: str
    status: str
    current_task_id: Optional[str]
    pid: Optional[int]
    is_alive: bool
    tasks_completed: int
    tasks_failed: int
    started_at: str
    last_heartbeat: str


class SchedulerStatusData(BaseModel):
    """调度器状态数据 Schema."""

    running: bool
    workers: List[WorkerStatusInfo]
    pending_tasks: int
    running_tasks: int
    completed_tasks: int
    alive_workers: int
    idle_workers: int


class SchedulerStatusResponse(BaseModel):
    """调度器状态响应 Schema."""

    success: bool
    message: str
    data: SchedulerStatusData
