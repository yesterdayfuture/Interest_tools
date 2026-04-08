"""
任务管理路由

提供任务创建、查询、确认等任务相关接口。
"""

import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Depends

from app.models.schemas import (
    StartTaskRequest, TaskResponse,
    ConfirmInteractionRequest, ConfirmInteractionResponse,
    PendingInteractionResponse
)
from app.models.user import User
from app.routers.auth import require_user
from app.services.task_manager import TaskManager, TaskStatus
from app.services.service import OpenAIAgent
from app.core.config import settings

# 创建路由
router = APIRouter(prefix="/task", tags=["任务"])

# 任务列表路由（使用 /api 前缀）
list_router = APIRouter(tags=["任务"])

# 全局任务管理器
task_manager = TaskManager()

# WebSocket 连接管理器
class ConnectionManager:
    """管理 WebSocket 连接"""

    def __init__(self):
        # task_id -> list of websockets
        self.active_connections: dict = {}
        # interaction_id -> websocket (用于确认通知)
        self.interaction_listeners: dict = {}

    async def connect(self, task_id: str, websocket: WebSocket):
        """建立 WebSocket 连接"""
        await websocket.accept()
        if task_id not in self.active_connections:
            self.active_connections[task_id] = []
        self.active_connections[task_id].append(websocket)

    def disconnect(self, task_id: str, websocket: WebSocket):
        """断开 WebSocket 连接"""
        if task_id in self.active_connections:
            if websocket in self.active_connections[task_id]:
                self.active_connections[task_id].remove(websocket)
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]

    async def send_message(self, task_id: str, message: dict):
        """发送消息到指定任务的所有连接"""
        if task_id in self.active_connections:
            for ws in self.active_connections[task_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    pass


# 全局连接管理器实例
manager = ConnectionManager()


@router.post("/start", response_model=TaskResponse)
async def start_task(
    request: StartTaskRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_user)
):
    """
    启动新任务

    创建一个新的 AI Agent 任务，异步执行用户请求
    """
    task_id = str(uuid.uuid4())

    # 创建 Agent 工厂函数
    def agent_factory(task_id: str = None, task_manager_ref = None):
        return OpenAIAgent(
            model_name=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )

    # 创建并启动任务
    task_manager.create_task(
        task_id=task_id,
        user_message=request.user_message,
        agent_factory=agent_factory,
        user_id=current_user.user_id
    )

    return TaskResponse(
        task_id=task_id,
        status="pending",
        message="任务已启动"
    )


@router.post("/confirm", response_model=ConfirmInteractionResponse)
async def confirm_interaction(
    request: ConfirmInteractionRequest,
    current_user: User = Depends(require_user)
):
    """
    确认或拒绝工具调用请求

    用户对 AI 的工具调用请求做出响应
    """
    success = await task_manager.confirm_interaction(
        request.interaction_id,
        request.approved,
        request.user_input
    )

    if success:
        return ConfirmInteractionResponse(
            success=True,
            message="已同意执行" if request.approved else "已拒绝执行"
        )

    raise HTTPException(status_code=404, detail="交互请求不存在或已过期")


@router.get("/{task_id}/pending", response_model=PendingInteractionResponse)
async def get_pending_interaction(
    task_id: str,
    current_user: User = Depends(require_user)
):
    """
    获取任务的待确认交互信息

    用于前端展示确认对话框的内容
    """
    interaction = await task_manager.get_task_pending_interaction(task_id, current_user.user_id)
    if not interaction:
        return PendingInteractionResponse(has_pending=False)

    return PendingInteractionResponse(
        has_pending=True,
        interaction_id=interaction.interaction_id,
        tool_name=interaction.tool_name,
        tool_args=interaction.tool_args,
        prompt=interaction.prompt,
        task_id=interaction.task_id
    )


# WebSocket 路由（不使用 /api 前缀，直接挂载到根路径）
ws_router = APIRouter(tags=["WebSocket"])


@ws_router.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """
    WebSocket 实时通知接口

    用于向前端推送任务状态更新和确认请求
    """
    await manager.connect(task_id, websocket)
    try:
        while True:
            # 保持连接，接收心跳
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(task_id, websocket)


@list_router.get("/tasks")
async def list_tasks(current_user: User = Depends(require_user)):
    """列出当前用户的所有任务"""
    tasks = await task_manager.list_tasks(current_user.user_id)
    return {"tasks": tasks}


@list_router.delete("/task/{task_id}")
async def cancel_task(task_id: str, current_user: User = Depends(require_user)):
    """取消正在运行的任务"""
    # 验证任务是否属于当前用户
    status = await task_manager.get_task_status(task_id, current_user.user_id)
    if not status:
        raise HTTPException(status_code=404, detail="任务不存在或无权限访问")

    success = await task_manager.cancel_task(task_id)

    if success:
        await manager.send_message(task_id, {
            "type": "task_cancelled",
            "data": {"task_id": task_id}
        })
        return {"success": True, "message": "任务已取消"}

    return {"success": False, "message": "任务无法取消（已完成或不存在）"}
