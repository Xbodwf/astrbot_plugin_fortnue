"""图片处理工具模块"""
from PIL import Image, ImageDraw
from io import BytesIO
import base64


class ImageUtils:
    """图片处理工具类"""
    
    @staticmethod
    def make_circle_image(img: Image.Image, size: tuple) -> Image.Image:
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
    
    @staticmethod
    def add_avatar_border(avatar: Image.Image, border_width: int = 4,
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
    
    @staticmethod
    def image_to_base64(img: Image.Image, quality: int = 85) -> str:
        """将图片转换为 base64 编码"""
        buffered = BytesIO()
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        img.save(buffered, format="JPEG", quality=quality)
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    @staticmethod
    def process_background(bg: Image.Image, target_width: int = 800, 
                           target_height: int = 1200) -> Image.Image:
        """处理背景图片（裁剪和缩放）"""
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
