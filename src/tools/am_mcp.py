from typing import Optional, Literal
from fastmcp import FastMCP, Context
from pydantic import Field
from lib.logger_config import setup_logger
import click
from alibabacloud_sysom20231230 import models as sys_om20231230_models

logger = setup_logger(__name__)
from lib import (
    ClientFactory,
    AMMCPHelper,
    MCPRequest,
    MCPResponse,
)
from lib.am_helper import AMResultCode
from lib.service_config import SERVICE_CONFIG

mcp = FastMCP("SysomAMSubMCP")


# 每个tool对应的MCPRequest和MCPResponse定义
class ListAllInstancesMCPRequest(MCPRequest):
    """ListAllInstances请求参数"""
    region: Optional[str] = Field(None, description="地域")
    managedType: Optional[str] = Field("managed", description="纳管类型")
    instanceType: Optional[str] = Field(None, description="实例类型")
    pluginId: Optional[str] = Field(None, description="插件ID")
    filters: Optional[str] = Field("", description="过滤条件，JSON字符串格式")
    current: Optional[str] = Field("1", description="页码，从1开始")
    pageSize: Optional[str] = Field("10", description="每页数量")
    maxResults: Optional[int] = Field(100, description="最大结果数")
    nextToken: Optional[str] = Field(None, description="分页游标，不为空表示还有更多数据")


class ListAllInstancesMCPResponse(MCPResponse):
    """ListAllInstances响应"""
    total: Optional[int] = Field(default=None, description="总数")
    nextToken: Optional[str] = Field(default=None, description="分页游标，不为空表示还有更多数据")
    maxResults: Optional[int] = Field(default=100, description="最大结果数")
    requestId: Optional[str] = Field(default=None, description="请求ID")


class ListPodsOfInstanceMCPRequest(MCPRequest):
    """ListPodsOfInstance请求参数"""
    instance: str = Field(..., description="实例ID")
    clusterId: Optional[str] = Field(None, alias="cluster_id", description="集群ID")
    current: Optional[int] = Field(1, description="页码，从1开始")
    pageSize: Optional[int] = Field(10, description="每页数量")


class ListPodsOfInstanceMCPResponse(MCPResponse):
    """ListPodsOfInstance响应"""
    total: Optional[int] = Field(default=None, description="总数")
    requestId: Optional[str] = Field(default=None, alias="RequestId", description="请求ID")


class ListClustersMCPRequest(MCPRequest):
    """ListClusters请求参数"""
    name: Optional[str] = Field(None, description="集群名称")
    clusterId: Optional[str] = Field(None, alias="cluster_id", description="集群ID（用于过滤）")
    clusterType: Optional[str] = Field(None, alias="cluster_type", description="集群类型")
    clusterStatus: Optional[str] = Field(None, alias="cluster_status", description="集群状态")
    current: Optional[int] = Field(1, description="页码，从1开始")
    pageSize: Optional[int] = Field(10, description="每页数量")


class ListClustersMCPResponse(MCPResponse):
    """ListClusters响应"""
    total: Optional[int] = Field(default=None, description="总数")
    requestId: Optional[str] = Field(default=None, alias="RequestId", description="请求ID")


class ListInstancesMCPRequest(MCPRequest):
    """ListInstances请求参数"""
    instance: Optional[str] = Field(None, description="实例ID")
    status: Optional[str] = Field(None, description="实例状态")
    region: Optional[str] = Field(None, description="地域")
    clusterId: Optional[str] = Field(None, alias="cluster_id", description="集群ID")
    current: Optional[int] = Field(1, description="页码，从1开始")
    pageSize: Optional[int] = Field(10, description="每页数量")


class ListInstancesMCPResponse(MCPResponse):
    """ListInstances响应"""
    total: Optional[int] = Field(default=None, description="总数")
    requestId: Optional[str] = Field(default=None, alias="request_id", description="请求ID")


