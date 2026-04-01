# Interest_tools

学习过程中感觉有趣的一些小工具集合，每个子文件夹都是一个独立完整的项目。

---

## 项目列表

| 项目名称 | 技术栈 | 功能描述 |
|:---------|:-------|:---------|
| [ChatRoom](./ChatRoom) | FastAPI + Vue 3 + WebSocket | 实时聊天室应用，支持私聊、群聊、好友系统和群组邀请 |

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

#### 项目结构

```
ChatRoom/
├── backend/                 # 后端服务
│   ├── app/                # 主应用目录
│   │   ├── core/          # 核心模块（数据库、认证、WebSocket）
│   │   ├── services/      # 服务层（业务逻辑）
│   │   ├── routes/        # 路由层（API 端点）
│   │   └── schemas.py     # 数据模型
│   ├── main.py            # 应用入口
│   └── requirements.txt   # Python 依赖
│
└── frontend/               # 前端应用
    ├── src/               # 源代码
    │   ├── views/         # 页面组件
    │   ├── stores/        # Pinia 状态管理
    │   └── router/        # 路由配置
    ├── package.json       # Node.js 依赖
    └── vite.config.js     # Vite 配置
```

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

## 许可证

[MIT](./LICENSE)

---

*持续更新中...*