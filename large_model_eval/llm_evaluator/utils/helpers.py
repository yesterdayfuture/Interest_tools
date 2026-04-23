"""
工具函数模块

提供通用的辅助功能，包括日志设置、配置加载、结果保存等
"""

import os
import json
import yaml
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# 尝试导入loguru，如不可用则使用标准库logging
try:
    from loguru import logger
    HAS_LOGURU = True
except ImportError:
    HAS_LOGURU = False
    logger = logging.getLogger(__name__)


def setup_logging(
    log_file: str = "logs/llm_evaluator.log",
    level: str = "INFO",
    rotation: str = "10 MB"
) -> None:
    """
    设置日志配置
    
    Args:
        log_file: 日志文件路径
        level: 日志级别
        rotation: 日志轮转大小
    """
    # 创建日志目录
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    if HAS_LOGURU:
        # 配置loguru
        logger.remove()  # 移除默认处理器
        
        # 添加控制台输出
        logger.add(
            sink=lambda msg: print(msg, end=""),
            level=level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                   "<level>{level: <8}</level> | "
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                   "<level>{message}</level>"
        )
        
        # 添加文件输出
        logger.add(
            log_file,
            rotation=rotation,
            level=level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            encoding="utf-8"
        )
        
        logger.info(f"日志已配置，级别: {level}，文件: {log_file}")
    else:
        # 使用标准库logging，支持日志轮转
        from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
        
        # 解析rotation参数（支持 "10 MB" 或 "1 day" 格式）
        rotation_parts = rotation.lower().split()
        if len(rotation_parts) == 2 and rotation_parts[1] in ('mb', 'gb', 'kb'):
            # 按大小轮转
            size_map = {'kb': 1024, 'mb': 1024**2, 'gb': 1024**3}
            max_bytes = int(rotation_parts[0]) * size_map[rotation_parts[1]]
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=5,
                encoding="utf-8"
            )
        elif len(rotation_parts) == 2 and rotation_parts[1] in ('day', 'days', 'hour', 'hours', 'minute', 'minutes'):
            # 按时间轮转
            interval = int(rotation_parts[0])
            when_map = {
                'minute': 'M', 'minutes': 'M',
                'hour': 'H', 'hours': 'H',
                'day': 'D', 'days': 'D'
            }
            file_handler = TimedRotatingFileHandler(
                log_file,
                when=when_map.get(rotation_parts[1], 'D'),
                interval=interval,
                backupCount=5,
                encoding="utf-8"
            )
        else:
            # 默认按10MB轮转
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8"
            )
        
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
        )
        file_handler.setFormatter(formatter)
        
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        # 配置根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, level.upper()))
        root_logger.handlers = []  # 清除现有处理器
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
        logger.info(f"日志已配置（标准库），级别: {level}，文件: {log_file}，轮转: {rotation}")


def load_yaml_config(config_path: str) -> Dict[str, Any]:
    """
    加载YAML配置文件
    
    Args:
        config_path: 配置文件路径
    
    Returns:
        Dict: 配置字典
    
    Raises:
        FileNotFoundError: 配置文件不存在
        yaml.YAMLError: YAML解析错误
    """
    path = Path(config_path)
    
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    logger.info(f"已加载配置文件: {config_path}")
    return config or {}


def save_json_results(
    data: Dict[str, Any],
    output_dir: str,
    filename: Optional[str] = None
) -> str:
    """
    保存结果为JSON文件
    
    Args:
        data: 要保存的数据
        output_dir: 输出目录
        filename: 文件名，默认使用时间戳
    
    Returns:
        str: 保存的文件路径
    """
    # 创建输出目录
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 生成文件名
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"result_{timestamp}.json"
    
    file_path = output_path / filename
    
    # 保存文件
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"结果已保存: {file_path}")
    return str(file_path)


