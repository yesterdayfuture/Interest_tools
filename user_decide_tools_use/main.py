"""
AI Agent API with Human-in-the-Loop

这是一个结合 FastAPI 和 OpenAI 的智能代理系统，主要功能包括：
1. 用户认证系统（JWT Token）
2. 任务管理系统（支持异步执行和用户确认）
3. WebSocket 实时通知
4. 数据持久化存储（SQLite）

启动命令：
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.core.config import settings
from app.routers import auth, tasks, pages

# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI Agent API with Human-in-the-Loop - 支持用户确认的智能代理系统"
)

# 添加 CORS 支持（前端需要）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# 注册路由
app.include_router(auth.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(tasks.list_router, prefix="/api")  # 任务列表路由
app.include_router(tasks.ws_router)  # WebSocket 路由（无前缀）
app.include_router(pages.router)

# 挂载静态文件目录
static_dir = os.path.join(os.path.dirname(__file__), "app", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
