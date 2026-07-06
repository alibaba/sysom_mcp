# -*- coding: utf-8 -*-
"""内存诊断MCP工具测试

直接调用函数进行测试，无需启动HTTP服务器
测试内存诊断工具（memgraph, javamem, oomcheck）
"""
import asyncio
import sys
import traceback
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
import logging

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 导入要测试的模块
from tools.mem_diag_mcp import memgraph, javamem, oomcheck
from lib import DiagnosisMCPResponse, DiagnoseResultCode


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
# 测试用例数据（请根据实际情况修改参数）
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
    # Pod诊断 - ACK Serverless集群（可选，取消注释以启用）
    # MemGraphTestParams(
    #     uid="1418925853835361",
    #     region="cn-hangzhou",
    #     channel="auto",
    #     clusterType="ackServerlessClusters",
    #     clusterId="c0addd452a4664dbe8cf846f5fed91f7e",
    #     namespace="kagent",
    #     pod="kagent-controller-794fc765df-zgtfd",
    # ),
    # Pod诊断 - ACS集群（可选，取消注释以启用）
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
# 测试辅助函数
# ============================================================================

def format_result(result: DiagnosisMCPResponse) -> str:
    """格式化诊断结果"""
    lines = [
        f"状态码: {result.code}",
        f"任务ID: {result.task_id}",
    ]
    
    if result.message:
        lines.append(f"消息: {result.message}")
    
    if result.code == DiagnoseResultCode.SUCCESS and result.result:
        lines.append(f"诊断结果: {result.result}")
    elif result.code != DiagnoseResultCode.SUCCESS:
        lines.append(f"错误信息: {result.message}")
    
    return "\n".join(lines)


# ============================================================================
# 测试执行函数
# ============================================================================

async def test_memgraph(test_cases: List[MemGraphTestParams]):
    """测试memgraph工具"""
    logger.info("=" * 80)
    logger.info("开始测试 memgraph 工具")
    logger.info("=" * 80)
    
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\n--- 测试用例 {i}/{len(test_cases)} ---")
        logger.info(f"参数: {test_case}")
        
        try:
            # 直接调用函数
            result = await memgraph(
                uid=test_case.uid,
                region=test_case.region,
                channel=test_case.channel,
                instance=test_case.instance,
                pod=test_case.pod,
                clusterType=test_case.clusterType,
                clusterId=test_case.clusterId,
                namespace=test_case.namespace,
            )
            
            logger.info(f"测试结果:\n{format_result(result)}")
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
    
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\n--- 测试用例 {i}/{len(test_cases)} ---")
        logger.info(f"参数: {test_case}")
        
        try:
            # 直接调用函数
            result = await javamem(
                uid=test_case.uid,
                region=test_case.region,
                channel=test_case.channel,
                instance=test_case.instance,
                pid=test_case.pid,
                pod=test_case.pod,
                duration=test_case.duration,
                clusterType=test_case.clusterType,
                clusterId=test_case.clusterId,
                namespace=test_case.namespace,
            )
            
            logger.info(f"测试结果:\n{format_result(result)}")
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
    
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\n--- 测试用例 {i}/{len(test_cases)} ---")
        logger.info(f"参数: {test_case}")
        
        try:
            # 直接调用函数
            result = await oomcheck(
                uid=test_case.uid,
                region=test_case.region,
                channel=test_case.channel,
                instance=test_case.instance,
                pod=test_case.pod,
                time=test_case.time,
                clusterType=test_case.clusterType,
                clusterId=test_case.clusterId,
                namespace=test_case.namespace,
            )
            
            logger.info(f"测试结果:\n{format_result(result)}")
            logger.info("-" * 80)
            
        except Exception as e:
            logger.error(f"测试用例 {i} 执行失败: {e}")
            logger.error(traceback.format_exc())
            logger.info("-" * 80)


async def run_all_tests():
    """运行所有测试"""
    try:
        logger.info("开始执行内存诊断MCP工具测试...")
        
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
