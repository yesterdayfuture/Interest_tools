"""进程管理器 - 负责管理工作进程的生命周期."""

import multiprocessing as mp
import signal
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from app.core.logging import get_logger
from app.core.process_config import process_settings

logger = get_logger("process_manager")


class WorkerStatus(Enum):
    """工作进程状态."""
    IDLE = "idle"
    BUSY = "busy"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class WorkerInfo:
    """工作进程信息."""
    worker_id: str
    process: mp.Process
    status: WorkerStatus = WorkerStatus.IDLE
    current_task_id: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    tasks_completed: int = 0
    tasks_failed: int = 0


class ProcessManager:
    """进程管理器 - 管理工作进程池."""

    def __init__(self):
        """初始化进程管理器."""
        self._workers: Dict[str, WorkerInfo] = {}
        self._worker_count = process_settings.WORKER_COUNT
        self._shutdown_event = mp.Event()
        self._task_queue: Optional[mp.Queue] = None
        self._result_queue: Optional[mp.Queue] = None
        self._manager: Optional[mp.managers.SyncManager] = None
        self._shared_dict: Optional[Dict] = None

    def start(self) -> None:
        """启动进程管理器和工作进程池."""
        logger.info(f"Starting ProcessManager with {self._worker_count} workers...")

        # 创建 Manager 用于进程间共享数据
        self._manager = mp.Manager()
        self._shared_dict = self._manager.dict()

        # 创建任务队列和结果队列
        self._task_queue = mp.Queue(maxsize=process_settings.TASK_QUEUE_MAX_SIZE)
        self._result_queue = mp.Queue(maxsize=process_settings.RESULT_QUEUE_MAX_SIZE)

        # 启动工作进程
        for i in range(self._worker_count):
            self._start_worker(i)

        logger.info(f"ProcessManager started with {len(self._workers)} workers")

    def _start_worker(self, index: int) -> str:
        """启动单个工作进程."""
        worker_id = f"worker-{index}-{int(time.time() * 1000)}"

        # 创建工作进程
        process = mp.Process(
            target=_worker_process_entry,
            args=(
                worker_id,
                self._task_queue,
                self._result_queue,
                self._shutdown_event,
            ),
            name=worker_id,
            daemon=False,
        )

        process.start()

        worker_info = WorkerInfo(
            worker_id=worker_id,
            process=process,
        )
        self._workers[worker_id] = worker_info

        logger.info(f"Worker {worker_id} started (PID: {process.pid})")
        return worker_id

    def stop(self) -> None:
        """停止所有工作进程."""
        logger.info("Stopping ProcessManager...")

        # 设置关闭事件
        self._shutdown_event.set()

        # 等待所有工作进程结束
        for worker_id, worker_info in list(self._workers.items()):
            worker_info.status = WorkerStatus.STOPPING

            if worker_info.process.is_alive():
                logger.info(f"Waiting for worker {worker_id} to stop...")
                worker_info.process.join(timeout=5)

                if worker_info.process.is_alive():
                    logger.warning(f"Force terminating worker {worker_id}")
                    worker_info.process.terminate()
                    worker_info.process.join(timeout=2)

            worker_info.status = WorkerStatus.STOPPED
            logger.info(f"Worker {worker_id} stopped")

        # 清空队列
        if self._task_queue:
            while not self._task_queue.empty():
                try:
                    self._task_queue.get_nowait()
                except:
                    break

        if self._result_queue:
            while not self._result_queue.empty():
                try:
                    self._result_queue.get_nowait()
                except:
                    break

        # 关闭 Manager
        if self._manager:
            self._manager.shutdown()

        self._workers.clear()
        logger.info("ProcessManager stopped")

    def get_worker_status(self) -> List[Dict[str, Any]]:
        """获取所有工作进程状态."""
        status_list = []
        for worker_id, info in self._workers.items():
            status_list.append({
                "worker_id": worker_id,
                "status": info.status.value,
                "current_task_id": info.current_task_id,
                "pid": info.process.pid if info.process else None,
                "is_alive": info.process.is_alive() if info.process else False,
                "tasks_completed": info.tasks_completed,
                "tasks_failed": info.tasks_failed,
                "started_at": info.started_at.isoformat(),
                "last_heartbeat": info.last_heartbeat.isoformat(),
            })
        return status_list

    def get_alive_worker_count(self) -> int:
        """获取存活的工作进程数量."""
        return sum(
            1 for w in self._workers.values()
            if w.process and w.process.is_alive()
        )

    def get_idle_worker_count(self) -> int:
        """获取空闲的工作进程数量."""
        return sum(
            1 for w in self._workers.values()
            if w.status == WorkerStatus.IDLE and w.process and w.process.is_alive()
        )

    def restart_worker(self, worker_id: str) -> Optional[str]:
        """重启指定的工作进程."""
        if worker_id not in self._workers:
            logger.error(f"Worker {worker_id} not found")
            return None

        old_worker = self._workers[worker_id]

        # 停止旧进程（如果还在运行）
        if old_worker.process.is_alive():
            old_worker.process.terminate()
            old_worker.process.join(timeout=2)

        # 提取索引，保持原有的 worker 编号
        try:
            # worker_id 格式: worker-{index}-{timestamp}
            index = int(worker_id.split("-")[1])
        except (IndexError, ValueError):
            # 如果解析失败，使用当前 workers 数量作为索引
            index = len(self._workers)

        # 删除旧工作进程记录
        del self._workers[worker_id]

        # 启动新进程（使用相同的索引）
        new_worker_id = self._start_worker(index)

        logger.info(f"Worker {worker_id} restarted as {new_worker_id}")
        return new_worker_id

    def update_worker_status(self, worker_id: str, status: str, task_id: Optional[str] = None) -> None:
        """更新工作进程状态（由工作进程调用）."""
        if worker_id in self._workers:
            self._workers[worker_id].status = WorkerStatus(status)
            self._workers[worker_id].current_task_id = task_id
            self._workers[worker_id].last_heartbeat = datetime.utcnow()

    def increment_worker_stats(self, worker_id: str, completed: bool = True) -> None:
        """增加工作进程统计（由工作进程调用）."""
        if worker_id in self._workers:
            if completed:
                self._workers[worker_id].tasks_completed += 1
            else:
                self._workers[worker_id].tasks_failed += 1

    @property
    def task_queue(self) -> Optional[mp.Queue]:
        """获取任务队列."""
        return self._task_queue

    @property
    def result_queue(self) -> Optional[mp.Queue]:
        """获取结果队列."""
        return self._result_queue


def _worker_process_entry(
    worker_id: str,
    task_queue: mp.Queue,
    result_queue: mp.Queue,
    shutdown_event: mp.Event,
) -> None:
    """工作进程入口函数（在子进程中运行）."""
    # 忽略 SIGINT，由父进程管理生命周期
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    from app.services.worker import TaskWorker

    worker = TaskWorker(worker_id, task_queue, result_queue, shutdown_event)
    worker.run()
