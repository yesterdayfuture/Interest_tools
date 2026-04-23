"""
Pydantic数据模型Schema模块

本模块定义了所有API请求和响应的数据模型，使用Pydantic进行数据验证和序列化。

主要功能：
1. 请求数据验证：确保客户端提交的数据符合要求
2. 响应数据格式化：统一API响应格式
3. 类型转换：自动进行数据类型转换和验证
4. 文档生成：为API文档提供字段说明

Schema分类：
- 枚举定义：OntologyType, OntologyStatus等
- 基础Schema：定义共享的字段结构
- 创建Schema：用于POST请求的入参验证
- 更新Schema：用于PUT/PATCH请求的入参验证
- 响应Schema：用于API响应的数据格式化

使用FastAPI时，直接将Schema作为参数类型或响应模型使用。
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ==================== 基础枚举 ====================
# 这些枚举与database.py中定义的一致，用于API层面的数据验证

class OntologyType(str, Enum):
    """本体定义类型枚举 - 用于API参数验证"""
    ENTITY = "entity"
    RELATION = "relation"
    ATTRIBUTE = "attribute"


class OntologyStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MERGED = "merged"


class FileType(str, Enum):
    DOCUMENT = "document"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"
    OTHER = "other"


class FileStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


# ==================== 本体定义相关Schema ====================

class OntologyPropertyDef(BaseModel):
    """本体属性定义"""
    name: str
    display_name: str
    data_type: str = "string"  # string, integer, float, boolean, datetime, enum
    required: bool = False
    default_value: Optional[str] = None
    enum_values: Optional[List[str]] = None
    validation_rules: Optional[Dict[str, Any]] = None
    description: Optional[str] = None


class OntologyDefinitionBase(BaseModel):
    """本体定义基础Schema"""
    name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    ontology_type: OntologyType
    properties: Dict[str, Any] = Field(default_factory=dict)


class OntologyDefinitionCreate(OntologyDefinitionBase):
    """创建本体定义"""
    parent_id: Optional[int] = None


class OntologyDefinitionUpdate(BaseModel):
    """更新本体定义"""
    display_name: Optional[str] = None
    description: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    status: Optional[OntologyStatus] = None


class OntologyDefinitionResponse(OntologyDefinitionBase):
    """本体定义响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    parent_id: Optional[int]
    level: int
    path: str
    status: OntologyStatus
    nebula_tag: Optional[str]
    nebula_edge: Optional[str]
    synced_to_nebula: bool
    last_sync_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    
    # 树状结构相关
    children: Optional[List['OntologyDefinitionResponse']] = None
    parent: Optional['OntologyDefinitionResponse'] = None


class OntologyDefinitionTree(OntologyDefinitionResponse):
    """树状结构的本体定义"""
    children: List['OntologyDefinitionTree'] = Field(default_factory=list)


class OntologyMergeRequest(BaseModel):
    """合并本体请求"""
    source_ids: List[int]  # 要合并的源本体ID列表
    target_id: int  # 合并到的目标本体ID


# ==================== 属性类型Schema ====================

class PropertyTypeStatus(str, Enum):
    """属性类型状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"


class PropertyTypeBase(BaseModel):
    """属性类型基础Schema"""
    name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    data_type: str = Field(..., min_length=1, max_length=50)  # string, integer, float, boolean, datetime, enum, array, object
    default_value: Optional[str] = None
    enum_values: Optional[List[str]] = None
    validation_rules: Optional[Dict[str, Any]] = None
    required: bool = False
    unique: bool = False
    indexable: bool = False


class PropertyTypeCreate(PropertyTypeBase):
    """创建属性类型"""
    pass


class PropertyTypeUpdate(BaseModel):
    """更新属性类型"""
    display_name: Optional[str] = None
    description: Optional[str] = None
    data_type: Optional[str] = None
    default_value: Optional[str] = None
    enum_values: Optional[List[str]] = None
    validation_rules: Optional[Dict[str, Any]] = None
    required: Optional[bool] = None
    unique: Optional[bool] = None
    indexable: Optional[bool] = None
    status: Optional[PropertyTypeStatus] = None


class PropertyTypeResponse(PropertyTypeBase):
    """属性类型响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    status: PropertyTypeStatus
    is_system: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    
    # 使用该属性类型的本体属性数量
    usage_count: Optional[int] = None


class PropertyTypeListResponse(BaseModel):
    """属性类型列表响应"""
    total: int
    items: List[PropertyTypeResponse]


# ==================== 本体关系Schema ====================

class OntologyRelationBase(BaseModel):
    """本体关系基础Schema"""
    name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    source_type_id: int
    target_type_id: int
    is_directed: bool = True
    properties: Dict[str, Any] = Field(default_factory=dict)


class OntologyRelationCreate(OntologyRelationBase):
    pass


class OntologyRelationUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    is_directed: Optional[bool] = None
    status: Optional[OntologyStatus] = None