@mcp.tool(
    tags={"sysom_am"}
)
async def list_all_instances(
    uid: str = Field(..., description="用户ID"),
    region: Optional[str] = Field(None, description="地域"),
    managedType: Optional[str] = Field("all", description="纳管类型，可选值：managed（已纳管）、unmanaged（未纳管）、all（全部）、install（待安装）、uninstall（待卸载）、upgrade（待升级）"),
    instanceType: Optional[str] = Field("ecs", description="实例类型"),
    pluginId: Optional[str] = Field("74a86327-3170-412c-8e67-da3389ec56a9", description="插件ID"),
    filters: Optional[str] = Field(None, description="过滤条件，JSON字符串格式"),
    current: Optional[str] = Field("1", description="页码，从1开始"),
    pageSize: Optional[str] = Field("10", description="每页数量"),
    maxResults: Optional[int] = Field(100, description="最大结果数"),
    nextToken: Optional[str] = Field(None, description="分页游标，不为空表示还有更多数据"),
    ctx: Context | None = None,
) -> ListAllInstancesMCPResponse:
    """列出所有实例，支持按地域、纳管类型、实例类型等条件筛选
    
    调用示例：
    
    1. 查询未纳管实例，通过instance_id_name筛选：
    {
        "uid": "uid-1",
        "region": "cn-hangzhou",
        "managedType": "unmanaged",
        "instanceType": "ecs",
        "filters": "[{\"infoType\": \"instance_id_name\", \"infoValue\": \"test-2\"}]"
    }
    
    2. 查询未纳管实例，通过IP筛选：
    {
        "uid": "uid-1",
        "region": "cn-hangzhou",
        "managedType": "unmanaged",
        "instanceType": "ecs",
        "filters": "[{\"infoType\": \"ip\", \"infoValue\": \"9.9.9.9\"}]"
    }
    
    3. 查询未纳管实例，通过instance_tag筛选：
    {
        "uid": "uid-1",
        "region": "cn-hangzhou",
        "managedType": "unmanaged",
        "instanceType": "ecs",
        "filters": "[{\"infoType\": \"instance_tag\", \"infoKey\": \"key3\", \"infoValue\": \"value3\"}]"
    }
    
    4. 查询未纳管实例，通过instance_tag + resource_group筛选：
    {
        "uid": "uid-1",
        "region": "cn-hangzhou",
        "managedType": "unmanaged",
        "instanceType": "ecs",
        "filters": "[{\"infoType\": \"instance_tag\", \"infoKey\": \"key1\", \"infoValue\": \"value1\"}, {\"infoType\": \"resource_group_id_name\", \"infoValue\": \"rg-test-3\"}]"
    }
    
    5. 查询已纳管实例，通过健康度筛选：
    {
        "uid": "uid-1",
        "region": "cn-hangzhou",
        "managedType": "managed",
        "instanceType": "ecs",
        "filters": "[{\"infoType\": \"os_health_score\", \"infoValue\": \"unhealthy\"}]"
    }
    
    6. 查询已纳管实例，通过agent_config_id筛选：
    {
        "uid": "uid-1",
        "region": "cn-hangzhou",
        "managedType": "managed",
        "instanceType": "ecs",
        "filters": "[{\"infoType\": \"agent_config_id\", \"infoValue\": \"test-config-id1\"}]"
    }
    
    7. 查询已纳管实例，通过instance_id筛选（支持多个，逗号分隔）：
    {
        "uid": "uid-1",
        "managedType": "managed",
        "filters": "[{\"infoType\": \"instance_id\", \"infoValue\": \"i-test-1,i-test-7\"}]"
    }
    
    8. 查询已纳管实例，通过cluster_id筛选：
    {
        "uid": "uid-1",
        "region": "cn-hangzhou",
        "managedType": "managed",
        "filters": "[{\"infoType\": \"cluster_id\", \"infoValue\": \"cluster-id-123\"}]"
    }
    
    9. 查询已纳管实例，通过GPU筛选：
    {
        "uid": "uid-1",
        "region": "cn-hangzhou",
        "managedType": "managed",
        "filters": "[{\"infoType\": \"gpu\", \"infoValue\": \"nvidia\"}]"
    }
    
    10. 查询可以安装插件的实例（待安装）：
    {
        "uid": "uid-1",
        "region": "cn-hangzhou",
        "managedType": "install",
        "instanceType": "ecs",
        "pluginId": "plugin-sysak-id",
        "filters": "[{\"infoType\": \"instance_tag\", \"infoKey\": \"key1\", \"infoValue\": \"value1\"}]"
    }
    
    11. 查询可以卸载插件的实例（待卸载）：
    {
        "uid": "uid-1",
        "region": "cn-hangzhou",
        "managedType": "uninstall",
        "instanceType": "ecs",
        "pluginId": "plugin-sysak-id",
        "filters": "[{\"infoType\": \"instance_id_name\", \"infoValue\": \"test-6\"}]"
    }
    
    12. 查询可以升级插件的实例（待升级）：
    {
        "uid": "uid-1",
        "region": "cn-hangzhou",
        "managedType": "upgrade",
        "instanceType": "ecs",
        "pluginId": "plugin-copilot-id",
        "filters": "[{\"infoType\": \"instance_tag\", \"infoKey\": \"key3\", \"infoValue\": \"value3\"}]"
    }
    
    13. 查询所有实例（不区分纳管状态）：
    {
        "uid": "uid-1",
        "region": "cn-hangzhou",
        "managedType": "all",
        "instanceType": "ecs",
        "pluginId": "plugin-sysak-id"
    }
    
    14. 分页查询：
    {
        "uid": "uid-1",
        "region": "cn-hangzhou",
        "managedType": "managed",
        "current": 1,
        "pageSize": 20
    }
    
    注意：
    - filters参数必须是JSON字符串格式，包含一个数组，数组中每个元素是一个筛选条件对象
    - 筛选条件对象包含infoType（筛选类型）和infoValue（筛选值），某些类型还需要infoKey（如instance_tag）
    - 支持的infoType包括：instance_id, instance_id_name, ip, instance_tag, resource_group_id_name, 
      os_health_score, agent_config_id, cluster_id, gpu等
    - 通过实例id查询时，infoType使用instance_id_name，infoValue使用实例ID或实例名称，逗号分隔多个实例ID或实例名称
    - 分页查询时，current和pageSize必须同时指定，current从1开始，pageSize为每页数量，maxResults为最大结果数，nextToken为分页游标，不为空表示还有更多数据
    
    Args:
        uid: 用户ID
        region: 地域，如cn-hangzhou
        managedType: 纳管类型
        instanceType: 实例类型
        pluginId: 插件ID
        filters: 过滤条件，JSON字符串格式
        current: 页码
        pageSize: 每页数量，从1开始
        maxResults: 最大结果数
        nextToken: 分页游标，不为空表示还有更多数据
        
    Returns:
        AMResult: 包含实例列表的响应对象
            code: 状态码，可能的值：
                - Success: 请求成功
                - Error: 请求失败
            message: 详细的错误信息，当code不为Success时提供
            data: 响应数据，当code为Success时包含响应数据
            total: 总数（列表接口）
            requestId: 请求ID
    """
    try:
        # 使用ClientFactory创建客户端
        client = ClientFactory.create_client(
            uid=uid,
        )
        
        # 创建MCP Helper
        helper = AMMCPHelper(client)
        
        # 创建MCP请求

        mcp_request = sys_om20231230_models.ListAllInstancesRequest(
            region=region,
            # managedType=managedType,
            instanceType=instanceType,
            pluginId=pluginId,
            filters=filters,
            current=current,
            pageSize=pageSize,
            maxResults=maxResults,
            nextToken=nextToken,
        )
        
        # 调用Helper方法
        response = await helper.list_all_instances(mcp_request)
        return ListAllInstancesMCPResponse(**response.model_dump())
    except Exception as e:
        logger.error(f"list_all_instances failed: {e}")
        return ListAllInstancesMCPResponse(
            code=AMResultCode.ERROR,
            message=f"调用失败：{str(e)}",
            data=None
        )


