"""API路由注册表

统一管理OpenAPI的URL到模型和方法的映射关系
支持接口级别的调用方式限制，Framework和SDK两种调用方式分离设计
"""
import threading
from typing import Dict, Type, Callable, Optional, Any
from enum import Enum
from Tea.model import TeaModel


class SupportMode(Enum):
    """接口支持模式"""
    FRAMEWORK_ONLY = "framework_only"  # 仅支持Framework调用
    SDK_ONLY = "sdk_only"  # 仅支持SDK调用
    BOTH = "both"  # 两种方式都支持


class FrameworkRoute:
    """Framework调用方式的路由信息"""
    def __init__(
        self,
        url_pattern: str,
        method: str,
        service_name: str
    ):
        """
        初始化Framework路由
        
        Args:
            url_pattern: URL模式
            method: HTTP方法
            service_name: 服务名称（必需）
        """
        self.url_pattern = url_pattern
        self.method = method.upper()
        self.service_name = service_name


class SDKRoute:
    """SDK调用方式的路由信息"""
    def __init__(
        self,
        request_model: Type[TeaModel],
        response_model: Type[TeaModel],
        client_method: Callable
    ):
        """
        初始化SDK路由
        
        Args:
            request_model: 请求模型类
            response_model: 响应模型类
            client_method: 客户端方法（lambda函数）
        """
        self.request_model = request_model
        self.response_model = response_model
        self.client_method = client_method


class APIRoute:
    """API路由信息（包含Framework和SDK两种调用方式的信息）"""
    def __init__(
        self,
        api_name: str,
        support_mode: SupportMode = SupportMode.SDK_ONLY,
        framework_route: Optional[FrameworkRoute] = None,
        sdk_route: Optional[SDKRoute] = None
    ):
        """
        初始化API路由
        
        Args:
            api_name: 接口名称（唯一标识）
            support_mode: 支持模式
            framework_route: Framework路由信息（Framework调用时需要）
            sdk_route: SDK路由信息（SDK调用时需要）
        """
        self.api_name = api_name
        self.support_mode = support_mode
        self.framework_route = framework_route
        self.sdk_route = sdk_route


class APIRegistry:
    """API路由注册表（单例模式）"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._routes: Dict[str, APIRoute] = {}  # key: api_name
        return cls._instance
    
    def register_framework(
        self,
        api_name: str,
        url_pattern: str,
        method: str,
        service_name: str
    ):
        """
        注册Framework调用方式的路由
        
        Args:
            api_name: 接口名称（唯一标识）
            url_pattern: URL模式
            method: HTTP方法
            service_name: 服务名称（必需）
        """
        framework_route = FrameworkRoute(url_pattern, method, service_name)
        
        # 如果路由已存在，更新framework_route
        if api_name in self._routes:
            route = self._routes[api_name]
            route.framework_route = framework_route
            # 如果之前是SDK_ONLY，现在添加了Framework支持，更新为BOTH
            if route.support_mode == SupportMode.SDK_ONLY:
                route.support_mode = SupportMode.BOTH
        else:
            # 创建新路由
            route = APIRoute(
                api_name=api_name,
                support_mode=SupportMode.FRAMEWORK_ONLY,
                framework_route=framework_route,
                sdk_route=None
            )
            self._routes[api_name] = route
    
    def register_sdk(
        self,
        api_name: str,
        request_model: Type[TeaModel],
        response_model: Type[TeaModel],
        client_method: Callable
    ):
        """
        注册SDK调用方式的路由
        
        Args:
            api_name: 接口名称（唯一标识）
            request_model: 请求模型类
            response_model: 响应模型类
            client_method: 客户端方法（lambda函数）
        """
        sdk_route = SDKRoute(request_model, response_model, client_method)
        
        # 如果路由已存在，更新sdk_route
        if api_name in self._routes:
            route = self._routes[api_name]
            route.sdk_route = sdk_route
            # 如果之前是FRAMEWORK_ONLY，现在添加了SDK支持，更新为BOTH
            if route.support_mode == SupportMode.FRAMEWORK_ONLY:
                route.support_mode = SupportMode.BOTH
        else:
            # 创建新路由
            route = APIRoute(
                api_name=api_name,
                support_mode=SupportMode.SDK_ONLY,
                framework_route=None,
                sdk_route=sdk_route
            )
            self._routes[api_name] = route
    
    def get_route(self, api_name: str) -> Optional[APIRoute]:
        """根据接口名称获取路由信息"""
        return self._routes.get(api_name)
    
    def get_framework_route(self, api_name: str) -> Optional[FrameworkRoute]:
        """
        获取Framework路由信息
        
        Args:
            api_name: 接口名称
        """
        route = self.get_route(api_name)
        return route.framework_route if route and route.framework_route else None
    
    def get_sdk_route(self, api_name: str) -> Optional[SDKRoute]:
        """
        获取SDK路由信息
        
        Args:
            api_name: 接口名称
        """
        route = self.get_route(api_name)
        return route.sdk_route if route and route.sdk_route else None
    
    def get_request_model(self, api_name: str) -> Optional[Type[TeaModel]]:
        """获取请求模型（SDK调用时使用）"""
        sdk_route = self.get_sdk_route(api_name)
        return sdk_route.request_model if sdk_route else None
    
    def get_response_model(self, api_name: str) -> Optional[Type[TeaModel]]:
        """获取响应模型（SDK调用时使用）"""
        sdk_route = self.get_sdk_route(api_name)
        return sdk_route.response_model if sdk_route else None

