"""
群组服务层
处理群组相关的数据库操作

主要功能：
- 创建、查询、删除群组
- 管理群组成员（添加、删除、查询）
- 发送和处理群组邀请
- 群组权限验证
"""
from datetime import datetime
import aiosqlite
from typing import Optional, List
import os

# 数据库路径
DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chatroom.db")


async def create_group(name: str, creator_id: int, description: Optional[str] = None) -> int:
    """
    创建新群组
    
    功能说明：
    1. 在 groups 表中创建群组记录
    2. 自动将创建者添加为群组成员，角色为 'creator'
    
    Args:
        name: 群组名称
        creator_id: 创建者 ID
        description: 群组描述（可选）
        
    Returns:
        int: 新建群组的 ID
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO groups (name, description, creator_id)
            VALUES (?, ?, ?)
            """,
            (name, description, creator_id)
        )
        await db.commit()
        group_id = cursor.lastrowid
        
        # 创建者自动成为群组成员，角色为 creator
        await db.execute(
            """
            INSERT INTO group_members (group_id, user_id, role)
            VALUES (?, ?, 'creator')
            """,
            (group_id, creator_id)
        )
        await db.commit()
        return group_id


async def get_group(group_id: int) -> Optional[dict]:
    """
    根据ID获取群组信息
    
    Args:
        group_id: 群组ID
        
    Returns:
        Optional[dict]: 群组信息字典或 None
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM groups WHERE id = ?",
            (group_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_user_groups(user_id: int) -> List[dict]:
    """
    获取用户所属的所有群组
    
    Args:
        user_id: 用户ID
        
    Returns:
        List[dict]: 群组列表，包含成员数量
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # 不使用 row_factory，手动构建字典
        cursor = await db.execute(
            """
            SELECT g.id, g.name, g.description, g.creator_id, g.created_at,
                   (SELECT COUNT(*) FROM group_members gm2 WHERE gm2.group_id = g.id) as member_count
            FROM groups g
            JOIN group_members gm ON g.id = gm.group_id
            WHERE gm.user_id = ?
            """,
            (user_id,)
        )
        # 获取列名
        columns = [description[0] for description in cursor.description]
        rows = await cursor.fetchall()
        
        result = []
        for row in rows:
            # 手动构建字典，确保所有字段都包含
            row_dict = {}
            for i, col in enumerate(columns):
                row_dict[col] = row[i]
            # 确保 member_count 是整数
            row_dict['member_count'] = row_dict.get('member_count', 0) or 0
            result.append(row_dict)
        
        print(f"[DEBUG] get_user_groups: user_id={user_id}, result={result}")
        return result


async def get_group_members(group_id: int) -> List[dict]:
    """
    获取群组成员列表
    
    Args:
        group_id: 群组ID
        
    Returns:
        List[dict]: 成员列表
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
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


async def add_member_to_group(group_id: int, user_id: int, inviter_id: int) -> bool:
    """
    添加成员到群组
    
    Args:
        group_id: 群组ID
        user_id: 用户ID
        inviter_id: 邀请者ID
        
    Returns:
        bool: 是否添加成功
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            cursor = await db.execute(
                """
                INSERT INTO group_members (group_id, user_id, role)
                VALUES (?, ?, 'member')
                """,
                (group_id, user_id)
            )
            await db.commit()
            return cursor.rowcount > 0
        except aiosqlite.IntegrityError:
            return False


async def remove_member_from_group(group_id: int, user_id: int, remover_id: int) -> bool:
    """
    从群组中移除成员
    
    Args:
        group_id: 群组ID
        user_id: 用户ID
        remover_id: 移除者ID
        
    Returns:
        bool: 是否移除成功
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """
            DELETE FROM group_members 
            WHERE group_id = ? AND user_id = ?
            """,
            (group_id, user_id)
        )
        await db.commit()
        return cursor.rowcount > 0


async def update_member_role(group_id: int, user_id: int, role: str, updater_id: int) -> bool:
    """
    更新成员角色
    
    Args:
        group_id: 群组ID
        user_id: 用户ID
        role: 新角色
        updater_id: 更新者ID
        
    Returns:
        bool: 是否更新成功
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """
            UPDATE group_members 
            SET role = ? 
            WHERE group_id = ? AND user_id = ?
            """,
            (role, group_id, user_id)
        )
        await db.commit()
        return cursor.rowcount > 0


