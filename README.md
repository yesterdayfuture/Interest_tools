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
| [fastapi-nacos](./fastapi-nacos) | FastAPI + Nacos | FastAPI 服务注册与发现集成 |
| [fastapi_SseAndStreamable](./fastapi_SseAndStreamable) | FastAPI + SSE + Streamable HTTP | SSE 和 Streamable HTTP 流式传输对比测试 |
| [kg_from_unstructure_text](./kg_from_unstructure_text) | FastAPI + Nebula Graph + OpenAI | 电商客服知识图谱系统，支持本体管理和RAG检索 |
| [keyframes_extract](./keyframes_extract) | PyTorch + Bi-LSTM + OpenCV | 视频关键帧提取与视频摘要生成 |
| [large_model_eval](./large_model_eval) | FastAPI + OpenAI + HuggingFace | 大语言模型评估框架，支持多种数据集和评估指标 |
| [learn_flask](./learn_flask) | Flask + SQLAlchemy | Flask 框架学习项目，包含用户管理和文件下载 |
| [simulation_claude_code_skill](./simulation_claude_code_skill) | FastAPI + OpenAI | Claude Code Skills 系统模拟实现 |
| [testRuntimeRegister](./testRuntimeRegister) | Python + FastAPI + importlib | 运行时动态加载模块，不重启服务即可使用新文件中的函数 |
| [use_importlib_module](./use_importlib_module) | Python + importlib | 学习动态导入模块的各种方法 |
| [use_pytorch_model_some_layers](./use_pytorch_model_some_layers) | PyTorch + torchvision | PyTorch 模型部分层使用与中间层输出查看 |
| [user_decide_tools_use](./user_decide_tools_use) | FastAPI + OpenAI + WebSocket | AI Agent 系统，支持用户确认机制（Human-in-the-Loop） |
| [user_join_running_task](./user_join_running_task) | Python + threading + asyncio | 运行过程中的线程和协程，实现中间人工参与 |
| [vedio_extract_frames_demo](./vedio_extract_frames_demo) | FastAPI + OpenCV + MoviePy | 视频处理任务管理系统，支持视频切分和关键帧提取 |
| [定时器任务](./定时器任务) | Python + APScheduler/schedule/sched | 多种方式实现 Python 定时任务 |
| [装饰器实现](./装饰器实现) | Python | 装饰器的多种实现方式（嵌套函数、类、类方法） |

---

## 项目详情

### 1. ChatRoom - 实时聊天室应用

**项目路径**: [./ChatRoom](./ChatRoom)

#### 技术栈
- **后端**: FastAPI, Uvicorn, SQLite, aiosqlite, JWT, Passlib, Pydantic, WebSocket
- **前端**: Vue 3, Vue Router, Pinia, Element Plus, Axios, Vite

#### 功能特性
- 用户注册和登录（JWT 认证）
- 好友系统（搜索、申请、管理）
- 群组系统（创建、邀请、管理）
- 实时消息（WebSocket）
- 聊天室统计功能

#### 快速开始
```bash
cd ChatRoom/backend && pip install -r requirements.txt && uvicorn main:app --reload
cd ChatRoom/frontend && npm install && npm run dev
```

---

### 2. agent_eval - AI Agent 评估系统

**项目路径**: [./agent_eval](./agent_eval)

#### 技术栈
- Python, 装饰器, SQLite/PostgreSQL, ContextVars, Pydantic

#### 功能特性
- 零代码侵入式集成
- 全面指标：正确性、步骤比率、工具调用比率、解决率、延迟比率
- 混合评分：代码检查 + LLM-as-Judge
- 多种存储后端：JSON、CSV、SQLite、PostgreSQL
- 支持 LangChain、AutoGen、LangGraph

#### 快速开始
```bash
cd agent_eval && pip install -e .
python examples/basic_usage.py
```

---

### 3. dispatch_center_asyncio - 异步任务调度中心

**项目路径**: [./dispatch_center_asyncio](./dispatch_center_asyncio)

#### 技术栈
- FastAPI, SQLAlchemy 2.0, SQLite, asyncio.Semaphore, Pydantic

#### 功能特性
- 基于 asyncio.Semaphore 实现并发控制
- 任务生命周期管理
- 数据持久化存储
- RESTful API 接口

#### 快速开始
```bash
cd dispatch_center_asyncio && pip install -r requirements.txt && python start.py
```

---

### 4. dispatch_center_process - 多进程任务调度中心

**项目路径**: [./dispatch_center_process](./dispatch_center_process)

#### 技术栈
- FastAPI, SQLAlchemy 2.0, SQLite, multiprocessing, Pydantic

