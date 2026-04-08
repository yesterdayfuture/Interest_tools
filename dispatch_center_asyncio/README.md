# Task Scheduler Center - 任务调度中心

一个基于 FastAPI 开发的高性能任务调度系统，采用标准工程化项目结构，支持任务并发控制、状态管理和统计分析。

## 功能特性

- **任务调度**: 支持异步任务提交和执行，最大并发数可控（默认10个）
- **状态管理**: 完整的任务生命周期管理（pending → running → completed/failed/cancelled）
- **数据持久化**: 使用 SQLite 数据库存储任务信息
- **灵活查询**: 支持多维度过滤和分页查询
- **统计分析**: 实时任务统计和成功率计算
- **RESTful API**: 完整的 HTTP API 接口，支持 API 版本控制

## 技术栈

- **Web 框架**: FastAPI 0.104.1
- **数据库**: SQLite + SQLAlchemy 2.0（异步支持）
- **数据验证**: Pydantic 2.x
- **并发控制**: asyncio.Semaphore
- **服务器**: Uvicorn

## 项目结构

```
app/
├── api/                    # API 层
│   ├── deps.py            # 依赖注入
│   └── v1/                # API v1 版本
│       ├── api.py         # 路由聚合
│       └── tasks.py       # 任务相关接口
├── core/                   # 核心配置
│   ├── config.py          # 应用配置
│   ├── exceptions.py      # 自定义异常
│   └── logging.py         # 日志配置
├── db/                     # 数据库层
│   ├── base.py            # ORM 基类
│   └── session.py         # 数据库会话
├── models/                 # 数据模型层
│   └── task.py            # 任务模型
├── schemas/                # 数据验证层
│   └── task.py            # 任务相关 Schema
├── services/               # 业务逻辑层
│   ├── task_scheduler.py  # 任务调度器
│   └── task_service.py    # 任务服务
├── utils/                  # 工具函数
└── main.py                # 应用入口

tests/                      # 测试目录
```

## 架构设计

### 分层架构

```
┌─────────────────────────────────────────┐
│              API Layer                  │
│  (routers, request/response handling)   │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│           Service Layer                 │
│  (business logic, task scheduling)      │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│           Data Access Layer             │
│  (models, database operations)          │
└─────────────────────────────────────────┘
```

### 模块职责

| 模块 | 职责 |
|------|------|
| `api/` | HTTP 请求处理、路由定义、依赖注入 |
| `core/` | 配置管理、日志、异常定义 |
| `db/` | 数据库连接、会话管理 |
| `models/` | 数据库模型定义 |
| `schemas/` | 数据验证和序列化 |
| `services/` | 业务逻辑实现 |

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动服务

```bash
python start.py
```

服务将在 `http://localhost:8000` 启动，API 文档访问 `http://localhost:8000/docs`

## API 接口文档

**基础路径**: `/api/v1`

### 1. 提交任务

```http
POST /api/v1/tasks/submit
Content-Type: application/json

{
    "name": "任务名称",
    "description": "任务描述",
    "task_type": "任务类型",
    "priority": 5,
    "payload": {"key": "value"}
}
```

**响应示例**:
```json
{
    "success": true,
    "message": "Task submitted successfully",
    "task_id": "uuid-string",
    "data": { ... }
}
```

### 2. 任务列表查询

```http
GET /api/v1/tasks/list?page=1&page_size=10&status=pending&name=keyword
```

**查询参数**:
- `page`: 页码（默认1）
- `page_size`: 每页数量（默认10，最大100）
- `task_id`: 任务ID精确匹配
- `name`: 任务名称模糊查询
- `status`: 任务状态过滤（pending/running/completed/failed/cancelled）
- `task_type`: 任务类型过滤
- `priority_min/max`: 优先级范围
- `created_after/before`: 创建时间范围

### 3. 获取任务详情

```http
GET /api/v1/tasks/{task_id}
```

### 4. 更新任务

```http
PUT /api/v1/tasks/{task_id}
Content-Type: application/json

{
    "name": "新名称",
    "priority": 10
}
```

### 5. 删除任务

```http
DELETE /api/v1/tasks/{task_id}
```

### 6. 取消任务

```http
POST /api/v1/tasks/{task_id}/cancel
```

### 7. 任务统计

```http
GET /api/v1/tasks/statistics/overview
```

**响应示例**:
```json
{
    "total_tasks": 100,
    "pending_count": 10,
    "running_count": 5,
    "completed_count": 80,
    "failed_count": 3,
    "cancelled_count": 2,
    "success_rate": 96.39,
    "average_execution_time": 5.23
}
```

