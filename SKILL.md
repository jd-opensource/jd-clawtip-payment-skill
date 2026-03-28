---
name: "jd-clawtip-payment-skill" 
description: >
  Executes a jd-clawtip payment transaction for third-party skills. 
  Trigger this tool strictly when a third-party service initiates a valid jd-clawtip payment request or user wanna create jd-clawtip payment user token(DO NOT GENERATION WITHOUT CONDITION).
metadata:  
    version: "1.0.1"
    author: "payment-infra-rd" 
    category: "payment_utilities"
    capabilities:
        - "payment.process"
    permissions:
        - "network.outbound"
        - "credential.read"
        - "credential.write"
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
python3 skills/jd-clawtip-payment-skill/scripts/payment_process.py <payTo> <amount> <order_no> <question> <encrypted_data> <description> <skill_name> <resource_url> <skill-version>
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
      * **Execution Limit:** If it exceeds 5 times, cancel the scheduled task (`jd-clawtip-payment user token register status {clawtip_id}`).
      * **Conflict Handling:** Cancel any currently running scheduled tasks related to `查询token注册状态` before starting the new one.
      * **Task Name:** `jd-clawtip-payment user token register status {clawtip_id}`。当用户需要授权，并创建了授权任务后，需要显示提示用户可以说当用户扫码完成授权后，可以说`我已授权`或`我已完成授权`以继续之前的流程

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
python3 skills/jd-clawtip-payment-skill/scripts/create_token.py <user_token>
```

## 3. Other Actions

You should check and cancel the running scheduled task about `查询token注册状态` if it is running (named `jd-clawtip-payment user token register status ${device_id}`). The `device_id` is a flexible value.

---

# Query the User Register Status

When the user explicitly requests to query the user register status with a phrase like `查询token注册状态 xxx` or `query token register status xxx`, or `我已注册`, execute the following command.

## 1. Required Parameters

Provide the following parameter:

* **`device_id`** (string): The user's device ID.

## 2. Execution Command

```bash
python3 skills/jd-clawtip-payment-skill/scripts/check_register_status.py <device_id>
```

## 3. Result Processing Rules

Analyze the standard output of the execution command and strictly follow these response protocols:

### **Case A: Processing**

* **Trigger:** The output matches the pattern `Status: processing`.
* **Action:** Inform the user that the registration is still processing, and optionally tell them the current count.

### **Case B: Successful**

* **Trigger:** The output matches the pattern `Status: successful`.
* **Action:** Confirm to the user that the registration is successful, and they have obtained the user token. You should check and cancel the running scheduled task about `查询token注册状态` if it is running (named `jd-clawtip-payment user token register status ${device_id}`). The `device_id` is a flexible value.

### **Case C: Execution Failure**

* **Trigger:** Any error message, timeout, or failure to match the patterns above.
* **Action:** Report the specific error returned by the script.