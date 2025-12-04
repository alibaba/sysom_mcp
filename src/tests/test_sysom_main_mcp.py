# -*- coding: utf-8 -*-
"""SysOM 统一 MCP 服务器测试

基于 agentscope 的 MCP 客户端测试 sysom_main_mcp.py 统一服务器中的所有工具
包括：AM 服务、内存诊断、IO 诊断、网络诊断、调度诊断、其他诊断等
"""
import asyncio
import copy
import os
import sys
import subprocess
import time
import traceback
from pathlib import Path
from typing import Optional

from agentscope.agent import ReActAgent
from agentscope.formatter import DashScopeChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.message import Msg
from agentscope.model import DashScopeChatModel
from agentscope.tool import Toolkit
from agentscope.tool._response import ToolResponse
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack
import logging

# 配置测试日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 获取项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
# 统一 MCP 服务器脚本路径
MCP_SERVER_SCRIPT = PROJECT_ROOT / "sysom_main_mcp.py"

# 全局变量：MCP 会话和退出栈
_mcp_session: Optional[ClientSession] = None
_mcp_exit_stack: Optional[AsyncExitStack] = None


# ============================================================================
# MCP 客户端连接管理（stdio 模式）
# ============================================================================

async def connect_mcp_server():
    """连接到统一 MCP 服务器（stdio 模式）"""
    global _mcp_session, _mcp_exit_stack
    
    if _mcp_session is not None:
        logger.warning("MCP 会话已经存在")
        return _mcp_session
    
    if not MCP_SERVER_SCRIPT.exists():
        raise FileNotFoundError(f"MCP 服务器脚本不存在: {MCP_SERVER_SCRIPT}")
    
    logger.info("正在连接到 MCP 服务器（stdio 模式）...")
    
    try:
        # 创建退出栈来管理资源
        _mcp_exit_stack = AsyncExitStack()
        
        # 设置服务器参数（使用 uv run 来运行）
        server_params = StdioServerParameters(
            command="uv",
            args=["run", "python", str(MCP_SERVER_SCRIPT), "--stdio"],
            env=None,
            cwd=str(PROJECT_ROOT),
        )
        
        # 创建 stdio 客户端连接
        stdio_transport = await _mcp_exit_stack.enter_async_context(stdio_client(server_params))
        stdio, write = stdio_transport
        
        # 创建客户端会话
        _mcp_session = await _mcp_exit_stack.enter_async_context(ClientSession(stdio, write))
        
        # 初始化会话
        await _mcp_session.initialize()
        
        logger.info("成功连接到 MCP 服务器")
        return _mcp_session
        
    except Exception as e:
        logger.error(f"连接 MCP 服务器时出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # 清理资源
        if _mcp_exit_stack:
            await _mcp_exit_stack.aclose()
            _mcp_exit_stack = None
        _mcp_session = None
        raise RuntimeError(f"连接 MCP 服务器时出错: {e}")


async def disconnect_mcp_server():
    """断开 MCP 服务器连接"""
    global _mcp_session, _mcp_exit_stack
    
    logger.info("正在断开 MCP 服务器连接...")
    
    try:
        if _mcp_exit_stack:
            await _mcp_exit_stack.aclose()
            _mcp_exit_stack = None
        _mcp_session = None
        logger.info("已断开 MCP 服务器连接")
    except Exception as e:
        logger.error(f"断开 MCP 服务器连接时出错: {e}")


# ============================================================================
# MCP客户端初始化
# ============================================================================

toolkit: Toolkit = None
_toolkit_lock = asyncio.Lock()


async def initialize_toolkit() -> Toolkit:
    """初始化MCP工具包（使用 stdio 模式）"""
    global toolkit
    
    if toolkit is None:    
        async with _toolkit_lock:
            if toolkit is None:
                try:
                    # 连接到 MCP 服务器
                    session = await connect_mcp_server()
                    
                    # 列出所有可用工具
                    response = await session.list_tools()
                    tools = response.tools
                    
                    logger.info(f"从 MCP 服务器获取到 {len(tools)} 个工具")
                    
                    # 创建 Toolkit
                    toolkit = Toolkit()
                    
                    # 为每个 MCP 工具创建 agentscope 工具函数包装器
                    for mcp_tool in tools:
                        tool_name = mcp_tool.name
                        tool_description = mcp_tool.description
                        tool_schema = mcp_tool.inputSchema
                        
                        # 创建异步工具函数（使用闭包捕获变量）
                        # 使用工厂函数确保每个工具都有独立的闭包
                        def create_tool_wrapper(name: str, sess: ClientSession):
                            async def tool_func_wrapper(**kwargs):
                                """动态创建的工具函数包装器"""
                                try:
                                    result = await sess.call_tool(name, kwargs)
                                    if result.isError:
                                        return ToolResponse(
                                            content=f"工具调用失败: {result.content}",
                                            is_error=True
                                        )
                                    return ToolResponse(
                                        content=result.content,
                                        is_error=False
                                    )
                                except Exception as e:
                                    return ToolResponse(
                                        content=f"工具调用出错: {str(e)}",
                                        is_error=True
                                    )
                            return tool_func_wrapper
                        
                        # 创建工具函数包装器（确保每个工具都有独立的闭包）
                        tool_func_wrapper = create_tool_wrapper(tool_name, session)
                        
                        # 设置函数的 __name__ 属性为工具名，这样 agentscope 可以正确识别
                        tool_func_wrapper.__name__ = tool_name
                        tool_func_wrapper.__doc__ = tool_description
                        
                        # 构建 JSON schema
                        json_schema = {
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "description": tool_description,
                                "parameters": tool_schema
                            }
                        }
                        
                        # 注册工具函数到 Toolkit
                        toolkit.register_tool_function(
                            tool_func=tool_func_wrapper,
                            func_description=tool_description,
                            json_schema=json_schema
                        )
                        
                        logger.debug(f"已添加工具: {tool_name}")
                    
                    logger.info(f"成功初始化 toolkit，共 {len(tools)} 个工具")
                    logger.info("可用工具列表:")
                    for mcp_tool in tools:
                        logger.info(f"  - {mcp_tool.name}: {mcp_tool.description[:50]}")
                    
                    return toolkit
                    
                except Exception as e:
                    toolkit = None
                    error_msg = str(e)
                    logger.error(f"初始化 toolkit 失败: {error_msg}")
                    import traceback
                    logger.error(traceback.format_exc())
                    raise RuntimeError(f"Failed to initialize toolkit: {e}")
    return toolkit


