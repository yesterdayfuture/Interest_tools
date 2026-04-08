"""
任务管理器模块

负责任务的创建、执行、状态管理和用户确认交互。
使用 asyncio.Future 实现任务的暂停和恢复机制。

主要功能：
1. 创建和管理异步任务
2. 处理用户确认交互（Human-in-the-Loop）
3. 任务状态持久化到数据库
4. 支持任务取消
"""

import asyncio
from typing import Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import uuid

# 导入数据库模块
from app.core.database import db


class TaskStatus(str, Enum):
    """
    任务状态枚举

    定义了任务生命周期的所有可能状态：
    - PENDING: 等待执行
    - RUNNING: 正在执行
    - WAITING: 等待用户确认
    - COMPLETED: 已完成
    - FAILED: 执行失败
    - CANCELLED: 已取消
    """
    PENDING = "pending"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PendingInteraction:
    """
    等待中的用户确认请求

    当任务需要用户确认某个操作时，创建此对象来暂停任务执行，
    直到用户做出响应。

    Attributes:
        interaction_id: 交互唯一标识符
        task_id: 关联的任务ID
        tool_name: 需要确认的工具名称
        tool_args: 工具参数
        prompt: 显示给用户的提示信息
        tool_description: 工具描述
        future: asyncio.Future 对象，用于暂停和恢复任务
        created_at: 交互创建时间
    """
    interaction_id: str
    task_id: str
    tool_name: str
    tool_args: Dict[str, Any]
    prompt: str
    tool_description: str
    future: asyncio.Future
    created_at: datetime = field(default_factory=datetime.now)


