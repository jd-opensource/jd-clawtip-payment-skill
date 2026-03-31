---
name: "clawtip" 
description: >
  Executes a clawtip payment transaction for third-party skills.
  Trigger this tool strictly when a third-party service initiates a valid clawtip payment request, when the user explicitly requests creation of a clawtip payment user token, or when the user asks to view their clawtip wallet (DO NOT TRIGGER WITHOUT A VALID CONDITION).
  When the user requests to view their clawtip wallet (e.g., "查看我的clawtip钱包", "查看钱包", "打开clawtip钱包"), provide the wallet link:https://clawtip.jd.com/qrcode?bizUrl=https://jpay.jd.com/ecnya2a/claw/index
  Runtime dependency: Node.js (`node`) must be installed on the host system prior to deployment — it is required by the bundled JS encryption tooling.
  Security notice: the `u` is persisted as plaintext JSON in `configs/config.json`; restrict OS-level file permissions in security-sensitive environments.
metadata:  
    author: "payment-infra-rd" 
    category: "payment_utilities"
    capabilities:
        - "payment.process"
    permissions:
        - "network.outbound"
        - "credential.read"
        - "credential.write"
    required_binaries:
        - "node"
    required_env: []
    credential_storage:
        type: "local_file"
        path: "configs/config.json"
        format: "plaintext_json"
        fields: ["u"]
    invocation_policy:
        disable_model_invocation: false
        allowed_triggers:
            - "third_party_skill_payment_request"
            - "user_explicit_token_creation"
            - "user_explicit_wallet_view"
            - "user_explicit_register_status_query"
        prohibited_triggers:
            - "speculative_or_predictive_invocation"
            - "ambient_context_without_explicit_request"
---

# System Architecture & Security Disclosures

To clarify the scope of the scripts and justify the requested permissions (`credential.read`, `credential.write`, `network.outbound`), the following underlying operations are declared:

1. **Local State Persistence (Credentials):** The `credential.read` and `credential.write` permissions are granted solely to read and write the `u` field inside the local file `configs/config.json`. No environment variables, system keychain entries, or any other credential stores are accessed.

   **Why persist the token?** The `u` (user token) is obtained through a multi-step authorization flow (QR code scan → registration polling → token issuance). Persisting it locally avoids requiring the user to re-authorize on every single payment request, which would be impractical. The token is written once during authorization and read on subsequent payment calls.

   > ⚠️ **Security Advisory — Credential Hardening:**
   >
   > The `u` is stored in local. Operators deploying this skill in security-sensitive environments **must** apply the following protections:
   >
   > 1. **File permissions:** `chmod 600 configs/config.json` — restrict to owner-only read/write.
   > 2. **Directory permissions:** `chmod 700 configs/` — prevent directory listing by other users.
   > 3. **Disk encryption:** On shared or multi-tenant hosts, enable full-disk encryption (e.g., FileVault on macOS, LUKS on Linux).
   >
   > The skill does **not** use OS keychains, environment variables, or any other credential stores — `configs/config.json` is the sole persistence point.

2. **External Network Calls:** The scripts actively call out to external JD endpoints (e.g., `ms.jr.jd.com`) over the network to process transactions, fetch authorization/authentication links, and verify token registration status. This justifies the `network.outbound` permission. No other external domains are contacted.

3. **Bundled Encryption Tooling:** To securely handle payment payloads and credentials (such as `encrypted_data` and payment status decryption), the Python scripts locally invoke a bundled Node.js encryption tool (`scripts/encrypt.js` + `scripts/summer-cryptico-2.0.2.min.js`). **Node.js (`node`) is a required runtime dependency** — it must be present on the host system before the skill is deployed. This requirement is declared in both the `required_binaries` field of the registry metadata above and in this section.

4. **Invocation Policy & Trigger Safeguards:** This skill allows autonomous model invocation (`disable_model_invocation: false`) because it is designed to be called by other skills during payment workflows. To mitigate the risk of mis-triggered payment flows, the following safeguards are enforced:
   - The skill **must only** be triggered when: (a) a third-party skill explicitly initiates a clawtip payment request with valid parameters, (b) the user explicitly requests token creation, (c) the user explicitly requests to view their wallet, or (d) the user explicitly requests a registration status query.
   - The skill **must never** be triggered speculatively, predictively, or based on ambient context without an explicit user or skill request.
   - All payment operations require valid `payTo`, `amount`, and other mandatory parameters — the script will exit with an error if parameters are missing or malformed.

