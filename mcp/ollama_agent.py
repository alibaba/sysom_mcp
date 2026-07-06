#!/usr/bin/env python3
"""基于 Ollama 的 Agent，用于调用 SysOM MCP 工具

这个 agent 使用 Ollama 作为本地 LLM，通过 MCP 协议调用 sysom_mcp 工具。
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
import subprocess

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError as e:
    print(f"错误: 无法导入 mcp 包: {e}", file=sys.stderr)
    print("请运行: uv sync", file=sys.stderr)
    sys.exit(1)

try:
    import requests
except ImportError:
    print("错误: 需要安装 requests 包。请运行: uv sync", file=sys.stderr)
    sys.exit(1)


class OllamaAgent:
    """基于 Ollama 的 Agent，可以调用 MCP 工具"""
    
    def __init__(
        self,
        ollama_base_url: str = "http://localhost:11434",
        ollama_model: str = "llama3.2",
        mcp_server_path: Optional[str] = None
    ):
        """
        初始化 Agent
        
        Args:
            ollama_base_url: Ollama 服务的基础 URL
            ollama_model: 要使用的 Ollama 模型名称
            mcp_server_path: MCP 服务器脚本路径，如果为 None 则使用默认路径
        """
        self.ollama_base_url = ollama_base_url.rstrip('/')
        self.ollama_model = ollama_model
        self.mcp_server_path = mcp_server_path or str(PROJECT_ROOT / "sysom_main_mcp.py")
        self.session: Optional[ClientSession] = None
        self.available_tools: List[Dict[str, Any]] = []
        
    async def initialize(self):
        """初始化 MCP 客户端连接"""
        print("正在连接到 MCP 服务器...", file=sys.stderr)
        
        # 设置服务器参数
        server_params = StdioServerParameters(
            command="python3",
            args=[self.mcp_server_path, "--stdio"],
            env={
                "type": "ram_role_arn",
                "ACCESS_KEY_ID": "",
                "ACCESS_KEY_SECRET": "",
                "ROLE_ARN": "",
                "ALIBABA_CLOUD_SECURITY_TOKEN": "",
                "DASHSCOPE_API_KEY": ""
            },
        )
        
        # 启动客户端会话
        self.stdio_transport = stdio_client(server_params)
        self.read, self.write = await self.stdio_transport.__aenter__()
        self.session = ClientSession(self.read, self.write)
        await self.session.__aenter__()
        await self.session.initialize()
        
        # 获取可用工具列表
        tools_result = await self.session.list_tools()
        self.available_tools = tools_result.tools
        
        print(f"成功连接到 MCP 服务器，发现 {len(self.available_tools)} 个工具", file=sys.stderr)
        for tool in self.available_tools:
            print(f"  - {tool.name}: {tool.description[:60]}...", file=sys.stderr)
    
    async def close(self):
        """关闭 MCP 客户端连接"""
        if self.session:
            await self.session.__aexit__(None, None, None)
            await self.stdio_transport.__aexit__(None, None, None)
    
    def _format_tools_for_ollama(self) -> str:
        """将工具列表格式化为 Ollama 可以理解的格式（简化版）"""
        tools_list = []
        for tool in self.available_tools:
            tool_info = f"{tool.name}: {tool.description[:80]}"
            if tool.inputSchema and "properties" in tool.inputSchema:
                required = tool.inputSchema.get("required", [])
                if required:
                    tool_info += f" (必需: {', '.join(required)})"
            tools_list.append(tool_info)
        return "\n".join(tools_list)
    
    def _call_ollama(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """调用 Ollama API（非流式，最简单可靠）"""
        url = f"{self.ollama_base_url}/api/chat"
        
        payload = {
            "model": self.ollama_model,
            "messages": messages,
            "stream": False
        }
        
        try:
            print("正在调用 Ollama API...", file=sys.stderr)
            # 使用较长的超时时间，因为大模型响应可能需要较长时间
            response = requests.post(
                url, 
                json=payload, 
                timeout=600  # 10分钟超时
            )
            response.raise_for_status()
            result = response.json()
            print("✓ Ollama API 调用成功", file=sys.stderr)
            return result
        except requests.exceptions.Timeout as e:
            raise Exception(f"Ollama API 调用超时（超过10分钟）。请检查：\n"
                          f"1. Ollama 服务是否正常运行\n"
                          f"2. 模型是否已加载（qwen2.5:7b 可能需要较长时间）\n"
                          f"3. 尝试使用更小的模型（如 llama3.2）")
        except requests.exceptions.RequestException as e:
            raise Exception(f"调用 Ollama API 失败: {e}\n"
                          f"请检查 Ollama 服务是否正常运行")
    
    async def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """调用 MCP 工具"""
        try:
            result = await self.session.call_tool(tool_name, arguments)
            if result.isError:
                return f"工具调用失败: {result.content}"
            return result.content
        except Exception as e:
            return f"工具调用出错: {str(e)}"
    
    def _parse_tool_call(self, response_text: str) -> Optional[Dict[str, Any]]:
        """从 LLM 响应中解析工具调用
        
        期望格式：
        TOOL_CALL: tool_name
        ARGS: {"arg1": "value1", "arg2": "value2"}
        """
        lines = response_text.strip().split('\n')
        tool_name = None
        args_json = None
        
        for i, line in enumerate(lines):
            if line.startswith("TOOL_CALL:"):
                tool_name = line.split(":", 1)[1].strip()
            elif line.startswith("ARGS:"):
                args_json = line.split(":", 1)[1].strip()
        
        if tool_name and args_json:
            try:
                args = json.loads(args_json)
                return {"tool_name": tool_name, "arguments": args}
            except json.JSONDecodeError:
                return None
        return None
    
    async def chat(self, user_query: str, max_iterations: int = 5) -> str:
        """与 Agent 对话，Agent 可以调用工具
        
        Args:
            user_query: 用户查询
            max_iterations: 最大迭代次数（工具调用循环）
        
        Returns:
            Agent 的最终回复
        """
        if not self.session:
            await self.initialize()
        
        # 构建简化的系统提示词
        system_prompt = f"""你是系统运维助手。必须使用工具解决问题。