class OntologyRelationResponse(OntologyRelationBase):
    """本体关系响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    status: OntologyStatus
    nebula_edge_type: Optional[str]
    synced_to_nebula: bool
    last_sync_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    # 关联的本体信息
    source_type: Optional[OntologyDefinitionResponse] = None
    target_type: Optional[OntologyDefinitionResponse] = None


# ==================== 文件相关Schema ====================

class FileRecordBase(BaseModel):
    """文件记录基础Schema"""
    original_name: str
    file_type: FileType


class FileRecordResponse(FileRecordBase):
    """文件记录响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    filename: str
    file_path: str
    file_size: int
    mime_type: Optional[str]
    file_extension: str
    content_summary: Optional[str]
    status: FileStatus
    processed_at: Optional[datetime]
    processing_error: Optional[str]
    extracted_entities: List[int]
    rag_processed: bool
    created_at: datetime
    updated_at: datetime
    uploaded_by: Optional[str]


class FileListResponse(BaseModel):
    """文件列表响应"""
    total: int
    items: List[FileRecordResponse]


# ==================== 同步相关Schema ====================

class SyncRequest(BaseModel):
    """同步请求"""
    ontology_ids: Optional[List[int]] = None  # 为空则同步全部
    sync_type: str = "all"  # all, entities_only, relations_only, ontology_only


class SyncResponse(BaseModel):
    """同步响应"""
    success: bool
    message: str
    total_count: int
    success_count: int
    failed_count: int
    failed_items: List[Dict[str, Any]] = Field(default_factory=list)


class SyncLogResponse(BaseModel):
    """同步日志响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    sync_type: str
    target: str
    status: str
    total_count: int
    success_count: int
    failed_count: int
    error_message: Optional[str]
    details: Dict[str, Any]
    created_at: datetime


# ==================== 实体提取相关Schema ====================

class EntityExtractRequest(BaseModel):
    """实体提取请求"""
    text: str = Field(..., min_length=1)
    file_id: Optional[int] = None
    ontology_ids: Optional[List[int]] = None  # 指定要提取的本体类型


class ExtractedEntityBase(BaseModel):
    """提取的实体基础Schema"""
    name: str
    ontology_id: int
    properties: Dict[str, Any] = Field(default_factory=dict)
    confidence: str = "high"


class ExtractedEntityCreate(ExtractedEntityBase):
    file_id: Optional[int] = None
    source_text: Optional[str] = None
    source_location: Optional[str] = None


class ExtractedEntityResponse(ExtractedEntityBase):
    """提取的实体响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    file_id: Optional[int]
    source_text: Optional[str]
    source_location: Optional[str]
    nebula_vertex_id: Optional[str]
    synced_to_nebula: bool
    created_at: datetime
    extracted_by: Optional[str]
    
    # 关联的本体信息
    ontology: Optional[OntologyDefinitionResponse] = None


class ExtractedRelationBase(BaseModel):
    """提取的关系基础Schema"""
    relation_id: int
    source_entity_id: int
    target_entity_id: int
    properties: Dict[str, Any] = Field(default_factory=dict)
    confidence: str = "high"


class ExtractedRelationCreate(ExtractedRelationBase):
    file_id: Optional[int] = None
    source_text: Optional[str] = None


class ExtractedRelationResponse(ExtractedRelationBase):
    """提取的关系响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    file_id: Optional[int]
    source_text: Optional[str]
    nebula_edge_id: Optional[str]
    synced_to_nebula: bool
    created_at: datetime
    extracted_by: Optional[str]
    
    # 关联信息
    relation: Optional[OntologyRelationResponse] = None
    source_entity: Optional[ExtractedEntityResponse] = None
    target_entity: Optional[ExtractedEntityResponse] = None


class BatchExtractResponse(BaseModel):
    """批量提取响应"""
    success: bool
    message: str
    entities: List[ExtractedEntityResponse]
    relations: List[ExtractedRelationResponse]


# ==================== RAG相关Schema ====================

class RAGQueryRequest(BaseModel):
    """RAG查询请求"""
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    filters: Optional[Dict[str, Any]] = None
    use_multi_reciprocal: bool = True  # 是否使用多路召回
    use_rerank: bool = True  # 是否使用重排序


class RAGDocument(BaseModel):
    """RAG文档"""
    id: str
    content: str
    metadata: Dict[str, Any]
    score: float
    source: str  # 来源：vector, bm25, qa等


class RAGQueryResponse(BaseModel):
    """RAG查询响应"""
    query: str
    documents: List[RAGDocument]
    total_results: int


class DocumentChunk(BaseModel):
    """文档分块"""
    chunk_id: str
    content: str
    parent_id: Optional[str] = None
    chunk_type: str = "paragraph"  # paragraph, sentence, fixed_size
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RAGIndexRequest(BaseModel):
    """RAG索引请求"""
    file_id: int
    chunk_size: int = 500
    chunk_overlap: int = 50
    use_parent_child: bool = True  # 是否使用父子文档索引


# ==================== 通用响应Schema ====================

class APIResponse(BaseModel):
    """通用API响应"""
    code: int = 200
    message: str = "success"
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """错误响应"""
    code: int = 400
    message: str
    details: Optional[Any] = None


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


# 解决循环引用
OntologyDefinitionResponse.model_rebuild()
OntologyDefinitionTree.model_rebuild()