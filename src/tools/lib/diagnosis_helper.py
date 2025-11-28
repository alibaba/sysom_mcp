"""诊断MCP Helper实现

负责诊断相关的MCP工具逻辑，包括：
1. 参数转换
2. 调用诊断接口
3. 轮询查询结果
"""
import json
import asyncio
from typing import Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from .logger_config import setup_logger
from .mcp_helper import MCPHelper, MCPRequest, MCPResponse

logger = setup_logger(__name__)
from .openapi_client import OpenAPIClient, AlibabaCloudSDKClient
from .api_registry import APIRegistry
from alibabacloud_sysom20231230 import models as sysom_20231230_models
from Tea.model import TeaModel


class DiagnoseResultCode:
    """诊断结果状态码常量"""
    SUCCESS = "Success"
    TASK_CREATE_FAILED = "TaskCreateFailed"
    TASK_EXECUTE_FAILED = "TaskExecuteFailed"
    TASK_TIMEOUT = "TaskTimeout"
    RESULT_PARSE_FAILED = "ResultParseFailed"
    GET_RESULT_FAILED = "GetResultFailed"


class DiagnosisMCPRequestParams(MCPRequest):
    """诊断MCP请求参数基类
    
    每个诊断项可以继承此类并添加自己的额外参数字段
    """
    region: str = Field(..., description="地域")
    hide: str = Field(default="0", alias="_hide", description="隐藏字段")


class DiagnosisMCPRequest(MCPRequest):
    """诊断MCP请求参数"""
    service_name: str = Field(..., description="诊断服务名称")
    channel: str = Field(..., description="诊断通道")
    region: str = Field(..., description="地域")
    params: Dict[str, Any] = Field(default_factory=dict, description="诊断参数")


class DiagnosisMCPResponse(MCPResponse):
    """诊断MCP响应"""
    task_id: str = Field(default="", description="任务ID")
    result: Dict[str, Any] = Field(default_factory=dict, description="诊断结果")