## 设计思路

### 1. 并发控制架构

```
┌─────────────────────────────────────────────────────────┐
│                    Task Scheduler                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │        asyncio.Semaphore(max=10)                │   │
│  │  ┌─────┐ ┌─────┐ ┌─────┐ ... ┌─────┐           │   │
│  │  │Task1│ │Task2│ │Task3│     │Task10│          │   │
│  │  └─────┘ └─────┘ └─────┘     └─────┘           │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  新任务 → 等待信号量 → 获取信号量 → 执行 → 释放信号量    │
└─────────────────────────────────────────────────────────┘
```

- 使用 `asyncio.Semaphore` 实现轻量级并发控制
- 任务提交后立即返回，异步执行不阻塞 HTTP 响应
- 信号量机制确保同时最多10个任务在执行，其余任务排队等待

### 2. 任务状态流转

```
                    submit
                       │
                       ▼
    ┌─────────┐   start   ┌─────────┐
    │ PENDING │ ─────────▶│ RUNNING │
    └────┬────┘           └────┬────┘
         │                     │
    cancel│              ┌──────┴──────┐
         │              │             │
         ▼              ▼             ▼
    ┌─────────┐    ┌─────────┐  ┌─────────┐
    │CANCELLED│    │COMPLETED│  │ FAILED  │
    └─────────┘    └─────────┘  └─────────┘
```

### 3. 依赖注入设计

```python
# app/api/deps.py
DbSession = Annotated[AsyncSession, Depends(get_db)]

async def get_task_service(db: DbSession) -> TaskService:
    return TaskService(db)

TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
```

使用 FastAPI 的依赖注入系统实现：
- 数据库会话管理
- 服务层实例化
- 便于单元测试时 Mock

### 4. 异常处理

```python
# app/core/exceptions.py
class AppException(HTTPException):
    def __init__(self, status_code: int, detail: str, headers: dict = None):
        super().__init__(status_code=status_code, detail=detail, headers=headers)

class TaskNotFoundException(AppException):
    def __init__(self, task_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found"
        )
```

统一的异常处理机制：
- 业务异常继承自 `AppException`
- 自动转换为 HTTP 响应
- 便于维护和扩展

### 5. 配置管理

```python
# app/core/config.py
class Settings(BaseSettings):
    app_name: str = "Task Scheduler Center"
    max_concurrent_tasks: int = 10
    database_url: str = "sqlite+aiosqlite:///./tasks.db"
    
    class Config:
        env_file = ".env"
```

使用 Pydantic Settings：
- 环境变量自动加载
- 类型安全验证
- 支持 `.env` 文件

### 6. 日志配置

```python
# app/core/logging.py
def setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format=settings.log_format,
        handlers=[logging.StreamHandler(sys.stdout)],
    )
```

统一的日志管理：
- 可配置的日志级别
- 统一的格式
- 模块级日志器

## 扩展建议

### 1. 自定义任务处理器

```python
from app.services.task_scheduler import task_scheduler

async def my_custom_handler(task_id: str, payload: dict):
    # 实现自定义任务逻辑
    await process_data(payload)

# 注册处理器
task_scheduler.register_handler("my_task_type", my_custom_handler)
```

### 2. 更换数据库

修改 `app/core/config.py` 中的数据库连接字符串：

```python
# MySQL
DATABASE_URL = "mysql+aiomysql://user:pass@localhost/dbname"

# PostgreSQL
DATABASE_URL = "postgresql+asyncpg://user:pass@localhost/dbname"
```

### 3. 调整并发数

修改 `app/core/config.py`：

```python
max_concurrent_tasks = 20  # 调整为20个并发
```

### 4. 添加新的 API 版本

```
app/api/
├── deps.py
├── v1/
│   ├── api.py
│   └── tasks.py
└── v2/              # 新版本
    ├── api.py
    └── tasks.py
```

## 性能考虑

1. **连接池**: SQLAlchemy 内置连接池管理
2. **索引优化**: 常用查询字段均已建立索引
3. **异步执行**: 所有 I/O 操作均为异步，避免阻塞
4. **信号量控制**: 防止资源耗尽，保证系统稳定性
5. **依赖注入**: 避免重复创建对象，提高性能

## 测试

```bash
# 运行测试
pytest tests/

# 带覆盖率
pytest --cov=app tests/
```

## 部署建议

### 生产环境启动

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker 部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 许可证

MIT License
