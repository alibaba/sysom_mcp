import asyncio
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

#from anthropic import Anthropic
from dotenv import load_dotenv
from openai import OpenAI
import json,os


load_dotenv()  # load environment variables from .env

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        #self.anthropic = Anthropic()
    # methods will go here

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server

        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]

        response = await self.session.list_tools()
        print(response)
        available_tools = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema,
                "required": tool.inputSchema["required"]
            }
        } for tool in response.tools]
        print(json.dumps(available_tools,ensure_ascii=False,indent=4))
        # Initial qwen API call
        client = OpenAI(
            # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
            api_key="",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )

        response = client.chat.completions.create(
            model="qwen-max",
            #max_tokens=1000,
            messages=messages,
            tools=available_tools
        )

        # Process response and handle tool calls
        final_text = []
        print(response)
        assistant_message_content = []
        assistant_output = response.choices[0].message
        if  assistant_output.content is None:
            assistant_output.content = ""
        messages.append(assistant_output)
        if assistant_output.tool_calls == None:  # 如果模型判断无需调用工具，则将assistant的回复直接打印出来，无需进行模型的第二轮调用
            print(f"无需调用工具，我可以直接回复：{assistant_output.content}")
            return assistant_output.content
        #print(json.dumps(assistant_output,ensure_ascii=False,indent=4))
        while assistant_output.tool_calls != None:

            tool_info = {"content": "","role": "tool", "tool_call_id": assistant_output.tool_calls[0].id}
            if assistant_output.tool_calls[0].function.name :
                # 提取位置参数信息
                argumens = json.loads(assistant_output.tool_calls[0].function.arguments)
                tool_name = assistant_output.tool_calls[0].function.name
                tool_args =  argumens
                print (tool_name,argumens)
                try:
                    result = await self.session.call_tool(tool_name, tool_args)
                except Exception as e:
                    print(f"Error processing query: {e}")
                    return "An error occurred while processing your request."
                print(result)
                tool_info["content"] = result.content
            # 如果判断需要调用查询时间工具，则运行查询时间工具
            #elif assistant_output.tool_calls[0].function.name == 'get_current_time':
            #    tool_info["content"] = get_current_time()
            tool_output = tool_info["content"]
            print(f"工具输出信息：{tool_output}\n")
            messages.append(tool_info)
            response = client.chat.completions.create(
                model="qwen-max",
                #max_tokens=1000,
                messages=messages,
                tools=available_tools
            )
            assistant_output = response.choices[0].message
            if assistant_output.content is None:
                assistant_output.content = ""
            messages.append(assistant_output)

            #for content in assistant_output:
            '''
            print (assistant_output.tool_calls)
            if content.type == 'text':
                final_text.append(content.text)
                assistant_message_content.append(content)
            elif content.type == 'tool_use':
                tool_name = content.name
                tool_args = content.input

                # Execute tool call
                result = await self.session.call_tool(tool_name, tool_args)
                print (result)
                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")
                print (final_text)

                assistant_message_content.append(content)
                messages.append({
                    "role": "assistant",
                    "content": assistant_message_content
                })
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": content.id,
                            "content": result.content
                        }
                    ]
                })

                # Get next response from qwen
                response = client.chat.completions.create(
                    model="qwen-max",
                    #max_tokens=1000,
                    messages=messages,
                    tools=available_tools
                )

                final_text.append(response.content[0].text)
            '''

        #return "\n".join(final_text)
        return assistant_output.content

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
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    import sys
    asyncio.run(main())


