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
    
    @staticmethod
    def apply_mosaic(img: Image.Image, bbox: tuple, block_size: int = 15) -> Image.Image:
        """
        对图片指定区域应用马赛克效果
        
        Args:
            img: PIL Image 对象
            bbox: 边界框 (x1, y1, x2, y2)，支持相对坐标(0-1)或绝对坐标
            block_size: 马赛克块大小（像素）
        
        Returns:
            处理后的 PIL Image 对象
        """
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        width, height = img.size
        x1, y1, x2, y2 = bbox
        
        # 判断是相对坐标还是绝对坐标
        if all(0 <= v <= 1 for v in bbox):
            x1 = int(x1 * width)
            y1 = int(y1 * height)
            x2 = int(x2 * width)
            y2 = int(y2 * height)
        
        # 边界检查
        x1 = max(0, min(int(x1), width))
        y1 = max(0, min(int(y1), height))
        x2 = max(0, min(int(x2), width))
        y2 = max(0, min(int(y2), height))
        
        if x1 >= x2 or y1 >= y2:
            return img
        
        # 复制图片以避免修改原图
        result = img.copy()
        pixels = result.load()
        
        # 应用马赛克效果
        for y in range(y1, y2, block_size):
            for x in range(x1, x2, block_size):
                # 计算当前块的范围
                block_x2 = min(x + block_size, x2)
                block_y2 = min(y + block_size, y2)
                
                # 计算块内平均颜色
                r_sum, g_sum, b_sum = 0, 0, 0
                count = 0
                for by in range(y, block_y2):
                    for bx in range(x, block_x2):
                        if bx < width and by < height:
                            r, g, b = pixels[bx, by][:3]
                            r_sum += r
                            g_sum += g
                            b_sum += b
                            count += 1
                
                if count > 0:
                    avg_r = r_sum // count
                    avg_g = g_sum // count
                    avg_b = b_sum // count
                    
                    # 用平均颜色填充整个块
                    for by in range(y, block_y2):
                        for bx in range(x, block_x2):
                            if bx < width and by < height:
                                pixels[bx, by] = (avg_r, avg_g, avg_b)
        
        return result
    
    @staticmethod
    def apply_mosaic_multi(img: Image.Image, bboxes: list, block_size: int = 15) -> Image.Image:
        """
        对多个区域应用马赛克效果
        
        Args:
            img: PIL Image 对象
            bboxes: 边界框列表 [(x1, y1, x2, y2), ...]
            block_size: 马赛克块大小
        
        Returns:
            处理后的 PIL Image 对象
        """
        result = img
        for bbox in bboxes:
            if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
                result = ImageUtils.apply_mosaic(result, bbox[:4], block_size)
        return result
