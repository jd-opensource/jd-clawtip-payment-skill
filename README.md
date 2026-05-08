# jd-clawtip-payment-skill

![Version](https://img.shields.io/badge/version-1.0.12-blue.svg)

**Project URL:** [https://github.com/jd-opensource/jd-clawtip-payment-skill#](https://github.com/jd-opensource/jd-clawtip-payment-skill#)

[中文说明](#中文说明) | [English Documentation](#english-documentation)

---
<a id="english-documentation"></a>
## English Documentation

### Overview
`jd-clawtip-payment-skill` is an OpenClaw skill designed to execute JD-Clawtip payment transactions for third-party skills. It serves as foundational payment infrastructure (`payment-infra-rd`), securely handling payment requests, user token creation, and registration status queries.

### Core Capabilities
The skill provides the `payment.process` capability and is structured around three main operations:
1. **Payment Processing**: Initiates payment transactions securely using parameters like `order_no`, `indicator`, and `skill-version`. It handles complex responses such as generating payment credentials for the calling skill to decrypt, or prompting for user authorization/authentication URLs when required.
2. **User Token Creation**: Generates a JD-Clawtip payment user token when explicitly requested by a user.
3. **Register Status Query**: Queries the registration status of a user token based on `clawtip_id` (crucial during asynchronous QR-code authorization processes).

### Architecture

This skill uses the `@clawtip/clawtip-cli@1.0.1` npm package as its sole runtime dependency. All payment, token creation, and registration queries are executed via `npx` commands, eliminating the need for local scripts or additional runtime dependencies.

**Key commands:**
- `npx --yes @clawtip/clawtip-cli@1.0.1 pay` — Execute payment requests
- `npx --yes @clawtip/clawtip-cli@1.0.1 create-token` — Create user payment tokens
- `npx --yes @clawtip/clawtip-cli@1.0.1 check-register` — Query user registration status

### Key Files
- `SKILL.md`: The definitive AI execution protocol for OpenClaw agents describing how to interact with this skill and handle network/status fallbacks.
- `IMPORTANT_STATEMENTS.md`: Security disclosures, provenance attestation, and architecture documentation.

### Required Permissions
- `network.outbound`: Required to communicate with external payment servers via the CLI.
- `install`: Permission to install `npm:@clawtip/clawtip-cli@1.0.1`.

---
<a id="中文说明"></a>
## 中文说明 (Chinese Documentation)

### 项目简介
`jd-clawtip-payment-skill` 是一个 OpenClaw 技能（Skill），专为第三方技能提供执行京东 Clawtip 支付交易的基础设施平台（属于 `payment-infra-rd` 分类）。它主要负责处理安全支付请求发起、用户支付 Token 的创建以及授权注册状态的查询。

### 核心功能
本技能提供 `payment.process` 能力，主要包含以下三大核心业务流：
1. **支付处理 (Payment Processing)**：接收 `order_no`（订单号）、`indicator`（技能标识）等参数发起支付交易。根据网关响应，技能既能生成可供调用方解密的"支付凭证"(Credential)，也能在其失败时优雅降级，提供用户授权 (Authorization) 或鉴权 (Authentication) 链接。
2. **创建用户 Token (User Token Creation)**：根据用户指令触发，创建或绑定京东 Clawtip 的支付 Token。
3. **查询注册状态 (Register Status Query)**：根据 `clawtip_id` 查询用户 Token 的注册状态（例如在异步扫码授权流程中，确认授权是否完成）。

### 技术架构

本技能全面采用 `@clawtip/clawtip-cli@1.0.1` npm CLI 包作为唯一运行时依赖，通过 `npx` 命令执行所有支付、Token 创建和注册查询操作，无需本地脚本或额外运行时环境。

**核心命令：**
- `npx --yes @clawtip/clawtip-cli@1.0.1 pay` — 执行支付请求
- `npx --yes @clawtip/clawtip-cli@1.0.1 create-token` — 创建用户支付 Token
- `npx --yes @clawtip/clawtip-cli@1.0.1 check-register` — 查询用户注册状态

### 核心文件
- `SKILL.md`：OpenClaw Agent 的标准"技能说明书"，定义了 Agent 在调用本技能时的传参规范、错误重试机制及复杂的条件分支回退策略。
- `IMPORTANT_STATEMENTS.md`：安全披露声明、包来源追溯及架构文档。

### 权限要求
- `network.outbound`：需要通过 CLI 访问外部网络进行支付收单和状态查询。
- `install`：安装 `npm:@clawtip/clawtip-cli@1.0.1` 的权限。
