from typing import Optional
from fastmcp import FastMCP, Context
from pydantic import Field
from lib.logger_config import setup_logger

logger = setup_logger(__name__)
from lib import (
    ClientFactory,
    DiagnosisMCPHelper,
    DiagnosisMCPRequest,
    DiagnosisMCPResponse,
    DiagnosisMCPRequestParams,
    DiagnoseResultCode,
)
from lib.service_config import SERVICE_CONFIG

mcp = FastMCP("SysomDiagnoseSubMCP")

# delay诊断请求参数示例
# {\"instance\":\"i-wz9fckjns2yegqca8t9q\",\"duration\":\"20\",\"threshold\":\"20\",\"region\":\"cn-shenzhen\",\"instanceName\":\"\"}

class DelayDiagnosisMCPRequestParams(DiagnosisMCPRequestParams):
    """delay诊断请求参数"""
    instance: str = Field(..., description="实例ID")
    duration: Optional[str] = Field(None, description="诊断时长(s)")
    threshold: Optional[str] = Field(None, description="抖动阈值(ms)")

@mcp.tool(
    tags={"sysom_scheddiag"}
)
async def delay(
    uid: str = Field(..., description="用户ID"),
    region: str = Field(..., description="实例地域"),
    channel: str = Field(..., description="诊断通道"),
    instance: str = Field(..., description="实例ID"),
    duration: Optional[str] = Field(None, description="诊断时长(s)"),
    threshold: Optional[str] = Field(None, description="抖动阈值(ms)"),
    ctx: Context | None = None,
) -> DiagnosisMCPResponse:
    """delay（调度抖动诊断）工具主要分析CPU长时间不进行任务切换导致用户态业务进程长期得不到调度引发的问题（例如内存回收等场景）。
    仅支持节点诊断模式，channel必须为ecs。
    参数说明：
        uid: 用户ID
        region: 实例地域
        channel: 诊断通道，仅支持ecs诊断通道
        instance: 实例ID
        duration: 诊断持续的时长(s)（可选），默认为20秒
        threshold: 判定出现抖动的阈值(ms)（可选），默认为20ms
    示例：
        - {"uid": "123456789", "channel":"ecs", "instance":"i-wz9fckjns2yegqca8t9q","region":"cn-shenzhen"}
        - {"uid": "123456789", "channel":"ecs", "instance":"i-wz9fckjns2yegqca8t9q","duration":"30","threshold":"20","region":"cn-shenzhen"}
    返回值:
        DiagnoseResult: 诊断结果
            code: 状态码，可能的值：
                - Success: 诊断成功
                - TaskCreateFailed: 任务创建失败
                - TaskExecuteFailed: 任务执行失败
                - TaskTimeout: 任务执行超时
                - ResultParseFailed: 结果解析失败
                - GetResultFailed: 获取结果失败
            message: 详细的错误信息，当code不为Success时提供
            task_id: 任务ID
            result: 诊断结果，当code为Success时包含诊断结果
    """
    try:
        client = ClientFactory.create_client(
            deploy_mode=getattr(SERVICE_CONFIG, 'deploy_mode', 'sysom_framework'),
            uid=uid
        )
        helper = DiagnosisMCPHelper(client, timeout=150, poll_interval=1)
        params_obj = DelayDiagnosisMCPRequestParams(
            region=region,
            instance=instance,
            duration=duration,
            threshold=threshold,
        )
        params = params_obj.model_dump(exclude_none=True, by_alias=True)
        mcp_request = DiagnosisMCPRequest(
            service_name="delay",
            channel=channel,
            region=region,
            params=params
        )
        return await helper.execute(mcp_request)
    except Exception as e:
        logger.error(f"delay诊断失败: {e}")
        return DiagnosisMCPResponse(
            code=DiagnoseResultCode.TASK_CREATE_FAILED,
            message=f"诊断失败：{str(e)}",
            task_id=""
        )

# loadtask诊断请求参数示例
# {\"instance\":\"i-wz9fckjns2yegqca8t9q\",\"region\":\"cn-shenzhen\",\"instanceName\":\"\"}

class LoadTaskDiagnosisMCPRequestParams(DiagnosisMCPRequestParams):
    """loadtask诊断请求参数"""
    instance: str = Field(..., description="实例ID")

@mcp.tool(
    tags={"sysom_scheddiag"}
)
async def loadtask(
    uid: str = Field(..., description="用户ID"),
    region: str = Field(..., description="实例地域"),
    channel: str = Field(..., description="诊断通道"),
    instance: str = Field(..., description="实例ID"),
    ctx: Context | None = None,
) -> DiagnosisMCPResponse:
    """loadtask（系统负载诊断）工具主要分析系统在一分钟内的平均负载(load1指标)异常原因机器详细信息。
    仅支持节点诊断模式，channel必须为ecs。
    参数说明：
        uid: 用户ID
        region: 实例地域
        channel: 诊断通道，仅支持ecs诊断通道
        instance: 实例ID
    示例：
        - {"uid": "123456789", "channel":"ecs", "instance":"i-wz9fckjns2yegqca8t9q","region":"cn-shenzhen"}
    返回值:
        DiagnoseResult: 诊断结果
            code: 状态码，可能的值：
                - Success: 诊断成功
                - TaskCreateFailed: 任务创建失败
                - TaskExecuteFailed: 任务执行失败
                - TaskTimeout: 任务执行超时
                - ResultParseFailed: 结果解析失败
                - GetResultFailed: 获取结果失败
            message: 详细的错误信息，当code不为Success时提供
            task_id: 任务ID
            result: 诊断结果，当code为Success时包含诊断结果
    """
    try:
        client = ClientFactory.create_client(
            deploy_mode=getattr(SERVICE_CONFIG, 'deploy_mode', 'sysom_framework'),
            uid=uid
        )
        helper = DiagnosisMCPHelper(client, timeout=150, poll_interval=1)
        params_obj = LoadTaskDiagnosisMCPRequestParams(region=region, instance=instance)
        params = params_obj.model_dump(exclude_none=True, by_alias=True)
        mcp_request = DiagnosisMCPRequest(
            service_name="loadtask",
            channel=channel,
            region=region,
            params=params
        )
        return await helper.execute(mcp_request)
    except Exception as e:
        logger.error(f"loadtask诊断失败: {e}")
        return DiagnosisMCPResponse(
            code=DiagnoseResultCode.TASK_CREATE_FAILED,
            message=f"诊断失败：{str(e)}",
            task_id=""
        )

def create_mcp_server():
    return mcp

if __name__ == "__main__":
    # 日志级别已通过 logger_config 配置
    create_mcp_server().run(transport="stdio")

