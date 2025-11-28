import asyncio
import json
from pathlib import Path
from typing import Annotated, Any, Dict

import aiohttp
from cmg_base import LoadBalancingStrategy, dispatch_service_discovery
from fastmcp import Context, FastMCP
from pydantic import BaseModel, ConfigDict, Field
# from sysom_utils import ConfigParser, SysomFramework
from lib.logger_config import setup_logger

logger = setup_logger(__name__)


# 新增诊断任务请求模型
class DiagnoseInput(BaseModel):
    instance: str = Field(..., description="实例名称")
    service_name: str = Field(..., description="诊断服务名称")
    region: str = Field(default="cn-hangzhou", 
                        description="实例地域")
    
from typing import Any, Dict

from pydantic import BaseModel


class DiagnoseRequestParams(BaseModel):
    instance: str
    region: str
    _hide: str = "1"

    def custom_dump(self) -> Dict[str, Any]:
        """自定义序列化方法，输出所有字段"""
        return {
            "instance": self.instance,
            "region": self.region,
            "_hide": self._hide,
        }


class DiagnoseRequest(BaseModel):
    channel: str = "ecs"
    params: DiagnoseRequestParams
    service_name: str

    def custom_dump(self) -> Dict[str, Any]:
        """支持嵌套模型的自定义序列化方法"""
        return {
            "channel": self.channel,
            "params": self.params.custom_dump(), 
            "service_name": self.service_name,
        }


def create_task_request(input: DiagnoseInput) -> DiagnoseRequest:
    return DiagnoseRequest(
        channel="ecs",
        params=DiagnoseRequestParams(
            instance=input.instance,
            region=input.region,
            _hide="1",
        ),
        service_name=input.service_name,
    )


class DiagnoseResult(BaseModel):
    result: Dict[str, Any] = Field(..., description="诊断结果")

mcp = FastMCP("SysomDiagnoseMCP")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
# YAML_GLOBAL_CONFIG_PATH = "/etc/sysom/config.yml"
# YAML_SERVICE_CONFIG_PATH = f"{BASE_DIR}/config.yml"

# YAML_CONFIG = ConfigParser(YAML_GLOBAL_CONFIG_PATH, YAML_SERVICE_CONFIG_PATH)

# discovery = dispatch_service_discovery(YAML_CONFIG.get_cmg_url())

# serviceInstance = discovery.get_instance("sysom_openapi", LoadBalancingStrategy.RANDOM)


class _DiagnoseClient:
    def __init__(self, uid):
        self.url = f"http://{serviceInstance.host}:{serviceInstance.port}/api/v1/openapi/diagnosis/invokeDiagnosis"
        
        self.timeout = 130  # 超时时间
        self.poll_interval = 1  # 轮询间隔
        self.headers = {
            "x-acs-caller-type": "customer",
            "x-acs-caller-uid": uid,
        }

    async def _create_task(self, task_req: Dict[str, Any]) -> tuple[bool, Any]:
        """创建诊断任务"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self.url, json=task_req, headers=self.headers, timeout=aiohttp.ClientTimeout(total=self.timeout)) as response:
                    if response.status == 200:
                        resp = await response.json()
                        return True, resp
                    else:
                        return False, f"诊断失败：发起诊断失败，状态码: {response.status}"
            except Exception as e:
                logger.error(f"请求异常: {e}")
                return False, f"诊断失败：发起诊断失败"
            

    async def _get_task_result(self, task_id: str) -> tuple[bool, Any]:
        """轮询获取任务结果"""
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < self.timeout:
            try:
                params = {
                    "task_id": task_id,
                }
                url = f"http://{serviceInstance.host}:{serviceInstance.port}/api/v1/openapi/diagnosis/getDiagnosisResults"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=self.headers, timeout=aiohttp.ClientTimeout(total=self.timeout), params=params) as resp:
                        resp.raise_for_status()
                        task_data = await resp.json()
                                                
                        status = task_data.get("data", {}).get("status")
                        if status == "Success":
                            return True, task_data["data"]["result"]
                        elif status == "Fail":
                            return False, f"诊断失败：获取诊断结果失败"
            except Exception as e:
                logger.error(f"查询任务状态失败: {e}")
                return False, f"诊断失败：获取诊断结果失败"
            
            await asyncio.sleep(self.poll_interval)
        
        return False, f"诊断失败：诊断超时"


@mcp.tool(
    tags={"ocd"}
)
async def diagnose(
    instance: str = Field(..., description="实例名称"),
    service_name: str = Field(..., description="诊断服务名称"),
    uid: str = Field(..., description="用户ID"),
    region: str = Field(default="cn-hangzhou", description="实例地域"),
    ctx: Context | None = None,
) -> Dict[str, Any]:
    """执行诊断任务并返回结果"""
    client = _DiagnoseClient(uid)
    diagnoseRequest = create_task_request(DiagnoseInput(instance=instance, service_name=service_name, region=region))
    try:
        # 创建任务
        ok, task_data = await client._create_task(diagnoseRequest.custom_dump())
        if not ok:
            return {"error": task_data}
        
        task_id = task_data["data"]["task_id"]
        logger.info(f"任务已创建，ID: {task_id}")
        
        # 获取结果
        ok, result = await client._get_task_result(task_id)
        if not ok:
            return {"error": result}
        
        return {"result": result}
        
    except Exception as e:
        logger.error(f"诊断执行失败: {e}")
        import traceback
        error_trace = traceback.format_exc()
        logger.error(error_trace)  # 打印堆栈信息
        # raise Exception({"error": str(e), "traceback": error_trace, "task_data": task_data})
        return {"error": f"诊断失败：{e}"}

# @mcp.tool(
#     tags={"ocd"}
# )
# async def listDiagnoseResults(
#     instance: str = Field(..., description="实例名称"),
#     service_name: str = Field(..., description="诊断服务名称"),
#     uid: str = Field(..., description="用户ID"),
#     region: str = Field(default="cn-hangzhou", description="实例地域"),
#     start_time: str = Field(None, description="开始时间"),
#     end_time: str = Field(None, description="结束时间"),
#     ctx: Context | None = None,
# ) -> Dict[str, Any]:
#     """执行诊断任务并返回结果"""
#     client = _DiagnoseClient(uid)
#     DiagnoseRequest = create_task_request(DiagnoseInput(instance=instance, service_name=service_name, region=region))
#     try:
#         # 创建任务
#         task_data = await client._create_task(DiagnoseRequest.dict())
#         task_id = task_data["data"]["task_id"]
#         print(f"任务已创建，ID: {task_id}")
        
#         # 获取结果
#         result = await client._get_task_result(task_id)
#         return {"result": result}
        
#     except Exception as e:
#         print(f"诊断执行失败: {e}")
#         return {"error": str(e)}

def create_mcp_server():
    return mcp

if __name__ == "__main__":
    create_mcp_server().run(transport="stdio")
