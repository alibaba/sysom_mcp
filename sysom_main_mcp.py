#!/usr/bin/env python3
"""SysOM 统一 MCP 服务器

聚合所有 MCP 服务到一个统一的服务器中，实现 MCP 协议
可以被 Qwen Code 等客户端通过 stdio 模式调用
"""
import sys
from pathlib import Path
from typing import Literal
import click

# 添加项目根目录到 Python 路径
# 确保 src 和 src/tools 目录都在路径中
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
TOOLS_DIR = SRC_DIR / "tools"
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
# 添加 tools 目录到路径，这样 lib 模块可以被找到
if TOOLS_DIR.exists() and str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

# 配置日志输出到 stderr，避免干扰 MCP 协议的 stdout 通信
import logging
logging.basicConfig(
    level=logging.WARNING,  # 只记录警告和错误
    stream=sys.stderr,  # 输出到 stderr
    format='%(levelname)s:%(name)s:%(message)s'
)

from fastmcp import FastMCP, Context
from pydantic import Field

# 创建统一的 MCP 服务器
mcp = FastMCP(name="SysOM Unified MCP Server")

# 导入并注册所有服务的工具
try:
    # 导入各个服务的 MCP 实例
    from tools.am_mcp import mcp as am_mcp
    from tools.mem_diag_mcp import mcp as mem_mcp
    from tools.io_diag_mcp import mcp as io_mcp
    from tools.net_diag_mcp import mcp as net_mcp
    from tools.sched_diag_mcp import mcp as sched_mcp
    from tools.other_diag_mcp import mcp as other_mcp
    from tools.crash_agent_mcp import mcp as crash_agent_mcp
    
    # 从各个服务的 MCP 实例中获取工具并添加到统一服务器
    # FastMCP 使用 _tool_manager._tools 字典存储工具
    service_mcps = [am_mcp, mem_mcp, io_mcp, net_mcp, sched_mcp, other_mcp, crash_agent_mcp]
    
    total_tools = 0
    for service_mcp in service_mcps:
        if hasattr(service_mcp, '_tool_manager'):
            tool_manager = service_mcp._tool_manager
            # 使用 _tools 属性获取工具字典
            if hasattr(tool_manager, '_tools') and tool_manager._tools:
                tools_dict = tool_manager._tools
                for tool_name, tool_obj in tools_dict.items():
                    # 使用 add_tool 方法添加工具
                    mcp.add_tool(tool_obj)
                    total_tools += 1
                    print(f"Added tool: {tool_name}", file=sys.stderr)
    
    print(f"Successfully loaded {total_tools} tools from all MCP services", file=sys.stderr)
    
except ImportError as e:
    # 如果导入失败，记录错误到 stderr
    import traceback
    print(f"ERROR: Failed to import MCP tools: {e}", file=sys.stderr)
    print(traceback.format_exc(), file=sys.stderr)
    # 创建一个占位工具，避免服务器完全无法使用
    @mcp.tool()
    async def error_tool(message: str = Field(..., description="错误信息")) -> dict:
        """占位工具，表示服务未正确加载"""
        return {"error": f"MCP 工具加载失败: {message}"}
except Exception as e:
    # 处理其他异常
    import traceback
    print(f"ERROR: Unexpected error loading MCP tools: {e}", file=sys.stderr)
    print(traceback.format_exc(), file=sys.stderr)


@click.command()
@click.option("--stdio", "run_mode", flag_value="stdio", default=True, help="Run in stdio mode")
@click.option("--sse", "run_mode", flag_value="sse", help="Run in SSE mode")
@click.option("--host", default="127.0.0.1", help="Host to bind to (for SSE mode, default: 127.0.0.1)")
@click.option("--port", default=7140, type=int, help="Port to bind to (for SSE mode, default: 7140)")
@click.option("--path", default="/mcp/unified", help="Path for SSE endpoint (default: /mcp/unified)")
def main(run_mode: Literal["stdio", "sse"], host: str, port: int, path: str) -> None:
    """Run unified MCP server in stdio or SSE mode"""
    if run_mode == "sse":
        # SSE 模式：HTTP/SSE 服务器
        print(f"Starting MCP server in SSE mode on {host}:{port}{path}", file=sys.stderr)
        mcp.run(transport="sse", host=host, port=port, path=path)
    else:
        # stdio 模式：这是 Qwen Code 使用的模式
        # 注意：不要输出任何内容到 stdout，这会干扰 MCP 协议
        # 所有日志和错误信息都输出到 stderr
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

