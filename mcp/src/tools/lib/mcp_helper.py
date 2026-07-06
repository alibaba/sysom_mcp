"""MCP Helper基类

MCPHelper不是抽象类，而是一个普通基类，提供通用的辅助方法。
每一类MCP工具可以实现自己的MCPHelper，根据具体需求添加不同的方法。
对于Diagnosis类型，所有诊断项共享相同的接口，可以用一个通用方法。
对于AM类型，每个tool对应不同的接口，需要为每个tool实现单独的方法。
"""
from typing import Optional, Any, Dict
from pydantic import BaseModel
from .openapi_client import OpenAPIClient
from Tea.model import TeaModel


class MCPRequest(BaseModel):
    """MCP请求参数基类
    
    每个MCP工具可以继承此类并添加自己的参数字段
    """
    pass


class MCPResponse(BaseModel):
    """MCP响应基类
    
    每个MCP工具可以继承此类并添加自己的响应字段
    """
    code: str
    message: str = ""
    data: Any = None


class MCPHelper:
    """MCP Helper基类
    
    MCPHelper不是抽象类，可以根据需要添加不同的方法。
    每个tool对应一个MCPRequest、一个MCPResponse、一个MCPHelper方法。
    """
    
    def __init__(self, client: OpenAPIClient):
        """
        初始化MCP Helper
        
        Args:
            client: OpenAPI客户端实例
        """
        self.client = client
    
    def _convert_to_tea_request(
        self,
        mcp_request: MCPRequest,
        tea_request_class: type
    ) -> TeaModel:
        """
        将MCPRequest转换为TeaModel请求对象
        
        Args:
            mcp_request: MCP请求参数
            tea_request_class: TeaModel请求类
            
        Returns:
            TeaModel: TeaModel请求对象
        """
        # 将Pydantic模型转换为字典
        request_dict = mcp_request.model_dump(exclude_none=True, by_alias=True)
        
        # 创建TeaModel对象
        tea_request = tea_request_class()
        
        # 将字典中的值设置到TeaModel对象中
        # 注意：这里需要根据实际的TeaModel结构来处理字段映射
        for key, value in request_dict.items():
            # 处理字段名映射（如snake_case到camelCase）
            tea_key = self._convert_field_name(key)
            if hasattr(tea_request, tea_key):
                setattr(tea_request, tea_key, value)
        
        return tea_request
    
    def _convert_field_name(self, field_name: str) -> str:
        """
        转换字段名（如snake_case到camelCase）
        
        可以根据实际需要进行扩展
        
        Args:
            field_name: 原始字段名
            
        Returns:
            str: 转换后的字段名
        """
        # 简单的snake_case到camelCase转换
        parts = field_name.split('_')
        return parts[0] + ''.join(word.capitalize() for word in parts[1:])
    
    def _convert_tea_response_to_dict(self, tea_response: Any) -> Dict[str, Any]:
        """
        将TeaModel响应转换为字典
        
        Args:
            tea_response: TeaModel响应对象或字典
            
        Returns:
            Dict[str, Any]: 字典格式的响应
        """
        if isinstance(tea_response, TeaModel):
            return tea_response.to_map()
        elif isinstance(tea_response, dict):
            return tea_response
        else:
            return {"raw": str(tea_response)}

