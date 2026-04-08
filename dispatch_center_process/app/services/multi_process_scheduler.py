"""多进程任务调度器 - 主调度中心."""

import asyncio
import multiprocessing as mp
import time
from datetime import datetime
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set

from app.core.logging import get_logger
from app.core.process_config import process_settings
from app.models.task import Task, TaskStatus
from app.services.process_manager import ProcessManager

logger = get_logger("multi_process_scheduler")


class MultiProcessScheduler:
    """多进程任务调度器.

    负责任务分发、结果收集、状态管理。
    使用进程池实现真正的并行执行。
    """

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
        self._process_manager = ProcessManager()
        self._running = False
        self._result_processor_task: Optional[asyncio.Task] = None
        self._monitor_task: Optional[asyncio.Task] = None

        # 任务状态跟踪
        self._pending_tasks: Dict[str, Dict[str, Any]] = {}
        self._running_task_ids: Set[str] = set()
        self._completed_tasks: Dict[str, Dict[str, Any]] = {}
        self._cancelled_tasks: Set[str] = set()  # 已取消的任务ID集合

        # 回调函数
        self._task_callbacks: Dict[str, List[Callable]] = {}

        logger.info("MultiProcessScheduler initialized")

    async def start(self) -> None:
        """启动调度器."""
        if self._running:
            logger.warning("Scheduler is already running")
            return

        logger.info("Starting MultiProcessScheduler...")

        # 启动进程管理器
        self._process_manager.start()

        self._running = True

        # 启动结果处理器
        self._result_processor_task = asyncio.create_task(
            self._process_results(),
            name="result_processor"
        )

        # 启动监控任务
        self._monitor_task = asyncio.create_task(
            self._monitor_workers(),
            name="worker_monitor"
        )

        logger.info("MultiProcessScheduler started")

    async def shutdown(self) -> None:
        """关闭调度器."""
        if not self._running:
            return

        logger.info("Shutting down MultiProcessScheduler...")

        self._running = False

        # 取消后台任务
        if self._result_processor_task:
            self._result_processor_task.cancel()
            try:
                await self._result_processor_task
            except asyncio.CancelledError:
                pass

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        # 停止进程管理器
        self._process_manager.stop()

        logger.info("MultiProcessScheduler shutdown complete")

    async def submit_task(
        self,
        task: Task,
        handler: Optional[Callable[..., Coroutine]] = None,
    ) -> bool:
        """提交任务到调度器.

        Args:
            task: 任务对象
            handler: 可选的自定义处理器

        Returns:
            是否成功提交
        """
        if not self._running:
            logger.error("Scheduler is not running")
            return False

        task_id = str(task.id)

        if task_id in self._running_task_ids or task_id in self._pending_tasks:
            logger.warning(f"Task {task_id} is already queued or running")
            return False

        # 检查任务是否已被取消
        if task_id in self._cancelled_tasks:
            logger.warning(f"Task {task_id} was cancelled, cannot submit")
            return False

        # 准备任务数据
        task_data = {
            "task_id": task_id,
            "name": task.name,
            "task_type": task.task_type,
            "priority": task.priority,
            "payload": task.payload or {},
            "submitted_at": datetime.utcnow().isoformat(),
        }

        try:
            # 添加到任务队列
            self._process_manager.task_queue.put(task_data)
            self._pending_tasks[task_id] = task_data

            logger.info(f"Task {task_id} submitted to queue")
            return True

        except Exception as e:
            logger.error(f"Failed to submit task {task_id}: {e}")
            return False

    async def cancel_task(self, task_id: str) -> bool:
        """取消任务.

        Args:
            task_id: 任务ID

        Returns:
            是否成功取消
        """
        # 检查是否在待处理队列中
        if task_id in self._pending_tasks:
            # 从待处理队列中移除
            del self._pending_tasks[task_id]
            # 添加到已取消集合，防止工作进程处理
            self._cancelled_tasks.add(task_id)
            logger.info(f"Task {task_id} cancelled from pending queue")
            return True

        # 检查是否正在运行
        if task_id in self._running_task_ids:
            # 添加到已取消集合
            self._cancelled_tasks.add(task_id)
            # 发送取消信号到任务队列，让工作进程处理
            self._process_manager.task_queue.put({
                "type": "cancel_task",
                "task_id": task_id,
            })
            logger.info(f"Cancel signal sent for running task {task_id}")
            return True

        logger.warning(f"Task {task_id} not found")
        return False

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态.

        Args:
            task_id: 任务ID

        Returns:
            任务状态信息
        """
        if task_id in self._pending_tasks:
            return {
                "task_id": task_id,
                "status": "pending",
                "data": self._pending_tasks[task_id],
            }

        if task_id in self._running_task_ids:
            return {
                "task_id": task_id,
                "status": "running",
            }

        if task_id in self._completed_tasks:
            return {
                "task_id": task_id,
                "status": "completed",
                "data": self._completed_tasks[task_id],
            }

        return None

    def get_scheduler_status(self) -> Dict[str, Any]:
        """获取调度器状态."""
        return {
            "running": self._running,
            "workers": self._process_manager.get_worker_status(),
            "pending_tasks": len(self._pending_tasks),
            "running_tasks": len(self._running_task_ids),
            "completed_tasks": len(self._completed_tasks),
            "alive_workers": self._process_manager.get_alive_worker_count(),
            "idle_workers": self._process_manager.get_idle_worker_count(),
        }

    async def _process_results(self) -> None:
        """处理结果队列（后台任务）."""
        logger.info("Result processor started")

        while self._running:
            try:
                # 非阻塞检查结果队列
                if self._process_manager.result_queue.empty():
                    await asyncio.sleep(0.1)
                    continue

                result = self._process_manager.result_queue.get_nowait()
                await self._handle_result(result)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing result: {e}")
                await asyncio.sleep(0.1)

        logger.info("Result processor stopped")

    async def _handle_result(self, result: Dict[str, Any]) -> None:
        """处理单个结果.

        Args:
            result: 结果数据
        """
        result_type = result.get("type")
        data = result.get("data", {})
        task_id = data.get("task_id")

        if result_type == "task_started":
            # 任务开始执行
            if task_id in self._pending_tasks:
                del self._pending_tasks[task_id]
            self._running_task_ids.add(task_id)

            # 更新数据库状态
            await self._update_task_status(task_id, TaskStatus.RUNNING)

            logger.info(f"Task {task_id} started execution")

        elif result_type == "task_completed":
            # 任务完成
            self._running_task_ids.discard(task_id)
            self._completed_tasks[task_id] = data

            # 更新数据库状态
            await self._complete_task(
                task_id,
                result=data.get("result"),
                execution_time=data.get("execution_time", 0),
            )

            # 触发回调
            await self._trigger_callbacks(task_id, "completed", data)

            logger.info(f"Task {task_id} completed")

        elif result_type == "task_failed":
            # 任务失败或取消
            self._running_task_ids.discard(task_id)
            self._completed_tasks[task_id] = data

            # 检查是否是取消状态
            if data.get("status") == "cancelled":
                # 更新数据库状态为取消
                await self._cancel_task_in_db(task_id)
                # 从已取消集合中移除
                self._cancelled_tasks.discard(task_id)
                logger.info(f"Task {task_id} was cancelled")
            else:
                # 更新数据库状态为失败
                await self._fail_task(
                    task_id,
                    error_message=data.get("error", "Unknown error"),
                    execution_time=data.get("execution_time", 0),
                )
                # 触发回调
                await self._trigger_callbacks(task_id, "failed", data)
                logger.error(f"Task {task_id} failed: {data.get('error')}")

    async def _update_task_status(self, task_id: str, status: TaskStatus) -> None:
        """更新任务状态到数据库."""
        try:
            from app.services.task_service import TaskService
            task_service = TaskService()
            await task_service.update_task_status(
                task_id,
                status,
                started_at=datetime.utcnow() if status == TaskStatus.RUNNING else None,
            )
        except Exception as e:
            logger.error(f"Failed to update task status: {e}")

    async def _complete_task(
        self,
        task_id: str,
        result: Any,
        execution_time: float,
    ) -> None:
        """标记任务完成."""
        try:
            from app.services.task_service import TaskService
            task_service = TaskService()
            await task_service.complete_task(
                task_id,
                result=result,
                completed_at=datetime.utcnow(),
                execution_time=execution_time,
            )
        except Exception as e:
            logger.error(f"Failed to complete task: {e}")

    async def _fail_task(
        self,
        task_id: str,
        error_message: str,
        execution_time: float,
    ) -> None:
        """标记任务失败."""
        try:
            from app.services.task_service import TaskService
            task_service = TaskService()
            await task_service.fail_task(
                task_id,
                error_message=error_message,
                completed_at=datetime.utcnow(),
                execution_time=execution_time,
            )
        except Exception as e:
            logger.error(f"Failed to fail task: {e}")

    async def _cancel_task_in_db(self, task_id: str) -> None:
        """标记任务为已取消状态."""
        try:
            from app.services.task_service import TaskService
            from app.models.task import TaskStatus
            task_service = TaskService()
            await task_service.update_task_status(
                task_id,
                TaskStatus.CANCELLED,
                error_message="Task was cancelled",
            )
        except Exception as e:
            logger.error(f"Failed to cancel task in db: {e}")

    async def _monitor_workers(self) -> None:
        """监控工作进程状态（后台任务）."""
        logger.info("Worker monitor started")

        while self._running:
            try:
                # 检查工作进程健康状态
                for worker_info in self._process_manager.get_worker_status():
                    if not worker_info.get("is_alive"):
                        worker_id = worker_info.get("worker_id")
                        logger.warning(f"Worker {worker_id} is dead, restarting...")
                        self._process_manager.restart_worker(worker_id)

                await asyncio.sleep(process_settings.HEARTBEAT_INTERVAL)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in worker monitor: {e}")
                await asyncio.sleep(1)

        logger.info("Worker monitor stopped")

    async def _trigger_callbacks(
        self,
        task_id: str,
        event: str,
        data: Dict[str, Any],
    ) -> None:
        """触发任务回调."""
        callbacks = self._task_callbacks.get(task_id, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(task_id, event, data)
                else:
                    callback(task_id, event, data)
            except Exception as e:
                logger.error(f"Callback error for task {task_id}: {e}")

    def register_callback(
        self,
        task_id: str,
        callback: Callable,
    ) -> None:
        """注册任务回调."""
        if task_id not in self._task_callbacks:
            self._task_callbacks[task_id] = []
        self._task_callbacks[task_id].append(callback)


# 全局调度器实例
multi_process_scheduler = MultiProcessScheduler()