class TaskManager:
    """
    任务管理器

    负责任务的创建、执行、状态维护和用户交互。
    核心设计：使用 asyncio.Future 实现任务的暂停与恢复。

    属性:
        tasks: 内存中的任务状态缓存（Dict[task_id, task_data]）
        pending_interactions: 等待用户确认的交互请求
        _lock: 异步锁，确保并发安全
        _running_tasks: 正在运行的 asyncio.Task 对象
    """

    def __init__(self):
        """初始化任务管理器"""
        # 内存中的任务状态缓存（用于快速访问）
        self.tasks: Dict[str, Dict] = {}
        # 存储等待确认的交互请求
        self.pending_interactions: Dict[str, PendingInteraction] = {}
        # 任务锁，确保并发安全
        self._lock = asyncio.Lock()
        # 存储正在运行的任务对象（用于取消）
        self._running_tasks: Dict[str, asyncio.Task] = {}

    def create_task(
        self,
        task_id: str,
        user_message: str,
        agent_factory,
        user_id: str = None
    ) -> asyncio.Task:
        """
        创建并启动一个新任务

        流程：
        1. 在数据库中创建任务记录
        2. 在内存中缓存任务状态
        3. 创建异步任务开始执行

        Args:
            task_id: 任务唯一标识符（UUID）
            user_message: 用户输入的消息/指令
            agent_factory: Agent 工厂函数，用于创建任务执行器
            user_id: 所属用户ID（用于用户隔离）

        Returns:
            asyncio.Task: 创建的异步任务对象
        """
        # 在数据库中创建任务记录
        db.create_task(task_id, user_id, user_message, TaskStatus.PENDING)

        # 在内存中缓存任务状态（用于快速访问）
        self.tasks[task_id] = {
            "id": task_id,
            "user_id": user_id,
            "user_message": user_message,
            "status": TaskStatus.PENDING,
            "result": None,
            "error": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "pending_interaction_id": None,
            "completed_at": None,
        }

        # 创建异步任务
        loop = asyncio.get_running_loop()
        task = loop.create_task(self._run_agent_task(task_id, user_message, agent_factory))
        self._running_tasks[task_id] = task

        # 添加完成回调
        task.add_done_callback(lambda t: self._on_task_complete(task_id, t))

        return task

    def _on_task_complete(self, task_id: str, task: asyncio.Task):
        """任务完成时的回调"""
        # 从运行中任务列表移除
        self._running_tasks.pop(task_id, None)

        # 获取任务结果
        try:
            result = task.result()
            asyncio.create_task(self._update_task_status(
                task_id, TaskStatus.COMPLETED,
                result=result, completed_at=datetime.now()
            ))
        except asyncio.CancelledError:
            asyncio.create_task(self._update_task_status(
                task_id, TaskStatus.CANCELLED,
                error="任务被取消", completed_at=datetime.now()
            ))
        except Exception as e:
            asyncio.create_task(self._update_task_status(
                task_id, TaskStatus.FAILED,
                error=str(e), completed_at=datetime.now()
            ))

    async def _run_agent_task(self, task_id: str, user_message: str, agent_factory):
        """
        核心 Agent 执行逻辑
        这是每个任务独立运行的工作流
        """
        try:
            # 更新状态为运行中
            await self._update_task_status(task_id, TaskStatus.RUNNING)

            # 创建 Agent 实例（每个任务独立的 Agent）
            agent = agent_factory()

            # 执行 Agent 工作流
            result = await agent.run_with_tools(user_message, self, task_id)

            return result

        except asyncio.CancelledError:
            raise
        except Exception as e:
            raise

    async def cancel_task(self, task_id: str) -> bool:
        """取消正在运行的任务"""
        task = self._running_tasks.get(task_id)
        if task and not task.done():
            task.cancel()
            return True
        return False

    def _requires_confirmation(self, tool_name: str) -> bool:
        """判断工具是否需要用户确认"""
        sensitive_tools = {
            "create_file", "modify_file", "delete_file",
            "run_command", "execute_shell", "install_package",
            "move_file", "copy_file", "rename_file"
        }
        return tool_name in sensitive_tools

    async def _wait_for_confirmation(
            self,
            task_id: str,
            tool_name: str,
            tool_args: Dict[str, Any],
            tool_description: str = ""
    ) -> Dict[str, Any]:
        """
        等待用户确认
        核心机制：创建一个 Future，存储到 pending_interactions，然后 await
        """
        interaction_id = str(uuid.uuid4())
        future = asyncio.get_running_loop().create_future()

        # 构建提示信息
        prompt = self._build_confirmation_prompt(tool_name, tool_args)

        interaction = PendingInteraction(
            interaction_id=interaction_id,
            task_id=task_id,
            tool_name=tool_name,
            tool_args=tool_args,
            prompt=prompt,
            tool_description=tool_description,
            future=future
        )

        # 先获取锁注册交互
        async with self._lock:
            self.pending_interactions[interaction_id] = interaction

        # 然后更新任务状态（单独获取锁，避免死锁）
        await self._update_task_status(task_id, TaskStatus.WAITING,
                                       pending_interaction_id=interaction_id)

        try:
            # 关键：await future 会挂起当前协程，直到 future.set_result() 被调用
            # 在此期间，事件循环可以执行其他任务
            result = await future
            return {"approved": result, "user_input": None}
        finally:
            async with self._lock:
                self.pending_interactions.pop(interaction_id, None)
                # 清除任务的 pending_interaction_id
                if task_id in self.tasks:
                    self.tasks[task_id]["pending_interaction_id"] = None

    def _build_confirmation_prompt(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """构建确认提示信息"""
        prompts = {
            "create_file": f"创建文件 '{tool_args.get('filename', 'unknown')}'",
            "modify_file": f"修改文件 '{tool_args.get('filename', 'unknown')}'",
            "delete_file": f"删除文件 '{tool_args.get('filename', 'unknown')}'",
            "run_command": f"执行命令: {tool_args.get('command', 'unknown')}",
            "execute_shell": f"执行 Shell 命令: {tool_args.get('command', 'unknown')}",
            "move_file": f"移动文件 '{tool_args.get('source', 'unknown')}' 到 '{tool_args.get('destination', 'unknown')}'",
            "copy_file": f"复制文件 '{tool_args.get('source', 'unknown')}' 到 '{tool_args.get('destination', 'unknown')}'",
            "rename_file": f"重命名文件 '{tool_args.get('old_name', 'unknown')}' 为 '{tool_args.get('new_name', 'unknown')}'",
        }
        return prompts.get(tool_name, f"执行操作: {tool_name}")

    async def confirm_interaction(self, interaction_id: str, approved: bool, user_input: Optional[str] = None) -> bool:
        """
        确认一个等待中的交互
        通过设置 future 的结果来唤醒等待的任务
        """
        # 先获取锁查找交互
        async with self._lock:
            interaction = self.pending_interactions.get(interaction_id)
            if not interaction:
                return False

        # 设置 future 的结果，这会唤醒正在 await 的协程
        # 注意：这里不需要锁，因为 future 是线程安全的
        interaction.future.set_result(approved)

        # 然后更新任务状态（单独获取锁，避免死锁）
        await self._update_task_status(interaction.task_id, TaskStatus.RUNNING)

        return True

    async def get_pending_interaction(self, interaction_id: str) -> Optional[PendingInteraction]:
        """获取等待中的交互信息"""
        async with self._lock:
            return self.pending_interactions.get(interaction_id)

    async def list_tasks(self, user_id: str = None) -> list:
        """列出所有任务，如果指定user_id则只返回该用户的任务"""
        async with self._lock:
            # 从数据库查询任务列表
            tasks = db.get_tasks_by_user(user_id)
            return [
                {
                    "id": task["task_id"],
                    "status": task["status"],
                    "created_at": task.get("created_at"),
                    "updated_at": task.get("updated_at"),
                    "completed_at": task.get("completed_at"),
                    "pending_interaction_id": task.get("pending_interaction_id"),
                }
                for task in tasks
            ]

    async def get_task_status(self, task_id: str, user_id: str = None) -> Optional[Dict]:
        """
        获取任务状态

        优先从内存缓存获取，如果不在缓存中则从数据库查询。
        如果指定 user_id，会验证任务是否属于该用户。

        Args:
            task_id: 任务唯一标识符
            user_id: 可选，用于验证任务归属

        Returns:
            Dict: 任务状态信息
            None: 任务不存在或无权限访问
        """
        # 首先尝试从内存缓存获取
        async with self._lock:
            task = self.tasks.get(task_id)
            if task:
                # 验证用户权限
                if user_id is not None and task.get("user_id") != user_id:
                    return None
                return {
                    "id": task["id"],
                    "status": task["status"],
                    "result": task.get("result"),
                    "error": task.get("error"),
                    "created_at": task.get("created_at"),
                    "updated_at": task.get("updated_at"),
                    "completed_at": task.get("completed_at"),
                    "pending_interaction_id": task.get("pending_interaction_id"),
                    "user_message": task.get("user_message"),
                }

        # 如果不在内存中，从数据库查询
        task = db.get_task(task_id, user_id)
        if task:
            # 转换字段名以保持一致性
            return {
                "id": task["task_id"],
                "status": task["status"],
                "result": task.get("result"),
                "error": task.get("error"),
                "created_at": task.get("created_at"),
                "updated_at": task.get("updated_at"),
                "completed_at": task.get("completed_at"),
                "pending_interaction_id": task.get("pending_interaction_id"),
                "user_message": task.get("user_message"),
            }
        return None

    async def get_task_pending_interaction(self, task_id: str, user_id: str = None) -> Optional[PendingInteraction]:
        """
        获取指定任务的等待中交互

        首先验证任务归属（如果指定 user_id），然后返回对应的 PendingInteraction 对象。

        Args:
            task_id: 任务唯一标识符
            user_id: 可选，用于验证任务归属

        Returns:
            PendingInteraction: 等待中的交互对象
            None: 任务不存在、无权限或没有待确认交互
        """
        # 从数据库验证任务归属
        task_data = db.get_pending_interaction_task(task_id, user_id)
        if not task_data:
            return None

        pending_id = task_data.get("pending_interaction_id")
        if not pending_id:
            return None

        # 从内存中获取交互对象
        async with self._lock:
            return self.pending_interactions.get(pending_id)

    async def _update_task_status(self, task_id: str, status: TaskStatus, **kwargs):
        """
        更新任务状态

        同时更新内存缓存和数据库中的任务状态，确保数据一致性。

        Args:
            task_id: 任务唯一标识符
            status: 新的任务状态
            **kwargs: 其他要更新的字段（result, error, pending_interaction_id, completed_at）
        """
        async with self._lock:
            # 更新内存缓存
            if task_id in self.tasks:
                self.tasks[task_id]["status"] = status
                self.tasks[task_id]["updated_at"] = datetime.now()
                for key, value in kwargs.items():
                    self.tasks[task_id][key] = value

            # 更新数据库
            # 提取数据库支持的字段
            db_kwargs = {}
            if "result" in kwargs:
                db_kwargs["result"] = kwargs["result"]
            if "error" in kwargs:
                db_kwargs["error"] = kwargs["error"]
            if "pending_interaction_id" in kwargs:
                db_kwargs["pending_interaction_id"] = kwargs["pending_interaction_id"]
            if "completed_at" in kwargs:
                db_kwargs["completed_at"] = kwargs["completed_at"]

            db.update_task_status(task_id, status, **db_kwargs)
