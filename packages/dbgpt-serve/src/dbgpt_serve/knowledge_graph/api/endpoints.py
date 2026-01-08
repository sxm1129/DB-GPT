import logging
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, File, UploadFile, Query, Form, WebSocket, WebSocketDisconnect
from dbgpt.component import SystemApp
from .schemas import (
    KGUploadTaskCreateRequest,
    KGUploadTaskResponse,
    KGUploadTaskListResponse,
    KGUploadFileResponse,
    ExcelColumnMapping
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
    graph_space_name: str = Form(..., description="Graph Space name"),
    excel_mode: str = Form("auto", description="Excel process mode"),
    column_mapping: Optional[str] = Form(None, description="Excel column mapping config (JSON string)"),
    custom_prompt: Optional[str] = Form(None, description="Custom prompt"),
    user_id: Optional[str] = Form(None, description="User ID"),
    service: Service = Depends(get_service),
):
    """批量上传文件并创建知识图谱构建任务"""
    mapping_obj = None
    if column_mapping:
        try:
            mapping_dict = json.loads(column_mapping)
            mapping_obj = ExcelColumnMapping(**mapping_dict)
        except Exception as e:
            logger.error(f"Failed to parse column_mapping: {str(e)}")
            
    request = KGUploadTaskCreateRequest(
        graph_space_name=graph_space_name,
        excel_mode=excel_mode,
        column_mapping=mapping_obj,
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
    user_id: Optional[str] = Query(None, description="User ID"),
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = Query(None, description="Task status filter"),
    service: Service = Depends(get_service)
):
    """获取历史任务列表"""
    return service.list_tasks(user_id, page, limit, status)

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

@router.get("/spaces")
async def list_graph_spaces(
    service: Service = Depends(get_service)
):
    """获取可用的图空间列表"""
    return await service.list_graph_spaces()

@router.post("/spaces")
async def create_graph_space(
    space_name: str = Query(..., description="New graph space name"),
    service: Service = Depends(get_service)
):
    """创建新的图空间"""
    return await service.create_graph_space(space_name)

@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: str,
    service: Service = Depends(get_service)
):
    """删除任务"""
    return await service.delete_task(task_id)


# ============ Prompt Template APIs ============

from .schemas import (
    KGPromptTemplateCreateRequest,
    KGPromptTemplateResponse,
    KGPromptTemplateListResponse,
    TemplateVariableVO
)
from ..models.models import KGPromptTemplateDao, KGPromptTemplateEntity

# 模板 DAO 实例
template_dao = KGPromptTemplateDao()


@router.get("/templates", response_model=KGPromptTemplateListResponse)
async def list_templates(
    user_id: Optional[str] = Query(None, description="用户ID，获取该用户的自定义模板"),
    include_system: bool = Query(True, description="是否包含系统预置模板"),
):
    """获取提示词模板列表"""
    # 首次调用时初始化系统模板
    template_dao.init_system_templates()
    
    templates = template_dao.list_templates(user_id=user_id, include_system=include_system)
    
    response_templates = []
    for t in templates:
        variables = []
        if t.variables:
            for v in t.variables:
                variables.append(TemplateVariableVO(
                    name=v.get("name", ""),
                    type=v.get("type", "text"),
                    options=v.get("options"),
                    default=v.get("default"),
                    description=v.get("description")
                ))
        
        response_templates.append(KGPromptTemplateResponse(
            id=t.id,
            name=t.name,
            description=t.description,
            prompt_content=t.prompt_content,
            variables=variables,
            is_system=bool(t.is_system),
            user_id=t.user_id,
            gmt_created=t.gmt_created.strftime("%Y-%m-%d %H:%M:%S") if t.gmt_created else None,
            gmt_modified=t.gmt_modified.strftime("%Y-%m-%d %H:%M:%S") if t.gmt_modified else None,
        ))
    
    return KGPromptTemplateListResponse(
        templates=response_templates,
        total=len(response_templates)
    )


@router.get("/templates/{template_id}", response_model=KGPromptTemplateResponse)
async def get_template(template_id: int):
    """获取单个模板详情"""
    template = template_dao.get_template_by_id(template_id)
    if not template:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    
    variables = []
    if template.variables:
        for v in template.variables:
            variables.append(TemplateVariableVO(
                name=v.get("name", ""),
                type=v.get("type", "text"),
                options=v.get("options"),
                default=v.get("default"),
                description=v.get("description")
            ))
    
    return KGPromptTemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        prompt_content=template.prompt_content,
        variables=variables,
        is_system=bool(template.is_system),
        user_id=template.user_id,
        gmt_created=template.gmt_created.strftime("%Y-%m-%d %H:%M:%S") if template.gmt_created else None,
        gmt_modified=template.gmt_modified.strftime("%Y-%m-%d %H:%M:%S") if template.gmt_modified else None,
    )


@router.post("/templates", response_model=KGPromptTemplateResponse)
async def create_template(
    request: KGPromptTemplateCreateRequest,
    user_id: str = Query(..., description="创建用户ID"),
):
    """创建自定义模板"""
    # 检查名称是否已存在
    existing = template_dao.get_template_by_name(request.name)
    if existing:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Template name '{request.name}' already exists")
    
    # 转换变量格式
    variables_list = None
    if request.variables:
        variables_list = [v.dict() for v in request.variables]
    
    entity = KGPromptTemplateEntity(
        name=request.name,
        description=request.description,
        prompt_content=request.prompt_content,
        variables=variables_list,
        is_system=0,
        user_id=user_id
    )
    
    template_id = template_dao.create_template(entity)
    
    # 返回创建的模板
    return await get_template(template_id)


