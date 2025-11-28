#!/bin/bash
# SysOM MCP 服务器启动脚本
# 用于启动 SSE 模式的 MCP 服务器，支持远程访问

set -e

# 默认配置
DEFAULT_HOST="0.0.0.0"
DEFAULT_PORT=7140
DEFAULT_PATH="/mcp/unified"
DEFAULT_MODE="sse"

# 全局变量
USE_UV=false
UV_CMD=""
PYTHON_CMD=""

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印帮助信息
print_help() {
    cat << EOF
用法: $0 [选项]

启动 SysOM MCP 服务器（SSE 模式，支持远程访问）

选项:
    -h, --host HOST         监听地址 (默认: $DEFAULT_HOST)
                           使用 0.0.0.0 允许所有网络接口访问
                           使用 127.0.0.1 仅允许本地访问
    -p, --port PORT         监听端口 (默认: $DEFAULT_PORT)
    --path PATH             HTTP 路径 (默认: $DEFAULT_PATH)
    -d, --daemon           以后台守护进程模式运行
    --pid-file FILE         PID 文件路径 (仅用于守护进程模式)
    --log-file FILE         日志文件路径 (仅用于守护进程模式)
    --help                  显示此帮助信息

示例:
    # 前台运行，监听所有网络接口
    $0

    # 指定 IP 和端口
    $0 --host 192.168.1.100 --port 8080

    # 后台运行
    $0 --daemon --pid-file /var/run/sysom-mcp.pid --log-file /var/log/sysom-mcp.log

    # 仅允许本地访问
    $0 --host 127.0.0.1

环境变量:
    ACCESS_KEY_ID          阿里云 AccessKey ID
    ACCESS_KEY_SECRET      阿里云 AccessKey Secret
    DASHSCOPE_API_KEY      DashScope API Key

EOF
}

# 解析命令行参数
HOST="$DEFAULT_HOST"
PORT="$DEFAULT_PORT"
PATH="$DEFAULT_PATH"
DAEMON=false
PID_FILE=""
LOG_FILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--host)
            HOST="$2"
            shift 2
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        --path)
            PATH="$2"
            shift 2
            ;;
        -d|--daemon)
            DAEMON=true
            shift
            ;;
        --pid-file)
            PID_FILE="$2"
            shift 2
            ;;
        --log-file)
            LOG_FILE="$2"
            shift 2
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

# 检查必要的环境变量
check_env() {
    local missing_vars=()
    
    if [[ -z "$ACCESS_KEY_ID" ]]; then
        missing_vars+=("ACCESS_KEY_ID")
    fi
    
    if [[ -z "$ACCESS_KEY_SECRET" ]]; then
        missing_vars+=("ACCESS_KEY_SECRET")
    fi
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        echo -e "${YELLOW}警告: 以下环境变量未设置:${NC}" >&2
        for var in "${missing_vars[@]}"; do
            echo -e "  - $var" >&2
        done
        echo -e "${YELLOW}某些功能可能无法正常工作${NC}" >&2
    fi
}

# 查找 uv 命令
find_uv() {
    # 方法1: 使用 command -v
    if command -v uv &> /dev/null; then
        echo "uv"
        return 0
    fi
    
    # 方法2: 检查常见安装位置
    local uv_paths=(
        "/usr/local/bin/uv"
        "$HOME/.cargo/bin/uv"
        "$HOME/.local/bin/uv"
        "/usr/bin/uv"
    )
    
    for path in "${uv_paths[@]}"; do
        if [[ -x "$path" ]]; then
            echo "$path"
            return 0
        fi
    done
    
    return 1
}

# 查找 Python 命令
find_python() {
    # 优先使用虚拟环境中的 Python
    if [[ -f ".venv/bin/python" ]]; then
        echo ".venv/bin/python"
        return 0
    fi
    
    # 使用系统 Python
    if command -v python3 &> /dev/null; then
        echo "python3"
        return 0
    fi
    
    if command -v python &> /dev/null; then
        echo "python"
        return 0
    fi
    
    return 1
}

