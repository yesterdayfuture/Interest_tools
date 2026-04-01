# Chat Room API 接口文档

## 目录
1. [概述](#概述)
2. [认证](#认证)
3. [用户管理](#用户管理)
4. [好友系统](#好友系统)
5. [群组系统](#群组系统)
6. [消息系统](#消息系统)
7. [统计信息](#统计信息)
8. [WebSocket](#websocket)

---

## 概述

### 基本信息
- **Base URL**: `http://localhost:8000/api`
- **WebSocket URL**: `ws://localhost:8000/ws/{token}`
- **API 文档**: `http://localhost:8000/docs` (Swagger UI)
- **API 文档**: `http://localhost:8000/redoc` (ReDoc)

### 认证方式
所有需要认证的接口都需要在请求头中添加：
```
Authorization: Bearer {access_token}
```

### 响应格式
- **成功响应**: 返回对应的数据结构
- **错误响应**: 
  ```json
  {
    "detail": "错误信息"
  }
  ```

---

## 认证

### 1. 用户注册
**POST** `/auth/register`

**请求体**:
```json
{
  "username": "string",    // 必填，3-50字符
  "password": "string",    // 必填，至少6位
  "nickname": "string"     // 可选
}
```

**响应**:
```json
{
  "id": 1,
  "username": "string",
  "nickname": "string",
  "created_at": "2024-01-01T00:00:00",
  "last_login": null,
  "is_active": 1
}
```

**错误码**:
- `400`: 用户名已存在

---

### 2. 用户登录
**POST** `/auth/token`

**请求体** (form-data):
```
username: string
password: string
```

**响应**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**错误码**:
- `401`: 用户名或密码错误

---

### 3. 获取当前用户信息
**GET** `/auth/me`

**请求头**:
```
Authorization: Bearer {token}
```

**响应**:
```json
{
  "id": 1,
  "username": "string",
  "nickname": "string",
  "created_at": "2024-01-01T00:00:00",
  "last_login": "2024-01-01T12:00:00",
  "is_active": 1
}
```

---

## 用户管理

### 1. 获取所有用户
**GET** `/users`

**响应**:
```json
[
  {
    "id": 1,
    "username": "string",
    "nickname": "string",
    "created_at": "2024-01-01T00:00:00",
    "last_login": "2024-01-01T12:00:00",
    "is_active": 1
  }
]
```

---

### 2. 获取在线用户
**GET** `/users/online`

**响应**:
```json
[
  {
    "id": 1,
    "username": "string",
    "nickname": "string",
    "last_activity": "2024-01-01T12:00:00"
  }
]
```

---

### 3. 获取好友列表
**GET** `/users/friends`

**响应**:
```json
[
  {
    "id": 2,
    "username": "friend_name",
    "nickname": "friend_nickname"
  }
]
```

---

### 4. 搜索用户
**GET** `/users/search?username={keyword}`

**查询参数**:
- `username`: 搜索关键词（模糊匹配）

**响应**:
```json
{
  "users": [
    {
      "id": 2,
      "username": "searched_user",
      "nickname": "nickname",
      "created_at": "2024-01-01T00:00:00",
      "last_login": null,
      "is_active": 1
    }
  ]
}
```

---

## 好友系统

### 1. 发送好友申请
**POST** `/users/friend-requests`

**请求体**:
```json
{
  "to_user_id": 2,           // 必填，目标用户ID
  "message": "Hello!"        // 可选，申请消息
}
```

**响应**:
```json
{
  "request_id": 1,
  "from_user_id": 1,
  "to_user_id": 2,
  "status": "pending",
  "message": "Hello!",
  "created_at": "2024-01-01T12:00:00",
  "responded_at": null
}
```

**错误码**:
- `400`: 发送失败（可能已发送过申请）

---

### 2. 获取好友申请列表
**GET** `/users/friend-requests?status={status}`

**查询参数**:
- `status`: 可选，筛选状态（`pending`/`accepted`/`rejected`）

**响应**:
```json
[
  {
    "id": 1,
    "from_user_id": 2,
    "to_user_id": 1,
    "status": "pending",
    "message": "Hello!",
    "created_at": "2024-01-01T12:00:00",
    "responded_at": null,
    "username": "requester_name",
    "nickname": "requester_nickname"
  }
]
```

---

### 3. 处理好友申请
**POST** `/users/friend-requests/{request_id}/respond`

**路径参数**:
- `request_id`: 申请ID

**请求体**:
```json
{
  "accept": true    // true=同意，false=拒绝
}
```

**响应**:
```json
{
  "message": "Friend request accepted successfully"
}
```

**错误码**:
- `400`: 处理失败（申请不存在或已处理）

---

## 群组系统

### 1. 创建群组
**POST** `/groups`

**请求体**:
```json
{
  "name": "Group Name",           // 必填，群组名称
  "description": "Description"    // 可选，群组描述
}
```

**响应**:
```json
{
  "id": 1,
  "name": "Group Name",
  "description": "Description",
  "creator_id": 1,
  "created_at": "2024-01-01T12:00:00"
}
```

---

### 2. 获取用户群组
**GET** `/groups`

**响应**:
```json
[
  {
    "id": 1,
    "name": "Group Name",
    "description": "Description",
    "creator_id": 1,
    "created_at": "2024-01-01T12:00:00",
    "member_count": 5
  }
]
```

---

### 3. 获取群组详情
**GET** `/groups/{group_id}`

**路径参数**:
- `group_id`: 群组ID

**响应**:
```json
{
  "id": 1,
  "name": "Group Name",
  "description": "Description",
  "creator_id": 1,
  "created_at": "2024-01-01T12:00:00"
}
```

**错误码**:
- `403`: 不是群组成员

---

### 4. 获取群组成员
**GET** `/groups/{group_id}/members`

**响应**:
```json
[
  {
    "id": 1,
    "username": "member1",
    "nickname": "nickname1",
    "role": "creator",
    "joined_at": "2024-01-01T12:00:00"
  },
  {
    "id": 2,
    "username": "member2",
    "nickname": "nickname2",
    "role": "member",
    "joined_at": "2024-01-01T12:00:00"
  }
]
```

---

### 5. 添加群组成员
**POST** `/groups/{group_id}/members`

**请求体**:
```json
{
  "user_id": 2    // 要添加的用户ID
}
```

**响应**:
```json
{
  "message": "Member added successfully"
}
```

**错误码**:
- `400`: 添加失败（用户已在群组或不存在）
- `403`: 不是群组成员

---

### 6. 移除群组成员
**DELETE** `/groups/{group_id}/members/{user_id}`

**响应**:
```json
{
  "message": "Member removed successfully"
}
```

---

### 7. 解散群组
**DELETE** `/groups/{group_id}`

**响应**:
```json
{
  "message": "Group deleted successfully"
}
```

**错误码**:
- `403`: 不是群组创建者

---

### 8. 发送群组邀请
**POST** `/groups/{group_id}/invitations`

**请求体**:
```json
{
  "to_user_id": 2,           // 被邀请用户ID
  "message": "Join us!"      // 可选，邀请消息
}
```

**响应**:
```json
{
  "message": "Group invitation sent successfully"
}
```

---

### 9. 获取群组邀请列表
**GET** `/groups/invitations/list?status={status}`

**响应**:
```json
[
  {
    "id": 1,
    "group_id": 1,
    "from_user_id": 2,
    "to_user_id": 1,
    "status": "pending",
    "message": "Join us!",
    "created_at": "2024-01-01T12:00:00",
    "responded_at": null,
    "group_name": "Group Name",
    "description": "Description",
    "username": "inviter_name",
    "nickname": "inviter_nickname"
  }
]
```

---

### 10. 处理群组邀请
**POST** `/groups/invitations/{invitation_id}/respond`

**请求体**:
```json
{
  "accept": true    // true=同意，false=拒绝
}
```

**响应**:
```json
{
  "message": "Group invitation accepted successfully"
}
```

---

## 消息系统

### 1. 获取私聊消息历史
**GET** `/messages/history/personal?other_user_id={id}&limit={limit}`

**查询参数**:
- `other_user_id`: 对方用户ID（必填）
- `limit`: 消息数量（可选，默认50，最大100）

**响应**:
```json
[
  {
    "id": 1,
    "sender_id": 1,
    "receiver_id": 2,
    "group_id": null,
    "content": "Hello!",
    "message_type": "text",
    "created_at": "2024-01-01T12:00:00"
  }
]
```

---

### 2. 获取群组消息历史
**GET** `/messages/history/group?group_id={id}&limit={limit}`

**查询参数**:
- `group_id`: 群组ID（必填）
- `limit`: 消息数量（可选，默认50，最大100）

**响应**: 同上

**错误码**:
- `403`: 不是群组成员

---

### 3. 获取会话列表
**GET** `/messages/conversations`

**响应**:
```json
[
  {
    "other_user_id": 2,
    "last_message_time": "2024-01-01T12:00:00"
  }
]
```

---

## 统计信息

### 1. 获取聊天室统计
**GET** `/stats/chatroom`

**响应**:
```json
{
  "total_users": 100,
  "online_users": 10,
  "total_groups": 20,
  "total_messages": 1000
}
```

---

### 2. 获取用户统计
**GET** `/stats/user`

**响应**:
```json
{
  "messages_sent": 50,
  "messages_received": 30,
  "groups_joined": 5
}
```

---

## WebSocket

### 连接
**WebSocket** `/ws/{token}`

- 使用 JWT Token 作为路径参数连接
- Token 需先通过登录接口获取

### 消息格式

#### 发送私聊消息
```json
{
  "type": "personal",
  "receiver_id": 123,
  "content": "Hello!"
}
```

#### 发送群聊消息
```json
{
  "type": "group",
  "group_id": 456,
  "content": "Hello everyone!"
}
```

#### 心跳消息
```json
{
  "type": "ping"
}
```

**响应**:
```json
{
  "type": "pong",
  "timestamp": "2024-01-01T12:00:00"
}
```

#### 加入群组
```json
{
  "type": "join_group",
  "group_id": 456
}
```

**响应**:
```json
{
  "type": "joined_group",
  "group_id": 456
}
```

#### 离开群组
```json
{
  "type": "leave_group",
  "group_id": 456
}
```

**响应**:
```json
{
  "type": "left_group",
  "group_id": 456
}
```

### 接收消息格式

#### 私聊消息
```json
{
  "type": "personal_message",
  "id": 1,
  "sender_id": 123,
  "receiver_id": 456,
  "content": "Hello!",
  "created_at": "2024-01-01T12:00:00"
}
```

#### 群聊消息
```json
{
  "type": "group_message",
  "id": 1,
  "sender_id": 123,
  "group_id": 456,
  "content": "Hello everyone!",
  "created_at": "2024-01-01T12:00:00"
}
```

#### 发送确认
```json
{
  "type": "personal_message",
  "id": 1,
  "sender_id": 123,
  "receiver_id": 456,
  "content": "Hello!",
  "created_at": "2024-01-01T12:00:00",
  "sent": true
}
```

#### 错误消息
```json
{
  "type": "error",
  "message": "Error description"
}
```

---

## 错误码汇总

| 状态码 | 含义 | 说明 |
|--------|------|------|
| 200 | OK | 请求成功 |
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 未认证或Token无效 |
| 403 | Forbidden | 无权限访问 |
| 404 | Not Found | 资源不存在 |
| 422 | Validation Error | 参数验证失败 |
| 500 | Internal Server Error | 服务器内部错误 |

---

## 数据模型

### User（用户）
```json
{
  "id": 1,
  "username": "string",
  "nickname": "string",
  "created_at": "2024-01-01T00:00:00",
  "last_login": "2024-01-01T12:00:00",
  "is_active": 1
}
```

### Group（群组）
```json
{
  "id": 1,
  "name": "string",
  "description": "string",
  "creator_id": 1,
  "created_at": "2024-01-01T00:00:00"
}
```

### Message（消息）
```json
{
  "id": 1,
  "sender_id": 1,
  "receiver_id": 2,
  "group_id": null,
  "content": "string",
  "message_type": "text",
  "created_at": "2024-01-01T00:00:00"
}
```

### Token（令牌）
```json
{
  "access_token": "string",
  "token_type": "bearer"
}
```