async def create_test_agent() -> ReActAgent:
    """创建测试用的ReAct Agent"""
    toolkit = await initialize_toolkit()
    test_toolkit = copy.deepcopy(toolkit)
    
    # 从环境变量获取 API key
    api_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not api_key:
        # 尝试从 .env 文件加载
        from dotenv import load_dotenv
        env_path = PROJECT_ROOT / '.env'
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=True)
            api_key = os.environ.get("DASHSCOPE_API_KEY", "")
    
    if not api_key:
        raise ValueError(
            "DASHSCOPE_API_KEY 未设置。请在项目根目录的 .env 文件中设置 DASHSCOPE_API_KEY 环境变量。"
        )
    
    return ReActAgent(
        name="sysom_test_agent",
        model=DashScopeChatModel(
            model_name="qwen-max",
            api_key=api_key,
            stream=True,
            enable_thinking=False,
        ),
        toolkit=test_toolkit,
        max_iters=20,
        sys_prompt="""你是一个专业的系统运维诊断助手。你可以使用以下工具来帮助用户进行系统诊断：

1. AM 服务工具：
   - list_all_instances: 列出所有实例
   - list_pods_of_instance: 列出实例的 Pod
   - list_clusters: 列出集群
   - list_instances: 列出实例

2. 内存诊断工具：
   - memgraph: 内存全景分析
   - javamem: Java 内存诊断
   - oomcheck: OOM 检查

3. IO 诊断工具：
   - iodiagnose: IO 诊断

4. 网络诊断工具：
   - netjitter: 网络抖动诊断
   - netdelay: 网络延迟诊断
   - netloss: 网络丢包诊断

5. 其他诊断工具：
   - diskanalysis: 磁盘分析
   - cpucheck: CPU 检查

请根据用户的需求，选择合适的工具进行诊断。在调用工具时，请确保提供必要的参数（如 uid、region、instance 等）。""",
        memory=InMemoryMemory(),
        formatter=DashScopeChatFormatter(),
    )


# ============================================================================
# 测试函数
# ============================================================================

async def test_list_tools():
    """测试：列出所有可用工具"""
    logger.info("=" * 60)
    logger.info("测试：列出所有可用工具")
    logger.info("=" * 60)
    
    toolkit = await initialize_toolkit()
    tools = toolkit.get_json_schemas()
    
    logger.info(f"\n共找到 {len(tools)} 个工具：\n")
    for i, tool in enumerate(tools, 1):
        func = tool.get('function', {})
        name = func.get('name', 'unknown')
        desc = func.get('description', '无描述')
        logger.info(f"{i}. {name}")
        logger.info(f"   描述: {desc[:100]}...")
        logger.info("")
    
    return tools


async def test_agent_query(query: str):
    """测试：使用 agent 处理查询"""
    logger.info("=" * 60)
    logger.info(f"测试查询: {query}")
    logger.info("=" * 60)
    
    agent = await create_test_agent()
    
    try:
        response = await agent.run(Msg(name="user", content=query))
        logger.info("\n" + "=" * 60)
        logger.info("Agent 响应:")
        logger.info("=" * 60)
        logger.info(response)
        return response
    except Exception as e:
        logger.error(f"处理查询时出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


async def test_interactive_mode():
    """交互式测试模式"""
    logger.info("=" * 60)
    logger.info("进入交互式测试模式")
    logger.info("输入 'q' 或 'quit' 退出")
    logger.info("=" * 60)
    
    agent = await create_test_agent()
    
    while True:
        try:
            query = input("\n请输入查询: ").strip()
            
            if query.lower() in ['q', 'quit', 'exit']:
                logger.info("退出交互式模式")
                break
            
            if not query:
                continue
            
            response = await agent.run(Msg(name="user", content=query))
            print(f"\n响应: {response}")
            
        except KeyboardInterrupt:
            logger.info("\n\n用户中断，退出交互式模式")
            break
        except Exception as e:
            logger.error(f"处理查询时出错: {e}")
            import traceback
            logger.error(traceback.format_exc())


# ============================================================================
# 主函数
# ============================================================================

async def main():
    """主测试函数"""
    try:
        # 测试1: 列出所有工具（会自动连接 MCP 服务器）
        await test_list_tools()
        
        # 测试2: 示例查询（可以根据需要修改）
        # 注意：这些查询需要提供真实的参数（uid、region、instance 等）
        # await test_agent_query("列出所有可用的工具")
        # await test_agent_query("帮我列出所有实例，uid 是 1418925853835361，region 是 cn-hangzhou")
        
        # 测试3: 交互式模式
        logger.info("\n" + "=" * 60)
        logger.info("开始交互式测试")
        logger.info("=" * 60)
        await test_interactive_mode()
        
    except Exception as e:
        logger.error(f"测试过程中出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        # 断开 MCP 服务器连接
        logger.info("\n清理资源...")
        await disconnect_mcp_server()


if __name__ == "__main__":
    asyncio.run(main())

