"""开通sysom MCP Helper实现

负责开通sysom MCP工具逻辑
"""
from typing import Dict, Any, Optional, TYPE_CHECKING
from pydantic import BaseModel, Field
from .logger_config import setup_logger
from .mcp_helper import MCPHelper, MCPRequest, MCPResponse

logger = setup_logger(__name__)
from .openapi_client import OpenAPIClient, AlibabaCloudSDKClient
from .api_registry import APIRegistry
from alibabacloud_sysom20231230 import models as sysom_20231230_models
from Tea.model import TeaModel

class InitialResultCode:
    """初始化结果状态码常量"""
    SUCCESS = "Success"
    ERROR = "Error"

# 全局缓存：存储用户的开通状态
# key: uid (str), value: bool (True表示已开通，False表示未开通)
_sysom_initialed_cache: Dict[str, bool] = {}

def get_sysom_initialed_status(uid: str) -> Optional[bool]:
    """
    获取用户的开通状态（从缓存）
    
    Args:
        uid: 用户ID
        
    Returns:
        True表示已开通，False表示未开通，None表示未缓存
    """
    return _sysom_initialed_cache.get(uid)

def set_sysom_initialed_status(uid: str, is_initialed: bool) -> None:
    """
    设置用户的开通状态（写入缓存）
    
    Args:
        uid: 用户ID
        is_initialed: 是否已开通
    """
    _sysom_initialed_cache[uid] = is_initialed
    logger.info(f"缓存用户 {uid} 的开通状态: {is_initialed}")

def clear_sysom_initialed_cache(uid: Optional[str] = None) -> None:
    """
    清除缓存
    
    Args:
        uid: 用户ID，如果为None则清除所有缓存
    """
    if uid is None:
        _sysom_initialed_cache.clear()
        logger.info("已清除所有用户的开通状态缓存")
    else:
        _sysom_initialed_cache.pop(uid, None)
        logger.info(f"已清除用户 {uid} 的开通状态缓存")

class InitialSysomMCPHelper(MCPHelper):
    """开通sysom MCP Helper实现"""
    async def initial_sysom(
        self,
        check_only: bool = False,
        uid: Optional[str] = None,
    ) -> MCPResponse:
        """
        开通sysom MCP工具
        
        Args:
            check_only: 是否仅检查（不实际开通）
            uid: 用户ID（用于缓存）
        """
        
        api_name = "initial_sysom"
        
        # 注册路由（如果尚未注册）
        registry = APIRegistry()
        if registry.get_route(api_name) is None:

            # 注册SDK路由
            registry.register_sdk(
                api_name=api_name,
                request_model=sysom_20231230_models.InitialSysomRequest,
                response_model=sysom_20231230_models.InitialSysomResponse,
                client_method=lambda client, req: client.initial_sysom_async(req)
            )
        # SDK调用：传入TeaModel
        initial_request = sysom_20231230_models.InitialSysomRequest(
            check_only= check_only,
            source = "mcp"
        )
        # 调用initial_sysom接口
        success, response_data, error_msg = await self.client.call_api(
            api_name=api_name,
            request=initial_request
        )
        if not success:
            # 如果检查失败，缓存未开通状态
            if check_only and uid:
                set_sysom_initialed_status(uid, False)
            return MCPResponse(
                code=InitialResultCode.ERROR,
                message=error_msg or "开通sysom失败，请前往https://alinux.console.aliyun.com进行开通",
                data=None
            )
        
        # 如果成功，更新缓存
        if uid:
            if check_only:
                # 检查成功，缓存已开通状态
                set_sysom_initialed_status(uid, True)
            else:
                # 实际开通成功，缓存已开通状态
                set_sysom_initialed_status(uid, True)
        
        return MCPResponse(
            code=InitialResultCode.SUCCESS,
            message="initial sysom调用成功",
            data=response_data
        )
    
    