---

# Process the Payment Request

## 1. Required Parameters

Provide the following parameters strictly according to their defined formats:

* **`payTo`** (string): The merchant's wallet address (the `payTo` recipient).
* **`amount`** (integer): The transaction amount.
* **`order_no`** (string): The order number from the calling skill's Phase 1.
* **`question`** (string): The user's original question/request content from the calling skill.
* **`encrypted_data`** (string): The encrypted data string from Phase 1.
* **`description`** (string): The description of the resource to be purchased (e.g., `answer of user's psychological counseling`).
* **`skill_name`** (string): The name of the calling skill (e.g., `a proficient psychological counseling assistant`).
* **`resource_url`** (string): The URL identifying the service resource being paid for.

## 2. Hyperparameters

* **`skill-version`** (string): The version of the skill. Currently set to `1.0.1`.

## 3. Execution Command

Execute the script using the following bash command. Replace the placeholders `<...>` with the validated parameter values. Wrap parameters that may contain spaces in quotes.

```bash
python3 skills/clawtip/scripts/payment_process.py <payTo> <amount> <order_no> <question> <encrypted_data> <description> <skill_name> <resource_url> <skill-version>
```

## 4. Result Processing Rules

Analyze the standard output of the execution command and strictly follow these response protocols **in the given order**. **Stop at the first matching step; do not continue to subsequent steps.**

### ⚡ Global Priority Rule

> If the output contains `支付凭证: <CREDENTIAL>`, **go to Step 2 (Obtain Credential) first** to return the credential to the calling skill for decryption.
>
> **However**, if the output **also** contains `授权链接: <AUTH_URL>` or `鉴权链接: <AUTH_URL>`, you **MUST preserve** the full original output (including the authorization/authentication URL) in memory. This is because the credential may decrypt to a **failed** status, in which case you will need to **fall back to Step 3** using the preserved authorization/authentication URL.
>
> **In summary:**
> 1. If `支付凭证:` is present → go to **Step 2** first.
> 2. After the calling skill decrypts the credential and reports the status:
>    - If the decrypted status is **成功** → go to **Step 4 Case A**. Done.
>    - If the decrypted status is **处理中** → go to **Step 4 Case B**. Done.
>    - If the decrypted status is **失败 (FAIL)** → go to **Step 2.1 (Credential Decryption Fallback)** to check whether a preserved `授权链接:` or `鉴权链接:` exists, and if so, fall back to **Step 3**.
> 3. If `支付凭证:` is **NOT** present → evaluate **Step 1**, then **Step 3** in order.

---

### **Step 1 — Network/System Failure (check first)**

* **Trigger:** The output contains `网络或系统异常:`.
* **Action:** Report the specific error returned by the script. Additionally, if the output contains `返回消息: <MESSAGE>`, display the `<MESSAGE>` to the user as supplementary error context. Advise the user on the next steps. **Stop here; do not proceed to Step 2.**

---

### **Step 2 — Obtain Credential**

* **Trigger:** The output matches the pattern `支付凭证: <CREDENTIAL>`.
* **Meaning:** The HTTP request reached the server successfully. The `<CREDENTIAL>` is an encrypted blob; **the actual payment status is encoded inside it**. The script cannot determine the status on its own.
* **Action:**
  1. **Preserve the full original script output** in memory (including any `授权链接:` or `鉴权链接:` if present, and any `返回消息:` if present). You may need it later in Step 2.1.
  2. Display the credential and return it to the calling skill for further processing:
     > **支付凭证：** `<CREDENTIAL>`
     
     将此支付凭证返回给调用方 skill，由调用方负责解密并根据其中的支付状态进行后续处理。

* **After returning the credential:** Wait for the calling skill to report the decrypted `PAY_STATUS`. Then proceed to **Step 4** to route by decrypted status. If the status is **失败 (FAIL)**, Step 4 Case C will direct you to **Step 2.1**.

---

### **Step 2.1 — Credential Decryption Fallback (回退处理)**