@router.put("/templates/{template_id}", response_model=KGPromptTemplateResponse)
async def update_template(
    template_id: int,
    request: KGPromptTemplateCreateRequest,
    user_id: str = Query(..., description="用户ID"),
):
    """更新模板（仅允许更新自己创建的非系统模板）"""
    template = template_dao.get_template_by_id(template_id)
    if not template:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    
    if template.is_system:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Cannot modify system template")
    
    if template.user_id != user_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Cannot modify other user's template")
    
    # 转换变量格式
    variables_list = None
    if request.variables:
        variables_list = [v.dict() for v in request.variables]
    
    update_data = {
        "name": request.name,
        "description": request.description,
        "prompt_content": request.prompt_content,
        "variables": variables_list,
    }
    
    template_dao.update_template(template_id, update_data)
    
    return await get_template(template_id)


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: int,
    user_id: str = Query(..., description="用户ID"),
):
    """删除模板（仅允许删除自己创建的非系统模板）"""
    template = template_dao.get_template_by_id(template_id)
    if not template:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    
    if template.is_system:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Cannot delete system template")
    
    success = template_dao.delete_template(template_id, user_id)
    if not success:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Cannot delete other user's template")
    
    return {"success": True, "message": f"Template {template_id} deleted"}


# ============ Smart KG Builder APIs (Phase 2B) ============

from .schemas import (
    KGBuildUploadRequest,
    KGBuildExtractRequest,
    KGBuildExtractResponse,
    KGBuildConfirmRequest,
    KGBuildStatusResponse,
    TripletVO,
    FileInfoVO
)
import uuid
from datetime import datetime

# 临时任务存储（生产环境应使用数据库）
_smart_build_tasks = {}

@router.post("/build/upload")
async def smart_build_upload(
    files: List[UploadFile] = File(...),
    space_name: str = Form(..., description="目标知识库空间名称"),
    chunk_size: int = Form(500, description="切片大小"),
    chunk_overlap: int = Form(50, description="切片重叠"),
    service: Service = Depends(get_service),
):
    """智能构建 - 上传文件并切片"""
    task_id = str(uuid.uuid4())
    
    # 保存文件信息
    file_infos = []
    for f in files:
        file_infos.append(FileInfoVO(
            name=f.filename,
            size=0,
            type=f.filename.split(".")[-1] if "." in f.filename else "unknown",
            status="pending",
            progress=0.0
        ))
    
    _smart_build_tasks[task_id] = {
        "task_id": task_id,
        "space_name": space_name,
        "status": "uploaded",
        "progress": 10.0,
        "current_step": "文件已上传，等待提取",
        "files": file_infos,
        "triplets": [],
        "gmt_created": datetime.now()
    }
    
    return {
        "task_id": task_id,
        "status": "uploaded",
        "message": f"已上传 {len(files)} 个文件，可以开始提取三元组"
    }


@router.post("/build/extract", response_model=KGBuildExtractResponse)
async def smart_build_extract(
    request: KGBuildExtractRequest,
    service: Service = Depends(get_service),
):
    """智能构建 - 提取三元组预览"""
    task_id = request.task_id
    
    if task_id not in _smart_build_tasks:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = _smart_build_tasks[task_id]
    
    # 获取 prompt
    prompt = request.custom_prompt
    if not prompt and request.template_id:
        template = template_dao.get_template_by_id(request.template_id)
        if template:
            prompt = template.prompt_content
            # 替换变量
            if request.variable_values:
                for key, value in request.variable_values.items():
                    prompt = prompt.replace(f"{{{key}}}", value)
    
    # 模拟提取三元组（实际应调用 LLM）
    sample_triplets = [
        TripletVO(subject="知识图谱", predicate="是", object="数据结构", source_chunk="知识图谱是一种用于表示实体关系的数据结构..."),
        TripletVO(subject="实体", predicate="包含", object="属性", source_chunk="每个实体可以包含多个属性..."),
        TripletVO(subject="关系", predicate="连接", object="实体", source_chunk="关系用于连接不同的实体..."),
    ]
    
    task["status"] = "extracted"
    task["progress"] = 60.0
    task["triplets"] = sample_triplets
    task["current_step"] = "三元组提取完成，等待确认"
    
    return KGBuildExtractResponse(
        task_id=task_id,
        triplets=sample_triplets[:request.preview_limit],
        total_triplets=len(sample_triplets),
        preview_limit=request.preview_limit,
        chunks_processed=10,
        total_chunks=10
    )


@router.post("/build/confirm")
async def smart_build_confirm(
    request: KGBuildConfirmRequest,
    service: Service = Depends(get_service),
):
    """智能构建 - 确认并写入图数据库"""
    task_id = request.task_id
    
    if task_id not in _smart_build_tasks:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = _smart_build_tasks[task_id]
    
    # 模拟写入（实际应调用 service 写入 TuGraph）
    task["status"] = "completed"
    task["progress"] = 100.0
    task["current_step"] = "知识图谱构建完成"
    
    triplets_count = len(task.get("triplets", []))
    
    return {
        "success": True,
        "task_id": task_id,
        "message": f"成功导入 {triplets_count} 个三元组到知识图谱",
        "triplets_imported": triplets_count
    }


@router.get("/build/status/{task_id}", response_model=KGBuildStatusResponse)
async def smart_build_status(
    task_id: str,
    service: Service = Depends(get_service),
):
    """智能构建 - 获取任务状态"""
    if task_id not in _smart_build_tasks:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = _smart_build_tasks[task_id]
    
    return KGBuildStatusResponse(
        task_id=task_id,
        status=task["status"],
        progress=task["progress"],
        current_step=task["current_step"],
        files=task.get("files", []),
        triplets_count=len(task.get("triplets", [])),
        error_message=task.get("error_message")
    )

