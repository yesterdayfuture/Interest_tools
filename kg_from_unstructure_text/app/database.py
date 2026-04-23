"""
数据库模型模块

本模块定义了电商客服图谱系统的所有数据库表结构和模型，包括：
- 属性类型管理（PropertyType）
- 本体定义（OntologyDefinition）
- 本体关系（OntologyRelation）
- 本体属性（OntologyProperty）
- 文件记录（FileRecord）
- 提取的实体（ExtractedEntity）
- 提取的关系（ExtractedRelation）
- 同步日志（SyncLog）

使用SQLAlchemy ORM进行数据库操作，支持异步查询（asyncio）。
所有模型类都继承自Base，可以通过Base.metadata.create_all()创建所有表。
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, 
    Boolean, JSON, Enum, UniqueConstraint, Index, select, func, update, delete
)
from datetime import datetime
import enum
import logging
from typing import Optional, List
from app.config import settings

# 配置日志记录器
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== 数据库引擎和会话配置 ====================

# 创建异步数据库引擎
# 使用aiosqlite驱动支持异步SQLite操作
engine = create_async_engine(
    f"sqlite+aiosqlite:///{settings.SQLITE_DB_PATH}",  # 数据库连接URL
    echo=settings.DEBUG,  # 是否输出SQL语句（仅在DEBUG模式启用）
    future=True  # 使用SQLAlchemy 2.0风格API
)

# 创建异步会话工厂
# 用于创建数据库会话，支持async上下文管理器
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False  # 提交后不自动过期对象，避免异步问题
)

# SQLAlchemy声明式基类
# 所有模型类都继承自此类
Base = declarative_base()


# ==================== 枚举类型定义 ====================

class OntologyType(str, enum.Enum):
    """
    本体定义类型枚举
    
    定义本体可以是以下三种类型之一：
    - ENTITY: 实体类型，如"商品"、"客户"等
    - RELATION: 关系类型，如"购买"、"推荐"等
    - ATTRIBUTE: 属性类型，如"价格"、"颜色"等
    """
    ENTITY = "entity"          # 实体类型
    RELATION = "relation"      # 关系类型
    ATTRIBUTE = "attribute"    # 属性类型


class OntologyStatus(str, enum.Enum):
    """
    本体定义状态枚举
    
    管理本体定义的生命周期状态：
    - ACTIVE: 活跃状态，正常使用中
    - INACTIVE: 非活跃状态，暂时禁用
    - MERGED: 已合并状态，被合并到其他本体
    """
    ACTIVE = "active"
    INACTIVE = "inactive"
    MERGED = "merged"          # 已被合并


class FileType(str, enum.Enum):
    """
    文件类型枚举
    
    用于分类上传的文件，便于选择对应的解析器：
    - DOCUMENT: 文档类（txt, pdf, docx等）
    - SPREADSHEET: 表格类（xlsx, csv等）
    - PRESENTATION: 演示文稿（pptx等）
    - OTHER: 其他类型
    """
    DOCUMENT = "document"      # 文档
    SPREADSHEET = "spreadsheet" # 表格
    PRESENTATION = "presentation" # 演示文稿
    OTHER = "other"


class FileStatus(str, enum.Enum):
    """
    文件处理状态枚举
    
    跟踪文件从上传到处理完成的全生命周期：
    - UPLOADED: 已上传，等待处理
    - PROCESSING: 正在处理中（解析内容、提取实体等）
    - PROCESSED: 处理完成
    - FAILED: 处理失败
    """
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class PropertyTypeStatus(str, enum.Enum):
    """
    属性类型状态枚举
    
    管理属性类型的生命周期：
    - ACTIVE: 活跃状态，可用于创建新属性
    - INACTIVE: 非活跃状态，不再推荐使用但保留兼容
    - DEPRECATED: 已弃用，计划删除
    """
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"


class PropertyType(Base):
    """属性类型定义表 - 管理可复用的属性类型"""
    __tablename__ = "property_types"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    display_name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # 数据类型
    data_type = Column(String(50), nullable=False)  # string, integer, float, boolean, datetime, enum, array, object
    
    # 默认值
    default_value = Column(Text, nullable=True)
    
    # 枚举值 (如果是enum类型)
    enum_values = Column(JSON, nullable=True)
    
    # 验证规则
    validation_rules = Column(JSON, nullable=True)  # {"min_length": 1, "max_length": 100, "min": 0, "max": 100}
    
    # 约束条件
    required = Column(Boolean, default=False)
    unique = Column(Boolean, default=False)
    indexable = Column(Boolean, default=False)  # 是否在Nebula中创建索引
    
    # 状态
    status = Column(Enum(PropertyTypeStatus), default=PropertyTypeStatus.ACTIVE)
    
    # 是否系统预定义
    is_system = Column(Boolean, default=False)
    
    # 元数据
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100), nullable=True)
    
    # 关系：该属性类型被哪些本体使用
    ontology_properties = relationship("OntologyProperty", back_populates="property_type")
    
    __table_args__ = (
        Index('ix_property_type_status', 'status'),
    )


class OntologyDefinition(Base):
    """本体定义表 - 支持树状结构"""
    __tablename__ = "ontology_definitions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    display_name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # 树状关系
    parent_id = Column(Integer, ForeignKey("ontology_definitions.id"), nullable=True, index=True)
    level = Column(Integer, default=0)  # 层级深度
    path = Column(String(500), default="")  # 路径，如 "/1/2/3"
    
    # 本体类型
    ontology_type = Column(Enum(OntologyType), nullable=False, index=True)
    status = Column(Enum(OntologyStatus), default=OntologyStatus.ACTIVE)
    
    # 属性定义 (JSON格式)
    properties = Column(JSON, default=dict)  # 例如: {"color": "string", "size": "number"}
    
    # 合并信息
    merged_into_id = Column(Integer, ForeignKey("ontology_definitions.id"), nullable=True)
    merged_at = Column(DateTime, nullable=True)
    
    # Nebula同步信息
    nebula_tag = Column(String(100), nullable=True)  # Nebula中的Tag名
    nebula_edge = Column(String(100), nullable=True)  # Nebula中的Edge名
    synced_to_nebula = Column(Boolean, default=False)
    last_sync_at = Column(DateTime, nullable=True)
    
    # 元数据
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100), nullable=True)
    
    # 关系
    children = relationship(
        "OntologyDefinition",
        back_populates="parent",
        foreign_keys="[OntologyDefinition.parent_id]"
    )
    parent = relationship(
        "OntologyDefinition",
        back_populates="children",
        remote_side=[id],
        foreign_keys="[OntologyDefinition.parent_id]"
    )
    merged_into = relationship(
        "OntologyDefinition",
        remote_side=[id],
        foreign_keys="[OntologyDefinition.merged_into_id]"
    )
    
    __table_args__ = (
        UniqueConstraint('name', 'ontology_type', name='uix_name_type'),
        Index('ix_ontology_parent_type', 'parent_id', 'ontology_type'),
    )


class OntologyRelation(Base):
    """本体关系定义表 - 定义实体之间的关系类型"""
    __tablename__ = "ontology_relations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # 关系两端的实体类型
    source_type_id = Column(Integer, ForeignKey("ontology_definitions.id"), nullable=False)
    target_type_id = Column(Integer, ForeignKey("ontology_definitions.id"), nullable=False)
    
    # 是否是有向关系
    is_directed = Column(Boolean, default=True)
    
    # 属性定义
    properties = Column(JSON, default=dict)
    
    # 状态
    status = Column(Enum(OntologyStatus), default=OntologyStatus.ACTIVE)
    
    # Nebula同步信息
    nebula_edge_type = Column(String(100), nullable=True)
    synced_to_nebula = Column(Boolean, default=False)
    last_sync_at = Column(DateTime, nullable=True)
    
    # 元数据
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OntologyProperty(Base):
    """本体属性定义表"""
    __tablename__ = "ontology_properties"
    
    id = Column(Integer, primary_key=True, index=True)
    ontology_id = Column(Integer, ForeignKey("ontology_definitions.id"), nullable=False)
    name = Column(String(100), nullable=False)
    display_name = Column(String(200), nullable=False)
    
    # 关联的属性类型（外键）
    property_type_id = Column(Integer, ForeignKey("property_types.id"), nullable=True, index=True)
    
    # 数据类型: string, integer, float, boolean, datetime, enum
    data_type = Column(String(50), nullable=False)
    
    # 是否必填
    required = Column(Boolean, default=False)
    
    # 默认值
    default_value = Column(Text, nullable=True)
    
    # 枚举值 (如果是enum类型)
    enum_values = Column(JSON, nullable=True)
    
    # 验证规则
    validation_rules = Column(JSON, nullable=True)  # {"min_length": 1, "max_length": 100}
    
    # 描述
    description = Column(Text)
    
    # 排序
    sort_order = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    property_type = relationship("PropertyType", back_populates="ontology_properties")
    
    __table_args__ = (
        UniqueConstraint('ontology_id', 'name', name='uix_ontology_property'),
        Index('ix_ontology_property_type', 'property_type_id'),
    )


class FileRecord(Base):
    """文件记录表"""
    __tablename__ = "file_records"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(Enum(FileType), nullable=False)
    mime_type = Column(String(100), nullable=True)
    file_extension = Column(String(20), nullable=False)
    
    # 文件内容摘要
    content_summary = Column(Text, nullable=True)
    
    # 文件状态
    status = Column(Enum(FileStatus), default=FileStatus.UPLOADED)
    
    # 处理信息
    processed_at = Column(DateTime, nullable=True)
    processing_error = Column(Text, nullable=True)
    
    # 关联的本体实体 (提取的实体ID列表)
    extracted_entities = Column(JSON, default=list)
    
    # RAG处理状态
    rag_processed = Column(Boolean, default=False)
    chroma_doc_ids = Column(JSON, default=list)  # ChromaDB中的文档ID
    
    # 元数据
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    uploaded_by = Column(String(100), nullable=True)


class ExtractedEntity(Base):
    """从文本中提取的实体记录"""
    __tablename__ = "extracted_entities"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 关联的文件
    file_id = Column(Integer, ForeignKey("file_records.id"), nullable=True)
    
    # 实体信息
    name = Column(String(500), nullable=False, index=True)
    ontology_id = Column(Integer, ForeignKey("ontology_definitions.id"), nullable=False)
    
    # 属性值
    properties = Column(JSON, default=dict)
    
    # 来源信息
    source_text = Column(Text)  # 原文
    source_location = Column(String(200))  # 在文档中的位置
    
    # Nebula同步
    nebula_vertex_id = Column(String(100), nullable=True)
    synced_to_nebula = Column(Boolean, default=False)
    
    # 置信度
    confidence = Column(String(20), default="high")  # high, medium, low
    
    created_at = Column(DateTime, default=datetime.utcnow)
    extracted_by = Column(String(100), nullable=True)  # 使用的模型或规则


class ExtractedRelation(Base):
    """从文本中提取的关系记录"""
    __tablename__ = "extracted_relations"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 关联的文件
    file_id = Column(Integer, ForeignKey("file_records.id"), nullable=True)
    
    # 关系信息
    relation_id = Column(Integer, ForeignKey("ontology_relations.id"), nullable=False)
    
    # 关系两端
    source_entity_id = Column(Integer, ForeignKey("extracted_entities.id"), nullable=False)
    target_entity_id = Column(Integer, ForeignKey("extracted_entities.id"), nullable=False)
    
    # 属性值
    properties = Column(JSON, default=dict)
    
    # 来源信息
    source_text = Column(Text)
    
    # Nebula同步
    nebula_edge_id = Column(String(100), nullable=True)
    synced_to_nebula = Column(Boolean, default=False)
    
    # 置信度
    confidence = Column(String(20), default="high")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    extracted_by = Column(String(100), nullable=True)


class SyncLog(Base):
    """同步日志表"""
    __tablename__ = "sync_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    sync_type = Column(String(50), nullable=False)  # ontology, entity, relation
    target = Column(String(50), nullable=False)  # nebula, chromadb
    status = Column(String(20), nullable=False)  # success, failed, partial
    
    # 同步详情
    total_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    
    # 错误信息
    error_message = Column(Text, nullable=True)
    details = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)


# 数据库依赖
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# 初始化数据库
async def init_db():
    """初始化数据库 - 自动创建所有表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("数据库表创建/更新完成")


