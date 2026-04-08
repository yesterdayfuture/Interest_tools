"""
任务模型
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import String, Integer, Text, DateTime, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class TaskStatus(str, PyEnum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(Base):
    """任务模型"""
    
    __tablename__ = "tasks"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    task_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=TaskStatus.PENDING, index=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    
    # 任务负载数据
    payload: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    
    # 执行结果
    result: Mapped[dict] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    
    # 时间记录
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    
    # 执行时间（秒）
    execution_time: Mapped[float] = mapped_column(Float, nullable=True)
    
    def __repr__(self) -> str:
        return f"<Task(id={self.id}, name={self.name}, status={self.status})>"
