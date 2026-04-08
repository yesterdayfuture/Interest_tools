"""
FastAPI 应用入口
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import logger
from app.db.session import init_db, close_db
from app.api.v1.api import api_router
from app.services.task_scheduler import task_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    
    启动时：
    1. 初始化数据库
    2. 启动任务调度器
    
    关闭时：
    1. 停止任务调度器
    2. 关闭数据库连接
    """
    # 启动
    logger.info("Starting up...")
    await init_db()
    await task_scheduler.start()
    logger.info("Application started successfully")
    
    yield
    
    # 关闭
    logger.info("Shutting down...")
    await task_scheduler.stop()
    await close_db()
    logger.info("Application stopped")


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="基于 ThreadPoolExecutor 的高性能任务调度系统",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "running_tasks": task_scheduler.get_running_count(),
    }
