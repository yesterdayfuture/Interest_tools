"""任务工作进程 - 在独立进程中执行任务."""

import multiprocessing as mp
import time
import traceback
from datetime import datetime
from typing import Any, Dict, Optional

from app.core.logging import get_logger
from app.core.process_config import process_settings

logger = get_logger("worker")


class TaskWorker:
    """任务工作进程类."""

    def __init__(
        self,
        worker_id: str,
        task_queue: mp.Queue,
        result_queue: mp.Queue,
        shutdown_event: mp.Event,
    ):
        """初始化工作进程.

        Args:
            worker_id: 工作进程唯一标识
            task_queue: 任务队列
            result_queue: 结果队列
            shutdown_event: 关闭事件
        """
        self.worker_id = worker_id
        self.task_queue = task_queue
        self.result_queue = result_queue
        self.shutdown_event = shutdown_event
        self.tasks_processed = 0
        self.max_tasks = process_settings.WORKER_MAX_TASKS_PER_CHILD

    def run(self) -> None:
        """运行工作进程主循环."""
        logger.info(f"Worker {self.worker_id} started")

        try:
            while not self.shutdown_event.is_set():
                # 检查是否需要重启（防止内存泄漏）
                if self.tasks_processed >= self.max_tasks:
                    logger.info(
                        f"Worker {self.worker_id} reached max tasks limit, exiting"
                    )
                    break

                try:
                    # 非阻塞获取任务
                    task_data = self.task_queue.get(timeout=1)
                except Exception:
                    continue

                if task_data is None:
                    # 收到停止信号
                    logger.info(f"Worker {self.worker_id} received stop signal")
                    break

                # 处理任务
                self._process_task(task_data)

        except Exception as e:
            logger.error(f"Worker {self.worker_id} error: {e}")
            logger.error(traceback.format_exc())

        finally:
            logger.info(f"Worker {self.worker_id} stopped")

    def _process_task(self, task_data: Dict[str, Any]) -> None:
        """处理单个任务.

        Args:
            task_data: 任务数据字典
        """
        task_id = task_data.get("task_id")
        task_type = task_data.get("task_type", "default")
        payload = task_data.get("payload", {})

        # 检查任务是否已被取消
        if self._is_task_cancelled(task_id):
            logger.info(f"Task {task_id} was cancelled, skipping execution")
            self._send_cancelled_result(task_id)
            return

        logger.info(f"Worker {self.worker_id} processing task {task_id}")

        start_time = time.time()
        result_data = {
            "task_id": task_id,
            "worker_id": self.worker_id,
            "status": "running",
            "started_at": datetime.utcnow().isoformat(),
        }

        # 发送任务开始通知
        self.result_queue.put({
            "type": "task_started",
            "data": result_data,
        })

        try:
            # 获取任务处理器并执行
            handler = self._get_task_handler(task_type)
            result = handler(task_data)

            # 计算执行时间
            execution_time = time.time() - start_time

            # 发送成功结果
            self.result_queue.put({
                "type": "task_completed",
                "data": {
                    "task_id": task_id,
                    "worker_id": self.worker_id,
                    "status": "completed",
                    "result": result,
                    "execution_time": execution_time,
                    "completed_at": datetime.utcnow().isoformat(),
                },
            })

            self.tasks_processed += 1
            logger.info(
                f"Task {task_id} completed by worker {self.worker_id} "
                f"in {execution_time:.2f}s"
            )

        except Exception as e:
            execution_time = time.time() - start_time

            # 发送失败结果
            self.result_queue.put({
                "type": "task_failed",
                "data": {
                    "task_id": task_id,
                    "worker_id": self.worker_id,
                    "status": "failed",
                    "error": str(e),
                    "error_traceback": traceback.format_exc(),
                    "execution_time": execution_time,
                    "completed_at": datetime.utcnow().isoformat(),
                },
            })

            logger.error(f"Task {task_id} failed: {e}")

    def _get_task_handler(self, task_type: str) -> callable:
        """获取任务处理器.

        Args:
            task_type: 任务类型

        Returns:
            任务处理函数
        """
        # 注册内置任务处理器
        handlers = {
            "default": self._default_handler,
            "cpu_intensive": self._cpu_intensive_handler,
            "io_simulation": self._io_simulation_handler,
            "data_processing": self._data_processing_handler,
        }

        return handlers.get(task_type, self._default_handler)

    def _default_handler(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """默认任务处理器.

        Args:
            task_data: 任务数据

        Returns:
            处理结果
        """
        payload = task_data.get("payload", {})
        duration = payload.get("duration", 2)

        # 模拟任务执行
        time.sleep(duration)

        return {
            "message": "Task executed successfully",
            "task_name": task_data.get("name"),
            "processed_by": self.worker_id,
            "duration": duration,
        }

    def _cpu_intensive_handler(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """CPU 密集型任务处理器.

        Args:
            task_data: 任务数据

        Returns:
            处理结果
        """
        payload = task_data.get("payload", {})
        iterations = payload.get("iterations", 1000000)

        # CPU 密集型计算
        result = 0
        for i in range(iterations):
            result += i * i

        return {
            "message": "CPU intensive task completed",
            "result_sum": result,
            "iterations": iterations,
            "processed_by": self.worker_id,
        }

    def _io_simulation_handler(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """IO 模拟任务处理器.

        Args:
            task_data: 任务数据

        Returns:
            处理结果
        """
        payload = task_data.get("payload", {})
        operations = payload.get("operations", 5)
        delay = payload.get("delay", 0.5)

        results = []
        for i in range(operations):
            time.sleep(delay)
            results.append(f"operation_{i}_completed")

        return {
            "message": "IO simulation task completed",
            "operations_completed": operations,
            "results": results,
            "processed_by": self.worker_id,
        }

    def _data_processing_handler(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """数据处理任务处理器.

        Args:
            task_data: 任务数据

        Returns:
            处理结果
        """
        payload = task_data.get("payload", {})
        data_size = payload.get("data_size", 1000)

        # 模拟数据处理
        data = list(range(data_size))
        processed = [x * 2 for x in data]
        total = sum(processed)
        average = total / len(processed) if processed else 0

        return {
            "message": "Data processing task completed",
            "data_size": data_size,
            "total": total,
            "average": average,
            "processed_by": self.worker_id,
        }

    def _is_task_cancelled(self, task_id: str) -> bool:
        """检查任务是否已被取消.

        通过检查任务队列中是否有取消指令来判断.

        Args:
            task_id: 任务ID

        Returns:
            是否已取消
        """
        # 非阻塞检查队列中是否有取消指令
        cancelled = False
        temp_items = []

        while True:
            try:
                item = self.task_queue.get_nowait()
                if item is None:
                    break

                # 检查是否是取消指令
                if isinstance(item, dict) and item.get("type") == "cancel_task":
                    if item.get("task_id") == task_id:
                        cancelled = True
                        logger.info(f"Found cancel signal for task {task_id}")
                        continue  # 消费掉这个取消指令

                # 其他任务放回临时列表
                temp_items.append(item)
            except Exception:
                break

        # 将非取消指令的任务放回队列
        for item in temp_items:
            try:
                self.task_queue.put(item)
            except Exception:
                pass

        return cancelled

    def _send_cancelled_result(self, task_id: str) -> None:
        """发送任务取消结果.

        Args:
            task_id: 任务ID
        """
        self.result_queue.put({
            "type": "task_failed",
            "data": {
                "task_id": task_id,
                "worker_id": self.worker_id,
                "status": "cancelled",
                "error": "Task was cancelled before execution",
                "execution_time": 0,
                "completed_at": datetime.utcnow().isoformat(),
            },
        })
