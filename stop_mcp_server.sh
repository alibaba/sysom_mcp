#!/bin/bash
# SysOM MCP 服务器停止脚本

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 默认 PID 文件
DEFAULT_PID_FILE="/tmp/sysom-mcp-7140.pid"

# 打印帮助信息
print_help() {
    cat << EOF
用法: $0 [选项]

停止 SysOM MCP 服务器

选项:
    -p, --port PORT         服务器端口 (默认: 7140)
                           用于查找对应的 PID 文件
    --pid-file FILE         直接指定 PID 文件路径
    -f, --force             强制终止进程
    --help                  显示此帮助信息

示例:
    # 停止默认端口的服务器
    $0

    # 停止指定端口的服务器
    $0 --port 8080

    # 使用 PID 文件停止
    $0 --pid-file /var/run/sysom-mcp.pid

    # 强制停止
    $0 --force

EOF
}

# 解析命令行参数
PORT=""
PID_FILE=""
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        --pid-file)
            PID_FILE="$2"
            shift 2
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        --help)
            print_help
            exit 0
            ;;
        *)
            echo -e "${RED}错误: 未知选项 $1${NC}" >&2
            print_help
            exit 1
            ;;
    esac
done

# 确定 PID 文件路径
if [[ -n "$PID_FILE" ]]; then
    # 使用指定的 PID 文件
    :
elif [[ -n "$PORT" ]]; then
    PID_FILE="/tmp/sysom-mcp-${PORT}.pid"
else
    PID_FILE="$DEFAULT_PID_FILE"
fi

# 停止服务器
stop_server() {
    if [[ ! -f "$PID_FILE" ]]; then
        echo -e "${YELLOW}警告: 未找到 PID 文件: $PID_FILE${NC}" >&2
        echo -e "${YELLOW}尝试通过进程名查找...${NC}" >&2
        
        # 尝试通过进程名查找
        local pids=$(pgrep -f "sysom_main_mcp.py.*--sse" || true)
        if [[ -z "$pids" ]]; then
            echo -e "${YELLOW}未找到运行中的 MCP 服务器${NC}" >&2
            exit 0
        fi
        
        for pid in $pids; do
            echo -e "${GREEN}找到进程 (PID: $pid)，正在停止...${NC}"
            if [[ "$FORCE" == true ]]; then
                kill -9 $pid 2>/dev/null || true
            else
                kill $pid 2>/dev/null || true
            fi
        done
        
        echo -e "${GREEN}服务器已停止${NC}"
        return 0
    fi
    
    local pid=$(cat "$PID_FILE" 2>/dev/null || echo "")
    
    if [[ -z "$pid" ]]; then
        echo -e "${YELLOW}警告: PID 文件为空: $PID_FILE${NC}" >&2
        rm -f "$PID_FILE"
        exit 0
    fi
    
    # 检查进程是否存在
    if ! ps -p "$pid" > /dev/null 2>&1; then
        echo -e "${YELLOW}警告: 进程 $pid 不存在（可能已停止）${NC}" >&2
        rm -f "$PID_FILE"
        exit 0
    fi
    
    echo -e "${GREEN}正在停止 MCP 服务器 (PID: $pid)...${NC}"
    
    if [[ "$FORCE" == true ]]; then
        kill -9 $pid 2>/dev/null || true
        echo -e "${GREEN}服务器已强制停止${NC}"
    else
        kill $pid 2>/dev/null || true
        
        # 等待进程退出
        local count=0
        while ps -p "$pid" > /dev/null 2>&1 && [[ $count -lt 10 ]]; do
            sleep 1
            count=$((count + 1))
        done
        
        if ps -p "$pid" > /dev/null 2>&1; then
            echo -e "${YELLOW}进程未在 10 秒内退出，强制终止...${NC}" >&2
            kill -9 $pid 2>/dev/null || true
        fi
        
        echo -e "${GREEN}服务器已停止${NC}"
    fi
    
    rm -f "$PID_FILE"
}

# 主函数
main() {
    stop_server
}

# 运行主函数
main

