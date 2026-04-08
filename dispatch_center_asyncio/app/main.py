"""
任务调度中心 - 主应用入口模块

本模块是FastAPI应用程序的主入口点，负责：
1. 创建和配置FastAPI应用实例
2. 设置应用生命周期管理（启动/关闭）
3. 配置中间件（CORS跨域支持）
4. 注册API路由
5. 提供健康检查和根端点

架构说明：
- 使用FastAPI框架构建异步API服务
- 采用上下文管理器实现优雅的应用生命周期管理
- 通过依赖注入实现组件解耦
- 支持CORS跨域资源共享

使用示例：
    # 开发模式启动
    uvicorn app.main:app --reload
    
    # 生产模式启动
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.core.response import success_response, error_response, ResponseCode
from app.core.exceptions import AppException
from app.db.session import init_db
from app.services.task_scheduler import task_scheduler
from app.api.v1.api import api_router

# 获取应用配置实例
# 配置对象包含所有环境变量和应用程序设置
settings = get_settings()

# 初始化日志系统
# 配置日志格式、级别和输出目标
setup_logging()

# 获取当前模块的日志记录器
# 用于记录应用启动、关闭和运行时的日志信息
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI应用生命周期管理器
    
    这是一个异步上下文管理器，用于管理应用的启动和关闭过程。
    在yield之前的代码在应用启动时执行，yield之后的代码在应用关闭时执行。
    
    启动流程：
    1. 初始化数据库连接和表结构
    2. 记录启动日志
    3. 应用进入运行状态
    
    关闭流程：
    1. 触发优雅关闭信号
    2. 等待正在执行的任务完成
    3. 释放资源（数据库连接、线程池等）
    4. 记录关闭日志
    
    Args:
        app: FastAPI应用实例，由框架自动传入
        
    Yields:
        None: 控制权交给FastAPI框架，应用开始处理请求
        
    Raises:
        Exception: 数据库初始化失败时抛出，应用将无法正常启动
        
    示例：
        无需手动调用，FastAPI框架会自动管理生命周期
    """
    # ===== 应用启动阶段 =====
    logger.info("Initializing database...")
    # 初始化数据库：创建所有定义的表结构
    # 如果表已存在则不会重复创建（基于SQLAlchemy的create_all行为）
    await init_db()
    logger.info("Database initialized successfully")
    
    # 可以在这里添加其他启动逻辑：
    # - 加载缓存数据
    # - 启动后台任务
    # - 初始化外部服务连接

    # yield将控制权交给FastAPI，应用开始处理请求
    yield

    # ===== 应用关闭阶段 =====
    # 当应用收到关闭信号（SIGTERM/SIGINT）时执行
    logger.info("Shutting down...")
    # 关闭任务调度器：停止接受新任务，等待运行中的任务完成
    await task_scheduler.shutdown()
    logger.info("Shutdown complete")


# 创建FastAPI应用实例
# 这是整个应用程序的核心对象
app = FastAPI(
    # API文档标题，显示在Swagger UI和ReDoc页面顶部
    title=settings.api_title,
    # API详细描述，支持Markdown格式
    description=settings.app_description,
    # API版本号，遵循语义化版本规范（SemVer）
    version=settings.app_version,
    # 生命周期管理器，处理启动和关闭逻辑
    lifespan=lifespan,
    # 其他可选配置：
    # docs_url="/docs",      # Swagger UI路径
    # redoc_url="/redoc",    # ReDoc文档路径
    # openapi_url="/openapi.json",  # OpenAPI规范路径
)

# ===== 中间件配置 =====
# CORS（跨域资源共享）中间件
# 允许前端应用从不同域名访问API
app.add_middleware(
    CORSMiddleware,
    # 允许的源域名列表
    # 生产环境应设置为具体的域名，如 ["https://example.com"]
    # 开发环境可以设置为 ["*"] 允许所有域名
    allow_origins=settings.cors_origins,
    # 是否允许携带凭证（cookies、authorization headers等）
    allow_credentials=settings.cors_allow_credentials,
    # 允许的HTTP方法
    allow_methods=settings.cors_allow_methods,
    # 允许的HTTP请求头
    allow_headers=settings.cors_allow_headers,
)

# ===== API路由注册 =====
# 将v1版本的所有API路由注册到应用
# 前缀为 /api/v1，所有路由会自动加上此前缀
# 例如：tasks.py中定义的 /tasks 会变成 /api/v1/tasks
app.include_router(api_router, prefix=settings.api_v1_prefix)


# ===== 全局异常处理 =====
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """
    处理应用自定义异常
    
    将 AppException 转换为统一响应格式。
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(
            message=exc.detail,
            code=exc.status_code,
            error_detail={"path": request.url.path}
        )
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    处理所有未捕获的异常
    
    将未知异常转换为统一响应格式，避免暴露内部错误详情。
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=ResponseCode.INTERNAL_SERVER_ERROR,
        content=error_response(
            message="Internal server error",
            code=ResponseCode.INTERNAL_SERVER_ERROR,
            error_detail={"path": request.url.path}
        )
    )


@app.get("/")
async def root():
    """
    根端点 - 应用信息入口
    
    提供应用的基本信息，包括名称、版本、文档链接等。
    返回统一响应格式。
    
    Returns:
        统一响应格式，包含应用基本信息
        
    示例响应：
        {
            "code": 200,
            "message": "success",
            "data": {
                "name": "任务调度中心",
                "version": "1.0.0",
                "docs": "/docs",
                "api_prefix": "/api/v1"
            },
            "timestamp": 1234567890
        }
    """
    return success_response(
        data={
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "api_prefix": settings.api_v1_prefix,
        },
        message="Welcome to Task Scheduler Center"
    )


@app.get("/health")
async def health_check():
    """
    健康检查端点
    
    用于监控和负载均衡器检查应用运行状态。
    返回统一响应格式，表示应用正在正常运行。
    
    Returns:
        统一响应格式，包含健康状态信息
        
    使用场景：
    - Kubernetes存活探针（liveness probe）
    - 负载均衡器健康检查
    - 监控系统状态采集
    - 部署流水线健康验证
    
    示例响应：
        {
            "code": 200,
            "message": "success",
            "data": {
                "status": "healthy",
                "service": "task-scheduler",
                "timestamp": "2024-01-01T00:00:00"
            },
            "timestamp": 1234567890
        }
        
    HTTP状态码：
    - 200: 应用正常运行
    - 503: 服务不可用（当添加详细检查时）
    """
    from datetime import datetime
    return success_response(
        data={
            "status": "healthy",
            "service": "task-scheduler",
            "timestamp": datetime.utcnow().isoformat()
        },
        message="Service is healthy"
    )


# ===== 应用入口 =====
# 当直接运行此文件时启动开发服务器
# 生产环境应使用专业的ASGI服务器（如gunicorn + uvicorn）
if __name__ == "__main__":
    import uvicorn
    
    # 启动Uvicorn开发服务器
    # app.main:app 表示从 app/main.py 导入 app 对象
    uvicorn.run(
        "app.main:app",      # ASGI应用路径
        host="0.0.0.0",      # 监听所有网络接口
        port=8000,           # 服务端口
        reload=True,         # 开发模式：代码变更自动重载
        # 生产环境建议参数：
        # workers=4,         # 工作进程数
        # reload=False,      # 关闭自动重载
        # log_level="info",  # 日志级别
    )
