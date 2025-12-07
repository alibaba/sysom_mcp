# SysOM MCP 项目

## 项目简介

SysOM MCP 是一个基于 Model Context Protocol (MCP) 的系统诊断工具集，为 AI 代码助手（如 Qwen Code）提供系统运维和诊断能力。项目聚合了多个 SysOM 诊断服务，通过统一的 MCP 服务器接口，使 AI 助手能够执行系统诊断、性能分析和问题排查等操作。

### 核心特性

- ✅ **标准 MCP 协议实现**：完整实现 MCP 协议（JSON-RPC over stdio），可与 Qwen Code 等客户端无缝集成
- ✅ **统一服务聚合**：将多个诊断服务聚合到单一 MCP 服务器，提供统一的调用接口
- ✅ **多模式运行**：支持 stdio 和 SSE 两种运行模式，适应不同的使用场景
- ✅ **丰富的诊断工具**：提供 13+ 个系统诊断工具，覆盖内存、IO、网络、调度等多个维度

### 功能模块

#### 1. AM 服务（应用管理）
- `list_all_instances` - 列出所有实例
- `list_pods_of_instance` - 列出实例的 Pod
- `list_clusters` - 列出集群
- `list_instances` - 列出实例

#### 2. 内存诊断服务
- `memgraph` - 内存全景分析，扫描系统内存占用状态，详细拆解内存使用情况
- `javamem` - Java 内存诊断，分析 Java 应用的内存使用情况
- `oomcheck` - OOM 检查，检测系统内存溢出问题

#### 3. IO 诊断服务
- `iodiagnose` - IO 诊断，分析系统 IO 性能问题

#### 4. 网络诊断服务
- `netjitter` - 网络抖动诊断
- `netdelay` - 网络延迟诊断
- `netloss` - 网络丢包诊断

#### 5. 调度诊断服务
- 提供系统调度相关的诊断能力

#### 6. 其他诊断服务
- `diskanalysis` - 磁盘分析
- `cpucheck` - CPU 检查

### 技术栈

- **Python 3.11+**：主要开发语言
- **uv**：快速 Python 包管理工具
- **FastMCP**：MCP 协议实现框架
- **Pydantic**：数据验证和设置管理
- **OpenAPI Client**：与后端诊断服务 API 交互

### 使用场景

1. **AI 辅助系统诊断**：通过 Qwen Code 等 AI 代码助手，使用自然语言进行系统诊断
2. **自动化运维**：集成到自动化运维流程中，实现系统问题的自动检测和分析
3. **性能分析**：快速定位系统性能瓶颈，包括内存、IO、网络等方面
4. **问题排查**：在系统出现问题时，快速获取诊断信息，辅助问题定位

### 快速开始

#### 环境准备

本项目使用 `uv` 进行包管理。确保已安装 `uv`：

```bash
# 安装 uv（如果尚未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装项目依赖
cd /root/sysom_mcp
uv sync
```

#### 安装 Qwen Code

如果尚未安装 Qwen Code，请先安装：

```bash
# 配置 npm 镜像源加速（可选，但推荐）
npm config set registry https://registry.npmmirror.com

# 全局安装 Qwen Code
npm install -g @qwen-code/qwen-code@latest
```

**注意**：安装 Qwen Code 需要 Node.js 和 npm。如果尚未安装，请先安装 Node.js。

#### 获取api_key和免费额度
参考官网文档https://help.aliyun.com/zh/model-studio/get-api-key，开通百炼，获取免费额度

#### 在 Qwen Code 中配置

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

#### 使用 Qwen 测试 MCP 效果

使用 `qwen` 命令行工具测试 MCP 服务器。首先确保 MCP 服务器已在 Qwen Code 中正确配置（参考上面的配置），然后使用以下命令启动 Qwen：

```bash
cd /root/sysom_mcp

# 使用 qwen 测试 MCP 效果
qwen --openai-api-key "sk-d691e99a775e4ce09c7bea512e2b9a92" \
     --openai-base-url "https://dashscope.aliyuncs.com/compatible-mode/v1" \
     --model "qwen-max"
```

**注意**：确保在 Qwen Code 的配置文件中已正确配置 MCP 服务器（参考上面的"在 Qwen Code 中配置"部分），这样 Qwen 才能访问 MCP 工具。

#### 命令行运行

