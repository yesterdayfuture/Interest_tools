"""
应用配置模块

本模块负责管理整个电商客服图谱系统的所有配置项，包括：
- 应用基础配置（名称、版本、调试模式等）
- 数据库配置（SQLite、Nebula Graph）
- AI模型配置（OpenAI、嵌入模型）
- 向量数据库配置（ChromaDB）
- RAG检索配置
- 文件上传配置

配置项支持从环境变量(.env文件)读取，便于不同环境的部署。
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """
    应用配置类
    
    使用Pydantic的BaseSettings实现，支持：
    - 类型验证和默认值
    - 环境变量覆盖
    - .env文件读取
    
    所有配置项都可以通过环境变量进行覆盖，优先级：
    环境变量 > .env文件 > 默认值
    """
    
    # ==================== 应用基础配置 ====================
    APP_NAME: str = "电商客服图谱系统"
    """应用名称，用于API文档和日志显示"""
    
    APP_VERSION: str = "1.0.0"
    """应用版本号，用于API版本管理和兼容性检查"""
    
    DEBUG: bool = True
    """调试模式开关
    
    True: 开启调试模式，输出详细日志和错误信息
    False: 生产模式，只输出必要日志，隐藏敏感错误详情
    """
    
    # ==================== API配置 ====================
    API_V1_STR: str = "/api/v1"
    """API版本前缀，所有v1版本的API都会添加此前缀"""
    
    # ==================== SQLite数据库配置 ====================
    SQLITE_DB_PATH: str = "./data/ontology.db"
    """SQLite数据库文件路径
    
    存储本体定义、文件元数据、属性类型等结构化数据
    建议使用绝对路径或相对于工作目录的路径
    """
    
    # ==================== Nebula Graph图数据库配置 ====================
    NEBULA_HOST: str = "127.0.0.1"
    """Nebula Graph服务器主机地址"""
    
    NEBULA_PORT: int = 9669
    """Nebula Graph服务器端口，默认9669"""
    
    NEBULA_USER: str = "root"
    """Nebula Graph连接用户名"""
    
    NEBULA_PASSWORD: str = "nebula"
    """Nebula Graph连接密码"""
    
    NEBULA_SPACE: str = "customer_service"
    """Nebula Graph的Space名称（相当于数据库名）
    
    系统启动时会自动创建该Space（如果不存在）
    """
    
    # ==================== OpenAI配置 ====================
    OPENAI_API_KEY: Optional[str] = None
    """OpenAI API密钥
    
    用于调用大模型进行实体提取、关系识别等功能
    如果未设置，相关功能将不可用
    """
    
    OPENAI_BASE_URL: Optional[str] = "https://api.openai.com/v1"
    """OpenAI API基础URL
    
    支持自定义API代理或第三方兼容API
    例如：https://api.xxx.com/v1
    """
    
    OPENAI_MODEL: str = "gpt-4"
    """OpenAI模型名称
    
    推荐使用：
    - gpt-4: 最强性能，适合复杂任务
    - gpt-4-turbo: 性价比更好
    - gpt-3.5-turbo: 成本最低，简单任务可用
    """
    
    EMBEDDING_MODEL: str = "text-embedding-ada-002"
    """默认嵌入模型名称（向后兼容）"""
    
    # ==================== 嵌入模型独立配置（可选） ====================
    EMBEDDING_API_KEY: Optional[str] = None
    """嵌入模型专用API密钥
    
    如果设置，将优先使用此密钥调用嵌入模型API
    如果为空，则使用 OPENAI_API_KEY
    适用于嵌入模型使用不同服务商的场景
    """
    
    EMBEDDING_BASE_URL: Optional[str] = None
    """嵌入模型专用API基础URL
    
    如果设置，将优先使用此URL调用嵌入模型
    如果为空，则使用 OPENAI_BASE_URL
    """
    
    EMBEDDING_MODEL_NAME: str = "text-embedding-ada-002"
    """嵌入模型名称
    
    推荐使用：
    - text-embedding-ada-002: OpenAI官方模型，性价比高
    - text-embedding-3-small: 新版轻量模型
    - text-embedding-3-large: 新版高质量模型
    """
    
    # ==================== ChromaDB向量数据库配置 ====================
    CHROMA_DB_PATH: str = "./data/chroma_db"
    """ChromaDB数据存储路径
    
    存储文档向量、索引等RAG相关数据
    系统启动时会自动创建该目录（如果不存在）
    """
    
    CHROMA_COLLECTION_NAME: str = "customer_service_docs"
    """ChromaDB集合名称（相当于表名）"""
    
    # ==================== RAG检索配置 ====================
    RAG_TOP_K: int = 5
    """RAG检索返回的最大结果数量"""
    
    RAG_SCORE_THRESHOLD: float = 0.7
    """RAG检索相似度阈值
    
    只有相似度高于此阈值的结果才会被返回
    范围：0.0 - 1.0，值越大要求匹配越精确
    """
    
    # ==================== 文件上传配置 ====================
    UPLOAD_DIR: str = "./uploads"
    """上传文件的存储目录
    
    系统启动时会自动创建该目录（如果不存在）
    建议定期清理过期文件以节省空间
    """
    
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    """单个文件的最大允许大小（字节）"""
    
    ALLOWED_EXTENSIONS: list = [".txt", ".pdf", ".docx", ".doc", ".pptx", ".xlsx", ".csv", ".md"]
    """允许上传的文件扩展名列表
    
    系统会根据扩展名选择对应的解析器处理文件内容
    """
    
    class Config:
        """Pydantic配置类"""
        env_file = ".env"
        """指定从.env文件读取环境变量配置"""


@lru_cache()
def get_settings() -> Settings:
    """
    获取配置实例（带缓存）
    
    使用@lru_cache装饰器确保配置只被创建一次，提高性能
    在整个应用生命周期中，settings对象都是单例的
    
    Returns:
        Settings: 配置实例
    """
    return Settings()


# 全局配置实例
# 在应用各处通过导入settings来访问配置
# 示例：from app.config import settings
settings = get_settings()
