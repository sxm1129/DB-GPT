from typing import List, Optional, Any, Dict
from dbgpt._private.pydantic import BaseModel, Field


class RelationMappingConfig(BaseModel):
    """关系映射配置：定义如何从 Excel 列中提取关系"""
    subject_column: str = Field(..., description="主体实体所在的列名")
    predicate: str = Field(..., description="关系谓词（如'负责人是'、'属于'等）")
    object_column: str = Field(..., description="客体实体所在的列名")


class ExcelColumnMapping(BaseModel):
    """Excel 列映射配置：用于直接从 Excel 列中提取实体和关系"""
    entity_columns: List[str] = Field(default=[], description="作为实体提取的列名列表")
    relation_configs: List[RelationMappingConfig] = Field(
        default=[], 
        description="关系提取配置列表，支持多种关系类型"
    )


class KGUploadTaskCreateRequest(BaseModel):
    graph_space_name: str = Field(..., description="TuGraph Graph Space name")
    excel_mode: str = Field("auto", description="Excel process mode: text, mapping, auto")
    column_mapping: Optional[ExcelColumnMapping] = Field(None, description="Excel column mapping config (only for mapping mode)")
    custom_prompt: Optional[str] = Field(None, description="Custom extraction prompt")
    workflow_config: Optional[Dict[str, Any]] = Field(None, description="AWEL workflow config")
    user_id: Optional[str] = Field(None, description="User ID")

class FileInfoVO(BaseModel):
    name: str = Field(..., description="File name")
    size: int = Field(..., description="File size in bytes")
    type: str = Field(..., description="File type/extension")
    status: Optional[str] = Field("pending", description="Status of this file")
    progress: Optional[float] = Field(0.0, description="Progress of this file")

class KGUploadTaskResponse(BaseModel):
    task_id: str = Field(..., description="Unique task ID")
    graph_space_name: str = Field(..., description="Graph Space name")
    status: str = Field(..., description="Task status")
    progress: float = Field(0.0, description="Overall progress (0-100)")
    current_file: Optional[str] = Field(None, description="Current processing file")
    total_files: int = Field(0, description="Total files")
    entities_count: int = Field(0, description="Total entities extracted")
    relations_count: int = Field(0, description="Total relations extracted")
    file_names: List[FileInfoVO] = Field([], description="File list info")
    gmt_created: str = Field(..., description="Create time")
    completed_at: Optional[str] = Field(None, description="Complete time")
    error_message: Optional[str] = Field(None, description="Error message if failed")

class KGUploadFileResponse(BaseModel):
    file_name: str = Field(..., description="File name")
    status: str = Field(..., description="Status of this file")
    progress: float = Field(..., description="Progress of this file")
    entities_count: int = Field(0, description="Entities extracted from this file")
    relations_count: int = Field(0, description="Relations extracted from this file")
    chunks_count: int = Field(0, description="Text chunks count")
    processing_time_ms: int = Field(0, description="Processing time in ms")
    error_detail: Optional[str] = Field(None, description="Error detail if failed")

class KGUploadTaskListResponse(BaseModel):
    tasks: List[KGUploadTaskResponse] = Field(..., description="Task list")
    total: int = Field(..., description="Total count")
    page: int = Field(..., description="Current page")