# 检查 Python 和依赖
check_dependencies() {
    # 检查是否在项目目录
    if [[ ! -f "sysom_main_mcp.py" ]]; then
        echo -e "${RED}错误: 未找到 sysom_main_mcp.py${NC}" >&2
        echo -e "${RED}请确保在项目根目录运行此脚本${NC}" >&2
        exit 1
    fi
    
    # 尝试查找 uv
    UV_CMD=$(find_uv)
    if [[ -n "$UV_CMD" ]]; then
        echo -e "${GREEN}找到 uv: $UV_CMD${NC}" >&2
        USE_UV=true
    else
        echo -e "${YELLOW}未找到 uv，将使用 Python 直接运行${NC}" >&2
        USE_UV=false
        
        # 查找 Python
        PYTHON_CMD=$(find_python)
        if [[ -z "$PYTHON_CMD" ]]; then
            echo -e "${RED}错误: 未找到 Python${NC}" >&2
            exit 1
        fi
        echo -e "${GREEN}使用 Python: $PYTHON_CMD${NC}" >&2
    fi
}

# 检查端口是否被占用
check_port() {
    if command -v netstat &> /dev/null; then
        if netstat -tuln 2>/dev/null | grep -q ":$PORT "; then
            echo -e "${YELLOW}警告: 端口 $PORT 已被占用${NC}" >&2
            echo -e "${YELLOW}请使用 --port 选项指定其他端口${NC}" >&2
            exit 1
        fi
    elif command -v ss &> /dev/null; then
        if ss -tuln 2>/dev/null | grep -q ":$PORT "; then
            echo -e "${YELLOW}警告: 端口 $PORT 已被占用${NC}" >&2
            echo -e "${YELLOW}请使用 --port 选项指定其他端口${NC}" >&2
            exit 1
        fi
    fi
}

# 启动服务器
start_server() {
    # 构建启动命令
    if [[ "$USE_UV" == true ]]; then
        local cmd="$UV_CMD run python sysom_main_mcp.py --sse --host $HOST --port $PORT --path $PATH"
    else
        local cmd="$PYTHON_CMD sysom_main_mcp.py --sse --host $HOST --port $PORT --path $PATH"
    fi
    
    if [[ "$DAEMON" == true ]]; then
        # 守护进程模式
        if [[ -z "$PID_FILE" ]]; then
            PID_FILE="/tmp/sysom-mcp-${PORT}.pid"
        fi
        
        if [[ -z "$LOG_FILE" ]]; then
            LOG_FILE="/tmp/sysom-mcp-${PORT}.log"
        fi
        
        # 检查 PID 文件
        if [[ -f "$PID_FILE" ]]; then
            local old_pid=$(cat "$PID_FILE")
            if ps -p "$old_pid" > /dev/null 2>&1; then
                echo -e "${RED}错误: 服务器已在运行 (PID: $old_pid)${NC}" >&2
                exit 1
            else
                rm -f "$PID_FILE"
            fi
        fi
        
        echo -e "${GREEN}启动 MCP 服务器（守护进程模式）...${NC}"
        echo -e "  监听地址: $HOST:$PORT"
        echo -e "  HTTP 路径: $PATH"
        echo -e "  PID 文件: $PID_FILE"
        echo -e "  日志文件: $LOG_FILE"
        
        nohup $cmd > "$LOG_FILE" 2>&1 &
        local pid=$!
        echo $pid > "$PID_FILE"
        
        # 等待一下，检查进程是否正常启动
        sleep 2
        if ps -p $pid > /dev/null 2>&1; then
            echo -e "${GREEN}服务器已启动 (PID: $pid)${NC}"
            echo -e "${GREEN}访问地址: http://$HOST:$PORT$PATH${NC}"
            echo -e "${GREEN}查看日志: tail -f $LOG_FILE${NC}"
        else
            echo -e "${RED}错误: 服务器启动失败${NC}" >&2
            echo -e "${RED}请查看日志: $LOG_FILE${NC}" >&2
            rm -f "$PID_FILE"
            exit 1
        fi
    else
        # 前台模式
        echo -e "${GREEN}启动 MCP 服务器...${NC}"
        echo -e "  监听地址: $HOST:$PORT"
        echo -e "  HTTP 路径: $PATH"
        echo -e "  按 Ctrl+C 停止服务器"
        echo ""
        
        exec $cmd
    fi
}

# 主函数
main() {
    check_dependencies
    check_env
    check_port
    start_server
}

# 运行主函数
main

