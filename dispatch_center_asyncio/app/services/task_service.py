"""
任务业务服务模块

该模块实现了任务相关的业务逻辑，封装数据库操作和业务规则。
作为服务层，负责协调数据访问和调度器操作，为 API 层提供高层次的业务接口。

主要功能：
- 任务 CRUD 操作
- 任务列表查询和过滤
- 任务统计信息计算
- 业务规则验证

设计原则：
- 每个方法都是原子操作，独立处理事务
- 抛出业务异常而非返回错误码
- 与调度器解耦，不直接操作任务执行
"""

from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
import json

from app.models.task import Task, TaskStatus
from app.schemas.task import TaskCreate, TaskUpdate, TaskListResponse, TaskResponse, TaskStatistics
from app.core.exceptions import (
    TaskNotFoundException,
    TaskCannotBeUpdatedException,
    TaskCannotBeDeletedException,
)


class TaskService:
    """
    任务业务服务类
    
    封装任务相关的所有业务逻辑，为 API 层提供统一的服务接口。
    每个实例绑定一个数据库会话，所有操作在该会话中执行。
    
    Attributes:
        db: 异步数据库会话
        
    Example:
        >>> async with AsyncSessionLocal() as session:
        ...     service = TaskService(session)
        ...     task = await service.get_task_by_id("uuid-string")
        ...     stats = await service.get_statistics()
    """
    
    def __init__(self, db: AsyncSession):
        """
        初始化任务服务
        
        Args:
            db: 异步数据库会话
        """
        self.db = db

    async def get_task_by_id(self, task_id: str) -> Task:
        """
        根据任务ID获取任务
        
        查询数据库获取任务实体，如果任务不存在则抛出异常。
        
        Args:
            task_id: 任务UUID
            
        Returns:
            Task: 任务数据库模型实例
            
        Raises:
            TaskNotFoundException: 任务不存在时抛出
            
        Example:
            >>> try:
            ...     task = await service.get_task_by_id("abc-123")
            ...     print(task.name)
            ... except TaskNotFoundException:
            ...     print("Task not found")
        """
        result = await self.db.execute(
            select(Task).where(Task.task_id == task_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            raise TaskNotFoundException(task_id)

        return task

    async def list_tasks(
        self,
        page: int = 1,
        page_size: int = 10,
        task_id: Optional[str] = None,
        name: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        task_type: Optional[str] = None,
        priority_min: Optional[int] = None,
        priority_max: Optional[int] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
    ) -> TaskListResponse:
        """
        获取任务列表（支持分页和过滤）
        
        根据过滤条件查询任务，支持分页返回。所有过滤条件都是可选的，
        可以组合使用。
        
        Args:
            page: 页码，从1开始
            page_size: 每页记录数，默认10
            task_id: 按任务ID精确匹配
            name: 按名称模糊查询（支持SQL LIKE）
            status: 按状态过滤
            task_type: 按类型过滤
            priority_min: 最小优先级（包含）
            priority_max: 最大优先级（包含）
            created_after: 创建时间之后（包含）
            created_before: 创建时间之前（包含）
            
        Returns:
            TaskListResponse: 包含任务列表和分页元数据
            
        Example:
            >>> response = await service.list_tasks(
            ...     page=1,
            ...     page_size=20,
            ...     status=TaskStatus.PENDING,
            ...     priority_min=5
            ... )
            >>> print(f"Total: {response.total}, Pages: {response.total_pages}")
        """
        # 构建基础查询
        query = select(Task)
        count_query = select(func.count(Task.id))

        # 构建过滤条件
        filters = []
        if task_id:
            filters.append(Task.task_id == task_id)
        if name:
            # 使用 ilike 实现不区分大小写的模糊查询
            filters.append(Task.name.ilike(f"%{name}%"))
        if status:
            filters.append(Task.status == status)
        if task_type:
            filters.append(Task.task_type == task_type)
        if priority_min is not None:
            filters.append(Task.priority >= priority_min)
        if priority_max is not None:
            filters.append(Task.priority <= priority_max)
        if created_after:
            filters.append(Task.created_at >= created_after)
        if created_before:
            filters.append(Task.created_at <= created_before)

        # 应用过滤条件
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        # 获取总记录数
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # 分页查询
        offset = (page - 1) * page_size
        # 按创建时间倒序排列，最新的在前
        query = query.order_by(desc(Task.created_at)).offset(offset).limit(page_size)

        result = await self.db.execute(query)
        tasks = result.scalars().all()

        # 计算总页数
        total_pages = (total + page_size - 1) // page_size

        return TaskListResponse(
            total=total,
            items=[TaskResponse.model_validate(task) for task in tasks],
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def update_task(self, task_id: str, task_update: TaskUpdate) -> Task:
        """
        更新任务信息
        
        更新任务的名称、描述、类型、优先级或负载数据。
        只有处于 PENDING 状态的任务可以更新。
        
        Args:
            task_id: 要更新的任务ID
            task_update: 更新的数据，使用 TaskUpdate Schema
            
        Returns:
            Task: 更新后的任务实体
            
        Raises:
            TaskNotFoundException: 任务不存在
            TaskCannotBeUpdatedException: 任务状态不允许更新
            
        Example:
            >>> update_data = TaskUpdate(name="新名称", priority=10)
            >>> updated_task = await service.update_task("uuid", update_data)
        """
        # 获取任务，不存在会抛出异常
        task = await self.get_task_by_id(task_id)

        # 验证任务状态，只有 PENDING 可以更新
        # RUNNING/COMPLETED/FAILED/CANCELLED 状态的任务都不允许更新
        if task.status != TaskStatus.PENDING:
            raise TaskCannotBeUpdatedException(task.status.value)

        # 获取更新的数据，排除未设置的字段
        update_data = task_update.model_dump(exclude_unset=True)

        # 特殊处理 payload 字段，将字典序列化为 JSON 字符串
        if "payload" in update_data and update_data["payload"] is not None:
            update_data["payload"] = json.dumps(update_data["payload"])

        # 应用更新
        for field, value in update_data.items():
            setattr(task, field, value)

        # 更新时间戳
        task.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(task)

        return task

    async def delete_task(self, task_id: str) -> None:
        """
        删除任务
        
        从数据库中删除任务记录。只有非运行中的任务可以删除。
        
        Args:
            task_id: 要删除的任务ID
            
        Raises:
            TaskNotFoundException: 任务不存在
            TaskCannotBeDeletedException: 任务正在运行，无法删除
            
        Example:
            >>> try:
            ...     await service.delete_task("uuid")
            ...     print("Task deleted")
            ... except TaskCannotBeDeletedException:
            ...     print("Cannot delete running task")
        """
        task = await self.get_task_by_id(task_id)

        # 验证任务状态，运行中的任务不能删除
        if task.status == TaskStatus.RUNNING:
            raise TaskCannotBeDeletedException()

        await self.db.delete(task)
        await self.db.commit()

    async def get_statistics(self) -> TaskStatistics:
        """
        获取任务统计信息
        
        计算各类状态的任务数量、成功率和平均执行时间。
        
        Returns:
            TaskStatistics: 统计信息
            
        Example:
            >>> stats = await service.get_statistics()
            >>> print(f"成功率: {stats.success_rate}%")
            >>> print(f"平均执行时间: {stats.average_execution_time}s")
        """
        # 总任务数
        total_result = await self.db.execute(select(func.count(Task.id)))
        total_tasks = total_result.scalar()

        # 各状态任务数
        pending_result = await self.db.execute(
            select(func.count(Task.id)).where(Task.status == TaskStatus.PENDING)
        )
        pending_count = pending_result.scalar()

        running_result = await self.db.execute(
            select(func.count(Task.id)).where(Task.status == TaskStatus.RUNNING)
        )
        running_count = running_result.scalar()

        completed_result = await self.db.execute(
            select(func.count(Task.id)).where(Task.status == TaskStatus.COMPLETED)
        )
        completed_count = completed_result.scalar()

        failed_result = await self.db.execute(
            select(func.count(Task.id)).where(Task.status == TaskStatus.FAILED)
        )
        failed_count = failed_result.scalar()

        cancelled_result = await self.db.execute(
            select(func.count(Task.id)).where(Task.status == TaskStatus.CANCELLED)
        )
        cancelled_count = cancelled_result.scalar()

        # 计算成功率
        # 成功率 = 成功数 / (成功数 + 失败数) * 100
        success_rate = 0.0
        if completed_count + failed_count > 0:
            success_rate = (completed_count / (completed_count + failed_count)) * 100

        # 计算平均执行时间
        # 使用 julianday 函数计算天数差，转换为秒
        avg_time_result = await self.db.execute(
            select(func.avg(
                func.julianday(Task.completed_at) - func.julianday(Task.started_at)
            )).where(Task.status == TaskStatus.COMPLETED)
        )
        avg_time = avg_time_result.scalar()
        # julianday 返回天数，转换为秒（1天 = 24 * 3600 秒）
        average_execution_time = avg_time * 24 * 3600 if avg_time else None

        return TaskStatistics(
            total_tasks=total_tasks,
            pending_count=pending_count,
            running_count=running_count,
            completed_count=completed_count,
            failed_count=failed_count,
            cancelled_count=cancelled_count,
            success_rate=round(success_rate, 2),
            average_execution_time=round(average_execution_time, 2) if average_execution_time else None,
        )
