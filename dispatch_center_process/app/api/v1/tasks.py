"""任务相关 API 路由."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import TaskSchedulerDep, TaskServiceDep
from app.core.exceptions import TaskSchedulerException
from app.core.logging import get_logger
from app.models.task import TaskStatus
from app.schemas.task import (
    APIResponse,
    TaskCreate,
    TaskListRequest,
    TaskListResponse,
    TaskResponse,
    TaskStatisticsResponse,
    TaskSubmitResponse,
    TaskUpdate,
)
from app.services.task_scheduler import task_scheduler

logger = get_logger("api.tasks")

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/submit", response_model=TaskSubmitResponse)
async def submit_task(
    task_create: TaskCreate,
    task_service: TaskServiceDep,
) -> TaskSubmitResponse:
    """提交新任务."""
    try:
        # 创建任务
        task = await task_service.create_task(task_create)
        
        # 提交到调度器执行
        await task_scheduler.submit_task(task)
        
        return TaskSubmitResponse(
            success=True,
            message="Task submitted successfully",
            task_id=task.id,
            data=TaskResponse.model_validate(task),
        )
        
    except TaskSchedulerException as e:
        logger.error(f"Failed to submit task: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "message": e.message,
                "code": e.code,
                "details": e.details,
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error submitting task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "message": "Internal server error",
            }
        )


@router.get("/list", response_model=TaskListResponse)
async def list_tasks(
    task_service: TaskServiceDep,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    task_id: Optional[str] = Query(None, description="任务ID精确匹配"),
    name: Optional[str] = Query(None, description="任务名称模糊查询"),
    status: Optional[TaskStatus] = Query(None, description="任务状态过滤"),
    task_type: Optional[str] = Query(None, description="任务类型过滤"),
    priority_min: Optional[int] = Query(None, ge=1, le=10, description="最小优先级"),
    priority_max: Optional[int] = Query(None, ge=1, le=10, description="最大优先级"),
    created_after: Optional[str] = Query(None, description="创建时间之后(ISO格式)"),
    created_before: Optional[str] = Query(None, description="创建时间之前(ISO格式)"),
) -> TaskListResponse:
    """获取任务列表."""
    from datetime import datetime
    
    # 解析时间参数
    created_after_dt = None
    created_before_dt = None
    
    if created_after:
        try:
            created_after_dt = datetime.fromisoformat(created_after)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid created_after format, use ISO format"
            )
    
    if created_before:
        try:
            created_before_dt = datetime.fromisoformat(created_before)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid created_before format, use ISO format"
            )
    
    # 构建查询请求
    request = TaskListRequest(
        page=page,
        page_size=page_size,
        task_id=task_id,
        name=name,
        status=status,
        task_type=task_type,
        priority_min=priority_min,
        priority_max=priority_max,
        created_after=created_after_dt,
        created_before=created_before_dt,
    )
    
    try:
        tasks, total = await task_service.list_tasks(request)
        
        total_pages = (total + page_size - 1) // page_size
        
        return TaskListResponse(
            items=[TaskResponse.model_validate(task) for task in tasks],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
        
    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tasks"
        )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    task_service: TaskServiceDep,
) -> TaskResponse:
    """获取任务详情."""
    try:
        task = await task_service.get_task(task_id)
        return TaskResponse.model_validate(task)
        
    except TaskSchedulerException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "message": e.message,
                "code": e.code,
            }
        )
    except Exception as e:
        logger.error(f"Failed to get task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve task"
        )


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    task_update: TaskUpdate,
    task_service: TaskServiceDep,
) -> TaskResponse:
    """更新任务."""
    try:
        task = await task_service.update_task(task_id, task_update)
        return TaskResponse.model_validate(task)
        
    except TaskSchedulerException as e:
        status_code = (
            status.HTTP_404_NOT_FOUND 
            if e.code == "TASK_NOT_FOUND" 
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(
            status_code=status_code,
            detail={
                "success": False,
                "message": e.message,
                "code": e.code,
                "details": e.details,
            }
        )
    except Exception as e:
        logger.error(f"Failed to update task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update task"
        )


@router.delete("/{task_id}", response_model=APIResponse)
async def delete_task(
    task_id: str,
    task_service: TaskServiceDep,
) -> APIResponse:
    """删除任务."""
    try:
        await task_service.delete_task(task_id)
        
        return APIResponse(
            success=True,
            message="Task deleted successfully",
        )
        
    except TaskSchedulerException as e:
        status_code = (
            status.HTTP_404_NOT_FOUND 
            if e.code == "TASK_NOT_FOUND" 
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(
            status_code=status_code,
            detail={
                "success": False,
                "message": e.message,
                "code": e.code,
                "details": e.details,
            }
        )
    except Exception as e:
        logger.error(f"Failed to delete task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete task"
        )


@router.post("/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(
    task_id: str,
    task_service: TaskServiceDep,
) -> TaskResponse:
    """取消任务."""
    try:
        # 先尝试取消调度器中的任务
        await task_scheduler.cancel_task(task_id)
        
        # 更新数据库状态
        task = await task_service.cancel_task(task_id)
        
        return TaskResponse.model_validate(task)
        
    except TaskSchedulerException as e:
        status_code = (
            status.HTTP_404_NOT_FOUND 
            if e.code == "TASK_NOT_FOUND" 
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(
            status_code=status_code,
            detail={
                "success": False,
                "message": e.message,
                "code": e.code,
                "details": e.details,
            }
        )
    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel task"
        )


@router.get("/statistics/overview", response_model=TaskStatisticsResponse)
async def get_statistics(
    task_service: TaskServiceDep,
) -> TaskStatisticsResponse:
    """获取任务统计信息."""
    try:
        stats = await task_service.get_statistics()
        
        return TaskStatisticsResponse(
            success=True,
            data=stats,
        )
        
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
        )
