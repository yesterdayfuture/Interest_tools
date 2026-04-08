"""多进程调度器相关 API 路由."""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import MultiProcessSchedulerDep, TaskServiceDep
from app.core.logging import get_logger
from app.schemas.task import (
    APIResponse,
    SchedulerStatusResponse,
    TaskCreate,
    TaskResponse,
    TaskSubmitResponse,
)

logger = get_logger("api.scheduler")

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


@router.post("/submit", response_model=TaskSubmitResponse)
async def submit_task_multi_process(
    task_create: TaskCreate,
    task_service: TaskServiceDep,
    scheduler: MultiProcessSchedulerDep,
) -> TaskSubmitResponse:
    """使用多进程调度器提交新任务."""
    try:
        # 创建任务
        task = await task_service.create_task(task_create)

        # 提交到多进程调度器
        success = await scheduler.submit_task(task)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to submit task to scheduler",
            )

        return TaskSubmitResponse(
            success=True,
            message="Task submitted to multi-process scheduler successfully",
            task_id=task.id,
            data=TaskResponse.model_validate(task),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.get("/status", response_model=SchedulerStatusResponse)
async def get_scheduler_status(
    scheduler: MultiProcessSchedulerDep,
) -> SchedulerStatusResponse:
    """获取多进程调度器状态."""
    try:
        status = scheduler.get_scheduler_status()
        return SchedulerStatusResponse(
            success=True,
            message="Scheduler status retrieved successfully",
            data=status,
        )
    except Exception as e:
        logger.error(f"Failed to get scheduler status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}",
        )


@router.post("/cancel/{task_id}", response_model=APIResponse)
async def cancel_task(
    task_id: str,
    scheduler: MultiProcessSchedulerDep,
) -> APIResponse:
    """取消正在执行或排队中的任务."""
    try:
        success = await scheduler.cancel_task(task_id)

        if not success:
            return APIResponse(
                success=False,
                message=f"Task {task_id} not found or cannot be cancelled",
            )

        return APIResponse(
            success=True,
            message=f"Task {task_id} cancelled successfully",
        )
    except Exception as e:
        logger.error(f"Failed to cancel task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel task: {str(e)}",
        )


@router.get("/task/{task_id}/status")
async def get_task_status_in_scheduler(
    task_id: str,
    scheduler: MultiProcessSchedulerDep,
):
    """获取任务在调度器中的状态."""
    try:
        status = scheduler.get_task_status(task_id)

        if status is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found in scheduler",
            )

        return {
            "success": True,
            "message": "Task status retrieved",
            "data": status,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {str(e)}",
        )
