"""API v1 路由聚合."""

from fastapi import APIRouter

from app.api.v1 import scheduler, tasks

api_router = APIRouter()

# 注册任务路由
api_router.include_router(tasks.router)

# 注册多进程调度器路由
api_router.include_router(scheduler.router)