```bash
# stdio 模式（用于客户端调用）
uv run python sysom_main_mcp.py --stdio

# SSE 模式（HTTP/SSE 服务器）
uv run python sysom_main_mcp.py --sse --host 0.0.0.0 --port 7140
```

更多使用说明请参考 [SYSOM_MAIN_MCP_README.md](./SYSOM_MAIN_MCP_README.md)。

#### 测试 MCP 服务器

项目提供了测试客户端，可以用于测试 MCP 服务器的功能：

```bash
# 使用测试客户端测试统一 MCP 服务器
uv run python src/tests/test_client.py
```

测试客户端会：
1. 自动连接到统一 MCP 服务器 `sysom_main_mcp.py`
2. 列出所有可用的工具
3. 进入交互式聊天模式，可以使用自然语言查询并调用工具

**测试客户端功能**：
- 支持使用 Qwen 模型进行自然语言交互
- 自动调用合适的 MCP 工具
- 支持并行工具调用
- 提供详细的工具调用日志

**注意事项**：
- 确保已设置 `DASHSCOPE_API_KEY` 环境变量（在 `.env` 文件中）
- 测试客户端使用 stdio 模式连接 MCP 服务器
- 输入 `q` 或 `quit` 退出交互式模式

**其他测试方法**：

项目还提供了基于 agentscope 的测试客户端：

```bash
# 使用 agentscope 测试客户端（需要 agentscope 库）
uv run python src/tests/test_sysom_main_mcp.py
```

该测试客户端会：
- 自动启动 MCP 服务器（stdio 模式）
- 创建 ReAct Agent 进行测试
- 支持交互式测试模式

### 项目结构

```
sysom_mcp/
├── sysom_main_mcp.py      # 统一 MCP 服务器入口
├── main.py                # 主入口文件
├── pyproject.toml         # 项目配置文件（uv 使用）
├── uv.lock                # uv 依赖锁定文件
├── requirements.txt       # Python 依赖（兼容性）
├── src/
│   └── tools/             # 各诊断服务模块
│       ├── am_mcp.py      # AM 服务
│       ├── mem_diag_mcp.py    # 内存诊断服务
│       ├── io_diag_mcp.py     # IO 诊断服务
│       ├── net_diag_mcp.py    # 网络诊断服务
│       ├── sched_diag_mcp.py  # 调度诊断服务
│       ├── other_diag_mcp.py  # 其他诊断服务
│       ├── metrics_mcp.py     # 指标服务
│       └── lib/           # 公共库
│           ├── openapi_client.py
│           ├── mcp_helper.py
│           ├── diagnosis_helper.py
│           └── ...
├── src/tests/             # 测试文件
└── README.md             # 项目文档
```

### 许可证

本项目采用 Apache License 2.0 许可证，详见 [LICENSE](./LICENSE) 文件。

## 常见问题

### 1. 如何更新依赖？

使用 `uv` 管理依赖：

```bash
# 添加新依赖
uv add package_name

# 更新所有依赖
uv sync

# 更新特定依赖
uv add package_name@latest
```

如果使用 `requirements.txt`，修改后执行：

```bash
uv pip install -r requirements.txt
```

## 项目结构

```
sysom_mcp/
├── README.md          # 本文件
├── pyproject.toml     # 项目配置文件（uv 使用）
├── uv.lock            # uv 依赖锁定文件
├── requirements.txt   # Python 依赖（兼容性）
├── sysom_main_mcp.py  # 统一 MCP 服务器入口
├── main.py            # 主入口文件
└── src/               # 源代码目录
    └── tools/         # MCP 工具模块
        ├── am_mcp.py
        ├── mem_diag_mcp.py
        ├── io_diag_mcp.py
        ├── net_diag_mcp.py
        ├── sched_diag_mcp.py
        ├── other_diag_mcp.py
        ├── metrics_mcp.py
        └── lib/       # 公共库
    └── tests/         # 测试文件
```

## 注意事项

- 确保已安装 Python 3.11+ 和 `uv` 工具
- `.env` 文件位于项目根目录，确保已正确配置必要的环境变量（如 `ACCESS_KEY_ID`、`ACCESS_KEY_SECRET`、`DASHSCOPE_API_KEY`）
- 使用 `uv sync` 安装依赖后，即可直接运行项目

