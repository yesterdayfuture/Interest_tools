# Interest_tools

学习过程中感觉有趣的一些小工具集合，每个子文件夹都是一个独立完整的项目。

---

## 项目列表

| 项目名称 | 技术栈 | 功能描述 |
|:---------|:-------|:---------|
| [ChatRoom](./ChatRoom) | FastAPI + Vue 3 + WebSocket | 实时聊天室应用，支持私聊、群聊、好友系统和群组邀请 |
| [agent_eval](./agent_eval) | Python + 装饰器 + SQLite/PostgreSQL | AI Agent 评估系统，零代码侵入式集成 |
| [dispatch_center_asyncio](./dispatch_center_asyncio) | FastAPI + SQLAlchemy + asyncio | 基于 asyncio.Semaphore 的任务调度中心 |
| [dispatch_center_process](./dispatch_center_process) | FastAPI + SQLAlchemy + multiprocessing | 基于多进程的任务调度中心 |
| [dispatch_center_thteading](./dispatch_center_thteading) | FastAPI + SQLAlchemy + ThreadPoolExecutor | 基于线程池的任务调度中心 |
| [fastapi_SseAndStreamable](./fastapi_SseAndStreamable) | FastAPI + SSE + Streamable HTTP | SSE 和 Streamable HTTP 流式传输对比测试 |
| [simulation_claude_code_skill](./simulation_claude_code_skill) | FastAPI + OpenAI | Claude Code Skills 系统模拟实现 |
| [testRuntimeRegister](./testRuntimeRegister) | Python + FastAPI + importlib | 运行时动态加载模块，不重启服务即可使用新文件中的函数 |
| [use_importlib_module](./use_importlib_module) | Python + importlib | 学习动态导入模块的各种方法 |
| [use_pytorch_model_some_layers](./use_pytorch_model_some_layers) | PyTorch + torchvision | PyTorch 模型部分层使用与中间层输出查看 |
| [user_decide_tools_use](./user_decide_tools_use) | FastAPI + OpenAI + WebSocket | AI Agent 系统，支持用户确认机制（Human-in-the-Loop） |
| [user_join_running_task](./user_join_running_task) | Python + threading + asyncio | 运行过程中的线程和协程，实现中间人工参与 |

---

## 项目详情

### 1. ChatRoom - 实时聊天室应用

**项目路径**: [./ChatRoom](./ChatRoom)

#### 技术栈

**后端**:
- **FastAPI** - 现代化 Python Web 框架
- **Uvicorn** - ASGI 服务器
- **SQLite** - 轻量级数据库
- **aiosqlite** - 异步 SQLite 操作
- **JWT** - JSON Web Token 认证
- **Passlib** - 密码加密
- **Pydantic** - 数据验证
- **WebSocket** - 实时通信

**前端**:
- **Vue 3** - 渐进式 JavaScript 框架
- **Vue Router** - 路由管理
- **Pinia** - 状态管理
- **Element Plus** - UI 组件库
- **Axios** - HTTP 客户端
- **Vite** - 构建工具

#### 功能特性

**用户系统**:
- 用户注册和登录（JWT 认证）
- 密码加密存储（bcrypt）
- 用户信息管理
- 在线状态追踪

**好友系统**:
- 搜索用户（模糊匹配）
- 发送好友申请
- 处理好友申请（同意/拒绝）
- 好友列表管理
- 双向好友关系

**群组系统**:
- 创建群组
- 群组邀请（需同意）
- 群组成员管理
- 群主解散群组
- 角色管理（creator/member）

**消息系统**:
- 实时消息（WebSocket）
- 私聊消息
- 群聊消息
- 消息历史记录
- 会话列表

**统计功能**:
- 聊天室总体统计
- 用户个人统计
- 在线用户统计

#### 快速开始

**后端启动**:
```bash
cd ChatRoom/backend
pip install -r requirements.txt
uvicorn main:app --reload
```

**前端启动**:
```bash
cd ChatRoom/frontend
npm install
npm run dev
```

---

### 2. agent_eval - AI Agent 评估系统

**项目路径**: [./agent_eval](./agent_eval)

#### 技术栈
- **Python** - 编程语言
- **装饰器** - 零代码侵入式集成
- **SQLite/PostgreSQL** - 数据存储
- **ContextVars** - 并发执行跟踪
- **Pydantic** - 数据验证

