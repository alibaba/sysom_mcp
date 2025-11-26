# -*- coding: utf-8 -*-
"""内存诊断MCP工具测试

基于agentscope的MCP客户端测试内存诊断工具（memgraph, javamem, oomcheck）
"""
import asyncio
import copy
import os
import traceback
from typing import Dict, List, Optional
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
from pydantic import BaseModel, Field


# ============================================================================
# 测试参数数据结构定义
# ============================================================================

@dataclass
class MemGraphTestParams:
    """memgraph测试参数"""
    uid: str
    region: str
    channel: str  # "ecs" 或 "auto"
    instance: Optional[str] = None
    pod: Optional[str] = None
    clusterType: Optional[str] = None  # "ackClusters", "ackServerlessClusters", "acsClusters"
    clusterId: Optional[str] = None
    namespace: Optional[str] = None


@dataclass
class JavaMemTestParams:
    """javamem测试参数"""
    uid: str
    region: str
    channel: str  # "ecs" 或 "auto"
    instance: str
    pid: Optional[str] = None
    pod: Optional[str] = None
    duration: Optional[str] = "0"
    clusterType: Optional[str] = None  # "ackClusters", "ackServerlessClusters", "acsClusters"
    clusterId: Optional[str] = None
    namespace: Optional[str] = None


@dataclass
class OOMCheckTestParams:
    """oomcheck测试参数"""
    uid: str
    region: str
    channel: str  # "ecs" 或 "auto"
    instance: Optional[str] = None
    pod: Optional[str] = None
    time: Optional[str] = None  # 时间戳
    clusterType: Optional[str] = None  # "ackClusters", "ackServerlessClusters", "acsClusters"
    clusterId: Optional[str] = None
    namespace: Optional[str] = None


# ============================================================================
# 测试用例数据（请填写实际参数）
# ============================================================================

# memgraph测试用例
MEMGRAPH_TEST_CASES: List[MemGraphTestParams] = [
    # 节点诊断 - 仅实例
    MemGraphTestParams(
        uid="1418925853835361",
        region="cn-hangzhou",
        channel="ecs",
        instance="i-bp11jhwbwn9b8ln36i9e",
    ),
    # 节点诊断 - 实例+Pod
    MemGraphTestParams(
        uid="1418925853835361",
        region="cn-hangzhou",
        channel="ecs",
        instance="i-bp11jhwbwn9b8ln36i9e",
        pod="arms-springboot-demo-subcomponent-9c5d4fcbb-9hk28",
    ),
    # Pod诊断 - ACK托管集群
    MemGraphTestParams(
        uid="1418925853835361",
        region="cn-hangzhou",
        channel="auto",
        clusterType="ackClusters",
        clusterId="c7fb20635900c4e69bf6a60af743c0a7a",
        namespace="arms-demo",
        pod="arms-springboot-demo-subcomponent-9c5d4fcbb-9hk28",
    ),
    # # Pod诊断 - ACK Serverless集群
    # MemGraphTestParams(
    #     uid="1418925853835361",
    #     region="cn-hangzhou",
    #     channel="auto",
    #     clusterType="ackServerlessClusters",
    #     clusterId="c0addd452a4664dbe8cf846f5fed91f7e",
    #     namespace="kagent",
    #     pod="kagent-controller-794fc765df-zgtfd",
    # ),
    # # Pod诊断 - ACS集群
    # MemGraphTestParams(
    #     uid="1418925853835361",
    #     region="cn-hangzhou",
    #     channel="auto",
    #     clusterType="acsClusters",
    #     clusterId="c0addd452a4664dbe8cf846f5fed91f7e",
    #     namespace="kagent",
    #     pod="kagent-controller-794fc765df-zgtfd",
    # ),
]

