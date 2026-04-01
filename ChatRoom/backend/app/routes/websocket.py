"""
WebSocket 路由模块
处理实时消息通信
"""
import json
import uuid
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException

from app.core.auth import get_current_active_user
from app.core.connection_manager import connection_manager
from app.services.message_service import create_message
from app.services.group_service import is_group_member

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """
    WebSocket 连接端点
    
    - **token**: JWT Token
    
    连接成功后可以通过 WebSocket 发送和接收实时消息
    
    消息格式：
    - 私聊消息: `{"type": "personal", "receiver_id": 123, "content": "消息内容"}`
    - 群聊消息: `{"type": "group", "group_id": 456, "content": "消息内容"}`
    - 心跳消息: `{"type": "ping"}`
    - 加入群组: `{"type": "join_group", "group_id": 456}`
    - 离开群组: `{"type": "leave_group", "group_id": 456}`
    """
    user = await get_current_active_user(token)
    if not user:
        await websocket.close(code=4001, reason="Invalid token")
        return
    
    session_id = str(uuid.uuid4())
    await connection_manager.connect(websocket, user["id"], session_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            message_type = message_data.get("type")
            
            await connection_manager.update_last_activity(user["id"], session_id)
            
            if message_type == "personal":
                await handle_personal_message(websocket, user, message_data, session_id)
            
            elif message_type == "group":
                await handle_group_message(websocket, user, message_data, session_id)
            
            elif message_type == "ping":
                await websocket.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})
            
            elif message_type == "join_group":
                await handle_join_group(websocket, user, message_data, session_id)
            
            elif message_type == "leave_group":
                await handle_leave_group(websocket, user, message_data, session_id)
    
    except WebSocketDisconnect:
        await connection_manager.disconnect(user["id"], session_id)
    except Exception as e:
        await connection_manager.disconnect(user["id"], session_id)


async def handle_personal_message(websocket, user, message_data, session_id):
    """处理私聊消息"""
    receiver_id = message_data.get("receiver_id")
    content = message_data.get("content")
    
    if not receiver_id or not content:
        await websocket.send_json({"type": "error", "message": "Invalid message"})
        return
    
    message_id = await create_message(user["id"], receiver_id=receiver_id, content=content)
    
    message = {
        "type": "personal_message",
        "id": message_id,
        "sender_id": user["id"],
        "receiver_id": receiver_id,
        "content": content,
        "created_at": datetime.now().isoformat()
    }
    
    await connection_manager.send_personal_message(message, receiver_id)
    await connection_manager.send_personal_message({
        **message,
        "sent": True
    }, user["id"], session_id)


async def handle_group_message(websocket, user, message_data, session_id):
    """处理群聊消息"""
    group_id = message_data.get("group_id")
    content = message_data.get("content")
    
    print(f"[DEBUG] 收到群聊消息：group_id={group_id}, sender_id={user['id']}, content={content}")
    
    if not group_id or not content:
        await websocket.send_json({"type": "error", "message": "Invalid message"})
        return
    
    if not await is_group_member(group_id, user["id"]):
        print(f"[DEBUG] 用户 {user['id']} 不是群组成员")
        await websocket.send_json({"type": "error", "message": "Not a member of this group"})
        return
    
    # 确保用户已加入群组的 WebSocket 连接
    await connection_manager.add_to_group(group_id, user["id"], session_id)
    
    message_id = await create_message(user["id"], group_id=group_id, content=content)
    print(f"[DEBUG] 消息已保存：message_id={message_id}")
    
    message = {
        "type": "group_message",
        "id": message_id,
        "sender_id": user["id"],
        "group_id": group_id,
        "content": content,
        "created_at": datetime.now().isoformat()
    }
    
    print(f"[DEBUG] 广播群聊消息：{message}")
    await connection_manager.send_group_message(message, group_id, user["id"])


async def handle_join_group(websocket, user, message_data, session_id):
    """处理加入群组"""
    group_id = message_data.get("group_id")
    if group_id:
        if not await is_group_member(group_id, user["id"]):
            await websocket.send_json({"type": "error", "message": "Not a member of this group"})
            return
        await connection_manager.add_to_group(group_id, user["id"], session_id)
        await websocket.send_json({
            "type": "joined_group",
            "group_id": group_id
        })


async def handle_leave_group(websocket, user, message_data, session_id):
    """处理离开群组"""
    group_id = message_data.get("group_id")
    if group_id:
        await connection_manager.remove_from_group(group_id, session_id)
        await websocket.send_json({
            "type": "left_group",
            "group_id": group_id
        })
