"""
统一 API 响应格式模块

该模块定义了 RESTful API 的统一响应格式，所有 API 端点都使用这些响应模型
来确保接口返回格式的一致性。

标准响应格式：
{
    "code": 200,           # 业务状态码，与 HTTP 状态码一致或更细化
    "message": "success",  # 状态描述信息
    "data": { ... },       # 实际业务数据
    "timestamp": 1234567890 # 响应时间戳
}

错误响应格式：
{
    "code": 400,
    "message": "Invalid request parameters",
    "data": null,
    "error_detail": { ... },  # 可选的详细错误信息
    "timestamp": 1234567890
}
"""

from typing import Optional, Dict, Any, TypeVar, Generic
from datetime import datetime
from pydantic import BaseModel, Field

# 定义泛型类型变量，用于 data 字段的类型推断
T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """
    统一 API 响应基础模型
    
    所有 API 响应都基于此模型，提供一致的响应结构。
    使用泛型支持不同类型的 data 字段。
    
    Attributes:
        code: 业务状态码，通常与 HTTP 状态码一致
        message: 状态描述信息，简短说明请求结果
        data: 实际业务数据，成功时包含返回数据，失败时为 null
        timestamp: 响应时间戳（Unix 时间戳，秒）
        request_id: 请求追踪 ID，用于日志追踪和问题排查
        error_detail: 详细错误信息，仅在出错时包含
        
    Example:
        >>> response = BaseResponse(
        ...     code=200,
        ...     message="success",
        ...     data={"id": 1, "name": "task"},
        ...     timestamp=int(datetime.now().timestamp())
        ... )
        >>> print(response.model_dump_json())
    """
    
    # 业务状态码
    # 200: 成功
    # 400: 请求参数错误
    # 401: 未授权
    # 403: 禁止访问
    # 404: 资源不存在
    # 500: 服务器内部错误
    code: int = Field(
        ..., 
        description="业务状态码",
        examples=[200, 400, 404, 500]
    )
    
    # 状态描述
    message: str = Field(
        ..., 
        description="状态描述信息",
        examples=["success", "Task not found", "Invalid parameters"]
    )
    
    # 业务数据，使用泛型支持任意类型
    data: Optional[T] = Field(
        None, 
        description="业务数据，成功时返回具体数据，失败时为 null"
    )
    
    # 响应时间戳
    timestamp: int = Field(
        default_factory=lambda: int(datetime.now().timestamp()),
        description="响应时间戳（Unix 时间戳，秒）"
    )
    
    # 请求追踪 ID（可选）
    request_id: Optional[str] = Field(
        None,
        description="请求追踪 ID，用于日志追踪和问题排查"
    )
    
    # 详细错误信息（可选，仅错误响应包含）
    error_detail: Optional[Dict[str, Any]] = Field(
        None,
        description="详细错误信息，仅在出错时包含"
    )


class ResponseCode:
    """
    标准响应状态码常量
    
    定义常用的业务状态码，与 HTTP 状态码保持一致。
    可以根据业务需求扩展更多状态码。
    """
    
    # 成功
    SUCCESS = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    
    # 客户端错误
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    TOO_MANY_REQUESTS = 429
    
    # 服务器错误
    INTERNAL_SERVER_ERROR = 500
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504


class ResponseMessage:
    """
    标准响应消息常量
    
    定义常用的响应消息文本，支持多语言扩展。
    """
    
    SUCCESS = "success"
    CREATED = "created successfully"
    UPDATED = "updated successfully"
    DELETED = "deleted successfully"
    
    BAD_REQUEST = "bad request"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "resource not found"
    VALIDATION_ERROR = "validation error"
    
    INTERNAL_SERVER_ERROR = "internal server error"
    SERVICE_UNAVAILABLE = "service unavailable"


def success_response(
    data: Any = None,
    message: str = ResponseMessage.SUCCESS,
    code: int = ResponseCode.SUCCESS,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    创建成功响应
    
    快速创建标准格式的成功响应。
    
    Args:
        data: 业务数据，任意类型
        message: 成功消息
        code: 状态码，默认 200
        request_id: 请求追踪 ID
        
    Returns:
        Dict: 标准响应字典
        
    Example:
        >>> return success_response(data={"id": 1}, message="Task created")
    """
    return {
        "code": code,
        "message": message,
        "data": data,
        "timestamp": int(datetime.now().timestamp()),
        "request_id": request_id,
        "error_detail": None
    }


def error_response(
    message: str,
    code: int = ResponseCode.BAD_REQUEST,
    error_detail: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    创建错误响应
    
    快速创建标准格式的错误响应。
    
    Args:
        message: 错误消息
        code: 错误状态码，默认 400
        error_detail: 详细错误信息
        request_id: 请求追踪 ID
        
    Returns:
        Dict: 标准错误响应字典
        
    Example:
        >>> return error_response(
        ...     message="Task not found",
        ...     code=404,
        ...     error_detail={"task_id": "invalid-uuid"}
        ... )
    """
    return {
        "code": code,
        "message": message,
        "data": None,
        "timestamp": int(datetime.now().timestamp()),
        "request_id": request_id,
        "error_detail": error_detail
    }


def created_response(
    data: Any = None,
    message: str = ResponseMessage.CREATED,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    创建资源成功响应（201）
    
    Args:
        data: 创建的资源数据
        message: 成功消息
        request_id: 请求追踪 ID
        
    Returns:
        Dict: 201 响应字典
    """
    return success_response(
        data=data,
        message=message,
        code=ResponseCode.CREATED,
        request_id=request_id
    )


def no_content_response(request_id: Optional[str] = None) -> Dict[str, Any]:
    """
    无内容响应（204）
    
    用于删除成功等不需要返回数据的场景。
    
    Args:
        request_id: 请求追踪 ID
        
    Returns:
        Dict: 204 响应字典
    """
    return {
        "code": ResponseCode.NO_CONTENT,
        "message": ResponseMessage.SUCCESS,
        "data": None,
        "timestamp": int(datetime.now().timestamp()),
        "request_id": request_id,
        "error_detail": None
    }


def paginated_response(
    items: list,
    total: int,
    page: int,
    page_size: int,
    message: str = ResponseMessage.SUCCESS,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    创建分页响应
    
    为列表查询创建标准的分页响应格式。
    
    Args:
        items: 当前页数据列表
        total: 总记录数
        page: 当前页码
        page_size: 每页数量
        message: 成功消息
        request_id: 请求追踪 ID
        
    Returns:
        Dict: 分页响应字典
        
    Example:
        >>> return paginated_response(
        ...     items=[{"id": 1}, {"id": 2}],
        ...     total=100,
        ...     page=1,
        ...     page_size=10
        ... )
    """
    total_pages = (total + page_size - 1) // page_size
    
    return success_response(
        data={
            "items": items,
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        },
        message=message,
        request_id=request_id
    )