@mcp.tool(
    tags={"sysom_am"}
)
async def list_pods_of_instance(
    uid: str = Field(..., description="用户ID"),
    instance: str = Field(..., description="实例ID"),
    clusterId: Optional[str] = Field(None, alias="cluster_id", description="集群ID"),
    current: Optional[int] = Field(1, description="页码，从1开始"),
    pageSize: Optional[int] = Field(10, description="每页数量"),
    ctx: Context | None = None,
) -> ListPodsOfInstanceMCPResponse:
    """列出指定实例下的Pod列表
    
    Args:
        uid: 用户ID
        instance: 实例ID
        clusterId: 集群ID
        current: 页码，从1开始
        pageSize: 每页数量
    Returns:
        AMResult: 包含Pod列表的响应对象，每个Pod包含pod和namespace字段
            code: 状态码，可能的值：
                - Success: 请求成功
                - Error: 请求失败
            message: 详细的错误信息，当code不为Success时提供
            data: 响应数据，当code为Success时包含响应数据
            total: 总数（列表接口）
            requestId: 请求ID
    """
    try:
        # 使用ClientFactory创建客户端

        client = ClientFactory.create_client(
            uid=uid,
        )
        
        
        
        # 创建MCP Helper
        helper = AMMCPHelper(client)
        
        # 创建MCP请求
        mcp_request = ListPodsOfInstanceMCPRequest(
            instance=instance,
            clusterId=clusterId,
            current=current,
            pageSize=pageSize,
        )
        
        # 调用Helper方法
        response = await helper.list_pods_of_instance(mcp_request)
        return ListPodsOfInstanceMCPResponse(**response.model_dump())
    except Exception as e:
        logger.error(f"list_pods_of_instance failed: {e}")
        return ListPodsOfInstanceMCPResponse(
            code=AMResultCode.ERROR,
            message=f"调用失败：{str(e)}",
            data=None
        )


