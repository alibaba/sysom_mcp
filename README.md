# SysOM AI

基于 [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) 的系统诊断 AI 工具集，为 AI 编码助手提供 Linux 系统运维和诊断能力。

## 项目结构

```
sysom-ai/
├── mcp/       # MCP Server — 系统诊断工具服务端
└── skills/    # Agent Skills — AI 助手技能包
    ├── alibabacloud-sysom-diagnosis/    # 深度诊断技能
    └── alibabacloud-sysom-inspection/   # 巡检技能
```

## MCP Server

SysOM MCP Server 聚合了 20+ 个系统诊断工具，覆盖内存、IO、网络、调度、宕机分析等维度，通过标准 MCP 协议（JSON-RPC over stdio/SSE）与 AI 助手集成。

### 功能模块

#### 内存诊断
- `memgraph` - 内存全景分析，扫描系统内存占用状态，详细拆解内存使用情况
- `javamem` - Java 内存诊断，分析 Java 应用的内存使用情况
- `oomcheck` - OOM 检查，检测系统内存溢出问题

#### IO 诊断
- `iofsstat` - IO 文件系统统计，分析文件系统 IO 状态
- `iodiagnose` - IO 诊断，分析系统 IO 性能问题

#### 网络诊断
- `packetdrop` - 网络丢包诊断
- `netjitter` - 网络抖动诊断

#### 调度诊断
- `delay` - 调度延迟诊断
- `loadtask` - 负载任务诊断

#### 宕机诊断
- `create_vmcore_diagnosis_task` - 创建基于 VMCORE 文件的内核宕机诊断任务
- `create_dmesg_diagnosis_task` - 创建基于 dmesg 日志的内核诊断任务
- `query_diagnosis_task` - 查询诊断任务状态和结果
- `list_history_tasks` - 列出历史诊断任务

#### 应用管理
- `list_all_instances` - 列出所有实例
- `list_pods_of_instance` - 列出实例的 Pod
- `list_clusters` - 列出集群
- `list_instances` - 列出实例

#### 其他
- `vmcore` - VMCORE 分析
- `diskanalysis` - 磁盘分析

### 使用场景

1. **AI 辅助系统诊断** — 通过 AI 代码助手，使用自然语言进行系统诊断
2. **自动化运维** — 集成到自动化运维流程中，实现系统问题的自动检测和分析
3. **性能分析** — 快速定位系统性能瓶颈，包括内存、IO、网络等方面
4. **问题排查** — 系统出现问题时，快速获取诊断信息，辅助问题定位

### 安装

```bash
# 克隆项目
git clone https://github.com/chuyixiao/sysom-ai.git
cd sysom-ai/mcp

# 安装 uv（如未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装依赖
uv sync
```

### 配置

在 `mcp/` 目录创建 `.env` 文件：

```bash
type='access_key'
ACCESS_KEY_ID=your_access_key_id
ACCESS_KEY_SECRET=your_access_key_secret
```

更多认证模式（STS、RAM Role ARN）参考 [ENV_CONFIG.md](./mcp/ENV_CONFIG.md)。

### 运行

```bash
# stdio 模式（用于 AI 客户端集成）
uv run python sysom_main_mcp.py --stdio

# SSE 模式（HTTP 服务）
uv run python sysom_main_mcp.py --sse --host 0.0.0.0 --port 7140
```

### 客户端配置示例

在 AI 编码助手（如 Qoder、Qwen Code）中配置 MCP Server：

```json
{
  "mcpServers": {
    "sysom_mcp": {
      "command": "uv",
      "args": ["run", "python", "sysom_main_mcp.py", "--stdio"],
      "env": {
        "ACCESS_KEY_ID": "your_access_key_id",
        "ACCESS_KEY_SECRET": "your_access_key_secret"
      },
      "cwd": "/path/to/sysom-ai/mcp"
    }
  }
}
```

> 完整文档参见 [mcp/README.md](./mcp/README.md)

## Skills

Agent Skills 是为 AI 编码助手（Qoder、Claude 等）提供的技能包，让 AI 具备系统诊断和巡检能力。

### 安装 Skills

使用 `npx skills` 安装：

```bash
# 安装诊断技能
npx skills add chuyixiao/sysom-ai --skill alibabacloud-sysom-diagnosis -a qoder -g

# 安装巡检技能
npx skills add chuyixiao/sysom-ai --skill alibabacloud-sysom-inspection -a qoder -g

# 一键全部安装
npx skills add chuyixiao/sysom-ia --skill '*' -a qoder -g
```

### alibabacloud-sysom-diagnosis

排查 Linux 服务器性能和稳定性问题：CPU 饱和、高负载、调度延迟、内存压力、OOM、高 RSS、page cache/共享内存增长、内存 cgroup 残留、Java 堆问题、磁盘 IO 饱和或延迟、丢包、网络抖动等。

**前置条件：**
- 需要 `sysom-osops` CLI
- 远程诊断需要阿里云凭证（AK/SK 或 ECS RAM Role）
- 支持中国大陆及香港地域

### alibabacloud-sysom-inspection

检查 ECS 实例健康状况，检测内存、磁盘、CPU、负载和资源泄漏异常，在检测到关键内存问题时自动触发深度诊断。

**前置条件：**
- 需要阿里云凭证
- 目标 ECS 需安装云助手

**使用方式：**

```bash
cd skills/alibabacloud-sysom-inspection
./scripts/init.sh
./scripts/osops.sh inspection --region-id cn-hangzhou --managed-type all
```

## 环境要求

- Python >= 3.11
- [uv](https://github.com/astral-sh/uv) 包管理工具
- Node.js（仅安装 Skills 时需要）

## License

[Apache License 2.0](./mcp/LICENSE)
