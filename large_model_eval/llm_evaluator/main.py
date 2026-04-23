"""
FastAPI应用主入口

启动命令: uvicorn llm_evaluator.main:app --reload
"""

import yaml
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router


def load_config() -> dict:
    """
    加载配置文件
    
    Returns:
        dict: 配置字典
    """
    config_path = Path("config.yaml")
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    
    处理应用启动和关闭时的逻辑
    """
    # 启动时执行
    config = load_config()
    app.state.config = config
    
    print("=" * 60)
    print("大语言模型评估系统启动")
    print("=" * 60)
    print(f"API文档: http://localhost:8000/docs")
    print(f"Redoc文档: http://localhost:8000/redoc")
    print("=" * 60)
    
    yield
    
    # 关闭时执行
    print("\n正在关闭服务...")


# 创建FastAPI应用
app = FastAPI(
    title="LLM Evaluator API",
    description="""
    大语言模型评估系统API
    
    提供全面的LLM评估功能，包括：
    - 基础性能评估（准确性、效率、鲁棒性）
    - 高级能力评估（生成质量、交互能力）
    - 伦理安全评估（偏见、安全性、对齐）
    
    支持数据集：MMLU、C-Eval、CMMLU等
    支持模型：OpenAI API、本地HuggingFace模型
    """,
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router)


# 根路径
@app.get("/")
async def root():
    """
    根路径
    
    返回API基本信息
    """
    return {
        "name": "LLM Evaluator API",
        "version": "1.0.0",
        "description": "大语言模型评估系统",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "api_prefix": "/api/v1"
    }
