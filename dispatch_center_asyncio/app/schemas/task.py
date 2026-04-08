"""
任务数据验证和序列化模块 (Pydantic Schemas)

该模块定义了所有与任务相关的 Pydantic 模型，用于：
1. 请求数据验证：确保客户端提交的数据符合规范
2. 响应数据序列化：将数据库模型转换为 JSON 响应
3. API 文档生成：为 FastAPI 自动生成交互式文档

Schema 命名规范：
- TaskBase: 基础模型，包含共有的字段
- TaskCreate: 创建请求模型，通常继承自 Base
- TaskUpdate: 更新请求模型，所有字段可选
- TaskResponse: 响应模型，包含完整字段
- TaskListResponse: 列表响应模型，包含分页信息
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import json


class TaskStatus(str, Enum):
    """
    任务状态枚举
    
    与 models.task.TaskStatus 保持一致，用于 API 层的验证和文档生成。
    使用 str 和 Enum 混合继承，确保可以序列化为 JSON 字符串。
    
    Attributes:
        PENDING: 待执行
        RUNNING: 执行中
        COMPLETED: 已完成
        FAILED: 失败
        CANCELLED: 已取消
    """
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskBase(BaseModel):
    """
    任务基础 Schema
    
    定义创建和更新任务时的共有字段，作为其他 Task Schema 的基类。
    使用 Pydantic 的 Field 进行详细的字段验证配置。
    
    Attributes:
        name: 任务名称，必填，1-255字符
        description: 任务描述，可选
        task_type: 任务类型，可选，最大50字符
        priority: 优先级，0-100整数，默认0
        payload: 任务负载，任意JSON对象，可选
        
    Example:
        >>> task = TaskBase(
        ...     name="数据处理",
        ...     priority=5,
        ...     payload={"file": "data.csv"}
        ... )
    """
    
    # 任务名称：必填，长度1-255字符
    # Field 参数说明：
    #   - ... : 表示必填字段
    #   - min_length/max_length: 字符串长度限制
    #   - description: 字段描述，显示在API文档中
    name: str = Field(
        ..., 
        min_length=1, 
        max_length=255, 
        description="任务名称"
    )
    
    # 任务描述：可选，长文本
    description: Optional[str] = Field(
        None, 
        description="任务描述"
    )
    
    # 任务类型：可选，用于分类和路由到不同处理器
    task_type: Optional[str] = Field(
        None, 
        max_length=50, 
        description="任务类型"
    )
    
    # 优先级：整数，范围0-100，数值越大优先级越高
    # ge: greater than or equal (>=)
    # le: less than or equal (<=)
    priority: int = Field(
        0, 
        ge=0, 
        le=100, 
        description="优先级(0-100)"
    )
    
    # 任务负载：任意JSON对象，存储任务执行所需的参数
    # 在数据库中以JSON字符串存储，API中以Python字典形式交互
    payload: Optional[Dict[str, Any]] = Field(
        None, 
        description="任务负载数据"
    )


class TaskCreate(TaskBase):
    """
    创建任务请求 Schema
    
    继承自 TaskBase，用于验证创建任务的请求体。
    所有字段继承自父类，保持相同的验证规则。
    
    Note:
        如果需要添加创建时特有的字段（如 creator_id），可以在此类中添加。
    """
    pass


class TaskUpdate(BaseModel):
    """
    更新任务请求 Schema
    
    与 TaskCreate 不同，所有字段都是可选的（Optional）。
    这样客户端可以只更新部分字段，而不需要提供完整数据。
    
    Attributes:
        name: 新的任务名称，可选
        description: 新的描述，可选
        task_type: 新的类型，可选
        priority: 新的优先级，可选
        payload: 新的负载数据，可选
        
    Note:
        使用 model_dump(exclude_unset=True) 可以只序列化已设置的字段，
        避免将 None 值覆盖数据库中的原有数据。
    """
    
    name: Optional[str] = Field(
        None, 
        min_length=1, 
        max_length=255,
        description="新的任务名称"
    )
    description: Optional[str] = Field(
        None, 
        description="新的任务描述"
    )
    task_type: Optional[str] = Field(
        None, 
        max_length=50,
        description="新的任务类型"
    )
    priority: Optional[int] = Field(
        None, 
        ge=0, 
        le=100,
        description="新的优先级"
    )
    payload: Optional[Dict[str, Any]] = Field(
        None, 
        description="新的任务负载数据"
    )


class TaskResponse(BaseModel):
    """
    任务响应 Schema
    
    定义 API 返回的任务数据结构，包含完整的任务信息。
    与数据库模型 Task 对应，但进行了序列化和格式转换。
    
    Attributes:
        id: 数据库主键ID
        task_id: 业务UUID，对外暴露
        name: 任务名称
        description: 任务描述
        task_type: 任务类型
        priority: 优先级
        payload: 任务负载（从JSON字符串解析为字典）
        status: 当前状态
        result: 执行结果
        error_message: 错误信息
        created_at: 创建时间
        updated_at: 更新时间
        started_at: 开始执行时间
        completed_at: 完成时间
        
    Note:
        model_validate 类方法用于从 SQLAlchemy 模型实例创建 Schema 对象，
        并处理 payload 字段的 JSON 反序列化。
    """
    
    # 标识字段
    id: int = Field(..., description="数据库主键ID")
    task_id: str = Field(..., description="业务UUID")
    
    # 基本信息字段
    name: str = Field(..., description="任务名称")
    description: Optional[str] = Field(None, description="任务描述")
    task_type: Optional[str] = Field(None, description="任务类型")
    priority: int = Field(..., description="优先级")
    
    # 数据字段（从JSON字符串解析）
    payload: Optional[Dict[str, Any]] = Field(None, description="任务负载数据")
    
    # 状态字段
    status: TaskStatus = Field(..., description="任务状态")
    # result 也是 JSON 字符串存储，需要解析为字典
    result: Optional[Dict[str, Any]] = Field(None, description="执行结果")
    error_message: Optional[str] = Field(None, description="错误信息")
    
    # 时间戳字段
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    started_at: Optional[datetime] = Field(None, description="开始执行时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")

    @classmethod
    def model_validate(cls, obj):
        """
        从 SQLAlchemy 模型实例创建 Schema 对象
        
        这是自定义的验证方法，用于处理数据库模型到 Pydantic 模型的转换。
        主要处理 payload 字段：数据库中存储为 JSON 字符串，API 中需要转为字典。
        
        Args:
            obj: SQLAlchemy Task 模型实例
            
        Returns:
            TaskResponse: 验证后的响应对象
            
        Example:
            >>> task = await session.get(Task, 1)
            >>> response = TaskResponse.model_validate(task)
            >>> print(response.payload)  # 已经是字典，不是JSON字符串
        """
        data = {
            "id": obj.id,
            "task_id": obj.task_id,
            "name": obj.name,
            "description": obj.description,
            "task_type": obj.task_type,
            "priority": obj.priority,
            # 将数据库中的JSON字符串解析为Python字典
            "payload": json.loads(obj.payload) if obj.payload else None,
            "status": obj.status,
            # result 也是 JSON 字符串，解析为字典
            "result": json.loads(obj.result) if obj.result else None,
            "error_message": obj.error_message,
            "created_at": obj.created_at,
            "updated_at": obj.updated_at,
            "started_at": obj.started_at,
            "completed_at": obj.completed_at,
        }
        return cls(**data)


class TaskListResponse(BaseModel):
    """
    任务列表响应 Schema
    
    定义分页查询的响应结构，包含任务列表和分页元数据。
    
    Attributes:
        total: 符合条件的总记录数
        items: 当前页的任务列表
        page: 当前页码
        page_size: 每页记录数
        total_pages: 总页数
        
    Example:
        >>> response = TaskListResponse(
        ...     total=100,
        ...     items=[task1, task2],
        ...     page=1,
        ...     page_size=10,
        ...     total_pages=10
        ... )
    """
    total: int = Field(..., description="总记录数")
    items: List[TaskResponse] = Field(..., description="任务列表")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    total_pages: int = Field(..., description="总页数")


class TaskFilter(BaseModel):
    """
    任务过滤条件 Schema
    
    定义任务列表查询的过滤参数，所有字段都是可选的。
    用于构建类型安全的查询参数模型。
    
    Attributes:
        task_id: 按任务ID精确匹配
        name: 按名称模糊查询
        status: 按状态过滤
        task_type: 按类型过滤
        priority_min: 最小优先级
        priority_max: 最大优先级
        created_after: 创建时间之后
        created_before: 创建时间之前
    """
    task_id: Optional[str] = Field(None, description="任务ID精确匹配")
    name: Optional[str] = Field(None, description="任务名称模糊查询")
    status: Optional[TaskStatus] = Field(None, description="任务状态过滤")
    task_type: Optional[str] = Field(None, description="任务类型过滤")
    priority_min: Optional[int] = Field(None, description="最小优先级")
    priority_max: Optional[int] = Field(None, description="最大优先级")
    created_after: Optional[datetime] = Field(None, description="创建时间之后")
    created_before: Optional[datetime] = Field(None, description="创建时间之前")


class TaskStatistics(BaseModel):
    """
    任务统计响应 Schema
    
    定义任务统计信息的响应结构，用于仪表盘展示。
    
    Attributes:
        total_tasks: 总任务数
        pending_count: 待执行数量
        running_count: 执行中数量
        completed_count: 已完成数量
        failed_count: 失败数量
        cancelled_count: 已取消数量
        success_rate: 成功率（百分比）
        average_execution_time: 平均执行时间（秒）
        
    Example:
        >>> stats = TaskStatistics(
        ...     total_tasks=100,
        ...     pending_count=10,
        ...     running_count=5,
        ...     completed_count=80,
        ...     failed_count=3,
        ...     cancelled_count=2,
        ...     success_rate=96.39,
        ...     average_execution_time=5.23
        ... )
    """
    total_tasks: int = Field(..., description="总任务数")
    pending_count: int = Field(..., description="待执行数量")
    running_count: int = Field(..., description="执行中数量")
    completed_count: int = Field(..., description="已完成数量")
    failed_count: int = Field(..., description="失败数量")
    cancelled_count: int = Field(..., description="已取消数量")
    success_rate: float = Field(..., description="成功率(%)")
    average_execution_time: Optional[float] = Field(
        None, 
        description="平均执行时间(秒)"
    )


class TaskSubmitResponse(BaseModel):
    """
    任务提交响应 Schema
    
    定义任务提交接口的响应结构，包含操作结果和创建的任务信息。
    
    Attributes:
        success: 操作是否成功
        message: 操作结果消息
        task_id: 创建的任务ID
        data: 完整的任务数据
        
    Example:
        >>> response = TaskSubmitResponse(
        ...     success=True,
        ...     message="Task submitted successfully",
        ...     task_id="uuid-string",
        ...     data=task_data
        ... )
    """
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="结果消息")
    task_id: str = Field(..., description="任务ID")
    data: Optional[TaskResponse] = Field(None, description="任务数据")
