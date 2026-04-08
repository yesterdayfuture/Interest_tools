"""
应用配置模块

该模块使用 Pydantic Settings 管理应用的所有配置项，支持从环境变量加载配置。
通过 @lru_cache 装饰器确保配置实例全局唯一，避免重复创建。
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    """
    应用配置类
    
    继承自 Pydantic 的 BaseSettings，自动从环境变量读取配置。
    环境变量名与类属性名对应（不区分大小写，支持前缀）。
    
    Attributes:
        app_name: 应用名称，用于API文档和日志标识
        app_version: 应用版本号，遵循语义化版本规范
        app_description: 应用描述，显示在API文档中
        debug: 调试模式开关，影响日志级别和错误信息详细程度
        
        database_url: 数据库连接字符串，支持SQLite/MySQL/PostgreSQL
        
        max_concurrent_tasks: 任务调度器最大并发数，控制同时执行的任务数量
        task_timeout_seconds: 单个任务超时时间（秒），防止任务无限运行
        
        api_v1_prefix: API v1版本路由前缀
        api_title: API文档标题
        
        cors_origins: 允许的跨域请求来源列表
        cors_allow_credentials: 是否允许跨域请求携带凭证
        cors_allow_methods: 允许的HTTP方法列表
        cors_allow_headers: 允许的HTTP请求头列表
        
        log_level: 日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL）
        log_format: 日志输出格式字符串
    """
    
    # ==================== 应用基本信息 ====================
    app_name: str = "Task Scheduler Center"
    app_version: str = "1.0.0"
    app_description: str = "A task scheduling system with concurrent execution control"
    debug: bool = True

    # ==================== 数据库配置 ====================
    # SQLite示例: sqlite+aiosqlite:///./tasks.db
    # MySQL示例: mysql+aiomysql://user:password@localhost/dbname
    # PostgreSQL示例: postgresql+asyncpg://user:password@localhost/dbname
    database_url: str = "sqlite+aiosqlite:///./tasks.db"

    # ==================== 任务调度器配置 ====================
    max_concurrent_tasks: int = 10  # 使用信号量控制的最大并发任务数
    task_timeout_seconds: int = 5*60  # 任务执行超时时间，5分钟

    # ==================== API配置 ====================
    api_v1_prefix: str = "/api/v1"  # API版本前缀，便于后续版本迭代
    api_title: str = "Task Scheduler API"

    # ==================== CORS跨域配置 ====================
    # 生产环境应该限制具体的域名，如 ["https://example.com"]
    cors_origins: List[str] = ["*"]  # 允许所有来源（仅开发环境）
    cors_allow_credentials: bool = True  # 允许携带Cookie等凭证
    cors_allow_methods: List[str] = ["*"]  # 允许所有HTTP方法
    cors_allow_headers: List[str] = ["*"]  # 允许所有请求头

    # ==================== 日志配置 ====================
    log_level: str = "INFO"  # 日志级别
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    class Config:
        """
        Pydantic配置类
        
        Attributes:
            env_file: 环境变量文件路径，应用启动时自动加载
            case_sensitive: 环境变量名是否区分大小写
        """
        env_file = ".env"  # 从.env文件加载环境变量
        case_sensitive = False  # 环境变量名不区分大小写


@lru_cache()
def get_settings() -> Settings:
    """
    获取应用配置实例（单例模式）
    
    使用 @lru_cache 装饰器缓存配置实例，确保全局只有一个配置对象。
    这样可以避免每次导入时重复读取环境变量，提高性能。
    
    Returns:
        Settings: 应用配置实例
        
    Example:
        >>> from app.core.config import get_settings
        >>> settings = get_settings()
        >>> print(settings.app_name)
        'Task Scheduler Center'
    """
    return Settings()
