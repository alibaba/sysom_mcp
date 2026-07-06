"""AM服务MCP Helper实现

负责AM服务相关的MCP工具逻辑，每个tool对应一个独立的方法。
每个方法负责：
1. 将MCPRequest转换为OpenAPI的Request（TeaModel）
2. 调用OpenAPIClient的方法
3. 将OpenAPI的Response（TeaModel）转换为MCPResponse
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

if TYPE_CHECKING:
    # 避免循环导入，只在类型检查时导入
    pass


class AMResultCode:
    """AM服务结果状态码常量"""
    SUCCESS = "Success"
    ERROR = "Error"


class AMMCPHelper(MCPHelper):
    """AM服务MCP Helper实现
    
    为每个AM tool提供独立的方法
    """
    
    async def list_all_instances(
        self, 
        request: MCPRequest
    ) -> MCPResponse:
        """
        调用listAllInstances接口
        
        Args:
            request: ListAllInstancesMCPRequest (在am_mcp.py中定义)
            
        Returns:
            MCPResponse: 返回MCPResponse，调用方需要转换为ListAllInstancesMCPResponse
        """
        from alibabacloud_sysom20231230 import models as sysom_20231230_models
        
        api_name = "list_all_instances"
        
        # 注册路由（如果尚未注册）
        registry = APIRegistry()
        if registry.get_route(api_name) is None:

            # 注册SDK路由
            registry.register_sdk(
                api_name=api_name,
                request_model=sysom_20231230_models.ListAllInstancesRequest,
                response_model=sysom_20231230_models.ListAllInstancesResponse,
                client_method=lambda client, req: client.list_all_instances_async(req)
            )
        

        # SDK调用：传入TeaModel
        params = request.model_dump(exclude_none=True, by_alias=True)
        request_params = sysom_20231230_models.ListAllInstancesRequest.from_map(params)
        
        # 调用API
        success, response_data, error_msg = await self.client.call_api(
            api_name=api_name,
            request=request_params
        )
        
        if not success:
            logger.error(f"list_all_instances failed: {error_msg}")
            return MCPResponse(
                code=AMResultCode.ERROR,
                message=error_msg or "调用失败",
                data=None
            )
        
        # 转换响应
        result = self._convert_response(response_data)
        # 返回MCPResponse，由调用方转换为具体类型
        return MCPResponse(**result)
    
    async def list_pods_of_instance(
        self, 
        request: MCPRequest
    ) -> MCPResponse:
        """
        调用listPodsOfInstance接口
        
        Args:
            request: ListPodsOfInstanceMCPRequest (在am_mcp.py中定义)
            
        Returns:
            MCPResponse: 返回MCPResponse，调用方需要转换为ListPodsOfInstanceMCPResponse
        """
        api_name = "list_pods_of_instance"
        
        # 注册路由（如果尚未注册）
        registry = APIRegistry()
        if registry.get_route(api_name) is None:
            # 注册SDK路由
            registry.register_sdk(
                api_name=api_name,
                request_model=sysom_20231230_models.ListPodsOfInstanceRequest,
                response_model=sysom_20231230_models.ListPodsOfInstanceResponse,
                client_method=lambda client, req: client.list_pods_of_instance_async(req)
            )
        
        # SDK调用：传入TeaModel
        params = request.model_dump(exclude_none=True, by_alias=True)
        request_params = sysom_20231230_models.ListPodsOfInstanceRequest.from_map(params)
        # logger.error(f"list_pods_of_instance request (SDK): {request_params.to_map()}")
        
        # 调用API
        success, response_data, error_msg = await self.client.call_api(
            api_name=api_name,
            request=request_params
        )
        
        if not success:
            logger.error(f"list_pods_of_instance failed: {error_msg}")
            return MCPResponse(
                code=AMResultCode.ERROR,
                message=error_msg or "调用失败",
                data=None
            )
        
        # 转换响应
        result = self._convert_response(response_data)
        # 返回MCPResponse，由调用方转换为具体类型
        return MCPResponse(**result)
    
    async def list_clusters(
        self, 
        request: MCPRequest
    ) -> MCPResponse:
        """
        调用listClusters接口
        
        Args:
            request: ListClustersMCPRequest (在am_mcp.py中定义)
            
        Returns:
            MCPResponse: 返回MCPResponse，调用方需要转换为ListClustersMCPResponse
        """
        from alibabacloud_sysom20231230 import models as sysom_20231230_models
        
        api_name = "list_clusters"
        
        # 注册路由（如果尚未注册）
        registry = APIRegistry()
        if registry.get_route(api_name) is None:
            # 注册SDK路由
            registry.register_sdk(
                api_name=api_name,
                request_model=sysom_20231230_models.ListClustersRequest,
                response_model=sysom_20231230_models.ListClustersResponse,
                client_method=lambda client, req: client.list_clusters_async(req)
            )

        # SDK调用：传入TeaModel
        params = request.model_dump(exclude_none=True, by_alias=True)
        request_params = sysom_20231230_models.ListClustersRequest.from_map(params)
        
        # 调用API
        success, response_data, error_msg = await self.client.call_api(
            api_name=api_name,
            request=request_params
        )
        
        if not success:
            logger.error(f"list_clusters failed: {error_msg}")
            return MCPResponse(
                code=AMResultCode.ERROR,
                message=error_msg or "调用失败",
                data=None
            )
        
        # 转换响应
        result = self._convert_response(response_data)
        # 返回MCPResponse，由调用方转换为具体类型
        return MCPResponse(**result)
    
    async def list_instances(
        self, 
        request: MCPRequest
    ) -> MCPResponse:
        """
        调用listInstances接口
        
        Args:
            request: ListInstancesMCPRequest (在am_mcp.py中定义)
            
        Returns:
            MCPResponse: 返回MCPResponse，调用方需要转换为ListInstancesMCPResponse
        """
        from alibabacloud_sysom20231230 import models as sysom_20231230_models
        
        api_name = "list_instances"
        
        # 注册路由（如果尚未注册）
        registry = APIRegistry()
        if registry.get_route(api_name) is None:

            # 注册SDK路由
            registry.register_sdk(
                api_name=api_name,
                request_model=sysom_20231230_models.ListInstancesRequest,
                response_model=sysom_20231230_models.ListInstancesResponse,
                client_method=lambda client, req: client.list_instances_async(req)
            )
        
        # SDK调用：传入TeaModel
        params = request.model_dump(exclude_none=True, by_alias=True)
        request_params = sysom_20231230_models.ListInstancesRequest.from_map(params)
        
        # 调用API
        success, response_data, error_msg = await self.client.call_api(
            api_name=api_name,
            request=request_params
        )
        
        if not success:
            logger.error(f"list_instances failed: {error_msg}")
            return MCPResponse(
                code=AMResultCode.ERROR,
                message=error_msg or "调用失败",
                data=None
            )
        
        # 转换响应
        result = self._convert_response(response_data)
        # 返回MCPResponse，由调用方转换为具体类型
        return MCPResponse(**result)
    
    def _convert_response(self, response_data: Any) -> Dict[str, Any]:
        """
        将OpenAPI响应转换为统一的字典格式
        
        Args:
            response_data: OpenAPI响应（TeaModel或dict）
            
        Returns:
            Dict[str, Any]: 包含code, message, data, total, request_id的字典
        """
        # 如果是TeaModel，先转换为字典
        if hasattr(response_data, 'to_map'):
            response_data = response_data.to_map()
        
        # 统一按字典处理
        code = response_data.get("code", AMResultCode.ERROR)
        message = response_data.get("message", "")
        data = response_data.get("data")
        total = response_data.get("total")
        requestId = response_data.get("request_id") or response_data.get("requestId") or response_data.get("RequestId")
        
        # 如果没有total但data是列表，计算total
        if total is None and isinstance(data, list):
            total = len(data)
        
        return {
            "code": code,
            "message": message,
            "data": data,
            "total": total,
            "requestId": requestId
        }