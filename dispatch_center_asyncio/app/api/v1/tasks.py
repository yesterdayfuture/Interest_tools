"""
任务管理 API 路由模块

该模块实现了任务相关的所有 RESTful API 接口，包括：
- 任务提交和创建
- 任务列表查询（支持分页和过滤）
- 任务详情获取
- 任务信息更新
- 任务删除
- 任务取消
- 任务统计

所有接口都使用统一响应格式，包含 code、message、data 等字段。

统一响应格式示例：
成功响应:
{
    "code": 200,
    "message": "success",
    "data": { ... },
    "timestamp": 1234567890
}

错误响应:
{
    "code": 404,
    "message": "Task not found",
    "data": null,
    "error_detail": { ... },
    "timestamp": 1234567890
}

路由前缀: /api/v1/tasks
"""

from fastapi import APIRouter, Query, status
from typing import Optional, Dict, Any
from datetime import datetime

from app.schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskStatus,
    TaskStatistics,
)
from app.api.deps import TaskServiceDep
from app.services.task_scheduler import task_scheduler
from app.core.exceptions import TaskSubmissionException
from app.core.logging import get_logger
from app.core.response import (
    success_response,
    created_response,
    no_content_response,
    paginated_response,
    error_response,
    ResponseCode,
    ResponseMessage,
)

# 创建路由实例
router = APIRouter()

# 获取模块级日志器
logger = get_logger(__name__)


@router.post(
    "/submit",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="提交新任务",
    description="创建一个新任务并提交到调度队列，任务会立即进入 PENDING 状态等待执行。"
)
async def submit_task(task_data: TaskCreate):
    """
    提交新任务
    
    接收任务信息，创建任务记录并启动异步执行流程。
    任务提交后立即返回，不等待执行完成。
    
    Args:
        task_data: 任务创建数据，包含名称、描述、类型、优先级和负载
        
    Returns:
        统一响应格式，包含创建的任务信息
        
    Example:
        >>> POST /api/v1/tasks/submit
        >>> {
        ...     "name": "数据处理任务",
        ...     "description": "处理用户数据",
        ...     "task_type": "data_processing",
        ...     "priority": 5,
        ...     "payload": {"file": "data.csv"}
        ... }
        
        响应:
        {
            "code": 201,
            "message": "created successfully",
            "data": {
                "task_id": "uuid-string",
                "name": "数据处理任务",
                "status": "pending",
                ...
            },
            "timestamp": 1234567890
        }
    """
    try:
        # 提交任务到调度器
        task_id = await task_scheduler.submit_task(
            name=task_data.name,
            description=task_data.description,
            task_type=task_data.task_type,
            priority=task_data.priority,
            payload=task_data.payload,
        )

        # 查询创建的任务记录用于返回
        from app.db.session import AsyncSessionLocal
        from app.models.task import Task
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Task).where(Task.task_id == task_id)
            )
            task = result.scalar_one()

        return created_response(
            data=TaskResponse.model_validate(task).model_dump(),
            message="Task submitted successfully"
        )
    except Exception as e:
        logger.error(f"Failed to submit task: {e}")
        raise TaskSubmissionException(str(e))


