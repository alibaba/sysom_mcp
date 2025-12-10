from typing import List, Optional, Literal
from fastmcp import FastMCP, Context
from pydantic import BaseModel, Field
from lib.logger_config import setup_logger
import click

logger = setup_logger(__name__)

from lib import (
    ClientFactory,
)
from lib.service_config import SERVICE_CONFIG
from lib.crash_agent_helper import (
    CrashAgentMCPHelper,
)
from alibabacloud_sysom20231230 import models as sysom_20231230_models

mcp = FastMCP("SysomCrashAgentSubMCP")


class TaskBaseInfo(BaseModel):
    taskId: Optional[str] = Field(default=None, description="任务ID")
    taskType: Optional[str] = Field(
        default=None, description="任务类型 (vmcore 或 dmesg)"
    )
    taskStatus: Optional[str] = Field(
        default=None, description="任务状态 (created, queued, running, success, error)"
    )
    createdAt: Optional[str] = Field(default=None, description="任务创建时间")
    errorMsg: Optional[str] = Field(default=None, description="错误信息（任务失败时）")


class TaskInfo(BaseModel):
    """查询诊断任务响应"""

    taskId: Optional[str] = Field(default=None, description="任务ID")
    taskType: Optional[str] = Field(
        default=None, description="任务类型 (vmcore 或 dmesg)"
    )
    taskStatus: Optional[str] = Field(
        default=None, description="任务状态 (created, queued, running, success, error)"
    )
    createdAt: Optional[str] = Field(default=None, description="任务创建时间")
    errorMsg: Optional[str] = Field(default=None, description="错误信息（任务失败时）")

    diagnoseResult: Optional[str] = Field(
        default=None, description="诊断结果详情（任务完成时）"
    )
    urls: Optional[dict] = Field(default=None, description="诊断任务下发的文件下载链接")


class TaskId(BaseModel):
    """任务ID"""

    taskId: str = Field(default="", description="任务ID")


class BaseResponse(BaseModel):
    """基础响应"""

    code: str = Field(default="Success", description="状态码")
    message: str = Field(default="", description="错误信息")


class CreateTaskMCPResponse(BaseModel):
    """创建任务响应"""

    data: Optional[TaskId] = Field(default=None, description="返回数据")


class GetTaskMCPResponse(BaseResponse):
    """获取任务详情响应"""

    data: Optional[TaskInfo] = Field(default=None, description="任务详情")


class ListHistoryTasksMCPResponse(BaseResponse):
    """查询历史任务响应"""

    data: Optional[List[TaskBaseInfo]] = Field(default=None, description="任务列表")


@mcp.tool(tags={"sysom_crash_agent"})
async def create_vmcore_diagnosis_task(
    vmcore_url: str = Field(..., description="vmcore文件下载链接"),
    debuginfo_url: Optional[str] = Field(
        None, description="debuginfo文件下载链接（可选）"
    ),
    debuginfo_common_url: Optional[str] = Field(
        None, description="debuginfo-commmon下载链接（可选）"
    ),
) -> CreateTaskMCPResponse:
    """
    创建基于VMCORE文件的内核宕机诊断任务。此工具会分析内核崩溃时生成的VMCORE文件，结合debug符号信息，定位系统崩溃的根本原因，并搜索相关社区修复补丁。请注意此工具仅在分析Alinux和CentOS内核的vmcore文件时不需要提供debuginfo文件，对于其他发行版内核，需要提供debuginfo文件， 请确保提供的debuginfo文件正确。
    VMCORE诊断正常会持续5-30分钟，请耐心等待后查询结果。

    功能描述：
        创建一个基于VMCORE文件的内核宕机诊断任务，分析系统崩溃时的状态并定位根本原因

    使用场景：
        1. Linux内核发生panic导致系统宕机
        2. 需要分析系统崩溃时的内核状态
        3. 定位引起系统崩溃的具体驱动或内核模块

    参数说明：
        vmcore_url (str): vmcore文件下载链接（必填）
        debuginfo_url (Optional[str]): debuginfo文件下载链接（可选）
                   注意：对于CentOS或Alinux内核，系统会自动下载相应的debuginfo文件，
                   此时无需提供该参数；对于其他发行版内核，需要手动提供该参数。
        debuginfo_common_url (Optional[str]): debuginfo-common文件下载链接（可选）
                   注意：对于CentOS或Alinux内核，系统会自动下载相应的公共debuginfo文件，
                   此时无需提供该参数；对于其他发行版内核，需要手动提供该参数。

    返回值:
        CreateTaskMCPResponse: 包含诊断任务ID的响应对象
            - code: 状态码 ("Success"表示成功，"Error"表示失败)
            - message: 错误信息 (当code为"Error"时提供具体错误信息)
            - data: 包含任务ID的对象
                - taskId: 诊断任务ID (可用于查询诊断结果)

        成功示例:
            {"code": "Success", "message": "", "data": {"taskId": "99fc9c12-7169-4283-9ad1-94193c3486c1"}}

        失败示例:
            {"code": "Error", "message": "创建诊断任务失败: 具体错误信息", "data": null}
    """
    try:
        client = ClientFactory.create_client()
        helper = CrashAgentMCPHelper(client)
        request = sysom_20231230_models.CreateVmcoreDiagnosisTaskRequest(
            task_type="vmcore",
            vmcore_url=vmcore_url,
            debuginfo_url=debuginfo_url,
            debuginfo_common_url=debuginfo_common_url,
        )
        response = await helper.create_task(request)
        return CreateTaskMCPResponse(**response.model_dump())
    except Exception as e:
        logger.error(f"create_vmcore_diagnosis_task failed: {e}")
        return CreateTaskMCPResponse(
            code="Error", message=f"调用失败：{str(e)}", data=None
        )