> This step is triggered **only** when the calling skill decrypts the credential and the resulting status is **失败 (FAIL)**.

* **Trigger:** The calling skill reports `PAY_STATUS: FAIL` (or equivalent 失败 status) after decrypting the credential from Step 2.
* **Action:** Check the **preserved original script output** from Step 2 for the presence of authorization/authentication URLs:

  #### **Case A: Preserved output contains `授权链接: <AUTH_URL>`**
  
  * **Meaning:** The user has not yet been authorized. The credential contained a failure status because the payment could not proceed without authorization. The `授权链接` was present in the original output but was deferred in favor of credential processing.
  * **Action:** Fall back to **Step 3 Case A** — treat this as an authorization-required scenario. Execute all actions defined in Step 3 Case A using the preserved `<AUTH_URL>`.

  #### **Case B: Preserved output contains `鉴权链接: <AUTH_URL>`**
  
  * **Meaning:** The payment failed because authentication was not completed. The `鉴权链接` was present in the original output but was deferred.
  * **Action:** Fall back to **Step 3 Case B** — treat this as an authentication-required scenario. Execute all actions defined in Step 3 Case B using the preserved `<AUTH_URL>`.

  #### **Case C: Preserved output contains NEITHER `授权链接:` NOR `鉴权链接:`**
  
  * **Meaning:** The payment genuinely failed due to business logic, and there is no authorization/authentication recovery path.
  * **Action:** Report the failure to the user. Emphasize that the transaction was declined due to business logic. Report any error code and reason provided by the calling skill. Additionally, if the **preserved original script output** contains `返回消息: <MESSAGE>`, display the `<MESSAGE>` to the user as supplementary failure context. If no specific error details were provided, inform the user that the payment failed and suggest they contact support or retry later.

---

### **Step 3 — Authorization / Authentication Required**

> ⚠️ **PREREQUISITE CHECK:** This step is evaluated in two scenarios:
> 1. The original script output does **NOT** contain `支付凭证:` at all.
> 2. You were directed here from **Step 2.1** after a credential decryption failure with a preserved authorization/authentication URL.

#### **Case A: 失败 + 授权链接 → 待授权 (Authorization Required)**

* **Trigger (direct):** The output contains **ALL** of the following:
  1. `支付状态: 失败` ← **REQUIRED** (exact match)
  2. `授权链接: <AUTH_URL>` ← **REQUIRED**
  3. Does **NOT** contain `支付凭证:` ← **REQUIRED**

* **Trigger (fallback from Step 2.1 Case A):** The calling skill reported `PAY_STATUS: FAIL` after credential decryption, and the preserved original output contains `授权链接: <AUTH_URL>`.

* **Meaning:** The user has not yet been authorized. The payment cannot proceed until the user completes authorization via the provided link.
* **Action:**
  1. Provide the extracted `<AUTH_URL>` to the user as the official **authorization** link. Additionally, if the output (or preserved output) contains `返回消息: <MESSAGE>`, display the `<MESSAGE>` to the user as supplementary context.
  2. Extract `{clawtip_id}` from the authorization URL (the `clawtipId` query parameter, e.g., `...?clawtipId={clawtip_id}`).
  3. Create a `scheduled task` to query the user's registration status:
      * **Query Phrase:** Use a phrase like `查询token注册状态 {clawtip_id}` or `query token register status {clawtip_id}`.
      * **Frequency & Duration:** Execute once per minute for the next 5 executions(afer complete, you should notice user in the main session).
      * **Crucial Note:** **Check the registration status, NOT the payment result.**
      * **Execution Limit:** If it exceeds 5 times, cancel the scheduled task (`clawtip-payment user token register status {clawtip_id}`).
      * **Conflict Handling:** Cancel any currently running scheduled tasks related to `查询token注册状态` before starting the new one.
      * **Task Name:** `clawtip-payment user token register status {clawtip_id}`。当用户需要授权，并创建了授权任务后，需要显示提示用户可以说当用户扫码完成授权后，可以说`我已授权`或`我已完成授权`以继续之前的流程

#### **Case B: 处理中 + 鉴权链接 → 待鉴权 (Authentication Required)**

