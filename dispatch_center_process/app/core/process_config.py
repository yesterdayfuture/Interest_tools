"""多进程调度中心配置模块."""

from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings


class ProcessSettings(BaseSettings):
    """多进程调度配置类."""

    # 进程池配置
    WORKER_COUNT: int = 4
    WORKER_MAX_TASKS_PER_CHILD: int = 100

    # 任务队列配置
    TASK_QUEUE_MAX_SIZE: int = 1000
    RESULT_QUEUE_MAX_SIZE: int = 1000

    # 心跳配置
    HEARTBEAT_INTERVAL: int = 5
    WORKER_TIMEOUT: int = 30

    # 进程通信配置
    MANAGER_AUTH_KEY: str = "task-scheduler-secret-key"
    MANAGER_ADDRESS: str = "127.0.0.1"
    MANAGER_PORT: int = 50000

    # 任务执行配置
    TASK_TIMEOUT_SECONDS: int = 300
    MAX_RETRY_COUNT: int = 3

    # 监控配置
    ENABLE_METRICS: bool = True
    METRICS_INTERVAL: int = 10

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_process_settings() -> ProcessSettings:
    """获取进程配置（单例模式）."""
    return ProcessSettings()


process_settings = get_process_settings()
