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


# ============ Prompt Template Schemas ============

class TemplateVariableVO(BaseModel):
    """模板变量定义"""
    name: str = Field(..., description="变量名称，如 'language'")
    type: str = Field("text", description="变量类型: 'text' 或 'select'")
    options: Optional[List[str]] = Field(None, description="select 类型时的可选项列表")
    default: Optional[str] = Field(None, description="默认值")
    description: Optional[str] = Field(None, description="变量描述")


class KGPromptTemplateCreateRequest(BaseModel):
    """创建/更新模板请求"""
    name: str = Field(..., description="模板名称，需唯一")
    description: Optional[str] = Field(None, description="模板描述")
    prompt_content: str = Field(..., description="提示词内容，支持变量占位符如 {domain}")
    variables: Optional[List[TemplateVariableVO]] = Field(None, description="变量定义列表")


class KGPromptTemplateResponse(BaseModel):
    """模板响应"""
    id: int = Field(..., description="模板ID")
    name: str = Field(..., description="模板名称")
    description: Optional[str] = Field(None, description="模板描述")
    prompt_content: str = Field(..., description="提示词内容")
    variables: List[TemplateVariableVO] = Field([], description="变量定义列表")
    is_system: bool = Field(False, description="是否为系统预置模板")
    user_id: Optional[str] = Field(None, description="创建用户ID")
    gmt_created: Optional[str] = Field(None, description="创建时间")
    gmt_modified: Optional[str] = Field(None, description="修改时间")


class KGPromptTemplateListResponse(BaseModel):
    """模板列表响应"""
    templates: List[KGPromptTemplateResponse] = Field(..., description="模板列表")
    total: int = Field(..., description="总数")


# ============ Smart KG Builder Schemas ============

class KGBuildUploadRequest(BaseModel):
    """智能图谱构建 - 上传请求"""
    space_name: str = Field(..., description="目标知识库空间名称")
    chunk_size: int = Field(500, description="切片大小 (tokens)")
    chunk_overlap: int = Field(50, description="切片重叠 (tokens)")


class KGBuildExtractRequest(BaseModel):
    """智能图谱构建 - 三元组提取请求"""
    task_id: str = Field(..., description="任务ID")
    template_id: Optional[int] = Field(None, description="使用的模板ID")
    custom_prompt: Optional[str] = Field(None, description="自定义提示词（优先于模板）")
    variable_values: Optional[Dict[str, str]] = Field(None, description="模板变量值")
    preview_limit: int = Field(50, description="预览显示的最大三元组数量")


class TripletVO(BaseModel):
    """三元组值对象"""
    subject: str = Field(..., description="主体实体")
    predicate: str = Field(..., description="关系")
    object: str = Field(..., description="客体实体")
    source_chunk: Optional[str] = Field(None, description="来源文本片段")


class KGBuildExtractResponse(BaseModel):
    """智能图谱构建 - 三元组提取预览响应"""
    task_id: str = Field(..., description="任务ID")
    triplets: List[TripletVO] = Field([], description="提取的三元组（预览）")
    total_triplets: int = Field(0, description="三元组总数")
    preview_limit: int = Field(50, description="预览限制")
    chunks_processed: int = Field(0, description="已处理的切片数")
    total_chunks: int = Field(0, description="总切片数")


class KGBuildConfirmRequest(BaseModel):
    """智能图谱构建 - 确认写入请求"""
    task_id: str = Field(..., description="任务ID")
    

class KGBuildStatusResponse(BaseModel):
    """智能图谱构建 - 任务状态响应"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态: pending, parsing, chunking, extracting, previewing, confirming, completed, failed")
    progress: float = Field(0.0, description="总体进度 (0-100)")
    current_step: str = Field("", description="当前步骤描述")
    files: List[FileInfoVO] = Field([], description="文件列表")
    triplets_count: int = Field(0, description="已提取三元组数")
    error_message: Optional[str] = Field(None, description="错误信息")

