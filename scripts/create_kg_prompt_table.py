#!/usr/bin/env python3
"""Create kg_prompt_template table in MySQL"""
import pymysql

conn = pymysql.connect(
    host='39.102.122.9',
    port=3306,
    user='sxm1129',
    password='hs@A1b2c3d4e5',
    database='dbgpt',
    charset='utf8mb4'
)

cursor = conn.cursor()

create_sql = """
CREATE TABLE IF NOT EXISTS kg_prompt_template (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(128) NOT NULL UNIQUE COMMENT '模板名称',
    description TEXT COMMENT '模板描述',
    prompt_content TEXT NOT NULL COMMENT '提示词内容',
    variables JSON COMMENT '变量定义列表',
    is_system INT DEFAULT 0 COMMENT '是否为系统预置模板: 0=用户, 1=系统',
    user_id VARCHAR(128) COMMENT '创建用户ID',
    gmt_created DATETIME DEFAULT CURRENT_TIMESTAMP,
    gmt_modified DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

cursor.execute(create_sql)
conn.commit()

# Verify
cursor.execute("SHOW TABLES LIKE 'kg_prompt%'")
result = cursor.fetchall()
print("Tables created:", result)

cursor.close()
conn.close()
print("Done!")