@mcp.tool(
    tags={"sysom_am"}
)
async def list_clusters(
    uid: str = Field(..., description="用户ID"),
    name: Optional[str] = Field(None, description="集群名称"),
    clusterId: Optional[str] = Field(None, alias="cluster_id", description="集群ID（用于过滤）"),
    clusterType: Optional[str] = Field(None, alias="cluster_type", description="集群类型"),
    clusterStatus: Optional[str] = Field(None, alias="cluster_status", description="集群状态"),
    current: Optional[int] = Field(1, description="页码，从1开始"),
    pageSize: Optional[int] = Field(10, description="每页数量"),
    ctx: Context | None = None,
) -> ListClustersMCPResponse:
    """列出集群列表，支持按名称、类型、状态等条件筛选
    
    Args:
        uid: 用户ID
        name: 集群名称
        clusterId: 集群ID（用于过滤）
        clusterType: 集群类型
        clusterStatus: 集群状态
        current: 页码，从1开始
        pageSize: 每页数量
    Returns:
        AMResult: 包含集群列表的响应对象
            code: 状态码，可能的值：
                - Success: 请求成功
                - Error: 请求失败
            message: 详细的错误信息，当code不为Success时提供
            data: 响应数据，当code为Success时包含响应数据
            total: 总数（列表接口）
            requestId: 请求ID
    """
    try:
        # 使用ClientFactory创建客户端
        client = ClientFactory.create_client(
            uid=uid,
        )
        
        # 创建MCP Helper
        helper = AMMCPHelper(client)
        
        # 创建MCP请求
        mcp_request = ListClustersMCPRequest(
            name=name,
            clusterId=clusterId,
            clusterType=clusterType,
            clusterStatus=clusterStatus,
            current=current,
            pageSize=pageSize,
        )
        
        # 调用Helper方法
        response = await helper.list_clusters(mcp_request)
        return ListClustersMCPResponse(**response.model_dump())
    except Exception as e:
        logger.error(f"list_clusters failed: {e}")
        return ListClustersMCPResponse(
            code=AMResultCode.ERROR,
            message=f"调用失败：{str(e)}",
            data=None
        )


@mcp.tool(
    tags={"sysom_am"}
)
async def list_instances(
    uid: str = Field(..., description="用户ID"),
    instance: Optional[str] = Field(None, description="实例ID"),
    status: Optional[str] = Field(None, description="实例状态"),
    region: Optional[str] = Field(None, description="地域"),
    clusterId: Optional[str] = Field(None, alias="cluster_id", description="集群ID"),
    current: Optional[int] = Field(1, description="页码，从1开始"),
    pageSize: Optional[int] = Field(10, description="每页数量"),
    ctx: Context | None = None,
) -> ListInstancesMCPResponse:
    """列出实例列表，支持按实例ID、状态、地域、集群等条件筛选
    
    Args:
        uid: 用户ID
        instance: 实例ID
        status: 实例状态
        region: 地域
        clusterId: 集群ID
        current: 页码，从1开始
        pageSize: 每页数量
        
    Returns:
        AMResult: 包含实例列表的响应对象
            code: 状态码，可能的值：
                - Success: 请求成功
                - Error: 请求失败
            message: 详细的错误信息，当code不为Success时提供
            data: 响应数据，当code为Success时包含响应数据
            total: 总数（列表接口）
            requestId: 请求ID
    """
    try:
        logger.info(f"creating client")
        # 使用ClientFactory创建客户端
        client = ClientFactory.create_client(
            uid=uid,
        )
        logger.info(f"created client")
        # 创建MCP Helper
        helper = AMMCPHelper(client)
        
        # 创建MCP请求
        mcp_request = sys_om20231230_models.ListInstancesRequest(
            instance=instance,
            status=status,
            region=region,
            clusterId=clusterId,
            current=current,
            pageSize=pageSize,
        )
        # 调用Helper方法
        response = await helper.list_instances(mcp_request)
        return ListInstancesMCPResponse(**response.model_dump())
    except Exception as e:
        logger.error(f"list_instances failed: {e}")
        return ListInstancesMCPResponse(
            code=AMResultCode.ERROR,
            message=f"调用失败：{str(e)}",
            data=None
        )


@click.command()
@click.option("--stdio", "run_mode", flag_value="stdio", default=True, help="Run in stdio mode")
@click.option("--sse", "run_mode", flag_value="sse", help="Run in SSE mode")
@click.option("--host", default="127.0.0.1", help="Host to bind to (for SSE mode, default: 127.0.0.1)")
@click.option("--port", default=7130, type=int, help="Port to bind to (for SSE mode, default: 7130)")
@click.option("--path", default="/mcp/am", help="Path for SSE endpoint (default: /mcp/am)")
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

