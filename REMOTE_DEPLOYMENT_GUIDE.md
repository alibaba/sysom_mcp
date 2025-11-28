# MCP 服务器远程部署指南

本文档说明如何在一台机器上启动 MCP 服务器，并让其他机器上的 agent（如 Qwen Code）通过网络连接访问。

## 架构说明

MCP 协议支持两种传输方式：

1. **stdio 模式**：通过标准输入输出通信，仅支持本地进程间通信
2. **SSE 模式**：通过 HTTP/SSE（Server-Sent Events）通信，支持网络访问

对于远程访问，必须使用 **SSE 模式**。

## 部署步骤

### 第一步：在服务器端启动 MCP 服务器（SSE 模式）

#### 1.1 启动统一 MCP 服务器

```bash
cd /root/sysom_mcp

# 启动 SSE 模式的服务器，监听所有网络接口
uv run python sysom_main_mcp.py --sse --host 0.0.0.0 --port 7140

# 或者指定特定的 IP 地址
uv run python sysom_main_mcp.py --sse --host 192.168.1.100 --port 7140
```

**参数说明：**
- `--sse`：启用 SSE 模式（HTTP/SSE 传输）
- `--host 0.0.0.0`：监听所有网络接口（允许远程访问）
  - 如果只允许本地访问，使用 `--host 127.0.0.1`
  - 如果指定特定 IP，使用 `--host <服务器IP>`
- `--port 7140`：监听端口（默认 7140）
- `--path /mcp/unified`：HTTP 路径（默认 `/mcp/unified`）

#### 1.2 使用 systemd 服务（推荐，用于生产环境）

创建 systemd 服务文件 `/etc/systemd/system/sysom-mcp.service`：

```ini
[Unit]
Description=SysOM MCP Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/sysom_mcp
Environment="ACCESS_KEY_ID=your_access_key_id"
Environment="ACCESS_KEY_SECRET=your_access_key_secret"
Environment="DASHSCOPE_API_KEY=your_dashscope_api_key"
ExecStart=/root/sysom_mcp/.venv/bin/python sysom_main_mcp.py --sse --host 0.0.0.0 --port 7140
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable sysom-mcp
sudo systemctl start sysom-mcp
sudo systemctl status sysom-mcp
```

查看日志：

```bash
sudo journalctl -u sysom-mcp -f
```

#### 1.3 使用 screen 或 tmux（临时方案）

```bash
# 使用 screen
screen -S sysom-mcp
cd /root/sysom_mcp
uv run python sysom_main_mcp.py --sse --host 0.0.0.0 --port 7140
# 按 Ctrl+A 然后按 D 退出 screen（服务继续运行）

# 重新连接
screen -r sysom-mcp

# 使用 tmux
tmux new -s sysom-mcp
cd /root/sysom_mcp
uv run python sysom_main_mcp.py --sse --host 0.0.0.0 --port 7140
# 按 Ctrl+B 然后按 D 退出 tmux

# 重新连接
tmux attach -t sysom-mcp
```

### 第二步：配置防火墙

确保服务器防火墙允许客户端访问 MCP 服务器的端口：

```bash
# CentOS/RHEL/AlmaLinux (firewalld)
sudo firewall-cmd --permanent --add-port=7140/tcp
sudo firewall-cmd --reload

# Ubuntu/Debian (ufw)
sudo ufw allow 7140/tcp
sudo ufw reload

# 或者使用 iptables
sudo iptables -A INPUT -p tcp --dport 7140 -j ACCEPT
sudo iptables-save
```

### 第三步：在客户端配置 Agent

#### 3.1 Qwen Code 配置（如果支持 SSE）

如果 Qwen Code 支持 SSE 模式的 MCP 连接，修改客户端机器的配置文件：

**Windows/Mac/Linux 客户端：**

编辑 Qwen Code 的配置文件（通常在 `~/.qwen/settings.json` 或类似位置）：

```json
{
  "mcpServers": {
    "sysom_mcp_remote": {
      "transport": "sse",
      "url": "http://<服务器IP>:7140/mcp/unified",
      "env": {
        "ACCESS_KEY_ID": "your_access_key_id",
        "ACCESS_KEY_SECRET": "your_access_key_secret",
        "DASHSCOPE_API_KEY": "your_dashscope_api_key"
      },
      "timeout": 30000,
      "trust": false
    }
  }
}
```

**注意：** 将 `<服务器IP>` 替换为实际的服务器 IP 地址，例如 `192.168.1.100` 或 `10.0.0.50`。

#### 3.2 使用 Python MCP 客户端

如果 Qwen Code 不支持 SSE 模式，可以使用 Python 客户端作为代理：

```python
# client_proxy.py
import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

async def main():
    # 连接到远程 MCP 服务器
    server_url = "http://192.168.1.100:7140/mcp/unified"
    
    async with sse_client(server_url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # 列出可用工具
            tools = await session.list_tools()
            print("可用工具:", tools)
            
            # 调用工具
            result = await session.call_tool("list_all_instances", {
                "uid": "1418925853835361",
                "region": "cn-hangzhou"
            })
            print("结果:", result)

if __name__ == "__main__":
    asyncio.run(main())
```

