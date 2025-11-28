# import json
# from typing import Dict, Any, List
# from sysom_utils import ConfigParser
# from fastmcp import FastMCP, Context
# from pydantic import Field
# from cmg_base import dispatch_service_discovery
# import asyncio
# import aiohttp
# from clogger import logger
# from pathlib import Path
# import nest_asyncio
# from cmg_base import LoadBalancingStrategy
# import sys


# BASE_DIR = Path(__file__).resolve().parent.parent.parent
# sys.path.append(f"{BASE_DIR}")

# from app.prompt.metrics_config import SLS_METRICS

# def create_mcp_server():
#     mcp = FastMCP("SysomMetricsMCP")
    
#     nest_asyncio.apply()
#     BASE_DIR = Path(__file__).resolve().parent.parent.parent
#     YAML_GLOBAL_CONFIG_PATH = f"{BASE_DIR.parent.parent}/conf/config.yml"
#     YAML_SERVICE_CONFIG_PATH = f"{BASE_DIR}/config.yml"

#     YAML_CONFIG = ConfigParser(YAML_GLOBAL_CONFIG_PATH, YAML_SERVICE_CONFIG_PATH)
    
#     discovery = dispatch_service_discovery(YAML_CONFIG.get_cmg_url())
    
#     serviceInstance = discovery.get_instance("sysom_monitor_server", LoadBalancingStrategy.RANDOM)

#     class _MetricsClient:
#         async def _query(self, instance: str, metric_name: str, start_time: int, end_time: int) -> dict:                    
#             url = f"http://{serviceInstance.host}:{serviceInstance.port}/api/v1/monitor/metric/describeMetricList"
                        
#             params = {
#                 "instance": instance,
#                 "metricName": metric_name,
#                 "startTime": 1753431885,
#                 "endTime": 1753431985
#             }
            
#             headers = {
#                 "x-acs-caller-type": "customer",  # 修复格式
#                 "x-acs-caller-uid": "1418925853835361"  # 修复格式
#             }
            
#             async with aiohttp.ClientSession() as session:
#                 try:
#                     async with session.get(url, params=params, headers=headers) as response:
#                         if response.status == 200:
#                             return await response.json()
#                         else:
#                             raise Exception(f"请求失败，状态码: {response.status}")
#                 except Exception as e:
#                     logger.error(f"请求异常: {e}")
#                     return None
            

#         async def _parse_prompt(self) -> List[Dict[str, Any]]:
#             return SLS_METRICS

#     @mcp.tool()
#     def query(
#         instance: str = Field(..., description="目标主机实例ID"),
#         metric_name: str = Field(..., description="监控指标名称"),
#         start_time: int = Field(..., description="开始时间戳"),
#         end_time: int = Field(..., description="结束时间戳"),
#         ctx: Context | None = None,
#     ) -> str:
#         """查询某个特定监控指标"""
#         # 在同步函数中运行异步任务
#         def run_async_query():
#             client = _MetricsClient()
#             # 直接返回异步任务结果
#             return asyncio.run(client._query(instance, metric_name, start_time, end_time))
        
#         try:
#             result = run_async_query()
#             # 处理可能的None值
#             return result if result is not None else "查询结果为空"
#         except Exception as e:
#             ctx.error(f"查询失败: {e}")
#             return f"查询失败: {e}"

#     @mcp.tool()
#     def query_all(
#         instance: str = Field(..., description="目标主机实例ID"),
#         start_time: int = Field(..., description="开始时间戳"),
#         end_time: int = Field(..., description="结束时间戳"),
#         ctx: Context | None = None,
#     ) -> Dict[str, Any]:
#         """并发查询所有监控指标"""
#         # 在同步函数中运行异步任务
#         def run_async_query_all():
#             client = _MetricsClient()
            
#             async def fetch_all_metrics():
#                 metrics_prompt = await client._parse_prompt()
                
#                 tasks = [
#                     client._query(
#                         instance=instance,
#                         metric_name=metric["metricName"],
#                         start_time=start_time,
#                         end_time=end_time
#                     )
#                     for metric in metrics_prompt
#                 ]
                
#                 results = await asyncio.gather(*tasks, return_exceptions=True)
                
#                 metrics_map = summarize_metrics_simple(results, metrics_prompt)
                
#                 return metrics_map
            
#             return asyncio.run(fetch_all_metrics())
        
#         try:
#             return run_async_query_all()
#         except Exception as e:
#             ctx.error(f"批量查询失败: {e}")
#             return {"error": f"批量查询失败: {e}"}

#     return mcp

# def summarize_metrics_simple(results, metrics_prompt):
#     """
#     纯数据摘要函数 - 仅保留最大值、最小值和平均值
#     不包含任何异常分析或业务逻辑判断
#     """
#     metrics_summary = {}
    
#     for i, result in enumerate(results):
#         metric_name = metrics_prompt[i]["metricName"]
        
#         # 处理查询失败的情况
#         if isinstance(result, Exception):
#             metrics_summary[metric_name] = f"查询失败: {str(result)}"
#             continue
            
#         # 确保result是字典格式
#         if not isinstance(result, dict) or "data" not in result:
#             metrics_summary[metric_name] = "数据格式错误"
#             continue
            
#         data = result["data"]
#         if not data:
#             metrics_summary[metric_name] = "无数据"
#             continue
            
#         # 为当前指标创建摘要
#         metric_summary = {}
        
#         for item in data:
#             try:
#                 # 解析labels获取legend
#                 labels = json.loads(item["labels"])
#                 legend = labels.get("legend", "unknown")
                
#                 # 提取values并计算统计值
#                 values = [v[1] for v in item["values"] if len(v) == 2 and isinstance(v[1], (int, float))]
#                 if not values:
#                     continue
                
#                 avg_val = sum(values) / len(values)
#                 max_val = max(values)
#                 min_val = min(values)
                
#                 # 仅保留基本统计值，不做任何分析
#                 metric_summary[legend] = {
#                     "avg": round(avg_val, 2),
#                     "max": round(max_val, 2),
#                     "min": round(min_val, 2),
#                     "count": len(values)
#                 }
                
#             except (json.JSONDecodeError, TypeError, KeyError, IndexError):
#                 # 跳过无法解析的项目，不进行错误处理
#                 continue
        
#         # 如果有摘要数据，添加到结果中
#         if metric_summary:
#             metrics_summary[metric_name] = metric_summary
#         else:
#             metrics_summary[metric_name] = "无有效数据点"
    
#     return metrics_summary


# if __name__ == "__main__":
#     create_mcp_server().run(transport="stdio")
