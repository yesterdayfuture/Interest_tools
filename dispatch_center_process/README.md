# Task Scheduler Center - 任务调度中心

一个基于 FastAPI 开发的高性能多进程任务调度系统，采用标准工程化项目结构，支持真正的并行任务执行、进程池管理和实时监控。

## 功能特性

- **多进程并行调度** : 基于 multiprocessing 实现真正的并行任务执行，充分利用多核 CPU
- **进程池管理** : 可配置的工作进程数量，支持动态扩缩容
- **任务调度** : 支持异步任务提交和执行，任务在独立进程中运行
- **状态管理** : 完整的任务生命周期管理（pending → running → completed/failed/cancelled）
- **数据持久化** : 使用 SQLite 数据库存储任务信息
- **灵活查询** : 支持多维度过滤和分页查询
- **统计分析** : 实时任务统计和成功率计算
- **RESTful API** : 完整的 HTTP API 接口，支持 API 版本控制
- **进程监控** : 实时监控工作进程状态和任务执行情况

## 技术栈

- **Web 框架** : FastAPI 0.104.1
- **数据库** : SQLite + SQLAlchemy 2.0（异步支持）
- **数据验证** : Pydantic 2.x
- **并发控制** : multiprocessing + asyncio
- **进程通信** : multiprocessing.Queue
- **服务器** : Uvicorn

## 项目结构

```
app/
├── api/                    # API 层
│   ├── deps.py            # 依赖注入
│   └── v1/                # API v1 版本
│       ├── api.py         # 路由聚合
│       ├── scheduler.py   # 多进程调度器接口
│       └── tasks.py       # 任务相关接口
├── core/                   # 核心配置
│   ├── config.py          # 应用配置
│   ├── exceptions.py      # 自定义异常
│   ├── logging.py         # 日志配置
│   └── process_config.py  # 多进程配置
├── db/                     # 数据库层
│   ├── base.py            # ORM 基类
│   └── session.py         # 数据库会话
├── models/                 # 数据模型层
│   └── task.py            # 任务模型
├── schemas/                # 数据验证层
│   └── task.py            # 任务相关 Schema
├── services/               # 业务逻辑层
│   ├── multi_process_scheduler.py  # 多进程调度器
│   ├── process_manager.py # 进程管理器
│   ├── task_scheduler.py  # 任务调度器（兼容）
│   ├── task_service.py    # 任务服务
│   └── worker.py          # 工作进程实现
├── utils/                  # 工具函数
└── main.py                # 应用入口

tests/                      # 测试目录
```

## 架构设计

### 多进程调度架构

```
┌─────────────────────────────────────────────────────────────┐
│                      主进程 (Master)                         │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐ │
│  │   API 服务   │  │  任务调度中心  │  │    结果处理器        │ │
│  │  FastAPI    │  │              │  │                     │ │
│  └──────┬──────┘  └──────┬───────┘  └─────────────────────┘ │
│         │                │                                   │
│         ▼                ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              任务队列 (multiprocessing.Queue)             ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Worker-0    │    │  Worker-1    │    │  Worker-2    │
│  (独立进程)   │    │  (独立进程)   │    │  (独立进程)   │
│              │    │              │    │              │
│ • CPU密集型   │    │ • IO密集型    │    │ • 数据处理    │
│ • 任务执行    │    │ • 任务执行    │    │ • 任务执行    │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           ▼
              ┌──────────────────────┐
              │   结果队列 (Queue)    │
              └──────────────────────┘
```

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
│  - MultiProcessScheduler                │
│  - ProcessManager                       │
│  - TaskWorker                           │
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
| `services/` | 业务逻辑实现，包括多进程调度 |

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境变量

复制 `.env.example` 为 `.env` 并根据需要修改配置：

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

### 任务管理接口

#### 1. 提交任务（多进程调度器）

```http
POST /api/v1/scheduler/submit
Content-Type: application/json

{
    "name": "任务名称",
    "description": "任务描述",
    "task_type": "default",
    "priority": 5,
    "payload": {"key": "value"}
}
```

**响应示例** :
```json
{
    "success": true,
    "message": "Task submitted to multi-process scheduler successfully",
    "task_id": "uuid-string",
    "data": { ... }
}
```

#### 2. 获取调度器状态

```http
GET /api/v1/scheduler/status
```

