# 聊天室应用 (Chat Room Application)

一个基于 FastAPI + Vue 3 的实时聊天室应用，采用模块化架构设计，支持个人聊天、群组聊天、好友系统和群组邀请系统。

## 项目架构

### 整体架构

```
ChatRoom/
├── backend/                 # 后端服务
│   ├── app/                # 主应用目录
│   │   ├── core/          # 核心模块（数据库、认证、WebSocket）
│   │   ├── services/      # 服务层（业务逻辑）
│   │   ├── routes/        # 路由层（API 端点）
│   │   └── schemas.py     # 数据模型
│   ├── main.py            # 应用入口
│   ├── chatroom.db        # SQLite 数据库
│   ├── Interface.md       # API 接口文档
│   └── README.md          # 后端文档
│
├── frontend/               # 前端应用
│   ├── src/
│   │   ├── api/          # API 接口封装
│   │   ├── components/   # 公共组件
│   │   ├── views/        # 页面组件
│   │   ├── stores/       # Pinia 状态管理
│   │   ├── router/       # 路由配置
│   │   └── utils/        # 工具函数
│   └── README.md         # 前端文档
│
└── README.md              # 项目文档
```

### 后端架构

采用分层架构设计：

1. **路由层 (Routes)**: 处理 HTTP 请求，定义 API 端点
2. **服务层 (Services)**: 处理业务逻辑，数据库操作
3. **核心层 (Core)**: 提供基础设施（数据库、认证、WebSocket）
4. **模型层 (Schemas)**: 定义数据模型和验证规则

### 前端架构

采用模块化架构设计：

1. **API 层**: 封装后端接口调用
2. **组件层**: 可复用的 UI 组件
3. **视图层**: 页面级组件
4. **状态层**: Pinia 状态管理
5. **工具层**: 通用工具函数

## 功能特性

### 用户系统
- ✅ 用户注册和登录（JWT 认证）
- ✅ 密码加密存储（bcrypt）
- ✅ 用户信息管理
- ✅ 在线状态追踪

### 好友系统
- ✅ 搜索用户（模糊匹配）
- ✅ 发送好友申请
- ✅ 处理好友申请（同意/拒绝）
- ✅ 好友列表管理
- ✅ 双向好友关系
- ✅ 好友申请通知

### 群组系统
- ✅ 创建群组
- ✅ 群组邀请（需同意）
- ✅ 群组成员管理
- ✅ 群主解散群组
- ✅ 角色管理（creator/member）

### 消息系统
- ✅ 实时消息（WebSocket）
- ✅ 私聊消息
- ✅ 群聊消息
- ✅ 消息历史记录
- ✅ 会话列表

### 统计功能
- ✅ 聊天室总体统计
- ✅ 用户个人统计
- ✅ 在线用户统计

## 技术栈

### 后端
- **FastAPI**: 现代化 Python Web 框架
- **Uvicorn**: ASGI 服务器
- **SQLite**: 轻量级数据库
- **aiosqlite**: 异步 SQLite 操作
- **JWT**: JSON Web Token 认证
- **Passlib**: 密码加密
- **Pydantic**: 数据验证
- **WebSocket**: 实时通信

### 前端
- **Vue 3**: 渐进式 JavaScript 框架
- **Element Plus**: Vue 3 UI 组件库
- **Vue Router 4**: 路由管理
- **Pinia**: 状态管理
- **Vite**: 构建工具
- **Axios**: HTTP 客户端
- **WebSocket API**: 实时通信

## 快速开始

### 环境要求

- Python 3.8+
- Node.js 16+
- npm 或 yarn

### 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 安装前端依赖

```bash
cd frontend
npm install
```

### 配置环境变量

前端配置 `.env` 文件：

```
VITE_API_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws
```

### 运行项目

**启动后端服务：**

