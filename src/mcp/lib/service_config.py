"""服务配置模块

从 .env 文件读取配置，提供 SERVICE_CONFIG 对象供其他模块使用
所有配置都从 .env 文件中读取
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# 获取项目根目录（假设 .env 文件在项目根目录）
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
ENV_FILE = BASE_DIR / ".env"

# 加载 .env 文件
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    # 如果项目根目录没有，尝试在 src 目录下查找
    SRC_ENV_FILE = BASE_DIR / "src" / ".env"
    if SRC_ENV_FILE.exists():
        load_dotenv(SRC_ENV_FILE)
    else:
        # 如果都没有，尝试加载当前目录的 .env
        load_dotenv()


class OpenAPIConfig:
    """OpenAPI 配置类
    
    从 .env 文件读取 OpenAPI 相关配置
    """
    
    def __init__(self):
        self.type = os.getenv("OPENAPI_TYPE", "access_key")
        self.access_key_id = os.getenv("OPENAPI_ACCESS_KEY_ID")
        self.access_key_secret = os.getenv("OPENAPI_ACCESS_KEY_SECRET")
        self.security_token = os.getenv("OPENAPI_SECURITY_TOKEN")


class LLMConfig:
    """LLM 配置类
    
    从 .env 文件读取 LLM 相关配置
    """
    
    def __init__(self):
        # DashScope API Key（阿里云百炼平台）
        self.dashscope_api_key = os.getenv("DASHSCOPE_API_KEY")
        # 兼容旧的环境变量名（用于测试文件）
        self.llm_ak = os.getenv("sysom_service___llm___llm_ak") or self.dashscope_api_key


class LogConfig:
    """日志配置类
    
    从 .env 文件读取日志相关配置
    """
    
    def __init__(self):
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()


class ServiceConfig:
    """服务配置类
    
    从 .env 文件读取所有配置，提供统一的配置访问接口
    """
    
    def __init__(self):
        # 部署模式：sysom_framework 或 alibabacloud_sdk
        self.deploy_mode = os.getenv("DEPLOY_MODE", "alibabacloud_sdk")
        # OpenAPI 配置
        self.openapi = OpenAPIConfig()
        # LLM 配置
        self.llm = LLMConfig()
        # 日志配置
        self.log = LogConfig()
        
        # 为了向后兼容，添加 api_key 属性（指向 llm.dashscope_api_key）
        self.api_key = self.llm.dashscope_api_key


# 创建全局配置实例
SERVICE_CONFIG = ServiceConfig()