def load_json_results(file_path: str) -> Dict[str, Any]:
    """
    从JSON文件加载结果
    
    Args:
        file_path: JSON文件路径
    
    Returns:
        Dict: 加载的数据
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"结果文件不存在: {file_path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data


def format_metrics(metrics_dict: Dict[str, float], precision: int = 4) -> Dict[str, str]:
    """
    格式化指标数值
    
    Args:
        metrics_dict: 指标字典
        precision: 小数位数
    
    Returns:
        Dict: 格式化后的指标字典
    """
    return {
        k: f"{v:.{precision}f}" if isinstance(v, float) else str(v)
        for k, v in metrics_dict.items()
    }


def ensure_dir(path: str) -> Path:
    """
    确保目录存在
    
    Args:
        path: 目录路径
    
    Returns:
        Path: 目录Path对象
    """
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def get_project_root() -> Path:
    """
    获取项目根目录
    
    Returns:
        Path: 项目根目录
    """
    return Path(__file__).parent.parent.parent


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除非法字符
    
    Args:
        filename: 原始文件名
    
    Returns:
        str: 清理后的文件名
    """
    import re
    # 移除非法字符
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # 移除首尾空格和点
    sanitized = sanitized.strip(' .')
    # 限制长度
    if len(sanitized) > 200:
        sanitized = sanitized[:200]
    return sanitized or "unnamed"


def calculate_confidence_interval(
    values: list,
    confidence: float = 0.95
) -> tuple:
    """
    计算置信区间
    
    Args:
        values: 数值列表
        confidence: 置信水平
    
    Returns:
        tuple: (下界, 上界)
    """
    import statistics
    import scipy.stats as stats
    
    if len(values) < 2:
        return (0.0, 0.0)
    
    mean = statistics.mean(values)
    std_err = stats.sem(values)
    interval = std_err * stats.t.ppf((1 + confidence) / 2, len(values) - 1)
    
    return (mean - interval, mean + interval)


def chunk_list(lst: list, chunk_size: int) -> list:
    """
    将列表分块
    
    Args:
        lst: 原始列表
        chunk_size: 块大小
    
    Returns:
        list: 分块后的列表
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def merge_dicts(*dicts: Dict) -> Dict:
    """
    合并多个字典
    
    Args:
        *dicts: 要合并的字典
    
    Returns:
        Dict: 合并后的字典
    """
    result = {}
    for d in dicts:
        result.update(d)
    return result


def get_env_or_default(key: str, default: Any = None) -> Any:
    """
    获取环境变量值或使用默认值
    
    Args:
        key: 环境变量名
        default: 默认值
    
    Returns:
        Any: 环境变量值或默认值
    """
    return os.getenv(key, default)


def timer_decorator(func):
    """
    计时装饰器
    
    用于测量函数执行时间
    """
    import functools
    import time
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed = end_time - start_time
        logger.info(f"函数 {func.__name__} 执行耗时: {elapsed:.4f}秒")
        return result
    
    return wrapper


class ProgressTracker:
    """
    进度跟踪器
    
    用于跟踪长时间运行的任务进度
    """
    
    def __init__(self, total: int, description: str = "Processing"):
        """
        初始化进度跟踪器
        
        Args:
            total: 总任务数
            description: 任务描述
        """
        self.total = total
        self.current = 0
        self.description = description
        self.start_time = datetime.now()
    
    def update(self, increment: int = 1, message: str = ""):
        """
        更新进度
        
        Args:
            increment: 增量
            message: 进度消息
        """
        self.current += increment
        percentage = (self.current / self.total * 100) if self.total > 0 else 0
        
        elapsed = (datetime.now() - self.start_time).total_seconds()
        rate = self.current / elapsed if elapsed > 0 else 0
        
        status = f"{self.description}: {self.current}/{self.total} ({percentage:.1f}%)"
        if message:
            status += f" - {message}"
        status += f" [{rate:.2f} items/s]"
        
        logger.info(status)
    
    def finish(self):
        """完成跟踪"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        logger.info(f"{self.description} 完成！总耗时: {elapsed:.2f}秒")


def print_table(data: list, headers: list, title: str = ""):
    """
    打印表格
    
    Args:
        data: 表格数据（二维列表）
        headers: 表头
        title: 表格标题
    """
    if title:
        print(f"\n{title}")
        print("=" * 60)
    
    # 计算列宽
    col_widths = [len(h) for h in headers]
    for row in data:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # 打印表头
    header_line = " | ".join(h.ljust(w) for h, w in zip(headers, col_widths))
    print(header_line)
    print("-" * len(header_line))
    
    # 打印数据
    for row in data:
        row_line = " | ".join(str(cell).ljust(w) for cell, w in zip(row, col_widths))
        print(row_line)
    
    print()
