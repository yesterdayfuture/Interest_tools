"""
自定义异常模块
"""


class TaskSchedulerException(Exception):
    """任务调度基础异常"""
    pass


class TaskNotFoundException(TaskSchedulerException):
    """任务不存在异常"""
    pass


class TaskAlreadyExistsException(TaskSchedulerException):
    """任务已存在异常"""
    pass


class TaskInvalidStateException(TaskSchedulerException):
    """任务状态无效异常"""
    pass


class TaskExecutionException(TaskSchedulerException):
    """任务执行异常"""
    pass
