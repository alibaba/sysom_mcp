"""日志配置模块

提供统一的日志配置，使用 Python 标准库 logging
"""
import logging
import sys
from pathlib import Path

# 获取日志级别（从环境变量读取，默认为 INFO）
LOG_LEVEL = logging.INFO
log_level_str = None
try:
    import os
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    LOG_LEVEL = getattr(logging, log_level_str, logging.INFO)
except:
    pass


def setup_logger(name: str = None, level: int = None) -> logging.Logger:
    """
    设置并返回一个 logger 实例
    
    Args:
        name: logger 名称，默认为调用模块的名称
        level: 日志级别，默认为 LOG_LEVEL
        
    Returns:
        logging.Logger: 配置好的 logger 实例
    """
    if name is None:
        # 自动获取调用模块的名称
        import inspect
        frame = inspect.currentframe().f_back
        name = frame.f_globals.get('__name__', 'root')
    
    logger = logging.getLogger(name)
    
    # 如果 logger 已经有 handler，直接返回（避免重复配置）
    if logger.handlers:
        return logger
    
    logger.setLevel(level or LOG_LEVEL)
    
    # 创建控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level or LOG_LEVEL)
    
    # 创建格式器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # 添加 handler
    logger.addHandler(console_handler)
    
    # 防止日志向上传播到 root logger
    logger.propagate = False
    
    return logger


# 创建默认的 logger（用于向后兼容）
logger = setup_logger('sysom_mcp')

