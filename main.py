from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register, StarTools
from astrbot.api import logger
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import aiohttp
from io import BytesIO
from datetime import datetime
import random
import json
import os
import tempfile
import ssl
import asyncio
from concurrent.futures import ThreadPoolExecutor
try:
    from colornamer import get_color_from_rgb
except:
    get_color_from_rgb = None
try:
    from zhdate import ZhDate
except ImportError:
    ZhDate = None
try:
    import webcolors
except ImportError:
    webcolors = None


LUCKY_NUMBERS = [0, 1, 2, 3, 5, 6, 7, 8, 9]
FESTIVE_MIN_LUCK = 70


@register("astrbot_plugin_fortnue", "Xbodw", "今日运势生成器 - 生成一张二次元风格的运势图片", "1.25.0")
class FortunePlugin(Star):
    """今日运势插件 - 生成精美的运势图片"""
    
    def __init__(self, context: Context):
        super().__init__(context)
        self.data_dir = os.path.dirname(os.path.abspath(__file__))
        self.backgrounds_path = os.path.join(self.data_dir, "backgrounds.json")
        self.yunshi_data_path = StarTools.get_data_dir("astrbot_plugin_fortnue") / "yunshi.json"
        self.backgrounds_data = self._load_backgrounds()
        self.user_last_backgrounds = {}
        self.user_fortune_data = self._load_yunshi_data()
        
    def _get_proxy(self) -> str | None:
        """从配置获取代理地址"""
        if hasattr(self, "config") and self.config:
            proxy = self.config.get("fortune_config", {}).get("proxy")
            return proxy if proxy else None
        return None
        
    def _load_backgrounds(self) -> dict:
        """加载背景图片配置"""
        try:
            with open(self.backgrounds_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载背景图片配置失败: {e}")
            return {}
    
    def _load_yunshi_data(self) -> dict:
        """加载用户运势数据"""
        try:
            if os.path.exists(self.yunshi_data_path):
                with open(self.yunshi_data_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"加载运势数据失败: {e}")
        return {}
    
    def _save_yunshi_data(self):
        """保存用户运势数据到文件"""
        try:
            with open(self.yunshi_data_path, "w", encoding="utf-8") as f:
                json.dump(self.user_fortune_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存运势数据失败: {e}")
    
    def _get_background_spec(self, source_name: str = None) -> str | dict:
        if not self.backgrounds_data:
            return ""
        
        # 如果指定了图源名称
        if source_name:
            if source_name in self.backgrounds_data:
                chosen = self.backgrounds_data[source_name]
                if isinstance(chosen, list) and len(chosen) > 0:
                    return random.choice(chosen)
                if isinstance(chosen, str) and chosen:
                    return chosen
                if isinstance(chosen, dict):
                    t = chosen.get("type")
                    if t == "array":
                        items = chosen.get("items") or chosen.get("urls") or []
                        if isinstance(items, list) and len(items) > 0:
                            return random.choice(items)
                    if t == "api":
                        return chosen
            return "" # 指定图源不存在或无效

        # 未指定图源，随机选择
        source_keys = []
        for k, v in self.backgrounds_data.items():
            if isinstance(v, list) and len(v) > 0:
                source_keys.append(k)
            elif isinstance(v, str) and v:
                source_keys.append(k)
            elif isinstance(v, dict) and v.get("type"):
                t = v.get("type")
                if t == "array":
                    items = v.get("items") or v.get("urls") or []
                    if isinstance(items, list) and len(items) > 0:
                        source_keys.append(k)
                elif t == "api":
                    if isinstance(v.get("url"), str) and v.get("url"):
                        source_keys.append(k)
        
        if not source_keys:
            return ""
            
        chosen_key = random.choice(source_keys)
        chosen = self.backgrounds_data.get(chosen_key)
        
        if isinstance(chosen, list) and len(chosen) > 0:
            return random.choice(chosen)
        if isinstance(chosen, str) and chosen:
            return chosen
        if isinstance(chosen, dict):
            t = chosen.get("type")
            if t == "array":
                items = chosen.get("items") or chosen.get("urls") or []
                if isinstance(items, list) and len(items) > 0:
                    return random.choice(items)
            if t == "api":
                return chosen
        return ""
    
    def _extract_token_value(self, obj, token: str):
        if not isinstance(token, str) or not token:
            return obj
        parts = [p for p in token.split(".") if p]
        cur = obj
        for p in parts:
            if isinstance(cur, list):
                if len(cur) == 0:
                    return None
                # 支持数字索引
                if p.isdigit():
                    idx = int(p)
                    if 0 <= idx < len(cur):
                        cur = cur[idx]
                        continue # 消耗掉该 part，进入下一个
                # 兼容原有的随机选择逻辑
                cur = random.choice(cur)
            
            if isinstance(cur, dict):
                if p in cur:
                    cur = cur[p]
                else:
                    return None
            else:
                return None
        return cur
    
    async def _resolve_api_image_url(self, spec: dict, timeout: int = 15):
        url = spec.get("url")
        method = str(spec.get("method", "get")).lower()
        expected = str(spec.get("expected", "url")).lower()
        headers = spec.get("headers") or {}
        addition_tmpl = spec.get("addition")
        base_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        req_headers = {**base_headers, **headers} if isinstance(headers, dict) else base_headers
        proxy = self._get_proxy()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method.upper(), url, 
                                         timeout=aiohttp.ClientTimeout(total=timeout), 
                                         headers=req_headers,
                                         proxy=proxy) as resp:
                    if resp.status != 200:
                        raise Exception(f"API请求失败 (HTTP {resp.status} {resp.reason})")
                    
                    if expected == "image":
                        data = await resp.read()
                        try:
                            img = Image.open(BytesIO(data))
                        except Exception as e:
                            raise Exception(f"API返回的图片解析失败: {e}")
                        
                        addition_text = ""
                        if addition_tmpl:
                            addition_text = addition_tmpl 
                        return img, addition_text
                    
                    try:
                        js = await resp.json()
                    except Exception as e:
                        raise Exception(f"API返回格式非JSON: {e}")
                    
                    token = spec.get("token") or ""
                    img_url = url
                    if isinstance(js, dict) and token:
                        val = self._extract_token_value(js, token)
                        if isinstance(val, str):
                            img_url = val
                        elif isinstance(val, list) and len(val) > 0 and isinstance(val[0], str):
                            img_url = random.choice(val)
                        else:
                            raise Exception(f"Token '{token}' 未能解析到有效的图片URL路径")
                    
                    addition_text = ""
                    if addition_tmpl and isinstance(js, dict):
                        # Simple template parsing: {data.pid} -> js['data']['pid']
                        import re
                        def _repl(match):
                            path = match.group(1)
                            v = self._extract_token_value(js, path)
                            return str(v) if v is not None else match.group(0)
                        addition_text = re.sub(r"\{(.*?)\}", _repl, addition_tmpl)
                    
                    return img_url, addition_text
        except asyncio.TimeoutError:
            raise Exception("API请求超时")
        except Exception as e:
            logger.error(f"解析API图片失败 {url}: {e}")
            raise e
    
    async def _download_image(self, url: str, timeout: int = 15) -> Image.Image:
        """异步下载图片"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        proxy = self._get_proxy()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout), 
                                       headers=headers, proxy=proxy) as resp:
                    if resp.status != 200:
                        raise Exception(f"HTTP {resp.status} {resp.reason}")
                    data = await resp.read()
                    try:
                        return Image.open(BytesIO(data))
                    except Exception as e:
                        raise Exception(f"图片格式解析失败: {e}")
        except asyncio.TimeoutError:
            raise Exception("请求超时")
        except Exception as e:
            if isinstance(e, Image.DecompressionBombError):
                raise Exception("图片过大，拒绝处理")
            raise e
    
    async def _get_avatar_url(self, event: AstrMessageEvent) -> str:
        """获取用户头像URL"""
        user_id = event.get_sender_id()
        return f"https://q1.qlogo.cn/g?b=qq&nk={user_id}&s=640"
    
    def _make_circle_image(self, img: Image.Image, size: tuple) -> Image.Image:
        """将图片裁剪成圆形"""
        img = img.resize(size, Image.Resampling.LANCZOS)
        mask = Image.new('L', size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse([0, 0, size[0], size[1]], fill=255)
        result = Image.new('RGBA', size, (0, 0, 0, 0))
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        result.paste(img, mask=mask)
        return result
    
    def _add_avatar_border(self, avatar: Image.Image, border_width: int = 4, 
                           border_color: tuple = (255, 255, 255)) -> Image.Image:
        """为圆形头像添加边框"""
        new_size = (avatar.width + border_width * 2, avatar.height + border_width * 2)
        bordered = Image.new('RGBA', new_size, (0, 0, 0, 0))
        
        mask = Image.new('L', new_size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse([0, 0, new_size[0], new_size[1]], fill=255)
        
        border_layer = Image.new('RGBA', new_size, border_color + (255,))
        bordered.paste(border_layer, mask=mask)
        bordered.paste(avatar, (border_width, border_width), avatar)
        return bordered
    
    def _load_fortune_data(self) -> dict:
        """加载运势数据"""
        fortune_data_path = os.path.join(self.data_dir, "fortune_data.json")
        try:
            with open(fortune_data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Convert hex colors to RGB tuples
                for level, fortunes in data.items():
                    for fortune in fortunes:
                        if "color" in fortune and isinstance(fortune["color"], str):
                            # Convert hex to RGB
                            hex_color = fortune["color"].lstrip('#')
                            fortune["color"] = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                return data
        except Exception as e:
            logger.error(f"加载运势数据失败: {e}")
            return {}
    
    def _english_color_name_from_rgb(self, rgb: tuple) -> str:
        r, g, b = rgb
        if get_color_from_rgb:
            try:
                info = get_color_from_rgb([r, g, b])
                name = info.get('xkcd_color') or info.get('common_color') or info.get('design_color')
                if isinstance(name, str):
                    return name.lower()
            except:
                pass
        if webcolors:
            try:
                return webcolors.rgb_to_name((r, g, b)).lower()
            except:
                pass
        return ""
        
    def _zh_color_name_from_en(self, en_name: str) -> str:
        if not en_name:
            return "彩色"
        s = en_name.replace('-', ' ').strip()
        tokens = s.split()
        adj = ""
        base = ""
        phrase = " ".join(tokens)
        if "sky blue" in phrase:
            base = "天蓝色"
        elif "navy" in tokens:
            base = "海军蓝"
        elif "azure" in tokens or "cerulean" in tokens:
            base = "蔚蓝色"
        elif "aquamarine" in tokens:
            base = "碧绿色"
        elif "teal" in tokens:
            base = "水鸭色"
        elif "fuchsia" in tokens or "magenta" in tokens:
            base = "洋红"
        elif "maroon" in tokens:
            base = "栗色"
        elif "brown" in tokens:
            base = "棕色"
        elif "blue" in tokens:
            base = "蓝色"
        elif "green" in tokens:
            base = "绿色"
        elif "red" in tokens:
            base = "红色"
        elif "orange" in tokens:
            base = "橙色"
        elif "yellow" in tokens:
            base = "黄色"
        elif "purple" in tokens or "violet" in tokens:
            base = "紫色"
        elif "pink" in tokens:
            base = "粉色"
        elif "cyan" in tokens:
            base = "青色"
        elif "grey" in tokens or "gray" in tokens:
            base = "灰色"
        elif "black" in tokens:
            base = "黑色"
        elif "white" in tokens:
            base = "白色"
        if "light" in tokens:
            adj = "淡"
        elif "dark" in tokens or "deep" in tokens:
            adj = "深"
        elif "bright" in tokens:
            adj = "亮"
        elif "pale" in tokens:
            adj = "浅"
        if base:
            if base.startswith("天") and adj:
                return adj + base
            return (adj + base) if adj else base
        

        # webcolor不支持中文,只能硬编码...
        return "彩色"
        
    def _get_color_name(self, rgb: tuple) -> str:
        """Get color name based on RGB value ranges"""
        r, g, b = rgb
        
        # Calculate brightness
        brightness = (r + g + b) / 3
        
        # Black, white, or gray
        if brightness < 30:
            return "黑色"
        elif brightness > 240 and max(r,g,b) - min(r,g,b) < 30:
            return "白色"
        elif max(abs(r-g), abs(g-b), abs(b-r)) < 20:  # Similar values = gray
            return "灰色"
        
        # Calculate dominant color
        max_val = max(r, g, b)
        min_val = min(r, g, b)
        delta = max_val - min_val
        
        # Calculate hue
        if delta == 0:
            h = 0
        elif max_val == r:
            h = 60 * (((g - b) / delta) % 6)
        elif max_val == g:
            h = 60 * (((b - r) / delta) + 2)
        else:  # max_val == b
            h = 60 * (((r - g) / delta) + 4)
        
        # Normalize hue to 0-360
        h = h % 360
        
        # Calculate saturation
        if max_val == 0:
            s = 0
        else:
            s = delta / max_val * 100
        
        # Determine color based on hue and saturation
        if s < 20:  # Low saturation = gray
            return "灰色"
        elif h < 15 or h >= 345:  # Red
            if s > 70 and r > 200 and g < 100 and b < 100:
                return "正红色"
            elif r > 200 and g > 150 and b > 150:
                return "粉红色"
            return "红色"
        elif 15 <= h < 45:  # Orange
            return "橙色"
        elif 45 <= h < 75:  # Yellow
            return "黄色"
        elif 75 <= h < 165:  # Green
            if max_val < 100:
                return "深绿色"
            return "绿色"
        elif 165 <= h < 195:  # Cyan
            return "青色"
        elif 195 <= h < 255:  # Blue
            if max_val < 100:
                return "深蓝色"
            return "蓝色"
        elif 255 <= h < 285:  # Purple
            return "紫色"
        else:  # 285-345 Magenta
            return "品红色"
    
    def _get_random_hex_color(self) -> dict:
        """生成随机的十六进制颜色"""
        import random
        # Generate random RGB values
        r = random.randint(0, 255)
        g = random.randint(0, 255)
        b = random.randint(0, 255)
        hex_color = f"#{r:02x}{g:02x}{b:02x}".upper()

        # 先尝试正规库命名，若失败则回退到旧算法
        lib_name_zh = self._zh_color_name_from_en(self._english_color_name_from_rgb((r, g, b)))
        final_name = lib_name_zh if lib_name_zh and lib_name_zh != "彩色" else self._get_color_name((r, g, b))

        return {
            "name": final_name,
            "hex": hex_color,
            "rgb": [r, g, b]
        }
    
    def _is_festive_day(self, dt: datetime) -> bool:
        """判断是否为重大节假日 (元旦、春节、元宵、端午、中秋等)"""
        # 1. 元旦 (公历 1月1日)
        if dt.month == 1 and dt.day == 1:
            return True
        
        # 2. 农历节日 (使用 zhdate 计算)
        if ZhDate:
            try:
                lunar = ZhDate.from_datetime(dt)
                # 春节 (正月初一)
                if lunar.l_month == 1 and lunar.l_day == 1:
                    return True
                # 元宵节 (正月十五)
                if lunar.l_month == 1 and lunar.l_day == 15:
                    return True
                # 端午节 (五月初五)
                if lunar.l_month == 5 and lunar.l_day == 5:
                    return True
                # 中秋节 (八月十五)
                if lunar.l_month == 8 and lunar.l_day == 15:
                    return True
            except Exception:
                pass
                
        return False
        
    def _get_fortune_for_user(self, user_id: str) -> dict:
        today_dt = datetime.now()
        today_str = today_dt.strftime("%Y-%m-%d")
        
        if user_id in self.user_fortune_data:
            user_data = self.user_fortune_data[user_id]
            if user_data.get("date") == today_str:
                if self._is_festive_day(today_dt):
                    fd = user_data["fortune_data"]
                    if fd.get("luck_value", 0) >= FESTIVE_MIN_LUCK:
                        return fd
                else:
                    return user_data["fortune_data"]
        
        fortune_data = self._load_fortune_data()
        if not fortune_data:
            return {
                "fortune": {
                    "level": "中吉", 
                    "desc": "平稳安康，小有收获", 
                    "color": (144, 238, 144)  # Light green
                },
                "lucky_color": self._get_random_hex_color(),
                "lucky_number": random.choice(LUCKY_NUMBERS),
                "advice": "今天适合：读书学习、整理房间",
                "luck_value": 70
            }
        
        seed = f"{user_id}-{today_str}"
        rng = random.Random(seed)
        
        luck_levels = list(fortune_data.keys())
        if self._is_festive_day(today_dt):
            luck_levels = [lvl for lvl in luck_levels if int(lvl) >= FESTIVE_MIN_LUCK] or luck_levels
        selected_level = rng.choice(luck_levels)
        level_data = fortune_data[selected_level]
        fortune = rng.choice(level_data)
        
        lucky_color = self._get_random_hex_color()
        lucky_number = rng.choice(LUCKY_NUMBERS)
        advice = fortune.get('advice', '今天适合：保持好心情')
        
        result_data = {
            "fortune": {
                "level": fortune["level"],
                "desc": fortune["desc"],
                "color": fortune.get("color", (255, 255, 255))  # 使用JSON中定义的颜色，如果没有则使用白色
            },
            "lucky_color": lucky_color,
            "lucky_number": lucky_number,
            "advice": advice,
            "luck_value": int(selected_level)  # 使用选择的等级作为幸运值
        }
        
        self.user_fortune_data[user_id] = {
            "date": today_str,
            "fortune_data": result_data
        }
        self._save_yunshi_data()
        
        return result_data
    
    def _create_fortune_image(self, background: Image.Image, avatar: Image.Image | None,
                              user_name: str, fortune_data: dict, addition_text: str = "") -> Image.Image:
        """创建运势图片"""
        target_width = 800
        target_height = 1200
        
        # 处理背景图片
        bg_ratio = background.width / background.height
        target_ratio = target_width / target_height
        
        if bg_ratio > target_ratio:
            new_width = int(background.height * target_ratio)
            left = (background.width - new_width) // 2
            background = background.crop((left, 0, left + new_width, background.height))
        else:
            new_height = int(background.width / target_ratio)
            top = (background.height - new_height) // 2
            background = background.crop((0, top, background.width, top + new_height))
        
        background = background.resize((target_width, target_height), Image.Resampling.LANCZOS)
        
        if background.mode != 'RGBA':
            background = background.convert('RGBA')
        
        # 底部半透明遮罩
        overlay = Image.new('RGBA', (target_width, target_height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        gradient_start_y = target_height - 600
        for y in range(gradient_start_y, target_height):
            alpha = int(200 * (y - gradient_start_y) / (target_height - gradient_start_y))
            overlay_draw.rectangle([(0, y), (target_width, y + 1)], fill=(0, 0, 0, alpha))
        
        background = Image.alpha_composite(background, overlay)
        draw = ImageDraw.Draw(background)
        
        try:
            font_path = os.path.join(self.data_dir, "fonts", "千图马克手写体.ttf")
            if not os.path.exists(font_path):
                font_path = os.path.join(self.data_dir, "fonts", "1.ttf")
            
            font_large = ImageFont.truetype(font_path, 72) # 这里字号部分非功能更新则不需要动
            font_medium = ImageFont.truetype(font_path, 28)
            font_small = ImageFont.truetype(font_path, 28)
            font_tiny = ImageFont.truetype(font_path, 22)
        except (OSError, FileNotFoundError) as e:
            logger.warning(f"加载字体失败，使用默认字体: {e}")
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
            font_tiny = ImageFont.load_default()
        
        fortune = fortune_data["fortune"]
        lucky_color = fortune_data["lucky_color"]
        lucky_number = fortune_data["lucky_number"]
        advice = fortune_data["advice"]
        luck_value = fortune_data["luck_value"]
        
        fortune_color = fortune["color"]
        if isinstance(fortune_color, list):
            fortune_color = tuple(fortune_color)
        
        lucky_color_rgb = lucky_color["rgb"]
        if isinstance(lucky_color_rgb, list):
            lucky_color_rgb = tuple(lucky_color_rgb)
        
        content_start_y = target_height - 520
        
        avatar_size = 150
        avatar_x = 50
        avatar_y = content_start_y
        
        if avatar:
            circle_avatar = self._make_circle_image(avatar, (avatar_size, avatar_size))
            bordered_avatar = self._add_avatar_border(circle_avatar, 5, (255, 255, 255))
            background.paste(bordered_avatar, (avatar_x, avatar_y), bordered_avatar)
        
        name_x = avatar_x + avatar_size + 30
        name_y = avatar_y + 20
        draw.text((name_x, name_y), user_name, fill=(255, 255, 255), font=font_medium)
        
        date_str = datetime.now().strftime("%Y年%m月%d日")
        draw.text((name_x, name_y + 70), date_str, fill=(200, 200, 200), font=font_small)
        
        fortune_level = fortune["level"]
        
        bbox = draw.textbbox((0, 0), fortune_level, font=font_large)
        level_width = bbox[2] - bbox[0]
        level_x = target_width - level_width - 50
        level_y = content_start_y + 20
        
        draw.text((level_x + 4, level_y + 4), fortune_level, fill=(0, 0, 0, 128), font=font_large)
        draw.text((level_x, level_y), fortune_level, fill=fortune_color, font=font_large)
        
        desc_y = content_start_y + 180
        draw.text((50, desc_y), f"「{fortune['desc']}」", fill=(255, 255, 255), font=font_medium)
        
        bar_y = desc_y + 80
        bar_width = 400
        bar_height = 30
        bar_x = 50
        
        draw.text((bar_x, bar_y), f"幸运指数：{luck_value}%", fill=(200, 200, 200), font=font_small)
        
        bar_bg_y = bar_y + 55
        draw.rounded_rectangle([(bar_x, bar_bg_y), (bar_x + bar_width, bar_bg_y + bar_height)], 
                               radius=bar_height // 2, fill=(80, 80, 80))
        
        progress_width = int(bar_width * luck_value / 100)
        if progress_width > 0:
            draw.rounded_rectangle([(bar_x, bar_bg_y), (bar_x + progress_width, bar_bg_y + bar_height)], 
                                   radius=bar_height // 2, fill=fortune_color)
        
        tips_y = bar_bg_y + 55
        lucky_color_hex = lucky_color['hex'].upper()
        lucky_color_name = lucky_color['name']
        color_text = f"幸运色：{lucky_color_name}({lucky_color_hex})"
        
        color_block_size = 36
        color_block_x = 50
        color_block_y = tips_y
        
        draw.rounded_rectangle(
            [(color_block_x, color_block_y), 
             (color_block_x + color_block_size, color_block_y + color_block_size)],
            radius=8,
            fill=tuple(lucky_color['rgb'])  # 使用RGB元组
        )

        text_x = color_block_x + color_block_size + 10
        draw.text((text_x, tips_y), color_text, fill=(180, 180, 180), font=font_small)
        
        lucky_number_text = f"|  幸运数字：{lucky_number}"
        lucky_number_x = text_x + draw.textlength(color_text, font=font_small) + 10
        draw.text((lucky_number_x, tips_y), lucky_number_text, 
                 fill=(180, 180, 180), font=font_small)
        
        draw.text((50, tips_y + 55), advice, fill=(180, 180, 180), font=font_small)
        
        footer_text = "仅供娱乐 · 相信科学 · 请勿迷信"
        if addition_text:
            footer_text = f"{addition_text} | {footer_text}"
            
        bbox = draw.textbbox((0, 0), footer_text, font=font_tiny)
        footer_width = bbox[2] - bbox[0]
        footer_x = (target_width - footer_width) // 2
        draw.text((footer_x, target_height - 50), footer_text, fill=(120, 120, 120), font=font_tiny)
        
        return background.convert('RGB')
    
    def _process_background(self, bg: Image.Image) -> Image.Image:
        """处理背景图片（裁剪和缩放）"""
        target_width = 800
        target_height = 1200
        
        bg_ratio = bg.width / bg.height
        target_ratio = target_width / target_height
        
        if bg_ratio > target_ratio:
            new_width = int(bg.height * target_ratio)
            left = (bg.width - new_width) // 2
            bg = bg.crop((left, 0, left + new_width, bg.height))
        else:
            new_height = int(bg.width / target_ratio)
            top = (bg.height - new_height) // 2
            bg = bg.crop((0, top, bg.width, top + new_height))
        
        result_image = bg.resize((target_width, target_height), Image.Resampling.LANCZOS)
        
        if result_image.mode == 'RGBA':
            result_image = result_image.convert('RGB')
        return result_image

    async def _handle_none_generation(self, event: AstrMessageEvent, source_name: str = None):
        """处理纯背景图片获取逻辑"""
        try:
            bg_spec = self._get_background_spec(source_name)
            if not bg_spec:
                if source_name:
                    yield event.plain_result(f"未找到指定的图源: {source_name}")
                else:
                    yield event.plain_result("暂无背景图源配置，请检查 backgrounds.json~")
                return

            if isinstance(bg_spec, dict):
                resolved, _ = await self._resolve_api_image_url(bg_spec)
                if isinstance(resolved, Image.Image):
                    background = resolved
                else:
                    bg_url = resolved
                    logger.info(f"选取背景图片URL: {bg_url}")
                    background = await self._download_image(bg_url)
            else:
                bg_url = bg_spec
                logger.info(f"选取背景图片URL: {bg_url}")
                background = await self._download_image(bg_url)
            
            result_image = self._process_background(background)
            
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
            logger.error(f"获取背景图片失败: {e}")
            yield event.plain_result(f"获取失败: {e}")

    async def _handle_fortune_generation(self, event: AstrMessageEvent, source_name: str = None):
        user_id = event.get_sender_id()
        user_name = event.get_sender_name()
        
        try:
            bg_spec = self._get_background_spec(source_name)
            if not bg_spec:
                if source_name:
                    yield event.plain_result(f"未找到指定的图源: {source_name}")
                else:
                    yield event.plain_result("暂无背景图源配置，请检查 backgrounds.json~")
                return

            addition_text = ""
            if isinstance(bg_spec, dict):
                resolved, addition_text = await self._resolve_api_image_url(bg_spec)
                if isinstance(resolved, Image.Image):
                    background = resolved
                else:
                    bg_url = resolved
                    logger.info(f"选取背景图片URL: {bg_url}")
                    background = await self._download_image(bg_url)
            else:
                bg_url = bg_spec
                logger.info(f"选取背景图片URL: {bg_url}")
                background = await self._download_image(bg_url)
            
            self.user_last_backgrounds[user_id] = background.copy()
            
            avatar_url = await self._get_avatar_url(event)
            try:
                avatar = await self._download_image(avatar_url, timeout=10)
            except Exception as e:
                logger.warning(f"下载头像失败: {e}，将使用默认空白头像")
                avatar = Image.new('RGB', (100, 100), (200, 200, 200))
            
            fortune_data = self._get_fortune_for_user(user_id)
            
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                result_image = await loop.run_in_executor(executor, self._create_fortune_image, background, avatar, user_name, fortune_data, addition_text)
            
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
            
        except Exception as e:
            logger.error(f"生成运势图片失败: {e}")
            yield event.plain_result(f"生成失败: {e}")

    @filter.command("jrys", alias=["今日运势", "运势"])
    async def jrys_cmd(self, event: AstrMessageEvent):
        """生成今日运势图片"""
        async for res in self._handle_fortune_generation(event):
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
                result_image = await loop.run_in_executor(executor, self._process_background, background)
            
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
        async for res in self._handle_none_generation(event):
            yield res

    @none.command("source")
    async def none_source(self, event: AstrMessageEvent, source_name: str):
        """从指定的图源单独刷图（无运势信息）"""
        async for res in self._handle_none_generation(event, source_name=source_name):
            yield res
