import logging
from typing import Optional
from dbgpt.core.awel import DAG, JoinOperator, BaseOperator, TriggerOperator
from .operators import (
    FileParsingOperator,
    KGExtractionOperator,
    TuGraphImportOperator,
    ExcelMappingOperator,
    KGTaskContext
)
from dbgpt.component import SystemApp, ComponentType
from dbgpt.model.cluster import WorkerManagerFactory
from dbgpt_ext.datasource.conn_tugraph import TuGraphConnector

logger = logging.getLogger(__name__)

def create_kg_dag(system_app: SystemApp, config: any, connector: TuGraphConnector) -> DAG:
    """创建并返回知识图谱构建 DAG（LLM 提取模式）"""
    
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
        
        # 串联流: TriggerOperator -> FileParsingOperator -> KGExtractionOperator -> TuGraphImportOperator
        trigger_task >> parsing_task >> extraction_task >> import_task
        
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