#### 功能特性
- 基于多进程实现并发控制
- 利用多核 CPU 资源，适合 CPU 密集型任务
- 任务生命周期管理

#### 快速开始
```bash
cd dispatch_center_process && pip install -r requirements.txt && python start.py
```

---

### 5. dispatch_center_thteading - 线程池任务调度中心

**项目路径**: [./dispatch_center_thteading](./dispatch_center_thteading)

#### 技术栈
- FastAPI, SQLAlchemy 2.0, SQLite, ThreadPoolExecutor, Pydantic

#### 功能特性
- 基于线程池实现并发控制
- 适合 I/O 密集型任务
- 任务生命周期管理

#### 快速开始
```bash
cd dispatch_center_thteading && pip install -r requirements.txt && python start.py
```

---

### 6. fastapi-nacos - FastAPI Nacos 服务注册

**项目路径**: [./fastapi-nacos](./fastapi-nacos)

#### 技术栈
- FastAPI, Nacos, asynccontextmanager

#### 功能特性
- 服务注册：启动时自动注册到 Nacos
- 心跳保活：自动发送心跳维持服务健康
- 服务注销：关闭时自动注销

#### 快速开始
```bash
cd fastapi-nacos && pip install fastapi uvicorn nacos-sdk-python
python main.py
```

---

### 7. fastapi_SseAndStreamable - SSE 和 Streamable HTTP 对比测试

**项目路径**: [./fastapi_SseAndStreamable](./fastapi_SseAndStreamable)

#### 技术栈
- FastAPI, sse-starlette

#### 功能特性
对比测试 SSE 和 Streamable HTTP 两种流式传输技术

#### 快速开始
```bash
cd fastapi_SseAndStreamable && pip install sse-starlette
cd sse_mode_test && uvicorn main:app --reload --port 8001
cd ../streamable_mode_test && uvicorn main:app --reload --port 8002
```

---

### 8. kg_from_unstructure_text - 电商客服知识图谱系统

**项目路径**: [./kg_from_unstructure_text](./kg_from_unstructure_text)

#### 技术栈
- FastAPI, Nebula Graph, OpenAI, SQLite, Docker

#### 功能特性
- 本体定义管理（Ontology Management）
- 属性类型系统（10种预定义类型）
- Nebula Graph 集成与同步
- 文件管理与处理（PDF、Word、Excel等）
- 基于大模型的智能实体提取
- RAG 检索系统

#### 快速开始
```bash
cd kg_from_unstructure_text
docker-compose up -d
pip install -r requirements.txt
python main.py
```

---

### 9. keyframes_extract - 视频关键帧提取

**项目路径**: [./keyframes_extract](./keyframes_extract)

#### 技术栈
- PyTorch, Bi-LSTM, OpenCV, GoogleNet/ResNet

#### 功能特性
- 基于深度学习的视频关键帧提取
- Bi-LSTM 模型建模帧间时序依赖
- 支持 SumMe 和 TVSum 数据集
- RLHF 训练支持

#### 快速开始
```bash
cd keyframes_extract
pip install torch torchvision opencv-python numpy scipy h5py tqdm scikit-learn
python train.py
python extract_keyframes.py --video path/to/video.mp4
```

---

### 10. large_model_eval - 大语言模型评估框架

**项目路径**: [./large_model_eval](./large_model_eval)

#### 技术栈
- FastAPI, OpenAI API, HuggingFace Transformers

#### 功能特性
- 全面评估指标：准确性、效率、鲁棒性、生成质量、多样性、连贯性
- 多数据集支持：MMLU、C-Eval、HumanEval、TruthfulQA
- 支持 OpenAI API 和本地 HuggingFace 模型
- RESTful API 异步评估任务管理

#### 快速开始
```bash
cd large_model_eval && pip install -r requirements.txt
export OPENAI_API_KEY="your-api-key"
python run.py api
```

---

### 11. learn_flask - Flask 框架学习项目

**项目路径**: [./learn_flask](./learn_flask)

#### 技术栈
- Flask, Flask-SQLAlchemy, PostgreSQL, gevent

#### 功能特性
- 用户管理（增删改查）
- 文件下载（多种方式）
- 流式响应示例
- 数据库集成

#### 快速开始
```bash
cd learn_flask
pip install Flask Flask-SQLAlchemy psycopg2-binary gevent
python main.py
```

---

### 12. simulation_claude_code_skill - Claude Code Skills 模拟实现

**项目路径**: [./simulation_claude_code_skill](./simulation_claude_code_skill)

#### 技术栈
- FastAPI, OpenAI, Pydantic

