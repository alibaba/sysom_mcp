# .env 配置文件说明

本文档说明如何配置 `.env` 文件以使用 SysOM MCP 服务。

## 文件位置

`.env` 文件应位于项目根目录（`/root/sysom_mcp/.env`）。

## 配置项说明

### 认证模式配置

项目支持三种阿里云认证模式，通过 `type` 字段进行配置：

- `access_key`：使用 AccessKey ID 和 AccessKey Secret 进行认证
- `sts`：使用 STS 临时凭证进行认证
- `ram_role_arn`：使用 RAM 角色 ARN 进行认证

### 通用配置项

```bash
# 认证模式：access_key、sts、ram_role_arn
type='access_key'

# DashScope API Key（用于 LLM 调用，所有模式都需要）
DASHSCOPE_API_KEY=''
```

## 不同模式下的必填字段

### 1. AccessKey 模式（type='access_key'）

当 `type='access_key'` 时，必须填写以下字段：

```bash
type='access_key'

# 必填字段
ACCESS_KEY_ID=''
ACCESS_KEY_SECRET=''
DASHSCOPE_API_KEY=''
```

**必填字段说明：**
- `ACCESS_KEY_ID`：阿里云 AccessKey ID
- `ACCESS_KEY_SECRET`：阿里云 AccessKey Secret
- `DASHSCOPE_API_KEY`：DashScope API Key（用于 LLM 调用）

### 2. STS 模式（type='sts'）

当 `type='sts'` 时，必须填写以下字段：

```bash
type='sts'

# 必填字段
ALIBABA_CLOUD_SECURITY_TOKEN=''
DASHSCOPE_API_KEY=''
```

**必填字段说明：**
- `ALIBABA_CLOUD_SECURITY_TOKEN`：STS 安全令牌（Security Token）
- `DASHSCOPE_API_KEY`：DashScope API Key（用于 LLM 调用）

### 3. RAM Role ARN 模式（type='ram_role_arn'）

当 `type='ram_role_arn'` 时，必须填写以下字段：

```bash
type='ram_role_arn'

# 必填字段
ROLE_ARN=''
ACCESS_KEY_ID=''
ACCESS_KEY_SECRET=''
DASHSCOPE_API_KEY=''
```

**必填字段说明：**
- `ROLE_ARN`：要扮演的 RAM 角色 ARN（格式：`acs:ram::<account-id>:role/<role-name>`）
- `ACCESS_KEY_ID`：阿里云 AccessKey ID
- `ACCESS_KEY_SECRET`：阿里云 AccessKey Secret
- `DASHSCOPE_API_KEY`：DashScope API Key（用于 LLM 调用）


## 获取凭证

### AccessKey ID 和 AccessKey Secret

1. 登录阿里云控制台
2. 进入「访问控制」->「用户」->「创建用户」或选择已有用户
3. 创建 AccessKey，获取 AccessKey ID 和 AccessKey Secret

### DashScope API Key

1. 访问 [阿里云百炼平台](https://dashscope.console.aliyun.com/)
2. 开通百炼服务
3. 在「API-KEY 管理」中创建 API Key
4. 参考[官方文档](https://help.aliyun.com/zh/model-studio/get-api-key)获取免费额度

### STS 临时凭证

STS 临时凭证通常通过以下方式获取：
- 通过阿里云 STS 服务 AssumeRole 接口获取
- 通过 ECS 实例角色自动获取
- 通过其他支持 STS 的服务获取

### RAM Role ARN

RAM Role ARN 格式：`acs:ram::<account-id>:role/<role-name>`

- `account-id`：阿里云账号 ID
- `role-name`：RAM 角色名称

## 相关文档

- [阿里云访问控制文档](https://help.aliyun.com/product/28625.html)
- [阿里云 STS 文档](https://help.aliyun.com/product/28756.html)
- [DashScope API Key 获取指南](https://help.aliyun.com/zh/model-studio/get-api-key)

