"""OpenAPI客户端抽象层

提供统一的OpenAPI调用接口，支持两种实现方式：
1. SysomFrameworkClient: 通过SysomFramework微服务间发现调用（集群内部）
2. AlibabaCloudSDKClient: 通过阿里云OpenAPI SDK调用（公网）
"""
from abc import ABC, abstractmethod
from typing import Optional, Type, Tuple, Any, Dict, Union
from Tea.model import TeaModel
from .logger_config import setup_logger
from .api_registry import APIRegistry
from .service_config import SERVICE_CONFIG

logger = setup_logger(__name__)

class OpenAPIClient(ABC):
    """OpenAPI客户端抽象基类
    
    所有OpenAPI客户端实现都应该继承此类，提供统一的接口调用方式。
    
    注意：
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
        uid: Optional[str] = None,
        **kwargs
    ) -> OpenAPIClient:
        """
        创建OpenAPI客户端实例
        
        Args:
            uid: 用户ID（sysom_framework模式需要）
            **kwargs: 其他参数（alibabacloud_sdk模式可能需要access_key_id等）
            
        Returns:
            OpenAPIClient: 客户端实例
        """
       
        mode = kwargs.get("mode") or SERVICE_CONFIG.openapi.type
        access_key_id = kwargs.get("access_key_id") or SERVICE_CONFIG.openapi.access_key_id
        access_key_secret = kwargs.get("access_key_secret") or SERVICE_CONFIG.openapi.access_key_secret
        security_token = kwargs.get("security_token") or SERVICE_CONFIG.openapi.security_token
        region_id = kwargs.get("region_id", "cn-hangzhou")
        role_arn = kwargs.get("security_token") or SERVICE_CONFIG.openapi.role_arn
        logger.info(
            f"创建OpenAPI客户端，模式：{mode}, access_key_id: {access_key_id} region_id: {region_id} access_key_secret: {access_key_secret} role_arn: {role_arn}"
        )
        if mode == "ram_role_arn":
            import os
            from alibabacloud_credentials.client import Client as CredentialClient
            from alibabacloud_credentials.models import Config as CredentialConfig
            from alibabacloud_tea_openapi import models as open_api_models

            credentialsConfig = CredentialConfig(
                type="ram_role_arn",
                # 必填参数，此处以从环境变量中获取AccessKey ID为例
                access_key_id=access_key_id,
                # 必填参数，此处以从环境变量中获取AccessKey Secret为例
                access_key_secret=access_key_secret,
                # 必填参数，要扮演的RAM角色ARN，示例值：acs:ram::123456789012****:role/adminrole，支持通过环境变量ALIBABA_CLOUD_ROLE_ARN设置。
                role_arn=role_arn,
                # 可选参数，角色会话名称，支持通过环境变量ALIBABA_CLOUD_ROLE_SESSION_NAME设置。
                role_session_name="SYSOM_MCP_SERVER",
                # 可选参数，设置更小的权限策略，非必填。示例值：{"Statement": [{"Action": ["*"],"Effect": "Allow","Resource": ["*"]}],"Version":"1"}
                # policy="<policy>",
                # 可选参数，角色外部ID，主要功能是防止混淆代理人问题。
                # external_id="<external_id>",
                # 可选参数，会话过期时间，默认3600秒。
                role_session_expiration=3600,
            )

            credentialsClient = CredentialClient(credentialsConfig)

            credential = credentialsClient.get_credential()
            mode = "sts"
            access_key_id = credential.get_access_key_id()
            access_key_secret = credential.get_access_key_secret()
            security_token = credential.get_security_token()
            logger.info(f"get new credential, access_key_id: {access_key_id} access_key_secret: {access_key_secret} security_token: {security_token}")
            
        return AlibabaCloudSDKClient(
            mode=mode,
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            security_token=security_token,
            region_id=region_id,
        )
            
        