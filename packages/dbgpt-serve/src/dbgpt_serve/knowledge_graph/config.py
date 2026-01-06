from dataclasses import dataclass, field
from typing import Optional

from dbgpt.core.awel.flow import (
    TAGS_ORDER_HIGH,
    ResourceCategory,
    auto_register_resource,
)
from dbgpt.util.i18n_utils import _
from dbgpt_serve.core import BaseServeConfig

APP_NAME = "knowledge_graph"
SERVE_APP_NAME = "dbgpt_serve_knowledge_graph"
SERVE_APP_NAME_HUMP = "dbgpt_serve_knowledge_graph"
SERVE_CONFIG_KEY_PREFIX = "dbgpt.serve.knowledge_graph"
SERVE_SERVICE_COMPONENT_NAME = f"{SERVE_APP_NAME}_service"

@auto_register_resource(
    label=_("Knowledge Graph Serve Configurations"),
    category=ResourceCategory.KNOWLEDGE_GRAPH,
    tags={"order": TAGS_ORDER_HIGH},
    description=_("This configuration is for the knowledge graph serve module."),
    show_in_ui=False,
)
@dataclass
class ServeConfig(BaseServeConfig):
    """Parameters for the knowledge graph serve command"""

    __type__ = APP_NAME

    # 默认三元组提取模型
    default_llm_model: Optional[str] = field(
        default="qwen-max",
        metadata={"help": _("Default LLM model for triplet extraction")},
    )
    
    # 图谱构建参数
    max_chunks_once_load: Optional[int] = field(
        default=5,
        metadata={"help": _("Max chunks to process in one batch")},
    )
