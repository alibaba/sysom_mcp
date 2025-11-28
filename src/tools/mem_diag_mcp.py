from typing import Optional, Literal
from fastmcp import FastMCP, Context
from pydantic import Field
from lib.logger_config import setup_logger
import click


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

# memgraph诊断请求参数示例：
# {\"instance\":\"i-bp148hw2bn8rktm8u1a7\",\"pod\":\"\",\"region\":\"cn-hangzhou\",\"instanceName\":\"\"}
# {\"instance\":\"i-bp148hw2bn8rktm8u1a7\",\"pod\":\"kagent-ui-569cb875c6-h6l4s\",\"region\":\"cn-hangzhou\",\"instanceName\":\"\"}
# {\"pod\":\"kagent-controller-794fc765df-zgtfd\",\"clusterType\":\"ackClusters\",\"clusterId\":\"c0addd452a4664dbe8cf846f5fed91f7e\",\"namespace\":\"kagent\",\"instance\":\"\",\"region\":\"cn-hangzhou\"}

class MemGraphDiagnosisMCPRequestParams(DiagnosisMCPRequestParams):
    """memgraph诊断请求参数"""
    instance: Optional[str] = Field(None, description="实例ID")
    pod: Optional[str] = Field(None, description="Pod名称")
    clusterType: Optional[str] = Field(None, description="集群类型")
    clusterId: Optional[str] = Field(None, description="集群ID")
    namespace: Optional[str] = Field(None, description="Pod命名空间")

@mcp.tool(
    tags={"sysom_memdiag"}
)
async def memgraph(
    uid: str = Field(..., description="用户ID"),
    region: str = Field(..., description="地域"),
    channel: str = Field(..., description="诊断通道"),
    instance: Optional[str] = Field(None, description="实例名称"),
    pod: Optional[str] = Field(None, description="Pod名称"),
    clusterType: Optional[str] = Field(None, description="集群类型，可选值：ackClusters，表示ACK托管集群；ackServerlessClusters，表示ACK Serverless集群；acsClusters，表示ACS集群"),
    clusterId: Optional[str] = Field(None, description="集群ID"),
    namespace: Optional[str] = Field(None, description="Pod命名空间"),
    ctx: Context | None = None,
) -> DiagnosisMCPResponse:
    """
    memgraph（内存全景分析）工具：内存全景分析适用于内存占用较高但无法明确识别具体内存占用情况的场景。通过使用内存全景分析诊断功能，可以扫描当前系统的内存占用状态，详细拆解内存使用情况。系统内存与应用内存的分布，并列出当前Top 30的应用内存使用、文件缓存、共享内存缓存占用情况的排序。
    必需参数：
        - uid: 用户ID
        - region: 地域
        - channel: 诊断通道，可选值：ecs，auto
    支持两种模式：
        1. 节点诊断：对指定实例或实例中指定的Pod进行内存全景分析，channel必须为ecs。
            额外参数说明：
                - instance: 实例ID
                - pod: Pod名称（可选）
            示例：
                - {"uid": "123456789", "channel":"ecs", "instance":"i-bp148hw2bn8rktm8u1a7","region":"cn-hangzhou"}
                - {"uid": "123456789", "channel":"ecs", "instance":"i-bp148hw2bn8rktm8u1a7","pod":"kagent-ui-569cb875c6-h6l4s","region":"cn-hangzhou"}
        2. Pod诊断：对指定集群中特定namespace下的特定Pod进行内存全景分析，channel必须为auto。
            额外参数说明：
                - clusterType: 集群类型，可选值：
                    - ackClusters：表示ACK托管集群；
                    - ackServerlessClusters：表示ACK Serverless集群；
                    - acsClusters：表示ACS集群。
                - clusterId: 集群ID
                - namespace: Pod命名空间
                - pod: Pod名称
            示例：
                - {"uid": "123456789", "channel":"auto", "clusterType":"ackClusters", "clusterId":"c0addd452a4664dbe8cf846f5fed91f7e","namespace":"kagent","pod":"kagent-controller-794fc765df-zgtfd","region":"cn-hangzhou"}
                - {"uid": "123456789", "channel":"auto", "clusterType":"ackServerlessClusters", "clusterId":"c0addd452a4664dbe8cf846f5fed91f7e","namespace":"kagent","pod":"kagent-controller-794fc765df-zgtfd","region":"cn-hangzhou"}
                - {"uid": "123456789", "channel":"auto", "clusterType":"acsClusters", "clusterId":"c0addd452a4664dbe8cf846f5fed91f7e","namespace":"kagent","pod":"kagent-controller-794fc765df-zgtfd","region":"cn-hangzhou"}
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
            task_id: 诊断任务ID
            result: 诊断结果，当code为Success时包含诊断结果
    """
    try:
        # 使用ClientFactory创建客户端
        client = ClientFactory.create_client(
            uid=uid
        )
        
        # 创建MCP Helper
        helper = DiagnosisMCPHelper(client, timeout=150, poll_interval=1)
        
        # 创建诊断参数
        params_obj = MemGraphDiagnosisMCPRequestParams(
            region=region,
            instance=instance,
            pod=pod,
            clusterType=clusterType,
            clusterId=clusterId,
            namespace=namespace,
        )
        
        # 将参数对象转换为字典（包含region和_hide）
        params = params_obj.model_dump(exclude_none=True, by_alias=True)
        
        # 创建MCP请求
        mcp_request = DiagnosisMCPRequest(
            service_name="memgraph",
            channel=channel,
            region=region,
            params=params
        )
        
        # 执行诊断
        return await helper.execute(mcp_request)
    except Exception as e:
        logger.error(f"memgraph诊断失败: {e}")
        return DiagnosisMCPResponse(
            code=DiagnoseResultCode.TASK_CREATE_FAILED,
            message=f"诊断失败：{str(e)}",
            task_id=""
        )

