# 聊天室后端系统设计文档

## 目录
1. [系统概述](#系统概述)
2. [数据库设计](#数据库设计)
3. [好友系统](#好友系统)
4. [群组系统](#群组系统)
5. [WebSocket实时通信](#websocket实时通信)
6. [API接口设计](#api接口设计)
7. [核心流程](#核心流程)

---

## 系统概述

### 功能模块
- **用户认证**：注册、登录、JWT Token管理
- **好友系统**：添加好友、好友申请、好友列表
- **群组系统**：创建群组、邀请成员、群聊管理
- **消息系统**：私聊消息、群聊消息、消息历史
- **实时通信**：WebSocket连接、消息广播

### 技术栈
- **框架**：FastAPI (Python)
- **数据库**：SQLite (aiosqlite异步驱动)
- **认证**：JWT (PyJWT)
- **密码加密**：Passlib (bcrypt)
- **WebSocket**：FastAPI原生WebSocket支持

---

## 数据库设计

### 1. 用户表 (users)
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,      -- 用户名(唯一)
    password_hash TEXT NOT NULL,        -- 密码哈希
    nickname TEXT,                       -- 昵称
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active INTEGER DEFAULT 1
);
```

### 2. 好友关系表 (friendships)
```sql
CREATE TABLE friendships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,           -- 用户ID
    friend_id INTEGER NOT NULL,         -- 好友ID
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, friend_id),         -- 唯一约束，防止重复
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (friend_id) REFERENCES users(id)
);
```

### 3. 好友申请表 (friend_requests)
```sql
CREATE TABLE friend_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_user_id INTEGER NOT NULL,      -- 申请发送者
    to_user_id INTEGER NOT NULL,        -- 申请接收者
    status TEXT DEFAULT 'pending',      -- 状态: pending/accepted/rejected
    message TEXT,                        -- 申请消息
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    responded_at TIMESTAMP,
    FOREIGN KEY (from_user_id) REFERENCES users(id),
    FOREIGN KEY (to_user_id) REFERENCES users(id),
    UNIQUE(from_user_id, to_user_id, status)  -- 唯一约束
);
```

### 4. 群组表 (groups)
```sql
CREATE TABLE groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                  -- 群组名称
    description TEXT,                    -- 群组描述
    creator_id INTEGER NOT NULL,         -- 创建者ID
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (creator_id) REFERENCES users(id)
);
```

### 5. 群组成员表 (group_members)
```sql
CREATE TABLE group_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL,           -- 群组ID
    user_id INTEGER NOT NULL,            -- 用户ID
    role TEXT DEFAULT 'member',          -- 角色: creator/admin/member
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(group_id, user_id),           -- 唯一约束，防止重复加入
    FOREIGN KEY (group_id) REFERENCES groups(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### 6. 群组邀请表 (group_invitations)
```sql
CREATE TABLE group_invitations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL,           -- 群组ID
    from_user_id INTEGER NOT NULL,       -- 邀请者ID
    to_user_id INTEGER NOT NULL,         -- 被邀请者ID
    status TEXT DEFAULT 'pending',       -- 状态: pending/accepted/rejected
    message TEXT,                        -- 邀请消息
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    responded_at TIMESTAMP,
    FOREIGN KEY (group_id) REFERENCES groups(id),
    FOREIGN KEY (from_user_id) REFERENCES users(id),
    FOREIGN KEY (to_user_id) REFERENCES users(id),
    UNIQUE(group_id, from_user_id, to_user_id)  -- 唯一约束
);
```

### 7. 消息表 (messages)
```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL,          -- 发送者ID
    receiver_id INTEGER,                 -- 接收者ID(私聊)
    group_id INTEGER,                    -- 群组ID(群聊)
    content TEXT NOT NULL,               -- 消息内容
    message_type TEXT DEFAULT 'text',    -- 消息类型
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_id) REFERENCES users(id),
    FOREIGN KEY (receiver_id) REFERENCES users(id),
    FOREIGN KEY (group_id) REFERENCES groups(id)
);
```

---

## 好友系统

### 核心概念

#### 1. 好友关系模型
- **双向关系**：好友关系是双向的，A是B的好友，B也是A的好友
- **唯一性**：通过数据库唯一约束防止重复添加
- **状态管理**：好友申请有 pending/accepted/rejected 三种状态

#### 2. 添加好友流程

```
用户A                    后端                    用户B
  |                       |                       |
  |--- 发送好友申请 ----->|                       |
  |                       |-- 保存申请记录 --.    |
  |                       |                   |   |
  |                       |-- WebSocket通知 ->|   |
  |                       |                       |
  |                       |<-- 用户B收到通知 -----|
  |                       |                       |
  |                       |<-- 用户B响应申请 -----|
  |                       |                       |
  |                       |-- 更新申请状态 --.    |
  |                       |                   |   |
  |                       |-- 如接受:创建双向关系 |
  |                       |                       |
  |<-- WebSocket通知结果 -|                       |
```

### 实现代码

#### 发送好友申请
```python
async def send_friend_request(from_user_id: int, to_user_id: int, message: str = None) -> bool:
    """
    发送好友申请
    
    流程:
    1. 检查是否自己申请自己
    2. 检查是否已是好友
    3. 检查是否已有待处理申请
    4. 创建申请记录
    5. 发送WebSocket通知给被申请者
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            # 1. 检查是否自己申请自己
            if from_user_id == to_user_id:
                return False
            
            # 2. 检查是否已是好友
            cursor = await db.execute(
                """
                SELECT 1 FROM friendships 
                WHERE (user_id = ? AND friend_id = ?) 
                   OR (user_id = ? AND friend_id = ?)
                """,
                (from_user_id, to_user_id, to_user_id, from_user_id)
            )
            if await cursor.fetchone():
                return False
            
            # 3. 创建申请记录
            cursor = await db.execute(
                """
                INSERT INTO friend_requests (from_user_id, to_user_id, message)
                VALUES (?, ?, ?)
                """,
                (from_user_id, to_user_id, message)
            )
            await db.commit()
            
            if cursor.rowcount > 0:
                # 4. 发送WebSocket通知
                request_id = cursor.lastrowid
                notification = {
                    "type": "friend_request",
                    "request_id": request_id,
                    "from_user_id": from_user_id,
                    "from_username": from_user["username"],
                    "message": message
                }
                await connection_manager.send_personal_message(notification, to_user_id)
                return True
            return False
            
        except aiosqlite.IntegrityError:
            # 已有待处理申请
            return False
```

#### 响应好友申请
```python
async def respond_friend_request(request_id: int, to_user_id: int, accept: bool) -> bool:
    """
    响应好友申请
    
    流程:
    1. 验证申请是否存在且属于当前用户
    2. 检查申请状态是否为pending
    3. 如接受: 创建双向好友关系
    4. 更新申请状态
    5. 发送WebSocket通知给申请者
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # 1. 获取申请信息
        cursor = await db.execute(
            """
            SELECT from_user_id, status 
            FROM friend_requests 
            WHERE id = ? AND to_user_id = ?
            """,
            (request_id, to_user_id)
        )
        row = await cursor.fetchone()
        if not row or row[1] != 'pending':
            return False
        
        from_user_id = row[0]
        
        if accept:
            # 2. 创建双向好友关系
            await db.execute(
                "INSERT INTO friendships (user_id, friend_id) VALUES (?, ?)",
                (from_user_id, to_user_id)
            )
            await db.execute(
                "INSERT INTO friendships (user_id, friend_id) VALUES (?, ?)",
                (to_user_id, from_user_id)
            )
        
        # 3. 更新申请状态
        await db.execute(
            """
            UPDATE friend_requests 
            SET status = ?, responded_at = ? 
            WHERE id = ?
            """,
            ('accepted' if accept else 'rejected', datetime.now(), request_id)
        )
        await db.commit()
        
        # 4. 发送WebSocket通知
        notification = {
            "type": "friend_response",
            "request_id": request_id,
            "from_user_id": from_user_id,
            "to_user_id": to_user_id,
            "accept": accept
        }
        await connection_manager.send_personal_message(notification, from_user_id)
        return True
```

#### 获取好友列表
```python
async def get_user_friends(user_id: int) -> List[dict]:
    """
    获取用户好友列表
    
    使用UNION查询双向好友关系:
    - 用户A -> 用户B
    - 用户B -> 用户A
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """
            SELECT u.id, u.username, u.nickname
            FROM users u
            JOIN friendships f ON u.id = f.friend_id
            WHERE f.user_id = ?
            UNION
            SELECT u.id, u.username, u.nickname
            FROM users u
            JOIN friendships f ON u.id = f.user_id
            WHERE f.friend_id = ?
            """,
            (user_id, user_id)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
```

---

## 群组系统

### 核心概念

#### 1. 群组角色
- **creator**: 群主，拥有所有权限
- **admin**: 管理员，可管理成员
- **member**: 普通成员

#### 2. 群组生命周期
```
创建群组 -> 邀请成员 -> 成员接受 -> 群组聊天 -> 成员退出/被移除 -> 解散群组
```

#### 3. 邀请机制
- **邀请权限**: 群组成员可以邀请好友
- **邀请审批**: 被邀请者需要同意才能加入
- **唯一性**: 同一用户对同一群组只能有一个待处理邀请

### 实现代码

#### 创建群组
```python
async def create_group(name: str, description: str, creator_id: int) -> int:
    """
    创建群组
    
    流程:
    1. 创建群组记录
    2. 自动将创建者添加为成员，角色为creator
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # 1. 创建群组
        cursor = await db.execute(
            """
            INSERT INTO groups (name, description, creator_id)
            VALUES (?, ?, ?)
            """,
            (name, description, creator_id)
        )
        await db.commit()
        group_id = cursor.lastrowid
        
        # 2. 添加创建者为成员
        await db.execute(
            """
            INSERT INTO group_members (group_id, user_id, role)
            VALUES (?, ?, 'creator')
            """,
            (group_id, creator_id)
        )
        await db.commit()
        return group_id
```

#### 发送群组邀请
```python
async def send_group_invitation(
    group_id: int, 
    from_user_id: int, 
    to_user_id: int, 
    message: str = None
) -> bool:
    """
    发送群组邀请
    
    流程:
    1. 验证发送者是否为群组成员
    2. 检查被邀请者是否已是成员
    3. 检查是否已有待处理邀请
    4. 创建邀请记录
    5. 发送WebSocket通知
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # 1. 验证发送者是群组成员
        cursor = await db.execute(
            "SELECT 1 FROM group_members WHERE group_id = ? AND user_id = ?",
            (group_id, from_user_id)
        )
        if not await cursor.fetchone():
            return False
        
        # 2. 检查被邀请者是否已是成员
        cursor = await db.execute(
            "SELECT 1 FROM group_members WHERE group_id = ? AND user_id = ?",
            (group_id, to_user_id)
        )
        if await cursor.fetchone():
            return False
        
        try:
            # 3. 创建邀请记录
            cursor = await db.execute(
                """
                INSERT INTO group_invitations 
                (group_id, from_user_id, to_user_id, message)
                VALUES (?, ?, ?, ?)
                """,
                (group_id, from_user_id, to_user_id, message)
            )
            await db.commit()
            
            if cursor.rowcount > 0:
                invitation_id = cursor.lastrowid
                
                # 4. 发送WebSocket通知
                notification = {
                    "type": "group_invitation",
                    "invitation_id": invitation_id,
                    "group_id": group_id,
                    "group_name": group_name,
                    "from_user_id": from_user_id,
                    "message": message
                }
                await connection_manager.send_personal_message(notification, to_user_id)
                return True
            return False
            
        except aiosqlite.IntegrityError:
            # 已有待处理邀请
            return False
```

#### 响应群组邀请
```python
async def respond_group_invitation(
    invitation_id: int, 
    to_user_id: int, 
    accept: bool
) -> bool:
    """
    响应群组邀请
    
    流程:
    1. 验证邀请是否存在且属于当前用户
    2. 检查邀请状态
    3. 如接受: 添加用户到群组
    4. 更新邀请状态
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # 1. 获取邀请信息
        cursor = await db.execute(
            """
            SELECT group_id, from_user_id, status 
            FROM group_invitations 
            WHERE id = ? AND to_user_id = ?
            """,
            (invitation_id, to_user_id)
        )
        row = await cursor.fetchone()
        if not row or row[2] != 'pending':
            return False
        
        group_id = row[0]
        
        if accept:
            # 2. 添加用户到群组
            await db.execute(
                """
                INSERT INTO group_members (group_id, user_id, role)
                VALUES (?, ?, 'member')
                """,
                (group_id, to_user_id)
            )
        
        # 3. 更新邀请状态
        await db.execute(
            """
            UPDATE group_invitations 
            SET status = ?, responded_at = ? 
            WHERE id = ?
            """,
            ('accepted' if accept else 'rejected', datetime.now(), invitation_id)
        )
        await db.commit()
        return True
```

#### 获取群组成员
```python
async def get_group_members(group_id: int) -> List[dict]:
    """
    获取群组成员列表
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """
            SELECT u.id, u.username, u.nickname, gm.role, gm.joined_at
            FROM users u
            JOIN group_members gm ON u.id = gm.user_id
            WHERE gm.group_id = ?
            """,
            (group_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
```

---

## WebSocket实时通信

### 连接管理

#### ConnectionManager 类
```python
@dataclass
class ConnectionManager:
    """
    WebSocket连接管理器
    
    管理所有用户的WebSocket连接，支持:
    - 多会话管理(同一用户多个设备)
    - 群组聊天室
    - 消息广播
    """
    active_connections: Dict[int, Dict[str, any]]  # user_id -> {session_id -> connection}
    user_sessions: Dict[int, List[str]]            # user_id -> [session_id, ...]
    group_connections: Dict[int, List[str]]        # group_id -> [session_id, ...]
```

#### 连接建立
```python
async def connect(self, websocket, user_id: int, session_id: str):
    """建立新的WebSocket连接"""
    await websocket.accept()
    
    # 记录连接信息
    if user_id not in self.active_connections:
        self.active_connections[user_id] = {}
    self.active_connections[user_id][session_id] = {
        "websocket": websocket,
        "connected_at": datetime.now()
    }
    
    # 记录会话
    if user_id not in self.user_sessions:
        self.user_sessions[user_id] = []
    self.user_sessions[user_id].append(session_id)
```

#### 发送个人消息
```python
async def send_personal_message(self, message: dict, user_id: int):
    """发送消息给指定用户的所有会话"""
    if user_id in self.active_connections:
        for session_id, connection in self.active_connections[user_id].items():
            try:
                await connection["websocket"].send_json(message)
            except Exception as e:
                print(f"发送消息失败: {e}")
```

#### 发送群组消息
```python
async def send_group_message(self, message: dict, group_id: int, sender_id: int):
    """发送消息给群组所有成员"""
    if group_id not in self.group_connections:
        return
    
    # 建立session到user的映射
    session_to_user = {}
    for user_id, sessions in self.active_connections.items():
        for session_id in sessions:
            session_to_user[session_id] = user_id
    
    # 发送给群组所有成员
    for session_id in self.group_connections[group_id]:
        if session_id in session_to_user:
            user_id = session_to_user[session_id]
            try:
                await self.active_connections[user_id][session_id]["websocket"].send_json(message)
            except Exception as e:
                print(f"发送消息给用户 {user_id} 失败: {e}")
```

#### 加入群组
```python
async def add_to_group(self, group_id: int, user_id: int, session_id: str):
    """将用户添加到群组连接"""
    if group_id not in self.group_connections:
        self.group_connections[group_id] = []
    if session_id not in self.group_connections[group_id]:
        self.group_connections[group_id].append(session_id)
```

### WebSocket消息处理

```python
async def websocket_endpoint(websocket: WebSocket, token: str):
    """WebSocket连接处理"""
    # 验证Token
    user = await get_current_user(token)
    if not user:
        await websocket.close(code=4001)
        return
    
    session_id = str(uuid.uuid4())
    await connection_manager.connect(websocket, user["id"], session_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            message_type = message_data.get("type")
            
            if message_type == "personal":
                await handle_personal_message(websocket, user, message_data, session_id)
            
            elif message_type == "group":
                await handle_group_message(websocket, user, message_data, session_id)
            
            elif message_type == "join_group":
                await handle_join_group(websocket, user, message_data, session_id)
            
            elif message_type == "ping":
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        await connection_manager.disconnect(user["id"], session_id)
```

---

## API接口设计

### 好友相关接口

| 方法 | 路径 | 描述 | 请求体 | 响应 |
|------|------|------|--------|------|
| POST | /api/users/friend-requests | 发送好友申请 | {to_user_id, message} | {message} |
| GET | /api/users/friend-requests | 获取好友申请列表 | - | [FriendRequest] |
| POST | /api/users/friend-requests/{id}/respond | 响应好友申请 | {accept} | {message} |
| GET | /api/users/friends | 获取好友列表 | - | [User] |
| DELETE | /api/users/friends/{friend_id} | 删除好友 | - | {message} |

### 群组相关接口

| 方法 | 路径 | 描述 | 请求体 | 响应 |
|------|------|------|--------|------|
| POST | /api/groups | 创建群组 | {name, description} | Group |
| GET | /api/groups | 获取用户群组列表 | - | [Group] |
| GET | /api/groups/{id} | 获取群组详情 | - | Group |
| GET | /api/groups/{id}/members | 获取群组成员 | - | [GroupMember] |
| POST | /api/groups/{id}/invitations | 发送群组邀请 | {to_user_id, message} | {message} |
| GET | /api/groups/invitations/list | 获取群组邀请列表 | - | [GroupInvitation] |
| POST | /api/groups/invitations/{id}/respond | 响应群组邀请 | {accept} | {message} |
| DELETE | /api/groups/{id} | 解散群组 | - | {message} |

### 消息相关接口

| 方法 | 路径 | 描述 | 请求体 | 响应 |
|------|------|------|--------|------|
| GET | /api/messages/history/personal | 获取私聊历史 | other_user_id | {messages} |
| GET | /api/messages/history/group | 获取群聊历史 | group_id | {messages} |

---

## 核心流程

### 1. 添加好友完整流程

```
1. 用户A搜索用户B
2. 用户A点击"添加好友"，填写申请消息
3. 前端调用 POST /api/users/friend-requests
4. 后端:
   - 验证用户B是否存在
   - 检查是否已是好友
   - 创建friend_requests记录(status=pending)
   - 通过WebSocket发送通知给用户B
5. 用户B收到桌面通知
6. 用户B点击通知或进入好友申请页面
7. 用户B点击"同意"或"拒绝"
8. 前端调用 POST /api/users/friend-requests/{id}/respond
9. 后端:
   - 更新friend_requests状态
   - 如接受: 创建双向friendships记录
   - 通过WebSocket通知用户A结果
10. 用户A收到结果通知
11. 双方好友列表自动更新
```

### 2. 创建群组并邀请成员流程

```
1. 用户A点击"创建群组"
2. 填写群组名称和描述
3. 前端调用 POST /api/groups
4. 后端:
   - 创建groups记录
   - 创建group_members记录(用户A为creator)
5. 用户A进入群组页面
6. 用户A点击"邀请好友"
7. 选择好友用户B
8. 前端调用 POST /api/groups/{id}/invitations
9. 后端:
   - 验证用户A是群组成员
   - 检查用户B是否已是成员
   - 创建group_invitations记录
   - 通过WebSocket通知用户B
10. 用户B收到群组邀请通知
11. 用户B点击通知进入邀请页面
12. 用户B点击"接受邀请"
13. 前端调用 POST /api/groups/invitations/{id}/respond
14. 后端:
    - 更新group_invitations状态
    - 创建group_members记录(用户B为member)
15. 用户B自动跳转到群组聊天页面
16. 双方都可以在群组中发送和接收消息
```

### 3. 群聊消息流程

```
1. 用户A在群组中输入消息并发送
2. 前端通过WebSocket发送: {type: "group", group_id: 1, content: "Hello"}
3. 后端WebSocket处理:
   - 验证用户A是群组成员
   - 保存消息到messages表
   - 调用send_group_message广播消息
4. 所有在线群组成员收到WebSocket消息
5. 前端显示新消息
6. 离线用户下次登录后通过API获取历史消息
```

---

## 安全考虑

1. **身份验证**: 所有API都需要JWT Token
2. **权限检查**: 
   - 只有群组成员才能发送群聊消息
   - 只有群组成员才能邀请新成员
   - 只有群主才能解散群组
3. **数据验证**: 使用Pydantic模型验证请求数据
4. **SQL注入防护**: 使用参数化查询
5. **XSS防护**: 消息内容需要转义处理

---

## 性能优化

1. **数据库索引**:
   - friendships(user_id, friend_id)
   - friend_requests(from_user_id, to_user_id, status)
   - group_members(group_id, user_id)
   - messages(sender_id, receiver_id, created_at)
   - messages(group_id, created_at)

2. **缓存策略**:
   - 好友列表可以缓存
   - 群组成员列表可以缓存

3. **分页加载**:
   - 消息历史分页返回
   - 好友列表分页(如果好友很多)

---

## 扩展建议

1. **离线消息**: 使用消息队列处理离线用户的消息推送
2. **文件传输**: 支持图片、文件上传和下载
3. **消息已读**: 添加消息已读状态追踪
4. **@功能**: 支持在群聊中@特定成员
5. **消息撤回**: 支持撤回已发送的消息
6. **群公告**: 群主可以发布群公告
7. **禁言功能**: 群主/管理员可以禁言成员
