"""OpenAPI客户端抽象层

提供统一的OpenAPI调用接口，支持两种实现方式：
1. SysomFrameworkClient: 通过SysomFramework微服务间发现调用（集群内部）
2. AlibabaCloudSDKClient: 通过阿里云OpenAPI SDK调用（公网）
"""
from abc import ABC, abstractmethod
from typing import Optional, Type, Tuple, Any, Dict, Union
from Tea.model import TeaModel
from .logger_config import setup_logger
from .api_registry import APIRegistry, SupportMode
from .service_config import SERVICE_CONFIG

logger = setup_logger(__name__)

class OpenAPIClient(ABC):
    """OpenAPI客户端抽象基类
    
    所有OpenAPI客户端实现都应该继承此类，提供统一的接口调用方式。
    
    注意：
    - SysomFrameworkClient: 参数和返回值必须是字典类型
    - AlibabaCloudSDKClient: 参数和返回值必须是TeaModel类型
    """
    
    def __init__(self, **kwargs):
        """初始化客户端"""
        self.registry = APIRegistry()
    
    @abstractmethod
    async def call_api(
        self,
        api_name: str,
        request: Optional[Union[TeaModel, Dict[str, Any]]] = None
    ) -> Tuple[bool, Optional[Union[TeaModel, Dict[str, Any]]], Optional[str]]:
        """
        调用OpenAPI接口
        
        Args:
            api_name: 接口名称
            request: 请求对象（类型由具体实现决定）
            
        Returns:
            Tuple[bool, Optional[Union[TeaModel, Dict[str, Any]]], Optional[str]]: 
                (是否成功, 响应对象, 错误信息)
                响应对象的类型由具体实现决定
        """
        pass
    


