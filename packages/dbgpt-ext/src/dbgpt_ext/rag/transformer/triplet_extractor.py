"""TripletExtractor class."""

import logging
import re
from typing import Any, List, Optional, Tuple

from dbgpt.core import LLMClient
from dbgpt.rag.transformer.llm_extractor import LLMExtractor

logger = logging.getLogger(__name__)

TRIPLET_EXTRACT_PT = (
    "## 角色\n"
    "你是一个专业的知识图谱工程师，擅长从文本中精确抽取结构化的三元组知识。\n"
    "\n"
    "## 任务\n"
    "从给定文本中提取尽可能多的知识三元组，格式为 (主体, 谓词/关系, 客体)。\n"
    "\n"
    "## 抽取规则\n"
    "1. **实体识别**: 识别所有有意义的实体（人名、地名、组织、概念、事件、产品等）\n"
    "2. **关系抽取**: 识别实体间的各类关系（包含、属于、创建、位于、发生时间等）\n"
    "3. **属性提取**: 将实体的属性也转化为三元组，如 (实体, 属性名, 属性值)\n"
    "4. **层级关系**: 识别上下级、部分整体、类别实例等层级关系\n"
    "5. **时间事件**: 识别时间相关信息，如 (事件, 发生时间, 日期)\n"
    "\n"
    "## 关系类型参考\n"
    "- 层级关系: 包含、属于、是一种、部分\n"
    "- 空间关系: 位于、来自、前往\n"
    "- 时间关系: 发生于、开始于、结束于、创建于\n"
    "- 社会关系: 创建者、拥有者、成员、员工、合作者\n"
    "- 属性关系: 名称、类型、数量、特征、用途\n"
    "- 因果关系: 导致、影响、依赖、需要\n"
    "\n"
    "## 约束条件\n"
    "- 主体和客体必须是具体的实体或概念，不能为空\n"
    "- 谓词应简洁明确，使用动词或动词短语\n"
    "- 避免使用过于宽泛的词汇如\"是\"、\"有\"，尽量具体化\n"
    "- 同一信息可以从不同角度提取多个三元组\n"
    "- 数字信息也需要提取，如 (公司, 员工数量, 1000人)\n"
    "\n"
    "## 输出格式\n"
    "每个三元组占一行，格式: (主体, 谓词, 客体)\n"
    "\n"
    "## 示例\n"
    "文本: 腾讯公司于1998年在深圳成立，创始人是马化腾，主要产品包括微信和QQ。\n"
    "三元组:\n"
    "(腾讯公司, 成立时间, 1998年)\n"
    "(腾讯公司, 成立地点, 深圳)\n"
    "(腾讯公司, 创始人, 马化腾)\n"
    "(马化腾, 创立, 腾讯公司)\n"
    "(腾讯公司, 主要产品, 微信)\n"
    "(腾讯公司, 主要产品, QQ)\n"
    "(微信, 开发商, 腾讯公司)\n"
    "(QQ, 开发商, 腾讯公司)\n"
    "---------------------\n"
    "文本: {text}\n"
    "三元组:\n"
)


class TripletExtractor(LLMExtractor):
    """TripletExtractor class."""

    def __init__(self, llm_client: LLMClient, model_name: str):
        """Initialize the TripletExtractor."""
        super().__init__(llm_client, model_name, TRIPLET_EXTRACT_PT)

    def _parse_response(
        self, text: str, limit: Optional[int] = None
    ) -> List[Tuple[Any, ...]]:
        triplets = []

        for line in text.split("\n"):
            for match in re.findall(r"\((.*?)\)", line):
                splits = match.split(",")
                parts = [split.strip() for split in splits if split.strip()]
                if len(parts) == 3:
                    parts = [
                        p.strip(
                            "`~!@#$%^&*()-=+[]\\{}|;':\",./<>?"
                            "·！￥&*（）—【】、「」；‘’：“”，。、《》？"
                        )
                        for p in parts
                    ]
                    triplets.append(tuple(parts))
                    if limit and len(triplets) >= limit:
                        return triplets

        return triplets
