from fastmcp import FastMCP
from fastmcp.server.proxy import ProxyClient
import asyncio
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.server.dependencies import get_http_headers, get_http_request
from starlette.requests import Request
from lib.logger_config import setup_logger

logger = setup_logger(__name__)


dynamic_mcp = FastMCP(name="DynamicService")

# Create a proxy for a remote server
remote_proxy = FastMCP.as_proxy(ProxyClient("http://127.0.0.1:7130/api/v1/mcp/mcp"))

async def filter_tools():
    tools = await remote_proxy._list_tools()

    logger.info(f"remote_proxy tools: {tools}")
        
    for tool in tools:
        mirrored_tool = await remote_proxy.get_tool(tool.name)
        local_tool = mirrored_tool.copy()
        dynamic_mcp.add_tool(local_tool)
        
    tools = await dynamic_mcp._list_tools()
    logger.info(f"dynamic_mcp tools: {tools}")
    
    for tool in tools:
        if tool.name not in ["diagnose_diagnose"]:
            tool.disable()
    tools = await dynamic_mcp._list_tools()
    logger.info(f"dynamic_mcp tools after disabled: {tools}")
    

class SimpleErrorHandlingMiddleware(Middleware):
    def __init__(self):
        # self.logger = logger
        self.error_counts = {}
    
    async def on_message(self, context: MiddlewareContext, call_next):
        try:
            return await call_next(context)
        except Exception as error:
            # Log the error and track statistics
            error_key = f"{type(error).__name__}:{context.method}"
            self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
            
            logger.error(f"Error in {context.method}: {type(error).__name__}: {error}")


class UidMiddleware(Middleware):
    """Middleware that extracts the 'uid' field from HTTP headers."""

    async def on_message(self, context: MiddlewareContext, call_next):
        headers = get_http_headers()
        request: Request = get_http_request()
        
        uid = headers.get("uid", None)

        if uid:
            logger.debug(f"[UidMiddleware] UID found in headers: {uid}")
        else:
            logger.debug("[UidMiddleware] UID not found in headers")

        context.uid = uid

        return await call_next(context)



if __name__ == "__main__":
    # dynamic_mcp.add_middleware(UidMiddleware)
    dynamic_mcp.add_middleware(SimpleErrorHandlingMiddleware)
    
    asyncio.run(filter_tools())
        
    dynamic_mcp.run()