"""
用户服务层
处理用户相关的数据库操作

主要功能：
- 用户注册、登录验证
- 用户信息查询、更新
- 好友关系管理
- 好友申请处理
- 用户搜索
"""
from datetime import datetime
import aiosqlite
from typing import Optional, List
import os

# 数据库路径
DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chatroom.db")


async def create_user(username: str, password: str, nickname: Optional[str] = None) -> int:
    """
    创建新用户（用户注册）
    
    功能说明：
    1. 在 users 表中插入新用户记录
    2. 如果用户名已存在，返回 -1
    3. 密码应该先进行哈希处理再传入
    
    Args:
        username: 用户名（唯一）
        password: 密码（已哈希）
        nickname: 昵称（可选）
        
    Returns:
        int: 新建用户的 ID，如果用户名已存在返回 -1
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            cursor = await db.execute(
                """
                INSERT INTO users (username, password, nickname)
                VALUES (?, ?, ?)
                """,
                (username, password, nickname)
            )
            await db.commit()
            return cursor.lastrowid
        except aiosqlite.IntegrityError:
            # 用户名已存在（违反唯一约束）
            return -1


async def get_user(user_id: int) -> Optional[dict]:
    """
    根据用户 ID 获取用户信息
    
    功能说明：
    1. 查询 users 表中指定 ID 的用户
    2. 返回完整的用户信息字典
    
    Args:
        user_id: 用户 ID
        
    Returns:
        Optional[dict]: 用户信息字典，包含 id、username、nickname 等字段
                       如果用户不存在返回 None
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_user_by_username(username: str) -> Optional[dict]:
    """
    根据用户名获取用户信息
    
    功能说明：
    1. 查询 users 表中指定用户名的用户
    2. 用于登录验证时查找用户
    
    Args:
        username: 用户名
        
    Returns:
        Optional[dict]: 用户信息字典
                       如果用户不存在返回 None
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_all_users() -> List[dict]:
    """
    获取所有活跃用户列表
    
    Returns:
        List[dict]: 用户列表
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, username, nickname, created_at, last_login, is_active FROM users WHERE is_active = 1"
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_online_users() -> List[dict]:
    """
    获取在线用户列表
    
    Returns:
        List[dict]: 在线用户列表
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT DISTINCT u.id, u.username, u.nickname, o.last_activity
            FROM users u
            JOIN online_users o ON u.id = o.user_id
            WHERE u.is_active = 1
            """
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def update_user_last_login(user_id: int) -> bool:
    """
    更新用户最后登录时间
    
    Args:
        user_id: 用户ID
        
    Returns:
        bool: 是否更新成功
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (datetime.now(), user_id)
        )
        await db.commit()
        return cursor.rowcount > 0


async def update_user_password(user_id: int, new_password: str) -> bool:
    """
    更新用户密码
    
    Args:
        user_id: 用户ID
        new_password: 新密码（已哈希）
        
    Returns:
        bool: 是否更新成功
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "UPDATE users SET password = ? WHERE id = ?",
            (new_password, user_id)
        )
        await db.commit()
        return cursor.rowcount > 0


async def update_user_nickname(user_id: int, nickname: str) -> bool:
    """
    更新用户昵称
    
    Args:
        user_id: 用户ID
        nickname: 新昵称
        
    Returns:
        bool: 是否更新成功
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "UPDATE users SET nickname = ? WHERE id = ?",
            (nickname, user_id)
        )
        await db.commit()
        return cursor.rowcount > 0


async def deactivate_user(user_id: int) -> bool:
    """
    停用用户账号
    
    Args:
        user_id: 用户ID
        
    Returns:
        bool: 是否停用成功
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "UPDATE users SET is_active = 0 WHERE id = ?",
            (user_id,)
        )
        await db.commit()
        return cursor.rowcount > 0


async def activate_user(user_id: int) -> bool:
    """
    激活用户账号
    
    Args:
        user_id: 用户ID
        
    Returns:
        bool: 是否激活成功
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "UPDATE users SET is_active = 1 WHERE id = ?",
            (user_id,)
        )
        await db.commit()
        return cursor.rowcount > 0


async def delete_user(user_id: int) -> bool:
    """
    删除用户
    
    Args:
        user_id: 用户ID
        
    Returns:
        bool: 是否删除成功
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM users WHERE id = ?",
            (user_id,)
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_user_statistics() -> dict:
    """
    获取用户统计信息
    
    Returns:
        dict: 统计信息字典
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT 
                (SELECT COUNT(*) FROM users WHERE is_active = 1) as total_users,
                (SELECT COUNT(*) FROM online_users) as online_users,
                (SELECT COUNT(*) FROM groups) as total_groups,
                (SELECT COUNT(*) FROM messages) as total_messages
            """
        )
        row = await cursor.fetchone()
        return dict(row) if row else {}