# javamem测试用例
JAVAMEM_TEST_CASES: List[JavaMemTestParams] = [
    # 节点诊断 - 实例+Pid
    JavaMemTestParams(
        uid="1418925853835361",
        region="cn-hangzhou",
        channel="ecs",
        instance="i-bp11jhwbwn9b8ln36i9e",
        pid="4304",
        duration="30",
    ),
    # 节点诊断 - 实例+Pod
    JavaMemTestParams(
        uid="1418925853835361",
        region="cn-hangzhou",
        channel="ecs",
        instance="i-bp11jhwbwn9b8ln36i9e",
        pod="arms-springboot-demo-subcomponent-9c5d4fcbb-9hk28",
    ),
    # Pod诊断 - ACK托管集群
    JavaMemTestParams(
        uid="1418925853835361",
        region="cn-hangzhou",
        channel="auto",
        instance="",  # Pod诊断模式下instance可以为空
        clusterType="ackClusters",
        clusterId="c7fb20635900c4e69bf6a60af743c0a7a",
        namespace="arms-demo",
        pod="arms-springboot-demo-subcomponent-9c5d4fcbb-9hk28",
    ),
]

# oomcheck测试用例
OOMCHECK_TEST_CASES: List[OOMCheckTestParams] = [
    # 节点诊断 - 仅实例
    OOMCheckTestParams(
        uid="1418925853835361",
        region="cn-hangzhou",
        channel="ecs",
        instance="i-bp11jhwbwn9b8ln36i9e",
    ),
    # 节点诊断 - 实例+Pod+时间戳
    OOMCheckTestParams(
        uid="1418925853835361",
        region="cn-hangzhou",
        channel="ecs",
        instance="i-bp11jhwbwn9b8ln36i9e",
        pod="arms-springboot-demo-subcomponent-9c5d4fcbb-9hk28",
        time="1763949657",
    ),
    # Pod诊断 - ACK托管集群
    OOMCheckTestParams(
        uid="1418925853835361",
        region="cn-hangzhou",
        channel="auto",
        clusterType="ackClusters",
        clusterId="c7fb20635900c4e69bf6a60af743c0a7a",
        namespace="arms-demo",
        pod="arms-springboot-demo-subcomponent-9c5d4fcbb-9hk28",
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
                
                mcp_url = "http://127.0.0.1:7130/api/v1/mem_diag/mcp/"
                
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
        name="mem_diag_test_agent",
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

def build_memgraph_prompt(params: MemGraphTestParams) -> str:
    """构建memgraph工具的调用提示"""
    parts = [f"调用memgraph工具，帮我分析一下"]
    
    if params.channel == "ecs":
        # 节点诊断模式
        parts.append(f"{params.instance}实例（region是{params.region}）")
        if params.pod:
            parts.append(f"中的{params.pod}这个Pod")
        parts.append("的内存全景")
    else:
        # Pod诊断模式
        cluster_type_map = {
            "ackClusters": "ACK托管集群",
            "ackServerlessClusters": "ACK Serverless集群",
            "acsClusters": "ACS集群",
        }
        cluster_type_name = cluster_type_map.get(params.clusterType, params.clusterType)
        parts.append(f"{params.clusterId}这个{cluster_type_name}（region是{params.region}）")
        parts.append(f"中{params.namespace}这个namespace下的{params.pod}这个Pod的内存全景")
    
    parts.append(f"，uid是{params.uid}，诊断通道是{params.channel}")
    
    return "".join(parts)


def build_javamem_prompt(params: JavaMemTestParams) -> str:
    """构建javamem工具的调用提示"""
    parts = [f"调用javamem工具，帮我分析一下"]
    
    if params.channel == "ecs":
        # 节点诊断模式
        parts.append(f"{params.instance}实例（region是{params.region}）")
        if params.pid:
            parts.append(f"中的{params.pid}这个Java进程")
        elif params.pod:
            parts.append(f"中的{params.pod}这个Pod")
        parts.append("的Java内存全景")
    else:
        # Pod诊断模式
        cluster_type_map = {
            "ackClusters": "ACK托管集群",
            "ackServerlessClusters": "ACK Serverless集群",
            "acsClusters": "ACS集群",
        }
        cluster_type_name = cluster_type_map.get(params.clusterType, params.clusterType)
        parts.append(f"{params.clusterId}这个{cluster_type_name}（region是{params.region}）")
        parts.append(f"中{params.namespace}这个namespace下的{params.pod}这个Pod的Java内存全景")
    
    parts.append(f"，uid是{params.uid}，诊断通道是{params.channel}")
    
    return "".join(parts)


def build_oomcheck_prompt(params: OOMCheckTestParams) -> str:
    """构建oomcheck工具的调用提示"""
    parts = [f"调用oomcheck工具，帮我分析一下"]
    
    if params.channel == "ecs":
        # 节点诊断模式
        parts.append(f"{params.instance}实例（region是{params.region}）")
        if params.pod:
            parts.append(f"中的{params.pod}这个Pod")
        parts.append("的OOM问题")
    else:
        # Pod诊断模式
        cluster_type_map = {
            "ackClusters": "ACK托管集群",
            "ackServerlessClusters": "ACK Serverless集群",
            "acsClusters": "ACS集群",
        }
        cluster_type_name = cluster_type_map.get(params.clusterType, params.clusterType)
        parts.append(f"{params.clusterId}这个{cluster_type_name}（region是{params.region}）")
        parts.append(f"中{params.namespace}这个namespace下的{params.pod}这个Pod的OOM问题")
    
    parts.append(f"，uid是{params.uid}，诊断通道是{params.channel}")
    
    return "".join(parts)


# ============================================================================
# 测试执行函数
# ============================================================================

async def test_memgraph(test_cases: List[MemGraphTestParams]):
    """测试memgraph工具"""
    logger.info("=" * 80)
    logger.info("开始测试 memgraph 工具")
    logger.info("=" * 80)
    
    agent = await create_test_agent()
    
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\n--- 测试用例 {i}/{len(test_cases)} ---")
        logger.info(f"参数: {test_case}")
        
        try:
            prompt = build_memgraph_prompt(test_case)
            logger.info(f"调用提示: {prompt}")
            
            result = await agent(Msg(name="User", content=prompt, role="user"))
            result_text = result.get_text_content()
            
            logger.info(f"测试结果: {result_text}")
            logger.info("-" * 80)
            
        except Exception as e:
            logger.error(f"测试用例 {i} 执行失败: {e}")
            logger.error(traceback.format_exc())
            logger.info("-" * 80)


async def test_javamem(test_cases: List[JavaMemTestParams]):
    """测试javamem工具"""
    logger.info("=" * 80)
    logger.info("开始测试 javamem 工具")
    logger.info("=" * 80)
    
    agent = await create_test_agent()
    
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\n--- 测试用例 {i}/{len(test_cases)} ---")
        logger.info(f"参数: {test_case}")
        
        try:
            prompt = build_javamem_prompt(test_case)
            logger.info(f"调用提示: {prompt}")
            
            result = await agent(Msg(name="User", content=prompt, role="user"))
            result_text = result.get_text_content()
            
            logger.info(f"测试结果: {result_text}")
            logger.info("-" * 80)
            
        except Exception as e:
            logger.error(f"测试用例 {i} 执行失败: {e}")
            logger.error(traceback.format_exc())
            logger.info("-" * 80)


async def test_oomcheck(test_cases: List[OOMCheckTestParams]):
    """测试oomcheck工具"""
    logger.info("=" * 80)
    logger.info("开始测试 oomcheck 工具")
    logger.info("=" * 80)
    
    agent = await create_test_agent()
    
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\n--- 测试用例 {i}/{len(test_cases)} ---")
        logger.info(f"参数: {test_case}")
        
        try:
            prompt = build_oomcheck_prompt(test_case)
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
        
        # 测试memgraph
        await test_memgraph(MEMGRAPH_TEST_CASES)
        
        # 测试javamem
        await test_javamem(JAVAMEM_TEST_CASES)
        
        # 测试oomcheck
        await test_oomcheck(OOMCHECK_TEST_CASES)
        
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