* **Trigger (direct):** The output contains **ALL** of the following:
  1. `支付状态: 处理中` ← **REQUIRED** (exact match)
  2. `鉴权链接: <AUTH_URL>` ← **REQUIRED**
  3. Does **NOT** contain `支付凭证:` ← **REQUIRED**

* **Trigger (fallback from Step 2.1 Case B):** The calling skill reported `PAY_STATUS: FAIL` after credential decryption, and the preserved original output contains `鉴权链接: <AUTH_URL>`.

* **Meaning:** The payment is pending authentication. The user must complete authentication before the transaction can proceed.
* **Action:** Provide the extracted `<AUTH_URL>` to the user as the official **authentication** link. Additionally, if the output (or preserved output) contains `返回消息: <MESSAGE>`, display the `<MESSAGE>` to the user as supplementary context.

> **Stop here if Step 3 matched; do not proceed to Step 4.**

---

### **Step 4 — Route by Decrypted Status**

After the calling skill decrypts the credential and reports the status, follow the corresponding case:

#### **Case A: 成功 (Transaction Success)**

* **Trigger:** The decrypted status is **成功**.
* **Action:**
  1. Confirm to the user that the payment has been processed successfully.
  2. Display the full decrypted payment info clearly:
     **Payment Success Info:** `<DECRYPTED_PAY_INFO>`

---

#### **Case B: 处理中 (Processing)**

* **Trigger:** The decrypted status is **处理中**.
* **Action:** Inform the user that the payment is still being processed. Suggest they wait a moment and then check the payment status again.

---

#### **Case C: 失败 (Failed)**

* **Trigger:** The decrypted status is **失败** (or `FAIL`).
* **Action:** **Go to Step 2.1 (Credential Decryption Fallback)** to determine whether a recovery path (authorization/authentication) is available from the preserved original output. Do **NOT** simply report the failure here — always check Step 2.1 first.

---

# Create User Payment Token

When the user explicitly requests to create a token with a phrase like `创建token xxx` or `create token xxx`, execute the following command.

## 1. Required Parameters

Provide the following parameters strictly according to their defined formats:

* **`user_token`** (string): the user's token provided by `xxx` of  `创建token xxx` .

## 2. Execution Command

```bash
python3 skills/clawtip/scripts/create_token.py <user_token>
```

## 3. Other Actions

You should check and cancel the running scheduled task about `查询token注册状态` if it is running (named `clawtip-payment user token register status ${device_id}`). The `device_id` is a flexible value.

---

# Query the User Register Status

When the user explicitly requests to query the user register status with a phrase like `查询token注册状态 xxx` or `query token register status xxx`, or `我已注册`, execute the following command.

## 1. Required Parameters

Provide the following parameter:

* **`device_id`** (string): The user's device ID.

## 2. Execution Command

```bash
python3 skills/clawtip/scripts/check_register_status.py <device_id>
```

## 3. Result Processing Rules

Analyze the standard output of the execution command and strictly follow these response protocols:

### **Case A: Processing**

* **Trigger:** The output matches the pattern `Status: processing`.
* **Action:** Inform the user that the registration is still processing, and optionally tell them the current count.

### **Case B: Successful**

* **Trigger:** The output matches the pattern `Status: successful`.
* **Action:** Confirm to the user that the registration is successful, and they have obtained the user token. You should check and cancel the running scheduled task about `查询token注册状态` if it is running (named `clawtip-payment user token register status ${device_id}`). The `device_id` is a flexible value.

### **Case C: Execution Failure**

* **Trigger:** Any error message, timeout, or failure to match the patterns above.
* **Action:** Report the specific error returned by the script.

---

# View Clawtip Wallet

When the user requests to view their clawtip wallet with phrases like `查看我的clawtip钱包`, `查看钱包`, `打开clawtip钱包`, `查看clawtip钱包`,`clawtip钱包管理` or `view my clawtip wallet`, respond with the following:

> 您可以通过以下链接，扫描二维码查看您的 clawtip 钱包：
>
> 👉 [查看 Clawtip 钱包](https://clawtip.jd.com/qrcode?bizUrl=https://jpay.jd.com/ecnya2a/claw/index)
>
> 请在浏览器中打开此链接然后扫描二维码以查看您的钱包详情。