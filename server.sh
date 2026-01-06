#!/bin/bash

# DB-GPT Server Management Script
# Usage: ./server.sh [start|stop|status|restart]

PROJECT_ROOT=$(pwd)
DBGPT_BIN="$PROJECT_ROOT/.venv/bin/dbgpt"
CONFIG_FILE="$PROJECT_ROOT/configs/dbgpt-hs-custom.toml"
PID_FILE="$PROJECT_ROOT/logs/dbgpt.pid"
LOG_FILE="$PROJECT_ROOT/logs/dbgpt_server.log"

# Ensure logs directory exists
mkdir -p "$PROJECT_ROOT/logs"

# Load environment variables from .env if exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo "Loading environment variables from .env..."
    # Export variables from .env, ignoring comments and empty lines
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
fi

start() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null; then
            echo "DB-GPT is already running (PID: $PID)."
            return
        else
            echo "Found stale PID file. Cleaning up..."
            rm "$PID_FILE"
        fi
    fi

    echo "Starting DB-GPT server..."
    nohup "$DBGPT_BIN" start webserver -c "$CONFIG_FILE" > "$LOG_FILE" 2>&1 &
    
    NEW_PID=$!
    echo $NEW_PID > "$PID_FILE"
    echo "DB-GPT started in background (PID: $NEW_PID)."
    echo "Logs are available at: $LOG_FILE"
}

stop() {
    echo "Stopping DB-GPT server..."
    
    # 1. Try stopping by PID file
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null; then
            kill "$PID"
            echo "Sent SIGTERM to process $PID."
        fi
        rm "$PID_FILE"
    fi

    # 2. Force cleanup by name to ensure no orphans
    echo "Cleaning up any remaining dbgpt processes..."
    pkill -9 -f "dbgpt" 2>/dev/null
    
    sleep 2
    echo "Server stopped."
}

status() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null; then
            echo "DB-GPT is RUNNING (PID: $PID)."
            echo "Last 5 lines of log:"
            tail -n 5 "$LOG_FILE"
        else
            echo "DB-GPT is NOT running (stale PID file exists)."
        fi
    else
        # Check by process name as fallback
        PID=$(pgrep -f "dbgpt start webserver" | head -n 1)
        if [ -n "$PID" ]; then
            echo "DB-GPT is RUNNING (PID: $PID, untracked by PID file)."
        else
            echo "DB-GPT is STOPPED."
        fi
    fi
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    status)
        status
        ;;
    restart)
        stop
        start
        ;;
    *)
        echo "Usage: $0 {start|stop|status|restart}"
        exit 1
        ;;
esac
