#!/bin/bash
# DB-GPT 本地开发环境启动脚本
# 使用方法: source setup_env.sh && ./start_dev.sh

# ==========================================
# 环境变量配置
# ==========================================

# 阿里百炼 API
export ALI_APIKEY="sk-a9aa1d2df0f946259fa4b70291ffb1ae"

# OpenRouter API (可选)
export OPENROUTER_API_KEY=""  # 如果有 OpenRouter key，填入此处

# MySQL 数据库配置
export DB_HOST="39.102.122.9"
export DB_PORT="3306"
export DB_USER="sxm1129"
export DB_PASSWORD="hs@A1b2c3d4e5"
export DB_NAME="dbgpt"

# DB-GPT 语言设置
export DBGPT_LANG="zh"

echo "✅ 环境变量已设置完成"
echo "数据库: ${DB_USER}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
echo "模型: 阿里百炼 qwen-turbo"
