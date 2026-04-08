"""任务调度器模块."""

import asyncio
from datetime import datetime
from typing import Any, Callable, Coroutine, Optional, Union

from app.core.config import settings
from app.core.logging import get_logger
from app.models.task import Task, TaskStatus

logger = get_logger("scheduler")


class TaskScheduler:
    """任务调度器 - 使用 asyncio.Semaphore 实现并发控制."""
    
    _instance = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        """单例模式."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化调度器."""
        if self._initialized:
            return
        
        self._initialized = True
        self._semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_TASKS)
        self._running_tasks: dict[str, asyncio.Task] = {}
        self._task_handlers: dict[str, Callable[..., Coroutine]] = {}
        self._shutdown_event = asyncio.Event()
        
        logger.info(
            f"TaskScheduler initialized with max_concurrent={settings.MAX_CONCURRENT_TASKS}"
        )
    
    def register_handler(
        self, 
        task_type: str, 
        handler: Callable[..., Coroutine]
    ) -> None:
        """注册任务处理器."""
        self._task_handlers[task_type] = handler
        logger.info(f"Registered handler for task type: {task_type}")
    
    async def submit_task(
        self, 
        task: Task,
        handler: Optional[Callable[..., Coroutine]] = None
    ) -> None:
        """提交任务到调度器."""
        if task.id in self._running_tasks:
            logger.warning(f"Task {task.id} is already running")
            return
        
        # 创建异步任务
        asyncio_task = asyncio.create_task(
            self._execute_task(task, handler),
            name=f"task_{task.id}"
        )
        self._running_tasks[task.id] = asyncio_task
        
        # 添加完成回调
        asyncio_task.add_done_callback(
            lambda t: self._running_tasks.pop(task.id, None)
        )
        
        logger.info(f"Task {task.id} submitted to scheduler")
    
    async def _execute_task(
        self, 
        task: Task,
        handler: Optional[Callable[..., Coroutine]] = None
    ) -> None:
        """执行任务（受信号量控制）."""
        from app.services.task_service import TaskService
        
        async with self._semaphore:
            if self._shutdown_event.is_set():
                logger.info(f"Task {task.id} cancelled due to shutdown")
                return
            
            task_service = TaskService()
            start_time = datetime.utcnow()
            
            try:
                # 更新任务状态为运行中
                await task_service.update_task_status(
                    task.id, 
                    TaskStatus.RUNNING,
                    started_at=start_time
                )
                
                logger.info(f"Task {task.id} started execution")
                
                # 获取任务处理器
                if handler is None:
                    handler = self._task_handlers.get(
                        task.task_type, 
                        self._default_handler
                    )
                
                # 执行任务
                result = await handler(task)
                
                # 计算执行时间
                end_time = datetime.utcnow()
                execution_time = (end_time - start_time).total_seconds()
                
                # 更新任务为完成状态
                await task_service.complete_task(
                    task.id,
                    result=result,
                    completed_at=end_time,
                    execution_time=execution_time
                )
                
                logger.info(
                    f"Task {task.id} completed successfully in {execution_time:.2f}s"
                )
                
            except asyncio.CancelledError:
                logger.info(f"Task {task.id} was cancelled")
                await task_service.update_task_status(
                    task.id,
                    TaskStatus.CANCELLED,
                    error_message="Task was cancelled"
                )
                raise
                
            except Exception as e:
                end_time = datetime.utcnow()
                execution_time = (end_time - start_time).total_seconds()
                
                logger.error(f"Task {task.id} failed: {e}")
                await task_service.fail_task(
                    task.id,
                    error_message=str(e),
                    completed_at=end_time,
                    execution_time=execution_time
                )
    
    async def _default_handler(self, task: Task) -> dict:
        """默认任务处理器."""
        logger.info(f"Executing default handler for task {task.id}")
        
        # 模拟任务执行
        await asyncio.sleep(2)
        
        return {
            "task_id": task.id,
            "task_name": task.name,
            "executed_at": datetime.utcnow().isoformat(),
            "message": "Task executed successfully with default handler"
        }
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消正在执行的任务."""
        if task_id not in self._running_tasks:
            return False
        
        asyncio_task = self._running_tasks[task_id]
        asyncio_task.cancel()
        
        try:
            await asyncio_task
        except asyncio.CancelledError:
            pass
        
        logger.info(f"Task {task_id} cancelled")
        return True
    
    async def shutdown(self) -> None:
        """优雅关闭调度器."""
        logger.info("Shutting down TaskScheduler...")
        self._shutdown_event.set()
        
        # 取消所有正在运行的任务
        if self._running_tasks:
            logger.info(f"Cancelling {len(self._running_tasks)} running tasks...")
            for task_id, asyncio_task in list(self._running_tasks.items()):
                asyncio_task.cancel()
            
            # 等待所有任务完成
            await asyncio.gather(
                *self._running_tasks.values(), 
                return_exceptions=True
            )
        
        logger.info("TaskScheduler shutdown complete")
    
    def get_running_count(self) -> int:
        """获取当前运行中的任务数量."""
        return len(self._running_tasks)
    
    def get_queue_size(self) -> int:
        """获取等待队列大小（信号量等待者数量）."""
        return max(
            0, 
            settings.MAX_CONCURRENT_TASKS - self._semaphore._value
        )


# 全局调度器实例
task_scheduler = TaskScheduler()