@router.get(
    "/list",
    response_model=Dict[str, Any],
    summary="获取任务列表",
    description="获取任务列表，支持分页和多维度过滤。"
)
async def list_tasks(
    task_service: TaskServiceDep,
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量，最大100"),
    task_id: Optional[str] = Query(None, description="任务ID精确匹配"),
    name: Optional[str] = Query(None, description="任务名称模糊查询"),
    status: Optional[TaskStatus] = Query(None, description="任务状态过滤"),
    task_type: Optional[str] = Query(None, description="任务类型过滤"),
    priority_min: Optional[int] = Query(None, ge=0, le=100, description="最小优先级"),
    priority_max: Optional[int] = Query(None, ge=0, le=100, description="最大优先级"),
    created_after: Optional[datetime] = Query(None, description="创建时间之后（ISO格式）"),
    created_before: Optional[datetime] = Query(None, description="创建时间之前（ISO格式）"),
):
    """
    获取任务列表
    
    支持分页和多维度过滤查询，返回符合条件的任务列表和分页信息。
    
    Args:
        task_service: 任务服务实例（依赖注入）
        page: 页码，从1开始
        page_size: 每页记录数
        task_id: 按任务ID精确匹配
        name: 按名称模糊查询（支持SQL LIKE语法）
        status: 按状态过滤
        task_type: 按类型过滤
        priority_min: 最小优先级（包含）
        priority_max: 最大优先级（包含）
        created_after: 创建时间之后（包含）
        created_before: 创建时间之前（包含）
        
    Returns:
        统一响应格式，包含分页任务列表
        
    Example:
        >>> GET /api/v1/tasks/list?page=1&page_size=20&status=pending&priority_min=5
        
        响应:
        {
            "code": 200,
            "message": "success",
            "data": {
                "items": [{...}, {...}],
                "pagination": {
                    "total": 100,
                    "page": 1,
                    "page_size": 20,
                    "total_pages": 5,
                    "has_next": true,
                    "has_prev": false
                }
            },
            "timestamp": 1234567890
        }
    """
    result = await task_service.list_tasks(
        page=page,
        page_size=page_size,
        task_id=task_id,
        name=name,
        status=status,
        task_type=task_type,
        priority_min=priority_min,
        priority_max=priority_max,
        created_after=created_after,
        created_before=created_before,
    )
    
    # result.items 已经是 List[TaskResponse]，直接转换为字典
    items = [item.model_dump() for item in result.items]
    
    return paginated_response(
        items=items,
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        message="Tasks retrieved successfully"
    )


@router.get(
    "/{task_id}",
    response_model=Dict[str, Any],
    summary="获取任务详情",
    description="根据任务ID获取任务的完整信息。"
)
async def get_task(task_service: TaskServiceDep, task_id: str):
    """
    获取任务详情
    
    根据任务ID查询任务的完整信息。
    
    Args:
        task_service: 任务服务实例（依赖注入）
        task_id: 任务UUID
        
    Returns:
        统一响应格式，包含任务详细信息
        
    Raises:
        TaskNotFoundException: 任务不存在时抛出 404 错误
        
    Example:
        >>> GET /api/v1/tasks/abc-123-uuid
        
        响应:
        {
            "code": 200,
            "message": "success",
            "data": {
                "task_id": "abc-123-uuid",
                "name": "数据处理任务",
                "status": "running",
                ...
            },
            "timestamp": 1234567890
        }
    """
    task = await task_service.get_task_by_id(task_id)
    return success_response(
        data=TaskResponse.model_validate(task).model_dump(),
        message="Task retrieved successfully"
    )


@router.put(
    "/{task_id}",
    response_model=Dict[str, Any],
    summary="更新任务信息",
    description="更新任务的名称、描述、类型、优先级或负载数据。只有 PENDING 状态的任务可以更新。"
)
async def update_task(
    task_service: TaskServiceDep,
    task_id: str,
    task_update: TaskUpdate,
):
    """
    更新任务信息
    
    更新任务的部分或全部信息。只有处于 PENDING 状态的任务可以被更新。
    
    Args:
        task_service: 任务服务实例（依赖注入）
        task_id: 要更新的任务ID
        task_update: 更新的数据，所有字段都是可选的
        
    Returns:
        统一响应格式，包含更新后的任务信息
        
    Raises:
        TaskNotFoundException: 任务不存在
        TaskCannotBeUpdatedException: 任务状态不允许更新
        
    Example:
        >>> PUT /api/v1/tasks/abc-123-uuid
        >>> {
        ...     "name": "新名称",
        ...     "priority": 10
        ... }
        
        响应:
        {
            "code": 200,
            "message": "updated successfully",
            "data": {...},
            "timestamp": 1234567890
        }
    """
    task = await task_service.update_task(task_id, task_update)
    return success_response(
        data=TaskResponse.model_validate(task).model_dump(),
        message="Task updated successfully"
    )


