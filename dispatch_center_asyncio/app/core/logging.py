"""
日志配置模块

该模块提供统一的日志配置和管理功能，支持结构化日志输出。
所有模块应通过 get_logger 函数获取日志器实例，确保日志格式一致。
"""

import logging
import sys
from typing import Any, Dict

from app.core.config import get_settings


def setup_logging() -> None:
    """
    配置应用日志系统
    
    初始化 Python 标准日志库，设置日志级别、格式和输出处理器。
    同时降低第三方库的日志级别，减少不必要的日志输出。
    
    配置项从 Settings 中读取：
        - log_level: 日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL）
        - log_format: 日志格式字符串
    
    Note:
        该函数应在应用启动时调用一次，通常在 main.py 中调用。
        重复调用会重新配置日志系统，可能导致日志重复输出。
    
    Example:
        >>> from app.core.logging import setup_logging
        >>> setup_logging()
        >>> # 后续代码可以使用日志功能
    """
    # 从配置中读取日志设置
    settings = get_settings()
    
    # 配置根日志器
    # level: 设置日志级别，低于该级别的日志将被忽略
    # format: 设置日志输出格式
    # handlers: 设置日志输出目标，这里输出到标准输出
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format=settings.log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )

    # 降低第三方库的日志级别，减少噪音
    # SQLAlchemy 的引擎日志在生产环境通常不需要
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    # Uvicorn 的访问日志在调试时可能过于频繁
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志器实例
    
    建议使用当前模块的 __name__ 作为日志器名称，这样可以清楚地知道日志来源。
    例如：get_logger(__name__)
    
    Args:
        name: 日志器名称，通常使用模块的 __name__
        
    Returns:
        logging.Logger: 配置好的日志器实例
        
    Example:
        >>> from app.core.logging import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("这是一条信息日志")
        >>> logger.error("这是一条错误日志")
    """
    return logging.getLogger(name)
