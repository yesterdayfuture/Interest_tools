# Interest_tools

学习过程中感觉有趣的一些小工具集合，每个子文件夹都是一个独立完整的项目。

---

## 项目列表

| 项目名称 | 技术栈 | 功能描述 |
|:---------|:-------|:---------|
| [ChatRoom](./ChatRoom) | FastAPI + Vue 3 + WebSocket | 实时聊天室应用，支持私聊、群聊、好友系统和群组邀请 |
| [testRuntimeRegister](./testRuntimeRegister) | Python + FastAPI + importlib | 运行时动态加载模块，不重启服务即可使用新文件中的函数 |
| [use_importlib_module](./use_importlib_module) | Python + importlib | 学习动态导入模块的各种方法 |
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

### 2. testRuntimeRegister - 运行时动态模块加载

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

#### 项目结构

```
testRuntimeRegister/
├── app/
│   ├── __init__.py
│   └── function_loader.py    # 动态加载器核心实现
├── plugins/
│   ├── __init__.py
│   └── calculator.py         # 示例插件
└── main.py                   # FastAPI 应用入口
```

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

### 3. use_importlib_module - 动态导入模块学习

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
- `test_module.py` - 测试模块示例
- `test_package/` - 测试包示例

#### 快速开始

```bash
cd use_importlib_module
python 01_load_module.py
python 02_from_filepath_load_module.py
```

---

### 4. user_join_running_task - 人工介入运行中的任务

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

#### 项目结构

```
user_join_running_task/
├── use_threading/
│   ├── 01_user_interrupt_threading_event.py   # Event 方式
│   └── 02_user_interrupt_threading_queue.py   # Queue 方式
└── use_asyncio/
    ├── 01_test_interrupt_asyncio_event.py     # Event 方式
    └── 02_test_interrupt_asyncio_queue.py     # Queue 方式
```

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