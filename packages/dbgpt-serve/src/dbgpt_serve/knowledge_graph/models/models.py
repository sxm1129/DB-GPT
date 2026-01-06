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