async def init_default_data(db: AsyncSession):
    """初始化默认数据"""
    try:
        # 检查是否已有属性类型
        from app.database import PropertyType, PropertyTypeStatus
        from sqlalchemy import select, func
        
        result = await db.execute(select(func.count()).select_from(PropertyType))
        count = result.scalar()
        
        if count == 0:
            logger.info("正在初始化默认属性类型...")
            
            default_types = [
                {
                    "name": "string",
                    "display_name": "字符串",
                    "description": "文本字符串类型",
                    "data_type": "string",
                    "required": False,
                    "unique": False,
                    "indexable": True,
                    "is_system": True,
                    "status": PropertyTypeStatus.ACTIVE
                },
                {
                    "name": "integer",
                    "display_name": "整数",
                    "description": "整数类型",
                    "data_type": "integer",
                    "required": False,
                    "unique": False,
                    "indexable": True,
                    "is_system": True,
                    "status": PropertyTypeStatus.ACTIVE
                },
                {
                    "name": "float",
                    "display_name": "浮点数",
                    "description": "浮点数类型",
                    "data_type": "float",
                    "required": False,
                    "unique": False,
                    "indexable": True,
                    "is_system": True,
                    "status": PropertyTypeStatus.ACTIVE
                },
                {
                    "name": "boolean",
                    "display_name": "布尔值",
                    "description": "布尔值类型（是/否）",
                    "data_type": "boolean",
                    "required": False,
                    "unique": False,
                    "indexable": False,
                    "is_system": True,
                    "status": PropertyTypeStatus.ACTIVE
                },
                {
                    "name": "datetime",
                    "display_name": "日期时间",
                    "description": "日期时间类型",
                    "data_type": "datetime",
                    "required": False,
                    "unique": False,
                    "indexable": True,
                    "is_system": True,
                    "status": PropertyTypeStatus.ACTIVE
                },
                {
                    "name": "text",
                    "display_name": "长文本",
                    "description": "长文本类型，适用于大段文字",
                    "data_type": "text",
                    "required": False,
                    "unique": False,
                    "indexable": False,
                    "is_system": True,
                    "status": PropertyTypeStatus.ACTIVE
                },
                {
                    "name": "enum",
                    "display_name": "枚举",
                    "description": "枚举类型，从预定义选项中选择",
                    "data_type": "enum",
                    "required": False,
                    "unique": False,
                    "indexable": True,
                    "is_system": True,
                    "status": PropertyTypeStatus.ACTIVE
                },
                {
                    "name": "url",
                    "display_name": "URL链接",
                    "description": "URL链接类型",
                    "data_type": "string",
                    "required": False,
                    "unique": False,
                    "indexable": False,
                    "is_system": True,
                    "validation_rules": {"format": "url"},
                    "status": PropertyTypeStatus.ACTIVE
                },
                {
                    "name": "email",
                    "display_name": "邮箱",
                    "description": "电子邮箱类型",
                    "data_type": "string",
                    "required": False,
                    "unique": True,
                    "indexable": True,
                    "is_system": True,
                    "validation_rules": {"format": "email"},
                    "status": PropertyTypeStatus.ACTIVE
                },
                {
                    "name": "phone",
                    "display_name": "电话",
                    "description": "电话号码类型",
                    "data_type": "string",
                    "required": False,
                    "unique": False,
                    "indexable": True,
                    "is_system": True,
                    "validation_rules": {"format": "phone"},
                    "status": PropertyTypeStatus.ACTIVE
                }
            ]
            
            for type_data in default_types:
                db_obj = PropertyType(**type_data)
                db.add(db_obj)
            
            await db.commit()
            logger.info(f"已创建 {len(default_types)} 个默认属性类型")
        else:
            logger.info(f"已存在 {count} 个属性类型，跳过初始化")
            
    except Exception as e:
        logger.error(f"初始化默认数据失败: {e}")
        await db.rollback()
        raise
