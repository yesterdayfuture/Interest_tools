"""
Chat Room API - FastAPI 主应用入口

基于 FastAPI + WebSocket 的实时聊天室应用
支持个人聊天、群组聊天、好友系统和群组邀请系统
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import init_db
from app.routes import api_router
from app.routes.websocket import router as websocket_router

# 创建 FastAPI 应用实例
app = FastAPI(
    title="Chat Room API",
    description="WebSocket based chat room application with friend and group systems",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """
    应用启动事件
    初始化数据库
    """
    init_db()


# 注册 API 路由
app.include_router(api_router, prefix="/api")

# 注册 WebSocket 路由
app.include_router(websocket_router)


@app.get("/", tags=["根路径"])
async def root():
    """
    根路径，返回 API 信息
    """
    return {
        "message": "Welcome to Chat Room API",
        "version": "2.0.0",
        "docs": "/docs",
        "websocket": "/ws/{token}"
    }


@app.get("/health", tags=["健康检查"])
async def health_check():
    """
    健康检查端点
    """
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
