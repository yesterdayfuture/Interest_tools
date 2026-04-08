"""
API v1 路由聚合
"""
from fastapi import APIRouter
from app.api.v1 import tasks

api_router = APIRouter()

# 注册任务相关路由
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
