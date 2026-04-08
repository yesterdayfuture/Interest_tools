"""日志配置模块."""

import logging
import sys
from typing import Any

from app.core.config import settings


def setup_logging() -> logging.Logger:
    """配置应用日志."""
    
    # 创建根日志记录器
    logger = logging.getLogger("task_scheduler")
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # 清除现有处理器
    logger.handlers.clear()
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # 设置日志格式
    formatter = logging.Formatter(settings.LOG_FORMAT)
    console_handler.setFormatter(formatter)
    
    # 添加处理器
    logger.addHandler(console_handler)
    
    # 配置第三方库日志级别
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """获取命名日志记录器."""
    return logging.getLogger(f"task_scheduler.{name}")


# 全局日志实例
logger = setup_logging()
