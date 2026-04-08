"""
任务相关 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime

from app.api.deps import get_db_session
from app.schemas.task import (
    TaskCreate, 
    TaskUpdate, 
    TaskResponse, 
    TaskListRequest,
    TaskListResponse,
    TaskStatistics,
    ApiResponse
)
from app.services.task_service import task_service
from app.core.exceptions import TaskSchedulerException

router = APIRouter()


@router.post("/submit", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def submit_task(
    task_create: TaskCreate,
    session: AsyncSession = Depends(get_db_session)
):
    """
    提交新任务
    
    - **name**: 任务名称
    - **description**: 任务描述（可选）
    - **task_type**: 任务类型
    - **priority**: 优先级（1-10，默认5）
    - **payload**: 任务负载数据（可选）
    """
    try:
        task = await task_service.create_task(session, task_create)
        return ApiResponse(
            success=True,
            message="Task submitted successfully",
            task_id=task.id,
            data=TaskResponse.model_validate(task)
        )
    except TaskSchedulerException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/list", response_model=TaskListResponse)
async def list_tasks(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    task_id: Optional[str] = Query(None, description="任务ID精确匹配"),
    name: Optional[str] = Query(None, description="任务名称模糊查询"),
    status: Optional[str] = Query(None, description="任务状态过滤"),
    task_type: Optional[str] = Query(None, description="任务类型过滤"),
    priority_min: Optional[int] = Query(None, ge=1, le=10, description="最小优先级"),
    priority_max: Optional[int] = Query(None, ge=1, le=10, description="最大优先级"),
    created_after: Optional[datetime] = Query(None, description="创建时间起始"),
    created_before: Optional[datetime] = Query(None, description="创建时间截止"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    查询任务列表
    
    支持多维度过滤和分页查询
    """
    try:
        query_params = TaskListRequest(
            page=page,
            page_size=page_size,
            task_id=task_id,
            name=name,
            status=status,
            task_type=task_type,
            priority_min=priority_min,
            priority_max=priority_max,
            created_after=created_after,
            created_before=created_before
        )
        
        tasks, total = await task_service.list_tasks(session, query_params)
        
        return TaskListResponse(
            total=total,
            page=page,
            page_size=page_size,
            items=[TaskResponse.model_validate(task) for task in tasks]
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{task_id}", response_model=ApiResponse)
async def get_task(
    task_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    """
    获取任务详情
    
    - **task_id**: 任务ID
    """
    try:
        task = await task_service.get_task(session, task_id)
        return ApiResponse(
            success=True,
            message="Task found",
            task_id=task_id,
            data=TaskResponse.model_validate(task)
        )
    except TaskSchedulerException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/{task_id}", response_model=ApiResponse)
async def update_task(
    task_id: str,
    task_update: TaskUpdate,
    session: AsyncSession = Depends(get_db_session)
):
    """
    更新任务
    
    只能更新 pending 状态的任务
    
    - **task_id**: 任务ID
    """
    try:
        task = await task_service.update_task(session, task_id, task_update)
        return ApiResponse(
            success=True,
            message="Task updated successfully",
            task_id=task_id,
            data=TaskResponse.model_validate(task)
        )
    except TaskSchedulerException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/{task_id}", response_model=ApiResponse)
async def delete_task(
    task_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    """
    删除任务
    
    - **task_id**: 任务ID
    """
    try:
        await task_service.delete_task(session, task_id)
        return ApiResponse(
            success=True,
            message="Task deleted successfully",
            task_id=task_id
        )
    except TaskSchedulerException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{task_id}/cancel", response_model=ApiResponse)
async def cancel_task(
    task_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    """
    取消任务
    
    只能取消 pending 或 running 状态的任务
    
    - **task_id**: 任务ID
    """
    try:
        task = await task_service.cancel_task(session, task_id)
        return ApiResponse(
            success=True,
            message="Task cancelled successfully",
            task_id=task_id,
            data=TaskResponse.model_validate(task)
        )
    except TaskSchedulerException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/statistics/overview", response_model=TaskStatistics)
async def get_statistics(
    session: AsyncSession = Depends(get_db_session)
):
    """
    获取任务统计信息
    
    返回任务总数、各状态数量、成功率等统计信息
    """
    try:
        stats = await task_service.get_statistics(session)
        return stats
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
