import logging
import os
import pandas as pd
import json
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass

from dbgpt.core.awel import MapOperator, DAGContext
from dbgpt.core import LLMClient, ModelRequest, ModelMessage, Document
from dbgpt_ext.datasource.conn_tugraph import TuGraphConnector
from dbgpt_ext.rag.knowledge.factory import KnowledgeFactory
from dbgpt.rag.knowledge.base import KnowledgeType
from ..api.schemas import KGUploadTaskCreateRequest, ExcelColumnMapping

logger = logging.getLogger(__name__)

@dataclass
class KGTaskContext:
    task_id: str
    graph_space: str
    excel_mode: str
    file_paths: List[str]
    custom_prompt: Optional[str] = None
    column_mapping: Optional[ExcelColumnMapping] = None

class FileParsingOperator(MapOperator[KGTaskContext, List[Document]]):
    """解析多样化的文件类型（Excel, PDF, Word, TXT, MD）并提取文档内容"""
    
    async def map(self, ctx: KGTaskContext) -> List[Document]:
        logger.info(f"Start parsing {len(ctx.file_paths)} files for task {ctx.task_id}")
        # 将 graph_space 存入共享数据，供后续 Operator 使用
        await self.current_dag_context.save_to_share_data("kg_graph_space", ctx.graph_space)
        await self.current_dag_context.save_to_share_data("kg_custom_prompt", ctx.custom_prompt)
        
        all_documents = []
        for file_path in ctx.file_paths:
            if not os.path.exists(file_path):
                logger.warning(f"File not found: {file_path}")
                continue
            
            try:
                # 使用 KnowledgeFactory 自动识别文件类型并创建加载器
                knowledge = KnowledgeFactory.create(
                    datasource=file_path,
                    knowledge_type=KnowledgeType.DOCUMENT
                )
                # 加载并解析文件
                docs = knowledge.load()
                all_documents.extend(docs)
                logger.info(f"Successfully parsed {file_path}, got {len(docs)} documents")
            except Exception as e:
                logger.error(f"Failed to parse file {file_path}: {str(e)}")
                
        return all_documents

