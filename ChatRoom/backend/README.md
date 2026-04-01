# 聊天室后端 (Chat Room Backend)

基于 FastAPI 的实时聊天室后端服务，采用模块化架构设计，支持个人聊天、群组聊天、好友系统和群组邀请系统。

## 项目架构

### 目录结构

```
backend/
├── app/                      # 主应用目录
│   ├── __init__.py
│   ├── schemas.py           # Pydantic 数据模型
│   ├── core/                # 核心模块
│   │   ├── __init__.py
│   │   ├── database.py      # 数据库配置和初始化
│   │   ├── auth.py          # 认证相关（密码哈希、JWT）
│   │   └── connection_manager.py  # WebSocket 连接管理
│   ├── services/            # 服务层
│   │   ├── __init__.py
│   │   ├── user_service.py  # 用户服务
│   │   ├── group_service.py # 群组服务
│   │   └── message_service.py # 消息服务
│   ├── routes/              # 路由层（API 端点）
│   │   ├── __init__.py
│   │   ├── auth.py          # 认证路由
│   │   ├── users.py         # 用户路由
│   │   ├── groups.py        # 群组路由
│   │   ├── messages.py      # 消息路由
│   │   ├── stats.py         # 统计路由
│   │   └── websocket.py     # WebSocket 路由
│   └── utils/               # 工具函数
│       └── __init__.py
├── main.py                  # 应用入口
├── chatroom.db              # SQLite 数据库文件
├── requirements.txt         # Python 依赖
├── Interface.md             # API 接口文档
└── README.md               # 项目文档
```

### 架构说明

本项目采用分层架构设计：

1. **路由层 (Routes)**: 处理 HTTP 请求，定义 API 端点
2. **服务层 (Services)**: 处理业务逻辑，数据库操作
3. **核心层 (Core)**: 提供基础设施（数据库、认证、WebSocket）
4. **模型层 (Schemas)**: 定义数据模型和验证规则

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

- **FastAPI**: 现代化 Python Web 框架
- **Uvicorn**: ASGI 服务器
- **SQLite**: 轻量级数据库
- **aiosqlite**: 异步 SQLite 操作
- **JWT**: JSON Web Token 认证
- **Passlib**: 密码加密
- **Pydantic**: 数据验证
- **WebSocket**: 实时通信

## 快速开始

### 环境要求

- Python 3.8+
- pip

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行项目

```bash
# 开发模式（热重载）
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### 访问 API 文档

启动后访问：
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

### 添加新接口

1. 在 `app/routes/` 下创建或修改路由文件
2. 在 `app/services/` 下添加业务逻辑
3. 在 `app/schemas.py` 中添加数据模型
4. 在 `app/routes/__init__.py` 中注册路由

### 示例：添加新接口

```python
# app/routes/example.py
from fastapi import APIRouter, Depends
from app.schemas import SomeModel
from app.core.auth import get_current_active_user

router = APIRouter(prefix="/example", tags=["示例"])

@router.get("/", response_model=SomeModel)
async def example_endpoint(current_user: dict = Depends(get_current_active_user)):
    return {"message": "Hello"}
```

## 接口文档

详细的接口文档请查看 [Interface.md](./Interface.md)

## 注意事项

1. 所有 API 端点（除登录注册外）都需要在请求头中携带 `Authorization: Bearer {token}`
2. WebSocket 连接使用 Token 作为路径参数
3. 数据库文件 `chatroom.db` 会自动创建
4. 生产环境请修改 `SECRET_KEY` 环境变量

## 许可证

MIT License
