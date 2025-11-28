#!/usr/bin/env python3
"""SysOM MCP 服务启动脚本

启动所有 MCP 服务器，提供统一的入口点
支持 stdio 和 SSE 两种启动模式，默认使用 stdio 模式
参考 test_client.py 的实现，但只启动服务，不创建客户端
"""
import subprocess
import logging
import sys
import signal
import time
import argparse
from pathlib import Path
from typing import Dict, Optional, Literal

# 获取项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"

# 添加 src 目录到 Python 路径
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# 导入 logger（如果可用）
# 注意：默认情况下所有日志输出到 stderr，不能输出到 stdout
# 因为 stdout 用于 MCP 协议的 JSON-RPC 通信
# 如果指定了 --stdout 参数，则输出到 stdout
def setup_logging_output(use_stdout: bool = False):
    """配置日志输出流
    
    Args:
        use_stdout: 如果为 True，输出到 stdout；否则输出到 stderr
    """
    output_stream = sys.stdout if use_stdout else sys.stderr
    
try:
    from tools.lib.logger_config import setup_logger
    logger = setup_logger(__name__)
        # 移除所有现有的 handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        # 创建新的 handler，输出到指定流
        stream_handler = logging.StreamHandler(output_stream)
        stream_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    except ImportError:
        # 配置日志输出到指定流
        logging.basicConfig(
            level=logging.INFO,
            stream=output_stream,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            force=True
        )
        logger = logging.getLogger(__name__)
        logger.propagate = False
    
    return logger

# 默认输出到 stderr（稍后可能会根据命令行参数修改）
logger = setup_logging_output(use_stdout=False)

# MCP 服务配置
# 支持 stdio 和 SSE 两种模式
# stdio 模式：所有 MCP 服务器都支持的标准模式，通过标准输入输出通信
# SSE 模式：支持 HTTP/SSE 的服务器可以通过 HTTP 访问
MCP_SERVICES = {
    # "am_mcp": {
    #     "script": "src/tools/am_mcp.py",
    #     "enabled": True,
    #     # SSE 模式配置（仅在 --mode sse 时使用）
    #     "sse": {
    #         "host": "127.0.0.1",
    #         "port": 7130,
    #         "path": "/mcp/am",
    #     },
    # },
    "mem_diag_mcp": {
        "script": "src/tools/mem_diag_mcp.py",
        "enabled": True,
        "sse": {
            "host": "127.0.0.1",
            "port": 7131,
            "path": "/mcp/mem_diag",
        },
    },
    "io_diag_mcp": {
        "script": "src/tools/io_diag_mcp.py",
        "enabled": True,
        "sse": {
            "host": "127.0.0.1",
            "port": 7132,
            "path": "/mcp/io_diag",
        },
    },
    "net_diag_mcp": {
        "script": "src/tools/net_diag_mcp.py",
        "enabled": True,
        "sse": {
            "host": "127.0.0.1",
            "port": 7133,
            "path": "/mcp/net_diag",
        },
    },
    "other_diag_mcp": {
        "script": "src/tools/other_diag_mcp.py",
        "enabled": True,
        "sse": {
            "host": "127.0.0.1",
            "port": 7134,
            "path": "/mcp/other_diag",
        },
    },
}

# 存储所有服务进程
_service_processes: Dict[str, subprocess.Popen] = {}

# 全局运行模式（stdio 或 sse）
_run_mode: Literal["stdio", "sse"] = "stdio"


