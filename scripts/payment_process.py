import sys
import json
import base64
import os
import hashlib
import uuid
import platform
import subprocess
import requests
from pathlib import Path
import time
from payment_request import Accepted, Authorization, Payload, Resource, Extensions, PaymentRequest


def get_machine_id():
    """
    获取机器唯一标识的替代方法
    """
    try:
        if os.system == "Windows":
            # Windows系统：获取Windows机器GUID
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                 "SOFTWARE\\Microsoft\\Cryptography")
            machine_guid, _ = winreg.QueryValueEx(key, "MachineGuid")
            winreg.CloseKey(key)
            machine_id = machine_guid

        elif os.system == "Darwin":  # macOS
            # macOS系统：获取IOPlatformUUID
            result = subprocess.run(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                capture_output=True,
                text=True
            )
            for line in result.stdout.split('\n'):
                if "IOPlatformUUID" in line:
                    machine_id = line.split('"')[-2]
                    break
            else:
                machine_id = str(uuid.getnode())  # 备用方案

        elif os.system == "Linux":
            # Linux系统：尝试多种方法
            possible_paths = [
                "/etc/machine-id",
                "/var/lib/dbus/machine-id",
                "/sys/class/dmi/id/product_uuid"
            ]

            for path in possible_paths:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        machine_id = f.read().strip()
                    break
            else:
                # 如果都没有，使用MAC地址
                machine_id = str(uuid.getnode())
        else:
            # 其他系统使用MAC地址
            machine_id = str(uuid.getnode())

    except Exception as e:
        print(f"获取机器ID时出错: {e}，使用备用方案")
        # 最后的备用方案：使用主机名+MAC地址组合
        hostname = platform.node()
        mac = str(uuid.getnode())
        machine_id = hashlib.sha256(f"{hostname}{mac}".encode()).hexdigest()

    # 生成一个稳定的哈希ID（类似原machineid.hashed_id的功能）
    hashed_id = hashlib.sha256(f"jd_payment_skill_{machine_id}".encode()).hexdigest()
    return hashed_id[:128]  # 返回前16位作为简化版本


def get_user_token(device_id: str):
    """
    从上级目录的configs/config.json获取userToken
    如果文件或目录不存在，则生成链接和二维码
    """
    # 获取当前文件所在目录的上级目录中的configs文件夹
    current_dir = Path(__file__).parent.absolute()
    parent_dir = current_dir.parent
    config_dir = parent_dir / 'configs'
    config_file = config_dir / 'config.bin'

    # 检查配置文件是否存在
    if config_dir.exists() and config_file.exists():
        try:
            with open(config_file, 'rb') as f:
                encoded_data = f.read()
                config_data_str = base64.b64decode(encoded_data).decode('utf-8')
                config_data = json.loads(config_data_str)
                if 'userToken' in config_data:
                    print(f"从配置文件读取到userToken: {config_data['userToken']}")
                    return config_data['userToken']
                else:
                    print("配置文件中不存在userToken字段")
        except Exception as e:
            print(f"读取配置文件失败: {e}")
    return None


def get_public_key():
    """
    从域名获取base64编码后公钥
    """
    # api_url = "https://117.72.16.38/api/getPublicKey"
    api_url = "https://ms.jr.jd.com/gw2/generic/hyqy/h5/m/getSMPublicKey"

    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        response = requests.post(api_url, timeout=10, verify=False)
        response.raise_for_status()
        try:
            result = response.json()
            pub_key = result.get("resultData")
            key = pub_key if pub_key else response.text.strip()
        except json.JSONDecodeError:
            key = response.text.strip()
        print(f"获取到公钥 (前30字符): {key[:30] if key else 'None'}...")
        return key
    except Exception as e:
        print(f"获取公钥失败: {e}")
        return None