#### 功能特性
- **零代码侵入**：通过装饰器集成，无需修改现有代码
- **全面指标**：正确性、步骤比率、工具调用比率、解决率、延迟比率
- **混合评分**：结合基于代码的检查与 LLM-as-Judge 评估
- **多种存储后端**：支持 JSON、CSV、SQLite、PostgreSQL
- **理想答案生成**：使用 LLM 生成预期执行路径
- **详细报告**：单批次评估报告与对比分析
- **框架无关**：支持 LangChain、AutoGen、LangGraph 或自定义框架
- **并发执行**：基于 ContextVars 的跟踪支持并发和嵌套执行

#### 项目结构

```
agent_eval/
├── agent_eval/            # 核心包
│   ├── core.py           # 核心评估器
│   ├── decorators.py     # 装饰器
│   ├── metrics.py        # 指标计算
│   ├── models.py         # 数据模型
│   ├── recorders.py      # 记录器
│   ├── scorers.py        # 评分器
│   ├── storages.py       # 存储后端
│   └── tracker.py        # 跟踪器
├── examples/             # 示例代码
├── tests/                # 测试
├── docs/                 # 文档
└── README.md
```

#### 快速开始

```bash
cd agent_eval
pip install -e .

# 运行示例
python examples/basic_usage.py
```

---

### 3. dispatch_center_asyncio - 异步任务调度中心

**项目路径**: [./dispatch_center_asyncio](./dispatch_center_asyncio)

#### 技术栈
- **FastAPI** - Web 框架
- **SQLAlchemy 2.0** - ORM（异步支持）
- **SQLite** - 数据库
- **asyncio.Semaphore** - 并发控制
- **Pydantic** - 数据验证
- **Uvicorn** - ASGI 服务器

#### 功能特性
- 基于 `asyncio.Semaphore` 实现并发控制
- 任务生命周期管理（pending → running → completed/failed/cancelled）
- 数据持久化存储
- 多维度过滤和分页查询
- 实时任务统计和成功率计算
- RESTful API 接口
- 支持自定义任务处理器

#### 快速开始

```bash
cd dispatch_center_asyncio
pip install -r requirements.txt
python start.py
```

---

### 4. dispatch_center_process - 多进程任务调度中心

**项目路径**: [./dispatch_center_process](./dispatch_center_process)

#### 技术栈
- **FastAPI** - Web 框架
- **SQLAlchemy 2.0** - ORM（异步支持）
- **SQLite** - 数据库
- **multiprocessing** - 多进程并发
- **Pydantic** - 数据验证
- **Uvicorn** - ASGI 服务器

#### 功能特性
- 基于 Python `multiprocessing` 多进程实现并发控制
- 利用多核 CPU 资源，适合 CPU 密集型任务
- 任务生命周期管理
- 数据持久化存储
- 实时任务统计
- RESTful API 接口

#### 快速开始

```bash
cd dispatch_center_process
pip install -r requirements.txt
cp .env.example .env
python start.py
```

---

### 5. dispatch_center_thteading - 线程池任务调度中心

**项目路径**: [./dispatch_center_thteading](./dispatch_center_thteading)

#### 技术栈
- **FastAPI** - Web 框架
- **SQLAlchemy 2.0** - ORM（异步支持）
- **SQLite** - 数据库
- **ThreadPoolExecutor** - 线程池并发
- **Pydantic** - 数据验证
- **Uvicorn** - ASGI 服务器

#### 功能特性
- 基于 `ThreadPoolExecutor` 线程池实现并发控制
- 适合 I/O 密集型任务
- 任务生命周期管理
- 数据持久化存储
- 实时任务统计
- RESTful API 接口

#### 快速开始

```bash
cd dispatch_center_thteading
pip install -r requirements.txt
cp .env.example .env
python start.py
```

---

### 6. fastapi_SseAndStreamable - SSE 和 Streamable HTTP 对比测试

**项目路径**: [./fastapi_SseAndStreamable](./fastapi_SseAndStreamable)

#### 技术栈
- **FastAPI** - Web 框架
- **sse-starlette** - SSE 实现库
- **Streamable HTTP** - 通用流式传输机制

#### 功能特性
对比测试 SSE 和 Streamable HTTP 两种流式传输技术：

