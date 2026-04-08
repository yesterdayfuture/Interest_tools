"""
任务服务层
"""
import asyncio
import time
import random
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.core.exceptions import TaskNotFoundException, TaskInvalidStateException
from app.models.task import Task, TaskStatus
from app.schemas.task import TaskCreate, TaskUpdate, TaskListRequest, TaskStatistics
from app.services.task_scheduler import task_scheduler


class TaskService:
    """任务服务类"""
    
    @staticmethod
    async def create_task(session: AsyncSession, task_create: TaskCreate) -> Task:
        """
        创建新任务
        
        Args:
            session: 数据库会话
            task_create: 任务创建数据
            
        Returns:
            Task: 创建的任务对象
        """
        # 创建任务记录
        task = Task(
            name=task_create.name,
            description=task_create.description,
            task_type=task_create.task_type,
            priority=task_create.priority,
            payload=task_create.payload or {},
            status=TaskStatus.PENDING,
        )
        
        session.add(task)
        await session.commit()
        await session.refresh(task)
        
        logger.info(f"Task created: {task.id} - {task.name}")
        
        # 提交到调度器执行
        task_scheduler.submit_task(
            task.id,
            TaskService._execute_task,
            task.id,
            task.task_type,
            task.payload
        )
        
        return task
    
    @staticmethod
    async def get_task(session: AsyncSession, task_id: str) -> Task:
        """
        获取任务详情
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            
        Returns:
            Task: 任务对象
            
        Raises:
            TaskNotFoundException: 任务不存在
        """
        result = await session.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        
        if not task:
            raise TaskNotFoundException(f"Task not found: {task_id}")
        
        return task
    
    @staticmethod
    async def list_tasks(
        session: AsyncSession, 
        query_params: TaskListRequest
    ) -> tuple[List[Task], int]:
        """
        查询任务列表
        
        Args:
            session: 数据库会话
            query_params: 查询参数
            
        Returns:
            tuple: (任务列表, 总数)
        """
        # 构建查询条件
        conditions = []
        
        if query_params.task_id:
            conditions.append(Task.id == query_params.task_id)
        
        if query_params.name:
            conditions.append(Task.name.ilike(f"%{query_params.name}%"))
        
        if query_params.status:
            conditions.append(Task.status == query_params.status)
        
        if query_params.task_type:
            conditions.append(Task.task_type == query_params.task_type)
        
        if query_params.priority_min is not None:
            conditions.append(Task.priority >= query_params.priority_min)
        
        if query_params.priority_max is not None:
            conditions.append(Task.priority <= query_params.priority_max)
        
        if query_params.created_after:
            conditions.append(Task.created_at >= query_params.created_after)
        
        if query_params.created_before:
            conditions.append(Task.created_at <= query_params.created_before)
        
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
        offset = (query_params.page - 1) * query_params.page_size
        query = query.order_by(Task.created_at.desc()).offset(offset).limit(query_params.page_size)
        
        result = await session.execute(query)
        tasks = result.scalars().all()
        
        return list(tasks), total
    
    @staticmethod
    async def update_task(
        session: AsyncSession, 
        task_id: str, 
        task_update: TaskUpdate
    ) -> Task:
        """
        更新任务
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            task_update: 更新数据
            
        Returns:
            Task: 更新后的任务对象
        """
        task = await TaskService.get_task(session, task_id)
        
        # 只允许更新 pending 状态的任务
        if task.status != TaskStatus.PENDING:
            raise TaskInvalidStateException(
                f"Cannot update task in {task.status} state. Only pending tasks can be updated."
            )
        
        # 更新字段
        update_data = task_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(task, field, value)
        
        await session.commit()
        await session.refresh(task)
        
        logger.info(f"Task updated: {task_id}")
        return task
    
    @staticmethod
    async def delete_task(session: AsyncSession, task_id: str) -> bool:
        """
        删除任务
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            
        Returns:
            bool: 是否成功删除
        """
        task = await TaskService.get_task(session, task_id)
        
        # 如果任务正在运行，先取消
        if task.status == TaskStatus.RUNNING:
            await task_scheduler.cancel_task(task_id)
        
        await session.delete(task)
        await session.commit()
        
        logger.info(f"Task deleted: {task_id}")
        return True
    
    @staticmethod
    async def cancel_task(session: AsyncSession, task_id: str) -> Task:
        """
        取消任务
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            
        Returns:
            Task: 更新后的任务对象
        """
        task = await TaskService.get_task(session, task_id)
        
        # 只能取消 pending 或 running 状态的任务
        if task.status not in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            raise TaskInvalidStateException(
                f"Cannot cancel task in {task.status} state"
            )
        
        # 调用调度器取消任务
        await task_scheduler.cancel_task(task_id)
        
        # 刷新任务状态
        await session.refresh(task)
        
        logger.info(f"Task cancelled: {task_id}")
        return task
    
    @staticmethod
    async def get_statistics(session: AsyncSession) -> TaskStatistics:
        """
        获取任务统计信息
        
        Args:
            session: 数据库会话
            
        Returns:
            TaskStatistics: 统计信息
        """
        # 总数
        total_result = await session.execute(select(func.count()).select_from(Task))
        total_tasks = total_result.scalar()
        
        # 各状态数量
        status_counts = {}
        for status in TaskStatus:
            count_result = await session.execute(
                select(func.count()).where(Task.status == status)
            )
            status_counts[status] = count_result.scalar()
        
        # 成功率
        completed = status_counts.get(TaskStatus.COMPLETED, 0)
        failed = status_counts.get(TaskStatus.FAILED, 0)
        total_executed = completed + failed
        success_rate = (completed / total_executed * 100) if total_executed > 0 else 100.0
        
        # 平均执行时间
        avg_time_result = await session.execute(
            select(func.avg(Task.execution_time)).where(Task.execution_time.isnot(None))
        )
        avg_execution_time = avg_time_result.scalar()
        
        return TaskStatistics(
            total_tasks=total_tasks,
            pending_count=status_counts.get(TaskStatus.PENDING, 0),
            running_count=status_counts.get(TaskStatus.RUNNING, 0),
            completed_count=completed,
            failed_count=failed,
            cancelled_count=status_counts.get(TaskStatus.CANCELLED, 0),
            success_rate=round(success_rate, 2),
            average_execution_time=round(avg_execution_time, 2) if avg_execution_time else None
        )
    
    @staticmethod
    async def _execute_task(task_id: str, task_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        实际执行任务（在线程中运行）
        
        这是一个示例任务执行函数，实际项目中可以根据 task_type 
        调用不同的处理函数。
        
        Args:
            task_id: 任务ID
            task_type: 任务类型
            payload: 任务数据
            
        Returns:
            Dict: 执行结果
        """
        logger.info(f"Executing task {task_id} of type {task_type}")
        
        # 模拟任务执行时间（1-5秒）
        execution_time = random.uniform(1, 5)
        time.sleep(execution_time)
        
        # 模拟任务处理
        result = {
            "task_id": task_id,
            "task_type": task_type,
            "processed_data": payload,
            "execution_time": execution_time,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # 模拟随机失败（10%概率）
        if random.random() < 0.1:
            raise Exception("Simulated task failure")
        
        logger.info(f"Task {task_id} executed successfully")
        return result


# 服务实例
task_service = TaskService()
