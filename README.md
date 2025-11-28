# SysOM MCP 项目

## 开发环境

本项目使用 Docker 开发容器进行开发，基于 Python 3.11。

## 构建开发容器

### 前置要求

- Docker 已安装并运行
- 确保有足够的磁盘空间（建议至少 2GB）

### 构建步骤

1. **构建 Docker 镜像**

   在项目根目录执行：

   ```bash
   docker build -t sysom-mcp-dev:latest .
   ```

   这将创建一个名为 `sysom-mcp-dev:latest` 的开发镜像。

2. **验证镜像构建成功**

   ```bash
   docker images | grep sysom-mcp-dev
   ```

## 使用开发容器

### 运行开发容器

#### 方式一：交互式运行（推荐用于开发）

**挂载整个项目目录（包括 .env 文件）：**

```bash
docker run -it --rm \
  -v $(pwd):/workspace \
  --name sysom-mcp-dev \
  sysom-mcp-dev:latest
```

**参数说明：**
- `-it`: 交互式终端
- `--rm`: 容器退出时自动删除
- `-v $(pwd):/workspace`: 挂载整个项目目录到容器，包括 `.env` 文件，实现代码实时同步
- `--name sysom-mcp-dev`: 指定容器名称

**注意：**
- 容器以 root 用户运行，可以访问所有文件（包括 `.env`）
- 工作目录为 `/workspace`（项目根目录），可以直接访问 `.env` 文件
- 代码修改会实时同步到宿主机

#### 方式二：后台运行并进入

```bash
# 启动容器（挂载整个项目目录）
docker run -d \
  -v $(pwd):/workspace \
  --name sysom-mcp-dev \
  sysom-mcp-dev:latest \
  tail -f /dev/null

# 进入容器
docker exec -it sysom-mcp-dev /bin/bash
```

#### 方式三：使用 docker-compose（如果项目中有 docker-compose.yml）

```bash
docker-compose up -d
docker-compose exec dev /bin/bash
```

### 在容器内工作

进入容器后，工作目录默认为 `/workspace`（项目根目录），所有文件已挂载，修改会实时同步到宿主机。

```bash
# 查看 Python 版本
python --version

# 查看项目文件（包括 .env）
ls -la

# 进入源代码目录
cd src

# 运行测试
python -m pytest tests/

# 运行特定模块
python -m mcp.am_mcp

# 运行客户端测试（需要 .env 文件中的 DASHSCOPE_API_KEY）
python tests/client.py mcp/am_mcp.py
```

**重要提示：**
- `.env` 文件位于项目根目录 `/workspace/.env`
- 确保 `.env` 文件中已配置 `DASHSCOPE_API_KEY` 等必要的环境变量
- 容器以 root 用户运行，拥有所有文件访问权限

### 停止和清理

```bash
# 停止容器
docker stop sysom-mcp-dev

# 删除容器（如果使用 --rm 参数则不需要）
docker rm sysom-mcp-dev

# 删除镜像（可选）
docker rmi sysom-mcp-dev:latest
```

## 开发容器特性

- **Python 3.11**: 稳定版本
- **预装依赖**: 所有 `requirements.txt` 中的依赖已安装
- **系统工具**: 包含 git、vim、curl 等常用开发工具
- **Root 用户**: 容器以 root 用户运行，可以访问所有文件（包括 `.env`）
- **代码挂载**: 支持代码实时同步，无需重新构建镜像
- **项目根目录**: 工作目录为项目根目录，可直接访问 `.env` 文件

## 常见问题

### 1. 如何更新依赖？

修改 `requirements.txt` 后，在容器内执行：

```bash
pip install -r /workspace/requirements.txt
```

或者重新构建镜像：

```bash
docker build -t sysom-mcp-dev:latest .
```

### 2. 如何安装额外的系统包？

如果需要安装额外的系统包，可以：

- 修改 Dockerfile，添加所需的包
- 或者在运行的容器内临时安装（不推荐，容器重启后会丢失）

### 3. 权限问题

如果遇到文件权限问题，确保挂载的目录权限正确：

```bash
# 在宿主机上检查权限
ls -la src/
```

## 项目结构

```
sysom_mcp/
├── Dockerfile          # 开发容器定义文件
├── README.md          # 本文件
└── src/               # 源代码目录
    ├── requirements.txt
    ├── mcp/           # MCP 模块
    └── tests/         # 测试文件
```

## 注意事项

- 开发容器中的代码通过 volume 挂载，修改会实时同步
- 容器以 root 用户运行，拥有所有文件访问权限
- `.env` 文件位于项目根目录，确保已正确配置必要的环境变量
- 如需使用网络服务（如数据库、Redis），确保网络配置正确

