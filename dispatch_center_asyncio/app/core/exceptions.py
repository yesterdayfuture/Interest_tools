"""
自定义异常模块

该模块定义了应用中使用的所有业务异常类。
所有业务异常都继承自 AppException，便于统一处理和转换为 HTTP 响应。

异常层次结构：
    HTTPException (FastAPI)
        └── AppException (应用异常基类)
                ├── TaskNotFoundException (任务不存在)
                ├── TaskCannotBeUpdatedException (任务无法更新)
                ├── TaskCannotBeDeletedException (任务无法删除)
                ├── TaskCannotBeCancelledException (任务无法取消)
                └── TaskSubmissionException (任务提交失败)
"""

from fastapi import HTTPException, status


class AppException(HTTPException):
    """
    应用异常基类
    
    所有业务异常的基类，继承自 FastAPI 的 HTTPException。
    使用此类可以统一处理业务异常，自动转换为 HTTP 错误响应。
    
    Attributes:
        status_code: HTTP 状态码
        detail: 错误详情信息
        headers: 可选的响应头
        
    Example:
        >>> raise AppException(
        ...     status_code=status.HTTP_400_BAD_REQUEST,
        ...     detail="Invalid request parameters"
        ... )
    """
    
    def __init__(self, status_code: int, detail: str, headers: dict = None):
        """
        初始化应用异常
        
        Args:
            status_code: HTTP 状态码，如 404、400、500 等
            detail: 错误详情，会被包含在响应体中
            headers: 可选的响应头字典
        """
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class TaskNotFoundException(AppException):
    """
    任务不存在异常
    
    当根据 task_id 查询不到任务时抛出，返回 404 状态码。
    
    Args:
        task_id: 查询的任务ID，用于构造错误信息
        
    Example:
        >>> raise TaskNotFoundException("abc-123")
        # 响应: {"detail": "Task with ID abc-123 not found"}
    """
    
    def __init__(self, task_id: str):
        """
        初始化任务不存在异常
        
        Args:
            task_id: 未找到的任务ID
        """
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found"
        )


class TaskCannotBeUpdatedException(AppException):
    """
    任务无法更新异常
    
    当尝试更新处于运行中或已完成状态的任务时抛出。
    只有处于 pending 状态的任务才允许更新。
    
    Args:
        status: 当前任务状态
        
    Example:
        >>> raise TaskCannotBeUpdatedException("running")
        # 响应: {"detail": "Cannot update task with status: running"}
    """
    
    def __init__(self, status: str):
        """
        初始化任务无法更新异常
        
        Args:
            status: 当前任务状态，如 running、completed 等
        """
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update task with status: {status}"
        )


class TaskCannotBeDeletedException(AppException):
    """
    任务无法删除异常
    
    当尝试删除处于运行中状态的任务时抛出。
    需要先取消任务，然后才能删除。
    
    Example:
        >>> raise TaskCannotBeDeletedException()
        # 响应: {"detail": "Cannot delete a running task. Please cancel it first."}
    """
    
    def __init__(self):
        """初始化任务无法删除异常"""
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a running task. Please cancel it first."
        )


class TaskCannotBeCancelledException(AppException):
    """
    任务无法取消异常
    
    当尝试取消已经处于终态（completed/failed/cancelled）的任务时抛出。
    只有 pending 或 running 状态的任务可以取消。
    
    Args:
        status: 当前任务状态
        
    Example:
        >>> raise TaskCannotBeCancelledException("completed")
        # 响应: {"detail": "Cannot cancel task with status: completed"}
    """
    
    def __init__(self, status: str):
        """
        初始化任务无法取消异常
        
        Args:
            status: 当前任务状态
        """
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel task with status: {status}"
        )


class TaskSubmissionException(AppException):
    """
    任务提交失败异常
    
    当任务提交过程中发生错误时抛出，通常是数据库操作失败或序列化错误。
    返回 500 状态码，表示服务器内部错误。
    
    Args:
        detail: 错误详情
        
    Example:
        >>> raise TaskSubmissionException("Database connection failed")
        # 响应: {"detail": "Failed to submit task: Database connection failed"}
    """
    
    def __init__(self, detail: str):
        """
        初始化任务提交失败异常
        
        Args:
            detail: 具体的错误信息
        """
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit task: {detail}"
        )
