"""测试图片审查配置加载"""
import json
import sys
import os

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import ConfigLoader

# 测试配置文件路径
config_path = "../../activeApps/AstrBot/data/config/astrbot_plugin_fortnue_config.json"

print("=" * 60)
print("测试图片审查配置加载")
print("=" * 60)

# 读取配置文件
try:
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    print(f"\n✓ 成功读取配置文件: {config_path}")
    print(f"\n完整配置:")
    print(json.dumps(config, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"\n✗ 读取配置文件失败: {e}")
    sys.exit(1)

# 测试 ConfigLoader
print("\n" + "=" * 60)
print("测试 ConfigLoader.get_moderation_config()")
print("=" * 60)

moderation_config = ConfigLoader.get_moderation_config(config)
print(f"\n图片审查配置:")
print(json.dumps(moderation_config, indent=2, ensure_ascii=False))

# 检查关键配置项
print("\n" + "=" * 60)
print("检查关键配置项")
print("=" * 60)

enable_moderation = moderation_config.get("enable_moderation", False)
provider_type = moderation_config.get("provider_type", "builtin")
builtin_provider_id = moderation_config.get("builtin_provider_id", "")
max_retries = moderation_config.get("max_retries", 3)

print(f"\n启用审查: {enable_moderation}")
print(f"提供商类型: {provider_type}")
print(f"内置提供商ID: {builtin_provider_id}")
print(f"最大重试次数: {max_retries}")

if enable_moderation:
    print("\n✓ 图片审查已启用")
    if provider_type == "builtin":
        if builtin_provider_id:
            print(f"✓ 使用内置提供商: {builtin_provider_id}")
        else:
            print("✗ 警告: 未配置内置提供商ID")
    elif provider_type == "openai_compatible":
        api_key = moderation_config.get("openai_api_key", "")
        if api_key:
            print(f"✓ 使用 OpenAI Compatible API")
        else:
            print("✗ 警告: 未配置 OpenAI API Key")
else:
    print("\n✗ 图片审查未启用")

print("\n" + "=" * 60)
