# SysOM 统一 MCP 服务器使用说明

## 概述

`sysom_main_mcp.py` 是一个统一的 MCP 服务器，聚合了所有 SysOM MCP 服务的工具，实现了标准的 MCP 协议，可以被 Qwen Code 等客户端通过 stdio 模式调用。

## 功能特性

- ✅ 实现标准的 MCP 协议（JSON-RPC over stdio）
- ✅ 聚合所有子服务的工具（AM、内存诊断、IO诊断、网络诊断、其他诊断）
- ✅ 支持 stdio 和 SSE 两种运行模式
- ✅ 日志输出到 stderr，不干扰 MCP 协议通信
- ✅ 可以被 Qwen Code 等客户端直接调用

## 聚合的服务和工具

### AM 服务（4个工具）
- `list_all_instances` - 列出所有实例
- `list_pods_of_instance` - 列出实例的 Pod
- `list_clusters` - 列出集群
- `list_instances` - 列出实例

### 内存诊断服务（3个工具）
- `memgraph` - 内存图诊断
- `javamem` - Java 内存诊断
- `oomcheck` - OOM 检查

### IO 诊断服务（1个工具）
- `iodiagnose` - IO 诊断

### 网络诊断服务（3个工具）
- `netjitter` - 网络抖动诊断
- `netdelay` - 网络延迟诊断
- `netloss` - 网络丢包诊断

### 其他诊断服务（2个工具）
- `diskanalysis` - 磁盘分析
- `cpucheck` - CPU 检查

**总计：13个工具**

## 使用方法

### 1. 在 Qwen Code 中配置

修改 `/root/.qwen/settings.json`：

```json
{
  "mcpServers": {
    "sysom_mcp": {
      "command": "uv",
      "args": ["run", "python", "sysom_main_mcp.py", "--stdio"],
      "env": {
        "ACCESS_KEY_ID": "your_access_key_id",
        "ACCESS_KEY_SECRET": "your_access_key_secret",
        "DASHSCOPE_API_KEY": "your_dashscope_api_key"
      },
      "cwd": "/root/sysom_mcp",
      "timeout": 30000,
      "trust": false
    }
  }
}
```

### 2. 命令行运行

#### stdio 模式（默认，用于客户端调用）
```bash
cd /root/sysom_mcp
uv run python sysom_main_mcp.py --stdio
```

#### SSE 模式（HTTP/SSE 服务器）
```bash
cd /root/sysom_mcp
uv run python sysom_main_mcp.py --sse --host 0.0.0.0 --port 7140
```

### 3. 测试 MCP 协议

```bash
cd /root/sysom_mcp
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | \
uv run python sysom_main_mcp.py --stdio
```

## 与 sysom_mcp.py 的区别

| 特性 | sysom_mcp.py | sysom_main_mcp.py |
|------|-------------|-------------------|
| MCP 协议实现 | ❌ 不实现 | ✅ 完整实现 |
| 工具聚合 | ❌ 不聚合 | ✅ 聚合所有工具 |
| 可被客户端调用 | ❌ 不可以 | ✅ 可以 |
| 用途 | 服务管理器 | MCP 服务器 |

## 故障排查

### 1. 导入错误

如果遇到 `ModuleNotFoundError: No module named 'mcp.types'`，确保：
- 使用 `uv run` 运行（使用虚拟环境）
- 所有依赖已正确安装：`uv pip install -r requirements.txt`

### 2. 工具加载失败

检查 stderr 输出，查看具体的导入错误信息。

### 3. 超时问题

- 确保环境变量已正确设置
- 检查网络连接（如果需要访问外部 API）
- 增加 timeout 值

## 注意事项

1. **日志输出**：所有日志输出到 stderr，不会干扰 MCP 协议的 stdout 通信
2. **环境变量**：确保设置了必要的环境变量（ACCESS_KEY_ID、ACCESS_KEY_SECRET、DASHSCOPE_API_KEY）
3. **工作目录**：确保在正确的目录下运行，或者设置正确的 `cwd`
4. **依赖**：确保所有依赖已安装，特别是 `fastmcp` 和 `mcp` 包

