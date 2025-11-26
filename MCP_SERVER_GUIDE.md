# MCP 服务运行指南

本文档说明如何运行 `am_mcp.py` 的 MCP 服务，以及客户端如何调用该服务。

## 方式一：使用 stdio 传输（进程间通信）

### 1. 直接运行服务

```bash
# 进入项目目录
cd /root/sysom_mcp/src

# 直接运行（使用标准输入输出）
python -m mcp.am_mcp
```

这种方式使用标准输入输出（stdio）进行通信，适合：
- 作为子进程被其他程序调用
- 命令行工具集成
- 本地开发测试

### 2. 客户端调用（stdio 方式）

如果使用 stdio 方式，客户端需要通过进程调用的方式连接：

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    # 设置服务器参数
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "mcp.am_mcp"],
        env=None
    )

    # 启动客户端会话
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 列出服务器提供的工具
            tools = await session.list_tools()
            print("服务器提供的工具:", tools)

            # 调用特定工具
            result = await session.call_tool("list_all_instances", {
                "uid": "1418925853835361",
                "region": "cn-hangzhou"
            })
            print("工具调用结果:", result)

if __name__ == "__main__":
    asyncio.run(main())
```

## 方式二：使用 HTTP 传输（网络服务）

### 1. 创建 HTTP 服务器包装

由于 `am_mcp.py` 默认使用 stdio，需要通过 HTTP 服务器包装。创建一个 HTTP 服务器脚本：

```python
# 文件：src/run_am_mcp_server.py
from fastmcp.server import create_app
from mcp.am_mcp import create_mcp_server
import uvicorn

# 创建 MCP 服务器实例
mcp_server = create_mcp_server()

# 创建 FastAPI 应用
app = create_app(mcp_server, path="/api/v1/am/mcp/")

if __name__ == "__main__":
    # 运行 HTTP 服务器
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=7130,
        log_level="info"
    )
```

### 2. 运行 HTTP 服务器

```bash
# 进入项目目录
cd /root/sysom_mcp/src

# 运行 HTTP 服务器
python run_am_mcp_server.py
```

服务器将在 `http://127.0.0.1:7130/api/v1/am/mcp/` 上运行。

### 3. 客户端调用（HTTP 方式）

使用 agentscope 的 HttpStatelessClient（如测试文件中的方式）：

```python
import asyncio
from agentscope.mcp import HttpStatelessClient
from agentscope.tool import Toolkit

async def main():
    # 创建 MCP 客户端
    toolkit = Toolkit()
    
    stateless_client = HttpStatelessClient(
        name="am_mcp_client",
        transport="streamable_http",
        url="http://127.0.0.1:7130/api/v1/am/mcp/",
    )
    
    # 注册客户端
    await toolkit.register_mcp_client(stateless_client)
    
    # 获取可用工具
    tools = toolkit.get_json_schemas()
    print(f"可用工具: {tools}")
    
    # 调用工具
    result = await toolkit.call_tool(
        "list_all_instances",
        {
            "uid": "1418925853835361",
            "region": "cn-hangzhou"
        }
    )
    print(f"调用结果: {result}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 方式三：使用 FastMCP 的 HTTP 模式（推荐）

如果 FastMCP 支持直接运行 HTTP 服务器，可以修改 `am_mcp.py`：

```python
# 在 am_mcp.py 的 if __name__ == "__main__" 部分
if __name__ == "__main__":
    import sys
    
    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "http":
        # HTTP 模式
        create_mcp_server().run(
            transport="sse",  # 或 "http"
            host="0.0.0.0",
            port=7130,
            path="/api/v1/am/mcp/"
        )
    else:
        # 默认 stdio 模式
        create_mcp_server().run(transport="stdio")
```

然后运行：

```bash
# HTTP 模式
python -m mcp.am_mcp http

# 或 stdio 模式（默认）
python -m mcp.am_mcp
```

## 测试服务

### 使用测试脚本

项目已包含测试脚本，可以直接使用：

```bash
# 确保 HTTP 服务器正在运行（端口 7130）
python -m mcp.am_mcp http  # 或使用 run_am_mcp_server.py

# 在另一个终端运行测试
cd /root/sysom_mcp/src
python tests/test_am_mcp.py
```

### 手动测试 HTTP 端点

如果使用 HTTP 方式，可以使用 curl 测试：

```bash
# 列出可用工具
curl -X POST http://127.0.0.1:7130/api/v1/am/mcp/tools/list \
  -H "Content-Type: application/json" \
  -d '{}'

# 调用工具
curl -X POST http://127.0.0.1:7130/api/v1/am/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "list_all_instances",
    "arguments": {
      "uid": "1418925853835361",
      "region": "cn-hangzhou"
    }
  }'
```

## 注意事项

1. **环境变量**：确保设置了必要的环境变量（如 API 密钥、服务配置等）
2. **依赖安装**：确保所有依赖已安装（`pip install -r requirements.txt`）
3. **端口占用**：如果端口 7130 被占用，可以修改为其他端口
4. **网络访问**：HTTP 模式下，确保防火墙允许访问对应端口
5. **服务配置**：检查 `lib/service_config.py` 中的配置是否正确

## 故障排查

1. **连接失败**：检查服务器是否正在运行，端口是否正确
2. **工具调用失败**：检查参数格式是否正确，查看服务器日志
3. **导入错误**：确保在正确的目录下运行，Python 路径配置正确