**SSE (Server-Sent Events)**:
- 基于 HTTP 的特定协议，HTML5 标准的一部分
- 单向通信：数据从服务器流向客户端
- 固定格式：`text/event-stream`，数据行以 `data:` 开头
- 有状态连接：需要维护持久 HTTP 长连接

**Streamable HTTP**:
- 通用传输机制，灵活选择流式响应
- 请求-响应式，可升级为流式响应
- 使用 `Transfer-Encoding: chunked` 分块传输，格式自定义
- 无状态连接，支持从断开点续传

#### 项目结构

```
fastapi_SseAndStreamable/
├── sse_mode_test/         # SSE 模式测试
│   └── main.py
├── streamable_mode_test/  # Streamable HTTP 模式测试
│   └── main.py
└── readme.md
```

#### 快速开始

```bash
cd fastapi_SseAndStreamable
pip install sse-starlette

# 测试 SSE 模式
cd sse_mode_test
uvicorn main:app --reload --port 8001

# 测试 Streamable HTTP 模式
cd ../streamable_mode_test
uvicorn main:app --reload --port 8002
```

---

### 7. simulation_claude_code_skill - Claude Code Skills 模拟实现

**项目路径**: [./simulation_claude_code_skill](./simulation_claude_code_skill)

#### 技术栈
- **FastAPI** - Web 框架
- **OpenAI** - AI 模型接口
- **Pydantic** - 数据验证
- **python-dotenv** - 环境变量管理

#### 功能特性
- **技能管理**：基于文件系统的动态技能发现和管理
- **意图识别**：智能匹配用户请求与相关技能
- **渐进式披露**：按需加载技能内容，最小化 Token 消耗
- **安全沙盒**：隔离执行技能脚本，确保安全性
- **API 接口**：完整的 RESTful API 接口

#### 项目结构

```
simulation_claude_code_skill/
├── skills/                 # 技能目录
│   ├── code-reviewer/      # 代码审查技能
│   ├── fitness-plan-generator/  # 健身计划生成器
│   ├── learning-schedule-generator/  # 学习计划生成器
│   ├── project-health/     # 项目健康分析技能
│   ├── random-password-generator/  # 随机密码生成器
│   ├── skill-creator/      # 技能创建器
│   └── test-skill/         # 测试技能
├── src/                    # 源代码
│   ├── skill_parser.py     # 技能配置解析
│   ├── skill_manager.py    # 技能管理
│   ├── intent_matcher.py   # 意图匹配
│   ├── progressive_disclosure.py  # 渐进式披露
│   └── sandbox.py          # 安全沙盒
├── main.py                 # FastAPI 应用入口
└── requirements.txt        # 依赖文件
```

#### API 接口

- `GET /skills` - 获取技能列表
- `GET /skills/{skill_id}` - 获取技能详情
- `POST /skills/{skill_id}/trigger` - 触发技能执行
- `POST /intent/match` - 意图匹配
- `GET /health` - 健康检查

#### 快速开始

```bash
cd simulation_claude_code_skill
pip install -r requirements.txt
# 配置 .env 文件中的 OPENAI_API_KEY
uvicorn main:app --reload
```

---

### 8. testRuntimeRegister - 运行时动态模块加载

**项目路径**: [./testRuntimeRegister](./testRuntimeRegister)

#### 技术栈
- **Python** - 编程语言
- **FastAPI** - Web 框架
- **importlib** - 动态模块导入
- **Pydantic** - 数据验证

#### 功能特性
- 在应用运行过程中动态加载新的 Python 模块
- 无需重启服务即可使用新文件中的函数
- 支持同步和异步函数调用
- 提供模块重新加载功能（热更新）
- 路径白名单校验，确保安全性

#### API 接口

- `POST /admin/load-module` - 动态加载模块
- `POST /admin/call-function` - 调用模块中的函数
- `POST /admin/reload-module` - 重新加载模块

#### 快速开始

```bash
cd testRuntimeRegister
pip install fastapi uvicorn pydantic
python main.py
```

---

### 9. use_importlib_module - 动态导入模块学习

**项目路径**: [./use_importlib_module](./use_importlib_module)

#### 技术栈
- **Python** - 编程语言
- **importlib** - 模块导入库

#### 功能特性
演示 Python 中动态导入模块的多种方法：

