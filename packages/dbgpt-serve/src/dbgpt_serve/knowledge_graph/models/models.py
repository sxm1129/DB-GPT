from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, Enum, JSON, ForeignKey, BIGINT
from sqlalchemy.orm import relationship

from dbgpt._private.pydantic import model_to_dict
from dbgpt.storage.metadata import BaseDao, Model

class KGUploadTaskEntity(Model):
    __tablename__ = "knowledge_graph_upload_task"
    id = Column(BIGINT, primary_key=True, autoincrement=True)
    task_id = Column(String(64), unique=True, nullable=False)
    user_id = Column(String(64), nullable=False)
    graph_space_name = Column(String(128), nullable=False)
    
    # 文件信息
    file_names = Column(JSON, nullable=False)  # [{name, size, type}]
    total_files = Column(Integer, nullable=False)
    
    # 配置参数
    workflow_config = Column(JSON)
    excel_mode = Column(String(32), default="auto")  # text | mapping | auto
    custom_prompt = Column(Text)
    
    # 任务状态
    status = Column(String(32), default="pending")  # pending, running, completed, failed, cancelled
    progress = Column(Float, default=0.0)
    current_file = Column(String(255))
    
    # 结果统计
    entities_count = Column(Integer, default=0)
    relations_count = Column(Integer, default=0)
    error_message = Column(Text)
    
    # 时间戳
    gmt_created = Column(DateTime, default=datetime.now)
    gmt_modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    completed_at = Column(DateTime)

    def __repr__(self):
        return f"KGUploadTaskEntity(task_id='{self.task_id}', status='{self.status}', progress={self.progress})"

class KGUploadFileEntity(Model):
    __tablename__ = "knowledge_graph_upload_file"
    id = Column(BIGINT, primary_key=True, autoincrement=True)
    task_id = Column(String(64), ForeignKey("knowledge_graph_upload_task.task_id", ondelete="CASCADE"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(512))
    file_size = Column(BIGINT)
    file_type = Column(String(32))
    
    # 处理状态
    status = Column(String(32), default="pending")  # pending, processing, completed, failed
    progress = Column(Float, default=0.0)
    
    # 处理结果
    entities_extracted = Column(JSON)
    relations_extracted = Column(JSON)
    chunks_count = Column(Integer, default=0)
    processing_time_ms = Column(Integer, default=0)
    error_detail = Column(Text)
    
    gmt_created = Column(DateTime, default=datetime.now)
    gmt_modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class KGUploadTaskDao(BaseDao):
    def create_task(self, entity: KGUploadTaskEntity):
        session = self.get_raw_session()
        session.add(entity)
        session.commit()
        session.refresh(entity)  # 刷新确保所有属性都被加载
        session.expunge(entity)  # 从 session 分离实体
        session.close()
        return entity.task_id


    def get_task(self, task_id: str) -> Optional[KGUploadTaskEntity]:
        session = self.get_raw_session()
        task = session.query(KGUploadTaskEntity).filter(KGUploadTaskEntity.task_id == task_id).first()
        if task:
            session.expunge(task)
        session.close()
        return task

    def update_task(self, task_id: str, update_data: Dict[str, Any]):
        session = self.get_raw_session()
        session.query(KGUploadTaskEntity).filter(KGUploadTaskEntity.task_id == task_id).update(update_data)
        session.commit()
        session.close()

    def list_tasks(self, user_id: str, page: int = 1, limit: int = 20, status: Optional[str] = None):
        session = self.get_raw_session()
        query = session.query(KGUploadTaskEntity).filter(KGUploadTaskEntity.user_id == user_id)
        if status:
            query = query.filter(KGUploadTaskEntity.status == status)
        total = query.count()
        tasks = query.order_by(KGUploadTaskEntity.gmt_created.desc()).offset((page - 1) * limit).limit(limit).all()
        for task in tasks:
            session.expunge(task)
        session.close()
        return tasks, total

    def delete_task(self, task_id: str):
        """删除任务"""
        session = self.get_raw_session()
        session.query(KGUploadTaskEntity).filter(KGUploadTaskEntity.task_id == task_id).delete()
        session.commit()
        session.close()


class KGUploadFileDao(BaseDao):
    def create_file_detail(self, entity: KGUploadFileEntity):
        session = self.get_raw_session()
        session.add(entity)
        session.commit()
        session.close()

    def update_file_detail(self, task_id: str, file_name: str, update_data: Dict[str, Any]):
        session = self.get_raw_session()
        session.query(KGUploadFileEntity).filter(
            KGUploadFileEntity.task_id == task_id,
            KGUploadFileEntity.file_name == file_name
        ).update(update_data)
        session.commit()
        session.close()

    def get_files_by_task(self, task_id: str) -> List[KGUploadFileEntity]:
        session = self.get_raw_session()
        files = session.query(KGUploadFileEntity).filter(KGUploadFileEntity.task_id == task_id).all()
        session.close()
        return files


class KGPromptTemplateEntity(Model):
    """提示词模板实体 - 用于知识图谱三元组提取的自定义提示词"""
    __tablename__ = "kg_prompt_template"
    
    id = Column(BIGINT, primary_key=True, autoincrement=True)
    name = Column(String(128), unique=True, nullable=False, comment="模板名称")
    description = Column(Text, comment="模板描述")
    prompt_content = Column(Text, nullable=False, comment="提示词内容，支持变量占位符如 {domain}")
    
    # 变量定义：[{name, type, options, default, description}]
    # type: "text" | "select"
    # options: 仅 select 类型时使用，如 ["中文", "English"]
    variables = Column(JSON, comment="变量定义列表")
    
    # 模板属性
    is_system = Column(Integer, default=0, comment="是否为系统预置模板: 0=用户, 1=系统")
    user_id = Column(String(128), comment="创建用户ID，系统模板为 NULL")
    
    # 时间戳
    gmt_created = Column(DateTime, default=datetime.now)
    gmt_modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"KGPromptTemplateEntity(id={self.id}, name='{self.name}', is_system={self.is_system})"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "prompt_content": self.prompt_content,
            "variables": self.variables or [],
            "is_system": bool(self.is_system),
            "user_id": self.user_id,
            "gmt_created": self.gmt_created.strftime("%Y-%m-%d %H:%M:%S") if self.gmt_created else None,
            "gmt_modified": self.gmt_modified.strftime("%Y-%m-%d %H:%M:%S") if self.gmt_modified else None,
        }


