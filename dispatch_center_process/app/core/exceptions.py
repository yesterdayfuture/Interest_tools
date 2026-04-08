"""自定义异常模块."""

from typing import Any, Optional


class TaskSchedulerException(Exception):
    """任务调度器基础异常."""
    
    def __init__(
        self,
        message: str = "Task scheduler error",
        code: str = "TASK_ERROR",
        details: Optional[dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class TaskNotFoundException(TaskSchedulerException):
    """任务不存在异常."""
    
    def __init__(self, task_id: str):
        super().__init__(
            message=f"Task not found: {task_id}",
            code="TASK_NOT_FOUND",
            details={"task_id": task_id}
        )


class TaskInvalidStatusException(TaskSchedulerException):
    """任务状态无效异常."""
    
    def __init__(self, task_id: str, current_status: str, expected_status: str):
        super().__init__(
            message=f"Task {task_id} has invalid status: {current_status}, expected: {expected_status}",
            code="TASK_INVALID_STATUS",
            details={
                "task_id": task_id,
                "current_status": current_status,
                "expected_status": expected_status
            }
        )


class TaskExecutionException(TaskSchedulerException):
    """任务执行异常."""
    
    def __init__(self, task_id: str, reason: str):
        super().__init__(
            message=f"Task execution failed: {reason}",
            code="TASK_EXECUTION_FAILED",
            details={"task_id": task_id, "reason": reason}
        )


class TaskAlreadyExistsException(TaskSchedulerException):
    """任务已存在异常."""
    
    def __init__(self, task_id: str):
        super().__init__(
            message=f"Task already exists: {task_id}",
            code="TASK_ALREADY_EXISTS",
            details={"task_id": task_id}
        )


class ValidationException(TaskSchedulerException):
    """数据验证异常."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details={"field": field} if field else {}
        )


class DatabaseException(TaskSchedulerException):
    """数据库操作异常."""
    
    def __init__(self, message: str, operation: Optional[str] = None):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            details={"operation": operation} if operation else {}
        )
