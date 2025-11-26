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

```bash
docker run -it --rm \
  -v $(pwd)/src:/workspace/src \
  -v $(pwd)/requirements.txt:/workspace/requirements.txt \
  --name sysom-mcp-dev \
  sysom-mcp-dev:latest
```

**参数说明：**
- `-it`: 交互式终端
- `--rm`: 容器退出时自动删除
- `-v $(pwd)/src:/workspace/src`: 挂载源代码目录，实现代码实时同步
- `-v $(pwd)/requirements.txt:/workspace/requirements.txt`: 挂载 requirements.txt（可选）
- `--name sysom-mcp-dev`: 指定容器名称

#### 方式二：后台运行并进入

```bash
# 启动容器
docker run -d \
  -v $(pwd)/src:/workspace/src \
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

进入容器后，工作目录默认为 `/workspace/src`，所有源代码已挂载，修改会实时同步到宿主机。

```bash
# 查看 Python 版本
python --version

# 运行测试
python -m pytest tests/

# 运行特定模块
python -m mcp.am_mcp
```

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
- **非 root 用户**: 使用 `developer` 用户运行，提高安全性
- **代码挂载**: 支持代码实时同步，无需重新构建镜像

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
- 容器内使用非 root 用户 `developer`（UID 1000）
- 如需使用网络服务（如数据库、Redis），确保网络配置正确