def start_service(service_name: str, config: Dict, mode: Literal["stdio", "sse"] = "stdio") -> Optional[subprocess.Popen]:
    """启动单个 MCP 服务
    
    支持 stdio 和 SSE 两种模式：
    - stdio 模式：所有 MCP 服务器都支持的标准模式，通过标准输入输出通信
    - SSE 模式：支持 HTTP/SSE 的服务器可以通过 HTTP 访问
    
    Args:
        service_name: 服务名称
        config: 服务配置字典，包含 script、sse 等
        mode: 启动模式，"stdio" 或 "sse"，默认为 "stdio"
        
    Returns:
        subprocess.Popen: 服务进程对象，如果启动失败返回 None
    """
    if not config.get("enabled", False):
        logger.info(f"服务 {service_name} 未启用，跳过")
        return None
    
    script_path = PROJECT_ROOT / config["script"]
    
    if not script_path.exists():
        logger.error(f"服务脚本不存在: {script_path}")
        return None
    
    logger.info(f"正在启动服务: {service_name} (脚本: {script_path}, 模式: {mode})")
    
    try:
        is_python = str(script_path).endswith('.py')
        is_js = str(script_path).endswith('.js')
        
        if not (is_python or is_js):
            logger.error(f"服务脚本必须是 .py 或 .js 文件: {script_path}")
            return None
        
        command = "python" if is_python else "node"
        
        # 根据模式构建启动命令
        if mode == "sse":
            # SSE 模式：使用 --sse 参数，并指定 host、port、path
            sse_config = config.get("sse", {})
            host = sse_config.get("host", "127.0.0.1")
            port = sse_config.get("port", 7130)
            path = sse_config.get("path", "/mcp")
            
            cmd = [
                command,
                str(script_path),
                "--sse",
                "--host", host,
                "--port", str(port),
                "--path", path,
            ]
            
            # SSE 模式：服务器作为 HTTP 服务运行，不需要 stdin
            process = subprocess.Popen(
                cmd,
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            
            # 等待一下，检查进程是否正常启动
            time.sleep(2)
            if process.poll() is not None:
                try:
                    stdout, _ = process.communicate(timeout=1)
                    error_msg = stdout if stdout else "进程意外退出，无错误信息"
                    logger.error(f"服务 {service_name} 启动失败: {error_msg}")
                except:
                    logger.error(f"服务 {service_name} 启动失败: 进程意外退出")
                return None
            
            logger.info(f"服务 {service_name} 已启动，PID: {process.pid} (SSE 模式, URL: http://{host}:{port}{path})")
            
        else:
            # stdio 模式：默认模式，所有服务器都支持
            cmd = [
                command,
                str(script_path),
                "--stdio",  # 显式指定 stdio 模式
            ]
            
            # stdio 模式：服务器通过标准输入输出通信，需要提供 stdin
            process = subprocess.Popen(
                cmd,
                cwd=str(PROJECT_ROOT),
                stdin=subprocess.PIPE,  # 提供标准输入，防止服务器立即退出
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            
            # 等待一下，检查进程是否正常启动
            time.sleep(1)
            if process.poll() is not None:
                try:
                    stdout, _ = process.communicate(timeout=1)
                    error_msg = stdout if stdout else "进程意外退出，无错误信息"
                    logger.error(f"服务 {service_name} 启动失败: {error_msg}")
                except:
                    logger.error(f"服务 {service_name} 启动失败: 进程意外退出")
                return None
            
            logger.info(f"服务 {service_name} 已启动，PID: {process.pid} (stdio 模式)")
        
        return process
        
    except Exception as e:
        logger.error(f"启动服务 {service_name} 时出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def stop_service(service_name: str, process: subprocess.Popen):
    """停止单个 MCP 服务
    
    Args:
        service_name: 服务名称
        process: 服务进程对象
    """
    logger.info(f"正在停止服务: {service_name} (PID: {process.pid})")
    try:
        process.terminate()
        process.wait(timeout=5)
        logger.info(f"服务 {service_name} 已停止")
    except subprocess.TimeoutExpired:
        logger.warning(f"服务 {service_name} 未在 5 秒内停止，强制终止")
        process.kill()
        process.wait()
    except Exception as e:
        logger.error(f"停止服务 {service_name} 时出错: {e}")


def start_all_services(mode: Literal["stdio", "sse"] = "stdio"):
    """启动所有启用的 MCP 服务
    
    Args:
        mode: 启动模式，"stdio" 或 "sse"，默认为 "stdio"
    """
    global _run_mode
    _run_mode = mode
    
    logger.info("=" * 80)
    logger.info(f"开始启动所有 MCP 服务 (模式: {mode})")
    logger.info("=" * 80)
    
    for service_name, config in MCP_SERVICES.items():
        process = start_service(service_name, config, mode)
        if process:
            _service_processes[service_name] = process
        time.sleep(0.5)  # 短暂延迟，避免同时启动太多服务
    
    logger.info("=" * 80)
    logger.info(f"已启动 {len(_service_processes)} 个服务")
    logger.info("=" * 80)
    
    # 打印服务信息
    for service_name, process in _service_processes.items():
        config = MCP_SERVICES[service_name]
        script = config.get("script", "")
        if mode == "sse":
            sse_config = config.get("sse", {})
            host = sse_config.get("host", "127.0.0.1")
            port = sse_config.get("port", 7130)
            path = sse_config.get("path", "/mcp")
            logger.info(f"  - {service_name}: {script} (PID: {process.pid}, SSE 模式, URL: http://{host}:{port}{path})")
        else:
            logger.info(f"  - {service_name}: {script} (PID: {process.pid}, stdio 模式)")


def stop_all_services():
    """停止所有 MCP 服务"""
    logger.info("=" * 80)
    logger.info("正在停止所有 MCP 服务")
    logger.info("=" * 80)
    
    for service_name, process in list(_service_processes.items()):
        stop_service(service_name, process)
    
    _service_processes.clear()
    logger.info("所有服务已停止")


def signal_handler(signum, frame):
    """信号处理器，用于优雅关闭
    
    Args:
        signum: 信号编号
        frame: 当前堆栈帧
    """
    logger.info(f"收到信号 {signum}，正在关闭所有服务...")
    stop_all_services()
    sys.exit(0)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="SysOM MCP 服务启动脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
启动模式说明:
  stdio  - 标准输入输出模式（默认），所有 MCP 服务器都支持，通过标准输入输出通信
  sse    - Server-Sent Events 模式，支持 HTTP/SSE 的服务器可以通过 HTTP 访问

日志输出说明:
  默认情况下，所有日志输出到 stderr，避免干扰 MCP 协议的 stdout 通信
  如果指定 --stdout，则日志输出到 stdout

示例:
  # 使用默认 stdio 模式启动所有服务（日志输出到 stderr）
  python sysom_mcp.py

  # 使用 SSE 模式启动所有服务
  python sysom_mcp.py --mode sse

  # 使用 stdio 模式（显式指定）
  python sysom_mcp.py --mode stdio

  # 日志输出到 stdout（不推荐，会干扰 MCP 协议）
  python sysom_mcp.py --stdout
        """
    )
    parser.add_argument(
        "--mode",
        choices=["stdio", "sse"],
        default="stdio",
        help="启动模式：stdio（标准输入输出，默认）或 sse（Server-Sent Events）"
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="将日志输出到 stdout（默认输出到 stderr）"
    )
    return parser.parse_args()


def main():
    """主函数"""
    # 解析命令行参数
    args = parse_args()
    mode = args.mode
    use_stdout = args.stdout
    
    # 根据参数重新配置日志输出流
    global logger
    logger = setup_logging_output(use_stdout=use_stdout)
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 启动所有服务
        start_all_services(mode)
        
        if not _service_processes:
            logger.error("没有成功启动任何服务，退出")
            sys.exit(1)
        
        # 保持主进程运行，监控服务状态
        logger.info("所有服务运行中，按 Ctrl+C 停止...")
        while True:
            time.sleep(1)
            # 检查服务是否还在运行
            for service_name, process in list(_service_processes.items()):
                if process.poll() is not None:
                    logger.error(f"服务 {service_name} 意外退出，退出码: {process.returncode}")
                    # 读取错误输出
                    try:
                        stdout, _ = process.communicate(timeout=1)
                        if stdout:
                            logger.error(f"服务 {service_name} 错误输出: {stdout[:500]}")
                    except:
                        pass
                    # 从进程列表中移除
                    _service_processes.pop(service_name, None)
                    
    except KeyboardInterrupt:
        logger.info("收到中断信号")
    except Exception as e:
        logger.error(f"运行出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        stop_all_services()


if __name__ == "__main__":
    main()

