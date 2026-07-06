# SysOM MCP 项目

## 项目简介

SysOM MCP 是一个基于 Model Context Protocol (MCP) 的系统诊断工具集，为 AI 代码助手（如 Qwen Code）提供系统运维和诊断能力。项目聚合了多个 SysOM 诊断服务，通过统一的 MCP 服务器接口，使 AI 助手能够执行系统诊断、性能分析和问题排查等操作。

## 核心特性

- ✅ **标准 MCP 协议实现**：完整实现 MCP 协议（JSON-RPC over stdio），可与 Qwen Code 等客户端无缝集成
- ✅ **统一服务聚合**：将多个诊断服务聚合到单一 MCP 服务器，提供统一的调用接口
- ✅ **多模式运行**：支持 stdio 和 SSE 两种运行模式，适应不同的使用场景
- ✅ **丰富的诊断工具**：提供 20+ 个系统诊断工具，覆盖内存、IO、网络、调度、崩溃分析等多个维度
- ✅ **宕机诊断能力**：支持 VMCORE 和 dmesg 日志分析，自动定位系统崩溃根本原因

## 快速开始

### 环境要求

- Python 3.11 或更高版本
- Node.js 和 npm（用于安装 Qwen Code）
- uv 包管理工具

### 安装步骤

#### 1. 克隆项目

```bash
git clone https://github.com/alibaba/sysom_mcp.git
cd sysom_mcp
```

#### 2. 安装 uv

如果尚未安装 `uv`，请先安装：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### 3. 安装项目依赖

```bash
# 在项目根目录执行
uv sync
```

#### 4. 安装 Qwen Code（可选）

如果需要使用 Qwen Code 作为客户端，请先安装：

```bash
# 配置 npm 镜像源加速（可选，但推荐）
npm config set registry https://registry.npmmirror.com

# 全局安装 Qwen Code
npm install -g @qwen-code/qwen-code@latest
```

**注意**：安装 Qwen Code 需要 Node.js 和 npm。如果尚未安装，请先安装 Node.js。

#### 5. 获取 API Key

参考[阿里云百炼官方文档](https://help.aliyun.com/zh/model-studio/get-api-key)，开通百炼服务并获取 API Key 和免费额度。

### 配置说明

#### 环境变量配置

在项目根目录创建 `.env` 文件，配置以下环境变量（默认使用 AccessKey 模式）：

```bash
# 认证模式：默认为 access_key
type='access_key'

# AccessKey 模式必填字段
ACCESS_KEY_ID=your_access_key_id
ACCESS_KEY_SECRET=your_access_key_secret
```

**其他认证模式**（STS、RAM Role ARN）配置请参考 [ENV_CONFIG.md](./ENV_CONFIG.md)。

#### Qwen Code 配置

修改 Qwen Code 的配置文件（通常位于 `~/.qwen/settings.json`）：

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
      "cwd": "<项目目录>",
      "timeout": 30000,
      "trust": false
    }
  }
}
```

**配置说明**：
- `timeout`：MCP 服务器超时时间（毫秒），默认 30000（30 秒）
- `trust`：是否信任此服务器，设置为 `false` 时首次使用需要用户确认

**注意**：请将 `<项目目录>` 替换为实际的项目路径，并将环境变量值替换为实际的密钥。

## 使用指南

### 命令行运行

#### stdio 模式

用于客户端调用（如 Qwen Code）：

```bash
uv run python sysom_main_mcp.py --stdio
```

#### SSE 模式

启动 HTTP/SSE 服务器：

```bash
uv run python sysom_main_mcp.py --sse --host 0.0.0.0 --port 7140
```


## 功能模块

### 应用管理（AM 服务）
- `list_all_instances` - 列出所有实例
- `list_pods_of_instance` - 列出实例的 Pod
- `list_clusters` - 列出集群
- `list_instances` - 列出实例

### 内存诊断服务
- `memgraph` - 内存全景分析，扫描系统内存占用状态，详细拆解内存使用情况
- `javamem` - Java 内存诊断，分析 Java 应用的内存使用情况
- `oomcheck` - OOM 检查，检测系统内存溢出问题

### IO 诊断服务
- `iofsstat` - IO 文件系统统计，分析文件系统 IO 状态
- `iodiagnose` - IO 诊断，分析系统 IO 性能问题

### 网络诊断服务
- `packetdrop` - 网络丢包诊断
- `netjitter` - 网络抖动诊断

### 调度诊断服务
- `delay` - 调度延迟诊断
- `loadtask` - 负载任务诊断

### 宕机诊断服务
- `create_vmcore_diagnosis_task` - 创建基于 VMCORE 文件的内核宕机诊断任务
- `create_dmesg_diagnosis_task` - 创建基于 dmesg 日志的内核诊断任务
- `query_diagnosis_task` - 查询诊断任务状态和结果
- `list_history_tasks` - 列出历史诊断任务

### 其他诊断服务
- `vmcore` - VMCORE 分析
- `diskanalysis` - 磁盘分析

## 使用场景

1. **AI 辅助系统诊断**：通过 Qwen Code 等 AI 代码助手，使用自然语言进行系统诊断
2. **自动化运维**：集成到自动化运维流程中，实现系统问题的自动检测和分析
3. **性能分析**：快速定位系统性能瓶颈，包括内存、IO、网络等方面
4. **问题排查**：在系统出现问题时，快速获取诊断信息，辅助问题定位

## 项目结构

```
sysom_mcp/
├── README.md              # 项目说明文档
├── pyproject.toml         # 项目配置文件（uv 使用）
├── uv.lock                # uv 依赖锁定文件
├── requirements.txt       # Python 依赖（兼容性）
├── sysom_main_mcp.py     # 统一 MCP 服务器入口
└── src/                   # 源代码目录
    └── tools/             # MCP 工具模块
        ├── am_mcp.py          # 应用管理工具
        ├── mem_diag_mcp.py    # 内存诊断工具
        ├── io_diag_mcp.py     # IO 诊断工具
        ├── net_diag_mcp.py    # 网络诊断工具
        ├── sched_diag_mcp.py  # 调度诊断工具
        ├── other_diag_mcp.py  # 其他诊断工具
        ├── crash_agent_mcp.py # 崩溃诊断工具
        ├── metrics_mcp.py     # 指标工具
        └── lib/               # 公共库
    └── tests/             # 测试文件
```

## 常见问题

### 如何更新依赖？

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

### 环境变量配置

项目支持三种阿里云认证模式：AccessKey、STS 和 RAM Role ARN。默认使用 AccessKey 模式。

详细配置说明请参考 [ENV_CONFIG.md](./ENV_CONFIG.md)。

### 运行要求

- 确保已安装 Python 3.11+ 和 `uv` 工具
- 使用 `uv sync` 安装依赖后，即可直接运行项目

## 许可证

本项目采用 Apache License 2.0 许可证，详见 [LICENSE](./LICENSE) 文件。