@mcp.tool(tags={"sysom_crash_agent"})
async def create_dmesg_diagnosis_task(
    dmesg_url: str = Field(..., description="dmesg日志文件下载链接"),
) -> CreateTaskMCPResponse:
    """
    创建基于dmesg日志的系统诊断任务。此工具分析系统宕机保留的dmesg日志并分析宕机原因。

    功能描述：
        创建一个基于dmesg日志的系统诊断任务，用于分析系统宕机原因

    使用场景：
        1. 分析内核运行过程中宕机的原因
        2. 检查是否有硬件问题导致宕机
        3. 分析宕机的产生原因

    参数说明：
        dmesg_url (str): dmesg日志文件下载链接（必填）

    返回值:
        CreateTaskMCPResponse: 包含诊断任务ID的响应对象
            - code: 状态码 ("Success"表示成功，"Error"表示失败)
            - message: 错误信息 (当code为"Error"时提供具体错误信息)
            - data: 包含任务ID的对象
                - taskId: 诊断任务ID (可用于查询诊断结果)

        成功示例:
            {"code": "Success", "message": "", "data": {"taskId": "99fc9c12-7169-4283-9ad1-94193c3486c1"}}

        失败示例:
            {"code": "Error", "message": "创建诊断任务失败: 具体错误信息", "data": null}
    """
    try:
        client = ClientFactory.create_client()
        helper = CrashAgentMCPHelper(client)
        request = sysom_20231230_models.CreateVmcoreDiagnosisTaskRequest(
            task_type="dmesg", dmesg_url=dmesg_url
        )
        response = await helper.create_task(request)
        return CreateTaskMCPResponse(**response.model_dump())
    except Exception as e:
        logger.error(f"create_dmesg_diagnosis_task failed: {e}")
        return CreateTaskMCPResponse(
            code="Error", message=f"调用失败：{str(e)}", data=None
        )


@mcp.tool(tags={"sysom_crash_agent"})
async def query_diagnosis_task(
    task_id: str = Field(..., description="诊断任务ID"),
) -> GetTaskMCPResponse:
    """
    查询诊断任务的结果。根据任务ID获取诊断任务的执行状态和结果。由于诊断任务可能耗时较长，因此该接口返回的是任务在运行中时后请稍后再查询。

    功能描述：
        根据任务ID查询诊断任务的执行状态和结果

    参数说明：
        task_id (str): 诊断任务ID（必填）

    返回值:
        GetTaskMCPResponse: 诊断任务的完整结果
            - code: 状态码 ("Success"表示成功，"Error"表示失败)
            - message: 错误信息 (当code为"Error"时提供具体错误信息)
            - data: 任务详情对象，包含以下字段:
                - taskId: 任务ID
                - taskType: 任务类型 (vmcore 或 dmesg)
                - taskStatus: 任务状态 (created, queued, running, success, error)
                - createdAt: 任务创建时间
                - errorMsg: 错误信息（任务失败时）
                - diagnoseResult: 诊断结果详情（任务完成时）
                - urls: 诊断任务下发的文件下载链接

        任务进行中示例:
            {
                "code": "Success",
                "data": {
                    "taskId": "99fc9c12-7169-4283-9ad1-94193c3486c1",
                    "taskType": "vmcore",
                    "taskStatus": "running",
                    "createdAt": "2023-10-01T12:00:00Z",
                    "errorMsg": null,
                    "diagnoseResult": null,
                    "urls": {
                        "vmcoreUrl": "http://oss.example.com/vmcore-file",
                        "debuginfoUrl": "",
                        "debuginfoCommonUrl": "",
                        "dmesgUrl": ""
                    }
                }
            }

        任务完成示例:
            {
                "code": "Success",
                "data": {
                    "taskId": "99fc9c12-7169-4283-9ad1-94193c3486c1",
                    "taskType": "vmcore",
                    "taskStatus": "success",
                    "createdAt": "2023-10-01T12:00:00Z",
                    "errorMsg": null,
                    "diagnoseResult": "详细诊断结果...",
                    "urls": {
                        "vmcoreUrl": "http://oss.example.com/vmcore-file",
                        "debuginfoUrl": "",
                        "debuginfoCommonUrl": "",
                        "dmesgUrl": ""
                    }
                }
            }

        任务失败示例:
            {
                "code": "Success",
                "data": {
                    "taskId": "99fc9c12-7169-4283-9ad1-94193c3486c1",
                    "taskType": "dmesg",
                    "taskStatus": "error",
                    "createdAt": "2023-10-01T12:00:00Z",
                    "errorMsg": "具体的错误信息",
                    "diagnoseResult": null,
                    "urls": {
                        "vmcoreUrl": "",
                        "debuginfoUrl": "",
                        "debuginfoCommonUrl": "",
                        "dmesgUrl": "http://oss.example.com/dmesg-file"
                    }
                }
            }

        查询失败示例:
            {"code": "Error", "message": "查询诊断任务失败: 具体错误信息", "data": null}
    """
    try:
        client = ClientFactory.create_client()
        helper = CrashAgentMCPHelper(client)
        request = sysom_20231230_models.GetVmcoreDiagnosisTaskRequest(task_id=task_id)
        response = await helper.get_task(request)
        return GetTaskMCPResponse(**response.model_dump())

    except Exception as e:
        logger.error(f"query_diagnosis_task failed: {e}")
        return GetTaskMCPResponse(
            code="Error", message=f"调用失败：{str(e)}", data=None
        )


