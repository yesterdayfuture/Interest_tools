# AI Agent API with Human-in-the-Loop

一个结合 FastAPI 和 OpenAI 的智能代理系统，支持用户确认机制（Human-in-the-Loop），确保敏感操作需要人工审批。

## 功能特性

- **用户认证系统**：基于 JWT Token 的用户认证，支持注册、登录、登出
- **任务管理系统**：异步任务执行，支持多任务并行和任务隔离
- **用户确认机制**：敏感操作（文件创建、修改、删除等）需要用户确认
- **WebSocket 实时通知**：任务状态实时推送到前端
- **数据持久化**：SQLite 数据库存储用户和任务信息
- **任务隔离**：不同任务之间完全隔离，互不影响

## 项目结构

```
.
├── app/                      # 主应用包
│   ├── __init__.py          # 包初始化
│   ├── core/                # 核心模块
│   │   ├── config.py        # 配置管理（环境变量、常量）
│   │   ├── database.py      # 数据库操作
│   │   └── security.py      # 安全工具（密码哈希、JWT）
│   ├── models/              # 数据模型
│   │   ├── schemas.py       # Pydantic 请求/响应模型
│   │   └── user.py          # 用户模型
│   ├── routers/             # API 路由
│   │   ├── auth.py          # 认证路由（注册、登录、登出）
│   │   ├── tasks.py         # 任务路由（创建、确认、列表）
│   │   └── pages.py         # 页面路由
│   ├── services/            # 业务逻辑
│   │   ├── task_manager.py  # 任务管理器
│   │   └── service.py       # OpenAI 代理服务
│   ├── static/              # 静态文件目录
│   └── templates/           # HTML 模板
│       └── index.html       # 前端页面
├── main.py                  # 应用入口文件
├── .env                     # 环境变量配置
├── .env.example             # 环境变量示例
├── app.db                   # SQLite 数据库文件（自动创建）
└── README.md                # 项目说明
```

## 快速开始

### 1. 安装依赖

```bash
pip install fastapi uvicorn python-jose python-dotenv openai aiohttp
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，并填写你的配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# OpenAI 配置
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4

# JWT 配置（可选，会自动生成）
JWT_SECRET_KEY=your_secret_key_here

# 数据库配置（可选，默认使用 app.db）
DATABASE_PATH=app.db
```

### 3. 启动服务

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

或直接使用 Python 运行：

```bash
python main.py
```

### 4. 访问应用

打开浏览器访问：http://localhost:8000

## API 文档

启动服务后，访问以下地址查看自动生成的 API 文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 主要接口

#### 认证接口

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /api/auth/register | 用户注册 |
| POST | /api/auth/login | 用户登录 |
| GET | /api/auth/me | 获取当前用户信息 |
| POST | /api/auth/logout | 用户登出 |

#### 任务接口

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /api/task/start | 启动新任务 |
| POST | /api/task/confirm | 确认/拒绝工具调用 |
| GET | /api/task/{task_id}/pending | 获取任务待确认交互 |
| GET | /api/tasks | 获取任务列表 |
| DELETE | /api/task/{task_id} | 取消任务 |
| WebSocket | /ws/{task_id} | 实时通知 |

### 请求示例

#### 启动任务

```bash
curl -X POST http://localhost:8000/api/task/start \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_message": "创建一个 hello.txt 文件"}'
```

#### 确认交互

```bash
curl -X POST http://localhost:8000/api/task/confirm \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "interaction_id": "xxx",
    "approved": true,
    "user_input": null
  }'
```

## 使用说明

### 1. 注册和登录

首次使用需要注册账号，然后登录进入控制台。

### 2. 启动任务

在输入框中输入你的指令，例如：
- "创建一个名为 hello.txt 的文件，内容是 Hello World"
- "列出当前目录的所有文件"
- "读取 README.md 文件的内容"

### 3. 确认敏感操作

当 AI 需要执行敏感操作（如创建、修改、删除文件）时，会弹出确认对话框，你可以选择同意或拒绝。

### 4. 查看任务状态

任务列表会实时显示所有任务的状态：
- **PENDING**: 等待执行
- **RUNNING**: 正在执行
- **WAITING**: 等待用户确认
- **COMPLETED**: 已完成
- **FAILED**: 执行失败
- **CANCELLED**: 已取消

## 支持的工具

- `create_file`: 创建文件
- `modify_file`: 修改文件
- `delete_file`: 删除文件
- `read_file`: 读取文件
- `list_directory`: 列出目录
- `move_file`: 移动文件
- `copy_file`: 复制文件
- `rename_file`: 重命名文件
- `run_command`: 执行命令

## 技术栈

- **后端**: FastAPI, Python 3.8+
- **前端**: HTML5, CSS3, JavaScript (原生)
- **数据库**: SQLite
- **AI 模型**: OpenAI GPT-4
- **认证**: JWT (JSON Web Tokens)

## 开发说明

### 添加新的工具

在 `app/services/service.py` 中的 `OpenAIAgent` 类添加新的工具定义和执行逻辑：

```python
async def _execute_tool(self, tool_name: str, tool_args: dict) -> str:
    if tool_name == "your_new_tool":
        return await self._handle_your_new_tool(tool_args)
    # ...
```

### 修改数据库模型

在 `app/core/database.py` 中修改表结构，系统会自动创建新表。

## 项目架构

### 模块职责

- **app/core/config.py**: 集中管理所有配置项，支持从环境变量读取
- **app/core/database.py**: 提供数据库连接和操作，使用 SQLite
- **app/core/security.py**: 提供密码哈希、JWT 生成和验证
- **app/models/**: 定义数据模型，包括 Pydantic 模型和业务模型
- **app/routers/**: 定义 API 路由，处理 HTTP 请求
- **app/services/**: 实现业务逻辑，包括任务管理和 AI 代理

### 数据流

1. 用户通过前端发送请求到 FastAPI 路由
2. 路由层验证请求并调用服务层
3. 服务层执行业务逻辑，与数据库交互
4. 任务执行过程中通过 WebSocket 推送状态更新
5. 敏感操作需要用户确认后才能继续执行

## 安全说明

- 密码使用 SHA256 哈希存储
- JWT Token 有效期默认为 7 天
- 敏感操作需要用户确认
- 任务之间完全隔离，互不影响
- 用户数据隔离，只能访问自己的任务

## 许可证

MIT License
