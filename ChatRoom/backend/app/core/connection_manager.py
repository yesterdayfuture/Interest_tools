"""
WebSocket 连接管理器
管理用户的 WebSocket 连接、群组连接和消息广播

主要功能：
- 管理用户 WebSocket 连接（支持多会话）
- 管理群组聊天室
- 发送个人消息和广播消息
- 记录用户在线状态
"""
import json
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import aiosqlite
import os

# 数据库路径
DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chatroom.db")


@dataclass
class ConnectionManager:
    """
    WebSocket 连接管理器
    
    管理所有用户的 WebSocket 连接，支持多会话、群组消息广播等功能
    
    数据结构说明：
    - active_connections: {user_id: {session_id: {websocket, connected_at, last_activity}}}
    - user_sessions: {user_id: [session_id1, session_id2, ...]}
    - group_connections: {group_id: [session_id1, session_id2, ...]}
    """
    # 活跃连接：user_id -> {session_id -> connection_info}
    active_connections: Dict[int, Dict[str, any]] = field(default_factory=dict)
    # 用户会话列表：user_id -> [session_id, ...]
    user_sessions: Dict[int, List[str]] = field(default_factory=dict)
    # 群组连接：group_id -> [session_id, ...]
    group_connections: Dict[int, List[str]] = field(default_factory=dict)
    
    async def connect(
        self,
        websocket,
        user_id: int,
        session_id: str
    ):
        """
        建立新的 WebSocket 连接
        
        功能说明：
        1. 接受 WebSocket 连接
        2. 在内存中记录连接信息
        3. 在数据库中记录在线状态
        4. 支持同一用户多个会话
        
        Args:
            websocket: WebSocket 对象
            user_id: 用户 ID
            session_id: 会话 ID（唯一标识）
        """
        # 接受 WebSocket 连接
        await websocket.accept()
        
        # 在内存中记录连接
        if user_id not in self.active_connections:
            self.active_connections[user_id] = {}
        self.active_connections[user_id][session_id] = {
            "websocket": websocket,
            "connected_at": datetime.now(),
            "last_activity": datetime.now()
        }
        
        # 记录用户会话
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = []
        if session_id not in self.user_sessions[user_id]:
            self.user_sessions[user_id].append(session_id)
        
        # 记录到数据库
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO online_users 
                (user_id, session_id, connected_at, last_activity)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, session_id, datetime.now(), datetime.now())
            )
            await db.commit()
    
    async def disconnect(self, user_id: int, session_id: str):
        """
        断开 WebSocket 连接
        
        功能说明：
        1. 从内存中删除连接记录
        2. 从数据库中删除在线记录
        3. 清理相关群组连接
        
        Args:
            user_id: 用户 ID
            session_id: 会话 ID
        """
        if user_id in self.active_connections and session_id in self.active_connections[user_id]:
            del self.active_connections[user_id][session_id]
            
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
            
            if user_id in self.user_sessions and session_id in self.user_sessions[user_id]:
                self.user_sessions[user_id].remove(session_id)
                if not self.user_sessions[user_id]:
                    del self.user_sessions[user_id]
            
            # 从数据库中删除
            async with aiosqlite.connect(DATABASE_PATH) as db:
                await db.execute(
                    "DELETE FROM online_users WHERE user_id = ? AND session_id = ?",
                    (user_id, session_id)
                )
                await db.commit()
    
    async def update_last_activity(self, user_id: int, session_id: str):
        """
        更新用户最后活动时间
        
        Args:
            user_id: 用户ID
            session_id: 会话ID
        """
        if user_id in self.active_connections and session_id in self.active_connections[user_id]:
            self.active_connections[user_id][session_id]["last_activity"] = datetime.now()
            
            async with aiosqlite.connect(DATABASE_PATH) as db:
                await db.execute(
                    "UPDATE online_users SET last_activity = ? WHERE user_id = ? AND session_id = ?",
                    (datetime.now(), user_id, session_id)
                )
                await db.commit()
    
    async def send_personal_message(self, message: dict, user_id: int, session_id: Optional[str] = None):
        """
        发送私聊消息
        
        Args:
            message: 消息内容字典
            user_id: 目标用户ID
            session_id: 特定会话ID（可选，不指定则发送到所有会话）
        """
        if user_id in self.active_connections:
            if session_id:
                if session_id in self.active_connections[user_id]:
                    await self.active_connections[user_id][session_id]["websocket"].send_json(message)
            else:
                for session_id in self.active_connections[user_id]:
                    await self.active_connections[user_id][session_id]["websocket"].send_json(message)
    
    async def send_group_message(self, message: dict, group_id: int, sender_id: int):
        """
        发送群组消息
        
        功能说明：
        1. 获取群组的所有连接会话
        2. 遍历每个会话，找到对应的用户
        3. 发送消息给所有群组成员（包括发送者自己，用于确认）
        
        Args:
            message: 消息内容字典
            group_id: 群组ID
            sender_id: 发送者ID
        """
        if group_id not in self.group_connections:
            print(f"[DEBUG] 群组 {group_id} 没有活跃连接")
            return
        
        print(f"[DEBUG] 发送群组消息：group_id={group_id}, sender_id={sender_id}, sessions={self.group_connections[group_id]}")
        
        # 建立 session_id -> user_id 的映射
        session_to_user = {}
        for user_id, sessions in self.active_connections.items():
            for session_id_key in sessions:
                session_to_user[session_id_key] = user_id
        
        print(f"[DEBUG] session_to_user 映射: {session_to_user}")
        
        for session_id in self.group_connections[group_id]:
            if session_id in session_to_user:
                user_id = session_to_user[session_id]
                try:
                    await self.active_connections[user_id][session_id]["websocket"].send_json(message)
                    print(f"[DEBUG] 消息已发送给用户 {user_id}, session={session_id}")
                except Exception as e:
                    print(f"[DEBUG] 发送消息给用户 {user_id} 失败: {e}")
            else:
                print(f"[DEBUG] 未找到 session {session_id} 对应的用户")
    
    async def add_to_group(self, group_id: int, user_id: int, session_id: str):
        """
        将用户添加到群组连接
        
        功能说明：
        1. 检查群组连接列表是否存在
        2. 将会话 ID 添加到群组连接列表
        3. 用于后续群组消息广播
        
        Args:
            group_id: 群组ID
            user_id: 用户ID
            session_id: 会话ID
        """
        if group_id not in self.group_connections:
            self.group_connections[group_id] = []
        if session_id not in self.group_connections[group_id]:
            self.group_connections[group_id].append(session_id)
            print(f"[DEBUG] 用户 {user_id} 加入群组 {group_id}, session={session_id}")
        else:
            print(f"[DEBUG] 用户 {user_id} 已在群组 {group_id} 中")
    
    async def remove_from_group(self, group_id: int, session_id: str):
        """
        将用户从群组连接中移除
        
        Args:
            group_id: 群组ID
            session_id: 会话ID
        """
        if group_id in self.group_connections and session_id in self.group_connections[group_id]:
            self.group_connections[group_id].remove(session_id)
            if not self.group_connections[group_id]:
                del self.group_connections[group_id]
    
    async def get_online_users_count(self) -> int:
        """获取在线用户数量"""
        return len(self.active_connections)
    
    async def get_all_users_count(self) -> int:
        """获取总用户数"""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
            result = await cursor.fetchone()
            return result[0] if result else 0
    
    async def get_group_count(self) -> int:
        """获取群组数量"""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM groups")
            result = await cursor.fetchone()
            return result[0] if result else 0
    
    async def get_message_count(self) -> int:
        """获取消息总数"""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM messages")
            result = await cursor.fetchone()
            return result[0] if result else 0
    
    async def get_user_online_duration(self, user_id: int) -> int:
        """
        获取用户在线时长
        
        Args:
            user_id: 用户ID
            
        Returns:
            int: 在线时长（秒）
        """
        if user_id in self.active_connections:
            total_duration = 0
            for session_id, info in self.active_connections[user_id].items():
                duration = (datetime.now() - info["connected_at"]).total_seconds()
                total_duration += duration
            return int(total_duration)
        return 0
    
    async def get_user_sessions(self, user_id: int) -> List[dict]:
        """
        获取用户的所有会话
        
        Args:
            user_id: 用户ID
            
        Returns:
            List[dict]: 会话列表
        """
        if user_id in self.active_connections:
            return [
                {
                    "session_id": session_id,
                    "connected_at": info["connected_at"].isoformat(),
                    "last_activity": info["last_activity"].isoformat()
                }
                for session_id, info in self.active_connections[user_id].items()
            ]
        return []
    
    async def kick_user_session(self, user_id: int, session_id: str, reason: Optional[str] = None):
        """
        踢出指定会话
        
        Args:
            user_id: 用户ID
            session_id: 会话ID
            reason: 踢出原因
        """
        if user_id in self.active_connections and session_id in self.active_connections[user_id]:
            kick_message = {
                "type": "kick",
                "reason": reason or "You have been kicked"
            }
            await self.active_connections[user_id][session_id]["websocket"].send_json(kick_message)
            await self.disconnect(user_id, session_id)
    
    async def kick_user_all_sessions(self, user_id: int, reason: Optional[str] = None):
        """
        踢出用户的所有会话
        
        Args:
            user_id: 用户ID
            reason: 踢出原因
        """
        if user_id in self.active_connections:
            for session_id in list(self.active_connections[user_id].keys()):
                await self.kick_user_session(user_id, session_id, reason)

    async def get_user_statistics(self) -> dict:
        """
        获取用户统计信息
        
        Returns:
            dict: 统计信息字典
        """
        async with aiosqlite.connect(DATABASE_PATH) as db:
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
            if row:
                return {
                    "total_users": row[0] or 0,
                    "online_users": row[1] or 0,
                    "total_groups": row[2] or 0,
                    "total_messages": row[3] or 0
                }
            return {
                "total_users": 0,
                "online_users": 0,
                "total_groups": 0,
                "total_messages": 0
            }


# 全局连接管理器实例
connection_manager = ConnectionManager()
