# xSmartKG API 文档

## 概述

xSmartKG 是 DB-GPT 的知识图谱上传和构建服务，支持多种文件格式上传，通过 LLM 或用户配置的映射规则自动提取实体和关系。

**Base URL**: `/api/v2/serve/knowledge_graph`

---

## 接口列表

### 1. 上传文件并创建任务

**POST** `/upload`

上传文件并启动知识图谱构建任务。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| files | File[] | ✅ | 上传的文件，支持 .txt, .md, .docx, .pdf, .xlsx, .xls |
| graph_space_name | string | ✅ | 图空间名称 |
| excel_mode | string | ❌ | Excel 处理模式: `auto` (默认) 或 `mapping` |
| custom_prompt | string | ❌ | 自定义实体关系提取 Prompt |
| user_id | string | ❌ | 用户 ID |

#### 请求示例

```bash
curl -X POST "http://localhost:5670/api/v2/serve/knowledge_graph/upload" \
  -F "files=@company.xlsx" \
  -F "graph_space_name=my_kg" \
  -F "excel_mode=auto"
```

#### 响应示例

```json
{
  "task_id": "abc123...",
  "graph_space_name": "my_kg",
  "status": "pending",
  "progress": 0.0,
  "total_files": 1,
  "entities_count": 0,
  "relations_count": 0,
  "gmt_created": "2026-01-06 10:00:00"
}
```

---

### 2. 获取任务详情

**GET** `/tasks/{task_id}`

#### 响应示例

```json
{
  "task_id": "abc123...",
  "status": "completed",
  "progress": 100.0,
  "entities_count": 42,
  "relations_count": 35,
  "completed_at": "2026-01-06 10:05:00"
}
```

---

### 3. 获取任务列表

**GET** `/tasks`

| 参数 | 说明 |
|------|------|
| user_id | 用户 ID |
| page | 页码 (默认 1) |
| limit | 每页数量 (默认 20) |

---

### 4. 取消任务

**POST** `/tasks/{task_id}/cancel`

---

### 5. 获取图空间列表

**GET** `/spaces`

#### 响应示例

```json
{
  "spaces": ["default", "my_kg", "company_relations"]
}
```

---

### 6. WebSocket 实时进度

**WS** `/ws/task/{task_id}`

连接后将实时收到任务进度更新：

```json
{
  "status": "running",
  "progress": 0.5,
  "message": "Processing file 1/2",
  "entities_count": 20,
  "relations_count": 15
}
```

---

## 错误码

| 状态码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 404 | 任务不存在 |
| 500 | 服务器内部错误 |
| 503 | TuGraph 连接失败 |

---

## 支持的文件类型

| 格式 | 说明 |
|------|------|
| .txt | 纯文本文件 |
| .md | Markdown 文件 |
| .docx | Word 文档 |
| .pdf | PDF 文档 |
| .xlsx | Excel 2007+ |
| .xls | Excel 97-2003 |