# Java内存诊断请求参数示例：
# {\"instance\":\"i-bp1ggzdn555gsz87u9d7\",\"duration\":\"0\",\"pod\":\"alinux3-775ff84ccd-r9nsg\",\"region\":\"cn-hangzhou\",\"instanceName\":\"\"}
# {\"instance\":\"i-bp1ggzdn555gsz87u9d7\",\"duration\":\"3\",\"pod\":\"\",\"Pid\":\"1234\",\"region\":\"cn-hangzhou\",\"instanceName\":\"\"}
# {\"clusterType\":\"ackClusters\",\"clusterId\":\"c0addd452a4664dbe8cf846f5fed91f7e\",\"namespace\":\"kagent\",\"pod\":\"kagent-controller-794fc765df-zgtfd\",\"mode\":\"Pid\",\"instance\":\"\",\"Pid\":\"\",\"duration\":\"0\",\"region\":\"cn-hangzhou\"}

class JavaMemDiagnosisMCPRequestParams(DiagnosisMCPRequestParams):
    """javamem诊断请求参数"""
    instance: str = Field(..., description="实例名称")
    pid: Optional[str] = Field(None, alias="Pid", description="Java进程Pid")
    pod: Optional[str] = Field(None, description="Pod名称")
    duration: Optional[str] = Field("0", description="JNI内存分配profiling时长")
    clusterType: Optional[str] = Field(None, description="集群类型")
    clusterId: Optional[str] = Field(None, description="集群ID")
    namespace: Optional[str] = Field(None, description="Pod命名空间")

