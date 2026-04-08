"""
任务调度器服务模块

该模块实现了任务调度系统的核心功能，负责任务的提交、执行和生命周期管理。
使用 asyncio.Semaphore 实现并发控制，确保系统资源不被耗尽。

主要组件：
- TaskScheduler: 任务调度器类，管理任务执行和并发控制
- task_scheduler: 全局调度器实例
- get_task_scheduler: 获取调度器实例的依赖函数

工作流程：
1. 提交任务 → 创建数据库记录（PENDING状态）
2. 等待信号量 → 获取执行权限
3. 更新状态 → RUNNING
4. 执行任务 → 调用处理器或默认处理
5. 更新结果 → COMPLETED/FAILED
6. 释放信号量 → 允许下一个任务执行
"""

import asyncio
import uuid
import json
from datetime import datetime
from typing import Dict, Optional, Callable, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.db.session import AsyncSessionLocal
from app.models.task import Task, TaskStatus
from app.core.logging import get_logger
from app.core.config import get_settings

# 获取日志器和配置
logger = get_logger(__name__)
settings = get_settings()


class TaskScheduler:
    """
    任务调度器类
    
    负责任务的调度、执行和并发控制。使用信号量机制限制同时执行的任务数量，
    防止系统资源被耗尽。支持自定义任务处理器，可根据任务类型路由到不同的处理逻辑。
    
    Attributes:
        max_concurrent_tasks: 最大并发任务数
        semaphore: 异步信号量，控制并发
        running_tasks: 正在运行的任务字典，task_id -> asyncio.Task
        task_handlers: 任务处理器字典，task_type -> handler_function
        _shutdown: 关闭标志，用于优雅停机
        
    Example:
        >>> scheduler = TaskScheduler(max_concurrent_tasks=10)
        >>> 
        >>> # 注册自定义处理器
        >>> async def my_handler(task_id: str, payload: dict):
        ...     await process_data(payload)
        >>> 
        >>> scheduler.register_handler("my_type", my_handler)
        >>> 
        >>> # 提交任务
        >>> task_id = await scheduler.submit_task(
        ...     name="数据处理",
        ...     task_type="my_type",
        ...     payload={"file": "data.csv"}
        ... )
    """
    
    def __init__(self, max_concurrent_tasks: int = None):
        """
        初始化任务调度器
        
        Args:
            max_concurrent_tasks: 最大并发任务数，默认从配置读取
        """
        # 从配置读取或使用传入值
        self.max_concurrent_tasks = max_concurrent_tasks or settings.max_concurrent_tasks
        
        # 创建信号量，控制并发数量
        # 信号量初始值为 max_concurrent_tasks，每次获取减少1，释放时增加1
        self.semaphore = asyncio.Semaphore(self.max_concurrent_tasks)
        
        # 存储正在运行的任务，用于取消操作
        self.running_tasks: Dict[str, asyncio.Task] = {}
        
        # 任务类型到处理器的映射
        self.task_handlers: Dict[str, Callable] = {}
        
        # 关闭标志，用于优雅停机
        self._shutdown = False

    def register_handler(self, task_type: str, handler: Callable):
        """
        注册任务类型处理器
        
        为特定任务类型注册自定义处理函数。当该类型的任务执行时，
        会调用对应的处理器而不是默认处理逻辑。
        
        Args:
            task_type: 任务类型标识符
            handler: 处理函数，签名应为 async handler(task_id: str, payload: dict)
            
        Example:
            >>> async def email_handler(task_id: str, payload: dict):
            ...     await send_email(payload["to"], payload["content"])
            >>> 
            >>> scheduler.register_handler("send_email", email_handler)
        """
        self.task_handlers[task_type] = handler
        logger.info(f"Registered handler for task type: {task_type}")

    async def submit_task(self, name: str, description: Optional[str] = None,
                         task_type: Optional[str] = None, priority: int = 0,
                         payload: Optional[Dict] = None) -> str:
        """
        提交新任务
        
        创建任务记录并启动异步执行流程。任务会立即进入 PENDING 状态，
        等待信号量可用后开始执行。
        
        Args:
            name: 任务名称，必填
            description: 任务描述，可选
            task_type: 任务类型，用于路由到对应处理器
            priority: 优先级，0-100，数值越大优先级越高
            payload: 任务负载数据，任意JSON可序列化对象
            
        Returns:
            str: 创建的任务ID（UUID格式）
            
        Raises:
            Exception: 数据库操作失败时抛出
            
        Example:
            >>> task_id = await scheduler.submit_task(
            ...     name="数据备份",
            ...     task_type="backup",
            ...     priority=10,
            ...     payload={"database": "production"}
            ... )
            >>> print(f"Task created: {task_id}")
        """
        # 生成唯一任务ID
        task_id = str(uuid.uuid4())

        # 创建数据库记录
        async with AsyncSessionLocal() as session:
            task = Task(
                task_id=task_id,
                name=name,
                description=description,
                task_type=task_type or "default",
                priority=priority,
                # 将字典序列化为JSON字符串存储
                payload=json.dumps(payload) if payload else None,
                status=TaskStatus.PENDING
            )
            session.add(task)
            await session.commit()

        # 创建异步任务执行实际逻辑
        # 不等待执行完成，立即返回 task_id
        asyncio.create_task(self._process_task_when_available(task_id))
        logger.info(f"Task submitted: {task_id}")
        return task_id

    async def _process_task_when_available(self, task_id: str):
        """
        在信号量可用时处理任务
        
        内部方法，等待信号量后执行实际任务逻辑。
        使用信号量确保并发数量受控。
        
        Args:
            task_id: 要处理的任务ID
        """
        # 创建任务执行协程，并将其添加到running_tasks字典
        # 这样可以跟踪正在执行的任务，支持取消操作
        task = asyncio.create_task(self._execute_task(task_id))
        self.running_tasks[task_id] = task
        
        try:
            # 等待任务完成
            await task
        except asyncio.CancelledError:
            # 任务被取消，记录日志
            logger.info(f"Task was cancelled: {task_id}")
            raise
        finally:
            # 任务完成或取消后，从running_tasks中移除
            # 使用pop避免KeyError（任务可能已被移除）
            self.running_tasks.pop(task_id, None)

    async def _execute_task(self, task_id: str):
        """
        执行任务的内部方法
        
        获取信号量后执行任务，更新任务状态，处理成功/失败情况。
        这是任务执行的核心逻辑。
        
        Args:
            task_id: 要执行的任务ID
        """
        # 使用信号量控制并发
        # 当信号量计数为0时，会阻塞等待其他任务释放
        async with self.semaphore:
            # 检查是否正在关闭
            if self._shutdown:
                return

            # 查询任务并更新状态为 RUNNING
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Task).where(Task.task_id == task_id)
                )
                task = result.scalar_one_or_none()

                # 任务不存在或状态不是 PENDING，跳过执行
                if not task or task.status != TaskStatus.PENDING:
                    return

                # 更新状态为 RUNNING，记录开始时间
                await session.execute(
                    update(Task)
                    .where(Task.task_id == task_id)
                    .values(
                        status=TaskStatus.RUNNING,
                        started_at=datetime.utcnow()
                    )
                )
                await session.commit()

            logger.info(f"Task started: {task_id}")

            try:
                # 执行实际的任务逻辑
                await self._run_task_logic(task_id)

                # 执行成功，更新状态为 COMPLETED
                async with AsyncSessionLocal() as session:
                    await session.execute(
                        update(Task)
                        .where(Task.task_id == task_id)
                        .values(
                            status=TaskStatus.COMPLETED,
                            completed_at=datetime.utcnow(),
                            result=json.dumps({"message": "Task completed successfully"})
                        )
                    )
                    await session.commit()
                logger.info(f"Task completed: {task_id}")

            except Exception as e:
                # 执行失败，记录错误信息
                error_msg = str(e)
                logger.error(f"Task failed: {task_id}, error: {error_msg}")

                async with AsyncSessionLocal() as session:
                    await session.execute(
                        update(Task)
                        .where(Task.task_id == task_id)
                        .values(
                            status=TaskStatus.FAILED,
                            completed_at=datetime.utcnow(),
                            error_message=error_msg
                        )
                    )
                    await session.commit()

    async def _run_task_logic(self, task_id: str):
        """
        运行任务实际业务逻辑
        
        根据任务类型查找对应的处理器并执行，如果没有找到处理器则使用默认逻辑。
        
        Args:
            task_id: 任务ID
            
        Raises:
            ValueError: 任务不存在时抛出
            Exception: 处理器执行出错时抛出
        """
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Task).where(Task.task_id == task_id)
            )
            task = result.scalar_one_or_none()

            if not task:
                raise ValueError(f"Task not found: {task_id}")

            # 获取任务类型和负载数据
            task_type = task.task_type or "default"
            # 将JSON字符串解析为字典
            payload = json.loads(task.payload) if task.payload else {}

            # 查找对应的处理器
            handler = self.task_handlers.get(task_type)

            if handler:
                # 使用自定义处理器
                await handler(task_id, payload)
            else:
                # 使用默认处理器
                await self._default_task_handler(task_id, payload)

    async def _default_task_handler(self, task_id: str, payload: Dict):
        """
        默认任务处理器
        
        当任务没有注册自定义处理器时使用。模拟一个耗时的异步操作。
        
        Args:
            task_id: 任务ID
            payload: 任务负载数据
        """
        # 模拟任务执行时间（5秒）
        await asyncio.sleep(5)
        logger.info(f"Default task handler executed for {task_id}")

    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        取消处于 PENDING 或 RUNNING 状态的任务。如果任务正在运行，
        会尝试取消对应的 asyncio.Task。
        
        Args:
            task_id: 要取消的任务ID
            
        Returns:
            bool: 取消成功返回 True，任务不存在或无法取消返回 False
            
        Example:
            >>> success = await scheduler.cancel_task("uuid-string")
            >>> if success:
            ...     print("Task cancelled")
            ... else:
            ...     print("Task not found or already finished")
        """
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Task).where(Task.task_id == task_id)
            )
            task = result.scalar_one_or_none()

            if not task:
                return False

            # 如果任务正在运行，取消对应的 asyncio.Task
            if task.status == TaskStatus.RUNNING and task_id in self.running_tasks:
                self.running_tasks[task_id].cancel()
                try:
                    await self.running_tasks[task_id]
                except asyncio.CancelledError:
                    pass
                # 不需要手动删除，_process_task_when_available的finally块会处理

            # 只有 PENDING 或 RUNNING 状态的任务可以取消
            if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                await session.execute(
                    update(Task)
                    .where(Task.task_id == task_id)
                    .values(
                        status=TaskStatus.CANCELLED,
                        completed_at=datetime.utcnow()
                    )
                )
                await session.commit()
                logger.info(f"Task cancelled: {task_id}")
                return True

            return False

    async def shutdown(self):
        """
        关闭调度器
        
        优雅地关闭调度器，取消所有正在运行的任务。
        应在应用关闭时调用。
        
        Example:
            >>> @asynccontextmanager
            ... async def lifespan(app: FastAPI):
            ...     yield
            ...     await scheduler.shutdown()  # 应用关闭时调用
        """
        self._shutdown = True
        logger.info("Shutting down task scheduler...")

        # 取消所有正在运行的任务
        for task_id, task in self.running_tasks.items():
            task.cancel()

        # 等待所有任务完成取消
        if self.running_tasks:
            await asyncio.gather(*self.running_tasks.values(), return_exceptions=True)

        logger.info("Task scheduler shutdown complete")


# ==================== 全局实例 ====================
# 创建全局调度器实例，整个应用共享
task_scheduler = TaskScheduler()


async def get_task_scheduler() -> TaskScheduler:
    """
    获取任务调度器实例
    
    用于 FastAPI 依赖注入，返回全局调度器实例。
    
    Returns:
        TaskScheduler: 全局调度器实例
    """
    return task_scheduler
