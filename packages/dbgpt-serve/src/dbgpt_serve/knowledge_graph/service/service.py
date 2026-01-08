import os
import uuid
import logging
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import UploadFile, BackgroundTasks
from dbgpt.component import BaseComponent, SystemApp, ComponentType
from dbgpt.storage.metadata import DatabaseManager
from dbgpt.rag.knowledge.base import KnowledgeType
from dbgpt_serve.core import BaseServeConfig
from dbgpt_serve.datasource.manages import ConnectorManager
from dbgpt_serve.rag.models.document_db import KnowledgeDocumentDao, KnowledgeDocumentEntity
from dbgpt_serve.rag.models.models import KnowledgeSpaceDao, KnowledgeSpaceEntity
from dbgpt_serve.rag.models.chunk_db import DocumentChunkDao, DocumentChunkEntity
from dbgpt_serve.rag.service.service import SyncStatus
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
        self.document_dao = KnowledgeDocumentDao()
        self.space_dao = KnowledgeSpaceDao()
        self.chunk_dao = DocumentChunkDao()
        
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
            logger.info(f"xSmartKG: Available databases: {db_list}")
            tugraph_db_name = None
            for db in db_list:
                db_type = db.get("db_type", "").lower()
                if db_type == "tugraph":
                    tugraph_db_name = db.get("db_name")
                    break
            
            if tugraph_db_name:
                logger.info(f"xSmartKG: Found TuGraph datasource: {tugraph_db_name}")
                self._tugraph_connector = self._connector_manager.get_connector(tugraph_db_name)
            else:
                logger.warning("xSmartKG: No TuGraph datasource found in system configuration.")
        except Exception as e:
            logger.error(f"Failed to init TuGraph connector: {str(e)}")

    def _get_or_create_space(self, space_name: str) -> Optional[KnowledgeSpaceEntity]:
        """获取或创建知识库空间，确保 KnowledgeGraph 类型的文档可以关联到对应空间"""
        spaces = self.space_dao.get_knowledge_space(KnowledgeSpaceEntity(name=space_name))
        if spaces:
            return spaces[0]
        # 如果空间不存在，不自动创建（用户应该先在知识库页面创建）
        logger.warning(f"Knowledge space '{space_name}' not found. Documents will be created without space association.")
        return None

    def _get_worker_dag(self):
        if not hasattr(self, "_kg_dag") or self._kg_dag is None:
            self._kg_dag = create_kg_dag(self._system_app, self._config, self._tugraph_connector)
        return self._kg_dag

    def _get_mapping_dag(self):
        """获取 Excel 列映射模式的 DAG"""
        if not hasattr(self, "_kg_mapping_dag") or self._kg_mapping_dag is None:
            from ..awel.dag import create_kg_mapping_dag
            self._kg_mapping_dag = create_kg_mapping_dag(self._tugraph_connector)
        return self._kg_mapping_dag

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

        # 3. 创建文件详情实体 + 创建对应的 KnowledgeDocumentEntity
        # 获取或查找对应的知识库空间
        space = self._get_or_create_space(request.graph_space_name)
        doc_id_map = {}  # 用于存储文件名到文档ID的映射
        
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
            
            # 同时创建 KnowledgeDocumentEntity，使其与标准知识库系统集成
            if space:
                # 检查是否已存在同名文档
                existing_docs = self.document_dao.get_knowledge_documents(
                    KnowledgeDocumentEntity(doc_name=f["name"], space=space.name)
                )
                if existing_docs:
                    # 如果已存在，更新状态为 RUNNING
                    doc = existing_docs[0]
                    doc.status = SyncStatus.RUNNING.name
                    doc.last_sync = datetime.now()
                    doc.content = f["path"]
                    self.document_dao.update_knowledge_document(doc)
                    doc_id_map[f["name"]] = doc.id
                    logger.info(f"Updated existing document: {f['name']} (id={doc.id})")
                else:
                    # 创建新文档
                    doc_type = KnowledgeType.DOCUMENT.value
                    doc_entity = KnowledgeDocumentEntity(
                        doc_name=f["name"],
                        doc_type=doc_type,
                        space=space.name,
                        chunk_size=0,  # 初始化为 0，处理完成后更新
                        status=SyncStatus.RUNNING.name,
                        last_sync=datetime.now(),
                        content=f["path"],
                        result="",
                    )
                    doc_id = self.document_dao.create_knowledge_document(doc_entity)
                    doc_id_map[f["name"]] = doc_id
                    logger.info(f"Created new document: {f['name']} (id={doc_id})")

        # 4. 异步启动处理流程，传入 doc_id_map 以便后续更新
        asyncio.create_task(
            self._run_task_real(
                task_id, 
                request.graph_space_name, 
                request.excel_mode,
                [f["path"] for f in saved_files],
                request.custom_prompt,
                request.column_mapping,
                doc_id_map  # 新增参数
            )
        )

        return self._to_task_response(task_entity)

    def get_task_detail(self, task_id: str) -> KGUploadTaskResponse:
        entity = self.task_dao.get_task(task_id)
        if not entity:
            raise Exception(f"Task {task_id} not found")
        return self._to_task_response(entity)

    def list_tasks(self, user_id: str, page: int, limit: int, status: Optional[str] = None) -> KGUploadTaskListResponse:
        entities, total = self.task_dao.list_tasks(user_id, page, limit, status)
        return KGUploadTaskListResponse(
            tasks=[self._to_task_response(e) for e in entities],
            total=total,
            page=page
        )

    async def cancel_task(self, task_id: str):
        self.task_dao.update_task(task_id, {"status": "cancelled", "gmt_modified": datetime.now()})
        await self.ws_manager.broadcast(task_id, {"type": "task_cancelled", "task_id": task_id})
        return {"success": True}

    async def list_graph_spaces(self):
        """获取可用的图空间列表 - 返回存储类型为 Knowledge Graph 的知识库"""
        spaces = []
        try:
            # 从 DB-GPT 知识库系统获取存储类型为 Knowledge Graph 的空间
            # KnowledgeSpaceEntity 的 vector_type 字段存储存储类型
            all_spaces = self.space_dao.get_knowledge_space(KnowledgeSpaceEntity())
            if all_spaces:
                for space in all_spaces:
                    # 检查 vector_type 是否包含 'Graph' 或 'Knowledge' 关键词
                    # 通常 Knowledge Graph 类型的 vector_type 值为 'KnowledgeGraph'
                    vector_type = getattr(space, 'vector_type', '') or ''
                    if 'graph' in vector_type.lower() or 'knowledge' in vector_type.lower():
                        spaces.append(space.name)
                        logger.info(f"xSmartKG: Found KG space: {space.name} (type={vector_type})")
            
            # 如果没有找到 KnowledgeGraph 类型的空间，返回所有空间供选择
            if not spaces and all_spaces:
                spaces = [s.name for s in all_spaces]
                logger.info(f"xSmartKG: No KG-type spaces found, returning all {len(spaces)} spaces")
                
        except Exception as e:
            logger.error(f"xSmartKG: Error listing knowledge spaces: {str(e)}")
        
        # 确保 spaces 是列表且不为空
        if not spaces:
            spaces = ["default"]
            
        return {"spaces": spaces}

    async def create_graph_space(self, space_name: str):
        """创建新的图空间"""
        try:
            if self._tugraph_connector:
                self._tugraph_connector.create_graph(space_name)
                return {"success": True, "space_name": space_name}
            else:
                return {"success": False, "error": "TuGraph not connected"}
        except Exception as e:
            logger.error(f"Failed to create graph space {space_name}: {str(e)}")
            return {"success": False, "error": str(e)}

    async def delete_task(self, task_id: str):
        """删除任务"""
        try:
            task = self.task_dao.get_task_by_id(task_id)
            if not task:
                return {"success": False, "error": "Task not found"}
            
            # 删除任务记录
            self.task_dao.delete_task(task_id)
            logger.info(f"Deleted task {task_id}")
            return {"success": True, "task_id": task_id}
        except Exception as e:
            logger.error(f"Failed to delete task {task_id}: {str(e)}")
            return {"success": False, "error": str(e)}


    def _to_task_response(self, e: KGUploadTaskEntity) -> KGUploadTaskResponse:
        file_vos = []
        for f in e.file_names:
            status = f.get("status", "pending")
            progress = f.get("progress", 0.0)
            # 如果任务已完成，所有文件标记为完成
            if e.status == "completed":
                status = "completed"
                progress = 1.0
            file_vos.append(FileInfoVO(
                name=f["name"], 
                size=f["size"], 
                type=f["type"],
                status=status,
                progress=progress
            ))
        
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
        # 获取最新任务状态以获取最新的 file_names (可能包含各文件进度)
        task = self.task_dao.get_task(task_id)
        file_vos = []
        if task:
            task_resp = self._to_task_response(task)
            file_vos = [f.dict() for f in task_resp.file_names]

        await self.ws_manager.send_progress(
            task_id, 
            progress, 
            status=status, 
            message=message,
            file_names=file_vos
        )

    async def _run_task_real(self, task_id: str, graph_space: str, excel_mode: str, file_paths: List[str], custom_prompt: Optional[str], column_mapping=None, doc_id_map: Optional[Dict[str, int]] = None):
        """执行真实的 AWEL 任务流程"""
        logger.info(f"Starting real task processing for {task_id}, mode: {excel_mode}")
        try:
            await self._update_task_status(task_id, "running", 10.0, "开始解析文件...")
            
            # 准备上下文
            ctx = KGTaskContext(
                task_id=task_id,
                graph_space=graph_space,
                excel_mode=excel_mode,
                file_paths=file_paths,
                custom_prompt=custom_prompt,
                column_mapping=column_mapping
            )
            
            # 根据 excel_mode 选择 DAG
            if excel_mode == "mapping" and column_mapping:
                dag = self._get_mapping_dag()
            else:
                dag = self._get_worker_dag()
            
            # 获取 DAG 的根节点（第一个 Operator - FileParsingOperator）
            root_nodes = dag.root_nodes
            if not root_nodes:
                raise Exception("DAG has no root nodes")
            start_node = root_nodes[0]
            
            # 获取末端节点用于动态调整图空间
            leaf_nodes = dag.leaf_nodes
            if leaf_nodes and hasattr(leaf_nodes[0], "_graph_name"):
                leaf_nodes[0]._graph_name = graph_space
            
            await self._update_task_status(task_id, "running", 30.0, "正在利用 LLM 提取知识三元组...")
            
            # 使用 DefaultWorkflowRunner 执行 DAG
            # 从末端节点开始执行，但将数据作为根节点的call_data传入
            from dbgpt.core.awel.runner.local_runner import DefaultWorkflowRunner
            runner = DefaultWorkflowRunner()
            
            # execute_workflow 需要从末端节点调用，会自动执行上游节点
            # 重要: SimpleCallDataInputSource 期望 call_data 格式为 {"data": actual_data}
            end_node = leaf_nodes[0] if leaf_nodes else start_node
            dag_ctx = await runner.execute_workflow(end_node, call_data={"data": ctx})
            
            # 从 DAG Context 获取结果（新的并行 DAG 返回聚合结果）
            task_output = dag_ctx.current_task_context.task_output
            result = task_output.output if task_output else {}
            
            # 解析聚合结果
            if isinstance(result, dict):
                triplets_count = result.get("triplets_count", 0)
                vectors_count = result.get("vectors_count", 0)
            else:
                # 兼容旧版本（只返回三元组数量）
                triplets_count = result if isinstance(result, int) else 0
                vectors_count = 0
            
            logger.info(f"Task {task_id} completed: {triplets_count} triplets, {vectors_count} vectors")
            
            # 更新关联的 KnowledgeDocumentEntity 的 chunk_size 和状态
            if doc_id_map:
                total_files = len(doc_id_map)
                avg_chunks = max(1, vectors_count // total_files) if total_files > 0 and vectors_count > 0 else 0
                avg_triplets = max(1, triplets_count // total_files) if total_files > 0 and triplets_count > 0 else 0
                
                for file_name, doc_id in doc_id_map.items():
                    try:
                        docs = self.document_dao.documents_by_ids([doc_id])
                        if docs:
                            doc = docs[0]
                            doc.chunk_size = avg_chunks
                            doc.status = SyncStatus.FINISHED.name
                            doc.result = f"知识图谱处理完成：{avg_triplets} 个三元组，{avg_chunks} 个向量切片"
                            self.document_dao.update_knowledge_document(doc)
                            logger.info(f"Updated document {file_name} (id={doc_id}): chunks={avg_chunks}, triplets={avg_triplets}")
                    except Exception as e:
                        logger.error(f"Failed to update document {file_name}: {str(e)}")
            
            completion_message = f"处理完成！三元组：{triplets_count}，向量切片：{vectors_count}"
            await self._update_task_status(task_id, "completed", 100.0, completion_message)
            self.task_dao.update_task(task_id, {
                "status": "completed",
                "progress": 100.0,
                "completed_at": datetime.now(),
                "relations_count": triplets_count,
                "entities_count": vectors_count
            })
            await self.ws_manager.broadcast(task_id, {"type": "task_completed", "task_id": task_id})
            
        except Exception as e:
            logger.error(f"Task {task_id} failed: {str(e)}")
            await self._update_task_status(task_id, "failed", 1.0, f"处理失败: {str(e)}")
            # 同时更新关联文档的状态为失败
            if doc_id_map:
                for file_name, doc_id in doc_id_map.items():
                    try:
                        docs = self.document_dao.documents_by_ids([doc_id])
                        if docs:
                            doc = docs[0]
                            doc.status = SyncStatus.FAILED.name
                            doc.result = f"知识图谱处理失败: {str(e)}"
                            self.document_dao.update_knowledge_document(doc)
                    except Exception as update_error:
                        logger.error(f"Failed to update document {file_name} status: {str(update_error)}")


    async def _run_task_mock(self, task_id: str):
        """模拟执行任务用于测试"""
        task = self.task_dao.get_task(task_id)
        if not task:
            logger.error(f"Task {task_id} not found in mock")
            return

        self.task_dao.update_task(task_id, {"status": "running", "progress": 0.0})
        await self._update_task_status(task_id, "running", 0.0, "任务启动中...")

        total = task.total_files
        file_list = task.file_names
        for i, file_info in enumerate(file_list):
            file_name = file_info["name"]
            
            # 模拟处理每个文件
            for p in range(0, 101, 20):
                await asyncio.sleep(0.5)
                # 更新当前文件的进度并保存回 task entity 的 JSON 中
                file_info["status"] = "processing" if p < 100 else "completed"
                file_info["progress"] = float(p) # 0-100
                self.task_dao.update_task(task_id, {
                    "file_names": file_list,
                    "current_file": file_name
                })
                
                overall_progress = (i / total * 100.0) + (p / total)
                await self._update_task_status(
                    task_id, 
                    "running", 
                    overall_progress, 
                    f"正在处理文件: {file_name} ({p}%)"
                )

        self.task_dao.update_task(task_id, {
            "status": "completed", 
            "progress": 100.0, 
            "completed_at": datetime.now(),
            "entities_count": total * 12,
            "relations_count": total * 7
        })
        await self._update_task_status(task_id, "completed", 100.0, "任务处理完成")
        await self.ws_manager.broadcast(task_id, {"type": "task_completed", "task_id": task_id})
        logger.info(f"Mock task {task_id} completed")
