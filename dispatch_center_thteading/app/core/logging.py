"""
日志配置模块
"""
import logging
import sys
from app.core.config import settings


def setup_logging() -> logging.Logger:
    """配置日志"""
    logger = logging.getLogger("task_scheduler")
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # 清除已有处理器
    logger.handlers.clear()
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # 格式化
    formatter = logging.Formatter(settings.LOG_FORMAT)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    return logger


# 全局日志实例
logger = setup_logging()
