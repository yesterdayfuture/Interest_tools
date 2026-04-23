# 电商客服图谱系统

一个基于FastAPI、Nebula Graph、OpenAI和SQLite构建的电商客服知识图谱系统，支持本体管理、实体提取、RAG检索和知识图谱构建。

## 📋 目录

- [功能特性](#功能特性)
- [系统架构](#系统架构)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [核心设计](#核心设计)
- [实现细节](#实现细节)
- [快速开始](#快速开始)
- [API文档](#api文档)
- [部署指南](#部署指南)

## ✨ 功能特性

### 1. 本体定义管理（Ontology Management）

**功能列表：**
- ✅ 支持实体、关系、属性三种本体类型
- ✅ 树状结构组织，支持层级关系
- ✅ 本体合并功能，支持相似本体融合
- ✅ 属性类型管理，预定义10种常用数据类型
- ✅ 版本控制和变更历史

**使用场景：**
- 定义电商领域的实体类型（商品、客户、订单等）
- 定义实体间关系（购买、推荐、投诉等）
- 管理实体属性（价格、颜色、状态等）

### 2. 属性类型系统（Property Type System）

**功能列表：**
- ✅ 10种预定义属性类型（字符串、整数、浮点数、布尔值、日期时间、长文本、枚举、URL、邮箱、电话）
- ✅ 自定义属性类型创建
- ✅ 数据类型验证规则
- ✅ 枚举值管理
- ✅ 使用统计追踪

**支持的属性类型：**
| 类型 | 说明 | 验证规则 |
|------|------|----------|
| string | 字符串 | 长度限制 |
| integer | 整数 | 范围限制 |
| float | 浮点数 | 精度控制 |
| boolean | 布尔值 | true/false |
| datetime | 日期时间 | 格式验证 |
| text | 长文本 | 无限制 |
| enum | 枚举 | 预定义选项 |
| url | URL链接 | 格式验证 |
| email | 邮箱 | 格式验证 |
| phone | 电话 | 格式验证 |

### 3. Nebula Graph 集成

**功能列表：**
- ✅ 自动创建Space和Schema
- ✅ 本体定义一键同步到Nebula
- ✅ 实体和关系自动同步
- ✅ 同步日志记录
- ✅ 失败重试机制

**同步策略：**
- 增量同步：只同步变更数据
- 批量处理：提高同步效率
- 事务保证：确保数据一致性

### 4. 文件管理与处理

**功能列表：**
- ✅ 多文件上传（支持拖拽）
- ✅ 多种格式支持（PDF、Word、Excel、PPT、TXT、CSV、MD）
- ✅ 文件内容自动提取
- ✅ 文件元数据管理
- ✅ 文件下载和删除

**支持格式：**
- 文档类：.txt, .pdf, .doc, .docx, .md
- 表格类：.xls, .xlsx, .csv
- 演示类：.ppt, .pptx

### 5. 实体提取服务

**功能列表：**
- ✅ 基于大模型的智能实体提取
- ✅ 支持自定义本体模板
- ✅ 批量文本处理
- ✅ 实体关系联合提取
- ✅ 置信度评分

**处理流程：**
1. 加载本体定义作为提取模板
2. 构建优化Prompt
3. 调用OpenAI API进行提取
4. 解析和验证结果
5. 保存到SQLite和Nebula

### 6. RAG 检索系统

**功能列表：**
- ✅ 多路召回（向量 + 关键词 + QA）
- ✅ 向量检索基于语义相似度
- ✅ BM25关键词匹配
- ✅ QA问答对检索
- ✅ 结果重排序
- ✅ 父子文档索引
- ✅ Trie树前缀匹配

**检索技术栈：**
| 技术 | 用途 |
|------|------|
| ChromaDB | 向量存储和检索 |
| SentenceTransformer | 文本向量化 |
| BM25 | 关键词匹配 |
| Trie树 | 前缀匹配和分词 |
| jieba | 中文分词 |

**多路召回流程：**
```
用户查询
    │
    ├──→ 向量检索（语义相似度）
    ├──→ BM25检索（关键词匹配）
    ├──→ QA匹配（问答对）
    │
    ↓
结果融合与重排序
    │
    ↓
返回Top-K结果
```

### 7. 智能问答（Chat）

**功能列表：**
- ✅ 结合检索和生成的问答
- ✅ 支持知识图谱查询
- ✅ 上下文感知
- ✅ 流式响应

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        前端层                                │
│              (Vue/React/其他前端框架)                        │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/REST
┌──────────────────────▼──────────────────────────────────────┐
│                      FastAPI                                │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐  │
│  │ 本体管理  │ 文件管理  │ 实体提取  │ RAG检索  │ 智能问答  │  │
│  │  Router  │  Router  │  Router  │  Router  │  Router  │  │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘  │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐  │
│  │ CRUD操作 │ 文件处理 │ LLM服务  │ 检索服务 │ 同步服务 │  │
│  │  Service │  Service │  Service │  Service │  Service │  │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┬──────────────┐
        │              │              │              │
┌───────▼──────┐ ┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐
│   SQLite     │ │  Nebula   │ │  ChromaDB │ │  OpenAI   │
│  (本体定义)   │ │  (知识图谱)│ │ (向量存储) │ │  (大模型)  │
└──────────────┘ └───────────┘ └───────────┘ └───────────┘
```

## 🛠️ 技术栈

### 后端框架
- **FastAPI**: 高性能异步Web框架
- **Pydantic**: 数据验证和序列化
- **SQLAlchemy 2.0**: 异步ORM框架

### 数据库
- **SQLite + aiosqlite**: 关系型数据存储
- **Nebula Graph**: 图数据库存储
- **ChromaDB**: 向量数据库存储

### AI/ML
- **OpenAI API**: 大语言模型调用
- **SentenceTransformers**: 文本向量化
- **jieba**: 中文分词
- **rank-bm25**: BM25算法实现

### 数据处理
- **pypdf**: PDF处理
- **python-docx**: Word文档处理
- **openpyxl**: Excel处理
- **pandas**: 数据分析和处理

## 📁 项目结构

```
.
├── app/                          # 应用核心代码
│   ├── __init__.py
│   ├── config.py                 # 配置管理
│   ├── database.py               # 数据库模型
│   ├── schemas.py                # Pydantic模型
│   ├── crud.py                   # CRUD操作
│   ├── nebula_client.py          # Nebula Graph客户端
│   ├── file_processor.py         # 文件处理
│   ├── extraction_service.py     # 实体提取服务
│   ├── sync_service.py           # 数据同步服务
│   ├── rag_service.py            # RAG检索服务
│   └── routers/                  # API路由
│       ├── __init__.py
│       ├── ontology.py           # 本体管理路由
│       ├── property_types.py     # 属性类型路由
│       ├── files.py              # 文件管理路由
│       ├── extraction.py         # 实体提取路由
│       └── rag.py                # RAG检索路由
├── data/                         # 数据目录
│   ├── ontology.db               # SQLite数据库
│   └── chroma_db/                # ChromaDB存储
├── uploads/                      # 上传文件存储
├── tests/                        # 测试代码
├── .env                          # 环境变量配置
├── .env.example                  # 环境变量示例
├── main.py                       # 应用入口
├── requirements.txt              # Python依赖
├── Dockerfile                    # Docker配置
├── docker-compose.yml            # Docker Compose配置
└── README.md                     # 项目文档
```

## 🎨 核心设计

### 1. 分层架构设计

```
┌─────────────────────────────────────┐
│  Router层 (API接口)                  │
│  - 处理HTTP请求/响应                 │
│  - 参数验证和转换                    │
│  - 调用Service层                     │
├─────────────────────────────────────┤
│  Service层 (业务逻辑)                │
│  - 实现业务功能                      │
│  - 协调多个CRUD操作                  │
│  - 调用外部服务                      │
├─────────────────────────────────────┤
│  CRUD层 (数据操作)                   │
│  - 数据库增删改查                    │
│  - SQLAlchemy ORM封装                │
│  - 事务管理                          │
├─────────────────────────────────────┤
│  Model层 (数据模型)                  │
│  - SQLAlchemy模型定义                │
│  - 数据库表结构                      │
│  - 关系定义                          │
└─────────────────────────────────────┘
```

### 2. 本体树状结构设计

**设计思路：**
- 使用 `parent_id` 建立父子关系
- 使用 `level` 字段记录节点深度
- 使用 `path` 字段记录完整路径（如 "/1/2/3"）
- 支持任意层级的嵌套

**表结构设计：**
```python
class OntologyDefinition(Base):
    id = Column(Integer, primary_key=True)
    name = Column(String(100))           # 唯一标识名
    display_name = Column(String(200))   # 显示名称
    parent_id = Column(Integer, ForeignKey("ontology_definitions.id"))  # 父节点
    level = Column(Integer, default=0)   # 层级深度
    path = Column(String(500), default="")  # 路径 "/1/2/3"
    ontology_type = Column(Enum(OntologyType))  # 类型：实体/关系/属性
```

### 3. 属性类型系统设计

**设计思路：**
- 属性类型独立管理，可复用
- 支持数据类型验证规则
- 支持枚举值定义
- 标记系统预定义类型

**核心字段：**
```python
class PropertyType(Base):
    name = Column(String(100))           # 类型标识
    data_type = Column(String(50))       # 数据类型
    validation_rules = Column(JSON)      # 验证规则
    enum_values = Column(JSON)           # 枚举值
    is_system = Column(Boolean)          # 是否系统预定义
```

### 4. RAG多路召回设计

**设计思路：**
- 多种检索方式并行执行
- 结果融合和去重
- 重排序优化
- 支持过滤条件

**召回策略：**
1. **向量召回**: 基于语义相似度，适合同义不同词的查询
2. **BM25召回**: 基于关键词匹配，适合精确匹配
3. **QA召回**: 基于问答对匹配，适合常见问题
4. **Trie树**: 基于前缀匹配，适合自动补全

### 5. 数据同步设计

**SQLite → Nebula Graph 同步：**

| SQLite | Nebula Graph |
|--------|-------------|
| OntologyDefinition (Entity) | Tag |
| OntologyDefinition (Relation) | Edge Type |
| OntologyProperty | Tag属性 |
| ExtractedEntity | Vertex |
| ExtractedRelation | Edge |

**同步策略：**
- 增量同步：只同步未同步或已变更的数据
- 批量处理：每批100条，减少网络往返
- 失败重试：失败记录单独处理，不阻塞整体流程

## 🔧 实现细节

### 1. 数据库初始化

**自动建表流程：**
```python
async def lifespan(app: FastAPI):
    # 1. 创建必要目录
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(settings.SQLITE_DB_PATH), exist_ok=True)
    
    # 2. 初始化数据库表
    await init_db()  # SQLAlchemy自动建表
    
    # 3. 初始化默认数据
    async with AsyncSessionLocal() as db:
        await init_default_data(db)  # 创建10个默认属性类型
    
    # 4. 初始化Nebula
    if await nebula_client.connect():
        nebula_client.ensure_space()  # 自动创建Space
        nebula_client.init_basic_schema()  # 创建基础Tag/Edge
```

### 2. 实体提取实现

**Prompt工程：**
```python
async def extract_from_text(self, text: str, ontology_ids: List[int]):
    # 1. 构建本体描述
    ontology_desc = self._build_ontology_description(ontologies)
    
    # 2. 构建系统Prompt
    system_prompt = f"""
    你是一个专业的信息提取助手。请从文本中提取以下类型的实体：
    {ontology_desc}
    
    请以JSON格式返回提取结果。
    """
    
    # 3. 调用大模型
    response = await self.client.chat.completions.create(
        model=self.model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]
    )
    
    # 4. 解析结果
    result = json.loads(response.choices[0].message.content)
    
    # 5. 验证和保存
    validated_entities = self._validate_entities(result["entities"])
    await self._save_entities(validated_entities)
```

### 3. RAG检索实现

**多路召回代码结构：**
```python
def query(self, query_text: str, top_k: int = 5):
    results = {
        "vector_results": [],
        "keyword_results": [],
        "qa_results": [],
        "final_results": []
    }
    
    # 1. 向量召回
    results["vector_results"] = self._vector_search(query_text, top_k)
    
    # 2. BM25召回
    results["keyword_results"] = self._bm25_search(query_text, top_k)
    
    # 3. QA召回
    results["qa_results"] = self._qa_search(query_text, top_k)
    
    # 4. 结果融合
    merged = self._merge_results(results)
    
    # 5. 重排序
    results["final_results"] = self._rerank(merged, query_text)
    
    return results
```

### 4. 文件处理实现

**多格式支持：**
```python
class FileProcessor:
    async def process(self, file_path: str, file_extension: str) -> str:
        processors = {
            '.txt': self._process_text,
            '.pdf': self._process_pdf,
            '.docx': self._process_word,
            '.xlsx': self._process_excel,
            '.pptx': self._process_ppt,
        }
        
        processor = processors.get(file_extension.lower())
        if processor:
            return await processor(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {file_extension}")
```

### 5. 嵌入模型配置

**独立配置支持：**
```python
class Settings(BaseSettings):
    # 通用OpenAI配置
    OPENAI_API_KEY: str
    OPENAI_BASE_URL: str
    
    # 嵌入模型独立配置（可选）
    EMBEDDING_API_KEY: Optional[str] = None  # 为空则使用OPENAI_API_KEY
    EMBEDDING_BASE_URL: Optional[str] = None  # 为空则使用OPENAI_BASE_URL
    EMBEDDING_MODEL_NAME: str = "text-embedding-ada-002"
```

## 🚀 快速开始

### 1. 环境准备

**系统要求：**
- Python 3.9+
- Nebula Graph 3.x (可选，用于知识图谱功能)
- 4GB+ RAM

**安装依赖：**
```bash
# 克隆项目
git clone <repository-url>
cd kg_from_unstructure_text

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置文件

**复制环境变量模板：**
```bash
cp .env.example .env
```

**编辑 .env 文件：**
```env
# 应用配置
DEBUG=true

# SQLite配置
SQLITE_DB_PATH=./data/ontology.db

# Nebula Graph配置（可选）
NEBULA_HOST=127.0.0.1
NEBULA_PORT=9669
NEBULA_USER=root
NEBULA_PASSWORD=nebula
NEBULA_SPACE=customer_service

# OpenAI配置（必填）
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4

# 嵌入模型配置（可选，为空则使用OpenAI配置）
EMBEDDING_API_KEY=
EMBEDDING_BASE_URL=
EMBEDDING_MODEL_NAME=text-embedding-ada-002

# ChromaDB配置
CHROMA_DB_PATH=./data/chroma_db

# 文件上传配置
UPLOAD_DIR=./uploads
MAX_FILE_SIZE=52428800
```

### 3. 启动服务

**方式一：直接启动**
```bash
# 启动服务
python main.py

# 或使用uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**方式二：Docker启动**
```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 4. 访问服务

- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

## 📚 API文档

### 本体管理 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/ontology/definitions` | 创建本体定义 |
| GET | `/api/v1/ontology/definitions` | 获取本体列表 |
| GET | `/api/v1/ontology/definitions/tree` | 获取本体树 |
| GET | `/api/v1/ontology/definitions/{id}` | 获取本体详情 |
| PUT | `/api/v1/ontology/definitions/{id}` | 更新本体 |
| DELETE | `/api/v1/ontology/definitions/{id}` | 删除本体 |
| POST | `/api/v1/ontology/definitions/{id}/merge` | 合并本体 |
| POST | `/api/v1/ontology/sync` | 同步到Nebula |

### 属性类型 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/property-types` | 创建属性类型 |
| GET | `/api/v1/property-types` | 获取属性类型列表 |
| GET | `/api/v1/property-types/{id}` | 获取属性类型详情 |
| PUT | `/api/v1/property-types/{id}` | 更新属性类型 |
| DELETE | `/api/v1/property-types/{id}` | 删除属性类型 |
| GET | `/api/v1/property-types/{id}/usage` | 查看使用情况 |
| POST | `/api/v1/property-types/init-defaults` | 初始化默认类型 |

### 文件管理 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/files/upload` | 上传文件 |
| GET | `/api/v1/files` | 获取文件列表 |
| GET | `/api/v1/files/{id}` | 获取文件详情 |
| GET | `/api/v1/files/{id}/download` | 下载文件 |
| DELETE | `/api/v1/files/{id}` | 删除文件 |
| POST | `/api/v1/files/{id}/process` | 处理文件 |

### 实体提取 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/extraction/extract` | 提取实体和关系 |
| POST | `/api/v1/extraction/batch-extract` | 批量提取 |
| GET | `/api/v1/extraction/entities` | 获取实体列表 |
| GET | `/api/v1/extraction/relations` | 获取关系列表 |

### RAG检索 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/rag/query` | RAG查询 |
| POST | `/api/v1/rag/chat` | 智能问答 |
| POST | `/api/v1/rag/index` | 建立索引 |
| DELETE | `/api/v1/rag/index/{file_id}` | 删除索引 |
| GET | `/api/v1/rag/stats` | 获取统计信息 |

## 🐳 部署指南

### Docker部署

**1. 构建镜像：**
```bash
docker build -t kg-service:latest .
```

**2. 运行容器：**
```bash
docker run -d \
  --name kg-service \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/uploads:/app/uploads \
  -e OPENAI_API_KEY=your_key \
  kg-service:latest
```

**3. Docker Compose（推荐）：**
```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./uploads:/app/uploads
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - NEBULA_HOST=nebula-graph
    depends_on:
      - nebula-graph
      
  nebula-graph:
    image: vesoft/nebula-graph:v3.6.0
    ports:
      - "9669:9669"
```

### 生产环境部署

**使用Gunicorn + Uvicorn：**
```bash
gunicorn main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

**使用Nginx反向代理：**
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 📄 License

[MIT License](LICENSE)

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

## 📧 联系方式

如有问题，请提交Issue或联系维护者。

---

**注意：** 本项目仅供学习和研究使用，生产环境使用请自行评估风险。