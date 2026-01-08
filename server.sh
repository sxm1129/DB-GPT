#!/bin/bash

# DB-GPT Server Management Script
# 管理前后端服务：start/stop/status/restart
# Usage: ./server.sh [start|stop|status|restart] [backend|frontend|all]

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
DBGPT_BIN="$PROJECT_ROOT/.venv/bin/dbgpt"
CONFIG_FILE="$PROJECT_ROOT/configs/dbgpt-hs-custom.toml"
WEB_DIR="$PROJECT_ROOT/web"

# PID 和日志文件
BACKEND_PID_FILE="$PROJECT_ROOT/logs/dbgpt.pid"
FRONTEND_PID_FILE="$PROJECT_ROOT/logs/frontend.pid"
BACKEND_LOG_FILE="$PROJECT_ROOT/logs/dbgpt_server.log"
FRONTEND_LOG_FILE="$PROJECT_ROOT/logs/frontend.log"

# 端口配置
BACKEND_PORT=5670
FRONTEND_PORT=3000

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Ensure logs directory exists
mkdir -p "$PROJECT_ROOT/logs"

# Load environment variables from .env if exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | grep -v '^$' | xargs 2>/dev/null)
fi

# 根据端口查找并杀死进程
kill_by_port() {
    local port=$1
    local pids=$(lsof -ti:$port 2>/dev/null)
    
    if [ -n "$pids" ]; then
        echo -e "${YELLOW}发现端口 $port 被占用，正在停止相关进程...${NC}"
        for pid in $pids; do
            echo "  终止进程 PID: $pid"
            kill -9 $pid 2>/dev/null
        done
        sleep 1
        return 0
    fi
    return 1
}

# 检查端口是否被占用
check_port() {
    local port=$1
    lsof -ti:$port >/dev/null 2>&1
    return $?
}

# ============ 后端服务管理 ============

