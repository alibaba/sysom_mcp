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

from agentscope.agent import ReActAgent
from agentscope.formatter import DashScopeChatFormatter
from agentscope.mcp import HttpStatelessClient
from agentscope.memory import InMemoryMemory
from agentscope.message import Msg
from agentscope.model import DashScopeChatModel
from agentscope.tool import Toolkit
import logging

# 配置测试日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
# 使用直接运行脚本文件的方式启动 am_mcp 服务
MCP_SERVER_SCRIPT = PROJECT_ROOT / "mcp" / "am_mcp.py"
# 注意：路径需要与服务器实际监听的路径一致（不带尾部斜杠）
MCP_SERVER_URL = "http://127.0.0.1:7130/mcp/am"


# ============================================================================
# 测试参数数据结构定义
# ============================================================================

@dataclass
class ListAllInstancesTestParams:
    """list_all_instances测试参数"""
    uid: str
    region: Optional[str] = None
    managed_type: Optional[str] = "all"  # "managed", "unmanaged", "all", "install", "uninstall", "upgrade"
    instance_type: Optional[str] = "ecs"
    pluginId: Optional[str] = "74a86327-3170-412c-8e67-da3389ec56a9"
    filters: Optional[str] = None  # JSON字符串格式
    current: int = 1
    pageSize: int = 10


@dataclass
class ListPodsOfInstanceTestParams:
    """list_pods_of_instance测试参数"""
    uid: str
    instance: str
    region: Optional[str] = None
    status: Optional[str] = None
    cluster_id: Optional[str] = None
    gpu: Optional[str] = None
    install_channel: Optional[str] = "console"


@dataclass
class ListClustersTestParams:
    """list_clusters测试参数"""
    uid: str
    id: Optional[str] = None  # 集群ID（用于查询）
    name: Optional[str] = None
    cluster_id: Optional[str] = None  # 集群ID（用于过滤）
    cluster_type: Optional[str] = None
    cluster_status: Optional[str] = None


@dataclass
class ListInstancesTestParams:
    """list_instances测试参数"""
    uid: str
    instance: Optional[str] = None
    status: Optional[str] = None
    region: Optional[str] = None
    cluster_id: Optional[str] = None
    gpu: Optional[str] = None
    install_channel: Optional[str] = "console"


# ============================================================================
# 测试用例数据（请填写实际参数）
# ============================================================================

# list_all_instances测试用例
LIST_ALL_INSTANCES_TEST_CASES: List[ListAllInstancesTestParams] = [
    # 基础测试 - 查询所有实例
    ListAllInstancesTestParams(
        uid="1418925853835361",
        region="cn-hangzhou",
        managed_type="all",
        instance_type="ecs",
    ),
    # 查询已纳管实例
    ListAllInstancesTestParams(
        uid="1418925853835361",
        region="cn-hangzhou",
        managed_type="managed",
        instance_type="ecs",
    ),
    # 查询未纳管实例
    ListAllInstancesTestParams(
        uid="1418925853835361",
        region="cn-hangzhou",
        managed_type="unmanaged",
        instance_type="ecs",
    ),
    # 分页查询
    ListAllInstancesTestParams(
        uid="1418925853835361",
        region="cn-hangzhou",
        managed_type="managed",
        current=1,
        pageSize=20,
    ),
]

# list_pods_of_instance测试用例
LIST_PODS_OF_INSTANCE_TEST_CASES: List[ListPodsOfInstanceTestParams] = [
    # 基础测试
    ListPodsOfInstanceTestParams(
        uid="1418925853835361",
        instance="i-bp11jhwbwn9b8ln36i9e",
        region="cn-hangzhou",
    ),
]

# list_clusters测试用例
LIST_CLUSTERS_TEST_CASES: List[ListClustersTestParams] = [
    # 基础测试 - 查询所有集群
    ListClustersTestParams(
        uid="1418925853835361",
    ),
    # 按集群ID查询
    ListClustersTestParams(
        uid="1418925853835361",
        id="c7fb20635900c4e69bf6a60af743c0a7a",
    ),
    # 按集群名称查询
    ListClustersTestParams(
        uid="1418925853835361",
        name="ack-1763536426",
    ),
]

