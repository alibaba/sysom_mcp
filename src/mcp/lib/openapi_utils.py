import threading
from .logger_config import setup_logger
from sysom_utils import SysomFramework, CmgPlugin
from typing import Any, Optional

logger = setup_logger(__name__)
from Tea.model import TeaModel
from alibabacloud_credentials.client import Client as CredClient
from alibabacloud_credentials.models import Config as CreConfig
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_sysom20231230.client import Client as SysOM20231230Client

OPENAPI_CONNECT_TIMEOUT = 2000

# SysomFramework初始化相关
_framework_init_lock = threading.Lock()
_framework_initialized = False

def init_framework():
    """初始化SysomFramework（线程安全，只初始化一次）"""
    global _framework_initialized
    
    if _framework_initialized:
        # logger.error("SysomFramework already initialized, skip")
        return
    
    with _framework_init_lock:
        if _framework_initialized:
            return
        
        # 注意：如果 SysomFramework 需要 YAML_CONFIG，可能需要从 .env 或其他方式提供
        # 这里暂时注释掉，如果框架初始化失败，需要根据实际情况调整
        try:
            # 尝试使用 None 或创建默认配置
            # 如果 SysomFramework.init 需要配置对象，可能需要创建适配器
            SysomFramework\
                .init(None) \
                .load_plugin_cls(CmgPlugin) \
                .start()
        except Exception as e:
            logger.error(f"SysomFramework 初始化失败: {e}")
            logger.warning("提示：如果 SysomFramework 需要配置，请检查是否需要提供 YAML_CONFIG")
            raise
        
        _framework_initialized = True
        # logger.error("SysomFramework init finished!")

def create_sysom_client(
    mode: str,
    access_key_id: str,
    access_key_secret: str,
    security_token: Optional[str] = None,
):
    """Use STS secrets to generate Client
    Args:
        access_key_id:      STS temporary access key
        access_key_secret:  STS temporary access key secret
        security_token:     STS security token
        region_id:          Machine region
    Returns:
        Ecs20140526Client
    """
    credentialClient = None
    if mode == "access_key":
        credentialsConfig = CreConfig(
            type='access_key',
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
        )
        credentialClient = CredClient(credentialsConfig)
    elif mode == "sts" and security_token is not None:
        credentialsConfig = CreConfig(
            type='sts',
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            security_token=security_token
        )
        credentialClient = CredClient(credentialsConfig)
    else:
        raise Exception("Invalid mode: {mode}")
    
    config = open_api_models.Config(
        credential=credentialClient,
        connect_timeout=OPENAPI_CONNECT_TIMEOUT
    )
    config.endpoint = f'sysom.cn-hangzhou.aliyuncs.com'
    return SysOM20231230Client(config)