# 聊天室前端 (Chat Room Frontend)

基于 Vue 3 + Element Plus 的聊天室前端应用，采用模块化架构设计。

## 项目架构

### 目录结构

```
frontend/
├── src/
│   ├── api/               # API 接口封装
│   │   ├── request.js     # axios 请求配置
│   │   ├── auth.js        # 认证相关接口
│   │   ├── user.js        # 用户相关接口
│   │   ├── group.js       # 群组相关接口
│   │   └── message.js     # 消息相关接口
│   ├── components/        # 公共组件
│   │   ├── MessageBubble.vue    # 消息气泡组件
│   │   ├── UserAvatar.vue       # 用户头像组件
│   │   └── OnlineStatus.vue     # 在线状态组件
│   ├── views/             # 页面组件
│   │   ├── Login.vue              # 登录页面
│   │   ├── Register.vue           # 注册页面
│   │   ├── Chat.vue               # 聊天主页面
│   │   ├── GroupChat.vue          # 群组聊天页面
│   │   ├── StrangerSearch.vue     # 陌生人搜索页面
│   │   ├── FriendRequests.vue     # 好友申请页面
│   │   └── CreateGroup.vue        # 创建群组页面
│   ├── stores/            # Pinia 状态管理
│   │   ├── auth.js        # 认证状态
│   │   ├── user.js        # 用户状态
│   │   ├── chat.js        # 聊天状态
│   │   └── index.js       # 状态管理入口
│   ├── router/            # 路由配置
│   │   └── index.js       # 路由定义
│   ├── utils/             # 工具函数
│   │   ├── websocket.js   # WebSocket 管理
│   │   ├── storage.js     # 本地存储封装
│   │   └── format.js      # 格式化工具
│   ├── App.vue
│   └── main.js
├── index.html
├── package.json
├── vite.config.js
└── README.md
```

### 架构说明

本项目采用模块化架构设计：

1. **API 层**: 封装后端接口调用
2. **组件层**: 可复用的 UI 组件
3. **视图层**: 页面级组件
4. **状态层**: Pinia 状态管理
5. **工具层**: 通用工具函数

## 快速开始

### 环境要求

- Node.js 16+
- npm 或 yarn

### 安装依赖

```bash
npm install
```

### 环境配置

创建 `.env` 文件配置 API 地址:

```
VITE_API_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws
```

### 开发模式

```bash
npm run dev
```

访问: http://localhost:5173

### 生产构建

```bash
npm run build
```

## 功能特性

### 用户认证
- ✅ 用户注册
- ✅ 用户登录
- ✅ JWT Token 管理
- ✅ 登录状态持久化
- ✅ 自动 Token 刷新

### 聊天功能
- ✅ 实时个人聊天（WebSocket）
- ✅ 群组聊天
- ✅ 消息历史记录
- ✅ 消息已读状态
- ✅ 消息发送状态
- ✅ 消息时间显示

### 好友系统
- ✅ 搜索用户（模糊匹配）
- ✅ 查看用户资料
- ✅ 发送好友申请
- ✅ 处理好友申请（同意/拒绝）
- ✅ 好友列表管理
- ✅ 好友在线状态
- ✅ 好友申请通知

### 群组系统
- ✅ 创建新群组
- ✅ 群组信息管理
- ✅ 邀请好友加入
- ✅ 处理群组邀请
- ✅ 群组成员管理
- ✅ 群主解散群组
- ✅ 群组消息

### 界面特性
- ✅ 响应式设计
- ✅ 侧边栏导航
- ✅ 消息气泡样式
- ✅ 在线状态指示器
- ✅ 搜索功能
- ✅ 加载状态提示
- ✅ 错误提示
- ✅ 空状态提示

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

## 页面说明

### 登录页面 (`/login`)
- 用户名和密码输入
- 表单验证
- 登录成功后跳转到聊天页面

### 注册页面 (`/register`)
- 用户名、密码、昵称输入
- 表单验证
- 注册成功后自动登录

### 聊天页面 (`/`)
- **侧边栏**:
  - 当前用户信息
  - 好友列表（显示在线状态）
  - 群组列表
  - 功能按钮（搜索、申请、创建群组）
- **聊天区域**:
  - 消息列表（气泡样式）
  - 消息输入框
  - 发送按钮
- **WebSocket 连接**:
  - 实时接收消息
  - 心跳保持连接

### 陌生人搜索页面 (`/strangers`)
- 搜索框（支持模糊匹配）
- 搜索结果列表
- 用户基本信息展示
- 添加好友按钮

