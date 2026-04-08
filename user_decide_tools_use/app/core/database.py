"""
数据库模块 - 使用 SQLite 持久化存储用户和任务信息

本模块提供：
1. 数据库连接管理
2. 用户表操作（创建、查询、验证）
3. 任务表操作（创建、查询、更新、删除）
4. 数据库初始化和迁移

数据库表结构：
- users: 存储用户信息
- tasks: 存储任务信息
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, List, Any
from contextlib import contextmanager
import os

# 数据库文件路径
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "app.db")


class Database:
    """
    数据库管理类

    提供数据库连接池和常用操作方法
    使用上下文管理器确保连接正确关闭
    """

    def __init__(self, db_path: str = DATABASE_PATH):
        """
        初始化数据库管理器

        Args:
            db_path: 数据库文件路径，默认为当前目录下的 app.db
        """
        self.db_path = db_path
        self._init_database()

    @contextmanager
    def _get_connection(self):
        """
        获取数据库连接的上下文管理器

        使用示例：
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT * FROM users")
                results = cursor.fetchall()

        Yields:
            sqlite3.Connection: 数据库连接对象
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 使查询结果可以通过列名访问
        try:
            yield conn
            conn.commit()  # 自动提交事务
        except Exception as e:
            conn.rollback()  # 发生错误时回滚
            raise e
        finally:
            conn.close()

    def _init_database(self):
        """
        初始化数据库表结构

        创建必要的表（如果不存在）：
        - users: 用户表
        - tasks: 任务表
        """
        with self._get_connection() as conn:
            # 创建用户表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,           -- 用户唯一标识符（UUID）
                    username TEXT UNIQUE NOT NULL,      -- 用户名（唯一）
                    password_hash TEXT NOT NULL,        -- 密码哈希值（SHA256）
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 创建时间
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP   -- 更新时间
                )
            """)

            # 创建任务表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,           -- 任务唯一标识符（UUID）
                    user_id TEXT NOT NULL,              -- 所属用户ID（外键）
                    user_message TEXT NOT NULL,         -- 用户输入的消息/指令
                    status TEXT NOT NULL,               -- 任务状态：pending/running/waiting/completed/failed/cancelled
                    result TEXT,                        -- 任务执行结果（JSON字符串）
                    error TEXT,                         -- 错误信息（如果失败）
                    pending_interaction_id TEXT,        -- 当前等待确认的交互ID
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 创建时间
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 更新时间
                    completed_at TIMESTAMP,             -- 完成时间
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)

            # 创建索引以提高查询性能
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)
            """)

    # ==================== 用户相关操作 ====================

    def create_user(self, user_id: str, username: str, password_hash: str) -> bool:
        """
        创建新用户

        Args:
            user_id: 用户唯一标识符（UUID）
            username: 用户名
            password_hash: 密码的SHA256哈希值

        Returns:
            bool: 创建成功返回True，用户名已存在返回False

        Raises:
            sqlite3.IntegrityError: 当用户名已存在时抛出
        """
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO users (user_id, username, password_hash)
                    VALUES (?, ?, ?)
                    """,
                    (user_id, username, password_hash)
                )
            return True
        except sqlite3.IntegrityError:
            # 用户名已存在
            return False

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """
        通过用户名查询用户信息

        Args:
            username: 用户名

        Returns:
            Dict: 用户信息字典，包含 user_id, username, password_hash, created_at
            None: 用户不存在时返回None
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM users WHERE username = ?",
                (username,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        通过用户ID查询用户信息

        Args:
            user_id: 用户唯一标识符

        Returns:
            Dict: 用户信息字典
            None: 用户不存在时返回None
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM users WHERE user_id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    # ==================== 任务相关操作 ====================

    def create_task(
        self,
        task_id: str,
        user_id: str,
        user_message: str,
        status: str = "pending"
    ) -> bool:
        """
        创建新任务记录

        Args:
            task_id: 任务唯一标识符（UUID）
            user_id: 所属用户ID
            user_message: 用户输入的消息/指令
            status: 初始状态，默认为 "pending"

        Returns:
            bool: 创建成功返回True
        """
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO tasks (task_id, user_id, user_message, status)
                VALUES (?, ?, ?, ?)
                """,
                (task_id, user_id, user_message, status)
            )
        return True

    def get_task(self, task_id: str, user_id: str = None) -> Optional[Dict[str, Any]]:
        """
        查询任务信息

        Args:
            task_id: 任务唯一标识符
            user_id: 可选，如果提供则验证任务是否属于该用户

        Returns:
            Dict: 任务信息字典
            None: 任务不存在或无权限访问时返回None
        """
        with self._get_connection() as conn:
            if user_id:
                # 验证任务归属
                cursor = conn.execute(
                    "SELECT * FROM tasks WHERE task_id = ? AND user_id = ?",
                    (task_id, user_id)
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM tasks WHERE task_id = ?",
                    (task_id,)
                )
            row = cursor.fetchone()
            if row:
                task = dict(row)
                # 解析JSON结果
                if task.get("result"):
                    try:
                        task["result"] = json.loads(task["result"])
                    except json.JSONDecodeError:
                        pass
                return task
            return None

    def get_tasks_by_user(self, user_id: str = None) -> List[Dict[str, Any]]:
        """
        获取任务列表

        Args:
            user_id: 可选，如果提供则只返回该用户的任务

        Returns:
            List[Dict]: 任务列表，按创建时间倒序排列
        """
        with self._get_connection() as conn:
            if user_id:
                cursor = conn.execute(
                    """
                    SELECT task_id, status, created_at, updated_at, completed_at, pending_interaction_id
                    FROM tasks
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                    """,
                    (user_id,)
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT task_id, status, created_at, updated_at, completed_at, pending_interaction_id
                    FROM tasks
                    ORDER BY created_at DESC
                    """
                )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def update_task_status(
        self,
        task_id: str,
        status: str,
        result: Any = None,
        error: str = None,
        pending_interaction_id: str = None,
        completed_at: datetime = None
    ) -> bool:
        """
        更新任务状态

        Args:
            task_id: 任务唯一标识符
            status: 新状态
            result: 执行结果（会被序列化为JSON）
            error: 错误信息
            pending_interaction_id: 当前等待的交互ID
            completed_at: 完成时间

        Returns:
            bool: 更新成功返回True
        """
        with self._get_connection() as conn:
            # 构建动态更新语句
            fields = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
            params = [status]

            if result is not None:
                fields.append("result = ?")
                params.append(json.dumps(result) if not isinstance(result, str) else result)

            if error is not None:
                fields.append("error = ?")
                params.append(error)

            if pending_interaction_id is not None:
                fields.append("pending_interaction_id = ?")
                params.append(pending_interaction_id)

            if completed_at is not None:
                fields.append("completed_at = ?")
                params.append(completed_at.isoformat())

            params.append(task_id)

            query = f"UPDATE tasks SET {', '.join(fields)} WHERE task_id = ?"
            conn.execute(query, params)

        return True

    def delete_task(self, task_id: str, user_id: str = None) -> bool:
        """
        删除任务

        Args:
            task_id: 任务唯一标识符
            user_id: 可选，如果提供则验证任务是否属于该用户

        Returns:
            bool: 删除成功返回True，任务不存在或无权限返回False
        """
        with self._get_connection() as conn:
            if user_id:
                cursor = conn.execute(
                    "DELETE FROM tasks WHERE task_id = ? AND user_id = ?",
                    (task_id, user_id)
                )
            else:
                cursor = conn.execute(
                    "DELETE FROM tasks WHERE task_id = ?",
                    (task_id,)
                )
            return cursor.rowcount > 0

    def get_pending_interaction_task(
        self,
        task_id: str,
        user_id: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取包含待确认交互的任务信息

        Args:
            task_id: 任务唯一标识符
            user_id: 可选，如果提供则验证任务是否属于该用户

        Returns:
            Dict: 包含 pending_interaction_id 的任务信息
            None: 任务不存在、无权限或没有待确认交互时返回None
        """
        with self._get_connection() as conn:
            if user_id:
                cursor = conn.execute(
                    """
                    SELECT task_id, pending_interaction_id
                    FROM tasks
                    WHERE task_id = ? AND user_id = ? AND pending_interaction_id IS NOT NULL
                    """,
                    (task_id, user_id)
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT task_id, pending_interaction_id
                    FROM tasks
                    WHERE task_id = ? AND pending_interaction_id IS NOT NULL
                    """,
                    (task_id,)
                )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None


# 全局数据库实例
db = Database()
