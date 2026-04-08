"""FastAPI 应用主入口."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import close_db, init_db
from app.services.multi_process_scheduler import multi_process_scheduler
from app.services.task_scheduler import task_scheduler

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理."""
    # 启动时执行
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # 初始化数据库
    await init_db()

    # 启动多进程调度器
    await multi_process_scheduler.start()

    logger.info("Application startup complete")

    yield

    # 关闭时执行
    logger.info("Shutting down application...")

    # 关闭多进程调度器
    await multi_process_scheduler.shutdown()

    # 关闭旧版任务调度器
    await task_scheduler.shutdown()

    # 关闭数据库连接
    await close_db()

    logger.info("Application shutdown complete")


def create_application() -> FastAPI:
    """创建 FastAPI 应用实例."""
    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # 配置 CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )

    # 注册 API 路由
    app.include_router(
        api_router,
        prefix=settings.API_V1_PREFIX,
    )

    # 健康检查端点
    @app.get("/health", tags=["health"])
    async def health_check():
        """健康检查."""
        scheduler_status = multi_process_scheduler.get_scheduler_status()
        return {
            "status": "healthy",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "scheduler": {
                "running": scheduler_status["running"],
                "alive_workers": scheduler_status["alive_workers"],
                "pending_tasks": scheduler_status["pending_tasks"],
            },
        }

    # 根路径
    @app.get("/", tags=["root"])
    async def root():
        """根路径."""
        return {
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "description": settings.APP_DESCRIPTION,
            "docs": "/docs",
            "api_prefix": settings.API_V1_PREFIX,
            "features": [
                "multi-process task scheduling",
                "worker pool management",
                "real-time task monitoring",
            ],
        }

    return app


# 创建应用实例
app = create_application()
