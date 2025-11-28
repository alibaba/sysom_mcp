from typing import Optional, Literal
import click
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

# vmcore诊断请求参数示例
# {\"instance\":\"i-wz9fckjns2yegqca8t9q\",\"region\":\"cn-shenzhen\",\"instanceName\":\"\"}

class VmcoreDiagnosisMCPRequestParams(DiagnosisMCPRequestParams):
    """vmcore诊断请求参数"""
    instance: str = Field(..., description="实例ID")

@mcp.tool(
    tags={"sysom_otherdiag"}
)
async def vmcore(
    uid: str = Field(..., description="用户ID"),
    region: str = Field(..., description="实例地域"),
    channel: str = Field(..., description="诊断通道"),
    instance: str = Field(..., description="实例ID"),
    ctx: Context | None = None,
) -> DiagnosisMCPResponse:
    """vmcore（宕机诊断）工具主要分析操作系统崩溃的原因，通过分析内核panic产生的core dump文件，结合dmesg日志，分析操作系统崩溃的原因。
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
        # client = ClientFactory.create_client(
        #     deploy_mode=getattr(SERVICE_CONFIG, 'deploy_mode', 'alibabacloud_sdk'),
        #     uid=uid
        # )
        client = ClientFactory.create_client(
            uid=uid
        )
        helper = DiagnosisMCPHelper(client, timeout=150, poll_interval=1)
        params_obj = VmcoreDiagnosisMCPRequestParams(region=region, instance=instance)
        params = params_obj.model_dump(exclude_none=True, by_alias=True)
        mcp_request = DiagnosisMCPRequest(
            service_name="vmcore",
            channel=channel,
            region=region,
            params=params
        )
        return await helper.execute(mcp_request)
    except Exception as e:
        logger.error(f"vmcore诊断失败: {e}")
        return DiagnosisMCPResponse(
            code=DiagnoseResultCode.TASK_CREATE_FAILED,
            message=f"诊断失败：{str(e)}",
            task_id=""
        )

# diskanalysis诊断请求参数示例
# {\"instance\":\"i-wz9fckjns2yegqca8t9q\",\"region\":\"cn-shenzhen\",\"instanceName\":\"\"}

class DiskAnalysisDiagnosisMCPRequestParams(DiagnosisMCPRequestParams):
    """diskanalysis诊断请求参数"""
    instance: str = Field(..., description="实例ID")

@mcp.tool(
    tags={"sysom_otherdiag"}
)
async def diskanalysis(
    uid: str = Field(..., description="用户ID"),
    region: str = Field(..., description="实例地域"),
    channel: str = Field(..., description="诊断通道"),
    instance: str = Field(..., description="实例ID"),
    ctx: Context | None = None,
) -> DiagnosisMCPResponse:
    """diskanalysis（磁盘分析诊断）工具主要分析系统中磁盘的使用情况。
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
        # client = ClientFactory.create_client(
        #     deploy_mode=getattr(SERVICE_CONFIG, 'deploy_mode', 'alibabacloud_sdk'),
        #     uid=uid
        # )
        client = ClientFactory.create_client(
            uid=uid
        )
        helper = DiagnosisMCPHelper(client, timeout=150, poll_interval=1)
        params_obj = DiskAnalysisDiagnosisMCPRequestParams(region=region, instance=instance)
        params = params_obj.model_dump(exclude_none=True, by_alias=True)
        mcp_request = DiagnosisMCPRequest(
            service_name="diskanalysis",
            channel=channel,
            region=region,
            params=params
        )
        return await helper.execute(mcp_request)
    except Exception as e:
        logger.error(f"diskanalysis诊断失败: {e}")
        return DiagnosisMCPResponse(
            code=DiagnoseResultCode.TASK_CREATE_FAILED,
            message=f"诊断失败：{str(e)}",
            task_id=""
        )
        
@click.command()
@click.option("--stdio", "run_mode", flag_value="stdio", default=True, help="Run in stdio mode")
@click.option("--sse", "run_mode", flag_value="sse", help="Run in SSE mode")
@click.option("--host", default="127.0.0.1", help="Host to bind to (for SSE mode, default: 127.0.0.1)")
@click.option("--port", default=7130, type=int, help="Port to bind to (for SSE mode, default: 7130)")
@click.option("--path", default="/mcp/other_diag", help="Path for SSE endpoint (default: /mcp/other_diag)")
def main(run_mode: Literal["stdio", "sse"], host: str, port: int, path: str) -> None:
    """Run MCP server in stdio or SSE mode"""
    if run_mode == "sse":
        # SSE 模式：直接使用 mcp.run()，它应该支持这些参数
        logger.info(f"Starting MCP server in SSE mode on {host}:{port}{path}")
        # FastMCP 的 run() 方法应该支持 transport、host、port、path 参数
        mcp.run(transport="sse", host=host, port=port, path=path)
    else:
        # stdio 模式
        logger.info("Starting MCP server in stdio mode")
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

# def create_mcp_server():
#     return mcp

# if __name__ == "__main__":
#     # 日志级别已通过 logger_config 配置
#     create_mcp_server().run(transport="stdio")

