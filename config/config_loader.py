"""配置加载模块"""
import json
import os
from astrbot.api import logger


class ConfigLoader:
    """配置加载器"""
    
    @staticmethod
    def load_backgrounds(backgrounds_path: str) -> dict:
        """加载背景图片配置"""
        try:
            with open(backgrounds_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载背景图片配置失败: {e}")
            return {}
    
    @staticmethod
    def get_fortune_config(config: dict) -> dict:
        """获取运势配置"""
        return config.get("fortune_config", {})
    
    @staticmethod
    def get_moderation_config(config: dict) -> dict:
        """获取图片审查配置"""
        return config.get("image_moderation", {})
    
    @staticmethod
    def get_proxy(config: dict) -> str | None:
        """获取代理配置"""
        proxy = config.get("fortune_config", {}).get("proxy")
        return proxy if proxy else None
