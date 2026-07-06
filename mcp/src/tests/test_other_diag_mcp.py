# -*- coding: utf-8 -*-
"""其他诊断MCP工具测试

基于agentscope的MCP客户端测试其他诊断工具（vmcore, diskanalysis）
"""
import asyncio
import copy
import os
import traceback
from typing import List
from dataclasses import dataclass

from agentscope.agent import ReActAgent
from agentscope.formatter import DashScopeChatFormatter
from agentscope.mcp import HttpStatelessClient
from agentscope.memory import InMemoryMemory
from agentscope.message import Msg
from agentscope.model import DashScopeChatModel
from agentscope.tool import Toolkit
import logging
logger = logging.getLogger(__name__)


# ============================================================================
# 测试参数数据结构定义
# ============================================================================

@dataclass
class VmcoreTestParams:
    """vmcore测试参数"""
    uid: str
    region: str
    channel: str  # "ecs"
    instance: str


@dataclass
class DiskAnalysisTestParams:
    """diskanalysis测试参数"""
    uid: str
    region: str
    channel: str  # "ecs"
    instance: str


# ============================================================================
# 测试用例数据（请填写实际参数）
# ============================================================================

# vmcore测试用例
VMCORE_TEST_CASES: List[VmcoreTestParams] = [
    VmcoreTestParams(
        uid="1418925853835361",
        region="cn-hangzhou",
        channel="ecs",
        instance="i-bp11jhwbwn9b8ln36i9e",
    ),
]

# diskanalysis测试用例
DISKANALYSIS_TEST_CASES: List[DiskAnalysisTestParams] = [
    DiskAnalysisTestParams(
        uid="1418925853835361",
        region="cn-hangzhou",
        channel="ecs",
        instance="i-bp11jhwbwn9b8ln36i9e",
    ),
]


# ============================================================================
# MCP客户端初始化
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
                
                mcp_url = "http://127.0.0.1:7130/api/v1/other_diag/mcp/"
                
                for attempt in range(max_retries):
                    try:
                        toolkit = Toolkit()
                        
                        stateless_client = HttpStatelessClient(
                            name="mcp_services_stateless",
                            transport="streamable_http",
                            url=mcp_url,
                        )
                        
                        logger.info(f"尝试连接 MCP 服务器 (第 {attempt + 1}/{max_retries} 次)...")
                        await toolkit.register_mcp_client(stateless_client)
                        
                        logger.info(f"成功注册 MCP 客户端，共 {len(toolkit.get_json_schemas())} 个工具")
                        logger.info(f"工具列表: {toolkit.get_json_schemas()}")
                                            
                        return toolkit
                    except Exception as e:
                        toolkit = None
                        error_msg = str(e)
                        logger.warning(f"初始化 toolkit 失败 (第 {attempt + 1}/{max_retries} 次): {error_msg}")
                        
                        if attempt < max_retries - 1:
                            logger.info(f"等待 {retry_delay} 秒后重试...")
                            await asyncio.sleep(retry_delay)
                        else:
                            logger.error(f"初始化 toolkit 失败，已重试 {max_retries} 次")
                            raise RuntimeError(f"Failed to initialize toolkit after {max_retries} attempts: {e}")
    return toolkit


async def create_test_agent() -> ReActAgent:
    """创建测试用的ReAct Agent"""
    toolkit = await initialize_toolkit()
    test_toolkit = copy.deepcopy(toolkit)
    
    return ReActAgent(
        name="other_diag_test_agent",
        model=DashScopeChatModel(
            model_name="qwen3-max-preview",
            api_key=os.environ.get("sysom_service___llm___llm_ak", ""),
            stream=True,
            enable_thinking=False,
        ),
        toolkit=test_toolkit,
        max_iters=20,
        sys_prompt="你是一个专业的系统诊断测试助手。请根据用户提供的参数调用相应的MCP工具进行测试。",
        memory=InMemoryMemory(),
        formatter=DashScopeChatFormatter(),
    )


# ============================================================================
# 测试辅助函数
# ============================================================================

def build_vmcore_prompt(params: VmcoreTestParams) -> str:
    """构建vmcore工具的调用提示"""
    return f"调用vmcore工具，帮我分析一下{params.instance}实例（region是{params.region}）的宕机问题，uid是{params.uid}，诊断通道是{params.channel}"


def build_diskanalysis_prompt(params: DiskAnalysisTestParams) -> str:
    """构建diskanalysis工具的调用提示"""
    return f"调用diskanalysis工具，帮我分析一下{params.instance}实例（region是{params.region}）的磁盘使用情况，uid是{params.uid}，诊断通道是{params.channel}"


# ============================================================================
# 测试执行函数
# ============================================================================

async def test_vmcore(test_cases: List[VmcoreTestParams]):
    """测试vmcore工具"""
    logger.info("=" * 80)
    logger.info("开始测试 vmcore 工具")
    logger.info("=" * 80)
    
    agent = await create_test_agent()
    
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\n--- 测试用例 {i}/{len(test_cases)} ---")
        logger.info(f"参数: {test_case}")
        
        try:
            prompt = build_vmcore_prompt(test_case)
            logger.info(f"调用提示: {prompt}")
            
            result = await agent(Msg(name="User", content=prompt, role="user"))
            result_text = result.get_text_content()
            
            logger.info(f"测试结果: {result_text}")
            logger.info("-" * 80)
            
        except Exception as e:
            logger.error(f"测试用例 {i} 执行失败: {e}")
            logger.error(traceback.format_exc())
            logger.info("-" * 80)


async def test_diskanalysis(test_cases: List[DiskAnalysisTestParams]):
    """测试diskanalysis工具"""
    logger.info("=" * 80)
    logger.info("开始测试 diskanalysis 工具")
    logger.info("=" * 80)
    
    agent = await create_test_agent()
    
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\n--- 测试用例 {i}/{len(test_cases)} ---")
        logger.info(f"参数: {test_case}")
        
        try:
            prompt = build_diskanalysis_prompt(test_case)
            logger.info(f"调用提示: {prompt}")
            
            result = await agent(Msg(name="User", content=prompt, role="user"))
            result_text = result.get_text_content()
            
            logger.info(f"测试结果: {result_text}")
            logger.info("-" * 80)
            
        except Exception as e:
            logger.error(f"测试用例 {i} 执行失败: {e}")
            logger.error(traceback.format_exc())
            logger.info("-" * 80)


async def run_all_tests():
    """运行所有测试"""
    try:
        logger.info("开始初始化 MCP 测试环境...")
        await initialize_toolkit()
        logger.info("MCP 测试环境初始化完成")
        
        # 测试vmcore
        await test_vmcore(VMCORE_TEST_CASES)
        
        # 测试diskanalysis
        await test_diskanalysis(DISKANALYSIS_TEST_CASES)
        
        logger.info("=" * 80)
        logger.info("所有测试执行完成")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"测试执行失败: {e}")
        logger.error(traceback.format_exc())
        raise


async def main():
    """主函数"""
    await run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())

