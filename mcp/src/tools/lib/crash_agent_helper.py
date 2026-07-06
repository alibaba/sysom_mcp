from typing import Optional
from pydantic import Field, BaseModel
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_credentials.models import Config as CredentialConfig

from lib.service_config import SERVICE_CONFIG
from lib.api_registry import APIRegistry
from typing import Dict, Any, Optional, TYPE_CHECKING
from pydantic import BaseModel, Field
from .logger_config import setup_logger
from .mcp_helper import MCPHelper, MCPRequest, MCPResponse

logger = setup_logger(__name__)
from .openapi_client import OpenAPIClient, AlibabaCloudSDKClient
from .api_registry import APIRegistry
from alibabacloud_sysom20231230 import models as sysom_20231230_models
from Tea.model import TeaModel


class ResultCode:
    """AM服务结果状态码常量"""

    SUCCESS = "Success"
    ERROR = "Error"


class CrashAgentMCPHelper:
    """Crash Agent MCP辅助类"""

    def __init__(self, client=None):
        """初始化CrashAgentMCPHelper

        Args:
            client: OpenAPI客户端实例（可选）
        """
        self._client = client or self._create_default_client()

    async def create_task(
        self,
        request: sysom_20231230_models.CreateVmcoreDiagnosisTaskRequest,
    ) -> MCPResponse:
        from alibabacloud_sysom20231230 import models as sysom_20231230_models

        api_name = "create_task"

        # 注册路由（如果尚未注册）
        registry = APIRegistry()
        if registry.get_route(api_name) is None:

            # 注册SDK路由
            registry.register_sdk(
                api_name=api_name,
                request_model=sysom_20231230_models.CreateVmcoreDiagnosisTaskRequest,
                response_model=sysom_20231230_models.CreateVmcoreDiagnosisTaskResponse,
                client_method=lambda client, req: client.create_vmcore_diagnosis_task_async(
                    req
                ),
            )

        # 调用API
        success, response_data, error_msg = await self._client.call_api(
            api_name=api_name, request=request
        )

        if not success:
            logger.error(f"create_task failed: {error_msg}")
            return MCPResponse(
                code=ResultCode.ERROR, message=error_msg or "调用失败", data=None
            )

        # 转换响应
        result = self._convert_response(response_data)
        # 返回MCPResponse，由调用方转换为具体类型
        return MCPResponse(**result)

    async def get_task(
        self, request: sysom_20231230_models.GetVmcoreDiagnosisTaskRequest
    ) -> MCPResponse:
        from alibabacloud_sysom20231230 import models as sysom_20231230_models

        api_name = "get_task"

        # 注册路由（如果尚未注册）
        registry = APIRegistry()
        if registry.get_route(api_name) is None:

            # 注册SDK路由
            registry.register_sdk(
                api_name=api_name,
                request_model=sysom_20231230_models.GetVmcoreDiagnosisTaskRequest,
                response_model=sysom_20231230_models.GetVmcoreDiagnosisTaskResponse,
                client_method=lambda client, req: client.get_vmcore_diagnosis_task_async(
                    req
                ),
            )

        # 调用API
        success, response_data, error_msg = await self._client.call_api(
            api_name=api_name, request=request
        )

        if not success:
            logger.error(f"get_task failed: {error_msg}")
            return MCPResponse(
                code=ResultCode.ERROR, message=error_msg or "调用失败", data=None
            )

        # 转换响应
        result = self._convert_response(response_data)
        # 返回MCPResponse，由调用方转换为具体类型
        return MCPResponse(**result)

    async def list_task(
        self, request: sysom_20231230_models.ListVmcoreDiagnosisTaskRequest
    ) -> MCPResponse:
        from alibabacloud_sysom20231230 import models as sysom_20231230_models

        api_name = "list_task"

        # 注册路由（如果尚未注册）
        registry = APIRegistry()
        if registry.get_route(api_name) is None:

            # 注册SDK路由
            registry.register_sdk(
                api_name=api_name,
                request_model=sysom_20231230_models.ListVmcoreDiagnosisTaskRequest,
                response_model=sysom_20231230_models.ListVmcoreDiagnosisTaskResponse,
                client_method=lambda client, req: client.list_vmcore_diagnosis_task_async(
                    req
                ),
            )

        # 调用API
        success, response_data, error_msg = await self._client.call_api(
            api_name=api_name, request=request
        )

        if not success:
            logger.error(f"list_task failed: {error_msg}")
            return MCPResponse(
                code=ResultCode.ERROR, message=error_msg or "调用失败", data=None
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
        if hasattr(response_data, "to_map"):
            response_data = response_data.to_map()

        # 统一按字典处理
        code = response_data.get("code", ResultCode.ERROR)
        message = response_data.get("message", "")
        data = response_data.get("data")
        total = response_data.get("total")
        requestId = (
            response_data.get("request_id")
            or response_data.get("requestId")
            or response_data.get("RequestId")
        )

        # 如果没有total但data是列表，计算total
        if total is None and isinstance(data, list):
            total = len(data)

        return {
            "code": code,
            "message": message,
            "data": data,
            "total": total,
            "requestId": requestId,
        }
