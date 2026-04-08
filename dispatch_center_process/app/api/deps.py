"""API 依赖注入模块."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.multi_process_scheduler import (
    MultiProcessScheduler,
    multi_process_scheduler,
)
from app.services.task_scheduler import TaskScheduler, task_scheduler
from app.services.task_service import TaskService


# 数据库会话依赖
DBSession = Annotated[AsyncSession, Depends(get_db)]


async def get_task_service() -> TaskService:
    """获取任务服务实例."""
    return TaskService()


# 任务服务依赖
TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]


async def get_task_scheduler() -> TaskScheduler:
    """获取任务调度器实例（向后兼容）."""
    return task_scheduler


# 任务调度器依赖
TaskSchedulerDep = Annotated[TaskScheduler, Depends(get_task_scheduler)]


async def get_multi_process_scheduler() -> MultiProcessScheduler:
    """获取多进程调度器实例."""
    return multi_process_scheduler


# 多进程调度器依赖
MultiProcessSchedulerDep = Annotated[
    MultiProcessScheduler, Depends(get_multi_process_scheduler)
]
