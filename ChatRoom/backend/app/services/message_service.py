"""
消息服务层
处理消息相关的数据库操作

主要功能：
- 创建和查询消息
- 私聊消息历史记录
- 群聊消息历史记录
- 消息存储和检索
"""
from datetime import datetime
import aiosqlite
from typing import Optional, List
import os

# 数据库路径
DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chatroom.db")


async def create_message(
    sender_id: int,
    receiver_id: Optional[int] = None,
    group_id: Optional[int] = None,
    content: str = "",
    message_type: str = "text"
) -> int:
    """
    创建新消息
    
    功能说明：
    1. 在 messages 表中插入新消息记录
    2. 私聊消息：receiver_id 有值，group_id 为 None
    3. 群聊消息：group_id 有值，receiver_id 为 None
    4. 自动设置 created_at 为当前时间
    
    Args:
        sender_id: 消息发送者 ID
        receiver_id: 消息接收者 ID（私聊时有值）
        group_id: 群组 ID（群聊时有值）
        content: 消息内容
        message_type: 消息类型（text/image/file 等，默认 text）
        
    Returns:
        int: 新建消息的 ID
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO messages (sender_id, receiver_id, group_id, content, message_type)
            VALUES (?, ?, ?, ?, ?)
            """,
            (sender_id, receiver_id, group_id, content, message_type)
        )
        await db.commit()
        return cursor.lastrowid


async def get_message(message_id: int) -> Optional[dict]:
    """
    根据消息 ID 获取消息详情
    
    功能说明：
    1. 查询 messages 表中指定 ID 的消息
    2. 返回完整的消息信息
    
    Args:
        message_id: 消息 ID
        
    Returns:
        Optional[dict]: 消息字典，包含所有字段
                       如果消息不存在返回 None
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM messages WHERE id = ?",
            (message_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_personal_messages(user1_id: int, user2_id: int, limit: int = 50) -> List[dict]:
    """
    获取两个用户之间的私聊消息历史
    
    功能说明：
    1. 查询两个用户之间的双向消息记录
    2. 包括 user1->user2 和 user2->user1 的所有消息
    3. 按创建时间倒序排列（最新的在前）
    4. 限制返回数量以避免过多数据
    
    Args:
        user1_id: 用户 1 ID
        user2_id: 用户 2 ID
        limit: 返回消息数量限制（默认 50 条）
        
    Returns:
        List[dict]: 消息列表，按时间倒序排列
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT * FROM messages 
            WHERE (sender_id = ? AND receiver_id = ?) 
               OR (sender_id = ? AND receiver_id = ?)
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user1_id, user2_id, user2_id, user1_id, limit)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_group_messages(group_id: int, limit: int = 50) -> List[dict]:
    """
    获取群组消息历史
    
    功能说明：
    1. 查询指定群组的所有消息
    2. 按创建时间倒序排列（最新的在前）
    3. 限制返回数量以避免过多数据
    
    Args:
        group_id: 群组 ID
        limit: 返回消息数量限制（默认 50 条）
        
    Returns:
        List[dict]: 群组消息列表，按时间倒序排列
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT * FROM messages 
            WHERE group_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (group_id, limit)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_conversation_list(user_id: int) -> List[dict]:
    """
    获取用户的会话列表
    
    Args:
        user_id: 用户ID
        
    Returns:
        List[dict]: 会话列表
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT DISTINCT 
                CASE 
                    WHEN sender_id = ? THEN receiver_id 
                    ELSE sender_id 
                END as other_user_id,
                MAX(created_at) as last_message_time
            FROM messages
            WHERE sender_id = ? OR receiver_id = ?
            GROUP BY CASE 
                WHEN sender_id = ? THEN receiver_id 
                ELSE sender_id 
            END
            ORDER BY last_message_time DESC
            """,
            (user_id, user_id, user_id, user_id)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_unread_count(user_id: int) -> int:
    """
    获取用户未读消息数量
    
    Args:
        user_id: 用户ID
        
    Returns:
        int: 未读消息数量
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM messages WHERE receiver_id = ? AND read_status = 0",
            (user_id,)
        )
        result = await cursor.fetchone()
        return result[0] if result else 0


async def mark_messages_as_read(user_id: int, other_user_id: int) -> int:
    """
    标记消息为已读
    
    Args:
        user_id: 用户ID
        other_user_id: 对方用户ID
        
    Returns:
        int: 标记的消息数量
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """
            UPDATE messages 
            SET read_status = 1 
            WHERE sender_id = ? AND receiver_id = ? AND read_status = 0
            """,
            (other_user_id, user_id)
        )
        await db.commit()
        return cursor.rowcount


async def get_user_message_stats(user_id: int) -> dict:
    """
    获取用户消息统计
    
    Args:
        user_id: 用户ID
        
    Returns:
        dict: 统计信息
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT 
                (SELECT COUNT(*) FROM messages WHERE sender_id = ?) as sent_count,
                (SELECT COUNT(*) FROM messages WHERE receiver_id = ?) as received_count
            """,
            (user_id, user_id)
        )
        row = await cursor.fetchone()
        return dict(row) if row else {"sent_count": 0, "received_count": 0}