可用工具：
{self._format_tools_for_ollama()}

规则：系统诊断/查询 → 调用工具；问候/闲聊 → 直接回答

格式：
调用工具：TOOL_CALL: 工具名
ARGS: {{"参数":"值"}}
直接回答：直接文本回复"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ]
        
        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            print(f"\n[迭代 {iteration}/{max_iterations}]", file=sys.stderr)
            
            # 调用 Ollama
            print("正在调用 Ollama...", file=sys.stderr)
            response = self._call_ollama(messages)
            assistant_message = response.get("message", {}).get("content", "")
            print(f"Ollama 响应: {assistant_message[:200]}...", file=sys.stderr)
            
            # 检查是否需要调用工具
            tool_call = self._parse_tool_call(assistant_message)
            
            if tool_call:
                tool_name = tool_call["tool_name"]
                tool_args = tool_call["arguments"]
                
                print(f"\n调用工具: {tool_name}", file=sys.stderr)
                print(f"参数: {json.dumps(tool_args, ensure_ascii=False, indent=2)}", file=sys.stderr)
                
                # 调用工具
                tool_result = await self._call_tool(tool_name, tool_args)
                print(f"工具返回结果: {tool_result[:200]}...", file=sys.stderr)
                
                # 将工具调用和结果添加到消息历史
                messages.append({
                    "role": "assistant",
                    "content": assistant_message
                })
                messages.append({
                    "role": "user",
                    "content": f"工具 {tool_name} 的返回结果：\n{tool_result}\n\n请根据这个结果继续回答用户的问题。如果需要调用其他工具，请继续调用。"
                })
            else:
                # 检查用户查询是否应该使用工具
                should_use_tool = any(keyword in user_query.lower() for keyword in [
                    "检查", "诊断", "分析", "查看", "查询", "列出", "内存", "网络", 
                    "io", "调度", "实例", "pod", "集群", "崩溃", "oom", "jitter"
                ])
                
                if should_use_tool:
                    # 如果应该使用工具但没有调用，引导使用工具
                    messages.append({
                        "role": "assistant",
                        "content": assistant_message
                    })
                    messages.append({
                        "role": "user",
                        "content": f"你的问题需要使用工具来解决。请分析问题并调用合适的工具。\n"
                                 f"用户问题: {user_query}\n"
                                 f"请使用以下格式调用工具：\nTOOL_CALL: 工具名称\nARGS: {{参数JSON}}"
                    })
                else:
                    # 不需要工具的情况（如问候语），直接返回模型的回复
                    return assistant_message
        
        # 达到最大迭代次数
        return assistant_message


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="基于 Ollama 的 SysOM MCP Agent")
    parser.add_argument(
        "--ollama-url",
        default="http://localhost:11434",
        help="Ollama 服务 URL (默认: http://localhost:11434)"
    )
    parser.add_argument(
        "--model",
        default="llama3.2",
        help="Ollama 模型名称 (默认: llama3.2)"
    )
    parser.add_argument(
        "--mcp-server",
        default=None,
        help="MCP 服务器脚本路径 (默认: sysom_main_mcp.py)"
    )
    parser.add_argument(
        "--query",
        help="要执行的查询（如果不提供，将进入交互模式）"
    )
    
    args = parser.parse_args()
    
    # 检查 Ollama 是否可用
    try:
        response = requests.get(f"{args.ollama_url}/api/tags", timeout=5)
        response.raise_for_status()
        print(f"✓ Ollama 服务可用 ({args.ollama_url})", file=sys.stderr)
    except Exception as e:
        print(f"✗ 无法连接到 Ollama 服务 ({args.ollama_url}): {e}", file=sys.stderr)
        print("请确保 Ollama 已安装并运行。安装方法：https://ollama.ai", file=sys.stderr)
        sys.exit(1)
    
    # 创建 Agent
    agent = OllamaAgent(
        ollama_base_url=args.ollama_url,
        ollama_model=args.model,
        mcp_server_path=args.mcp_server
    )
    
    try:
        await agent.initialize()
        
        if args.query:
            # 单次查询模式
            print(f"\n用户查询: {args.query}\n", file=sys.stderr)
            result = await agent.chat(args.query)
            print("\n" + "="*60)
            print("Agent 回复:")
            print("="*60)
            print(result)
        else:
            # 交互模式
            print("\n" + "="*60)
            print("SysOM MCP Agent (基于 Ollama)")
            print("="*60)
            print("输入 'quit' 或 'exit' 退出\n")
            
            while True:
                try:
                    user_input = input("你: ").strip()
                    if not user_input:
                        continue
                    if user_input.lower() in ['quit', 'exit', 'q']:
                        break
                    
                    result = await agent.chat(user_input)
                    print(f"\nAgent: {result}\n")
                except KeyboardInterrupt:
                    print("\n\n退出...")
                    break
                except Exception as e:
                    print(f"\n错误: {e}\n", file=sys.stderr)
    
    finally:
        await agent.close()


if __name__ == "__main__":
    asyncio.run(main())