class SysomFrameworkClient(OpenAPIClient):
    """基于SysomFramework的OpenAPI客户端实现（使用服务发现）"""
    
    def __init__(self, uid: str, service_name: str = "sysom_openapi", **kwargs):
        """
        初始化SysomFramework客户端
        
        Args:
            uid: 用户ID
            service_name: 服务名称，默认为sysom_openapi
        """
        super().__init__(**kwargs)
        self.uid = uid
        self.service_name = service_name
        self.headers = {
            "x-acs-caller-type": "customer",
            "x-acs-caller-uid": self.uid,
        }
        # 初始化框架
        from .openapi_utils import init_framework
        init_framework()
    
    async def call_api(
        self,
        api_name: str,
        request: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """调用OpenAPI接口（使用SysomFramework）
        
        注意：Framework调用时，参数和返回值都必须是字典类型，不进行任何类型转换。
        
        Args:
            api_name: 接口名称
            request: 请求参数，必须是 Dict[str, Any] 类型，不能是 TeaModel
            
        Returns:
            Tuple[bool, Optional[Dict[str, Any]], Optional[str]]: 
                (是否成功, 响应字典, 错误信息)
                响应对象是 Dict[str, Any] 类型，不进行任何转换
        """
        try:
            # 类型检查：Framework调用时参数必须是字典
            if request is not None and not isinstance(request, dict):
                return False, None, f"Framework调用时参数必须是字典类型，实际类型：{type(request).__name__}"
            
            # 获取Framework路由信息
            framework_route = self.registry.get_framework_route(api_name)
            if framework_route is None:
                return False, None, f"接口 {api_name} 未注册Framework路由或仅支持SDK调用"
            
            # 使用路由中的method和service_name
            actual_method = framework_route.method
            service_name = framework_route.service_name
            url = framework_route.url_pattern
            
            params = request if request is not None else {}
            
            from sysom_utils import SysomFramework
            
            if actual_method == "GET":
                status, json_data, text = await SysomFramework.gclient_get(
                    service_name,
                    url,
                    headers=self.headers,
                    params=params,
                    uid=self.uid
                )
            else:
                status, json_data, text = await SysomFramework.gclient_post(
                    service_name,
                    url,
                    headers=self.headers,
                    data=params,
                    uid=self.uid
                )
            
            if status == 200:
                # Framework返回的是JSON字典，直接返回
                return True, json_data, None
            else:
                return False, None, f"HTTP状态码：{status}，响应：{text}"
        except Exception as e:
            print(f"调用API失败: {e}")
            return False, None, f"调用API失败，错误信息：{e}"


class AlibabaCloudSDKClient(OpenAPIClient):
    """基于阿里云OpenAPI SDK的客户端实现（直接HTTP调用）"""
    
    def __init__(
        self,
        mode: str = "access_key",
        access_key_id: Optional[str] = None,
        access_key_secret: Optional[str] = None,
        security_token: Optional[str] = None,
        region_id: str = "cn-hangzhou",
        **kwargs
    ):
        """
        初始化阿里云OpenAPI SDK客户端
        
        Args:
            mode: 认证模式（access_key或sts）
            access_key_id: AccessKey ID
            access_key_secret: AccessKey Secret
            security_token: STS安全令牌（sts模式需要）
            region_id: 地域ID
        """
        super().__init__(**kwargs)
        self._mode = mode
        self._access_key_id = access_key_id
        self._access_key_secret = access_key_secret
        self._security_token = security_token
        self._region_id = region_id
        self._client = None
    
    def _get_client(self):
        """获取或创建SDK客户端（懒加载）"""
        if self._client is None:
            from .openapi_utils import create_sysom_client
            self._client = create_sysom_client(
                self._mode,
                self._access_key_id,
                self._access_key_secret,
                self._security_token,
            )
        return self._client
    
    async def call_api(
        self,
        api_name: str,
        request: Optional[TeaModel] = None
    ) -> Tuple[bool, Optional[TeaModel], Optional[str]]:
        """调用OpenAPI接口（使用阿里云SDK）
        
        注意：SDK调用时，参数和返回值都必须是TeaModel类型，不进行任何类型转换。
        
        Args:
            api_name: 接口名称
            request: 请求参数，必须是 TeaModel 类型，不能是字典
            
        Returns:
            Tuple[bool, Optional[TeaModel], Optional[str]]: 
                (是否成功, 响应TeaModel对象, 错误信息)
                响应对象是 TeaModel 类型，不进行任何转换
        """
        try:
            # 获取SDK路由信息
            sdk_route = self.registry.get_sdk_route(api_name)
            if sdk_route is None:
                return False, None, f"接口 {api_name} 未注册SDK路由或仅支持Framework调用"
            
            if request is None:
                return False, None, "SDK调用需要TeaModel类型的请求对象"
            
            # 类型检查：SDK调用时参数必须是TeaModel
            if not isinstance(request, TeaModel):
                return False, None, f"SDK调用时参数必须是TeaModel类型，实际类型：{type(request).__name__}"
            
            # 检查请求类型是否匹配
            if not isinstance(request, sdk_route.request_model):
                return False, None, f"请求类型错误，期望{sdk_route.request_model.__name__}，实际：{type(request).__name__}"
            
            # 获取客户端（懒加载）
            client = self._get_client()
            
            # 调用对应的客户端方法
            response = await sdk_route.client_method(client, request)
            
            if response.status_code == 200:
                # SDK返回的是TeaModel对象，直接返回
                return True, response.body, None
            else:
                error_msg = getattr(response.body, 'message', 'Unknown error')
                return False, None, f"调用失败，状态码：{response.body.code}，错误信息：{error_msg}"
        except Exception as e:
            print(f"调用API失败: {e}")
            return False, None, f"调用API失败，错误信息：{e}"


class ClientFactory:
    """客户端工厂类
    
    统一创建OpenAPI客户端实例，根据配置自动选择实现方式
    支持根据接口要求自动选择合适的客户端
    """
    
    @staticmethod
    def create_client(
        deploy_mode: Optional[str] = None,
        uid: Optional[str] = None,
        service_name: str = "sysom_openapi",
        api_name: Optional[str] = None,
        **kwargs
    ) -> OpenAPIClient:
        """
        创建OpenAPI客户端实例
        
        Args:
            deploy_mode: 部署模式（sysom_framework或alibabacloud_sdk），如果为None则从配置读取
            uid: 用户ID（sysom_framework模式需要）
            service_name: 服务名称（sysom_framework模式使用）
            api_name: 要调用的API名称（可选，用于根据接口要求自动选择客户端）
            **kwargs: 其他参数（alibabacloud_sdk模式可能需要access_key_id等）
            
        Returns:
            OpenAPIClient: 客户端实例
        """
        # 如果提供了api_name，检查接口的支持模式
        if api_name:
            registry = APIRegistry()
            route = registry.get_route(api_name)
            if route:
                if route.support_mode == SupportMode.FRAMEWORK_ONLY:
                    # 强制使用SysomFramework
                    deploy_mode = "sysom_framework"
                elif route.support_mode == SupportMode.SDK_ONLY:
                    # 强制使用AlibabaCloudSDK
                    deploy_mode = "alibabacloud_sdk"
                # 如果是BOTH，则使用配置的deploy_mode
        
        if deploy_mode is None:
            deploy_mode = getattr(SERVICE_CONFIG, 'deploy_mode', 'sysom_framework')
        
        if deploy_mode == "alibabacloud_sdk":
            # 从配置或kwargs中获取认证信息
            mode = kwargs.get("mode", getattr(SERVICE_CONFIG, 'type', 'access_key'))
            access_key_id = kwargs.get("access_key_id") or getattr(SERVICE_CONFIG, 'ACCESS_KEY_ID', None)
            access_key_secret = kwargs.get("access_key_secret") or getattr(SERVICE_CONFIG, 'ACCESS_KEY_SECRET', None)
            security_token = kwargs.get("security_token") or getattr(SERVICE_CONFIG, 'security_token', None)
            region_id = kwargs.get("region_id", "cn-hangzhou")
            
            return AlibabaCloudSDKClient(
                mode=mode,
                access_key_id=access_key_id,
                access_key_secret=access_key_secret,
                security_token=security_token,
                region_id=region_id
            )
        else:
            # sysom_framework模式
            if uid is None:
                raise ValueError("sysom_framework模式需要提供uid参数")
            
            return SysomFrameworkClient(
                uid=uid,
                service_name=service_name
            )