```bash
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

后端 API 地址: http://localhost:8000

**启动前端服务：**

```bash
cd frontend
npm run dev
```

前端访问地址: http://localhost:5173

### 访问 API 文档

启动后端后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 端点

### 认证相关
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/register | 用户注册 |
| POST | /api/auth/token | 用户登录 |
| GET | /api/auth/me | 获取当前用户 |

### 用户相关
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/users | 获取所有用户 |
| GET | /api/users/online | 获取在线用户 |
| GET | /api/users/friends | 获取好友列表 |
| GET | /api/users/search | 搜索用户 |
| POST | /api/users/friend-requests | 发送好友申请 |
| GET | /api/users/friend-requests | 获取好友申请 |
| POST | /api/users/friend-requests/{id}/respond | 处理好友申请 |

### 群组相关
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/groups | 创建群组 |
| GET | /api/groups | 获取用户群组 |
| GET | /api/groups/{id} | 获取群组详情 |
| GET | /api/groups/{id}/members | 获取群组成员 |
| POST | /api/groups/{id}/members | 添加成员 |
| DELETE | /api/groups/{id}/members/{user_id} | 移除成员 |
| DELETE | /api/groups/{id} | 解散群组 |
| POST | /api/groups/{id}/invitations | 发送群组邀请 |
| GET | /api/groups/invitations/list | 获取群组邀请 |
| POST | /api/groups/invitations/{id}/respond | 处理群组邀请 |

### 消息相关
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/messages/history/personal | 获取私聊历史 |
| GET | /api/messages/history/group | 获取群聊历史 |
| GET | /api/messages/conversations | 获取会话列表 |

### 统计相关
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/stats/chatroom | 聊天室统计 |
| GET | /api/stats/user | 用户统计 |

### WebSocket
| 路径 | 说明 |
|------|------|
| /ws/{token} | WebSocket 连接端点 |

## 页面路由

| 路由 | 页面 | 说明 | 权限 |
|------|------|------|------|
| `/login` | 登录页面 | 用户登录 | 公开 |
| `/register` | 注册页面 | 用户注册 | 公开 |
| `/` | 聊天页面 | 主聊天界面 | 需要登录 |
| `/strangers` | 陌生人搜索 | 搜索和添加好友 | 需要登录 |
| `/friend-requests` | 好友申请 | 处理好友申请 | 需要登录 |
| `/create-group` | 创建群组 | 创建和管理群组 | 需要登录 |
| `/group/:groupId` | 群组聊天 | 群组聊天页面 | 需要登录 |

## 数据库表结构

### users（用户表）
- id: 主键
- username: 用户名（唯一）
- password: 密码（哈希）
- nickname: 昵称
- created_at: 创建时间
- last_login: 最后登录时间
- is_active: 是否激活

### groups（群组表）
- id: 主键
- name: 群组名称
- description: 群组描述
- creator_id: 创建者ID
- created_at: 创建时间

### group_members（群组成员表）
- id: 主键
- group_id: 群组ID
- user_id: 用户ID
- joined_at: 加入时间
- role: 角色（creator/member）

### friendships（好友关系表）
- id: 主键
- user_id: 用户ID
- friend_id: 好友ID
- created_at: 创建时间

### friend_requests（好友申请表）
- id: 主键
- from_user_id: 申请者ID
- to_user_id: 目标用户ID
- status: 状态（pending/accepted/rejected）
- message: 申请消息
- created_at: 创建时间
- responded_at: 响应时间

### group_invitations（群组邀请表）
- id: 主键
- group_id: 群组ID
- from_user_id: 邀请者ID
- to_user_id: 被邀请者ID
- status: 状态（pending/accepted/rejected）
- message: 邀请消息
- created_at: 创建时间
- responded_at: 响应时间

### messages（消息表）
- id: 主键
- sender_id: 发送者ID
- receiver_id: 接收者ID（私聊）
- group_id: 群组ID（群聊）
- content: 内容
- message_type: 消息类型
- created_at: 创建时间

### online_users（在线用户表）
- id: 主键
- user_id: 用户ID
- session_id: 会话ID
- connected_at: 连接时间
- last_activity: 最后活动时间

## 开发指南

### 后端开发

1. 在 `app/routes/` 下创建或修改路由文件
2. 在 `app/services/` 下添加业务逻辑
3. 在 `app/schemas.py` 中添加数据模型
4. 在 `app/routes/__init__.py` 中注册路由

### 前端开发

1. 在 `src/views/` 下创建页面组件
2. 在 `src/router/index.js` 中添加路由
3. 在 `src/api/` 下添加相关接口
4. 在 `src/stores/` 下添加状态管理（如果需要）

## 文档

- [后端文档](./backend/README.md)
- [前端文档](./frontend/README.md)
- [API 接口文档](./backend/Interface.md)

## 注意事项

1. **认证**: 所有 API 端点（除登录注册外）都需要在请求头中携带 `Authorization: Bearer {token}`
2. **WebSocket**: 连接使用 Token 作为路径参数
3. **数据库**: 数据库文件 `chatroom.db` 会自动创建
4. **安全**: 生产环境请修改 `SECRET_KEY` 环境变量
5. **好友申请**: 需要对方同意后才能成为好友
6. **群组邀请**: 需要被邀请者同意后才能加入群组

## 浏览器支持

- Chrome (推荐)
- Firefox
- Safari
- Edge

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

如有问题或建议，请联系项目维护者。