async def is_group_member(group_id: int, user_id: int) -> bool:
    """
    检查用户是否是群组成员
    
    Args:
        group_id: 群组ID
        user_id: 用户ID
        
    Returns:
        bool: 是否是成员
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM group_members WHERE group_id = ? AND user_id = ?",
            (group_id, user_id)
        )
        result = await cursor.fetchone()
        return result[0] > 0


async def is_group_creator(group_id: int, user_id: int) -> bool:
    """
    检查用户是否是群组创建者
    
    Args:
        group_id: 群组ID
        user_id: 用户ID
        
    Returns:
        bool: 是否是创建者
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM groups WHERE id = ? AND creator_id = ?",
            (group_id, user_id)
        )
        result = await cursor.fetchone()
        return result[0] > 0


async def delete_group(group_id: int, user_id: int) -> bool:
    """
    删除群组（仅创建者可删除）
    
    Args:
        group_id: 群组ID
        user_id: 用户ID
        
    Returns:
        bool: 是否删除成功
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM groups WHERE id = ? AND creator_id = ?",
            (group_id, user_id)
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_group_stats(group_id: int) -> dict:
    """
    获取群组统计信息
    
    Args:
        group_id: 群组ID
        
    Returns:
        dict: 统计信息字典
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT 
                (SELECT COUNT(*) FROM group_members WHERE group_id = ?) as member_count,
                (SELECT COUNT(*) FROM messages WHERE group_id = ?) as message_count
            """,
            (group_id, group_id)
        )
        row = await cursor.fetchone()
        return dict(row) if row else {"member_count": 0, "message_count": 0}


async def get_user_online_in_groups(user_id: int) -> List[dict]:
    """
    获取用户加入的所有群组
    
    Args:
        user_id: 用户ID
        
    Returns:
        List[dict]: 群组列表
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT DISTINCT g.id, g.name
            FROM groups g
            JOIN group_members gm ON g.id = gm.group_id
            WHERE gm.user_id = ?
            """,
            (user_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


# ==================== 群组邀请相关功能 ====================

async def send_group_invitation(group_id: int, from_user_id: int, to_user_id: int, message: Optional[str] = None) -> bool:
    """
    发送群组邀请
    
    功能说明：
    1. 在 group_invitations 表中创建邀请记录
    2. 状态默认为 'pending'（待处理）
    3. 如果已存在未处理的邀请，则返回失败（数据库唯一约束）
    4. 通过 WebSocket 向被邀请者发送实时通知
    
    Args:
        group_id: 群组 ID
        from_user_id: 邀请者 ID
        to_user_id: 被邀请者 ID
        message: 邀请消息（可选）
        
    Returns:
        bool: 是否发送成功（True 成功，False 失败）
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            # 创建邀请记录
            cursor = await db.execute(
                """
                INSERT INTO group_invitations (group_id, from_user_id, to_user_id, message)
                VALUES (?, ?, ?, ?)
                """,
                (group_id, from_user_id, to_user_id, message)
            )
            await db.commit()
            
            if cursor.rowcount > 0:
                invitation_id = cursor.lastrowid
                
                # 调试日志
                print(f"[DEBUG] 邀请创建成功：id={invitation_id}, group_id={group_id}, from={from_user_id}, to={to_user_id}")
                
                # 获取邀请者信息
                from app.services.user_service import get_user
                from_user = await get_user(from_user_id)
                
                # 获取群组信息
                group = await get_group(group_id)
                
                # 通过 WebSocket 通知被邀请者
                from app.core.connection_manager import connection_manager
                from datetime import datetime
                notification = {
                    "type": "group_invitation",
                    "invitation_id": invitation_id,
                    "group_id": group_id,
                    "group_name": group["name"] if group else "Unknown",
                    "from_user_id": from_user_id,
                    "from_username": from_user["username"] if from_user else "Unknown",
                    "from_nickname": from_user["nickname"] if from_user else None,
                    "message": message,
                    "created_at": datetime.now().isoformat()
                }
                
                # 发送 WebSocket 通知给被邀请者
                print(f"[DEBUG] 发送 WebSocket 通知给被邀请者：to_user_id={to_user_id}")
                await connection_manager.send_personal_message(notification, to_user_id)
                
                return True
            return False
        except aiosqlite.IntegrityError as e:
            # 已存在未处理的邀请
            print(f"[DEBUG] 邀请创建失败（唯一约束）：group_id={group_id}, from={from_user_id}, to={to_user_id}, error={e}")
            return False
        except Exception as e:
            print(f"[DEBUG] 邀请创建失败（未知错误）：error={e}")
            return False


