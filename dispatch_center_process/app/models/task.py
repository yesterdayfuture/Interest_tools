"""任务数据模型."""

import enum
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TaskStatus(str, enum.Enum):
    """任务状态枚举."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(Base):
    """任务模型."""
    
    __tablename__ = "tasks"
    
    # 任务基本信息
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="任务名称"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="任务描述"
    )
    task_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="default",
        index=True,
        comment="任务类型"
    )
    
    # 任务状态和优先级
    status: Mapped[TaskStatus] = mapped_column(
        String(20),
        nullable=False,
        default=TaskStatus.PENDING,
        index=True,
        comment="任务状态"
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
        index=True,
        comment="优先级(1-10)"
    )
    
    # 任务数据
    payload: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="任务负载数据"
    )
    result: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="执行结果"
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="错误信息"
    )
    
    # 执行时间记录
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="开始执行时间"
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="完成时间"
    )
    
    # 执行统计
    execution_time: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        comment="执行耗时(秒)"
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="重试次数"
    )
    
    def __repr__(self) -> str:
        return f"<Task(id={self.id}, name={self.name}, status={self.status})>"
