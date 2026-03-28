# jd-clawtip-payment-skill

![Version](https://img.shields.io/badge/version-1.0.1-blue.svg)

**Project URL:** [https://github.com/jd-opensource/jd-clawtip-payment-skill#](https://github.com/jd-opensource/jd-clawtip-payment-skill#)

[中文说明](#中文说明) | [English Documentation](#english-documentation)

---
<a id="english-documentation"></a>
## English Documentation

### Overview
`jd-clawtip-payment-skill` is an OpenClaw skill designed to execute JD-Clawtip payment transactions for third-party skills. It serves as foundational payment infrastructure (`payment-infra-rd`), securely handling payment requests, user token creation, and registration status queries.

### Core Capabilities
The skill provides the `payment.process` capability and is structured around three main operations:
1. **Payment Processing**: Initiates payment transactions securely using parameters like `payTo`, `amount`, and `encrypted_data`. It handles complex responses such as generating payment credentials for local decryption, or prompting for user authorization/authentication URLs when required.
2. **User Token Creation**: Generates a JD-Clawtip payment user token when explicitly requested by a user.
3. **Register Status Query**: Queries or polls the registration status of a user token based on `device_id` (crucial during asynchronous QR-code authorization processes).

### Key Components
- `scripts/payment_process.py`: Core script for executing the payment request and generating necessary credentials.
- `scripts/create_token.py`: Script to bind or create a new user payment token.
- `scripts/check_register_status.py`: Script to check the status of a device/user token registration (e.g., successful or processing).
- `scripts/summer-cryptico-2.0.2.min.js` & `test2.js`: Encryption utilities used in generating secure payloads for the payment requests.
- `SKILL.md`: The definitive AI execution protocol for OpenClaw agents describing how to interact with this skill and handle network/status fallbacks.

### Required Permissions
- `network.outbound`: Required to communicate with external payment servers.
- `credential.read` & `credential.write`: Required to securely handle payment credentials and tokens locally.

---
<a id="中文说明"></a>
## 中文说明 (Chinese Documentation)

### 项目简介
`jd-clawtip-payment-skill` 是一个 OpenClaw 技能（Skill），专为第三方技能提供执行京东 Clawtip 支付交易的基础设施平台（属于 `payment-infra-rd` 分类）。它主要负责处理安全支付请求发起、用户支付 Token 的创建以及授权注册状态的轮询查询。

### 核心功能
本技能提供 `payment.process` 能力，主要包含以下三大核心业务流：
1. **支付处理 (Payment Processing)**：接收 `payTo`（收款方）、`amount`（金额）、`encrypted_data` 等参数发起支付交易。根据网关响应，技能既能生成可供调用方解密的“支付凭证”(Credential)，也能在其失败时优雅降级，提供用户授权 (Authorization) 或鉴权 (Authentication) 链接。
2. **创建用户 Token (User Token Creation)**：根据用户指令触发，创建或绑定京东 Clawtip 的支付 Token。
3. **查询注册状态 (Register Status Query)**：根据 `device_id` 轮询或单次查询用户 Token 的注册状态（例如在异步扫码授权流程中，定时检查授权是否完成）。

### 核心目录与脚本
- `scripts/payment_process.py`：核心支付脚本，负责验证参数、签名、发起请求并输出终端凭证或授权链接。
- `scripts/create_token.py`：用于创建/绑定用户支付 Token 的脚本。
- `scripts/check_register_status.py`：用于轮询或校验设备注册及授权状态的脚本。
- `scripts/summer-cryptico-2.0.2.min.js` & `test2.js`：用于支付请求相关的签名和加密工具库。
- `SKILL.md`：OpenClaw Agent 的标准“技能说明书”，定义了 Agent 在调用本技能时的传参规范、错误重试机制及复杂的条件分支回退策略。

### 权限要求
此技能属于高权限的基础设施模块，必须具备以下系统权限才能正常工作：
- `network.outbound`：需要访问外部网络进行支付收单和状态查询。
- `credential.read` & `credential.write`：需要安全地读取系统凭证存储并在本地管理用户支付 Token。
