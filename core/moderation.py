"""图片审查模块"""
import aiohttp
import os
import tempfile
from PIL import Image
from astrbot.api import logger
from ..utils.image_utils import ImageUtils


class ImageModerator:
    """图片审查器"""
    
    DEFAULT_MODERATION_PROMPT = """请分析这张图片，判断是否包含以下不适宜内容：
1. 色情/成人内容
2. 暴力/血腥内容
3. 违法/危险内容
4. 极端或令人不适的内容

请只回复 "PASS" 或 "REJECT"：
- 如果图片安全、适合一般用户查看，回复 "PASS"
- 如果包含不适宜内容，回复 "REJECT"

只回复 PASS 或 REJECT，不要其他内容。"""
    
    def __init__(self, config: dict, context=None, proxy: str = None):
        self.config = config
        self.context = context
        self.proxy = proxy
    
    def get_moderation_prompt(self) -> str:
        """获取审查提示词"""
        custom_prompt = self.config.get("moderation_prompt", "")
        if custom_prompt and custom_prompt.strip():
            return custom_prompt.strip()
        return self.DEFAULT_MODERATION_PROMPT
    
    def is_enabled(self) -> bool:
        """检查审查是否启用"""
        return self.config.get("enable_moderation", False)
    
    def get_max_retries(self) -> int:
        """获取最大重试次数"""
        return self.config.get("max_retries", 3)
    
    async def moderate_with_builtin(self, img: Image.Image, provider_id: str) -> tuple:
        """使用 AstrBot 内置提供商进行图片审查"""
        temp_path = None
        try:
            logger.info(f"[图片审查] 开始使用内置提供商: {provider_id}")

            if not self.context:
                logger.error("[图片审查] 无上下文，无法使用内置提供商")
                return True, "无上下文，无法使用内置提供商"

            # 使用 context.get_provider_by_id() 获取提供商
            provider = self.context.get_provider_by_id(provider_id)
            if not provider:
                logger.error(f"[图片审查] 未找到提供商: {provider_id}")
                return True, f"未找到提供商: {provider_id}"

            logger.info(f"[图片审查] 找到提供商: {provider.meta().id}")

            # 保存图片到临时文件
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                img.save(f, format="JPEG", quality=95)
                temp_path = f.name

            logger.info(f"[图片审查] 图片已保存到临时文件: {temp_path}")

            # 构建提示词
            prompt = self.get_moderation_prompt()

            logger.info(f"[图片审查] 发送审查请求到提供商...")

            # 使用 text_chat 方法，传入图片文件路径
            response = await provider.text_chat(
                prompt=prompt,
                image_urls=[temp_path]
            )

            logger.info(f"[图片审查] 收到响应: {response}")

            # 提取响应内容
            if hasattr(response, 'completion_text'):
                result = response.completion_text.strip().upper()
            elif isinstance(response, dict):
                result = response.get("content", "").strip().upper()
            else:
                result = str(response).strip().upper()

            if "PASS" in result:
                logger.info("[图片审查] 审查通过")
                return True, "审查通过"
            elif "REJECT" in result:
                logger.warning(f"[图片审查] 图片被拒绝: {result}")
                return False, "图片内容不适宜"
            else:
                logger.warning(f"[图片审查] 审查结果无法解析: {result}")
                return True, f"审查结果未知: {result}"

        except Exception as e:
            logger.error(f"[图片审查] 内置提供商审查失败: {e}", exc_info=True)
            return True, f"审查出错: {e}"
        finally:
            # 清理临时文件
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    logger.debug(f"[图片审查] 已删除临时文件: {temp_path}")
                except Exception as e:
                    logger.warning(f"[图片审查] 删除临时文件失败: {e}")
    
    async def moderate_with_openai(self, img: Image.Image, api_key: str, 
                                    api_base: str, model: str) -> tuple:
        """使用 OpenAI Compatible API 进行图片审查"""
        try:
            img_base64 = ImageUtils.image_to_base64(img)
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": self.get_moderation_prompt()},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}}
                        ]
                    }
                ],
                "max_tokens": 10
            }
            
            async with aiohttp.ClientSession() as session:
                url = f"{api_base.rstrip('/')}/chat/completions"
                async with session.post(url, json=payload, headers=headers,
                                        timeout=aiohttp.ClientTimeout(total=60),
                                        proxy=self.proxy) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        return True, f"API 请求失败: {resp.status} - {error_text}"
                    
                    data = await resp.json()
                    result = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip().upper()
                    
                    if "PASS" in result:
                        return True, "审查通过"
                    elif "REJECT" in result:
                        return False, "图片内容不适宜"
                    else:
                        logger.warning(f"审查结果无法解析: {result}")
                        return True, f"审查结果未知: {result}"
                        
        except Exception as e:
            logger.error(f"OpenAI Compatible API 审查失败: {e}")
            return True, f"审查出错: {e}"
    
    async def moderate(self, img: Image.Image) -> tuple:
        """执行图片审查"""
        logger.info(f"[图片审查] 开始审查，配置: {self.config}")

        if not self.is_enabled():
            logger.info("[图片审查] 审查未启用")
            return True, "审查未启用"

        provider_type = self.config.get("provider_type", "builtin")
        logger.info(f"[图片审查] 使用提供商类型: {provider_type}")
        
        if provider_type == "builtin":
            provider_id = self.config.get("builtin_provider_id", "")
            logger.info(f"[图片审查] 内置提供商ID: {provider_id}")
            if not provider_id:
                logger.warning("[图片审查] 未配置内置提供商ID")
                return True, "未配置内置提供商ID"
            logger.info(f"[图片审查] 调用内置提供商审查: {provider_id}")
            result = await self.moderate_with_builtin(img, provider_id)
            logger.info(f"[图片审查] 审查结果: {result}")
            return result
        
        elif provider_type == "openai_compatible":
            api_key = self.config.get("openai_api_key", "")
            api_base = self.config.get("openai_api_base", "https://api.openai.com/v1")
            model = self.config.get("openai_model", "gpt-4o")

            logger.info(f"[图片审查] OpenAI Compatible API配置 - base: {api_base}, model: {model}")
            if not api_key:
                logger.warning("[图片审查] 未配置 OpenAI API Key")
                return True, "未配置 OpenAI API Key"

            result = await self.moderate_with_openai(img, api_key, api_base, model)
            logger.info(f"[图片审查] 审查结果: {result}")
            return result

        else:
            logger.error(f"[图片审查] 未知的提供商类型: {provider_type}")
            return True, f"未知的提供商类型: {provider_type}"
