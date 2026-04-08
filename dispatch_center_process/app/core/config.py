"""应用配置模块."""

from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置类."""
    
    # 应用信息
    APP_NAME: str = "Task Scheduler Center"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "高性能任务调度系统"
    
    # API 配置
    API_V1_PREFIX: str = "/api/v1"
    API_VERSION: str = "v1"
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    
    # 数据库配置
    DATABASE_URL: str = "sqlite+aiosqlite:///./task_scheduler.db"
    DATABASE_ECHO: bool = False
    
    # 任务调度配置
    MAX_CONCURRENT_TASKS: int = 10
    TASK_TIMEOUT_SECONDS: int = 300
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # CORS 配置
    CORS_ORIGINS: List[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取应用配置（单例模式）."""
    return Settings()


settings = get_settings()
