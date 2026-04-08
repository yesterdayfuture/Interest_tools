"""
任务数据模型模块

该模块定义了任务相关的数据库模型和枚举类型。
使用 SQLAlchemy 的声明式基类定义表结构，支持异步数据库操作。
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Enum as SQLEnum
from sqlalchemy.sql import func
from enum import Enum

from app.db.base import Base


class TaskStatus(str, Enum):
    """
    任务状态枚举类
    
    定义任务在其生命周期中可能处于的各种状态。
    使用 str 和 Enum 混合继承，便于序列化和数据库存储。
    
    Attributes:
        PENDING: 待执行状态，任务已创建但尚未开始执行
        RUNNING: 执行中状态，任务正在被执行
        COMPLETED: 已完成状态，任务成功执行完毕
        FAILED: 失败状态，任务执行过程中发生错误
        CANCELLED: 已取消状态，任务被手动取消
        
    Example:
        >>> task.status = TaskStatus.PENDING
        >>> if task.status == TaskStatus.COMPLETED:
        ...     print("任务已完成")
    """
    PENDING = "pending"       # 任务已创建，等待执行
    RUNNING = "running"       # 任务正在执行
    COMPLETED = "completed"   # 任务成功完成
    FAILED = "failed"         # 任务执行失败
    CANCELLED = "cancelled"   # 任务被取消


class Task(Base):
    """
    任务数据模型
    
    定义任务在数据库中的表结构和字段。
    每个实例代表一个具体的任务，包含任务的完整生命周期信息。
    
    Attributes:
        id: 数据库主键，自增整数
        task_id: 业务唯一标识符，UUID格式，对外暴露
        name: 任务名称，用于显示和搜索
        description: 任务描述，可选的详细说明
        status: 任务当前状态，使用 TaskStatus 枚举
        task_type: 任务类型，用于区分不同种类的任务
        priority: 任务优先级，数值越大优先级越高（0-100）
        payload: 任务负载数据，JSON格式字符串存储
        result: 任务执行结果，JSON格式字符串
        error_message: 错误信息，任务失败时记录
        created_at: 创建时间，自动设置
        updated_at: 更新时间，自动更新
        started_at: 开始执行时间，任务开始执行时设置
        completed_at: 完成时间，任务结束时设置
        
    Table Name:
        tasks
        
    Indexes:
        - id: 主键索引
        - task_id: 唯一索引
        - name: 普通索引，支持模糊查询
        - status: 普通索引，状态过滤
        - task_type: 普通索引，类型过滤
        - priority: 普通索引，优先级排序
        - created_at: 普通索引，时间范围查询
        
    Example:
        >>> task = Task(
        ...     task_id="uuid-string",
        ...     name="数据处理任务",
        ...     status=TaskStatus.PENDING,
        ...     priority=5
        ... )
    """
    
    # 表名
    __tablename__ = "tasks"

    # ==================== 主键和标识字段 ====================
    # 数据库自增主键，内部使用
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # 业务唯一标识符，UUID格式
    # 对外暴露的ID，避免暴露数据库自增ID
    task_id = Column(String(64), unique=True, index=True, nullable=False)
    
    # ==================== 任务基本信息 ====================
    # 任务名称，必填，最大255字符
    # 用于显示和搜索，建立索引支持模糊查询
    name = Column(String(255), nullable=False, index=True)
    
    # 任务描述，可选，长文本类型
    description = Column(Text, nullable=True)
    
    # 任务状态，使用枚举类型
    # 默认值为 PENDING，建立索引支持状态过滤
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING, index=True)
    
    # 任务类型，可选，用于区分不同种类的任务
    # 例如：data_processing, report_generation 等
    task_type = Column(String(50), nullable=True, index=True)
    
    # 任务优先级，整数类型，默认0
    # 数值越大优先级越高，建立索引支持排序
    priority = Column(Integer, default=0, index=True)
    
    # ==================== 任务数据字段 ====================
    # 任务负载数据，JSON格式字符串存储
    # 包含任务执行所需的参数和数据
    payload = Column(Text, nullable=True)
    
    # 任务执行结果，JSON格式字符串
    # 任务成功完成后存储返回值
    result = Column(Text, nullable=True)
    
    # 错误信息，任务失败时记录错误详情
    error_message = Column(Text, nullable=True)
    
    # ==================== 时间戳字段 ====================
    # 创建时间，默认当前时间
    # server_default 使用数据库服务器时间
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # 更新时间，默认当前时间，更新时自动刷新
    # onupdate 在记录更新时自动设置为当前时间
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 开始执行时间，任务开始执行时设置
    started_at = Column(DateTime(timezone=True), nullable=True)
    
    # 完成时间，任务结束时设置（无论成功或失败）
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        """
        返回任务的字符串表示
        
        用于调试和日志输出，显示任务的关键信息。
        
        Returns:
            str: 任务的字符串表示
            
        Example:
            >>> print(task)
            <Task(id=1, task_id=abc-123, name=测试任务, status=pending)>
        """
        return f"<Task(id={self.id}, task_id={self.task_id}, name={self.name}, status={self.status})>"
