import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, File, UploadFile, Query, WebSocket, WebSocketDisconnect
from dbgpt.component import SystemApp
from .schemas import (
    KGUploadTaskCreateRequest,
    KGUploadTaskResponse,
    KGUploadTaskListResponse,
    KGUploadFileResponse
)
from ..service.service import Service
from ..config import SERVE_SERVICE_COMPONENT_NAME, ServeConfig

router = APIRouter()
logger = logging.getLogger(__name__)

global_system_app: Optional[SystemApp] = None

def get_service() -> Service:
    """Get the service instance"""
    return global_system_app.get_component(SERVE_SERVICE_COMPONENT_NAME, Service)

# 全局 Service 实例初始化函数
def init_endpoints(system_app: SystemApp, config: ServeConfig):
    global global_system_app
    system_app.register(Service, config)
    global_system_app = system_app

@router.post("/upload", response_model=KGUploadTaskResponse)
async def upload_files(
    files: List[UploadFile] = File(...),
    graph_space_name: str = Query(..., description="Graph Space name"),
    excel_mode: str = Query("auto", description="Excel process mode"),
    custom_prompt: Optional[str] = Query(None, description="Custom prompt"),
    user_id: Optional[str] = Query(None, description="User ID"),
    service: Service = Depends(get_service),
):
    """批量上传文件并创建知识图谱构建任务"""
    request = KGUploadTaskCreateRequest(
        graph_space_name=graph_space_name,
        excel_mode=excel_mode,
        custom_prompt=custom_prompt,
        user_id=user_id
    )
    return await service.create_upload_task(request, files)

@router.get("/tasks/{task_id}", response_model=KGUploadTaskResponse)
async def get_task_detail(
    task_id: str,
    service: Service = Depends(get_service)
):
    """获取任务详情"""
    return service.get_task_detail(task_id)

@router.get("/tasks", response_model=KGUploadTaskListResponse)
async def list_tasks(
    user_id: str,
    page: int = 1,
    limit: int = 20,
    service: Service = Depends(get_service)
):
    """获取历史任务列表"""
    return service.list_tasks(user_id, page, limit)

@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    service: Service = Depends(get_service)
):
    """取消任务"""
    return await service.cancel_task(task_id)

@router.websocket("/ws/task/{task_id}")
async def task_progress_ws(
    websocket: WebSocket,
    task_id: str,
    service: Service = Depends(get_service)
):
    """WebSocket 进度推送"""
    await service.ws_manager.connect(task_id, websocket)
    try:
        while True:
            # 保持连接，接收客户端可能的控制消息
            data = await websocket.receive_text()
            logger.debug(f"Received from client {task_id}: {data}")
    except WebSocketDisconnect:
        await service.ws_manager.disconnect(task_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error for task {task_id}: {str(e)}")
        await service.ws_manager.disconnect(task_id, websocket)