async def respond_group_invitation(invitation_id: int, to_user_id: int, accept: bool) -> bool:
    """
    响应群组邀请
    
    功能说明：
    1. 验证邀请是否存在且属于当前用户
    2. 检查邀请状态是否为 'pending'（待处理）
    3. 如果接受邀请：
       - 将用户添加到 group_members 表，角色为 'member'
       - 更新邀请状态为 'accepted'
    4. 如果拒绝邀请：
       - 更新邀请状态为 'rejected'
    
    Args:
        invitation_id: 邀请 ID
        to_user_id: 响应者 ID（被邀请人）
        accept: 是否接受（True 接受，False 拒绝）
        
    Returns:
        bool: 是否响应成功（True 成功，False 失败）
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT group_id, from_user_id, status 
            FROM group_invitations 
            WHERE id = ? AND to_user_id = ?
            """,
            (invitation_id, to_user_id)
        )
        row = await cursor.fetchone()
        if not row:
            # 邀请不存在或不属于当前用户
            return False
        
        row_dict = dict(row)
        if row_dict['status'] != 'pending':
            # 邀请已处理过，不能重复响应
            return False
        
        group_id = row_dict['group_id']
        
        if accept:
            # 接受邀请：添加用户到群组
            await db.execute(
                """
                INSERT INTO group_members (group_id, user_id, role)
                VALUES (?, ?, 'member')
                """,
                (group_id, to_user_id)
            )
        
        # 更新邀请状态
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


async def get_group_invitations(user_id: int, status: Optional[str] = None) -> List[dict]:
    """
    获取群组邀请列表
    
    功能说明：
    1. 查询发往指定用户的所有群组邀请
    2. 可选按状态筛选（pending/accepted/rejected）
    3. 返回邀请详情，包括群组信息和邀请者信息
    
    Args:
        user_id: 用户 ID（被邀请人）
        status: 状态筛选（可选）
               - 'pending': 待处理
               - 'accepted': 已接受
               - 'rejected': 已拒绝
               - None: 所有状态
        
    Returns:
        List[dict]: 邀请列表，包含：
                   - 邀请基本信息（ID、群组 ID、邀请者 ID、状态等）
                   - 群组信息（名称、描述）
                   - 邀请者信息（用户名、昵称）
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        if status:
            # 按状态筛选
            cursor = await db.execute(
                """
                SELECT gi.*, g.name as group_name, g.description, u.username, u.nickname 
                FROM group_invitations gi
                JOIN groups g ON gi.group_id = g.id
                JOIN users u ON gi.from_user_id = u.id
                WHERE gi.to_user_id = ? AND gi.status = ?
                ORDER BY gi.created_at DESC
                """,
                (user_id, status)
            )
        else:
            # 不过滤状态，返回所有邀请
            cursor = await db.execute(
                """
                SELECT gi.*, g.name as group_name, g.description, u.username, u.nickname 
                FROM group_invitations gi
                JOIN groups g ON gi.group_id = g.id
                JOIN users u ON gi.from_user_id = u.id
                WHERE gi.to_user_id = ?
                ORDER BY gi.created_at DESC
                """,
                (user_id,)
            )
        rows = await cursor.fetchall()
        result = [dict(row) for row in rows]
        print(f"[DEBUG] 查询邀请列表：user_id={user_id}, status={status}, count={len(result)}")
        return result


async def get_user_pending_invitations_count(user_id: int) -> int:
    """
    获取用户待处理的邀请数量
    
    功能说明：
    统计状态为 'pending' 的群组邀请数量
    
    Args:
        user_id: 用户 ID
        
    Returns:
        int: 待处理邀请数量
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT COUNT(*) as count 
            FROM group_invitations 
            WHERE to_user_id = ? AND status = 'pending'
            """,
            (user_id,)
        )
        row = await cursor.fetchone()
        return dict(row)['count'] if row else 0
