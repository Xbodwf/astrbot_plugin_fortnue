"""背景图片管理模块"""
import random
import aiohttp
import asyncio
import re
from PIL import Image
from io import BytesIO
from astrbot.api import logger
from utils.http_utils import HttpUtils


class BackgroundManager:
    """背景图片管理器"""
    
    def __init__(self, backgrounds_data: dict, config: dict, proxy: str = None):
        self.backgrounds_data = backgrounds_data
        self.config = config
        self.proxy = proxy
    
    def _get_ignored_sources(self) -> list:
        """从配置获取忽略的图源列表"""
        return self.config.get("ignored_sources", [])
    
    def _get_source_weights(self) -> dict:
        """从配置获取图源权重映射"""
        weights = {}
        weight_list = self.config.get("source_weights", [])
        for item in weight_list:
            if isinstance(item, str) and ":" in item:
                parts = item.split(":", 1)
                if len(parts) == 2:
                    name = parts[0].strip()
                    try:
                        weight = float(parts[1].strip())
                        if weight > 0:
                            weights[name] = weight
                    except ValueError:
                        pass
        return weights
    
    def _weighted_choice(self, choices: list, weights: dict) -> str:
        """根据权重进行加权随机选择"""
        if not choices:
            return ""
        
        choice_weights = [weights.get(choice, 1.0) for choice in choices]
        total_weight = sum(choice_weights)
        
        if total_weight <= 0:
            return random.choice(choices)
        
        r = random.uniform(0, total_weight)
        cumsum = 0
        for choice, weight in zip(choices, choice_weights):
            cumsum += weight
            if r <= cumsum:
                return choice
        
        return choices[-1]
    
    def _extract_token_value(self, obj, token: str):
        """从JSON对象中提取token路径对应的值"""
        if not isinstance(token, str) or not token:
            return obj
        parts = [p for p in token.split(".") if p]
        cur = obj
        for p in parts:
            if isinstance(cur, list):
                if len(cur) == 0:
                    return None
                if p.isdigit():
                    idx = int(p)
                    if 0 <= idx < len(cur):
                        cur = cur[idx]
                        continue
                cur = random.choice(cur)
            
            if isinstance(cur, dict):
                if p in cur:
                    cur = cur[p]
                else:
                    return None
            else:
                return None
        return cur
    
    def get_background_spec(self, source_name: str = None, ignore_sources: bool = True) -> str | dict:
        """获取背景图片规格"""
        if not self.backgrounds_data:
            return ""
        
        # 指定图源
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
                    if t == "object":
                        return chosen
            return ""

        # 随机选择
        ignored = self._get_ignored_sources() if ignore_sources else []
        ignored_set = set(ignored) if ignored else set()
        source_weights = self._get_source_weights()
        
        source_keys = []
        for k, v in self.backgrounds_data.items():
            if k in ignored_set:
                continue
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
                elif t == "object":
                    if isinstance(v.get("sources"), list) and len(v.get("sources")) > 0:
                        source_keys.append(k)
        
        if not source_keys:
            return ""
        
        chosen_key = self._weighted_choice(source_keys, source_weights)
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
            if t == "object":
                return chosen
        return ""
    
    async def _resolve_api_image_url(self, spec: dict, timeout: int = 15):
        """解析API类型的图源URL"""
        url = spec.get("url")
        method = str(spec.get("method", "get")).lower()
        expected = str(spec.get("expected", "url")).lower()
        headers = spec.get("headers") or {}
        img_headers = spec.get("img_headers")
        addition_tmpl = spec.get("addition")
        
        base_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        req_headers = {**base_headers, **headers} if isinstance(headers, dict) else base_headers
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method.upper(), url,
                                         timeout=aiohttp.ClientTimeout(total=timeout),
                                         headers=req_headers,
                                         proxy=self.proxy) as resp:
                    if resp.status != 200:
                        raise Exception(f"API请求失败 (HTTP {resp.status} {resp.reason})")
                    
                    if expected == "image":
                        data = await resp.read()
                        try:
                            img = Image.open(BytesIO(data))
                        except Exception as e:
                            raise Exception(f"API返回的图片解析失败: {e}")
                        
                        addition_text = addition_tmpl or ""
                        return img, addition_text, img_headers
                    
                    try:
                        js = await resp.json()
                    except Exception as e:
                        raise Exception(f"API返回格式非JSON: {e}")
                    
                    token = spec.get("token") or ""
                    replacement = spec.get("replacement")
                    img_url = url
                    
                    if isinstance(js, dict) and token:
                        val = self._extract_token_value(js, token)
                        if isinstance(val, str):
                            img_url = val
                        elif isinstance(val, list) and len(val) > 0 and isinstance(val[0], str):
                            img_url = random.choice(val)
                        else:
                            raise Exception(f"Token '{token}' 未能解析到有效的图片URL路径")
                    
                    if replacement and isinstance(replacement, dict):
                        pattern = replacement.get("pattern")
                        repl = replacement.get("replace")
                        if pattern and repl:
                            try:
                                img_url = re.sub(pattern, repl, img_url)
                                logger.info(f"应用替换规则: {img_url}")
                            except Exception as e:
                                logger.error(f"正则替换失败: {e}")
                    
                    addition_text = ""
                    if addition_tmpl and isinstance(js, dict):
                        def _repl(match):
                            path = match.group(1)
                            v = self._extract_token_value(js, path)
                            return str(v) if v is not None else match.group(0)
                        addition_text = re.sub(r"\{(.*?)\}", _repl, addition_tmpl)
                    
                    return img_url, addition_text, img_headers
        except asyncio.TimeoutError:
            raise Exception("API请求超时")
        except Exception as e:
            logger.error(f"解析API图片失败 {url}: {e}")
            raise e

    async def _resolve_object_image(self, spec: dict):
        """处理 type: object 的图源"""
        sources = spec.get("sources")
        if not sources or not isinstance(sources, list):
            raise Exception("object 类型图源必须包含 sources 列表")
        
        source = random.choice(sources)
        img_headers = spec.get("img_headers")
        addition_tmpl = spec.get("addition")
        
        img_url = ""
        addition_vars = {}
        
        if isinstance(source, str):
            img_url = source
        elif isinstance(source, dict):
            img_url = source.get("url", "")
            addition_vars = source
        else:
            raise Exception(f"不支持的 source 类型: {type(source)}")
        
        if not img_url:
            raise Exception("无法从 source 中获取图片 URL")
            
        addition_text = ""
        if addition_tmpl:
            def _repl(match):
                key = match.group(1)
                return str(addition_vars.get(key, match.group(0)))
            addition_text = re.sub(r"\{(.*?)\}", _repl, addition_tmpl)
            
        return img_url, addition_text, img_headers

    async def get_background_and_addition(self, bg_spec: str | dict) -> tuple:
        """统一获取背景图片和附加文本的逻辑"""
        background = None
        addition_text = ""
        
        if isinstance(bg_spec, dict):
            spec_type = bg_spec.get("type", "api")
            if spec_type == "object":
                img_url, addition_text, img_headers = await self._resolve_object_image(bg_spec)
                background = await HttpUtils.download_image(img_url, headers=img_headers, proxy=self.proxy)
            else:
                resolved, addition_text, img_headers = await self._resolve_api_image_url(bg_spec)
                if isinstance(resolved, Image.Image):
                    background = resolved
                else:
                    bg_url = resolved
                    logger.info(f"选取背景图片URL: {bg_url}")
                    background = await HttpUtils.download_image(bg_url, headers=img_headers, proxy=self.proxy)
        else:
            bg_url = bg_spec
            if bg_url.startswith("http"):
                background = await HttpUtils.download_image(bg_url, proxy=self.proxy)
            else:
                background = Image.open(bg_url)
                
        return background, addition_text
