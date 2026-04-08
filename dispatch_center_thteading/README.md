# Task Scheduler Center - 任务调度中心

一个基于 FastAPI 开发的高性能任务调度系统，采用 **ThreadPoolExecutor** 线程池实现并发控制，支持任务并发执行、状态管理和统计分析。

## 功能特性

- **任务调度** : 支持异步任务提交和执行，最大并发数可控（默认10个线程）
- **状态管理** : 完整的任务生命周期管理（pending → running → completed/failed/cancelled）
- **数据持久化** : 使用 SQLite 数据库存储任务信息
- **灵活查询** : 支持多维度过滤和分页查询
- **统计分析** : 实时任务统计和成功率计算
- **RESTful API** : 完整的 HTTP API 接口，支持 API 版本控制

## 技术栈

- **Web 框架** : FastAPI 0.104.1
- **数据库** : SQLite + SQLAlchemy 2.0（异步支持）
- **数据验证** : Pydantic 2.x
- **并发控制** : ThreadPoolExecutor（线程池）
- **服务器** : Uvicorn

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
│   ├── task_scheduler.py  # 任务调度器（ThreadPoolExecutor）
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

### 配置环境变量

复制 `.env.example` 为 `.env` 并根据需要修改：

```bash
cp .env.example .env
```

### 启动服务

```bash
python start.py
```

服务将在 `http://localhost:8000` 启动，API 文档访问 `http://localhost:8000/docs`

## API 接口文档

**基础路径** : `/api/v1`

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

**响应示例** :
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

**查询参数** :
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

**响应示例** :
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

### 1. 并发控制架构（ThreadPoolExecutor）

```
┌─────────────────────────────────────────────────────────┐
│                    Task Scheduler                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │        ThreadPoolExecutor(max_workers=10)       │   │
│  │  ┌─────┐ ┌─────┐ ┌─────┐ ... ┌─────┐           │   │
│  │  │Task1│ │Task2│ │Task3│     │Task10│          │   │
│  │  └─────┘ └─────┘ └─────┘     └─────┘           │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  新任务 → 提交到线程池 → 线程执行 → 返回结果            │
└─────────────────────────────────────────────────────────┘
```

- 使用 `ThreadPoolExecutor` 实现线程池并发控制
- 任务提交后立即返回，异步执行不阻塞 HTTP 响应
- 线程池机制确保同时最多10个任务在执行，其余任务排队等待

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

## 配置说明

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `APP_NAME` | Task Scheduler Center | 应用名称 |
| `APP_VERSION` | 1.0.0 | 应用版本 |
| `DEBUG` | true | 调试模式 |
| `HOST` | 0.0.0.0 | 服务器主机 |
| `PORT` | 8000 | 服务器端口 |
| `DATABASE_URL` | sqlite+aiosqlite:///./tasks.db | 数据库连接 |
| `MAX_CONCURRENT_TASKS` | 10 | 最大并发任务数 |
| `TASK_TIMEOUT_SECONDS` | 300 | 任务超时时间 |
| `LOG_LEVEL` | INFO | 日志级别 |

## 开发指南

### 添加新的任务类型

在 `app/services/task_service.py` 中修改 `_execute_task` 方法：

```python
@staticmethod
async def _execute_task(task_id: str, task_type: str, payload: Dict[str, Any]):
    if task_type == "my_custom_type":
        # 实现自定义任务逻辑
        return await my_custom_handler(payload)
    # ...
```

### 自定义任务处理器

```python
async def my_custom_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
    # 处理任务逻辑
    return {"result": "success"}
```

## 许可证

MIT License
