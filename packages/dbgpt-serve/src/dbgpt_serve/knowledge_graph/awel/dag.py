import logging
from typing import Optional, List, Any
from dbgpt.core.awel import DAG, JoinOperator, BaseOperator, TriggerOperator, MapOperator
from .operators import (
    FileParsingOperator,
    KGExtractionOperator,
    TuGraphImportOperator,
    ExcelMappingOperator,
    KGTaskContext,
    ChunkingOperator,
    EmbeddingOperator,
    VectorStoreOperator,
)
from dbgpt.component import SystemApp, ComponentType
from dbgpt.model.cluster import WorkerManagerFactory
from dbgpt_ext.datasource.conn_tugraph import TuGraphConnector

logger = logging.getLogger(__name__)

class ResultAggregatorOperator(MapOperator[List[Any], dict]):
    """聚合图谱和向量分支的结果"""
    
    async def map(self, results: List[Any]) -> dict:
        triplets_count = results[0] if len(results) > 0 else 0
        vectors_count = results[1] if len(results) > 1 else 0
        result = {
            "triplets_count": triplets_count,
            "vectors_count": vectors_count
        }
        logger.info(f"Aggregated result: {result}")
        return result


def create_kg_dag(system_app: SystemApp, config: any, connector: TuGraphConnector) -> DAG:
    """创建并返回知识图谱构建 DAG（LLM 提取模式 + 向量存储）"""
    
    with DAG("dbgpt_kg_upload_workflow") as dag:
        # 0. 触发器 Operator - 接收 call_data (KGTaskContext)
        # TriggerOperator 使用 SimpleCallDataInputSource 自动接收 execute_workflow 的 call_data
        trigger_task = TriggerOperator()
        
        # 1. 解析 Operator
        parsing_task = FileParsingOperator()
        
        # 获取 LLM Client
        worker_manager = system_app.get_component(
            ComponentType.WORKER_MANAGER_FACTORY, WorkerManagerFactory
        ).create()
        from dbgpt.model import DefaultLLMClient
        llm_client = DefaultLLMClient(worker_manager)
        
        # 2. 提取 Operator (使用配置中的 qwen-max)
        extraction_task = KGExtractionOperator(
            llm_client=llm_client, 
            model_name=getattr(config, 'default_llm_model', None) or "qwen-max"
        )
        
        # 3. 导入 Operator
        import_task = TuGraphImportOperator(
            connector=connector,
            graph_name="default"  # 初始占位，运行时从上下文获取
        )
        
        # === 向量分支 ===
        chunking_task = ChunkingOperator(chunk_size=512, chunk_overlap=50)
        embedding_task = EmbeddingOperator(embedding_model_name=getattr(config, 'embedding_model', None))
        vector_store_task = VectorStoreOperator()
        
        # === 结果聚合 ===
        aggregator_task = ResultAggregatorOperator()
        
        # 构建并行流程
        trigger_task >> parsing_task
        parsing_task >> extraction_task >> import_task
        parsing_task >> chunking_task >> embedding_task >> vector_store_task
        
        # 合并结果 - JoinOperator 需要 combine_function 来合并两个分支的输出
        def combine_results(triplet_result, vector_result):
            """合并图谱分支和向量分支的结果"""
            return [triplet_result, vector_result]
        
        join_task = JoinOperator(combine_function=combine_results)
        import_task >> join_task
        vector_store_task >> join_task
        join_task >> aggregator_task
        
    return dag


def create_kg_mapping_dag(connector: TuGraphConnector) -> DAG:
    """创建 Excel 列映射模式的 DAG（不使用 LLM，直接从列中提取三元组）"""
    
    with DAG("dbgpt_kg_mapping_workflow") as dag:
        # 0. 触发器 Operator - 接收 call_data (KGTaskContext with column_mapping)
        trigger_task = TriggerOperator()
        
        # 1. Excel 映射 Operator - 直接从 Excel 列中提取三元组
        mapping_task = ExcelMappingOperator()
        
        # 2. 导入 Operator
        import_task = TuGraphImportOperator(
            connector=connector,
            graph_name="default"  # 运行时从上下文获取
        )
        
        # 串联流: TriggerOperator -> ExcelMappingOperator -> TuGraphImportOperator
        # 跳过 LLM 提取步骤，更快更精确
        trigger_task >> mapping_task >> import_task
        
    return dag
