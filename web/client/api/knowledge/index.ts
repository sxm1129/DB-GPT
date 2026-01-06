import { AddYuqueProps, RecallTestChunk, RecallTestProps, SearchDocumentParams } from '@/types/knowledge';
import { GET, POST } from '../index';

/**
 * 知识库编辑搜索
 */
export const searchDocumentList = (spaceName: string, data: SearchDocumentParams) => {
  return POST<SearchDocumentParams, { data: string[]; total: number; page: number }>(
    `/knowledge/${spaceName}/document/list`,
    data,
  );
};

/**
 * 上传语雀文档
 */
export const addYuque = (data: AddYuqueProps) => {
  return POST<AddYuqueProps, null>(`/knowledge/${data.space_name}/document/yuque/add`, data);
};

/**
 * 编辑知识库切片
 */
export const editChunk = (
  knowledgeName: string,
  data: { questions: string[]; doc_id: string | number; doc_name: string },
) => {
  return POST<{ questions: string[]; doc_id: string | number; doc_name: string }, null>(
    `/knowledge/${knowledgeName}/document/edit`,
    data,
  );
};
/**
 * 召回测试推荐问题
 */
export const recallTestRecommendQuestion = (id: string) => {
  return GET<{ id: string }, string[]>(`/knowledge/${id}/recommend_questions`);
};

/**
 * 召回方法选项
 */
export const recallMethodOptions = (id: string) => {
  return GET<{ id: string }, string[]>(`/knowledge/${id}/recall_retrievers`);
};
/**
 * 召回测试
 */
export const recallTest = (data: RecallTestProps, id: string) => {
  return POST<RecallTestProps, RecallTestChunk[]>(`/knowledge/${id}/recall_test`, data);
};

// chunk模糊搜索
export const searchChunk = (data: { document_id: string; content: string }, name: string) => {
  return POST<{ document_id: string; content: string }, string[]>(`/knowledge/${name}/chunk/list`, data);
};

// chunk添加问题
export const chunkAddQuestion = (data: { chunk_id: string; questions: string[] }) => {
  return POST<{ chunk_id: string; questions: string[] }, string[]>(`/knowledge/questions/chunk/edit`, data);
};

/**
 * 知识图谱相关接口 (Serve V2)
 */

interface KGTaskRequest {
  user_id?: string;
  graph_space_name: string;
  excel_mode?: string;
  custom_prompt?: string;
}

export interface KGTaskResponse {
  task_id: string;
  graph_space_name: string;
  status: string;
  progress: number;
  current_file?: string;
  total_files: number;
  entities_count: number;
  relations_count: number;
  file_names: any[];
  gmt_created: string;
  completed_at?: string;
  error_message?: string;
}

// 上传知识图谱文件请求
export const uploadKGFiles = (formData: FormData) => {
  return POST<FormData, KGTaskResponse>('/api/v2/serve/knowledge_graph/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000, // 5分钟超时
  });
};

// 获取任务列表
export const getKGTasks = (params: { user_id?: string; page?: number; page_size?: number; status?: string }) => {
  return GET<any, { tasks: KGTaskResponse[]; total: number; page: number }>('/api/v2/serve/knowledge_graph/tasks', params);
};

// 获取任务详情
export const getKGTaskDetail = (taskId: string) => {
  return GET<any, KGTaskResponse>(`/api/v2/serve/knowledge_graph/tasks/${taskId}`);
};

// 取消任务
export const cancelKGTask = (taskId: string) => {
  return POST<any, any>(`/api/v2/serve/knowledge_graph/tasks/${taskId}/cancel`);
};

// 获取 TuGraph 图空间列表
export const getGraphSpaces = () => {
  return GET<any, { spaces: string[] }>('/api/v2/serve/knowledge_graph/spaces');
};

// 创建新的图空间
export const createGraphSpace = (spaceName: string) => {
  return POST<{ space_name: string }, any>('/api/v2/serve/knowledge_graph/spaces', { space_name: spaceName });
};

// 删除任务
export const deleteKGTask = (taskId: string) => {
  return DELETE<any, any>(`/api/v2/serve/knowledge_graph/tasks/${taskId}`);
};

