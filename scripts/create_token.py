import sys
from pathlib import Path
import json
import base64
import time
import os

def create_and_save_token(user_token: str):
    """
    创建支付令牌并保存到config.json

    Args:
        user_token (str): 用户令牌

    Returns:
        str: 生成的支付令牌，如果失败则返回None
    """
    current_dir = Path(__file__).parent.absolute()
    parent_dir = current_dir.parent
    config_dir = parent_dir / 'configs'
    config_file = config_dir / 'config.bin'

    # 确保configs目录存在
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
        print(f"确保目录存在: {config_dir}")
    except Exception as e:
        print(f"创建目录失败: {e}")
        return None

    # 读取或创建config.bin
    config_data = {}
    if config_file.exists():
        try:
            with open(config_file, 'rb') as f:
                encoded_data = f.read()
                config_data_str = base64.b64decode(encoded_data).decode('utf-8')
                config_data = json.loads(config_data_str)
            print(f"已读取现有配置文件: {config_file}")
        except Exception as e:
            print(f"读取配置文件出错: {e}，将创建新文件")
            config_data = {}

    # 添加或更新userToken
    config_data['userToken'] = user_token
    timestamp = str(int(time.time()))
    config_data['lastUpdateTime'] = timestamp

    # 写入config.bin
    try:
        config_data_str = json.dumps(config_data)
        encoded_data = base64.b64encode(config_data_str.encode('utf-8'))
        with open(config_file, 'wb') as f:
            f.write(encoded_data)
        print(f"成功将userToken写入配置文件: {config_file}")
        print(f"userToken: {user_token}")
        return user_token
    except Exception as e:
        print(f"写入配置文件失败: {e}")
        return None

if __name__ == "__main__":
    # 检查传入参数的数量是否正确 (1个脚本名 + 1个参数 = 2)
    if len(sys.argv) != 2:
        print("用法: create_token.py <user_token>")
        sys.exit(1)

    # 获取参数
    user_token = sys.argv[1]

    token = create_and_save_token(user_token)