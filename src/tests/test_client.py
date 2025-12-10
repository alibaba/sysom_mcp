import asyncio
from typing import Optional, Dict, List
from contextlib import AsyncExitStack
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

#from anthropic import Anthropic
from dotenv import load_dotenv
from openai import OpenAI
import json, os

# 获取项目根目录并加载 .env 文件
# 当前文件在 src/tests/，向上两级到项目根目录
project_root = Path(__file__).resolve().parent.parent.parent
env_path = project_root / '.env'
# 加载 .env 文件，override=True 表示覆盖已存在的环境变量
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
else:
    # 如果项目根目录没有，尝试加载当前目录的 .env
    load_dotenv(override=True)


class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        # 原来的单服务器支持（保留用于向后兼容）
        # self.session: Optional[ClientSession] = None
        
        # 新的多服务器支持
        self.sessions: List[ClientSession] = []
        self.tool_session_map: Dict[str, ClientSession] = {}  # 工具名到会话的映射
        self.exit_stack = AsyncExitStack()
        self.available_tools = []  # 所有可用工具列表
        #self.anthropic = Anthropic()
    # methods will go here

    # 原来的单服务器连接方法（已注释，保留用于向后兼容）
    # async def connect_to_server(self, server_script_path: str):
    #     """Connect to an MCP server
    #
    #     Args:
    #         server_script_path: Path to the server script (.py or .js)
    #     """
    #     is_python = server_script_path.endswith('.py')
    #     is_js = server_script_path.endswith('.js')
    #     if not (is_python or is_js):
    #         raise ValueError("Server script must be a .py or .js file")
    #
    #     command = "python" if is_python else "node"
    #     server_params = StdioServerParameters(
    #         command=command,
    #         args=[server_script_path],
    #         env=None
    #     )
    #
    #     stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
    #     self.stdio, self.write = stdio_transport
    #     self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
    #
    #     await self.session.initialize()
    #
    #     # List available tools
    #     response = await self.session.list_tools()
    #     tools = response.tools
    #     print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def connect_to_servers(self, server_script_paths: List[str]):
        """Connect to multiple MCP servers

        Args:
            server_script_paths: List of paths to server scripts (.py or .js)
        """
        print(f"\n正在连接 {len(server_script_paths)} 个 MCP 服务器...")
        
        for server_script_path in server_script_paths:
            # 转换为 Path 对象以便处理
            script_path = Path(server_script_path)
            if not script_path.is_absolute():
                # 如果是相对路径，相对于项目根目录
                script_path = project_root / script_path
            
            if not script_path.exists():
                raise FileNotFoundError(f"MCP 服务器脚本不存在: {script_path}")
            
            is_python = script_path.suffix == '.py'
            is_js = script_path.suffix == '.js'
            if not (is_python or is_js):
                raise ValueError(f"Server script must be a .py or .js file: {script_path}")

            # 对于 Python 脚本，使用 uv run 来运行（确保依赖正确加载）
            if is_python:
                command = "uv"
                args = ["run", "python", str(script_path), "--stdio"]
            else:
                command = "node"
                args = [str(script_path)]
            
            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=None,
                cwd=str(project_root)  # 设置工作目录为项目根目录
            )

            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            stdio, write = stdio_transport
            session = await self.exit_stack.enter_async_context(ClientSession(stdio, write))

            await session.initialize()

            # List available tools
            response = await session.list_tools()
            tools = response.tools
            
            print(f"\n已连接服务器 {server_script_path}，工具: {[tool.name for tool in tools]}")
            
            # 检查工具名重复
            for tool in tools:
                if tool.name in self.tool_session_map:
                    raise ValueError(f"工具名重复: {tool.name} (来自 {server_script_path})")
                
                # 建立工具名到会话的映射
                self.tool_session_map[tool.name] = session
                
                # 转换为 LLM 工具格式
                tool_param = {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema,
                        "required": tool.inputSchema.get("required", [])
                    }
                }
                self.available_tools.append(tool_param)
            
            self.sessions.append(session)
        
        print(f"\n总共连接了 {len(self.sessions)} 个服务器，共 {len(self.available_tools)} 个工具可用")

    # 原来的单服务器 process_query 方法（已注释，保留用于向后兼容）
    # async def process_query(self, query: str) -> str:
    #     """Process a query using Claude and available tools"""
    #     messages = [
    #         {
    #             "role": "user",
    #             "content": query
    #         }
    #     ]
    #
    #     response = await self.session.list_tools()
    #     print(response)
    #     available_tools = [{
    #         "type": "function",
    #         "function": {
    #             "name": tool.name,
    #             "description": tool.description,
    #             "parameters": tool.inputSchema,
    #             "required": tool.inputSchema["required"]
    #         }
    #     } for tool in response.tools]
    #     print(json.dumps(available_tools,ensure_ascii=False,indent=4))
    #     # Initial qwen API call
    #     # API key 从 .env 文件中读取
    #     api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    #     if not api_key:
    #         raise ValueError(
    #             "DASHSCOPE_API_KEY 未设置。请在项目根目录的 .env 文件中设置 DASHSCOPE_API_KEY 环境变量。"
    #         )
    #     client = OpenAI(
    #         api_key=api_key,
    #         base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    #     )
    #
    #     response = client.chat.completions.create(
    #         model="qwen-max",
    #         #max_tokens=1000,
    #         messages=messages,
    #         tools=available_tools
    #     )
    #
    #     # Process response and handle tool calls
    #     final_text = []
    #     print(response)
    #     assistant_message_content = []
    #     assistant_output = response.choices[0].message
    #     if  assistant_output.content is None:
    #         assistant_output.content = ""
    #     messages.append(assistant_output)
    #     if assistant_output.tool_calls == None:  # 如果模型判断无需调用工具，则将assistant的回复直接打印出来，无需进行模型的第二轮调用
    #         print(f"无需调用工具，我可以直接回复：{assistant_output.content}")
    #         return assistant_output.content
    #     #print(json.dumps(assistant_output,ensure_ascii=False,indent=4))
    #     while assistant_output.tool_calls != None:
    #
    #         tool_info = {"content": "","role": "tool", "tool_call_id": assistant_output.tool_calls[0].id}
    #         if assistant_output.tool_calls[0].function.name :
    #             # 提取位置参数信息
    #             argumens = json.loads(assistant_output.tool_calls[0].function.arguments)
    #             tool_name = assistant_output.tool_calls[0].function.name
    #             tool_args =  argumens
    #             print (tool_name,argumens)
    #             try:
    #                 result = await self.session.call_tool(tool_name, tool_args)
    #             except Exception as e:
    #                 print(f"Error processing query: {e}")
    #                 return "An error occurred while processing your request."
    #             print(result)
    #             tool_info["content"] = result.content
    #         # 如果判断需要调用查询时间工具，则运行查询时间工具
    #         #elif assistant_output.tool_calls[0].function.name == 'get_current_time':
    #         #    tool_info["content"] = get_current_time()
    #         tool_output = tool_info["content"]
    #         print(f"工具输出信息：{tool_output}\n")
    #         messages.append(tool_info)
    #         response = client.chat.completions.create(
    #             model="qwen-max",
    #             #max_tokens=1000,
    #             messages=messages,
    #             tools=available_tools
    #         )
    #         assistant_output = response.choices[0].message
    #         if assistant_output.content is None:
    #             assistant_output.content = ""
    #         messages.append(assistant_output)
    #
    #     return assistant_output.content

    async def process_query(self, query: str, parallel: bool = True) -> str:
        """Process a query using LLM and available tools from all connected servers
        
        Args:
            query: User query string
            parallel: Whether to allow parallel tool calls
        """
        messages = [
            {
                "role": "system",
                "content": "仅使用 role=tool 相关数据进行分析，不使用模型中的数据"
            },
            {
                "role": "user",
                "content": f"要求：每次返回选择工具时，在 choices.message.content 返回选择工具的原因。\n任务：{query}"
            }
        ]

        print(f"\n可用工具列表 ({len(self.available_tools)} 个):")
        print(json.dumps(self.available_tools, ensure_ascii=False, indent=2))
        # Initial qwen API call
        # API key 从 .env 文件中读取
        api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
        if not api_key:
            raise ValueError(
                "DASHSCOPE_API_KEY 未设置。请在项目根目录的 .env 文件中设置 DASHSCOPE_API_KEY 环境变量。"
            )
        client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )

        seq = 0
        max_iterations = 20  # 防止无限循环
        
        while seq < max_iterations:
            seq += 1
            response = client.chat.completions.create(
                model="qwen-max",
                messages=messages,
                tools=self.available_tools,
                parallel_tool_calls=parallel
            )

            assistant_output = response.choices[0].message
            if assistant_output.content is None:
                assistant_output.content = ""
            
            messages.append(assistant_output)
            
            # 如果模型判断无需调用工具，直接返回结果
            if (response.choices[0].finish_reason != "tool_calls" or 
                assistant_output.tool_calls is None or 
                len(assistant_output.tool_calls) == 0):
                print(f"\n获得最终结果：{assistant_output.content}")
                return assistant_output.content

            # 处理工具调用
            for tool_call in assistant_output.tool_calls:
                function = tool_call.function
                tool_name = function.name
                tool_args = json.loads(function.arguments)
                
                print(f"\n调用工具: {tool_name}, 参数: {tool_args}")
                
                # 根据工具名找到对应的会话
                session = self.tool_session_map.get(tool_name)
                if session is None:
                    error_msg = f"工具 {tool_name} 不存在或未找到对应的服务器会话"
                    print(f"错误: {error_msg}")
                    raise ValueError(error_msg)
                
                try:
                    result = await session.call_tool(tool_name, tool_args)
                    if result.isError:
                        error_msg = f"调用工具 {tool_name} 返回失败: {result.content}"
                        print(f"错误: {error_msg}")
                        raise ValueError(error_msg)
                    
                    print(f"工具 {tool_name} 返回结果: {result.content[:200]}...")
                    
                    # 将工具结果添加到消息历史
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result.content
                    })
                except Exception as e:
                    error_msg = f"调用工具 {tool_name} 时出错: {str(e)}"
                    print(f"错误: {error_msg}")
                    raise ValueError(error_msg)
                
                # 如果非并行模式，只处理第一个工具调用
                if not parallel:
                    break
        
        # 如果达到最大迭代次数，返回当前结果
        print(f"\n警告: 达到最大迭代次数 ({max_iterations})，返回当前结果")
        return assistant_output.content if assistant_output.content else "处理超时，请重试"

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'q' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == 'q':
                    break

                response = await self.process_query(query)
                print("\n" + response)

            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    # 方式一：使用统一 MCP 服务器（推荐）
    # 统一服务器聚合了所有工具，只需要连接一个服务器
    unified_server = str(project_root / "sysom_main_mcp.py")
    
    # 方式二：连接多个独立的 MCP 服务器
    # 如果需要分别连接各个服务，可以使用以下列表
    individual_servers = [
        str(project_root / "src" / "tools" / "am_mcp.py"),
        str(project_root / "src" / "tools" / "mem_diag_mcp.py"),
        str(project_root / "src" / "tools" / "io_diag_mcp.py"),
        str(project_root / "src" / "tools" / "net_diag_mcp.py"),
        str(project_root / "src" / "tools" / "sched_diag_mcp.py"),
        str(project_root / "src" / "tools" / "other_diag_mcp.py"),
    ]
    
    client = MCPClient()
    try:
        # 使用统一服务器（推荐方式）
        print("=" * 60)
        print("使用统一 MCP 服务器（推荐）")
        print("=" * 60)
        await client.connect_to_servers([unified_server])
        await client.chat_loop()
        
        # 如果需要使用多个独立服务器，取消下面的注释
        # print("=" * 60)
        # print("使用多个独立的 MCP 服务器")
        # print("=" * 60)
        # await client.connect_to_servers(individual_servers)
        # await client.chat_loop()
        
    finally:
        await client.cleanup()

if __name__ == "__main__":
    import sys
    asyncio.run(main())


