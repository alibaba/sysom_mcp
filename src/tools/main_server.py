# """MCP 服务主服务器

# 统一启动所有 MCP 服务的入口脚本
# """
# import subprocess
# import sys
# import signal
# import time
# from pathlib import Path
# from typing import Dict, Optional

# # 项目根目录（main_server.py 在 mcp/ 目录下，所以需要上一级目录）
# PROJECT_ROOT = Path(__file__).parent.parent

# # 添加项目根目录到 Python 路径，以便导入 lib 模块
# if str(PROJECT_ROOT) not in sys.path:
#     sys.path.insert(0, str(PROJECT_ROOT))

# from lib.logger_config import setup_logger

# logger = setup_logger(__name__)

# # MCP 服务配置
# MCP_SERVICES = {
#     "am_mcp": {
#         "module": "mcp.am_mcp",
#         "port": 7130,
#         "path": "/api/v1/am/mcp/",
#         "enabled": True,
#     },
#     # 其他服务可以在这里添加
#     # "net_diag_mcp": {
#     #     "module": "mcp.net_diag_mcp",
#     #     "port": 7131,
#     #     "path": "/api/v1/net_diag/mcp/",
#     #     "enabled": False,
#     # },
# }

# # 存储所有服务进程
# _service_processes: Dict[str, subprocess.Popen] = {}


# def start_service(service_name: str, config: Dict) -> Optional[subprocess.Popen]:
#     """启动单个 MCP 服务"""
#     if not config.get("enabled", False):
#         logger.info(f"服务 {service_name} 未启用，跳过")
#         return None
    
#     module = config["module"]
#     port = config.get("port", 7130)
#     path = config.get("path", "/api/v1/mcp/")
    
#     logger.info(f"正在启动服务: {service_name} (模块: {module}, 端口: {port}, 路径: {path})")
    
#     try:
#         # 使用 subprocess 启动服务
#         # 注意：am_mcp.py 使用 click，支持 --sse 参数
#         # 如果 FastMCP 的 run() 不支持 host/port/path，可能需要使用 create_app + uvicorn
#         # 确保在 src 目录下运行，这样 Python 才能找到 mcp 模块
#         process = subprocess.Popen(
#             [
#                 sys.executable,
#                 "-m",
#                 module,
#                 "--sse",
#             ],
#             cwd=str(PROJECT_ROOT),  # PROJECT_ROOT 应该是 src/ 目录
#             stdout=subprocess.PIPE,
#             stderr=subprocess.STDOUT,
#             text=True,
#             bufsize=1,
#         )
        
#         # 等待一下，检查进程是否正常启动
#         time.sleep(2)
#         if process.poll() is not None:
#             # 进程已退出，读取错误信息
#             stdout, _ = process.communicate()
#             error_msg = stdout if stdout else "进程意外退出，无错误信息"
#             logger.error(f"服务 {service_name} 启动失败: {error_msg}")
#             return None
        
#         logger.info(f"服务 {service_name} 已启动，PID: {process.pid}")
#         return process
        
#     except Exception as e:
#         logger.error(f"启动服务 {service_name} 时出错: {e}")
#         import traceback
#         logger.error(traceback.format_exc())
#         return None


# def stop_service(service_name: str, process: subprocess.Popen):
#     """停止单个 MCP 服务"""
#     logger.info(f"正在停止服务: {service_name} (PID: {process.pid})")
#     try:
#         process.terminate()
#         process.wait(timeout=5)
#         logger.info(f"服务 {service_name} 已停止")
#     except subprocess.TimeoutExpired:
#         logger.warning(f"服务 {service_name} 未在 5 秒内停止，强制终止")
#         process.kill()
#         process.wait()
#     except Exception as e:
#         logger.error(f"停止服务 {service_name} 时出错: {e}")


# def start_all_services():
#     """启动所有启用的 MCP 服务"""
#     logger.info("=" * 80)
#     logger.info("开始启动所有 MCP 服务")
#     logger.info("=" * 80)
    
#     for service_name, config in MCP_SERVICES.items():
#         process = start_service(service_name, config)
#         if process:
#             _service_processes[service_name] = process
#         time.sleep(0.5)  # 短暂延迟，避免同时启动太多服务
    
#     logger.info("=" * 80)
#     logger.info(f"已启动 {len(_service_processes)} 个服务")
#     logger.info("=" * 80)
    
#     # 打印服务信息
#     for service_name, process in _service_processes.items():
#         config = MCP_SERVICES[service_name]
#         logger.info(f"  - {service_name}: http://0.0.0.0:{config['port']}{config['path']} (PID: {process.pid})")


# def stop_all_services():
#     """停止所有 MCP 服务"""
#     logger.info("=" * 80)
#     logger.info("正在停止所有 MCP 服务")
#     logger.info("=" * 80)
    
#     for service_name, process in list(_service_processes.items()):
#         stop_service(service_name, process)
    
#     _service_processes.clear()
#     logger.info("所有服务已停止")


# def signal_handler(signum, frame):
#     """信号处理器，用于优雅关闭"""
#     logger.info(f"收到信号 {signum}，正在关闭所有服务...")
#     stop_all_services()
#     sys.exit(0)


# def main():
#     """主函数"""
#     # 注册信号处理器
#     signal.signal(signal.SIGINT, signal_handler)
#     signal.signal(signal.SIGTERM, signal_handler)
    
#     try:
#         # 启动所有服务
#         start_all_services()
        
#         # 保持主进程运行，监控服务状态
#         logger.info("所有服务运行中，按 Ctrl+C 停止...")
#         while True:
#             time.sleep(1)
#             # 检查服务是否还在运行
#             for service_name, process in list(_service_processes.items()):
#                 if process.poll() is not None:
#                     logger.error(f"服务 {service_name} 意外退出，退出码: {process.returncode}")
#                     # 可以选择重新启动服务
#                     # process = start_service(service_name, MCP_SERVICES[service_name])
#                     # if process:
#                     #     _service_processes[service_name] = process
                    
#     except KeyboardInterrupt:
#         logger.info("收到中断信号")
#     except Exception as e:
#         logger.error(f"运行出错: {e}")
#     finally:
#         stop_all_services()


# if __name__ == "__main__":
#     main()

