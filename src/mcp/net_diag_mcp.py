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

# packetdrop诊断请求参数示例
# {\"instance\":\"i-wz9fckjns2yegqca8t9q\",\"region\":\"cn-shenzhen\",\"instanceName\":\"\"}

class PacketDropDiagnosisMCPRequestParams(DiagnosisMCPRequestParams):
    """packetdrop诊断请求参数"""
    instance: str = Field(..., description="实例名称")

@mcp.tool(
    tags={"sysom_netdiagnose"}
)
async def packetdrop(
    uid: str = Field(..., description="用户ID"),
    region: str = Field(..., description="实例地域"),
    channel: str = Field(..., description="诊断通道"),
    instance: str = Field(..., description="实例名称"),
    ctx: Context | None = None,
) -> DiagnosisMCPResponse:
    """
    packetdrop（网络丢包诊断）工具主要分析数据包通过网络传输过程中，由于多种原因在操作系统内核层面发生的丢失问题。
    使用场景：
        1. 由于系统配置错误导致的丢包，提示用户及时调整相关配置参数。
        2. 由于实例的iptables规则或驱动导致丢包，提示用户检查iptables配置或驱动。
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
        params_obj = PacketDropDiagnosisMCPRequestParams(region=region, instance=instance)
        params = params_obj.model_dump(exclude_none=True, by_alias=True)
        mcp_request = DiagnosisMCPRequest(
            service_name="packetdrop",
            channel=channel,
            region=region,
            params=params
        )
        return await helper.execute(mcp_request)
    except Exception as e:
        logger.error(f"packetdrop诊断失败: {e}")
        return DiagnosisMCPResponse(
            code=DiagnoseResultCode.TASK_CREATE_FAILED,
            message=f"诊断失败：{str(e)}",
            task_id=""
        )

# netjitter诊断请求参数示例
# {\"instance\":\"i-wz9fckjns2yegqca8t9q\",\"duration\":\"20\",\"threshold\":\"10\",\"region\":\"cn-shenzhen\",\"instanceName\":\"\"}

class NetJitterDiagnosisMCPRequestParams(DiagnosisMCPRequestParams):
    """netjitter诊断请求参数"""
    instance: str = Field(..., description="实例名称")
    duration: Optional[str] = Field(None, description="诊断时长(s)")
    threshold: Optional[str] = Field(None, description="抖动阈值(ms)")

@mcp.tool(
    tags={"sysom_netdiagnose"}
)
async def netjitter(
    uid: str = Field(..., description="用户ID"),
    region: str = Field(..., description="实例地域"),
    channel: str = Field(..., description="诊断通道"),
    instance: str = Field(..., description="实例名称"),
    duration: Optional[str] = Field(None, description="诊断时长(s)"),
    threshold: Optional[str] = Field(None, description="抖动阈值(ms)"),
    ctx: Context | None = None,
) -> DiagnosisMCPResponse:
    """netjitter（网络抖动诊断）工具主要分析数据包在网络传输过程中，由于多种因素引起的操作系统内核层面的不稳定现象。
    使用场景：
        1. 检测网络抖动是否由应用程序自身接收数据包速度缓慢所引起的。
        2. 检测网络抖动是否由内核软中断处理数据包速度缓慢所引起的。
        3. 检测网络抖动是否由内核qdisc队列处理数据包速度缓慢所引起的。
    仅支持节点诊断模式，channel必须为ecs。
    参数说明：
        uid: 用户ID
        region: 实例地域
        channel: 诊断通道，仅支持ecs诊断通道
        instance: 实例ID
        duration: 诊断持续的时长(s)（可选），默认为20秒
        threshold: 判定出现抖动的阈值(ms)（可选），默认为10ms
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
        params_obj = NetJitterDiagnosisMCPRequestParams(
            region=region,
            instance=instance,
            duration=duration,
            threshold=threshold,
        )
        params = params_obj.model_dump(exclude_none=True, by_alias=True)
        mcp_request = DiagnosisMCPRequest(
            service_name="netjitter",
            channel=channel,
            region=region,
            params=params
        )
        return await helper.execute(mcp_request)
    except Exception as e:
        logger.error(f"netjitter诊断失败: {e}")
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