1. **同级模块导入** - 使用 `importlib.import_module()` 导入同级模块
2. **文件路径加载** - 使用 `importlib.util.spec_from_file_location()` 从文件路径加载模块
3. **检查模块加载** - 验证模块是否正确加载

#### 示例文件

- `01_load_module.py` - 导入同级模块和包内模块
- `02_from_filepath_load_module.py` - 根据文件路径动态加载模块
- `03_check_load_module.py` - 检查模块加载状态

#### 快速开始

```bash
cd use_importlib_module
python 01_load_module.py
python 02_from_filepath_load_module.py
```

---

### 10. use_pytorch_model_some_layers - PyTorch 模型层操作

**项目路径**: [./use_pytorch_model_some_layers](./use_pytorch_model_some_layers)

#### 技术栈
- **PyTorch** - 深度学习框架
- **torchvision** - 预训练模型库
- **torchsummary** - 模型摘要工具

#### 功能特性
演示 PyTorch 模型的部分层使用和中间层输出查看：

- **获取模型前几层**：使用 `list(model.children())` 获取指定层
- **使用 named_children**：通过名称访问子模块
- **使用 named_parameters**：查看模型参数
- **查看中间层输出**：使用 `torchsummary` 展示模型中间输入输出维度

#### 示例文件

- `01_use_some_layer.py` - 获取模型前几层
- `02_use_name_children.py` - 使用 named_children 访问子模块
- `03_use_name_parameters.py` - 查看模型参数
- `04_show_model_middle_inputAndOutput.py` - 展示模型中间层输入输出维度

#### 快速开始

```bash
cd use_pytorch_model_some_layers
pip install torch torchvision torchsummary
python 01_use_some_layer.py
python 04_show_model_middle_inputAndOutput.py
```

---

### 11. user_decide_tools_use - AI Agent 用户确认系统

**项目路径**: [./user_decide_tools_use](./user_decide_tools_use)

#### 技术栈
- **FastAPI** - Web 框架
- **OpenAI** - AI 模型接口
- **SQLite** - 数据库
- **WebSocket** - 实时通信
- **JWT** - 用户认证
- **Pydantic** - 数据验证

#### 功能特性
- **用户认证系统**：基于 JWT Token 的用户认证，支持注册、登录、登出
- **AI Agent 任务管理**：异步任务执行，支持多任务并行和任务隔离
- **Human-in-the-Loop**：敏感操作（文件创建、修改、删除等）需要用户确认
- **WebSocket 实时通知**：任务状态实时推送到前端
- **数据持久化**：SQLite 数据库存储用户和任务信息
- **任务隔离**：不同任务之间完全隔离，互不影响

#### API 接口

- `POST /auth/register` - 用户注册
- `POST /auth/login` - 用户登录
- `POST /auth/logout` - 用户登出
- `POST /task/start` - 创建任务
- `POST /task/{task_id}/confirm` - 确认任务操作
- `WebSocket /ws/task/{task_id}` - 任务状态实时推送

#### 快速开始

```bash
cd user_decide_tools_use
pip install fastapi uvicorn python-jose python-dotenv openai aiohttp
cp .env.example .env
# 编辑 .env 文件，配置 OPENAI_API_KEY
python main.py
```

---

### 12. user_join_running_task - 人工介入运行中的任务

**项目路径**: [./user_join_running_task](./user_join_running_task)

#### 技术栈
- **Python** - 编程语言
- **threading** - 线程模块
- **asyncio** - 异步 I/O 模块
- **queue** - 队列模块

#### 功能特性
演示如何在运行过程中的线程和协程中实现人工参与：

**线程方案** (`use_threading/`):
- 使用 `threading.Event` 实现线程间通信
- 支持用户输入中断当前任务
- 支持动态切换执行新任务
- 使用队列 (Queue) 进行任务传递

**协程方案** (`use_asyncio/`):
- 使用 `asyncio.Event` 实现协程间通信
- 异步方式处理用户输入
- 支持协程任务切换
- 使用 `asyncio.Queue` 进行任务传递

#### 快速开始

**线程示例**:
```bash
cd user_join_running_task/use_threading
python 01_user_interrupt_threading_event.py
```

**协程示例**:
```bash
cd user_join_running_task/use_asyncio
python 01_test_interrupt_asyncio_event.py
```

---

## 许可证

[MIT](./LICENSE)

---

*持续更新中...*
