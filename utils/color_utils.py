"""颜色处理工具模块"""
from astrbot.api import logger

try:
    from colornamer import get_color_from_rgb
except:
    get_color_from_rgb = None

try:
    import webcolors
except ImportError:
    webcolors = None


class ColorUtils:
    """颜色处理工具类"""
    
    @staticmethod
    def english_color_name_from_rgb(rgb: tuple) -> str:
        """从RGB获取英文颜色名"""
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
    
    @staticmethod
    def zh_color_name_from_en(en_name: str) -> str:
        """从英文颜色名获取中文颜色名"""
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
        
        return "彩色"
    
    @staticmethod
    def get_color_name(rgb: tuple) -> str:
        """根据RGB值范围获取颜色名"""
        r, g, b = rgb
        
        # 计算亮度
        brightness = (r + g + b) / 3
        
        # 黑、白、灰
        if brightness < 30:
            return "黑色"
        elif brightness > 240 and max(r, g, b) - min(r, g, b) < 30:
            return "白色"
        elif max(abs(r - g), abs(g - b), abs(b - r)) < 20:
            return "灰色"
        
        # 计算主色调
        max_val = max(r, g, b)
        min_val = min(r, g, b)
        delta = max_val - min_val
        
        # 计算色相
        if delta == 0:
            h = 0
        elif max_val == r:
            h = 60 * (((g - b) / delta) % 6)
        elif max_val == g:
            h = 60 * (((b - r) / delta) + 2)
        else:
            h = 60 * (((r - g) / delta) + 4)
        
        h = h % 360
        
        # 计算饱和度
        if max_val == 0:
            s = 0
        else:
            s = delta / max_val * 100
        
        # 根据色相和饱和度确定颜色
        if s < 20:
            return "灰色"
        elif h < 15 or h >= 345:
            if s > 70 and r > 200 and g < 100 and b < 100:
                return "正红色"
            elif r > 200 and g > 150 and b > 150:
                return "粉红色"
            return "红色"
        elif 15 <= h < 45:
            return "橙色"
        elif 45 <= h < 75:
            return "黄色"
        elif 75 <= h < 165:
            if max_val < 100:
                return "深绿色"
            return "绿色"
        elif 165 <= h < 195:
            return "青色"
        elif 195 <= h < 255:
            if max_val < 100:
                return "深蓝色"
            return "蓝色"
        elif 255 <= h < 285:
            return "紫色"
        else:
            return "品红色"
    
    @staticmethod
    def get_random_hex_color() -> dict:
        """生成随机的十六进制颜色"""
        import random
        r = random.randint(0, 255)
        g = random.randint(0, 255)
        b = random.randint(0, 255)
        hex_color = f"#{r:02x}{g:02x}{b:02x}".upper()

        lib_name_zh = ColorUtils.zh_color_name_from_en(
            ColorUtils.english_color_name_from_rgb((r, g, b))
        )
        final_name = lib_name_zh if lib_name_zh and lib_name_zh != "彩色" else ColorUtils.get_color_name((r, g, b))

        return {
            "name": final_name,
            "hex": hex_color,
            "rgb": [r, g, b]
        }
