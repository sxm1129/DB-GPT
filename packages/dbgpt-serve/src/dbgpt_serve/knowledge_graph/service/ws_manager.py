import logging
from typing import Dict, List
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class WebSocketManager:
    """管理 WebSocket 连接和消息推送"""
    
    def __init__(self):
        # task_id -> list of websockets
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, task_id: str, websocket: WebSocket):
        await websocket.accept()
        if task_id not in self.active_connections:
            self.active_connections[task_id] = []
        self.active_connections[task_id].append(websocket)
        logger.info(f"WebSocket connected for task {task_id}")
    
    async def disconnect(self, task_id: str, websocket: WebSocket):
        if task_id in self.active_connections:
            if websocket in self.active_connections[task_id]:
                self.active_connections[task_id].remove(websocket)
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]
        logger.info(f"WebSocket disconnected for task {task_id}")
    
    async def broadcast(self, task_id: str, message: dict):
        """向订阅指定任务的所有客户端推送消息"""
        if task_id in self.active_connections:
            for ws in self.active_connections[task_id]:
                try:
                    await ws.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send message over WS for {task_id}: {str(e)}")
                    # 可以在这里处理自动清理
    
    async def send_progress(self, task_id: str, progress: float, **kwargs):
        """推送进度更新的具体封装"""
        await self.broadcast(task_id, {
            "type": "progress",
            "task_id": task_id,
            "data": {
                "progress": round(progress, 2),
                **kwargs
            }
        })

# 全局单例
ws_manager = WebSocketManager()
