import logging
from typing import Optional
from dbgpt.core.awel import DAG, JoinOperator, BaseOperator
from .operators import (
    FileParsingOperator,
    KGExtractionOperator,
    TuGraphImportOperator,
    KGTaskContext
)
from dbgpt.component import SystemApp, ComponentType
from dbgpt.model.cluster import WorkerManagerFactory
from dbgpt_ext.datasource.conn_tugraph import TuGraphConnector

logger = logging.getLogger(__name__)

def create_kg_dag(system_app: SystemApp, config: any, connector: TuGraphConnector) -> DAG:
    """创建并返回知识图谱构建 DAG"""
    
    with DAG("dbgpt_kg_upload_workflow") as dag:
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
            model_name=config.extraction_model or "qwen-max"
        )
        
        # 3. 导入 Operator
        # 注意：这里的 graph_name 将由输入上下文决定，或者由 Operator 内部动态处理
        # 暂时在 Operator 创建时传入，或者让 Operator 支持运行时从上下文获取
        import_task = TuGraphImportOperator(
            connector=connector,
            graph_name="default" # 初始占位，实际逻辑在 Operator 内部优化
        )
        
        # 串联流
        parsing_task >> extraction_task >> import_task
        
    return dag