#### 3.3 使用 HTTP 客户端直接调用

MCP 服务器在 SSE 模式下提供 HTTP 端点，可以直接通过 HTTP 调用：

```bash
# 测试服务器是否运行
curl http://<服务器IP>:7140/mcp/unified

# 发送 MCP 请求（需要按照 MCP 协议格式）
curl -X POST http://<服务器IP>:7140/mcp/unified \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
  }'
```

### 第四步：验证连接

#### 4.1 检查服务器是否运行

```bash
# 在服务器上检查端口是否监听
netstat -tlnp | grep 7140
# 或
ss -tlnp | grep 7140

# 检查进程
ps aux | grep sysom_main_mcp
```

#### 4.2 从客户端测试连接

```bash
# 测试 HTTP 连接
curl -v http://<服务器IP>:7140/mcp/unified

# 如果服务器正常运行，应该返回 HTTP 200 或相关的 MCP 响应
```

## 安全考虑

### 1. 使用 HTTPS（推荐）

在生产环境中，建议使用 HTTPS 而不是 HTTP。可以通过以下方式实现：

#### 方案 A：使用反向代理（Nginx）

```nginx
# /etc/nginx/sites-available/sysom-mcp
server {
    listen 443 ssl;
    server_name mcp.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location /mcp/unified {
        proxy_pass http://127.0.0.1:7140;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

然后客户端连接到 `https://mcp.example.com/mcp/unified`。

#### 方案 B：在 MCP 服务器中直接支持 HTTPS

需要修改 `sysom_main_mcp.py` 以支持 SSL/TLS。

### 2. 认证和授权

当前实现没有内置认证机制。建议：

1. **使用防火墙限制访问**：只允许特定 IP 访问
2. **使用 API Key**：在 HTTP 请求头中添加 API Key 验证
3. **使用 VPN**：将 MCP 服务器放在 VPN 网络中
4. **使用反向代理认证**：在 Nginx 等反向代理中配置基本认证

### 3. 网络隔离

- 将 MCP 服务器部署在内网
- 使用私有 IP 地址
- 通过 VPN 或专线连接

## 故障排查

### 问题 1：无法连接到服务器

**检查项：**
1. 服务器是否正在运行：`ps aux | grep sysom_main_mcp`
2. 端口是否监听：`netstat -tlnp | grep 7140`
3. 防火墙是否允许：`sudo firewall-cmd --list-ports`
4. 网络是否可达：`ping <服务器IP>`
5. 端口是否开放：`telnet <服务器IP> 7140` 或 `nc -zv <服务器IP> 7140`

### 问题 2：连接超时

**可能原因：**
1. 防火墙阻止了连接
2. 服务器监听地址不正确（应该使用 `0.0.0.0` 而不是 `127.0.0.1`）
3. 网络路由问题

**解决方案：**
- 检查服务器启动命令中的 `--host` 参数
- 检查防火墙规则
- 检查网络配置

### 问题 3：工具调用失败

**检查项：**
1. 环境变量是否正确设置（ACCESS_KEY_ID、ACCESS_KEY_SECRET 等）
2. 服务器日志：查看 stderr 输出或 systemd 日志
3. 网络连接是否稳定

### 问题 4：Qwen Code 不支持 SSE 模式

如果 Qwen Code 只支持 stdio 模式，可以考虑：

1. **使用本地代理**：在客户端机器上运行一个本地代理，将 stdio 请求转发到远程 SSE 服务器
2. **使用 SSH 隧道**：通过 SSH 端口转发将远程服务器映射到本地
3. **等待 Qwen Code 更新**：关注 Qwen Code 的更新，看是否添加 SSE 支持

## 性能优化

1. **使用进程管理器**：使用 systemd、supervisor 或 pm2 管理进程
2. **负载均衡**：如果有多台服务器，可以使用负载均衡器
3. **监控和日志**：配置日志收集和监控系统
4. **资源限制**：设置适当的 CPU 和内存限制

## 示例配置

### 完整示例：服务器端

```bash
# 1. 启动服务器
cd /root/sysom_mcp
uv run python sysom_main_mcp.py --sse --host 0.0.0.0 --port 7140 --path /mcp/unified

# 2. 配置防火墙
sudo firewall-cmd --permanent --add-port=7140/tcp
sudo firewall-cmd --reload

# 3. 验证
curl http://localhost:7140/mcp/unified
```

### 完整示例：客户端

```json
{
  "mcpServers": {
    "sysom_mcp_remote": {
      "transport": "sse",
      "url": "http://192.168.1.100:7140/mcp/unified",
      "timeout": 30000
    }
  }
}
```

## 参考资源

- [MCP 协议规范](https://modelcontextprotocol.io/)
- [FastMCP 文档](https://github.com/jlowin/fastmcp)
- [SSE (Server-Sent Events) 规范](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)

