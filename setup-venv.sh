#!/bin/bash

# Python 3.12 虚拟环境设置脚本

set -e

VENV_DIR="venv"
PYTHON_VERSION="3.12"
REQUIREMENTS_FILE="requirements.txt"

echo "=========================================="
echo "Python 3.12 虚拟环境设置脚本"
echo "=========================================="
echo ""

# 检查 Python 3.12 是否已安装
check_python312() {
    if command -v python3.12 &> /dev/null; then
        PYTHON_CMD="python3.12"
        echo "✓ 找到 Python 3.12: $(which python3.12)"
        python3.12 --version
        return 0
    else
        echo "✗ 未找到 Python 3.12"
        return 1
    fi
}

# 尝试使用 pyenv 安装 Python 3.12
install_with_pyenv() {
    if command -v pyenv &> /dev/null; then
        echo ""
        echo "检测到 pyenv，尝试安装 Python 3.12..."
        pyenv install -s ${PYTHON_VERSION} || {
            echo "pyenv 安装失败，请手动安装 Python 3.12"
            return 1
        }
        pyenv local ${PYTHON_VERSION}
        PYTHON_CMD="python"
        return 0
    else
        return 1
    fi
}

# 主逻辑
if ! check_python312; then
    echo ""
    echo "Python 3.12 未安装，尝试使用 pyenv 安装..."
    if ! install_with_pyenv; then
        echo ""
        echo "=========================================="
        echo "错误：未找到 Python 3.12"
        echo "=========================================="
        echo ""
        echo "请先安装 Python 3.12，可以使用以下方法："
        echo ""
        echo "方法一：使用 pyenv（推荐）"
        echo "  1. 安装 pyenv:"
        echo "     curl https://pyenv.run | bash"
        echo "  2. 配置环境变量（添加到 ~/.bashrc 或 ~/.zshrc）:"
        echo "     export PYENV_ROOT=\"\$HOME/.pyenv\""
        echo "     export PATH=\"\$PYENV_ROOT/bin:\$PATH\""
        echo "     eval \"\$(pyenv init -)\""
        echo "  3. 重新加载 shell 配置:"
        echo "     source ~/.bashrc"
        echo "  4. 安装 Python 3.12:"
        echo "     pyenv install 3.12.7"
        echo "     pyenv local 3.12.7"
        echo ""
        echo "方法二：从源码编译安装"
        echo "  参考: https://www.python.org/downloads/"
        echo ""
        echo "方法三：使用包管理器（根据系统选择）"
        echo "  - CentOS/RHEL: yum install python312"
        echo "  - Ubuntu/Debian: apt-get install python3.12"
        echo ""
        exit 1
    fi
fi

# 检查 requirements.txt 是否存在
if [ ! -f "$REQUIREMENTS_FILE" ]; then
    echo "错误: 未找到 $REQUIREMENTS_FILE 文件"
    exit 1
fi

# 删除已存在的虚拟环境
if [ -d "$VENV_DIR" ]; then
    echo ""
    echo "检测到已存在的虚拟环境，是否删除并重新创建？(y/N)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo "删除旧的虚拟环境..."
        rm -rf "$VENV_DIR"
    else
        echo "保留现有虚拟环境"
        exit 0
    fi
fi

# 创建虚拟环境
echo ""
echo "创建 Python 3.12 虚拟环境..."
$PYTHON_CMD -m venv "$VENV_DIR"

# 激活虚拟环境并升级 pip
echo ""
echo "激活虚拟环境并升级 pip..."
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip setuptools wheel

# 安装依赖
echo ""
echo "安装依赖包（这可能需要几分钟）..."
pip install -r "$REQUIREMENTS_FILE"

# 显示安装结果
echo ""
echo "=========================================="
echo "虚拟环境设置完成！"
echo "=========================================="
echo ""
echo "虚拟环境位置: $(pwd)/$VENV_DIR"
echo "Python 版本: $(python --version)"
echo ""
echo "激活虚拟环境:"
echo "  source $VENV_DIR/bin/activate"
echo ""
echo "退出虚拟环境:"
echo "  deactivate"
echo ""