def deal_payment(payTo: str, amount: int,
                 skill_id: str = "", order_no: str = "", question: str = "",
                 encrypted_data: str = "", description: str = "",
                 skill_name: str = "", resource_url: str = "", skill_version: str = "1.0.1",
                 system_id: str = "jd-clawtip", system_token: str = "jd-clawtip"):
    machine_id = get_machine_id()

    # 获取user_token
    user_token = get_user_token(machine_id)

    # ------------------------------
    # 调用 Node.js 脚本 test2.js 加密数据
    # ------------------------------
    encrypted_user_token = user_token
    encrypted_machine_id = machine_id

    # 获取公钥
    base64_pub_key = get_public_key()
    if not base64_pub_key:
        print("未能获取到公钥，无法加密数据。")
        return None

    try:
        current_dir = Path(__file__).parent.absolute()
        js_script_path = current_dir / 'test2.js'

        if user_token:
            result = subprocess.run(
                ["node", str(js_script_path), user_token, base64_pub_key],
                capture_output=True,
                text=True,
                check=True
            )
            encrypted_user_token = result.stdout.strip()
            print("成功调用 test2.js 对 userToken 进行了加密。")

        if machine_id:
            result_machine = subprocess.run(
                ["node", str(js_script_path), machine_id, base64_pub_key],
                capture_output=True,
                text=True,
                check=True
            )
            encrypted_machine_id = result_machine.stdout.strip()
            print("成功调用 test2.js 对 deviceId 进行了加密。")

    except subprocess.CalledProcessError as e:
        print(f"调用加密脚本时加密失败: {e.stderr if hasattr(e, 'stderr') else e}")
        return None
    except Exception as e:
        print(f"执行加密脚本时发生异常: {e}")
        return None

    # 构造支付入参
    accepted = Accepted(
        payTo=payTo,
        amount=str(amount),
        network="eip155:84532",  # 待定
        asset="0x036CbD53842c5426634e7929541eC2318f3dCF7e",  # 待定
    )

    authorization = Authorization(
        from_address=encrypted_user_token,
        to=payTo,
        value=str(amount),
        nonce=uuid.uuid4().hex
    )

    payload = Payload(
        signature="",
        authorization=authorization
    )

    resource = Resource(
        url=resource_url if resource_url else "https://api.example.com/premium/resource/123",
        description=description if description else "Premium API access for data analysis.",
        mimeType="application/json"
    )

    order_no = order_no if order_no else (str(int(time.time() * 1000)) + str(uuid.uuid4().int % 1000000))
    asked_contents = question if question else ""
    extensions = Extensions(
        orderNo=order_no,
        askedContents=asked_contents,
        deviceId=encrypted_machine_id,
        skillId=skill_id,
        skillName=skill_name,
        skillVersion=skill_version,
        encryptedData=encrypted_data
    )

    payment_request = PaymentRequest(
        accepted=accepted,
        payload=payload,
        resource=resource,
        extensions=extensions,
        systemId=system_id,
        systemToken=system_token
    )

    print(payment_request.to_json())

    # 发起真实支付请求
    # api_url = "https://117.72.16.38/api/payment"
    api_url = "https://ms.jr.jd.com/gw2/generic/hyqy/h5/m/clawtipPay"
    headers = {
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(api_url, json=payment_request.to_dict(), headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()

        result_data = result.get("resultData", {})
        success = result.get("success", False)
        result_code = str(result.get("code", ""))

        # print(f"支付请求: {json.dumps(payment_request.to_dict(), ensure_ascii=False)}")

        auth_url = result_data.get("authUrl")
        if auth_url is not None and auth_url != "":
            url_type = result_data.get("urlType")
            if "OPEN" == url_type:
                print(f"授权链接: {auth_url}")
            elif "RISK" == url_type:
                print(f"鉴权连接: {auth_url}")
        if not success:
            print(f"网络或系统异常: {result.get('resultMsg', 'Unknown Error')}")
            return None

        response_message = result_data.get("message", "")
        print(f"返回消息: {response_message}")

        success_pay_info_json = result_data.get("payCredential", "")
        print(f"支付凭证: {success_pay_info_json}")
        return success_pay_info_json

    except requests.exceptions.RequestException as e:
        print(f"支付请求失败: {e}")
        return None
    except (json.JSONDecodeError, KeyError) as e:
        print(f"解析支付响应失败: {e}")
        return None


if __name__ == "__main__":
    # 检查传入参数的数量是否正确 (1个脚本名 + 2个必须参数 + 其他可选参数)
    if len(sys.argv) < 9:
        print(
            "用法: python payment_process.py <payTo> <amount> [skill_id] [order_no] [question] [encrypted_data] [description] [skill_name] [resource_url] [skill_version] [system_id] [system_token]")
        sys.exit(1)

    # 获取必须参数
    payTo = sys.argv[1]
    try:
        amount = int(sys.argv[2])
    except ValueError:
        print("错误: 金额必须是整数")
        sys.exit(1)

    # 获取可选参数
    order_no = sys.argv[3] if len(sys.argv) > 4 else ""
    question = sys.argv[4] if len(sys.argv) > 5 else ""
    encrypted_data = sys.argv[5] if len(sys.argv) > 6 else ""
    description = sys.argv[6] if len(sys.argv) > 7 else ""
    skill_name = sys.argv[7] if len(sys.argv) > 8 else ""
    resource_url = sys.argv[8] if len(sys.argv) > 9 else ""
    skill_version = sys.argv[9] if len(sys.argv) > 10 else "1.0.1"
    system_id = sys.argv[10] if len(sys.argv) > 11 else "jd-clawtip"
    system_token = sys.argv[11] if len(sys.argv) > 12 else "jd-clawtip"

    # 传入函数并执行
    token = deal_payment(payTo, amount, "blank", order_no, question, encrypted_data, description, skill_name,
                         resource_url, skill_version, system_id, system_token)

    if token is None:
        print("支付未成功")
    else:
        print(f"支付凭证: {token}")