class KGExtractionOperator(MapOperator[List[Document], List[Tuple[str, str, str]]]):
    """利用 LLM 从文档中提取知识三元组"""
    
    def __init__(self, llm_client: LLMClient, model_name: str, custom_prompt: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self._llm_client = llm_client
        self._model_name = model_name
        self._custom_prompt = custom_prompt

    async def map(self, documents: List[Document]) -> List[Tuple[str, str, str]]:
        if not documents:
            logger.warning("KGExtractionOperator received empty documents list!")
            return []
        
        # 日志输出接收到的文档数量和内容长度
        logger.info(f"KGExtractionOperator received {len(documents)} documents")
        for i, doc in enumerate(documents):
            logger.info(f"  Doc[{i}] content length: {len(doc.content) if doc.content else 0} chars")
            
        # 构建文本内容进行处理
        # 简单处理：将所有 Document 的 content 拼接
        # 实际生产中建议针对大文本进行 Batch 处理以避免超过 LLM 上下文限制
        full_text_content = "\n\n".join([doc.content for doc in documents if doc.content])
        
        if not full_text_content:
            logger.warning("All documents have empty content, skipping extraction")
            return []
            
        logger.info(f"Total text content length: {len(full_text_content)} chars")
        
        # 如果文本过长，截断（示例中简单截断）
        if len(full_text_content) > 10000:
            logger.warning("Content too long for extraction, truncating to 10000 characters...")
            full_text_content = full_text_content[:10000]

        system_prompt = self._custom_prompt or """
你是一个知识图谱提取专家。请从给出的文本中提取实体及其关系，并以 JSON 数组格式返回三元组。
每个三元组格式为: ["实体1", "关系", "实体2"]
只返回 JSON 代码块，不要包含任何额外的解释说明。
"""
        user_prompt = f"请提取以下文本中的三元组关系：\n\n{full_text_content}"
        
        logger.info(f"Sending to LLM - system_prompt length: {len(system_prompt)}, user_prompt length: {len(user_prompt)}")
        
        messages = [
            ModelMessage(role="system", content=system_prompt),
            ModelMessage(role="human", content=user_prompt)  # 必须使用 'human' 而非 'user'
        ]
        
        request = ModelRequest(model=self._model_name, messages=messages)
        
        # 详细日志：打印所有消息的角色和内容长度
        logger.info(f"ModelRequest messages count: {len(messages)}")
        for i, msg in enumerate(messages):
            logger.info(f"  Message[{i}] role={msg.role}, content_len={len(msg.content) if msg.content else 0}")
        
        # 调用 LLM (generate_stream 返回异步生成器，不需要 await)
        response = self._llm_client.generate_stream(request)
        full_text = ""
        async for chunk in response:
            full_text += chunk.text
            
        logger.debug(f"LLM Raw Output for extraction: {full_text}")
        
        # 简单解析 JSON 结果
        triplets = []
        try:
            # 去掉可能的 Markdown 标记
            clean_text = full_text.strip()
            if "```json" in clean_text:
                clean_text = clean_text.split("```json")[1].split("```")[0]
            elif "```" in clean_text:
                clean_text = clean_text.split("```")[1].split("```")[0]
            
            clean_text = clean_text.strip()
            
            # 使用 raw_decode 尝试解析第一个合法的 JSON 对象，忽略由于流式拼接可能导致的后续重复内容
            try:
                data, _ = json.JSONDecoder().raw_decode(clean_text)
            except json.JSONDecodeError:
                # 如果 raw_decode 失败（例如开头不是合法 JSON），尝试直接 loads
                # 或者如果有其他干扰字符，这里作为兜底
                data = json.loads(clean_text)

            if isinstance(data, list):
                for item in data:
                    if isinstance(item, list) and len(item) == 3:
                        triplets.append(tuple([str(i).strip() for i in item]))
        except Exception as e:
            logger.error(f"Failed to parse LLM output as JSON: {str(e)}. Raw text: {full_text[:200]}...")
            
        return triplets

class TuGraphImportOperator(MapOperator[List[Tuple[str, str, str]], int]):
    """将三元组导入 TuGraph"""
    
    def __init__(self, connector: TuGraphConnector, graph_name: str, **kwargs):
        super().__init__(**kwargs)
        self._connector = connector
        self._graph_name = graph_name

    async def map(self, triplets: List[Tuple[str, str, str]]) -> int:
        if not triplets:
            return 0
            
        if self._connector is None:
            logger.error("TuGraph connector is not initialized. Please check system configuration.")
            raise ValueError("TuGraph 连接器未初始化，请先在数据源管理中配置 TuGraph。")

        # 从共享数据中获取真实的图空间名
        graph_name = await self.current_dag_context.get_from_share_data("kg_graph_space") or self._graph_name
        
        count = 0
        # 确保图空间存在
        try:
            if not self._connector.is_exist(graph_name):
                self._connector.create_graph(graph_name)
        except Exception as e:
            logger.warning(f"Failed to check/create graph {graph_name}, trying default: {str(e)}")
            graph_name = "default"
            
        # 切换或确保使用正确的图空间
        # 注意：TuGraphConnector 的 run 方法是基于 self._graph 的
        # 我们这里动态修改简易实例属性（仅对当前执行有效）
        original_graph = self._connector._graph
        self._connector._graph = graph_name
        
        try:
            # 简单的导入逻辑：使用 Cypher MERGE
            for s, p, o in triplets:
                try:
                    # 实体转义
                    s_esc = s.replace("'", "\\'")
                    o_esc = o.replace("'", "\\'")
                    p_label = p.replace("'", "\\'").replace(" ", "_")
                    
                    # 创建节点和边
                    cypher_s = f"MERGE (n:Entity {{name: '{s_esc}'}})"
                    cypher_o = f"MERGE (n:Entity {{name: '{o_esc}'}})"
                    cypher_r = (
                        f"MATCH (a:Entity {{name: '{s_esc}'}}), (b:Entity {{name: '{o_esc}'}}) "
                        f"MERGE (a)-[r:Relation {{type: '{p_label}'}}]->(b)"
                    )
                    
                    self._connector.run(cypher_s)
                    self._connector.run(cypher_o)
                    self._connector.run(cypher_r)
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to import triplet ({s}, {p}, {o}): {str(e)}")
        finally:
            self._connector._graph = original_graph
            
        return count


class ExcelMappingOperator(MapOperator[KGTaskContext, List[Tuple[str, str, str]]]):
    """Excel 列映射模式：直接从 Excel 列中提取实体和关系，跳过 LLM 提取"""
    
    async def map(self, ctx: KGTaskContext) -> List[Tuple[str, str, str]]:
        if not ctx.column_mapping:
            logger.warning("No column_mapping provided, returning empty triplets")
            return []
            
        triplets = []
        mapping = ctx.column_mapping
        
        for file_path in ctx.file_paths:
            if not file_path.endswith(('.xlsx', '.xls')):
                logger.warning(f"Skipping non-Excel file: {file_path}")
                continue
                
            try:
                # 读取 Excel 文件
                df = pd.read_excel(file_path)
                logger.info(f"Read Excel file {file_path}, columns: {list(df.columns)}")
                
                # 从关系配置中提取三元组
                for rel_config in mapping.relation_configs:
                    subject_col = rel_config.subject_column
                    predicate = rel_config.predicate
                    object_col = rel_config.object_column
                    
                    if subject_col not in df.columns or object_col not in df.columns:
                        logger.warning(f"Column not found: {subject_col} or {object_col}")
                        continue
                    
                    # 遍历每行，生成三元组
                    for _, row in df.iterrows():
                        subject = str(row[subject_col]).strip()
                        obj = str(row[object_col]).strip()
                        
                        # 跳过空值
                        if subject and obj and subject != 'nan' and obj != 'nan':
                            triplets.append((subject, predicate, obj))
                            
                logger.info(f"Extracted {len(triplets)} triplets from {file_path}")
                
            except Exception as e:
                logger.error(f"Failed to process Excel file {file_path}: {str(e)}")
                
        # 将 graph_space 存入共享数据供导入使用
        await self.current_dag_context.save_to_share_data("kg_graph_space", ctx.graph_space)
        
        return triplets


# ============ 向量存储相关 Operators ============

class ChunkingOperator(MapOperator[List[Document], List["Chunk"]]):
    """文档切片 Operator - 将文档切分成小块以便向量化和存储"""
    
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50, **kwargs):
        super().__init__(**kwargs)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    async def map(self, documents: List[Document]) -> List["Chunk"]:
        """将文档切片
        
        Args:
            documents: 文档列表
            
        Returns:
            切片列表
        """
        from dbgpt.core import Chunk
        from dbgpt.rag.text_splitter import CharacterTextSplitter
        
        if not documents:
            logger.warning("ChunkingOperator received empty documents")
            return []
        
        logger.info(f"ChunkingOperator processing {len(documents)} documents")
        
        chunks = []
        text_splitter = CharacterTextSplitter(
            separator="\n\n",
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        
        for doc in documents:
            if not doc.content:
                continue
            
            # 使用 text_splitter 进行切片
            text_chunks = text_splitter.split_text(doc.content)
            
            # 转换为 Chunk 对象
            for i, text_chunk in enumerate(text_chunks):
                chunk = Chunk(
                    content=text_chunk,
                    metadata={
                        "source": doc.metadata.get("source", "unknown") if doc.metadata else "unknown",
                        "chunk_index": i,
                        "doc_name": doc.metadata.get("file_name", "unknown") if doc.metadata else "unknown",
                    }
                )
                chunks.append(chunk)
        
        logger.info(f"ChunkingOperator generated {len(chunks)} chunks from {len(documents)} documents")
        return chunks


class EmbeddingOperator(MapOperator[List["Chunk"], List["Chunk"]]):
    """向量化 Operator - 为文档切片生成向量表示"""
    
    def __init__(self, embedding_model_name: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.embedding_model_name = embedding_model_name
        self._embedding_model = None
    
    async def map(self, chunks: List["Chunk"]) -> List["Chunk"]:
        """为切片生成 embedding
        
        Args:
            chunks: 切片列表
            
        Returns:
            带有 embedding 的切片列表
        """
        from dbgpt.rag.embedding import EmbeddingFactory
        
        if not chunks:
            logger.warning("EmbeddingOperator received empty chunks")
            return []
        
        logger.info(f"EmbeddingOperator processing {len(chunks)} chunks")
        
        # 延迟加载 embedding 模型
        if self._embedding_model is None:
            self._embedding_model = EmbeddingFactory.get_instance(
                self.system_app
            ).create(model_name=self.embedding_model_name)
            logger.info(f"Loaded embedding model: {self.embedding_model_name or 'default'}")
        
        # 批量生成 embeddings
        texts = [chunk.content for chunk in chunks]
        
        try:
            # 调用 embedding 模型
            embeddings = await self._embedding_model.aembed_documents(texts)
            
            # 将 embeddings 添加到 chunks
            for chunk, embedding in zip(chunks, embeddings):
                chunk.embeddings = embedding
            
            logger.info(f"EmbeddingOperator generated embeddings for {len(chunks)} chunks")
        except Exception as e:
            logger.error(f"EmbeddingOperator failed: {str(e)}")
            raise
        
        return chunks


class VectorStoreOperator(MapOperator[List["Chunk"], int]):
    """向量存储 Operator - 将向量化的切片存储到向量数据库"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._storage_connector = None
    
    async def map(self, chunks: List["Chunk"]) -> int:
        """存储切片到向量数据库
        
        Args:
            chunks: 带有 embedding 的切片列表
            
        Returns:
            存储的切片数量
        """
        from dbgpt_serve.rag.storage_manager import StorageManager
        from dbgpt_serve.rag.models.models import KnowledgeSpaceDao, KnowledgeSpaceEntity
        from dbgpt_serve.rag.models.chunk_db import DocumentChunkDao, DocumentChunkEntity
        from datetime import datetime
        
        if not chunks:
            logger.warning("VectorStoreOperator received empty chunks")
            return 0
        
        logger.info(f"VectorStoreOperator storing {len(chunks)} chunks")
        
        # 从 DAG Context 获取 graph_space 名称
        graph_space = await self.current_dag_context.get_from_share_data("kg_graph_space")
        if not graph_space:
            logger.error("VectorStoreOperator: graph_space not found in context")
            return 0
        
        # 获取知识库空间信息
        space_dao = KnowledgeSpaceDao()
        spaces = space_dao.get_knowledge_space(KnowledgeSpaceEntity(name=graph_space))
        
        if not spaces:
            logger.error(f"VectorStoreOperator: Knowledge space '{graph_space}' not found")
            return 0
        
        space = spaces[0]
        
        # 获取存储连接器
        storage_manager = StorageManager.get_instance(self.system_app)
        storage_connector = storage_manager.get_storage_connector(
            space.name,
            space.vector_type
        )
        
        try:
            # 批量存储到向量数据库
            vector_ids = await storage_connector.aload_document(chunks)
            
            # 保存 chunk 详情到数据库（用于后续查询和管理）
            chunk_dao = DocumentChunkDao()
            chunk_entities = []
            
            # 获取 document_id（从第一个 chunk 的 metadata 中获取）
            # 注意：这里需要在 FileParsingOperator 或之前的步骤中设置 document_id
            doc_id = chunks[0].metadata.get("document_id") if chunks[0].metadata else None
            doc_name = chunks[0].metadata.get("doc_name", "unknown") if chunks[0].metadata else "unknown"
            
            for chunk in chunks:
                chunk_entity = DocumentChunkEntity(
                    doc_name=doc_name,
                    doc_type="DOCUMENT",
                    document_id=doc_id,
                    content=chunk.content,
                    meta_info=str(chunk.metadata),
                    gmt_created=datetime.now(),
                    gmt_modified=datetime.now(),
                )
                chunk_entities.append(chunk_entity)
            
            if chunk_entities:
                chunk_dao.create_documents_chunks(chunk_entities)
                logger.info(f"VectorStoreOperator saved {len(chunk_entities)} chunk entities to DB")
            
            logger.info(f"VectorStoreOperator successfully stored {len(vector_ids)} vectors")
            return len(vector_ids)
            
        except Exception as e:
            logger.error(f"VectorStoreOperator failed to store chunks: {str(e)}")
            raise