@mcp.tool(tags={"sysom_crash_agent"})
async def list_history_tasks(
    days: int = Field(
        ..., description="查询几天前的历史任务记录，不得超过30天", ge=1, le=30
    ),
) -> ListHistoryTasksMCPResponse:
    """
    查询历史创建的宕机诊断任务记录，返回指定天数内的任务列表，包括vmcore文件诊断和dmesg日志诊断两类。

    功能描述：
        查询指定天数内的历史诊断任务记录列表

    使用场景：
        1. 查看最近的诊断任务执行情况
        2. 追踪历史任务执行状态和错误信息
        3. 分析任务执行趋势和成功率

    参数说明：
        days (int): 查询几天前的历史任务记录，取值范围1-30天（必填）

    返回值说明：
        ListHistoryTasksMCPResponse: 包含历史任务列表的响应对象
            - code: 状态码 ("Success"表示成功，"Error"表示失败)
            - message: 错误信息 (当code为"Error"时提供具体错误信息)
            - data: 任务列表数组，每个元素包含：
              - taskId: 任务ID
              - taskType: 任务类型
              - taskStatus: 任务状态
              - createdAt: 任务创建时间（ISO 8601格式）
              - errorMsg: 错误信息

        成功示例:
        {
            "code": "Success",
            "data": [
                {
                "taskId": "9d24a3cd-9773-4044-9934-04d9d32c43a7",
                "taskType": "vmcore",
                "taskStatus": "success",
                "createdAt": "2025-12-02T20:03:25",
                "errorMsg": ""
                },
                {
                "taskId": "6e60fabf-c518-431a-bc3d-d818fb78e41e",
                "taskType": "vmcore",
                "taskStatus": "error",
                "createdAt": "2025-12-02T19:38:43",
                "errorMsg": "Task failed in FC"
                }
            ]
        }

        失败示例:
        {"code": "Error", "message": "查询历史任务失败: 具体错误信息", "data": null}
    """
    try:
        client = ClientFactory.create_client()
        helper = CrashAgentMCPHelper(client)
        request = sysom_20231230_models.ListVmcoreDiagnosisTaskRequest(days=days)
        response = await helper.list_task(request)
        return ListHistoryTasksMCPResponse(**response.model_dump())
    except Exception as e:
        logger.error(f"list_history_tasks failed: {e}")
        import traceback

        traceback.print_exc()
        return ListHistoryTasksMCPResponse(
            code="Error", message=f"调用失败：{str(e)}", data=None
        )


@click.command()
@click.option(
    "--stdio", "run_mode", flag_value="stdio", default=True, help="Run in stdio mode"
)
@click.option("--sse", "run_mode", flag_value="sse", help="Run in SSE mode")
@click.option(
    "--streamable-http",
    "run_mode",
    flag_value="streamable-http",
    help="Run in streamable-http mode",
)
@click.option(
    "--host",
    default="127.0.0.1",
    help="Host to bind to (for SSE mode, default: 127.0.0.1)",
)
@click.option(
    "--port",
    default=7130,
    type=int,
    help="Port to bind to (for SSE mode, default: 7130)",
)
@click.option(
    "--path",
    default="/mcp/crash_agent",
    help="Path for SSE endpoint (default: /mcp/crash_agent)",
)
def main(
    run_mode: Literal["stdio", "sse", "streamable-http"],
    host: str,
    port: int,
    path: str,
) -> None:
    """Run MCP server in stdio or SSE mode"""
    if run_mode in ["sse", "streamable-http"]:
        # SSE 模式：直接使用 mcp.run()，它应该支持这些参数
        logger.info(f"Starting MCP server in SSE mode on {host}:{port}{path}")
        # FastMCP 的 run() 方法应该支持 transport、host、port、path 参数
        mcp.run(transport=run_mode, host=host, port=port, path=path)
    else:
        # stdio 模式
        logger.info("Starting MCP server in stdio mode")
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
