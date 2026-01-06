#!/usr/bin/env python3
"""
DB-GPT 数据库初始化脚本
用于创建远程 MySQL 数据库并导入 Schema
"""

import os
import sys

# 数据库配置
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "39.102.122.9"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "sxm1129"),
    "password": os.getenv("DB_PASSWORD", "hs@A1b2c3d4e5"),
    "database": os.getenv("DB_NAME", "dbgpt"),
}

def check_pymysql():
    """检查并安装 PyMySQL"""
    try:
        import pymysql
        return pymysql
    except ImportError:
        print("正在安装 PyMySQL...")
        os.system(f"{sys.executable} -m pip install pymysql -q")
        import pymysql
        return pymysql


def create_database(pymysql):
    """创建数据库"""
    print(f"连接到 MySQL 服务器: {DB_CONFIG['user']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}")
    
    conn = pymysql.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        charset="utf8mb4",
    )
    
    try:
        with conn.cursor() as cursor:
            # 创建数据库
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            print(f"✅ 数据库 '{DB_CONFIG['database']}' 已创建/已存在")
        conn.commit()
    finally:
        conn.close()


def import_schema(pymysql):
    """导入 Schema"""
    schema_path = os.path.join(os.path.dirname(__file__), "assets/schema/dbgpt.sql")
    
    if not os.path.exists(schema_path):
        print(f"❌ Schema 文件未找到: {schema_path}")
        return False
    
    print(f"导入 Schema: {schema_path}")
    
    conn = pymysql.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        database=DB_CONFIG["database"],
        charset="utf8mb4",
    )
    
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            sql_content = f.read()
        
        # 分割 SQL 语句
        statements = []
        current_statement = []
        
        for line in sql_content.split("\n"):
            line = line.strip()
            if line.startswith("--") or not line:
                continue
            current_statement.append(line)
            if line.endswith(";"):
                statements.append(" ".join(current_statement))
                current_statement = []
        
        with conn.cursor() as cursor:
            success_count = 0
            skip_count = 0
            
            for stmt in statements:
                if not stmt.strip():
                    continue
                try:
                    cursor.execute(stmt)
                    success_count += 1
                except pymysql.err.OperationalError as e:
                    if "already exists" in str(e) or "1050" in str(e):
                        skip_count += 1
                    else:
                        print(f"⚠️ SQL 执行警告: {str(e)[:100]}")
                except Exception as e:
                    print(f"⚠️ SQL 执行警告: {str(e)[:100]}")
            
            conn.commit()
            print(f"✅ Schema 导入完成: {success_count} 条成功, {skip_count} 条已存在跳过")
        
        return True
    finally:
        conn.close()


def verify_tables(pymysql):
    """验证核心表是否存在"""
    core_tables = [
        "knowledge_space",
        "knowledge_document", 
        "document_chunk",
        "chat_history",
        "connect_config",
    ]
    
    conn = pymysql.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        database=DB_CONFIG["database"],
        charset="utf8mb4",
    )
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            print(f"\n📊 数据库 '{DB_CONFIG['database']}' 中共有 {len(existing_tables)} 张表")
            
            missing = [t for t in core_tables if t not in existing_tables]
            if missing:
                print(f"❌ 缺少核心表: {missing}")
                return False
            else:
                print("✅ 所有核心表已就绪")
                return True
    finally:
        conn.close()


def main():
    print("=" * 50)
    print("DB-GPT 数据库初始化")
    print("=" * 50)
    
    pymysql = check_pymysql()
    
    try:
        create_database(pymysql)
        import_schema(pymysql)
        verify_tables(pymysql)
        print("\n🎉 数据库初始化完成!")
        return 0
    except Exception as e:
        print(f"\n❌ 初始化失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