async def get_user_chat_statistics(user_id: int) -> dict:
    """
    获取用户聊天统计信息
    
    Args:
        user_id: 用户ID
        
    Returns:
        dict: 统计信息字典
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT 
                (SELECT COUNT(*) FROM messages WHERE sender_id = ?) as messages_sent,
                (SELECT COUNT(*) FROM messages WHERE receiver_id = ?) as messages_received,
                (SELECT COUNT(*) FROM group_members WHERE user_id = ?) as groups_joined
            """,
            (user_id, user_id, user_id)
        )
        row = await cursor.fetchone()
        return dict(row) if row else {}


async def get_user_online_duration(user_id: int) -> int:
    """
    获取用户在线时长（秒）
    
    Args:
        user_id: 用户ID
        
    Returns:
        int: 在线时长（秒）
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """
            SELECT SUM(
                strftime('%s', 'now') - strftime('%s', connected_at)
            ) as total_duration
            FROM online_users
            WHERE user_id = ?
            """,
            (user_id,)
        )
        result = await cursor.fetchone()
        return result[0] if result and result[0] else 0


async def get_all_user_sessions(user_id: int) -> List[dict]:
    """
    获取用户的所有会话
    
    Args:
        user_id: 用户ID
        
    Returns:
        List[dict]: 会话列表
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM online_users WHERE user_id = ?",
            (user_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


# ==================== 好友相关功能 ====================

async def get_user_friends(user_id: int) -> List[dict]:
    """
    获取用户的好友列表
    
    功能说明：
    1. 查询 friendships 表中与指定用户相关的所有好友关系
    2. 由于好友关系是双向的，需要查询两个方向：
       - user_id = 当前用户，friend_id = 好友
       - user_id = 好友，friend_id = 当前用户
    3. 使用 UNION 合并两个查询结果
    4. 返回好友的基本信息（ID、用户名、昵称）
    
    Args:
        user_id: 用户 ID
        
    Returns:
        List[dict]: 好友列表，每个好友包含：
                   - id: 好友 ID
                   - username: 好友用户名
                   - nickname: 好友昵称
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        # 查询双向好友关系
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


async def add_friend(user_id: int, friend_id: int) -> bool:
    """
    添加好友（双向）
    
    Args:
        user_id: 用户ID
        friend_id: 好友ID
        
    Returns:
        bool: 是否添加成功
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            cursor = await db.execute(
                "INSERT INTO friendships (user_id, friend_id) VALUES (?, ?)",
                (user_id, friend_id)
            )
            await db.commit()
            return cursor.rowcount > 0
        except aiosqlite.IntegrityError:
            return False


async def remove_friend(user_id: int, friend_id: int) -> bool:
    """
    删除好友关系
    
    Args:
        user_id: 用户ID
        friend_id: 好友ID
        
    Returns:
        bool: 是否删除成功
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """
            DELETE FROM friendships 
            WHERE (user_id = ? AND friend_id = ?) 
               OR (user_id = ? AND friend_id = ?)
            """,
            (user_id, friend_id, friend_id, user_id)
        )
        await db.commit()
        return cursor.rowcount > 0


# ==================== 好友申请相关功能 ====================

async def send_friend_request(from_user_id: int, to_user_id: int, message: Optional[str] = None) -> bool:
    """
    发送好友申请
    
    功能说明：
    1. 在 friend_requests 表中创建申请记录
    2. 状态默认为 'pending'（待处理）
    3. 通过 WebSocket 向被申请者发送实时通知
    4. 如果已存在未处理的申请，则返回失败（数据库唯一约束）
    
    Args:
        from_user_id: 申请者 ID
        to_user_id: 目标用户 ID（被申请者）
        message: 申请消息（可选）
        
    Returns:
        bool: 是否发送成功（True 成功，False 失败）
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            # 创建好友申请记录
            cursor = await db.execute(
                """
                INSERT INTO friend_requests (from_user_id, to_user_id, message)
                VALUES (?, ?, ?)
                """,
                (from_user_id, to_user_id, message)
            )
            await db.commit()
            
            if cursor.rowcount > 0:
                request_id = cursor.lastrowid
                
                # 获取申请者信息
                from_user = await get_user(from_user_id)
                
                # 通过 WebSocket 通知对方
                from app.core.connection_manager import connection_manager
                from datetime import datetime
                notification = {
                    "type": "friend_request",
                    "request_id": request_id,
                    "from_user_id": from_user_id,
                    "from_username": from_user["username"] if from_user else "Unknown",
                    "from_nickname": from_user["nickname"] if from_user else None,
                    "message": message,
                    "created_at": datetime.now().isoformat()
                }
                
                # 发送 WebSocket 通知给被申请者
                await connection_manager.send_personal_message(notification, to_user_id)
                
                return True
            return False
        except aiosqlite.IntegrityError:
            # 已存在未处理的申请
            return False


async def respond_friend_request(request_id: int, to_user_id: int, accept: bool) -> bool:
    """
    响应好友申请
    
    功能说明：
    1. 验证申请是否存在且属于当前用户
    2. 检查申请状态是否为 'pending'（待处理）
    3. 如果接受申请：
       - 在 friendships 表中创建双向好友关系记录
       - 更新申请状态为 'accepted'
    4. 如果拒绝申请：
       - 更新申请状态为 'rejected'
    
    Args:
        request_id: 申请 ID
        to_user_id: 响应者 ID（必须是目标用户/被申请者）
        accept: 是否接受（True 接受，False 拒绝）
        
    Returns:
        bool: 是否响应成功（True 成功，False 失败）
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        # 查询申请记录
        cursor = await db.execute(
            """
            SELECT from_user_id, to_user_id, status 
            FROM friend_requests 
            WHERE id = ? AND to_user_id = ?
            """,
            (request_id, to_user_id)
        )
        row = await cursor.fetchone()
        if not row:
            # 申请不存在或不属于当前用户
            return False
        
        row_dict = dict(row)
        if row_dict['status'] != 'pending':
            # 申请已处理过，不能重复响应
            return False
        
        from_user_id = row_dict['from_user_id']
        
        if accept:
            # 接受申请：创建双向好友关系
            # 记录 1: user_id = 申请者，friend_id = 响应者
            await db.execute(
                "INSERT INTO friendships (user_id, friend_id) VALUES (?, ?)",
                (from_user_id, to_user_id)
            )
            # 记录 2: user_id = 响应者，friend_id = 申请者
            await db.execute(
                "INSERT INTO friendships (user_id, friend_id) VALUES (?, ?)",
                (to_user_id, from_user_id)
            )
        
        # 更新申请状态
        await db.execute(
            """
            UPDATE friend_requests 
            SET status = ?, responded_at = ? 
            WHERE id = ?
            """,
            ('accepted' if accept else 'rejected', datetime.now(), request_id)
        )
        await db.commit()
        
        to_user = await get_user(to_user_id)
        from app.core.connection_manager import connection_manager
        notification = {
            "type": "friend_response",
            "request_id": request_id,
            "to_user_id": to_user_id,
            "to_username": to_user["username"] if to_user else "Unknown",
            "to_nickname": to_user["nickname"] if to_user else None,
            "accept": accept,
            "responded_at": datetime.now().isoformat()
        }
        
        await connection_manager.send_personal_message(notification, from_user_id)
        
        return True


async def get_friend_requests(user_id: int, status: Optional[str] = None) -> List[dict]:
    """
    获取好友申请列表
    
    Args:
        user_id: 用户ID
        status: 状态筛选（可选：pending/accepted/rejected）
        
    Returns:
        List[dict]: 申请列表
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        if status:
            cursor = await db.execute(
                """
                SELECT fr.*, u.username, u.nickname 
                FROM friend_requests fr
                JOIN users u ON fr.from_user_id = u.id
                WHERE fr.to_user_id = ? AND fr.status = ?
                ORDER BY fr.created_at DESC
                """,
                (user_id, status)
            )
        else:
            cursor = await db.execute(
                """
                SELECT fr.*, u.username, u.nickname 
                FROM friend_requests fr
                JOIN users u ON fr.from_user_id = u.id
                WHERE fr.to_user_id = ?
                ORDER BY fr.created_at DESC
                """,
                (user_id,)
            )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def search_users_by_username(username: str, current_user_id: int) -> List[dict]:
    """
    根据用户名搜索用户（模糊匹配）
    
    功能说明：
    1. 使用 LIKE 进行模糊匹配，支持部分匹配
    2. 排除当前用户自己（不能搜索到自己）
    3. 返回用户的基本信息
    4. 按用户名排序
    
    Args:
        username: 搜索关键词（支持部分匹配）
        current_user_id: 当前用户 ID（排除自己）
        
    Returns:
        List[dict]: 用户列表，每个用户包含：
                   - id: 用户 ID
                   - username: 用户名
                   - nickname: 昵称
                   - created_at: 创建时间
                   - last_login: 最后登录时间
                   - is_active: 是否激活
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        # 使用 LIKE 进行模糊匹配，% 表示通配符
        cursor = await db.execute(
            """
            SELECT id, username, nickname, created_at, last_login, is_active
            FROM users 
            WHERE username LIKE ? AND id != ?
            ORDER BY username
            """,
            (f'%{username}%', current_user_id)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
