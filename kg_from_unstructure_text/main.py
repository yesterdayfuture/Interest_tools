"""
电商客服图谱系统 - 主入口模块

本模块是FastAPI应用的入口点，负责：
1. 应用初始化：配置日志、创建目录、初始化数据库
2. 生命周期管理：启动时初始化资源，关闭时释放资源
3. 中间件配置：CORS、全局异常处理等
4. 路由注册：挂载各个模块的API路由
5. 健康检查：提供系统状态监控端点

系统架构：
- FastAPI：Web框架，提供高性能异步API
- SQLite：关系型数据库，存储本体定义、文件元数据等
- Nebula Graph：图数据库，存储实体和关系
- ChromaDB：向量数据库，支持RAG检索
- OpenAI：大语言模型，支持实体提取和自然语言处理

启动流程：
1. 创建必要的文件目录
2. 初始化SQLite数据库表
3. 初始化默认数据（属性类型等）
4. 连接Nebula Graph并创建Space
5. 初始化Nebula基础Schema
6. 启动FastAPI服务

环境变量：
所有配置均可通过.env文件或环境变量覆盖，详见app/config.py
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import os

from app.config import settings
from app.database import init_db, init_default_data, AsyncSessionLocal
from app.nebula_client import nebula_client

# 配置日志格式和级别
# 日志格式：时间 - 模块名 - 日志级别 - 消息内容
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("=" * 50)
    logger.info(f"正在初始化应用: {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("=" * 50)
    
    # 创建必要的目录
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(settings.SQLITE_DB_PATH), exist_ok=True)
    os.makedirs(settings.CHROMA_DB_PATH, exist_ok=True)
    logger.info("✓ 目录创建完成")
    
    # 初始化数据库表结构
    try:
        await init_db()
        logger.info("✓ 数据库表初始化完成")
    except Exception as e:
        logger.error(f"✗ 数据库初始化失败: {e}")
        raise
    
    # 初始化默认数据（属性类型等）
    try:
        async with AsyncSessionLocal() as db:
            await init_default_data(db)
        logger.info("✓ 默认数据初始化完成")
    except Exception as e:
        logger.error(f"✗ 默认数据初始化失败: {e}")
        # 不阻塞启动，继续
    
    # 初始化Nebula Graph
    try:
        logger.info("正在连接Nebula Graph...")
        if await nebula_client.connect():
            logger.info("✓ Nebula Graph连接成功")
            
            # 确保space存在并等待同步
            if nebula_client.ensure_space(wait_for_sync=True):
                logger.info(f"✓ Nebula Space '{settings.NEBULA_SPACE}' 就绪")
                
                # 初始化基础Schema
                if nebula_client.init_basic_schema():
                    logger.info("✓ Nebula基础Schema初始化完成")
                else:
                    logger.warning("⚠ Nebula基础Schema初始化失败")
            else:
                logger.warning(f"⚠ Nebula Space创建/切换失败")
        else:
            logger.warning("⚠ Nebula Graph连接失败，知识图谱功能可能不可用")
    except Exception as e:
        logger.warning(f"⚠ Nebula Graph初始化失败: {e}，知识图谱功能可能不可用")
    
    logger.info("=" * 50)
    logger.info("应用初始化完成，服务已启动")
    logger.info(f"API文档: http://localhost:8000/docs")
    logger.info("=" * 50)
    
    yield
    
    # 关闭时执行
    logger.info("正在关闭应用...")
    nebula_client.close()
    logger.info("应用已关闭")


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="电商客服图谱系统 - 支持本体管理、实体提取、知识图谱和RAG检索",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该配置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    logger.error(f"全局异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": "服务器内部错误",
            "detail": str(exc) if settings.DEBUG else "请联系管理员"
        }
    )


# 健康检查
@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "debug": settings.DEBUG
    }


# 根路径
@app.get("/")
async def root():
    """根路径 - API信息"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "api_v1": settings.API_V1_STR
    }


# 导入并注册路由
from app.routers import ontology, files, extraction, rag, property_types

# API V1 路由
api_v1_prefix = settings.API_V1_STR

app.include_router(ontology.router, prefix=api_v1_prefix)
app.include_router(property_types.router, prefix=api_v1_prefix)
app.include_router(files.router, prefix=api_v1_prefix)
app.include_router(extraction.router, prefix=api_v1_prefix)
app.include_router(rag.router, prefix=api_v1_prefix)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )