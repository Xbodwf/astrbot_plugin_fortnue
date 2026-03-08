"""
今日运势插件 - AstrBot 插件
生成精美的运势图片
"""
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register, StarTools
from astrbot.api import logger
import asyncio
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor

from .config import ConfigLoader
from .core import BackgroundManager, FortuneGenerator, ImageModerator
from .utils import ImageUtils


@register("astrbot_plugin_fortnue", "Xbodw", "今日运势生成器 - 生成一张二次元风格的运势图片", "1.30.0")
class FortunePlugin(Star):
    """今日运势插件 - 生成精美的运势图片"""
    
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.config = config  # 保存配置
        self.data_dir = os.path.dirname(os.path.abspath(__file__))
        self.backgrounds_path = os.path.join(self.data_dir, "backgrounds.json")

        # 加载配置
        self.backgrounds_data = ConfigLoader.load_backgrounds(self.backgrounds_path)

        # 初始化各模块
        self.fortune_generator = FortuneGenerator(self.data_dir)

        # 用户数据
        self.user_last_backgrounds = {}

        logger.info(f"[插件初始化] 收到的 config 参数: {config}")
    
    def _get_source_name_from_spec(self, bg_spec, bg_manager) -> str | None:
        """从背景规格中提取图源名称

        Args:
            bg_spec: 背景图片规格
            bg_manager: 背景管理器

        Returns:
            图源名称，如果无法确定则返回 None
        """
        if not bg_spec:
            return None

        # 遍历所有图源，找到匹配的
        for source_name, source_data in bg_manager.backgrounds_data.items():
            # 如果 bg_spec 是字符串
            if isinstance(bg_spec, str):
                if isinstance(source_data, list) and bg_spec in source_data:
                    return source_name
                if isinstance(source_data, str) and bg_spec == source_data:
                    return source_name
                if isinstance(source_data, dict):
                    items = source_data.get("items") or source_data.get("urls") or []
                    if isinstance(items, list) and bg_spec in items:
                        return source_name

            # 如果 bg_spec 是字典（API 类型）
            elif isinstance(bg_spec, dict):
                if source_data == bg_spec:
                    return source_name

        return None

    def _get_config(self) -> dict:
        """获取插件配置"""
        # 优先使用 __init__ 接收的 config 参数
        if hasattr(self, "config") and self.config:
            logger.info(f"[配置加载] 从 self.config 获取配置")
            return self.config

        # 尝试从 context 获取配置
        if hasattr(self.context, "get_config") and callable(self.context.get_config):
            try:
                config = self.context.get_config()
                if config:
                    logger.info(f"[配置加载] 从 context.get_config() 获取配置成功")
                    return config
            except Exception as e:
                logger.warning(f"[配置加载] 从 context.get_config() 获取配置失败: {e}")

        logger.warning(f"[配置加载] 未找到任何配置，返回空字典")
        return {}
    
    def _get_proxy(self) -> str | None:
        """获取代理配置"""
        return ConfigLoader.get_proxy(self._get_config())
    
    def _get_background_manager(self) -> BackgroundManager:
        """获取背景管理器"""
        fortune_config = ConfigLoader.get_fortune_config(self._get_config())
        return BackgroundManager(self.backgrounds_data, fortune_config, self._get_proxy())
    
    def _get_moderator(self) -> ImageModerator:
        """获取图片审查器"""
        config = self._get_config()
        logger.info(f"[插件配置] 完整配置: {config}")
        moderation_config = ConfigLoader.get_moderation_config(config)
        logger.info(f"[插件配置] 图片审查配置: {moderation_config}")
        moderator = ImageModerator(moderation_config, self.context, self._get_proxy())
        logger.info(f"[插件配置] 审查器已创建，启用状态: {moderator.is_enabled()}")
        return moderator
    
    async def _get_avatar_url(self, event: AstrMessageEvent) -> str:
        """获取用户头像URL"""
        user_id = event.get_sender_id()
        return f"https://q1.qlogo.cn/g?b=qq&nk={user_id}&s=640"
    
    async def _handle_none_generation(self, event: AstrMessageEvent, source_name: str = None):
        """处理纯背景图片获取逻辑"""
        moderator = self._get_moderator()
        max_retries = moderator.get_max_retries() if moderator.is_enabled() else 0
        
        retries = 0
        last_error = None
        
        while retries <= max_retries:
            try:
                bg_manager = self._get_background_manager()
                bg_spec = bg_manager.get_background_spec(source_name)
                
                if not bg_spec:
                    if source_name:
                        yield event.plain_result(f"未找到指定的图源: {source_name}")
                    else:
                        yield event.plain_result("暂无背景图源配置，请检查 backgrounds.json~")
                    return

                background, _ = await bg_manager.get_background_and_addition(bg_spec)
                
                if not background:
                    raise Exception("无法加载背景图片")
                
                # 图片审查
                if moderator.is_enabled():
                    logger.info(f"[运势生成] 开始图片审查，重试次数: {retries}/{max_retries}")
                    passed, reason = await moderator.moderate(background)
                    logger.info(f"[运势生成] 审查结果: passed={passed}, reason={reason}")
                    if not passed:
                        logger.warning(f"图片审查未通过: {reason}, 重试中...")
                        retries += 1
                        last_error = f"图片审查未通过: {reason}"
                        continue
                else:
                    logger.info("[运势生成] 图片审查未启用")
                
                result_image = ImageUtils.process_background(background)
                
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                    result_image.save(f, format="JPEG", quality=95)
                    temp_path = f.name
                
                try:
                    yield event.image_result(temp_path)
                finally:
                    try:
                        os.remove(temp_path)
                    except:
                        pass
                return
                    
            except Exception as e:
                logger.error(f"获取背景图片失败: {e}")
                last_error = str(e)
                retries += 1
        
        yield event.plain_result(f"获取失败: {last_error or '重试次数已达上限'}")

    async def _handle_fortune_generation(self, event: AstrMessageEvent, source_name: str = None):
        """处理运势图片生成逻辑"""
        user_id = event.get_sender_id()
        user_name = event.get_sender_name()

        moderator = self._get_moderator()
        max_retries = moderator.get_max_retries() if moderator.is_enabled() else 0
        failed_action = moderator.get_failed_action() if moderator.is_enabled() else "retry_same"

        retries = 0
        last_error = None
        current_source = source_name
        tried_sources = set()  # 记录已尝试的图源

        while retries <= max_retries:
            try:
                bg_manager = self._get_background_manager()

                # 如果是切换图源模式且已经尝试过当前图源，则选择新图源
                if failed_action == "switch_source" and current_source and current_source in tried_sources:
                    logger.info(f"[运势生成] 切换图源模式 - 已尝试过 {current_source}，选择新图源")
                    current_source = None  # 让系统随机选择

                bg_spec = bg_manager.get_background_spec(current_source)

                if not bg_spec:
                    if source_name:
                        yield event.plain_result(f"未找到指定的图源: {source_name}")
                    else:
                        yield event.plain_result("暂无背景图源配置，请检查 backgrounds.json~")
                    return

                # 获取实际使用的图源名称
                actual_source = self._get_source_name_from_spec(bg_spec, bg_manager)
                if actual_source:
                    tried_sources.add(actual_source)
                    logger.info(f"[运势生成] 使用图源: {actual_source}")

                background, addition_text = await bg_manager.get_background_and_addition(bg_spec)

                if not background:
                    raise Exception("无法加载背景图片")

                # 图片审查 - 检查是否需要审核此图源
                if moderator.is_enabled() and actual_source:
                    should_moderate = moderator.should_moderate_source(actual_source)

                    if should_moderate:
                        logger.info(f"[运势生成] 图源 {actual_source} 需要审核，开始图片审查，重试次数: {retries}/{max_retries}")
                        passed, reason = await moderator.moderate(background)
                        logger.info(f"[运势生成] 审查结果: passed={passed}, reason={reason}")

                        if not passed:
                            logger.warning(f"图片审查未通过: {reason}")
                            retries += 1
                            last_error = f"图片审查未通过: {reason}"

                            # 根据配置的失败行为处理
                            if failed_action == "notify_user":
                                yield event.plain_result(f"背景图因审查不通过无法生成运势\n原因: {reason}")
                                return
                            elif failed_action == "switch_source":
                                logger.info(f"[运势生成] 失败行为: 切换图源")
                                current_source = None  # 下次循环会选择新图源
                            else:  # retry_same
                                logger.info(f"[运势生成] 失败行为: 从同一图源重新取图")

                            continue
                    else:
                        logger.info(f"[运势生成] 图源 {actual_source} 在过滤列表中，跳过审核")
                else:
                    logger.info("[运势生成] 图片审查未启用或无法确定图源")

                self.user_last_backgrounds[user_id] = background.copy()

                # 获取头像
                avatar_url = await self._get_avatar_url(event)
                try:
                    from .utils import HttpUtils
                    avatar = await HttpUtils.download_image(avatar_url, timeout=10, proxy=self._get_proxy())
                except Exception as e:
                    logger.warning(f"下载头像失败: {e}，将使用默认空白头像")
                    from PIL import Image
                    avatar = Image.new('RGB', (100, 100), (200, 200, 200))

                fortune_data = self.fortune_generator.get_fortune_for_user(user_id)

                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as executor:
                    result_image = await loop.run_in_executor(
                        executor,
                        self.fortune_generator.create_fortune_image,
                        background, avatar, user_name, fortune_data, addition_text
                    )

                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                    result_image.save(f, format="JPEG", quality=90)
                    temp_path = f.name

                try:
                    yield event.image_result(temp_path)
                finally:
                    try:
                        os.remove(temp_path)
                    except:
                        pass
                return

            except Exception as e:
                logger.error(f"生成运势图片失败: {e}")
                last_error = str(e)
                retries += 1
        
        yield event.plain_result(f"生成失败: {last_error or '重试次数已达上限'}")

    @filter.command("jrys", alias=["今日运势", "运势"])
    async def jrys_cmd(self, event: AstrMessageEvent):
        """生成今日运势图片"""
        async for res in self._handle_fortune_generation(event):
            yield res

    @filter.command("jrysn")
    async def jrysn(self, event: AstrMessageEvent):
        """随机从图源中获取一张背景图 (无运势信息)"""
        async for res in self._handle_none_generation(event):
            yield res

    @filter.command_group("jrysl")
    async def jrysl(self, event: AstrMessageEvent):
        """今日运势管理指令组"""
        pass

    @jrysl.command("source")
    async def source(self, event: AstrMessageEvent, source_name: str):
        """从指定的图源加载图片生成今日运势"""
        async for res in self._handle_fortune_generation(event, source_name=source_name):
            yield res

    @jrysl.command("last")
    async def last(self, event: AstrMessageEvent):
        """获取上一次今日运势的原始背景图片（无运势信息）"""
        user_id = event.get_sender_id()
        if user_id not in self.user_last_backgrounds:
            yield event.plain_result("你还没有生成过今日运势，请先使用 /jrys 生成一次~")
            return
            
        try:
            background = self.user_last_backgrounds[user_id]
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                result_image = await loop.run_in_executor(executor, ImageUtils.process_background, background)
            
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                result_image.save(f, format="JPEG", quality=95)
                temp_path = f.name
            
            try:
                yield event.image_result(temp_path)
            finally:
                try:
                    os.remove(temp_path)
                except:
                    pass
        except Exception as e:
            logger.error(f"获取上次背景图片失败: {e}")
            yield event.plain_result(f"获取失败: {e}")

    @jrysl.group("none")
    async def none(self, event: AstrMessageEvent):
        """单独从图源中刷图（无运势信息）"""
        pass

    @none.command("source")
    async def none_source(self, event: AstrMessageEvent, source_name: str):
        """从指定的图源单独刷图（无运势信息）"""
        async for res in self._handle_none_generation(event, source_name=source_name):
            yield res