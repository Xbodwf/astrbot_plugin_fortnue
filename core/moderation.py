"""图片审查模块"""
import aiohttp
import os
import tempfile
import json
import re
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
    
    DEFAULT_MOSAIC_MODERATION_PROMPT = """请分析这张二次元风格图片，判断是否包含真正不适宜的内容。

【重要】以下情况应当判定为 PASS（通过），无需打码：
- 正常的二次元插画、动漫角色立绘
- 穿着正常服装的角色（包括泳装、露背装、短裤等常见服装）
- 角色的正常身体曲线和轮廓展示
- 美术风格的肌肤展示（如光滑的背部、腿部等）
- 轻度性感的服装或姿势（只要没有明显暴露私密部位）
- 艺术风格的绘画作品

【应当判定为 REJECT】仅以下真正不适宜的内容需要打码：
- 明确暴露的私密部位（生殖器、女性乳头等）
- 明显的性行为暗示或姿势
- 极度暴力的画面（大量血液、残肢等）
- 违法或极端令人不适的内容

如果图片通过审查，请只回复 "PASS"。

如果确实包含不适宜内容需要打码，请输出：
REJECT
{"bboxes": [[x1, y1, x2, y2], ...]}

其中坐标为相对坐标（0到1之间的小数），(x1, y1) 为左上角，(x2, y2) 为右下角。
仅标记真正需要遮挡的私密区域，不要过度标记。"""
    
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
    
    def get_mosaic_prompt(self) -> str:
        """获取打码模式的审查提示词"""
        custom_prompt = self.config.get("mosaic_prompt", "")
        if custom_prompt and custom_prompt.strip():
            return custom_prompt.strip()
        return self.DEFAULT_MOSAIC_MODERATION_PROMPT
    
    def is_enabled(self) -> bool:
        """检查审查是否启用"""
        return self.config.get("enable_moderation", False)

    def should_moderate_source(self, source_name: str) -> bool:
        """检查指定图源是否需要审核

        Args:
            source_name: 图源名称（如 pixiv, blue_archive）

        Returns:
            True 表示需要审核，False 表示跳过审核
        """
        if not self.is_enabled():
            return False

        filter_mode = self.config.get("source_filter_mode", "blacklist")
        filter_list = self.config.get("source_filter_list", ["pixiv"])

        # 黑名单模式：列表中的图源不审核
        if filter_mode == "blacklist":
            should_moderate = source_name not in filter_list
            logger.debug(f"[图片审查] 黑名单模式 - 图源 {source_name} {'需要' if should_moderate else '不需要'}审核")
            return should_moderate

        # 白名单模式：仅列表中的图源需要审核
        elif filter_mode == "whitelist":
            should_moderate = source_name in filter_list
            logger.debug(f"[图片审查] 白名单模式 - 图源 {source_name} {'需要' if should_moderate else '不需要'}审核")
            return should_moderate

        # 未知模式，默认需要审核
        logger.warning(f"[图片审查] 未知的过滤模式: {filter_mode}，默认需要审核")
        return True

    def get_failed_action(self) -> str:
        """获取审核失败后的行为

        Returns:
            retry_same: 从同一图源重新取图
            switch_source: 切换到其他图源
            notify_user: 提示用户审核失败
            mosaic: 对不适宜区域打码
        """
        return self.config.get("failed_action", "retry_same")
    
    def get_max_retries(self) -> int:
        """获取最大重试次数"""
        return self.config.get("max_retries", 3)
    
    def get_mosaic_block_size(self) -> int:
        """获取马赛克块大小"""
        return self.config.get("mosaic_block_size", 15)
    
    def _parse_bboxes(self, text: str) -> list:
        """从响应文本中解析边界框坐标"""
        bboxes = []
        
        # 尝试提取 JSON 部分
        json_match = re.search(r'\{[\s\S]*"bboxes"[\s\S]*\}', text)
        if json_match:
            try:
                data = json.loads(json_match.group())
                if "bboxes" in data:
                    for bbox in data["bboxes"]:
                        if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
                            # 验证坐标是否有效
                            if all(isinstance(v, (int, float)) for v in bbox[:4]):
                                bboxes.append(tuple(bbox[:4]))
            except json.JSONDecodeError:
                pass
        
        # 如果没有找到 JSON，尝试匹配 [x, y, x, y] 格式
        if not bboxes:
            pattern = r'\[(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\]'
            matches = re.findall(pattern, text)
            for match in matches:
                bboxes.append(tuple(float(x) for x in match))
        
        return bboxes
    
    def _extract_json_from_response(self, response) -> str:
        """从响应对象中提取文本内容"""
        if hasattr(response, 'completion_text'):
            return response.completion_text
        elif isinstance(response, dict):
            return response.get("content", "")
        else:
            return str(response)
    
    async def moderate_with_builtin(self, img: Image.Image, provider_id: str, 
                                     prompt: str = None) -> tuple:
        """使用 AstrBot 内置提供商进行图片审查"""
        temp_path = None
        try:
            logger.info(f"[图片审查] 开始使用内置提供商: {provider_id}")

            if not self.context:
                logger.error("[图片审查] 无上下文，无法使用内置提供商")
                return True, "无上下文，无法使用内置提供商", []

            # 使用 context.get_provider_by_id() 获取提供商
            provider = self.context.get_provider_by_id(provider_id)
            if not provider:
                logger.error(f"[图片审查] 未找到提供商: {provider_id}")
                return True, f"未找到提供商: {provider_id}", []

            logger.info(f"[图片审查] 找到提供商: {provider.meta().id}")

            # 保存图片到临时文件
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                # 如果图片有透明通道，转换为 RGB
                if img.mode in ('RGBA', 'LA', 'P'):
                    # 创建白色背景
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')

                img.save(f, format="JPEG", quality=95)
                temp_path = f.name

            logger.info(f"[图片审查] 图片已保存到临时文件: {temp_path}")

            # 使用传入的提示词或默认提示词
            use_prompt = prompt or self.get_moderation_prompt()

            logger.info(f"[图片审查] 发送审查请求到提供商...")

            # 使用 text_chat 方法，传入图片文件路径
            response = await provider.text_chat(
                prompt=use_prompt,
                image_urls=[temp_path]
            )

            logger.info(f"[图片审查] 收到响应: {response}")

            # 提取响应内容
            result = self._extract_json_from_response(response)
            result_upper = result.strip().upper()

            if "PASS" in result_upper:
                logger.info("[图片审查] 审查通过")
                return True, "审查通过", []
            elif "REJECT" in result_upper:
                # 尝试解析边界框坐标
                bboxes = self._parse_bboxes(result)
                if bboxes:
                    logger.warning(f"[图片审查] 图片不适宜，检测到 {len(bboxes)} 个区域需要打码")
                    return False, "图片内容不适宜", bboxes
                else:
                    logger.warning(f"[图片审查] 图片被拒绝: {result}")
                    return False, "图片内容不适宜", []
            else:
                logger.warning(f"[图片审查] 审查结果无法解析: {result}")
                return True, f"审查结果未知: {result}", []

        except Exception as e:
            logger.error(f"[图片审查] 内置提供商审查失败: {e}", exc_info=True)
            return True, f"审查出错: {e}", []
        finally:
            # 清理临时文件
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    logger.debug(f"[图片审查] 已删除临时文件: {temp_path}")
                except Exception as e:
                    logger.warning(f"[图片审查] 删除临时文件失败: {e}")
    
    async def moderate_with_openai(self, img: Image.Image, api_key: str, 
                                    api_base: str, model: str,
                                    prompt: str = None) -> tuple:
        """使用 OpenAI Compatible API 进行图片审查"""
        try:
            img_base64 = ImageUtils.image_to_base64(img)
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # 使用传入的提示词或默认提示词
            use_prompt = prompt or self.get_moderation_prompt()
            
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": use_prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}}
                        ]
                    }
                ],
                "max_tokens": 200  # 增加以容纳坐标输出
            }
            
            async with aiohttp.ClientSession() as session:
                url = f"{api_base.rstrip('/')}/chat/completions"
                async with session.post(url, json=payload, headers=headers,
                                        timeout=aiohttp.ClientTimeout(total=60),
                                        proxy=self.proxy) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        return True, f"API 请求失败: {resp.status} - {error_text}", []
                    
                    data = await resp.json()
                    result = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    result_upper = result.strip().upper()
                    
                    if "PASS" in result_upper:
                        return True, "审查通过", []
                    elif "REJECT" in result_upper:
                        # 尝试解析边界框坐标
                        bboxes = self._parse_bboxes(result)
                        if bboxes:
                            logger.warning(f"[图片审查] 图片不适宜，检测到 {len(bboxes)} 个区域需要打码")
                            return False, "图片内容不适宜", bboxes
                        else:
                            return False, "图片内容不适宜", []
                    else:
                        logger.warning(f"审查结果无法解析: {result}")
                        return True, f"审查结果未知: {result}", []
                        
        except Exception as e:
            logger.error(f"OpenAI Compatible API 审查失败: {e}")
            return True, f"审查出错: {e}", []
    
    async def moderate(self, img: Image.Image) -> tuple:
        """执行图片审查
        
        Returns:
            tuple: (passed: bool, message: str, bboxes: list)
            - passed: True 表示通过，False 表示不通过或需要打码
            - message: 状态描述
            - bboxes: 需要打码的区域列表（仅在打码模式下有值）
        """
        logger.info(f"[图片审查] 开始审查，配置: {self.config}")

        if not self.is_enabled():
            logger.info("[图片审查] 审查未启用")
            return True, "审查未启用", []

        provider_type = self.config.get("provider_type", "builtin")
        failed_action = self.get_failed_action()
        
        # 判断是否使用打码模式
        use_mosaic = failed_action == "mosaic"
        prompt = self.get_mosaic_prompt() if use_mosaic else self.get_moderation_prompt()
        
        logger.info(f"[图片审查] 使用提供商类型: {provider_type}, 打码模式: {use_mosaic}")
        
        if provider_type == "builtin":
            provider_id = self.config.get("builtin_provider_id", "")
            logger.info(f"[图片审查] 内置提供商ID: {provider_id}")
            if not provider_id:
                logger.warning("[图片审查] 未配置内置提供商ID")
                return True, "未配置内置提供商ID", []
            logger.info(f"[图片审查] 调用内置提供商审查: {provider_id}")
            result = await self.moderate_with_builtin(img, provider_id, prompt)
            logger.info(f"[图片审查] 审查结果: {result}")
            return result
        
        elif provider_type == "openai_compatible":
            api_key = self.config.get("openai_api_key", "")
            api_base = self.config.get("openai_api_base", "https://api.openai.com/v1")
            model = self.config.get("openai_model", "gpt-4o")

            logger.info(f"[图片审查] OpenAI Compatible API配置 - base: {api_base}, model: {model}")
            if not api_key:
                logger.warning("[图片审查] 未配置 OpenAI API Key")
                return True, "未配置 OpenAI API Key", []

            result = await self.moderate_with_openai(img, api_key, api_base, model, prompt)
            logger.info(f"[图片审查] 审查结果: {result}")
            return result

        else:
            logger.error(f"[图片审查] 未知的提供商类型: {provider_type}")
            return True, f"未知的提供商类型: {provider_type}", []
    
    async def moderate_and_mosaic(self, img: Image.Image) -> tuple:
        """执行图片审查，如果不适宜则打码处理
        
        Returns:
            tuple: (processed_img: Image.Image, passed: bool, message: str)
            - processed_img: 处理后的图片（可能已打码）
            - passed: True 表示原图通过，False 表示已打码
            - message: 状态描述
        """
        passed, message, bboxes = await self.moderate(img)
        
        if passed:
            return img, True, message
        
        if not bboxes:
            # 没有坐标，无法打码
            return img, False, message
        
        # 应用马赛克
        block_size = self.get_mosaic_block_size()
        processed_img = ImageUtils.apply_mosaic_multi(img, bboxes, block_size)
        logger.info(f"[图片审查] 已对 {len(bboxes)} 个区域应用马赛克")
        
        return processed_img, False, f"已对 {len(bboxes)} 个不适宜区域打码处理"