start_backend() {
    echo -e "${GREEN}[后端] 启动 DB-GPT 服务...${NC}"
    
    # 检查是否已运行
    if [ -f "$BACKEND_PID_FILE" ]; then
        PID=$(cat "$BACKEND_PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo -e "${YELLOW}后端已在运行 (PID: $PID)${NC}"
            return 0
        fi
        rm "$BACKEND_PID_FILE"
    fi
    
    # 确保端口未被占用
    if check_port $BACKEND_PORT; then
        echo -e "${YELLOW}端口 $BACKEND_PORT 已被占用，尝试清理...${NC}"
        kill_by_port $BACKEND_PORT
    fi
    
    # 启动服务
    cd "$PROJECT_ROOT"
    nohup "$DBGPT_BIN" start webserver -c "$CONFIG_FILE" > "$BACKEND_LOG_FILE" 2>&1 &
    
    NEW_PID=$!
    echo $NEW_PID > "$BACKEND_PID_FILE"
    echo -e "${GREEN}后端已启动 (PID: $NEW_PID), 端口: $BACKEND_PORT${NC}"
    echo "日志路径: $BACKEND_LOG_FILE"
}

stop_backend() {
    echo -e "${YELLOW}[后端] 停止 DB-GPT 服务...${NC}"
    
    # 1. 通过 PID 文件停止
    if [ -f "$BACKEND_PID_FILE" ]; then
        PID=$(cat "$BACKEND_PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            kill "$PID" 2>/dev/null
            echo "已发送停止信号到进程 $PID"
            sleep 2
        fi
        rm -f "$BACKEND_PID_FILE"
    fi
    
    # 2. 通过端口强制清理
    kill_by_port $BACKEND_PORT
    
    # 3. 清理残留的 dbgpt 进程
    local dbgpt_pids=$(pgrep -f "dbgpt start webserver" 2>/dev/null)
    if [ -n "$dbgpt_pids" ]; then
        echo "清理残留 dbgpt 进程..."
        echo "$dbgpt_pids" | xargs kill -9 2>/dev/null
    fi
    
    echo -e "${GREEN}后端已停止${NC}"
}

status_backend() {
    echo -e "${GREEN}[后端状态]${NC}"
    
    # 检查端口
    if check_port $BACKEND_PORT; then
        local pids=$(lsof -ti:$BACKEND_PORT 2>/dev/null | head -1)
        echo -e "  状态: ${GREEN}运行中${NC} (端口 $BACKEND_PORT, PID: $pids)"
        if [ -f "$BACKEND_LOG_FILE" ]; then
            echo "  最近日志:"
            tail -n 3 "$BACKEND_LOG_FILE" | sed 's/^/    /'
        fi
    else
        echo -e "  状态: ${RED}已停止${NC}"
    fi
}

# ============ 前端服务管理 ============

start_frontend() {
    echo -e "${GREEN}[前端] 启动 Next.js 开发服务...${NC}"
    
    # 检查是否已运行
    if [ -f "$FRONTEND_PID_FILE" ]; then
        PID=$(cat "$FRONTEND_PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo -e "${YELLOW}前端已在运行 (PID: $PID)${NC}"
            return 0
        fi
        rm "$FRONTEND_PID_FILE"
    fi
    
    # 确保端口未被占用
    if check_port $FRONTEND_PORT; then
        echo -e "${YELLOW}端口 $FRONTEND_PORT 已被占用，尝试清理...${NC}"
        kill_by_port $FRONTEND_PORT
    fi
    
    # 启动前端
    cd "$WEB_DIR"
    nohup npm run dev > "$FRONTEND_LOG_FILE" 2>&1 &
    
    NEW_PID=$!
    echo $NEW_PID > "$FRONTEND_PID_FILE"
    echo -e "${GREEN}前端已启动 (PID: $NEW_PID), 端口: $FRONTEND_PORT${NC}"
    echo "日志路径: $FRONTEND_LOG_FILE"
}

stop_frontend() {
    echo -e "${YELLOW}[前端] 停止 Next.js 服务...${NC}"
    
    # 1. 通过 PID 文件停止
    if [ -f "$FRONTEND_PID_FILE" ]; then
        PID=$(cat "$FRONTEND_PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            kill "$PID" 2>/dev/null
            echo "已发送停止信号到进程 $PID"
            sleep 1
        fi
        rm -f "$FRONTEND_PID_FILE"
    fi
    
    # 2. 通过端口强制清理
    kill_by_port $FRONTEND_PORT
    
    # 3. 清理 node 相关进程（仅限本项目）
    local node_pids=$(pgrep -f "next dev" 2>/dev/null)
    if [ -n "$node_pids" ]; then
        echo "清理残留 next 进程..."
        echo "$node_pids" | xargs kill -9 2>/dev/null
    fi
    
    echo -e "${GREEN}前端已停止${NC}"
}

status_frontend() {
    echo -e "${GREEN}[前端状态]${NC}"
    
    # 检查端口
    if check_port $FRONTEND_PORT; then
        local pids=$(lsof -ti:$FRONTEND_PORT 2>/dev/null | head -1)
        echo -e "  状态: ${GREEN}运行中${NC} (端口 $FRONTEND_PORT, PID: $pids)"
        if [ -f "$FRONTEND_LOG_FILE" ]; then
            echo "  最近日志:"
            tail -n 3 "$FRONTEND_LOG_FILE" | sed 's/^/    /'
        fi
    else
        echo -e "  状态: ${RED}已停止${NC}"
    fi
}

# ============ 统一操作 ============

start_all() {
    start_backend
    echo ""
    start_frontend
    echo ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}所有服务已启动！${NC}"
    echo -e "  后端: http://localhost:$BACKEND_PORT"
    echo -e "  前端: http://localhost:$FRONTEND_PORT"
    echo -e "${GREEN}============================================${NC}"
}

stop_all() {
    stop_frontend
    echo ""
    stop_backend
    echo ""
    echo -e "${GREEN}所有服务已停止${NC}"
}

status_all() {
    echo -e "${GREEN}========== 服务状态 ==========${NC}"
    status_backend
    echo ""
    status_frontend
    echo -e "${GREEN}==============================${NC}"
}

restart_all() {
    echo -e "${YELLOW}正在重启所有服务...${NC}"
    stop_all
    echo ""
    sleep 2
    start_all
}

# ============ 命令解析 ============

ACTION=$1
TARGET=${2:-all}  # 默认操作所有服务

case "$ACTION" in
    start)
        case "$TARGET" in
            backend)  start_backend ;;
            frontend) start_frontend ;;
            all)      start_all ;;
            *)        echo "未知目标: $TARGET"; exit 1 ;;
        esac
        ;;
    stop)
        case "$TARGET" in
            backend)  stop_backend ;;
            frontend) stop_frontend ;;
            all)      stop_all ;;
            *)        echo "未知目标: $TARGET"; exit 1 ;;
        esac
        ;;
    status)
        case "$TARGET" in
            backend)  status_backend ;;
            frontend) status_frontend ;;
            all)      status_all ;;
            *)        echo "未知目标: $TARGET"; exit 1 ;;
        esac
        ;;
    restart)
        case "$TARGET" in
            backend)  stop_backend; sleep 2; start_backend ;;
            frontend) stop_frontend; sleep 2; start_frontend ;;
            all)      restart_all ;;
            *)        echo "未知目标: $TARGET"; exit 1 ;;
        esac
        ;;
    *)
        echo "DB-GPT 服务管理脚本"
        echo ""
        echo "用法: $0 {start|stop|status|restart} [backend|frontend|all]"
        echo ""
        echo "命令:"
        echo "  start   - 启动服务"
        echo "  stop    - 停止服务（会清理占用端口的进程）"
        echo "  status  - 查看服务状态"
        echo "  restart - 重启服务"
        echo ""
        echo "目标:"
        echo "  backend  - 仅后端服务 (端口 $BACKEND_PORT)"
        echo "  frontend - 仅前端服务 (端口 $FRONTEND_PORT)"
        echo "  all      - 前后端全部 (默认)"
        echo ""
        echo "示例:"
        echo "  $0 start           # 启动全部"
        echo "  $0 stop backend    # 只停止后端"
        echo "  $0 restart frontend # 只重启前端"
        exit 1
        ;;
esac
