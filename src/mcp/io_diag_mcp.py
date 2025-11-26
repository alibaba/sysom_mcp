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

# iofsstat诊断请求参数示例
# {\"instance\":\"i-wz9fckjns2yegqca8t9q\",\"timeout\":\"15\",\"disk\":\"vda\",\"region\":\"cn-shenzhen\",\"instanceName\":\"\"}

class IOFSStatDiagnosisMCPRequestParams(DiagnosisMCPRequestParams):
    """iofsstat诊断请求参数"""
    instance: str = Field(..., description="实例名称")
    timeout: Optional[str] = Field("15", description="诊断时长")
    disk: Optional[str] = Field(None, description="磁盘名称")

@mcp.tool(
    tags={"sysom_iodiag"}
)
async def iofsstat(
    uid: str = Field(..., description="用户ID"),
    region: str = Field(..., description="实例地域"),
    channel: str = Field(..., description="诊断通道"),
    instance: str = Field(..., description="实例名称"),
    timeout: Optional[str] = Field(None, description="诊断时长"),
    disk: Optional[str] = Field(None, description="磁盘名称"),
    ctx: Context | None = None,
) -> DiagnosisMCPResponse:
    """
    iofsstat（IO流量分析）工具主要分析系统中IO流量的归属，结果包含每个磁盘/分区的IO流量统计列表以及每个进程的IO流量统计列表。
    使用场景：实例中存在IO Burst问题，需要分析IO流量的归属。
    仅支持节点诊断模式，channel必须为ecs。
    参数说明：
        uid: 用户ID
        region: 实例地域
        channel: 诊断通道，仅支持ecs诊断通道
        instance: 实例ID
        timeout: 诊断时长（可选），默认为15秒
        disk: 磁盘名称（可选），例如sda等，缺省为所有磁盘
    示例：
        - {"uid": "123456789", "channel":"ecs", "instance":"i-wz9fckjns2yegqca8t9q","region":"cn-shenzhen"}
        - {"uid": "123456789", "channel":"ecs", "instance":"i-wz9fckjns2yegqca8t9q","timeout":"30","disk":"vda","region":"cn-shenzhen"}
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
        params_obj = IOFSStatDiagnosisMCPRequestParams(
            region=region,
            instance=instance,
            timeout=timeout or "15",
            disk=disk,
        )
        params = params_obj.model_dump(exclude_none=True, by_alias=True)
        mcp_request = DiagnosisMCPRequest(
            service_name="iofsstat",
            channel=channel,
            region=region,
            params=params
        )
        return await helper.execute(mcp_request)
    except Exception as e:
        logger.error(f"iofsstat诊断失败: {e}")
        return DiagnosisMCPResponse(
            code=DiagnoseResultCode.TASK_CREATE_FAILED,
            message=f"诊断失败：{str(e)}",
            task_id=""
        )

# iodiagnose诊断请求参数示例
# {\"instance\":\"i-wz9fckjns2yegqca8t9q\",\"timeout\":\"30\",\"region\":\"cn-shenzhen\",\"instanceName\":\"\"}

class IODiagnoseDiagnosisMCPRequestParams(DiagnosisMCPRequestParams):
    """iodiagnose诊断请求参数"""
    instance: str = Field(..., description="实例名称")
    timeout: Optional[str] = Field("30", description="诊断时长")

@mcp.tool(
    tags={"sysom_iodiag"}
)
async def iodiagnose(
    uid: str = Field(..., description="用户ID"),
    region: str = Field(..., description="实例地域"),
    channel: str = Field(..., description="诊断通道"),
    instance: str = Field(..., description="实例名称"),
    timeout: Optional[str] = Field(None, description="诊断时长"),
    ctx: Context | None = None,
) -> DiagnosisMCPResponse:
    """iodiagnose（IO一键诊断）工具专注于高频出现的IO高延迟、IO Burst及IO Wait等问题，支持对各种IO问题类型的识别，并调用相应的子工具对IO数据进行分析，从而提供结论和建议。
    使用场景：
        1. IO延迟较高，需要排查主要的延迟点是位于操作系统（OS）层面，还是后端服务。
        2. 存在IO异常流量，需识别发起该流量的进程。
        3. 观测到IO Wait指标异常升高，需识别根本原因及异常IO路径。
    仅支持节点诊断模式，channel必须为ecs。
    参数说明：
        uid: 用户ID
        region: 实例地域
        channel: 诊断通道，仅支持ecs诊断通道
        instance: 实例ID
        timeout: 诊断时长（可选），默认为30秒，不建议低于30秒
    示例：
        - {"uid": "123456789", "channel":"ecs", "instance":"i-wz9fckjns2yegqca8t9q","region":"cn-shenzhen"}
        - {"uid": "123456789", "channel":"ecs", "instance":"i-wz9fckjns2yegqca8t9q","timeout":"60","region":"cn-shenzhen"}
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
        params_obj = IODiagnoseDiagnosisMCPRequestParams(
            region=region,
            instance=instance,
            timeout=timeout or "30",
        )
        params = params_obj.model_dump(exclude_none=True, by_alias=True)
        mcp_request = DiagnosisMCPRequest(
            service_name="iodiagnose",
            channel=channel,
            region=region,
            params=params
        )
        return await helper.execute(mcp_request)
    except Exception as e:
        logger.error(f"iodiagnose诊断失败: {e}")
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