**响应示例** :
```json
{
    "success": true,
    "message": "Scheduler status retrieved successfully",
    "data": {
        "running": true,
        "workers": [
            {
                "worker_id": "worker-0-xxx",
                "status": "idle",
                "current_task_id": null,
                "pid": 12345,
                "is_alive": true,
                "tasks_completed": 10,
                "tasks_failed": 0
            }
        ],
        "pending_tasks": 2,
        "running_tasks": 1,
        "completed_tasks": 15,
        "alive_workers": 4,
        "idle_workers": 3
    }
}
```

#### 3. 取消任务

```http
POST /api/v1/scheduler/cancel/{task_id}
```

#### 4. 获取任务在调度器中的状态

```http
GET /api/v1/scheduler/task/{task_id}/status
```

### 任务管理接口（兼容）

#### 5. 任务列表查询

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

#### 6. 获取任务详情

```http
GET /api/v1/tasks/{task_id}
```

#### 7. 更新任务

```http
PUT /api/v1/tasks/{task_id}
Content-Type: application/json

{
    "name": "新名称",
    "priority": 10
}
```

#### 8. 删除任务

```http
DELETE /api/v1/tasks/{task_id}
```

#### 9. 任务统计

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

### 1. 多进程调度架构

```
┌─────────────────────────────────────────────────────────┐
│                MultiProcessScheduler                     │
│  ┌─────────────────────────────────────────────────┐   │
│  │           ProcessManager (Worker Pool)          │   │
│  │  ┌─────┐ ┌─────┐ ┌─────┐ ... ┌─────┐           │   │
│  │  │  P0 │ │  P1 │ │  P2 │     │  Pn │            │   │
│  │  └─────┘ └─────┘ └─────┘     └─────┘           │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  新任务 → 任务队列 → 工作进程获取 → 执行 → 结果队列    │
└─────────────────────────────────────────────────────────┘
```

- 使用 `multiprocessing.Process` 创建独立工作进程
- 任务通过 `multiprocessing.Queue` 分发给工作进程
- 工作进程在独立进程中执行任务，真正实现并行
- 结果通过结果队列返回给主进程

### 2. 任务类型支持

系统内置多种任务处理器：

| 任务类型 | 说明 | 适用场景 |
|---------|------|---------|
| `default` | 默认任务处理器 | 通用任务 |
| `cpu_intensive` | CPU 密集型计算 | 数学计算、数据处理 |
| `io_simulation` | IO 模拟任务 | 文件操作、网络请求 |
| `data_processing` | 数据处理任务 | 数据转换、分析 |

### 3. 任务状态流转

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

## 环境变量配置

### 基础配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `APP_NAME` | Task Scheduler Center | 应用名称 |
| `APP_VERSION` | 1.0.0 | 应用版本 |
| `HOST` | 0.0.0.0 | 服务器地址 |
| `PORT` | 8000 | 服务器端口 |
| `DEBUG` | False | 调试模式 |
| `DATABASE_URL` | sqlite+aiosqlite:///./task_scheduler.db | 数据库连接 |
| `LOG_LEVEL` | INFO | 日志级别 |

### 多进程配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `WORKER_COUNT` | 4 | 工作进程数量 |
| `WORKER_MAX_TASKS_PER_CHILD` | 100 | 每个工作进程最大任务数（防止内存泄漏） |
| `TASK_QUEUE_MAX_SIZE` | 1000 | 任务队列最大长度 |
| `RESULT_QUEUE_MAX_SIZE` | 1000 | 结果队列最大长度 |
| `HEARTBEAT_INTERVAL` | 5 | 心跳检测间隔（秒） |
| `WORKER_TIMEOUT` | 30 | 工作进程超时时间（秒） |
| `TASK_TIMEOUT_SECONDS` | 300 | 任务执行超时时间（秒） |
| `MAX_RETRY_COUNT` | 3 | 任务最大重试次数 |

## 开发计划

- [x] 多进程并行任务调度
- [x] 进程池管理和监控
- [x] 任务类型扩展支持
- [ ] 添加任务重试机制
- [ ] 支持定时任务（Cron）
- [ ] 任务优先级队列优化
- [ ] WebSocket 实时推送任务状态
- [ ] 分布式多节点支持
- [ ] 任务执行历史记录

## 许可证

MIT License
