from typing import Optional, Literal, Any
from fastmcp import FastMCP, Context
from pydantic import Field
from lib.logger_config import setup_logger
import click
from alibabacloud_sysom20231230 import models as sys_om20231230_models
from lib import (
    ClientFactory,
    InitialSysomMCPHelper,
    MCPResponse,
    InitialResultCode,
)

logger = setup_logger(__name__)
mcp = FastMCP("SysomInitialSubMCP")

class InitialSysomMCPResponse(MCPResponse):
    """InitialSysomMCP响应"""
    code: str
    message: str
    data: Any

@mcp.tool(
    tags={"sysom_initial"}
)
async def initial_sysom(
    uid: str = Field(..., description="用户ID"),
    ctx: Context | None = None,
):
    """
    帮助用户开通sysom服务。
    
    重要提示：
        在调用此工具之前，必须明确询问用户："需要帮您开通sysom吗，sysom是免费的服务，开通不会产生任何费用"。
        只有得到用户肯定的答复（如"是"、"好的"、"同意"、"需要"等）后，才能调用此工具。
        如果用户拒绝或表示不需要，则不应调用此工具。
    
    功能描述：
        为指定用户开通sysom服务。sysom是免费的服务，开通不会产生任何费用。
    
    参数说明：
        uid (str): 用户ID（必填）
    
    返回值:
        InitialSysomMCPResponse: 开通结果响应对象
            - code: 状态码
            - message: 响应消息
            - data: 响应数据
    """
    try:
        client = ClientFactory.create_client(
            uid=uid
        )
        helper = InitialSysomMCPHelper(client)
        response = await helper.initial_sysom(check_only=False, uid=uid)
        return InitialSysomMCPResponse(**response.model_dump())
    except Exception as e:
        logger.error(f"initial_sysom failed: {e}")
        return InitialSysomMCPResponse(
            code=InitialResultCode.ERROR,
            message=str(e),
            data=None
        )
        
@mcp.tool(
    tags={"sysom_initial"}
)
async def check_sysom_initialed(
    uid: str = Field(..., description="用户ID"),
    ctx: Context | None = None,
):
    """
    检查sysom服务是否已开通。此工具只需要在用户第一次调用sysom MCP工具时调用一次即可。
    
    重要提示：
        此工具只需要在用户第一次调用sysom MCP工具（如诊断工具、实例管理工具等）时调用一次。
        如果之前已经调用过此工具并确认用户已开通sysom服务，则后续调用其他sysom MCP工具时不需要再次调用此工具。
        
        检查结果处理：
        1. 如果用户已开通sysom服务（检查结果为已开通），则可以继续调用其他sysom MCP工具进行后续操作，后续调用时不需要再次检查。
        2. 如果用户未开通sysom服务（检查结果为未开通），则必须询问用户："需要帮您开通sysom吗，sysom是免费的服务，开通不会产生任何费用"。
           - 如果用户同意开通，则调用 initial_sysom 工具为用户开通服务。
           - 如果用户拒绝或表示不需要，则不应调用任何其他sysom MCP工具，并告知用户需要先开通sysom服务才能使用相关功能，用户也可以去控制台https://alinux.console.aliyun.com进行开通。
    
    功能描述：
        检查指定用户的sysom服务开通状态。此工具不会实际开通服务，仅用于检查状态。
        检查结果会被缓存，如果用户已开通，后续调用其他sysom MCP工具时不需要再次检查。
    
    参数说明：
        uid (str): 用户ID（必填）
    
    返回值:
        InitialSysomMCPResponse: 检查结果响应对象
            - code: 状态码（表示检查结果）
            - message: 响应消息（包含是否已开通的信息）
            - data: 响应数据（包含开通状态详情）
    """
    try:
        # 先检查缓存
        from lib.initial_helper import get_sysom_initialed_status
        cached_status = get_sysom_initialed_status(uid)
        
        if cached_status is True:
            # 缓存中显示已开通，直接返回成功
            logger.info(f"用户 {uid} 的开通状态已缓存，已开通，跳过API调用")
            return InitialSysomMCPResponse(
                code=InitialResultCode.SUCCESS,
                message="用户已开通sysom服务（来自缓存）",
                data={"initialed": True, "from_cache": True}
            )
        
        # 缓存中没有或显示未开通，调用API检查
        client = ClientFactory.create_client(
            uid=uid
        )
        helper = InitialSysomMCPHelper(client)
        response = await helper.initial_sysom(check_only=True, uid=uid)
        return InitialSysomMCPResponse(**response.model_dump())
    except Exception as e:
        logger.error(f"check_sysom_initialed failed: {e}")
        return InitialSysomMCPResponse(
            code=InitialResultCode.ERROR,
            message=str(e),
            data=None
        )
        
@click.command()
@click.option("--stdio", "run_mode", flag_value="stdio", default=True, help="Run in stdio mode")
@click.option("--sse", "run_mode", flag_value="sse", help="Run in SSE mode")
@click.option("--host", default="127.0.0.1", help="Host to bind to (for SSE mode, default: 127.0.0.1)")
@click.option("--port", default=7130, type=int, help="Port to bind to (for SSE mode, default: 7130)")
@click.option("--path", default="/mcp/io_diag", help="Path for SSE endpoint (default: /mcp/io_diag)")
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