@router.delete(
    "/{task_id}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="删除任务",
    description="删除任务记录。只有非运行中的任务可以删除。"
)
async def delete_task(task_service: TaskServiceDep, task_id: str):
    """
    删除任务
    
    从数据库中删除任务记录。只有非 RUNNING 状态的任务可以被删除。
    
    Args:
        task_service: 任务服务实例（依赖注入）
        task_id: 要删除的任务ID
        
    Returns:
        统一响应格式，表示删除成功
        
    Raises:
        TaskNotFoundException: 任务不存在
        TaskCannotBeDeletedException: 任务正在运行，无法删除
        
    Example:
        >>> DELETE /api/v1/tasks/abc-123-uuid
        
        响应:
        {
            "code": 200,
            "message": "deleted successfully",
            "data": null,
            "timestamp": 1234567890
        }
    """
    await task_service.delete_task(task_id)
    return success_response(
        data=None,
        message="Task deleted successfully"
    )


@router.post(
    "/{task_id}/cancel",
    response_model=Dict[str, Any],
    summary="取消任务",
    description="取消处于 PENDING 或 RUNNING 状态的任务。"
)
async def cancel_task(task_service: TaskServiceDep, task_id: str):
    """
    取消任务
    
    取消处于 PENDING 或 RUNNING 状态的任务。
    如果任务正在执行，会尝试中断执行。
    
    Args:
        task_service: 任务服务实例（依赖注入）
        task_id: 要取消的任务ID
        
    Returns:
        统一响应格式，包含取消后的任务信息
        
    Raises:
        TaskNotFoundException: 任务不存在
        TaskCannotBeCancelledException: 任务状态不允许取消
        
    Example:
        >>> POST /api/v1/tasks/abc-123-uuid/cancel
        
        响应:
        {
            "code": 200,
            "message": "success",
            "data": {
                "task_id": "abc-123-uuid",
                "status": "cancelled",
                ...
            },
            "timestamp": 1234567890
        }
    """
    from app.core.exceptions import TaskCannotBeCancelledException

    # 调用调度器取消任务
    success = await task_scheduler.cancel_task(task_id)

    if not success:
        # 取消失败，获取任务信息并抛出异常
        task = await task_service.get_task_by_id(task_id)
        raise TaskCannotBeCancelledException(task.status.value)

    # 获取更新后的任务信息
    task = await task_service.get_task_by_id(task_id)
    return success_response(
        data=TaskResponse.model_validate(task).model_dump(),
        message="Task cancelled successfully"
    )


@router.get(
    "/statistics/overview",
    response_model=Dict[str, Any],
    summary="获取任务统计",
    description="获取任务统计信息，包括各状态数量、成功率和平均执行时间。"
)
async def get_task_statistics(task_service: TaskServiceDep):
    """
    获取任务统计信息
    
    计算并返回任务的各种统计数据，用于仪表盘展示。
    
    Args:
        task_service: 任务服务实例（依赖注入）
        
    Returns:
        统一响应格式，包含任务统计信息
        
    Example:
        >>> GET /api/v1/tasks/statistics/overview
        
        响应:
        {
            "code": 200,
            "message": "success",
            "data": {
                "total_tasks": 100,
                "pending_count": 10,
                "running_count": 5,
                "completed_count": 80,
                "failed_count": 3,
                "cancelled_count": 2,
                "success_rate": 96.39,
                "average_execution_time": 5.23
            },
            "timestamp": 1234567890
        }
    """
    stats = await task_service.get_statistics()
    return success_response(
        data=stats.model_dump(),
        message="Statistics retrieved successfully"
    )