class DiagnosisMCPHelper(MCPHelper):
    """诊断MCP Helper实现"""
    
    def __init__(
        self,
        client: OpenAPIClient,
        timeout: int = 150,
        poll_interval: int = 1
    ):
        """
        初始化诊断Helper
        
        Args:
            client: OpenAPI客户端
            timeout: 诊断超时时间（秒）
            poll_interval: 轮询间隔（秒）
        """
        super().__init__(client)
        self.timeout = timeout
        self.poll_interval = poll_interval
    
    async def execute(self, request: DiagnosisMCPRequest) -> DiagnosisMCPResponse:
        """
        执行诊断流程
        
        Args:
            request: 诊断请求参数
            
        Returns:
            DiagnosisMCPResponse: 诊断响应
        """
        # 1. 准备参数并发起诊断
        params_json = json.dumps(request.params, ensure_ascii=False)
        
        api_name = "invoke_diagnosis"
        
        # 注册路由（如果尚未注册）
        registry = APIRegistry()
        if registry.get_route(api_name) is None:
            
            # 注册SDK路由
            registry.register_sdk(
                api_name=api_name,
                request_model=sysom_20231230_models.InvokeDiagnosisRequest,
                response_model=sysom_20231230_models.InvokeDiagnosisResponse,
                client_method=lambda client, req: client.invoke_diagnosis_async(req)
            )
        
        # SDK调用：传入TeaModel
        invoke_request = sysom_20231230_models.InvokeDiagnosisRequest(
            service_name=request.service_name,
            channel=request.channel,
            params=params_json
        )
        
        # 调用invoke_diagnosis接口
        success, response_data, error_msg = await self.client.call_api(
            api_name=api_name,
            request=invoke_request
        )
        
        if not success:
            return DiagnosisMCPResponse(
                code=DiagnoseResultCode.TASK_CREATE_FAILED,
                message=error_msg or "发起诊断失败",
                task_id=""
            )
        
        # 如果是TeaModel，先转换为字典
        if isinstance(response_data, TeaModel):
            response_data = response_data.to_map()
        
        # 统一按字典处理
        if response_data.get("code") == "Success":
            task_id = response_data.get("data", {}).get("task_id", "")
        else:
            return DiagnosisMCPResponse(
                code=DiagnoseResultCode.TASK_CREATE_FAILED,
                message=response_data.get("message", "发起诊断失败"),
                task_id=""
            )
        
        
        # 2. 轮询获取结果
        code, message, result = await self._wait_for_result(task_id)
        
        if code == DiagnoseResultCode.SUCCESS:
            # 解析结果
            if isinstance(result, str):
                try:
                    result_dict = json.loads(result)
                except (json.JSONDecodeError, TypeError) as e:
                    return DiagnosisMCPResponse(
                        task_id=task_id,
                        code=DiagnoseResultCode.RESULT_PARSE_FAILED,
                        message=f"结果解析失败：{str(e)}，原始结果：{result[:200]}",
                        result={"raw": result}
                    )
            elif isinstance(result, dict):
                result_dict = result
            else:
                return DiagnosisMCPResponse(
                    task_id=task_id,
                    code=DiagnoseResultCode.RESULT_PARSE_FAILED,
                    message=f"结果类型异常：{type(result)}，期望字符串或字典",
                    result={"raw": str(result)}
                )
            
            return DiagnosisMCPResponse(
                task_id=task_id,
                code=DiagnoseResultCode.SUCCESS,
                result=result_dict
            )
        else:
            return DiagnosisMCPResponse(
                task_id=task_id,
                code=code,
                message=message
            )
    
    async def _wait_for_result(self, task_id: str) -> Tuple[str, str, Any]:
        """
        轮询等待诊断结果
        
        Args:
            task_id: 诊断任务ID
            
        Returns:
            Tuple[str, str, Any]: (状态码, 错误信息或空字符串, 诊断结果或None)
        """
        start_time = asyncio.get_event_loop().time()
        
        api_name = "get_diagnosis_result"
        
        # 注册路由（如果尚未注册）
        registry = APIRegistry()
        if registry.get_route(api_name) is None:
            # 注册SDK路由
            registry.register_sdk(
                api_name=api_name,
                request_model=sysom_20231230_models.GetDiagnosisResultRequest,
                response_model=sysom_20231230_models.GetDiagnosisResultResponse,
                client_method=lambda client, req: client.get_diagnosis_result_async(req)
            )
        
        while (asyncio.get_event_loop().time() - start_time) < self.timeout:

            # SDK调用：传入TeaModel
            get_result_request = sysom_20231230_models.GetDiagnosisResultRequest(
                task_id=task_id
            )
            
            # 调用get_diagnosis_result接口
            success, response_data, error_msg = await self.client.call_api(
                api_name=api_name,
                request=get_result_request
            )
            
            if not success:
                return DiagnoseResultCode.GET_RESULT_FAILED, error_msg or "获取结果失败", None
            
            # 如果是TeaModel，先转换为字典
            if isinstance(response_data, TeaModel):
                response_data = response_data.to_map()
            
            # 统一按字典处理
            if response_data.get("code") == "Success":
                data = response_data.get("data", {})
                task_status = data.get("status")
                if task_status == "Fail":
                    return DiagnoseResultCode.TASK_EXECUTE_FAILED, data.get("err_msg", "任务执行失败"), None
                elif task_status == "Success":
                    return DiagnoseResultCode.SUCCESS, "", data.get("result")
                else:
                    await asyncio.sleep(self.poll_interval)
            else:
                return DiagnoseResultCode.GET_RESULT_FAILED, response_data.get("message", "获取结果失败"), None
        
        return DiagnoseResultCode.TASK_TIMEOUT, f"诊断执行超时（{self.timeout}秒），task_id: {task_id}", None

