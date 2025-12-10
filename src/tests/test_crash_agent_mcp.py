# -*- coding: utf-8 -*-
"""应用管理(AM)MCP工具测试

基于agentscope的MCP客户端测试应用管理工具（list_all_instances, list_pods_of_instance, list_clusters, list_instances）
"""
import asyncio
import copy
import os
import sys
import subprocess
import time
import traceback
from typing import List, Optional
from dataclasses import dataclass
from pathlib import Path

from agentscope.agent import ReActAgent, UserAgent
from agentscope.formatter import DashScopeChatFormatter
from agentscope.mcp import HttpStatelessClient, HttpStatefulClient
from agentscope.memory import InMemoryMemory
from agentscope.message import Msg
from agentscope.model import DashScopeChatModel
from agentscope.tool import Toolkit
import logging

# 配置测试日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
logger.error(f"项目根目录: {PROJECT_ROOT}")
# 使用直接运行脚本文件的方式启动 am_mcp 服务
MCP_SERVER_SCRIPT = PROJECT_ROOT / "tools" / "crash_agent_mcp.py"
logger.error(f"MCP 服务器脚本: {MCP_SERVER_SCRIPT}")
# 注意：路径需要与服务器实际监听的路径一致（不带尾部斜杠）
MCP_SERVER_URL = "http://localhost:7130/mcp/crash_agent"


# ============================================================================
# MCP服务器管理
# ============================================================================

toolkit: Toolkit = None
_toolkit_lock = asyncio.Lock()


async def initialize_toolkit() -> Toolkit:
    """初始化MCP工具包"""
    global toolkit

    if toolkit is None:
        async with _toolkit_lock:
            if toolkit is None:
                max_retries = 3
                retry_delay = 2  # 秒

                mcp_url = MCP_SERVER_URL

                for attempt in range(max_retries):
                    try:
                        toolkit = Toolkit()

                        stateless_client = HttpStatelessClient(
                            name="mcp_services_stateless",
                            transport="streamable_http",
                            url=mcp_url,
                        )

                        logger.info(
                            f"尝试连接 MCP 服务器 (第 {attempt + 1}/{max_retries} 次)..."
                        )
                        await toolkit.register_mcp_client(stateless_client)
                        logger.info(
                            f"成功注册 MCP 客户端，共 {len(toolkit.get_json_schemas())} 个工具"
                        )
                        logger.debug(f"工具列表: {toolkit.get_json_schemas()}")

                        return toolkit
                    except Exception as e:
                        toolkit = None
                        error_msg = str(e)
                        logger.warning(
                            f"初始化 toolkit 失败 (第 {attempt + 1}/{max_retries} 次): {error_msg}"
                        )

                        if attempt < max_retries - 1:
                            logger.info(f"等待 {retry_delay} 秒后重试...")
                            await asyncio.sleep(retry_delay)
                        else:
                            logger.error(
                                f"初始化 toolkit 失败，已重试 {max_retries} 次"
                            )
                            raise RuntimeError(
                                f"Failed to initialize toolkit after {max_retries} attempts: {e}"
                            )
    return toolkit


async def create_test_agent() -> ReActAgent:
    """创建测试用的ReAct Agent"""
    toolkit = await initialize_toolkit()
    test_toolkit = copy.deepcopy(toolkit)

    return ReActAgent(
        name="am_test_agent",
        model=DashScopeChatModel(
            model_name="qwen3-max-preview",
            api_key=os.environ.get(
                "sysom_service___llm___llm_ak", ""
            ),
            stream=True,
            enable_thinking=False,
        ),
        toolkit=test_toolkit,
        max_iters=20,
        sys_prompt="你是一个专业的应用管理测试助手。请根据用户提供的参数调用相应的MCP工具进行测试。",
        memory=InMemoryMemory(),
        formatter=DashScopeChatFormatter(),
    )


async def main():
    """主函数"""
    # await run_all_tests()
    # start_mcp_server()
    agent = await create_test_agent()
    user = UserAgent(name="User")
    msg = None
    while True:
        msg = await agent(msg)
        msg = await user(msg)
        if msg.get_text_content() == "exit":
            break


if __name__ == "__main__":
    asyncio.run(main())
