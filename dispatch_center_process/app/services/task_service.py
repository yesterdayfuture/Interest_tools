"""任务服务层."""

from datetime import datetime
from typing import Any, List, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    DatabaseException,
    TaskAlreadyExistsException,
    TaskInvalidStatusException,
    TaskNotFoundException,
)
from app.core.logging import get_logger
from app.db.session import get_db_session
from app.models.task import Task, TaskStatus
from app.schemas.task import TaskCreate, TaskListRequest, TaskStatistics, TaskUpdate

logger = get_logger("task_service")


class TaskService:
    """任务服务类."""
    
    async def create_task(self, task_create: TaskCreate) -> Task:
        """创建新任务."""
        async with get_db_session() as session:
            try:
                # 创建任务对象
                task = Task(
                    name=task_create.name,
                    description=task_create.description,
                    task_type=task_create.task_type,
                    priority=task_create.priority,
                    payload=task_create.payload,
                    status=TaskStatus.PENDING,
                )
                
                session.add(task)
                await session.flush()
                await session.refresh(task)
                
                logger.info(f"Task created: {task.id}")
                return task
                
            except Exception as e:
                logger.error(f"Failed to create task: {e}")
                raise DatabaseException(f"Failed to create task: {e}")
    
    async def get_task(self, task_id: str) -> Task:
        """获取任务详情."""
        async with get_db_session() as session:
            result = await session.execute(
                select(Task).where(Task.id == task_id)
            )
            task = result.scalar_one_or_none()
            
            if task is None:
                raise TaskNotFoundException(task_id)
            
            return task
    
    async def get_task_or_none(self, task_id: str) -> Optional[Task]:
        """获取任务（可能不存在）."""
        async with get_db_session() as session:
            result = await session.execute(
                select(Task).where(Task.id == task_id)
            )
            return result.scalar_one_or_none()
    
    async def list_tasks(self, request: TaskListRequest) -> Tuple[List[Task], int]:
        """查询任务列表."""
        async with get_db_session() as session:
            # 构建查询条件
            conditions = []
            
            if request.task_id:
                conditions.append(Task.id == request.task_id)
            
            if request.name:
                conditions.append(Task.name.ilike(f"%{request.name}%"))
            
            if request.status:
                conditions.append(Task.status == request.status)
            
            if request.task_type:
                conditions.append(Task.task_type == request.task_type)
            
            if request.priority_min is not None:
                conditions.append(Task.priority >= request.priority_min)
            
            if request.priority_max is not None:
                conditions.append(Task.priority <= request.priority_max)
            
            if request.created_after:
                conditions.append(Task.created_at >= request.created_after)
            
            if request.created_before:
                conditions.append(Task.created_at <= request.created_before)
            
            # 构建查询
            query = select(Task)
            if conditions:
                query = query.where(and_(*conditions))
            
            # 获取总数
            count_query = select(func.count()).select_from(Task)
            if conditions:
                count_query = count_query.where(and_(*conditions))
            
            total_result = await session.execute(count_query)
            total = total_result.scalar()
            
            # 分页和排序
            query = query.order_by(Task.created_at.desc())
            query = query.offset((request.page - 1) * request.page_size)
            query = query.limit(request.page_size)
            
            # 执行查询
            result = await session.execute(query)
            tasks = result.scalars().all()
            
            return list(tasks), total
    
    async def update_task(
        self, 
        task_id: str, 
        task_update: TaskUpdate
    ) -> Task:
        """更新任务."""
        async with get_db_session() as session:
            # 获取任务
            result = await session.execute(
                select(Task).where(Task.id == task_id)
            )
            task = result.scalar_one_or_none()
            
            if task is None:
                raise TaskNotFoundException(task_id)
            
            # 检查任务状态
            if task.status == TaskStatus.RUNNING:
                raise TaskInvalidStatusException(
                    task_id, 
                    task.status.value, 
                    "pending/completed/failed/cancelled"
                )
            
            # 更新字段
            update_data = task_update.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(task, field, value)
            
            task.updated_at = datetime.utcnow()
            
            await session.flush()
            await session.refresh(task)
            
            logger.info(f"Task updated: {task_id}")
            return task
    
    async def delete_task(self, task_id: str) -> None:
        """删除任务."""
        async with get_db_session() as session:
            # 获取任务
            result = await session.execute(
                select(Task).where(Task.id == task_id)
            )
            task = result.scalar_one_or_none()
            
            if task is None:
                raise TaskNotFoundException(task_id)
            
            # 检查任务状态
            if task.status == TaskStatus.RUNNING:
                raise TaskInvalidStatusException(
                    task_id, 
                    task.status.value, 
                    "pending/completed/failed/cancelled"
                )
            
            await session.delete(task)
            
            logger.info(f"Task deleted: {task_id}")
    
    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        started_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
    ) -> Task:
        """更新任务状态."""
        async with get_db_session() as session:
            result = await session.execute(
                select(Task).where(Task.id == task_id)
            )
            task = result.scalar_one_or_none()
            
            if task is None:
                raise TaskNotFoundException(task_id)
            
            task.status = status
            task.updated_at = datetime.utcnow()
            
            if started_at:
                task.started_at = started_at
            
            if error_message:
                task.error_message = error_message
            
            await session.flush()
            await session.refresh(task)
            
            return task
    
    async def complete_task(
        self,
        task_id: str,
        result: dict[str, Any],
        completed_at: datetime,
        execution_time: float,
    ) -> Task:
        """标记任务完成."""
        async with get_db_session() as session:
            result_query = await session.execute(
                select(Task).where(Task.id == task_id)
            )
            task = result_query.scalar_one_or_none()
            
            if task is None:
                raise TaskNotFoundException(task_id)
            
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = completed_at
            task.execution_time = execution_time
            task.updated_at = datetime.utcnow()
            
            await session.flush()
            await session.refresh(task)
            
            return task
    
    async def fail_task(
        self,
        task_id: str,
        error_message: str,
        completed_at: datetime,
        execution_time: float,
    ) -> Task:
        """标记任务失败."""
        async with get_db_session() as session:
            result = await session.execute(
                select(Task).where(Task.id == task_id)
            )
            task = result.scalar_one_or_none()
            
            if task is None:
                raise TaskNotFoundException(task_id)
            
            task.status = TaskStatus.FAILED
            task.error_message = error_message
            task.completed_at = completed_at
            task.execution_time = execution_time
            task.updated_at = datetime.utcnow()
            
            await session.flush()
            await session.refresh(task)
            
            return task
    
    async def cancel_task(self, task_id: str) -> Task:
        """取消任务."""
        async with get_db_session() as session:
            result = await session.execute(
                select(Task).where(Task.id == task_id)
            )
            task = result.scalar_one_or_none()
            
            if task is None:
                raise TaskNotFoundException(task_id)
            
            # 只能取消 pending 或 running 的任务
            if task.status not in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                raise TaskInvalidStatusException(
                    task_id, 
                    task.status.value, 
                    "pending/running"
                )
            
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.utcnow()
            task.updated_at = datetime.utcnow()
            
            await session.flush()
            await session.refresh(task)
            
            logger.info(f"Task cancelled: {task_id}")
            return task
    
    async def get_statistics(self) -> TaskStatistics:
        """获取任务统计信息."""
        async with get_db_session() as session:
            # 总任务数
            total_result = await session.execute(select(func.count()).select_from(Task))
            total_tasks = total_result.scalar()
            
            # 各状态任务数
            status_counts = {}
            for status in TaskStatus:
                count_result = await session.execute(
                    select(func.count()).where(Task.status == status)
                )
                status_counts[status.value] = count_result.scalar()
            
            # 计算成功率
            completed = status_counts.get(TaskStatus.COMPLETED.value, 0)
            failed = status_counts.get(TaskStatus.FAILED.value, 0)
            
            if completed + failed > 0:
                success_rate = (completed / (completed + failed)) * 100
            else:
                success_rate = 0.0
            
            # 平均执行时间
            avg_time_result = await session.execute(
                select(func.avg(Task.execution_time)).where(
                    Task.execution_time.isnot(None)
                )
            )
            avg_execution_time = avg_time_result.scalar()
            
            return TaskStatistics(
                total_tasks=total_tasks,
                pending_count=status_counts.get(TaskStatus.PENDING.value, 0),
                running_count=status_counts.get(TaskStatus.RUNNING.value, 0),
                completed_count=completed,
                failed_count=failed,
                cancelled_count=status_counts.get(TaskStatus.CANCELLED.value, 0),
                success_rate=round(success_rate, 2),
                average_execution_time=round(avg_execution_time, 2) if avg_execution_time else None,
            )