@mcp.tool(
        tags={"sysom_memdiag"}
)
async def javamem(
    uid: str = Field(..., description="用户ID"),
    region: str = Field(..., description="实例地域"),
    channel: str = Field(..., description="诊断通道"),
    instance: str = Field(..., description="实例ID"),
    # mode: Optional[str] = Field(None, description="诊断模式，可选值：Pid，表示基于进程ID诊断；Pod，表示基于Pod诊断"),
    pid: Optional[str] = Field(None, description="Java进程Pid"),
    pod: Optional[str] = Field(None, description="Pod名称"),
    duration: Optional[str] = Field("0", description="JNI内存分配profiling时长"),
    clusterType: Optional[str] = Field(None, description="集群类型"),
    clusterId: Optional[str] = Field(None, description="集群ID"),
    namespace: Optional[str] = Field(None, description="Pod命名空间"),
    ctx: Context | None = None,
) -> DiagnosisMCPResponse:
    """
    javamem（Java内存诊断）工具，主要用于诊断Java应用的内存使用情况，帮助用户了解Java堆内存和非堆内存的分布和组成，识别潜在的内存泄漏和内存溢出问题，实现Java内存的可维可测可追踪。
    使用场景：Java应用内存占用较高，无法明确识别具体内存占用情况。
    必需参数：
        - uid: 用户ID
        - region: 地域
        - channel: 诊断通道，可选值：ecs，auto
    支持两种模式：
        1. 节点诊断：对指定实例中指定Pid进程进行Java内存诊断，或对指定实例中指定Pod中1号进程（适用于单容器且Java进程作为容器1号进程的业务Pod）进行Java内存诊断，channel必须为ecs。
            额外参数说明：pid和pod至少提供一个
                - instance: 实例ID
                - pid: Java进程Pid（可选）
                - pod: Pod名称（可选）
                - duration: JNI内存分配profiling时长(可选)
            示例：
                - {"uid": "123456789", "channel":"ecs", "instance":"i-bp1ggzdn555gsz87u9d7","region":"cn-hangzhou","pid":"1234","duration":"30"}
                - {"uid": "123456789", "channel":"ecs", "instance":"i-bp1ggzdn555gsz87u9d7","region":"cn-hangzhou","pod":"alinux3-775ff84ccd-r9nsg"}
        2. Pod诊断：对指定集群中特定namespace下的特定Pod中1号进程（适用于单容器且Java进程作为容器1号进程的业务Pod）进行Java内存诊断，channel必须为auto。
            额外参数说明：
                - clusterType: 集群类型，可选值：ackClusters，表示ACK托管集群；ackServerlessClusters，表示ACK Serverless集群；acsClusters，表示ACS集群
                - clusterId: 集群ID
                - namespace: Pod命名空间
                - pod: Pod名称
                - duration: JNI内存分配profiling时长(可选)
            示例：
                - {"uid": "123456789", "channel":"auto", "clusterType":"ackClusters", "clusterId":"c0addd452a4664dbe8cf846f5fed91f7e","namespace":"kagent","pod":"kagent-controller-794fc765df-zgtfd","region":"cn-hangzhou"}
                - {"uid": "123456789", "channel":"auto", "clusterType":"ackServerlessClusters", "clusterId":"c0addd452a4664dbe8cf846f5fed91f7e","namespace":"kagent","pod":"kagent-controller-794fc765df-zgtfd","region":"cn-hangzhou"}
                - {"uid": "123456789", "channel":"auto", "clusterType":"acsClusters", "clusterId":"c0addd452a4664dbe8cf846f5fed91f7e","namespace":"kagent","pod":"kagent-controller-794fc765df-zgtfd","region":"cn-hangzhou"}
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
        # 使用ClientFactory创建客户端
        client = ClientFactory.create_client(
            uid=uid
        )
        
        # 创建MCP Helper
        helper = DiagnosisMCPHelper(client, timeout=150, poll_interval=1)
        
        # 创建诊断参数
        params_obj = JavaMemDiagnosisMCPRequestParams(
            region=region,
            instance=instance,
            Pid=pid,
            pod=pod,
            duration=duration or "0",
            clusterType=clusterType,
            clusterId=clusterId,
            namespace=namespace,
        )
        
        # 将参数对象转换为字典（包含region和_hide）
        params = params_obj.model_dump(exclude_none=True, by_alias=True)
        
        # 创建MCP请求
        mcp_request = DiagnosisMCPRequest(
            service_name="javamem",
            channel=channel,
            region=region,
            params=params
        )
        
        # 执行诊断
        return await helper.execute(mcp_request)
    except Exception as e:
        logger.error(f"javamem诊断失败: {e}")
        return DiagnosisMCPResponse(
            code=DiagnoseResultCode.TASK_CREATE_FAILED,
            message=f"诊断失败：{str(e)}",
            task_id=""
        )

# OOM诊断请求参数示例：
# {\"instance\":\"i-bp1blue83tmld03eyhkz\",\"pod\":\"envoy-gateway-8cd5fc4d9-gcbnp\",\"time\":1763222400,\"region\":\"cn-hangzhou\",\"instanceName\":\"\"}
# {\"pod\":\"envoy-gateway-8cd5fc4d9-gcbnp\",\"clusterType\":\"ackClusters\",\"clusterId\":\"c0addd452a4664dbe8cf846f5fed91f7e\",\"namespace\":\"envoy-gateway-system\",\"instance\":\"\",\"time\":\"\",\"region\":\"cn-hangzhou\"}

class OOMCheckDiagnosisMCPRequestParams(DiagnosisMCPRequestParams):
    """oomcheck诊断请求参数"""
    instance: Optional[str] = Field(None, description="实例ID")
    pod: Optional[str] = Field(None, description="Pod名称")
    time: Optional[str] = Field(None, description="时间戳")
    clusterType: Optional[str] = Field(None, description="集群类型")
    clusterId: Optional[str] = Field(None, description="集群ID")
    namespace: Optional[str] = Field(None, description="Pod命名空间")
@mcp.tool(
    tags={"sysom_memdiag"}
)
async def oomcheck(
    uid: str = Field(..., description="用户ID"),
    region: str = Field(..., description="实例地域"),
    channel: str = Field(..., description="诊断通道"),
    instance: Optional[str] = Field(None, description="实例ID"),
    pod: Optional[str] = Field(None, description="Pod名称"),
    time: Optional[str] = Field(None, description="时间戳"),
    clusterType: Optional[str] = Field(None, description="集群类型"),
    clusterId: Optional[str] = Field(None, description="集群ID"),
    namespace: Optional[str] = Field(None, description="Pod命名空间"),
    ctx: Context | None = None,
) -> DiagnosisMCPResponse:
    """
    oomcheck（OOM诊断）工具，主要用于分析和界定OOM（Out of memory）问题，找出导致OOM的主要原因，并给出相应的处理建议，帮助用户解决OOM问题，提高系统的可用性和性能。
    使用场景：发生OOM问题，需要诊断OOM原因，常见的OOM场景包括：
        - 系统全局内存不足：整个主机的内存使用过量，导致系统内存不足，从而触发了OOM。
        - cgroup内存使用超限：在指定的cgroup下，进程的内存使用超过了设定限制，导致该cgroup整体的内存使用达到上限，从而触发了OOM。
        - 父级cgroup内存使用超限：父cgroup下的进程内存使用超标，导致父cgroup整体内存使用达到限制，从而触发了OOM。在终止进程时，系统选择了子cgroup下的进程执行终止操作。
        - 内存节点的内存不足：在NUMA存储模式下，操作系统可能具有多个内存节点（可通过执行cat /proc/buddyinfo命令来查看相关资源信息）。如果通过cpuset.mems参数指定cgroup仅能够使用特定内存节点的内存，则可能会导致实例在具备充足空闲内存的情况下，仍然出现OOM Killer的情况。
        - 共享内存过度使用导致cgroup内存使用超限：在cgroup内存使用超限的情况下，进一步发现cgroup下的共享内存使用已超过总的cgroup用户态内存的30%。因此，可以认为造成OOM的主要原因是共享内存的过量使用，需要进一步分析共享内存的主要占用者。
    必需参数：
        - uid: 用户ID
        - region: 地域
        - channel: 诊断通道，可选值：ecs，auto
    支持两种模式：
        1. 节点诊断：对指定实例或实例中指定的Pod进行OOM诊断，channel必须为ecs。
            额外参数说明：
                - instance: 实例ID
                - pod: Pod名称（可选）
                - time: 时间戳（可选），指定时间点的情况下，诊断离目标时间点最近一次的OOM事件，不指定则诊断最近一次的OOM事件。
            示例：
                - {"uid": "123456789", "channel":"ecs", "instance":"i-bp148hw2bn8rktm8u1a7","region":"cn-hangzhou"}
                - {"uid": "123456789", "channel":"ecs", "instance":"i-bp148hw2bn8rktm8u1a7","pod":"kagent-ui-569cb875c6-h6l4s","region":"cn-hangzhou","time":"1763222400"}
        2. Pod诊断：对指定集群中特定namespace下的特定Pod进行OOM诊断，channel必须为auto。
            额外参数说明：
                - clusterType: 集群类型，可选值：ackClusters，表示ACK托管集群；ackServerlessClusters，表示ACK Serverless集群；acsClusters，表示ACS集群
                - clusterId: 集群ID
                - namespace: Pod命名空间
                - pod: Pod名称
                - time: 时间戳（可选），指定时间点的情况下，诊断离目标时间点最近一次的OOM事件，不指定则诊断最近一次的OOM事件
            示例：
                - {"uid": "123456789", "channel":"auto", "clusterType":"ackClusters", "clusterId":"c0addd452a4664dbe8cf846f5fed91f7e","namespace":"kagent","pod":"kagent-controller-794fc765df-zgtfd","region":"cn-hangzhou"}
                - {"uid": "123456789", "channel":"auto", "clusterType":"ackServerlessClusters", "clusterId":"c0addd452a4664dbe8cf846f5fed91f7e","namespace":"kagent","pod":"kagent-controller-794fc765df-zgtfd","region":"cn-hangzhou"}
                - {"uid": "123456789", "channel":"auto", "clusterType":"acsClusters", "clusterId":"c0addd452a4664dbe8cf846f5fed91f7e","namespace":"kagent","pod":"kagent-controller-794fc765df-zgtfd","region":"cn-hangzhou"}
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
        # 使用ClientFactory创建客户端
        client = ClientFactory.create_client(
            uid=uid
        )
        
        # 创建MCP Helper
        helper = DiagnosisMCPHelper(client, timeout=150, poll_interval=1)
        
        # 创建诊断参数
        params_obj = OOMCheckDiagnosisMCPRequestParams(
            region=region,
            instance=instance,
            pod=pod,
            time=time,
            clusterType=clusterType,
            clusterId=clusterId,
            namespace=namespace,
        )
        
        # 将参数对象转换为字典（包含region和_hide）
        params = params_obj.model_dump(exclude_none=True, by_alias=True)
        
        # 创建MCP请求
        mcp_request = DiagnosisMCPRequest(
            service_name="oomcheck",
            channel=channel,
            region=region,
            params=params
        )
        
        # 执行诊断
        return await helper.execute(mcp_request)
    except Exception as e:
        logger.error(f"oomcheck诊断失败: {e}")
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
@click.option("--path", default="/mcp/mem_diag", help="Path for SSE endpoint (default: /mcp/mem_diag)")
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

