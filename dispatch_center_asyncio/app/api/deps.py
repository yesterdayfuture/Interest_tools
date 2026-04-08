"""
API 依赖注入模块

该模块定义了 FastAPI 依赖注入系统使用的依赖函数和类型注解。
通过依赖注入实现：
1. 数据库会话管理（每个请求一个会话）
2. 服务层实例化
3. 依赖项的自动解析和生命周期管理

使用 Annotated 类型注解（Python 3.9+）简化依赖声明。
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.db.session import get_db
from app.services.task_service import TaskService


# ==================== 数据库会话依赖 ====================
# 使用 Annotated 定义带依赖的类型别名
# DbSession 类型会在被使用时自动调用 get_db() 获取数据库会话
DbSession = Annotated[AsyncSession, Depends(get_db)]
"""
数据库会话依赖类型

使用方式：
    >>> async def my_endpoint(db: DbSession):
    ...     # db 会自动注入 AsyncSession 实例
    ...     result = await db.execute(query)

等价于：
    >>> async def my_endpoint(db: AsyncSession = Depends(get_db)):
    ...     result = await db.execute(query)
"""


# ==================== 服务层依赖 ====================
async def get_task_service(db: DbSession) -> TaskService:
    """
    获取任务服务实例
    
    工厂函数，创建 TaskService 实例并注入数据库会话。
    作为依赖使用，确保每个请求都有独立的服务实例。
    
    Args:
        db: 数据库会话，由 DbSession 依赖自动注入
        
    Returns:
        TaskService: 配置好的任务服务实例
        
    Example:
        >>> TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
        >>> 
        >>> @router.get("/tasks")
        ... async def list_tasks(service: TaskServiceDep):
        ...     return await service.list_tasks()
    """
    return TaskService(db)


# 定义带依赖的任务服务类型别名
TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
"""
任务服务依赖类型

使用方式：
    >>> @router.get("/tasks/{task_id}")
    ... async def get_task(service: TaskServiceDep, task_id: str):
    ...     return await service.get_task_by_id(task_id)
"""
