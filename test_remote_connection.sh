#!/bin/bash
# 测试远程 MCP 服务器连接

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 默认配置
DEFAULT_HOST="localhost"
DEFAULT_PORT=7140
DEFAULT_PATH="/mcp/unified"

# 打印帮助信息
print_help() {
    cat << EOF
用法: $0 [选项]

测试远程 MCP 服务器的连接

选项:
    -h, --host HOST         服务器地址 (默认: $DEFAULT_HOST)
    -p, --port PORT         服务器端口 (默认: $DEFAULT_PORT)
    --path PATH             HTTP 路径 (默认: $DEFAULT_PATH)
    --help                  显示此帮助信息

示例:
    # 测试本地服务器
    $0

    # 测试远程服务器
    $0 --host 192.168.1.100 --port 7140

EOF
}

# 解析命令行参数
HOST="$DEFAULT_HOST"
PORT="$DEFAULT_PORT"
PATH="$DEFAULT_PATH"

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
}

# 测试连接
test_connection() {
    local url="http://${HOST}:${PORT}${PATH}"
    
    echo -e "${GREEN}测试 MCP 服务器连接...${NC}"
    echo -e "  服务器地址: $url"
    echo ""
    
    # 检查 curl 是否可用
    if ! command -v curl &> /dev/null; then
        echo -e "${RED}错误: 未找到 curl 命令${NC}" >&2
        exit 1
    fi
    
    # 测试基本连接
    echo -e "${YELLOW}[1/3] 测试基本连接...${NC}"
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "$url" || echo "000")
    
    if [[ "$http_code" == "000" ]]; then
        echo -e "${RED}✗ 连接失败：无法连接到服务器${NC}" >&2
        echo -e "${RED}   请检查：${NC}" >&2
        echo -e "${RED}   1. 服务器是否正在运行${NC}" >&2
        echo -e "${RED}   2. 地址和端口是否正确${NC}" >&2
        echo -e "${RED}   3. 防火墙是否允许连接${NC}" >&2
        exit 1
    elif [[ "$http_code" =~ ^[45] ]]; then
        echo -e "${YELLOW}⚠ 服务器响应 HTTP $http_code${NC}"
        echo -e "${YELLOW}   这可能表示服务器正在运行，但路径或方法不正确${NC}"
    else
        echo -e "${GREEN}✓ 连接成功 (HTTP $http_code)${NC}"
    fi
    
    # 测试 MCP 协议（发送 initialize 请求）
    echo ""
    echo -e "${YELLOW}[2/3] 测试 MCP 协议...${NC}"
    local mcp_request='{
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }'
    
    local response=$(curl -s -X POST "$url" \
        -H "Content-Type: application/json" \
        -d "$mcp_request" \
        --connect-timeout 5 \
        --max-time 10 || echo "")
    
    if [[ -z "$response" ]]; then
        echo -e "${RED}✗ MCP 协议测试失败：无响应${NC}" >&2
        exit 1
    fi
    
    # 检查响应是否为有效的 JSON
    if echo "$response" | python3 -m json.tool > /dev/null 2>&1; then
        echo -e "${GREEN}✓ MCP 协议响应有效${NC}"
        echo -e "${GREEN}   响应: $(echo "$response" | python3 -m json.tool | head -5)${NC}"
    else
        echo -e "${YELLOW}⚠ 响应不是有效的 JSON${NC}"
        echo -e "${YELLOW}   响应: $response${NC}"
    fi
    
    # 测试工具列表
    echo ""
    echo -e "${YELLOW}[3/3] 测试工具列表...${NC}"
    local tools_request='{
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }'
    
    local tools_response=$(curl -s -X POST "$url" \
        -H "Content-Type: application/json" \
        -d "$tools_request" \
        --connect-timeout 5 \
        --max-time 10 || echo "")
    
    if [[ -n "$tools_response" ]]; then
        if echo "$tools_response" | python3 -m json.tool > /dev/null 2>&1; then
            local tool_count=$(echo "$tools_response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('result', {}).get('tools', [])))" 2>/dev/null || echo "?")
            echo -e "${GREEN}✓ 工具列表获取成功${NC}"
            echo -e "${GREEN}   可用工具数量: $tool_count${NC}"
        else
            echo -e "${YELLOW}⚠ 工具列表响应格式异常${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ 无法获取工具列表${NC}"
    fi
    
    echo ""
    echo -e "${GREEN}测试完成！${NC}"
    echo -e "${GREEN}服务器地址: $url${NC}"
}

# 主函数
main() {
    test_connection
}

# 运行主函数
main

