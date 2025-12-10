# Ollama Agent 使用指南

本指南介绍如何使用基于 Ollama 的 Agent 来调用 SysOM MCP 工具。

## 前置要求

1. **安装 Ollama**
   ```bash
   # 访问 https://ollama.ai 下载并安装 Ollama
   # 或使用以下命令（Linux）：
   curl -fsSL https://ollama.ai/install.sh | sh
   ```

2. **启动 Ollama 服务**
   
   Ollama 服务默认在 http://localhost:11434 运行。安装完成后需要启动服务才能使用。
   
   ```bash
   # 方式 1: 后台运行（推荐）
   ollama serve > /tmp/ollama_serve.log 2>&1 &
   
   # 方式 2: 使用 nohup（即使终端关闭也继续运行）
   nohup ollama serve > /tmp/ollama_serve.log 2>&1 &
   
   # 方式 3: 前台运行（可以看到实时输出，按 Ctrl+C 停止）
   ollama serve
   ```
   
   **验证服务是否启动：**
   ```bash
   # 检查进程
   ps aux | grep ollama
   
   # 检查端口（默认 11434）
   netstat -tlnp | grep 11434
   # 或
   ss -tlnp | grep 11434
   
   # 测试 API
   curl http://localhost:11434/api/tags
   ```
   
   **常见问题：**
   - 如果遇到 `ollama server not responding` 错误，说明服务未启动，需要先执行 `ollama serve`
   - 查看服务日志：`tail -f /tmp/ollama_serve.log`
   - 停止服务：`pkill ollama`

3. **下载模型**
   
   启动服务后，可以下载模型。下载模型需要 Ollama 服务运行。
   
   ```bash
   # 下载一个适合的模型（推荐 llama3.2 或 qwen2.5）
   ollama pull llama3.2
   # 或
   ollama pull qwen2.5:7b
   ```

4. **安装 Python 依赖**
   
   本项目使用 `uv` 管理依赖，所有依赖已在 `pyproject.toml` 中配置。
   ```bash
   uv sync
   ```

## 使用方法

### 方式一：基础 Agent（ollama_agent.py）

基础版本使用简单的文本格式来解析工具调用。

```bash
# 交互模式
uv run ollama_agent.py --model llama3.2

# 单次查询
uv run ollama_agent.py --model llama3.2 --query "帮我检查内存使用情况，用户ID是123456789，地域是cn-hangzhou，实例ID是i-xxx"
```

### 方式二：高级 Agent（ollama_agent_advanced.py）

高级版本使用 JSON 格式来确保更可靠的工具调用。

```bash
# 交互模式
uv run ollama_agent_advanced.py --model llama3.2

# 单次查询
uv run ollama_agent_advanced.py --model llama3.2 --query "帮我检查内存使用情况"
```

## 命令行参数

- `--ollama-url`: Ollama 服务 URL（默认: http://localhost:11434）
- `--model`: Ollama 模型名称（默认: llama3.2）
- `--mcp-server`: MCP 服务器脚本路径（默认: sysom_main_mcp.py）
- `--query`: 要执行的查询（如果不提供，将进入交互模式）

## 示例对话

```
你: 帮我检查一下用户ID为123456789，地域为cn-hangzhou，实例ID为i-bp148hw2bn8rktm8u1a7的内存使用情况

Agent: 我将为您调用内存诊断工具来检查该实例的内存使用情况。

[工具调用: memgraph]
[参数: {"uid": "123456789", "region": "cn-hangzhou", "channel": "ecs", "instance": "i-bp148hw2bn8rktm8u1a7"}]

根据诊断结果，该实例的内存使用情况如下：
...
```

## 工作原理

1. **初始化阶段**：
   - Agent 连接到 MCP 服务器（通过 stdio）
   - 获取所有可用的工具列表
   - 将工具信息格式化为提示词

2. **对话阶段**：
   - 用户输入查询
   - Agent 将查询和工具列表发送给 Ollama
   - Ollama 决定是否需要调用工具
   - 如果需要，Agent 解析工具调用并执行
   - 将工具结果返回给 Ollama，继续对话
   - 重复直到得到最终答案

## 支持的模型

理论上支持所有 Ollama 兼容的模型，推荐使用：
- `llama3.2` - Meta 的 Llama 3.2（推荐，速度快）
- `qwen2.5:7b` - 阿里通义千问（中文理解好）
- `mistral` - Mistral AI 模型
- `phi3` - Microsoft Phi-3

## 故障排除

### 1. 无法连接到 Ollama

```
错误: 无法连接到 Ollama 服务
错误: ollama server not responding - could not connect to ollama server
```

**解决方案**：
- **检查服务是否运行**：
  ```bash
  # 检查进程
  ps aux | grep ollama
  
  # 测试 API
  curl http://localhost:11434/api/tags
  ```
  
- **如果服务未运行，启动服务**：
  ```bash
  # 后台启动
  ollama serve > /tmp/ollama_serve.log 2>&1 &
  
  # 或使用 nohup
  nohup ollama serve > /tmp/ollama_serve.log 2>&1 &
  ```
  
- **检查端口是否正确**（默认 11434）：
  ```bash
  netstat -tlnp | grep 11434
  ```
  
- **如果 Ollama 运行在其他地址**，使用 `--ollama-url` 参数：
  ```bash
  uv run ollama_agent.py --ollama-url http://192.168.1.100:11434
  ```

### 2. 模型不存在

```
错误: model 'xxx' not found
```

**解决方案**：
- 先下载模型：`ollama pull 模型名称`
- 检查可用模型：`ollama list`

### 3. MCP 服务器连接失败

```
错误: 无法连接到 MCP 服务器
```

**解决方案**：
- 确保 `sysom_main_mcp.py` 文件存在
- 检查 Python 环境是否正确
- 确保所有依赖已安装（运行 `uv sync`）

### 4. 工具调用失败

如果 Agent 无法正确调用工具，可以尝试：
- 使用高级版本（`ollama_agent_advanced.py`）
- 使用更强大的模型（如 `qwen2.5:14b`）
- 在提示词中更明确地描述需要调用的工具

## 高级配置

### 使用自定义 MCP 服务器路径

```bash
uv run ollama_agent.py --mcp-server /path/to/custom_mcp.py
```

### 使用远程 Ollama 服务

```bash
uv run ollama_agent.py --ollama-url http://192.168.1.100:11434
```

## 开发建议

1. **改进工具调用解析**：
   - 基础版本使用简单的文本匹配
   - 高级版本使用 JSON 格式
   - 可以根据需要进一步改进解析逻辑

2. **优化提示词**：
   - 根据实际使用情况调整系统提示词
   - 可以针对特定工具添加更详细的说明

3. **错误处理**：
   - 添加重试机制
   - 改进错误消息
   - 添加日志记录

## 注意事项

1. **模型选择**：较小的模型（如 llama3.2:1b）可能无法很好地理解工具调用，建议使用至少 3B 以上的模型。

2. **工具调用格式**：不同模型对工具调用的理解能力不同，如果某个模型无法正确调用工具，可以尝试其他模型。

3. **性能**：工具调用涉及多次 LLM 调用，可能需要一些时间。对于复杂的诊断任务，可能需要等待较长时间。

4. **安全性**：在生产环境中使用时，请注意：
   - 验证用户输入
   - 限制工具调用权限
   - 添加访问控制

