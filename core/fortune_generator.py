"""运势生成模块"""
import random
import json
import os
from datetime import datetime
from astrbot.api import logger
from astrbot.api.star import StarTools
from PIL import Image, ImageDraw, ImageFont

try:
    from zhdate import ZhDate
except ImportError:
    ZhDate = None

from utils.color_utils import ColorUtils
from utils.image_utils import ImageUtils


LUCKY_NUMBERS = [0, 1, 2, 3, 5, 6, 7, 8, 9]
FESTIVE_MIN_LUCK = 70


class FortuneGenerator:
    """运势生成器"""
    
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.yunshi_data_path = StarTools.get_data_dir("astrbot_plugin_fortnue") / "yunshi.json"
        self.user_fortune_data = self._load_yunshi_data()
    
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
    
    def _load_fortune_data(self) -> dict:
        """加载运势数据"""
        fortune_data_path = os.path.join(self.data_dir, "fortune_data.json")
        try:
            with open(fortune_data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for level, fortunes in data.items():
                    for fortune in fortunes:
                        if "color" in fortune and isinstance(fortune["color"], str):
                            hex_color = fortune["color"].lstrip('#')
                            fortune["color"] = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                return data
        except Exception as e:
            logger.error(f"加载运势数据失败: {e}")
            return {}
    
    def _is_festive_day(self, dt: datetime) -> bool:
        """判断是否为重大节假日"""
        if dt.month == 1 and dt.day == 1:
            return True
        
        if ZhDate:
            try:
                lunar = ZhDate.from_datetime(dt)
                if lunar.l_month == 1 and lunar.l_day == 1:
                    return True
                if lunar.l_month == 1 and lunar.l_day == 15:
                    return True
                if lunar.l_month == 5 and lunar.l_day == 5:
                    return True
                if lunar.l_month == 8 and lunar.l_day == 15:
                    return True
            except Exception:
                pass
                
        return False
    
    def get_fortune_for_user(self, user_id: str) -> dict:
        """获取用户运势数据"""
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
                    "color": (144, 238, 144)
                },
                "lucky_color": ColorUtils.get_random_hex_color(),
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
        
        lucky_color = ColorUtils.get_random_hex_color()
        lucky_number = rng.choice(LUCKY_NUMBERS)
        advice = fortune.get('advice', '今天适合：保持好心情')
        
        result_data = {
            "fortune": {
                "level": fortune["level"],
                "desc": fortune["desc"],
                "color": fortune.get("color", (255, 255, 255))
            },
            "lucky_color": lucky_color,
            "lucky_number": lucky_number,
            "advice": advice,
            "luck_value": int(selected_level)
        }
        
        self.user_fortune_data[user_id] = {
            "date": today_str,
            "fortune_data": result_data
        }
        self._save_yunshi_data()
        
        return result_data
    
    def create_fortune_image(self, background: Image.Image, avatar: Image.Image | None,
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
        
        # 加载字体
        try:
            font_path = os.path.join(self.data_dir, "fonts", "千图马克手写体.ttf")
            if not os.path.exists(font_path):
                font_path = os.path.join(self.data_dir, "fonts", "1.ttf")
            
            font_large = ImageFont.truetype(font_path, 72)
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
        
        content_start_y = target_height - 520
        
        avatar_size = 150
        avatar_x = 50
        avatar_y = content_start_y
        
        if avatar:
            circle_avatar = ImageUtils.make_circle_image(avatar, (avatar_size, avatar_size))
            bordered_avatar = ImageUtils.add_avatar_border(circle_avatar, 5, (255, 255, 255))
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
            fill=tuple(lucky_color['rgb'])
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
