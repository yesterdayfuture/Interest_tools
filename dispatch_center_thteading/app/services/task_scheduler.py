"""
任务调度器 - 使用 ThreadPoolExecutor 实现并发控制
"""
import asyncio
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, Optional, Callable, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.logging import logger
from app.models.task import Task, TaskStatus
from app.db.session import AsyncSessionLocal


class TaskScheduler:
    """
    任务调度器
    
    使用 ThreadPoolExecutor 实现线程池并发控制，
    替代原来的 asyncio.Semaphore 方案。
    """
    
    _instance: Optional["TaskScheduler"] = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.max_workers = settings.MAX_CONCURRENT_TASKS
        
        # 线程池执行器
        self._executor = ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix="task_worker_"
        )
        
        # 存储正在运行的任务 future
        self._running_futures: Dict[str, Any] = {}
        
        # 任务取消标志
        self._cancelled_tasks: set = set()
        
        # 后台事件循环（用于在线程中执行异步操作）
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
        logger.info(f"TaskScheduler initialized with {self.max_workers} workers")
    
    async def start(self):
        """启动调度器"""
        self._loop = asyncio.get_event_loop()
        logger.info("TaskScheduler started")
    
    async def stop(self):
        """停止调度器"""
        logger.info("Stopping TaskScheduler...")
        
        # 取消所有正在运行的任务
        for task_id, future in list(self._running_futures.items()):
            if not future.done():
                future.cancel()
                logger.info(f"Cancelled task: {task_id}")
        
        # 关闭线程池
        self._executor.shutdown(wait=True)
        self._running_futures.clear()
        
        logger.info("TaskScheduler stopped")
    
    def submit_task(self, task_id: str, task_func: Callable, *args, **kwargs) -> bool:
        """
        提交任务到线程池
        
        Args:
            task_id: 任务ID
            task_func: 任务执行函数
            *args, **kwargs: 任务函数参数
        
        Returns:
            bool: 是否成功提交
        """
        try:
            # 提交任务到线程池
            future = self._executor.submit(
                self._run_task_wrapper,
                task_id,
                task_func,
                *args,
                **kwargs
            )
            
            self._running_futures[task_id] = future
            
            # 添加完成回调
            future.add_done_callback(
                lambda f, tid=task_id: self._on_task_complete(tid, f)
            )
            
            logger.info(f"Task {task_id} submitted to thread pool")
            return True
            
        except Exception as e:
            logger.error(f"Failed to submit task {task_id}: {e}")
            return False
    
    def _run_task_wrapper(self, task_id: str, task_func: Callable, *args, **kwargs):
        """
        任务包装器（在线程中执行）
        
        注意：这个方法在线程中执行，需要使用新的数据库会话
        """
        # 检查任务是否被取消
        if task_id in self._cancelled_tasks:
            logger.info(f"Task {task_id} was cancelled before execution")
            return None
        
        start_time = time.time()
        
        try:
            # 在线程中运行异步任务
            result = asyncio.run(self._execute_task_async(
                task_id, task_func, start_time, *args, **kwargs
            ))
            return result
            
        except Exception as e:
            logger.error(f"Task {task_id} execution failed: {e}")
            # 更新任务状态为失败
            asyncio.run(self._update_task_failed(task_id, str(e), start_time))
            raise
    
    async def _execute_task_async(
        self, 
        task_id: str, 
        task_func: Callable, 
        start_time: float,
        *args, 
        **kwargs
    ):
        """异步执行任务"""
        async with AsyncSessionLocal() as session:
            try:
                # 更新任务状态为运行中
                await self._update_task_running(session, task_id, start_time)
                
                # 执行任务函数
                if asyncio.iscoroutinefunction(task_func):
                    result = await task_func(*args, **kwargs)
                else:
                    result = task_func(*args, **kwargs)
                
                # 检查任务是否被取消
                if task_id in self._cancelled_tasks:
                    await self._update_task_cancelled(session, task_id)
                    return None
                
                # 更新任务状态为完成
                execution_time = time.time() - start_time
                await self._update_task_completed(session, task_id, result, execution_time)
                
                logger.info(f"Task {task_id} completed in {execution_time:.2f}s")
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                await self._update_task_failed(session, task_id, str(e), execution_time)
                raise
            finally:
                await session.close()
    
    async def _update_task_running(self, session: AsyncSession, task_id: str, start_time: float):
        """更新任务为运行状态"""
        from sqlalchemy import select
        
        result = await session.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        
        if task:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.utcnow()
            await session.commit()
    
    async def _update_task_completed(
        self, 
        session: AsyncSession, 
        task_id: str, 
        result: Any, 
        execution_time: float
    ):
        """更新任务为完成状态"""
        from sqlalchemy import select
        
        result_query = await session.execute(select(Task).where(Task.id == task_id))
        task = result_query.scalar_one_or_none()
        
        if task:
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            task.execution_time = execution_time
            task.result = {"data": result} if result is not None else {}
            await session.commit()
    
    async def _update_task_failed(
        self, 
        session_or_task_id: Any, 
        task_id_or_error: str, 
        error_or_start_time: str = None,
        execution_time: float = None
    ):
        """更新任务为失败状态"""
        from sqlalchemy import select
        
        # 处理不同参数签名
        if isinstance(session_or_task_id, AsyncSession):
            session = session_or_task_id
            task_id = task_id_or_error
            error_message = error_or_start_time
        else:
            # 创建新会话
            session = AsyncSessionLocal()
            task_id = session_or_task_id
            error_message = task_id_or_error
        
        try:
            result = await session.execute(select(Task).where(Task.id == task_id))
            task = result.scalar_one_or_none()
            
            if task:
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.utcnow()
                if execution_time:
                    task.execution_time = execution_time
                task.error_message = error_message
                await session.commit()
        finally:
            if not isinstance(session_or_task_id, AsyncSession):
                await session.close()
    
    async def _update_task_cancelled(self, session: AsyncSession, task_id: str):
        """更新任务为取消状态"""
        from sqlalchemy import select
        
        result = await session.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        
        if task:
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.utcnow()
            await session.commit()
            logger.info(f"Task {task_id} marked as cancelled")
    
    def _on_task_complete(self, task_id: str, future):
        """任务完成回调"""
        # 从运行中移除
        self._running_futures.pop(task_id, None)
        self._cancelled_tasks.discard(task_id)
        
        try:
            # 获取结果（触发异常如果有的话）
            future.result()
        except Exception as e:
            logger.error(f"Task {task_id} failed with exception: {e}")
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否成功取消
        """
        # 标记为取消
        self._cancelled_tasks.add(task_id)
        
        # 如果任务正在运行，取消 future
        future = self._running_futures.get(task_id)
        if future and not future.done():
            future.cancel()
            logger.info(f"Cancelled running task: {task_id}")
        
        # 更新数据库状态
        async with AsyncSessionLocal() as session:
            await self._update_task_cancelled(session, task_id)
        
        return True
    
    def get_running_count(self) -> int:
        """获取当前运行中的任务数"""
        return sum(
            1 for f in self._running_futures.values() 
            if not f.done()
        )
    
    def get_queue_size(self) -> int:
        """获取队列中的任务数（线程池内部队列）"""
        # ThreadPoolExecutor 不直接暴露队列大小
        # 这里返回已提交但未完成的任务数
        return len(self._running_futures)


# 全局调度器实例
task_scheduler = TaskScheduler()