#### 功能特性
- 技能管理：动态技能发现和管理
- 意图识别：智能匹配用户请求
- 渐进式披露：按需加载技能内容
- 安全沙盒：隔离执行技能脚本

#### 快速开始
```bash
cd simulation_claude_code_skill && pip install -r requirements.txt
uvicorn main:app --reload
```

---

### 13. testRuntimeRegister - 运行时动态模块加载

**项目路径**: [./testRuntimeRegister](./testRuntimeRegister)

#### 技术栈
- Python, FastAPI, importlib, Pydantic

#### 功能特性
- 运行时动态加载 Python 模块
- 无需重启服务使用新函数
- 支持同步和异步函数调用
- 模块热更新功能

#### 快速开始
```bash
cd testRuntimeRegister && pip install fastapi uvicorn pydantic
python main.py
```

---

### 14. use_importlib_module - 动态导入模块学习

**项目路径**: [./use_importlib_module](./use_importlib_module)

#### 技术栈
- Python, importlib

#### 功能特性
- 同级模块导入
- 文件路径动态加载模块
- 检查模块加载状态
- 获取模块所有函数

#### 快速开始
```bash
cd use_importlib_module
python 01_load_module.py
python 02_from_filepath_load_module.py
```

---

### 15. use_pytorch_model_some_layers - PyTorch 模型层操作

**项目路径**: [./use_pytorch_model_some_layers](./use_pytorch_model_some_layers)

#### 技术栈
- PyTorch, torchvision, torchsummary

#### 功能特性
- 获取模型前几层
- 使用 named_children 访问子模块
- 使用 named_parameters 查看参数
- 展示模型中间层输入输出维度

#### 快速开始
```bash
cd use_pytorch_model_some_layers
pip install torch torchvision torchsummary
python 01_use_some_layer.py
```

---

### 16. user_decide_tools_use - AI Agent 用户确认系统

**项目路径**: [./user_decide_tools_use](./user_decide_tools_use)

#### 技术栈
- FastAPI, OpenAI, SQLite, WebSocket, JWT

#### 功能特性
- JWT Token 用户认证
- AI Agent 异步任务管理
- Human-in-the-Loop 用户确认机制
- WebSocket 实时通知

#### 快速开始
```bash
cd user_decide_tools_use
pip install fastapi uvicorn python-jose python-dotenv openai aiohttp
cp .env.example .env
python main.py
```

---

### 17. user_join_running_task - 人工介入运行中的任务

**项目路径**: [./user_join_running_task](./user_join_running_task)

#### 技术栈
- Python, threading, asyncio, queue

#### 功能特性
- 线程方案：使用 threading.Event 实现通信
- 协程方案：使用 asyncio.Event 实现通信
- 支持用户输入中断任务
- 任务切换和队列传递

#### 快速开始
```bash
cd user_join_running_task/use_threading && python 01_user_interrupt_threading_event.py
cd user_join_running_task/use_asyncio && python 01_test_interrupt_asyncio_event.py
```

---

### 18. vedio_extract_frames_demo - 视频处理任务管理系统

**项目路径**: [./vedio_extract_frames_demo](./vedio_extract_frames_demo)

#### 技术栈
- FastAPI, OpenCV, MoviePy, 多进程

#### 功能特性
- 视频文件上传和切分
- 关键帧提取
- 多进程并行处理
- 实时任务进度监控
- 超时自动终止机制

#### 快速开始
```bash
cd vedio_extract_frames_demo
pip install fastapi uvicorn opencv-python moviepy
python main.py
```

---

### 19. 定时器任务 - Python 定时任务实现

**项目路径**: [./定时器任务](./定时器任务)

#### 技术栈
- Python, APScheduler, schedule, sched

#### 功能特性
- APScheduler 实现后台定时任务
- schedule 实现简单定时任务
- sched 实现基础定时任务
- uvicorn 与 APScheduler 集成

#### 快速开始
```bash
cd 定时器任务
python APScheduler实现定时任务.py
python schedule实现定时任务.py
```

---

### 20. 装饰器实现 - Python 装饰器学习

**项目路径**: [./装饰器实现](./装饰器实现)

#### 技术栈
- Python, functools, inspect

#### 功能特性
- 使用嵌套函数实现装饰器
- 使用类实现装饰器
- 通过类的方法实现装饰器
- 保留原函数元数据

#### 快速开始
```bash
cd 装饰器实现
python 1.使用嵌套函数实现.py
python 2.使用类实现.py
python 3.通过类的方法实现.py
```

---

## 许可证

[MIT](./LICENSE)

---

*持续更新中...*