### 好友申请页面 (`/friend-requests`)
- **标签页切换**:
  - 待处理：收到的好友申请
  - 已发送：已发送的申请
  - 历史记录：已处理的申请
- **操作按钮**:
  - 同意/拒绝申请

### 创建群组页面 (`/create-group`)
- **创建表单**:
  - 群组名称
  - 群组描述
  - 邀请好友（多选）
- **群组列表**: 显示已创建的群组
- **操作**: 解散群组

## 技术栈

- **Vue 3**: 渐进式 JavaScript 框架
- **Element Plus**: Vue 3 UI 组件库
- **Vue Router 4**: 路由管理
- **Pinia**: 状态管理
- **Vite**: 构建工具
- **Axios**: HTTP 客户端
- **WebSocket API**: 实时通信

## API 接口

### 认证接口
```javascript
// 登录
POST /api/auth/token

// 注册
POST /api/auth/register

// 获取当前用户
GET /api/auth/me
```

### 用户接口
```javascript
// 获取所有用户
GET /api/users

// 获取在线用户
GET /api/users/online

// 获取好友列表
GET /api/users/friends

// 搜索用户
GET /api/users/search?username={keyword}

// 发送好友申请
POST /api/users/friend-requests

// 获取好友申请
GET /api/users/friend-requests

// 处理好友申请
POST /api/users/friend-requests/{id}/respond
```

### 群组接口
```javascript
// 创建群组
POST /api/groups

// 获取用户群组
GET /api/groups

// 获取群组详情
GET /api/groups/{id}

// 获取群组成员
GET /api/groups/{id}/members

// 发送群组邀请
POST /api/groups/{id}/invitations

// 处理群组邀请
POST /api/groups/invitations/{id}/respond

// 解散群组
DELETE /api/groups/{id}
```

### 消息接口
```javascript
// 获取私聊历史
GET /api/messages/history/personal?other_user_id={id}

// 获取群聊历史
GET /api/messages/history/group?group_id={id}

// 获取会话列表
GET /api/messages/conversations
```

### WebSocket
```javascript
// 连接
ws://localhost:8000/ws/{token}

// 发送私聊消息
{
  "type": "personal",
  "receiver_id": 123,
  "content": "消息内容"
}

// 发送群聊消息
{
  "type": "group",
  "group_id": 456,
  "content": "消息内容"
}
```

## 状态管理

### Auth Store
```javascript
// 状态
isAuthenticated: boolean
user: object
token: string

// 方法
login(credentials)
register(userInfo)
logout()
fetchUser()
```

### Chat Store
```javascript
// 状态
messages: array
friends: array
groups: array
currentChat: object

// 方法
sendMessage(message)
receiveMessage(message)
loadHistory(userId)
```

## 开发指南

### 添加新页面

1. 在 `src/views/` 下创建页面组件
2. 在 `src/router/index.js` 中添加路由
3. 在 `src/api/` 下添加相关接口
4. 在 `src/stores/` 下添加状态管理（如果需要）

### 添加新组件

1. 在 `src/components/` 下创建组件
2. 在页面中导入使用

### 示例：添加新页面

```vue
<!-- src/views/Example.vue -->
<template>
  <div class="example-container">
    <h1>示例页面</h1>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const data = ref([])
</script>

<style scoped>
.example-container {
  padding: 20px;
}
</style>
```

```javascript
// src/router/index.js
{
  path: '/example',
  name: 'Example',
  component: () => import('../views/Example.vue'),
  meta: { requiresAuth: true }
}
```

## 注意事项

1. **后端服务**: 确保后端服务正在运行（默认端口 8000）
2. **WebSocket**: 保持网络稳定，断线会自动重连
3. **好友申请**: 需要对方同意后才能成为好友
4. **群组邀请**: 需要被邀请者同意后才能加入群组
5. **Token 过期**: 登录状态过期需要重新登录
6. **浏览器支持**: 推荐使用 Chrome、Firefox、Safari 最新版本

## 常见问题

### Q: WebSocket 连接失败？
A: 检查后端服务是否运行，以及 `.env` 中的 `VITE_WS_URL` 配置是否正确。

### Q: 登录后页面空白？
A: 检查浏览器控制台是否有错误，可能是 Token 验证失败，尝试清除 localStorage 后重新登录。

### Q: 消息发送失败？
A: 检查 WebSocket 连接状态，如果断开会自动重连，等待连接成功后重试。

## 许可证

MIT License
