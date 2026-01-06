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
            return []
            
        # 构建文本内容进行处理
        # 简单处理：将所有 Document 的 content 拼接
        # 实际生产中建议针对大文本进行 Batch 处理以避免超过 LLM 上下文限制
        full_text_content = "\n\n".join([doc.content for doc in documents])
        
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
        
        messages = [
            ModelMessage(role="system", content=system_prompt),
            ModelMessage(role="user", content=user_prompt)
        ]
        
        request = ModelRequest(model=self._model_name, messages=messages)
        
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
