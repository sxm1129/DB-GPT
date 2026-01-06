-- 知识图谱上传任务表
CREATE TABLE IF NOT EXISTS knowledge_graph_upload_task (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id VARCHAR(64) UNIQUE NOT NULL COMMENT '任务唯一ID',
    user_id VARCHAR(64) NOT NULL COMMENT '用户ID',
    graph_space_name VARCHAR(128) NOT NULL COMMENT 'TuGraph 库名',
    
    -- 文件信息
    file_names JSON NOT NULL COMMENT '文件列表 [{name, size, type}]',
    total_files INT NOT NULL COMMENT '文件总数',
    
    -- 配置参数
    workflow_config JSON COMMENT 'AWEL 工作流配置',
    excel_mode VARCHAR(32) DEFAULT 'auto' COMMENT 'Excel处理模式',
    custom_prompt TEXT COMMENT '自定义提取Prompt',
    
    -- 任务状态
    status VARCHAR(32) DEFAULT 'pending' COMMENT '任务状态: pending, running, completed, failed, cancelled',
    progress FLOAT DEFAULT 0 COMMENT '进度 0-100',
    current_file VARCHAR(255) COMMENT '当前处理文件',
    
    -- 结果统计
    entities_count INT DEFAULT 0 COMMENT '提取的实体数',
    relations_count INT DEFAULT 0 COMMENT '提取的关系数',
    error_message TEXT COMMENT '错误信息',
    
    -- 时间戳
    gmt_created DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    gmt_modified DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    completed_at DATETIME NULL COMMENT '完成时间',
    
    INDEX idx_user_created (user_id, gmt_created),
    INDEX idx_status (status),
    INDEX idx_graph_space (graph_space_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识图谱上传任务表';

-- 知识图谱上传详情表（每个文件一条记录）
CREATE TABLE IF NOT EXISTS knowledge_graph_upload_file (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id VARCHAR(64) NOT NULL COMMENT '关联任务ID',
    file_name VARCHAR(255) NOT NULL COMMENT '文件名',
    file_path VARCHAR(512) COMMENT '存储路径',
    file_size BIGINT COMMENT '文件大小(字节)',
    file_type VARCHAR(32) COMMENT '文件类型',
    
    -- 处理状态
    status VARCHAR(32) DEFAULT 'pending' COMMENT '处理状态: pending, processing, completed, failed',
    progress FLOAT DEFAULT 0 COMMENT '处理进度',
    
    -- 处理结果
    entities_extracted JSON COMMENT '提取的实体列表',
    relations_extracted JSON COMMENT '提取的关系列表',
    chunks_count INT DEFAULT 0 COMMENT '文本分块数',
    processing_time_ms INT DEFAULT 0 COMMENT '处理耗时(毫秒)',
    error_detail TEXT COMMENT '错误详情',
    
    gmt_created DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    gmt_modified DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    
    INDEX idx_task (task_id),
    CONSTRAINT fk_kg_upload_task FOREIGN KEY (task_id) REFERENCES knowledge_graph_upload_task(task_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='文件处理详情表';
