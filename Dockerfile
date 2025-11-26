# 使用 Anolis OS 23.2 作为基础镜像
FROM registry.openanolis.cn/openanolis/anolisos:23.2

# 设置工作目录
WORKDIR /workspace

# 安装系统依赖和 Python 3.11
# Anolis OS 使用 yum 包管理器
RUN yum install -y \
    gcc \
    gcc-c++ \
    make \
    libffi-devel \
    openssl-devel \
    pkgconfig \
    git \
    vim \
    curl \
    python3.11 \
    python3.11-pip \
    mariadb-devel \
    && yum clean all

# 安装 librdkafka（尝试从仓库安装，如果失败则从源码编译）
RUN yum install -y librdkafka-devel 2>/dev/null || \
    (yum install -y wget cmake autoconf automake libtool zlib-devel && \
    cd /tmp && \
    wget -q https://github.com/edenhill/librdkafka/archive/v2.3.0.tar.gz && \
    tar -xzf v2.3.0.tar.gz && \
    cd librdkafka-2.3.0 && \
    ./configure --prefix=/usr && \
    make -j$(nproc) && \
    make install && \
    cd / && rm -rf /tmp/librdkafka-2.3.0 /tmp/v2.3.0.tar.gz)

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/usr/bin:$PATH"

# 创建 Python 3.11 的软链接
RUN ln -sf /usr/bin/python3.11 /usr/bin/python3 && \
    ln -sf /usr/bin/python3.11 /usr/bin/python && \
    ln -sf /usr/bin/pip3.11 /usr/bin/pip3 && \
    ln -sf /usr/bin/pip3.11 /usr/bin/pip

# 升级 pip
RUN python3.11 -m pip install --upgrade pip setuptools wheel

# 复制 requirements.txt
COPY requirements.txt /workspace/requirements.txt

# 安装 Python 依赖
RUN python3.11 -m pip install -r /workspace/requirements.txt

# 复制项目代码（开发容器中，代码通常通过 volume 挂载，但这里先复制作为基础）
COPY src/ /workspace/src/

# 设置工作目录为 src
WORKDIR /workspace/src

# 创建非 root 用户（可选，用于开发）
RUN useradd -m -u 1000 developer && \
    chown -R developer:developer /workspace

# 切换到非 root 用户
USER developer

# 默认命令（可以根据需要修改）
CMD ["/bin/bash"]
