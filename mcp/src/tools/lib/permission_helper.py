"""权限错误检测和处理辅助函数

提供权限错误检测和错误消息增强功能
"""


def is_permission_error(message: str) -> bool:
    """检测是否是权限错误
    
    Args:
        message: 错误消息
        
    Returns:
        bool: 如果是权限错误返回 True，否则返回 False
    """
    if not message:
        return False
    message_lower = message.lower()
    permission_keywords = [
        "权限",
        "permission",
        "没有权限",
        "权限不足",
        "access denied",
        "forbidden",
        "unauthorized",
        "未授权",
        "未开通",
        "未启用",
        "未激活",
        # RAM角色相关错误
        "entitynotexist.role",
        "role not exists",
        "aliyunserviceroleforsysom",
        # 连接失败（可能是权限问题导致的）
        "connect failed",
    ]
    return any(keyword in message_lower for keyword in permission_keywords)


def enhance_permission_error_message(original_message: str) -> str:
    """增强权限错误消息，添加开通建议
    
    Args:
        original_message: 原始错误消息
        
    Returns:
        str: 增强后的错误消息，包含开通建议
    """
    # 统一使用sysom服务的表述，因为所有权限错误本质上都是需要开通sysom服务
    suggestion = (
        "\n\n【权限问题解决方案】\n"
        "检测到权限错误，您需要先开通sysom服务才能使用诊断功能。\n"
        "sysom是免费的服务，开通不会产生任何费用，也不会安装任何组件。\n\n"
        "开通方式：\n"
        "1. 访问 https://alinux.console.aliyun.com/ 进行开通\n"
        "2. 或者告诉我\"需要帮您开通sysom吗\"，我可以使用 initial_sysom 工具帮助您开通\n"
    )
    return original_message + suggestion

