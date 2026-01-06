import os
import uuid
import logging
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import UploadFile, BackgroundTasks
from dbgpt.component import BaseComponent, SystemApp, ComponentType
from dbgpt.storage.metadata import DatabaseManager
from dbgpt_serve.core import BaseServeConfig
from dbgpt_serve.datasource.manages import ConnectorManager
from dbgpt_ext.datasource.conn_tugraph import TuGraphConnector

from .ws_manager import ws_manager
from ..models.models import KGUploadTaskEntity, KGUploadFileEntity, KGUploadTaskDao, KGUploadFileDao
from ..api.schemas import (
    KGUploadTaskCreateRequest,
    KGUploadTaskResponse,
    KGUploadTaskListResponse,
    KGUploadFileResponse,
    FileInfoVO
)
from ..awel.operators import KGTaskContext
from ..awel.dag import create_kg_dag

logger = logging.getLogger(__name__)

class Service(BaseComponent):
    name = "dbgpt_serve_knowledge_graph_service"

    def __init__(self, system_app: SystemApp, config: BaseServeConfig):
        super().__init__(system_app)
        self._system_app = system_app
        self._config = config
        self._db_manager: Optional[DatabaseManager] = None
        self.task_dao = KGUploadTaskDao()
        self.file_dao = KGUploadFileDao()
        self.ws_manager = ws_manager
        
        # 上传文件存储路径
        self.upload_dir = os.path.join(os.getcwd(), "pilot", "data", "kg_upload")
        if not os.path.exists(self.upload_dir):
            os.makedirs(self.upload_dir)

    def init_app(self, system_app: SystemApp):
        pass

    def on_init(self):
        # 初始化 DAO
        self.task_dao = KGUploadTaskDao()
        self.file_dao = KGUploadFileDao()
        
        # 获取 ConnectorManager
        self._connector_manager: ConnectorManager = self._system_app.get_component(
            ComponentType.CONNECTOR_MANAGER, ConnectorManager
        )
        
        # 尝试初始化 TuGraph Connector
        self._tugraph_connector = None
        try:
            # 寻找类型为 tugraph 的连接配置
            # 优先查找名为 'tugraph_db' 的配置，如果没找到则找第一个类型匹配的
            db_list = self._connector_manager.get_db_list()
            tugraph_db_name = None
            for db in db_list:
                if db.get("db_type") == "tugraph":
                    tugraph_db_name = db.get("db_name")
                    break
            
            if tugraph_db_name:
                logger.info(f"Found TuGraph datasource: {tugraph_db_name}")
                self._tugraph_connector = self._connector_manager.get_connector(tugraph_db_name)
            else:
                logger.warning("No TuGraph datasource found in system configuration.")
        except Exception as e:
            logger.error(f"Failed to init TuGraph connector: {str(e)}")

    def _get_worker_dag(self):
        if not hasattr(self, "_kg_dag") or self._kg_dag is None:
            self._kg_dag = create_kg_dag(self._system_app, self._config, self._tugraph_connector)
        return self._kg_dag

    @classmethod
    def get_instance(cls, system_app: SystemApp):
        return system_app.get_component(cls.name, cls)

    async def create_upload_task(self, request: KGUploadTaskCreateRequest, files: List[UploadFile]) -> KGUploadTaskResponse:
        task_id = str(uuid.uuid4()).replace("-", "")
        
        file_infos = []
        for file in files:
            file_infos.append({
                "name": file.filename,
                "size": 0, # Will update after save
                "type": file.filename.split(".")[-1] if "." in file.filename else "unknown"
            })
            
        # 1. 保存文件到本地
        task_dir = os.path.join(self.upload_dir, task_id)
        os.makedirs(task_dir)
        
        saved_files = []
        for file in files:
            file_path = os.path.join(task_dir, file.filename)
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            
            # 更新文件大小
            size = os.path.getsize(file_path)
            for info in file_infos:
                if info["name"] == file.filename:
                    info["size"] = size
            
            saved_files.append({
                "name": file.filename,
                "path": file_path,
                "size": size
            })

        # 2. 创建任务实体
        task_entity = KGUploadTaskEntity(
            task_id=task_id,
            user_id=request.user_id or "default_user",
            graph_space_name=request.graph_space_name,
            file_names=file_infos,
            total_files=len(files),
            excel_mode=request.excel_mode,
            custom_prompt=request.custom_prompt,
            workflow_config=request.workflow_config,
            status="pending",
            progress=0.0,
            gmt_created=datetime.now(),
            gmt_modified=datetime.now()
        )
        self.task_dao.create_task(task_entity)

        # 3. 创建文件详情实体
        for f in saved_files:
            file_entity = KGUploadFileEntity(
                task_id=task_id,
                file_name=f["name"],
                file_path=f["path"],
                file_size=f["size"],
                file_type=f["name"].split(".")[-1],
                status="pending",
                gmt_created=datetime.now()
            )
            self.file_dao.create_file_detail(file_entity)

        # 4. 异步启动处理流程
        asyncio.create_task(
            self._run_task_real(
                task_id, 
                request.graph_space_name, 
                request.excel_mode,
                [f["path"] for f in saved_files],
                request.custom_prompt
            )
        )

        return self._to_task_response(task_entity)

    def get_task_detail(self, task_id: str) -> KGUploadTaskResponse:
        entity = self.task_dao.get_task(task_id)
        if not entity:
            raise Exception(f"Task {task_id} not found")
        return self._to_task_response(entity)

    def list_tasks(self, user_id: str, page: int, limit: int) -> KGUploadTaskListResponse:
        entities, total = self.task_dao.list_tasks(user_id, page, limit)
        return KGUploadTaskListResponse(
            tasks=[self._to_task_response(e) for e in entities],
            total=total,
            page=page
        )

    async def cancel_task(self, task_id: str):
        self.task_dao.update_task(task_id, {"status": "cancelled", "gmt_modified": datetime.now()})
        await self.ws_manager.broadcast(task_id, {"type": "task_cancelled", "task_id": task_id})
        return {"success": True}

    def _to_task_response(self, e: KGUploadTaskEntity) -> KGUploadTaskResponse:
        file_vos = [FileInfoVO(name=f["name"], size=f["size"], type=f["type"]) for f in e.file_names]
        return KGUploadTaskResponse(
            task_id=e.task_id,
            graph_space_name=e.graph_space_name,
            status=e.status,
            progress=e.progress,
            current_file=e.current_file,
            total_files=e.total_files,
            entities_count=e.entities_count,
            relations_count=e.relations_count,
            file_names=file_vos,
            gmt_created=e.gmt_created.strftime("%Y-%m-%d %H:%M:%S"),
            completed_at=e.completed_at.strftime("%Y-%m-%d %H:%M:%S") if e.completed_at else None,
            error_message=e.error_message
        )

    async def _update_task_status(self, task_id: str, status: str, progress: float, message: str):
        """更新任务状态并推送消息"""
        self.task_dao.update_task(task_id, {
            "status": status,
            "progress": progress,
            "error_message": message if status == "failed" else None,
            "gmt_modified": datetime.now()
        })
        await self.ws_manager.send_progress(task_id, progress, status=status, message=message)

    async def _run_task_real(self, task_id: str, graph_space: str, excel_mode: str, file_paths: List[str], custom_prompt: Optional[str]):
        """执行真实的 AWEL 任务流程"""
        logger.info(f"Starting real task processing for {task_id}")
        try:
            await self._update_task_status(task_id, "running", 0.1, "开始解析文件...")
            
            # 准备上下文
            ctx = KGTaskContext(
                task_id=task_id,
                graph_space=graph_space,
                excel_mode=excel_mode,
                file_paths=file_paths,
                custom_prompt=custom_prompt
            )
            
            # 使用 AWEL DAG 执行
            dag = self._get_worker_dag()
            
            # 动态调整导入目标的图空间
            import_task = dag.leaf_nodes[0]
            if hasattr(import_task, "_graph_name"):
                import_task._graph_name = graph_space
            
            await self._update_task_status(task_id, "running", 0.3, "正在利用 LLM 提取知识三元组...")
            
            # 运行 DAG
            result_count = await dag.call(ctx)
            
            await self._update_task_status(task_id, "completed", 1.0, f"提取完成，成功导入 {result_count} 个三元组")
            self.task_dao.update_task(task_id, {
                "status": "completed",
                "progress": 100.0,
                "completed_at": datetime.now(),
                "relations_count": result_count
            })
            await self.ws_manager.broadcast(task_id, {"type": "task_completed", "task_id": task_id})
            
        except Exception as e:
            logger.error(f"Task {task_id} failed: {str(e)}")
            await self._update_task_status(task_id, "failed", 1.0, f"处理失败: {str(e)}")

    async def _run_task_mock(self, task_id: str):
        pass

        self.task_dao.update_task(task_id, {"status": "running"})
        await self.ws_manager.send_progress(task_id, 0, status="running")

        total = task.total_files
        for i, file_info in enumerate(task.file_names):
            file_name = file_info["name"]
            self.task_dao.update_task(task_id, {"current_file": file_name})
            self.file_dao.update_file_detail(task_id, file_name, {"status": "processing"})
            
            # 模拟处理每个文件
            for p in range(0, 101, 20):
                file_progress = p
                overall_progress = (i / total * 100) + (p / 100 * (1 / total) * 100)
                
                # 更新任务和发送 WS
                self.task_dao.update_task(task_id, {"progress": overall_progress})
                await self.ws_manager.send_progress(
                    task_id, 
                    overall_progress, 
                    current_file=file_name,
                    file_progress=file_progress,
                    entities_count=task.entities_count + (i * 10) + (p // 10),
                    relations_count=task.relations_count + (i * 5) + (p // 20)
                )
                await asyncio.sleep(0.5)
            
            self.file_dao.update_file_detail(task_id, file_name, {
                "status": "completed", 
                "progress": 100.0,
                "chunks_count": 5
            })

        self.task_dao.update_task(task_id, {
            "status": "completed", 
            "progress": 100.0, 
            "completed_at": datetime.now(),
            "entities_count": total * 12,
            "relations_count": total * 7
        })
        await self.ws_manager.broadcast(task_id, {"type": "task_completed", "task_id": task_id})
        logger.info(f"Mock task {task_id} completed")