class KGPromptTemplateDao(BaseDao):
    """提示词模板 DAO"""
    
    def create_template(self, entity: KGPromptTemplateEntity) -> int:
        """创建模板，返回 ID"""
        session = self.get_raw_session()
        session.add(entity)
        session.commit()
        template_id = entity.id
        session.close()
        return template_id
    
    def get_template_by_id(self, template_id: int) -> Optional[KGPromptTemplateEntity]:
        """根据 ID 获取模板"""
        session = self.get_raw_session()
        template = session.query(KGPromptTemplateEntity).filter(
            KGPromptTemplateEntity.id == template_id
        ).first()
        if template:
            session.expunge(template)
        session.close()
        return template
    
    def get_template_by_name(self, name: str) -> Optional[KGPromptTemplateEntity]:
        """根据名称获取模板"""
        session = self.get_raw_session()
        template = session.query(KGPromptTemplateEntity).filter(
            KGPromptTemplateEntity.name == name
        ).first()
        if template:
            session.expunge(template)
        session.close()
        return template
    
    def list_templates(self, user_id: Optional[str] = None, include_system: bool = True) -> List[KGPromptTemplateEntity]:
        """列出模板
        
        Args:
            user_id: 用户ID，如果提供则返回该用户的自定义模板
            include_system: 是否包含系统模板
        """
        session = self.get_raw_session()
        query = session.query(KGPromptTemplateEntity)
        
        conditions = []
        if include_system:
            conditions.append(KGPromptTemplateEntity.is_system == 1)
        if user_id:
            conditions.append(KGPromptTemplateEntity.user_id == user_id)
        
        if conditions:
            from sqlalchemy import or_
            query = query.filter(or_(*conditions))
        
        templates = query.order_by(
            KGPromptTemplateEntity.is_system.desc(),  # 系统模板在前
            KGPromptTemplateEntity.gmt_created.desc()
        ).all()
        
        for t in templates:
            session.expunge(t)
        session.close()
        return templates
    
    def update_template(self, template_id: int, update_data: Dict[str, Any]) -> bool:
        """更新模板"""
        session = self.get_raw_session()
        result = session.query(KGPromptTemplateEntity).filter(
            KGPromptTemplateEntity.id == template_id
        ).update(update_data)
        session.commit()
        session.close()
        return result > 0
    
    def delete_template(self, template_id: int, user_id: str) -> bool:
        """删除模板（仅允许删除用户自己的非系统模板）"""
        session = self.get_raw_session()
        result = session.query(KGPromptTemplateEntity).filter(
            KGPromptTemplateEntity.id == template_id,
            KGPromptTemplateEntity.is_system == 0,
            KGPromptTemplateEntity.user_id == user_id
        ).delete()
        session.commit()
        session.close()
        return result > 0
    
    def init_system_templates(self) -> int:
        """初始化系统预置模板，返回创建的数量"""
        session = self.get_raw_session()
        
        # 检查是否已初始化
        existing = session.query(KGPromptTemplateEntity).filter(
            KGPromptTemplateEntity.is_system == 1
        ).count()
        if existing > 0:
            session.close()
            return 0
        
        # 预置模板定义
        system_templates = [
            {
                "name": "通用知识提取",
                "description": "适用于大多数文档的通用知识图谱提取模板",
                "prompt_content": """你是一个知识图谱专家。请从以下文本中提取实体和关系，以三元组形式返回。

要求：
1. 提取的实体应该是名词或名词短语
2. 关系应该简洁明了
3. 返回格式为 JSON 数组：[["实体1", "关系", "实体2"], ...]
4. 语言：{language}

文本内容：
{text}

请仅返回 JSON 数组，不要包含其他解释。""",
                "variables": [
                    {"name": "language", "type": "select", "options": ["中文", "English"], "default": "中文", "description": "输出语言"}
                ]
            },
            {
                "name": "技术文档提取",
                "description": "适用于技术文档、API 文档的知识提取",
                "prompt_content": """你是一个技术领域的知识图谱专家。请从以下技术文档中提取实体和关系。

领域：{tech_domain}
语言：{language}

重点关注：
- 技术概念之间的依赖关系
- 组件与功能的包含关系
- 参数与配置的属性关系

返回格式为 JSON 数组：[["实体1", "关系", "实体2"], ...]

文本内容：
{text}

请仅返回 JSON 数组。""",
                "variables": [
                    {"name": "language", "type": "select", "options": ["中文", "English"], "default": "中文", "description": "输出语言"},
                    {"name": "tech_domain", "type": "text", "default": "软件开发", "description": "技术领域"}
                ]
            },
            {
                "name": "医疗知识提取",
                "description": "适用于医学文献、临床指南的知识提取",
                "prompt_content": """你是一个医学领域的知识图谱专家。请从以下医学文本中提取实体和关系。

专科领域：{specialty}
语言：{language}

重点关注：
- 疾病与症状的关系
- 药物与疾病的治疗关系
- 检查与诊断的关系

返回格式为 JSON 数组：[["实体1", "关系", "实体2"], ...]

文本内容：
{text}

请仅返回 JSON 数组。""",
                "variables": [
                    {"name": "language", "type": "select", "options": ["中文", "English"], "default": "中文", "description": "输出语言"},
                    {"name": "specialty", "type": "text", "default": "内科", "description": "医学专科"}
                ]
            },
            {
                "name": "金融知识提取",
                "description": "适用于金融报告、财务分析的知识提取",
                "prompt_content": """你是一个金融领域的知识图谱专家。请从以下金融文本中提取实体和关系。

报告类型：{report_type}
语言：{language}

重点关注：
- 公司与公司的投资/合作关系
- 公司与产品/业务的关系
- 财务指标与业绩的关系

返回格式为 JSON 数组：[["实体1", "关系", "实体2"], ...]

文本内容：
{text}

请仅返回 JSON 数组。""",
                "variables": [
                    {"name": "language", "type": "select", "options": ["中文", "English"], "default": "中文", "description": "输出语言"},
                    {"name": "report_type", "type": "select", "options": ["年报", "季报", "研报", "其他"], "default": "年报", "description": "报告类型"}
                ]
            }
        ]
        
        created_count = 0
        for tpl in system_templates:
            entity = KGPromptTemplateEntity(
                name=tpl["name"],
                description=tpl["description"],
                prompt_content=tpl["prompt_content"],
                variables=tpl["variables"],
                is_system=1,
                user_id=None
            )
            session.add(entity)
            created_count += 1
        
        session.commit()
        session.close()
        return created_count
