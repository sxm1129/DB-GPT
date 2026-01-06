-- Knowledge Graph Upload Service 数据库初始化脚本
-- 执行方式: mysql -h39.102.122.9 -usxm1129 -p dbgpt < init_kg_schema.sql

-- 创建任务表
CREATE TABLE IF NOT EXISTS knowledge_graph_upload_task (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id VARCHAR(64) UNIQUE NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    graph_space_name VARCHAR(128) NOT NULL,
    file_names JSON NOT NULL COMMENT '文件信息列表 [{name, size, type}]',
    total_files INT NOT NULL,
    workflow_config JSON COMMENT 'AWEL 工作流配置',
    excel_mode VARCHAR(32) DEFAULT 'auto' COMMENT 'Excel 处理模式: text|mapping|auto',
    custom_prompt TEXT COMMENT '自定义提取 Prompt',
    status VARCHAR(32) DEFAULT 'pending' COMMENT '任务状态: pending|running|completed|failed|cancelled',
    progress FLOAT DEFAULT 0.0 COMMENT '任务进度 0.0-1.0',
    current_file VARCHAR(255) COMMENT '当前处理的文件名',
    entities_count INT DEFAULT 0 COMMENT '提取的实体数量',
    relations_count INT DEFAULT 0 COMMENT '提取的关系数量',
    error_message TEXT COMMENT '错误信息',
    gmt_created DATETIME DEFAULT CURRENT_TIMESTAMP,
    gmt_modified DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    completed_at DATETIME COMMENT '完成时间',
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_created (gmt_created)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识图谱上传任务表';

-- 创建文件详情表
CREATE TABLE IF NOT EXISTS knowledge_graph_upload_file (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id VARCHAR(64) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(512) COMMENT '文件存储路径',
    file_size BIGINT COMMENT '文件大小（字节）',
    file_type VARCHAR(32) COMMENT '文件类型扩展名',
    status VARCHAR(32) DEFAULT 'pending' COMMENT '处理状态: pending|processing|completed|failed',
    progress FLOAT DEFAULT 0.0 COMMENT '处理进度 0.0-1.0',
    entities_extracted JSON COMMENT '提取的实体列表',
    relations_extracted JSON COMMENT '提取的关系列表',
    chunks_count INT DEFAULT 0 COMMENT '分块数量',
    processing_time_ms INT DEFAULT 0 COMMENT '处理耗时（毫秒）',
    error_detail TEXT COMMENT '错误详情',
    gmt_created DATETIME DEFAULT CURRENT_TIMESTAMP,
    gmt_modified DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES knowledge_graph_upload_task(task_id) ON DELETE CASCADE,
    INDEX idx_task_id (task_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识图谱上传文件详情表';

-- 验证表是否创建成功
SHOW TABLES LIKE 'knowledge_graph_upload%';