# list_instances测试用例
LIST_INSTANCES_TEST_CASES: List[ListInstancesTestParams] = [
    # 基础测试 - 查询所有实例
    ListInstancesTestParams(
        uid="1418925853835361",
        region="cn-hangzhou",
    ),
    # 按实例ID查询
    ListInstancesTestParams(
        uid="1418925853835361",
        instance="i-bp11jhwbwn9b8ln36i9e",
        region="cn-hangzhou",
    ),
    # 按集群ID查询
    ListInstancesTestParams(
        uid="1418925853835361",
        cluster_id="c7fb20635900c4e69bf6a60af743c0a7a",
        region="cn-hangzhou",
    ),
]


# ============================================================================
# MCP服务器管理
# ============================================================================

_mcp_server_process: Optional[subprocess.Popen] = None


def start_mcp_server():
    """启动 MCP 服务器"""
    global _mcp_server_process
    
    if _mcp_server_process is not None:
        logger.info("MCP 服务器已经在运行")
        return
    
    logger.info("正在启动 MCP 服务器...")
    
    # 检查服务器脚本是否存在
    if not MCP_SERVER_SCRIPT.exists():
        raise FileNotFoundError(f"MCP 服务器脚本不存在: {MCP_SERVER_SCRIPT}")
    
    # 启动服务器进程（直接运行脚本文件，SSE 模式）
    # 确保传递正确的 host、port 和 path 参数，与 MCP_SERVER_URL 匹配
    try:
        _mcp_server_process = subprocess.Popen(
            [
                sys.executable,
                str(MCP_SERVER_SCRIPT),
                "--sse",
                # "--host", "127.0.0.1",
                # "--port", "7130",
                # "--path", "/mcp/am",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(PROJECT_ROOT),  # 在 src 目录下运行
            text=True,
            bufsize=1,
        )
        
        # 等待服务器启动
        logger.info("等待 MCP 服务器启动...")
        max_wait = 15  # 最多等待15秒
        server_ready = False
        
        for i in range(max_wait):
            time.sleep(1)
            # 检查进程是否还在运行
            if _mcp_server_process.poll() is not None:
                # 进程已退出，读取错误信息
                stdout, _ = _mcp_server_process.communicate()
                error_msg = stdout if stdout else "进程意外退出，无错误信息"
                logger.error(f"MCP 服务器进程退出，退出码: {_mcp_server_process.returncode}")
                logger.error(f"服务器输出:\n{error_msg}")
                raise RuntimeError(f"MCP 服务器启动失败 (退出码: {_mcp_server_process.returncode}): {error_msg}")
            
            # 尝试连接服务器（简单检查）
            try:
                import urllib.request
                urllib.request.urlopen(MCP_SERVER_URL, timeout=1)
                server_ready = True
                logger.info(f"MCP 服务器已启动，运行在 {MCP_SERVER_URL}")
                break
            except Exception as conn_err:
                if i < max_wait - 1:
                    logger.debug(f"等待服务器启动中... ({i+1}/{max_wait})")
                    continue
                else:
                    logger.warning(f"无法确认 MCP 服务器是否已完全启动: {conn_err}")
                    logger.warning("继续尝试连接，但服务器可能未完全就绪...")
                    break
        
        if not server_ready:
            logger.warning("服务器可能未完全就绪，但继续尝试连接...")
            
    except Exception as e:
        if _mcp_server_process:
            _mcp_server_process.terminate()
            _mcp_server_process = None
        logger.error(f"启动 MCP 服务器时出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise RuntimeError(f"启动 MCP 服务器时出错: {e}")


def stop_mcp_server():
    """停止 MCP 服务器"""
    global _mcp_server_process
    
    if _mcp_server_process is None:
        return
    
    logger.info("正在停止 MCP 服务器...")
    try:
        _mcp_server_process.terminate()
        # 等待进程结束，最多等待5秒
        try:
            _mcp_server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # 如果5秒内没有结束，强制杀死
            _mcp_server_process.kill()
            _mcp_server_process.wait()
        
        logger.info("MCP 服务器已停止")
    except Exception as e:
        logger.error(f"停止 MCP 服务器时出错: {e}")
    finally:
        _mcp_server_process = None


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
                
                mcp_url = MCP_SERVER_URL
                
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
                        logger.debug(f"工具列表: {toolkit.get_json_schemas()}")
                                            
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
        name="am_test_agent",
        model=DashScopeChatModel(
            model_name="qwen3-max-preview",
            api_key=os.environ.get("sysom_service___llm___llm_ak", ""),
            stream=True,
            enable_thinking=False,
        ),
        toolkit=test_toolkit,
        max_iters=20,
        sys_prompt="你是一个专业的应用管理测试助手。请根据用户提供的参数调用相应的MCP工具进行测试。",
        memory=InMemoryMemory(),
        formatter=DashScopeChatFormatter(),
    )


# ============================================================================
# 测试辅助函数
# ============================================================================

def build_list_all_instances_prompt(params: ListAllInstancesTestParams) -> str:
    """构建list_all_instances工具的调用提示"""
    parts = [f"调用list_all_instances工具，帮我列出所有实例"]
    
    if params.region:
        parts.append(f"，region是{params.region}")
    if params.managed_type and params.managed_type != "all":
        parts.append(f"，纳管类型是{params.managed_type}")
    if params.instance_type:
        parts.append(f"，实例类型是{params.instance_type}")
    if params.filters:
        parts.append(f"，过滤条件是{params.filters}")
    if params.current != 1 or params.pageSize != 10:
        parts.append(f"，页码是{params.current}，每页数量是{params.pageSize}")
    
    parts.append(f"，uid是{params.uid}")
    
    return "".join(parts)


def build_list_pods_of_instance_prompt(params: ListPodsOfInstanceTestParams) -> str:
    """构建list_pods_of_instance工具的调用提示"""
    parts = [f"调用list_pods_of_instance工具，帮我列出{params.instance}实例下的Pod列表"]
    
    if params.region:
        parts.append(f"，region是{params.region}")
    if params.cluster_id:
        parts.append(f"，集群ID是{params.cluster_id}")
    
    parts.append(f"，uid是{params.uid}")
    
    return "".join(parts)


def build_list_clusters_prompt(params: ListClustersTestParams) -> str:
    """构建list_clusters工具的调用提示"""
    parts = [f"调用list_clusters工具，帮我列出集群列表"]
    
    if params.id:
        parts.append(f"，集群ID是{params.id}")
    if params.name:
        parts.append(f"，集群名称是{params.name}")
    if params.cluster_type:
        parts.append(f"，集群类型是{params.cluster_type}")
    if params.cluster_status:
        parts.append(f"，集群状态是{params.cluster_status}")
    
    parts.append(f"，uid是{params.uid}")
    
    return "".join(parts)


def build_list_instances_prompt(params: ListInstancesTestParams) -> str:
    """构建list_instances工具的调用提示"""
    parts = [f"调用list_instances工具，帮我列出实例列表"]
    
    if params.instance:
        parts.append(f"，实例ID是{params.instance}")
    if params.region:
        parts.append(f"，region是{params.region}")
    if params.cluster_id:
        parts.append(f"，集群ID是{params.cluster_id}")
    if params.status:
        parts.append(f"，实例状态是{params.status}")
    
    parts.append(f"，uid是{params.uid}")
    
    return "".join(parts)


# ============================================================================
# 测试执行函数
# ============================================================================

async def test_list_all_instances(test_cases: List[ListAllInstancesTestParams]):
    """测试list_all_instances工具"""
    logger.info("=" * 80)
    logger.info("开始测试 list_all_instances 工具")
    logger.info("=" * 80)
    
    agent = await create_test_agent()
    
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\n--- 测试用例 {i}/{len(test_cases)} ---")
        logger.info(f"参数: {test_case}")
        
        try:
            prompt = build_list_all_instances_prompt(test_case)
            logger.info(f"调用提示: {prompt}")
            
            result = await agent(Msg(name="User", content=prompt, role="user"))
            result_text = result.get_text_content()
            
            logger.info(f"测试结果: {result_text}")
            logger.info("-" * 80)
            
        except Exception as e:
            logger.error(f"测试用例 {i} 执行失败: {e}")
            logger.error(traceback.format_exc())
            logger.info("-" * 80)


async def test_list_pods_of_instance(test_cases: List[ListPodsOfInstanceTestParams]):
    """测试list_pods_of_instance工具"""
    logger.info("=" * 80)
    logger.info("开始测试 list_pods_of_instance 工具")
    logger.info("=" * 80)
    
    agent = await create_test_agent()
    
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\n--- 测试用例 {i}/{len(test_cases)} ---")
        logger.info(f"参数: {test_case}")
        
        try:
            prompt = build_list_pods_of_instance_prompt(test_case)
            logger.info(f"调用提示: {prompt}")
            
            result = await agent(Msg(name="User", content=prompt, role="user"))
            result_text = result.get_text_content()
            
            logger.info(f"测试结果: {result_text}")
            logger.info("-" * 80)
            
        except Exception as e:
            logger.error(f"测试用例 {i} 执行失败: {e}")
            logger.error(traceback.format_exc())
            logger.info("-" * 80)


async def test_list_clusters(test_cases: List[ListClustersTestParams]):
    """测试list_clusters工具"""
    logger.info("=" * 80)
    logger.info("开始测试 list_clusters 工具")
    logger.info("=" * 80)
    
    agent = await create_test_agent()
    
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\n--- 测试用例 {i}/{len(test_cases)} ---")
        logger.info(f"参数: {test_case}")
        
        try:
            prompt = build_list_clusters_prompt(test_case)
            logger.info(f"调用提示: {prompt}")
            
            result = await agent(Msg(name="User", content=prompt, role="user"))
            result_text = result.get_text_content()
            
            logger.info(f"测试结果: {result_text}")
            logger.info("-" * 80)
            
        except Exception as e:
            logger.error(f"测试用例 {i} 执行失败: {e}")
            logger.error(traceback.format_exc())
            logger.info("-" * 80)


async def test_list_instances(test_cases: List[ListInstancesTestParams]):
    """测试list_instances工具"""
    logger.info("=" * 80)
    logger.info("开始测试 list_instances 工具")
    logger.info("=" * 80)
    
    agent = await create_test_agent()
    
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\n--- 测试用例 {i}/{len(test_cases)} ---")
        logger.info(f"参数: {test_case}")
        
        try:
            prompt = build_list_instances_prompt(test_case)
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
        # 启动 MCP 服务器
        start_mcp_server()
        
        logger.info("开始初始化 MCP 测试环境...")
        await initialize_toolkit()
        logger.info("MCP 测试环境初始化完成")
        
        # 测试list_all_instances
        await test_list_all_instances(LIST_ALL_INSTANCES_TEST_CASES)
        
        # 测试list_pods_of_instance
        await test_list_pods_of_instance(LIST_PODS_OF_INSTANCE_TEST_CASES)
        
        # 测试list_clusters
        await test_list_clusters(LIST_CLUSTERS_TEST_CASES)
        
        # 测试list_instances
        await test_list_instances(LIST_INSTANCES_TEST_CASES)
        
        logger.info("=" * 80)
        logger.info("所有测试执行完成")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"测试执行失败: {e}")
        logger.error(traceback.format_exc())
        raise
    finally:
        # 停止 MCP 服务器
        stop_mcp_server()


async def main():
    """主函数"""
    # await run_all_tests()
    await create_test_agent()


if __name__ == "__main__":
    asyncio.run(main())

