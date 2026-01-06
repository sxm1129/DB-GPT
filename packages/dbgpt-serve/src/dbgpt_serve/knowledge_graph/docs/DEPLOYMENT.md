# xSmartKG 部署配置

## 环境变量

```bash
# TuGraph 连接配置
TUGRAPH_HOST=localhost
TUGRAPH_PORT=7687
TUGRAPH_USER=admin
TUGRAPH_PASSWORD=your_password

# LLM 配置 (使用通义千问示例)
LLM_PROVIDER=tongyi
TONGYI_API_KEY=sk-xxxxx

# 数据库配置
LOCAL_DB_TYPE=mysql
LOCAL_DB_HOST=127.0.0.1
LOCAL_DB_PORT=3306
LOCAL_DB_USER=root
LOCAL_DB_PASSWORD=your_password
LOCAL_DB_NAME=dbgpt
```

## 数据库初始化

执行以下 SQL 初始化知识图谱上传任务表：

```sql
-- 见 init_kg_schema.sql
CREATE TABLE IF NOT EXISTS kg_upload_tasks (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(64) NOT NULL UNIQUE,
    user_id VARCHAR(64) DEFAULT 'default',
    graph_space_name VARCHAR(128) NOT NULL,
    status VARCHAR(32) DEFAULT 'pending',
    progress FLOAT DEFAULT 0.0,
    current_file VARCHAR(256),
    total_files INT DEFAULT 0,
    entities_count INT DEFAULT 0,
    relations_count INT DEFAULT 0,
    file_names JSON,
    error_message TEXT,
    gmt_created DATETIME DEFAULT CURRENT_TIMESTAMP,
    gmt_modified DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    completed_at DATETIME,
    INDEX idx_task_id (task_id),
    INDEX idx_user_id (user_id),
    INDEX idx_status (status)
);
```

## Nginx 配置示例

```nginx
location /api/v2/serve/knowledge_graph {
    proxy_pass http://127.0.0.1:5670;
    proxy_http_version 1.1;
    
    # WebSocket 支持
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    
    # 上传文件大小限制
    client_max_body_size 100M;
    
    # 超时设置
    proxy_read_timeout 300s;
    proxy_connect_timeout 60s;
}
```

## Docker Compose (可选)

```yaml
version: '3.8'
services:
  dbgpt:
    image: dbgpt/dbgpt:latest
    ports:
      - "5670:5670"
    environment:
      - TUGRAPH_HOST=tugraph
      - LLM_PROVIDER=tongyi
    depends_on:
      - mysql
      - tugraph

  tugraph:
    image: tugraph/tugraph-runtime:latest
    ports:
      - "7687:7687"

  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: root
      MYSQL_DATABASE: dbgpt
```
