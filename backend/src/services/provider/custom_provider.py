# src/services/providers/custom_provider.py
import asyncio
import aiohttp
import json
from typing import Any, Dict, List
from openai import AsyncOpenAI

from src.core.logging import get_logger
from src.services.provider.base import BaseLLMProvider, log_provider_call

logger = get_logger(__name__)


class CustomProvider(BaseLLMProvider):
    """
    纯净 SiliconFlow Provider，不含任何业务逻辑。

    - 不拼接 prompt
    - 不封装风格
    - 不理解句子
    - 不处理提示词生成

    只提供 completions() 和 generate_image() 接口 → 等同于一个可并发的 SiliconFlow SDK wrapper
    """

    def __init__(
        self,
        api_key: str,
        max_concurrency: int = 5,
        base_url: str = "https://api.aiconapi.me/v1",
    ):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.base_url = base_url
        self.api_key = api_key
        self.semaphore = asyncio.Semaphore(max_concurrency)

    @log_provider_call("completions")
    async def completions(
        self, model: str, messages: List[Dict[str, Any]], **kwargs: Any
    ):
        """
        调用 SiliconFlow chat.completions.create（纯粹透传）
        """

        # 用 semaphore 限制并发
        async with self.semaphore:
            return await self.client.chat.completions.create(
                model=model, messages=messages, **kwargs
            )

    @log_provider_call("generate_image")
    async def generate_image(self, prompt: str, model: str = None, **kwargs: Any):
        """
        调用 自定义 images.generate（纯粹透传）
        如果模型是 gemini-3-pro-image-preview，则调用 generate_image_gemini
        """

        # 检查是否是 Gemini 图像模型
        if model and "gemini" in model.lower():
            gemini_kwargs = dict(kwargs)
            aspect_ratio = str(gemini_kwargs.pop("aspect_ratio", "") or "").strip()
            image_size = str(gemini_kwargs.pop("image_size", "") or "").strip()
            if aspect_ratio:
                gemini_kwargs["aspectRatio"] = aspect_ratio
            if image_size:
                gemini_kwargs["imageSize"] = image_size
            # 调用 Gemini 专用方法，传递所有kwargs
            gemini_response = await self.generate_image_gemini(prompt, model, **gemini_kwargs)

            # 将 Gemini 响应包装成兼容格式
            return self._wrap_gemini_response(gemini_response)

        # 用 semaphore 限制并发
        async with self.semaphore:
            return await self.client.images.generate(
                model=model or "Kwai-Kolors/Kolors", prompt=prompt, **kwargs
            )

    @log_provider_call("generate_audio")
    async def generate_audio(
        self, input_text: str, voice: str = "alloy", model: str = "tts-1", **kwargs: Any
    ):
        """
        调用 OpenAI audio.speech.create（纯粹透传）
        """

        # 用 semaphore 限制并发
        async with self.semaphore:
            return await self.client.audio.speech.create(
                model=model, voice=voice, input=input_text, **kwargs
            )

    def _wrap_gemini_response(self, gemini_response: dict):
        """
        将 Gemini 响应包装成兼容 OpenAI 格式的对象

        Gemini API 实际返回格式:
        {
            "candidates": [{
                "content": {
                    "parts": [
                        {"text": "...", "thoughtSignature": "<BASE64>"},
                        {
                            "inlineData": {
                                "mimeType": "image/png",
                                "data": "<BASE64>"
                            }
                        }
                    ]
                }
            }]
        }
        
        thoughtSignature字段包含base64编码的图片数据
        """
        try:
            parts = gemini_response["candidates"][0]["content"]["parts"]
          
            base64_data = None
            mime = None

            # 遍历 parts 查找图片数据
            for part in parts:
                # 方式1: 检查 inlineData 字段
                if "inlineData" in part:
                    base64_data = part["inlineData"]["data"]
                    mime = part["inlineData"]["mimeType"]
                    logger.info("从inlineData字段提取到图片数据")
                    break
                
                # 方式2: 检查 thoughtSignature 字段(Gemini图片生成返回格式)
                # if "thoughtSignature" in part:
                #     base64_data = part["thoughtSignature"]
                #     mime = "image/png"  # Gemini默认返回PNG
                #     logger.info(gemini_response)
                #     logger.info(f"从thoughtSignature字段提取到图片数据(长度: {len(base64_data)})")
                #     break

            if not base64_data:
                logger.error("Gemini 响应中未找到图片数据")
                logger.error(f"响应结构: {json.dumps(gemini_response, indent=2, ensure_ascii=False)[:500]}...")
                # 打印parts的详细信息
                for i, part in enumerate(parts):
                    logger.error(f"Part {i}: keys={list(part.keys())}")
                raise ValueError(
                    "响应中未找到图片数据 (inlineData 或 thoughtSignature)"
                )

            # 创建兼容对象
            class GeminiImageResponse:
                def __init__(self, base64_data, mime):
                    self.data = [GeminiImageData(base64_data, mime)]

            class GeminiImageData:
                def __init__(self, base64_data, mime):
                    self.url = None  # Gemini 不返回 URL
                    self.b64_json = base64_data  # 存储 base64 数据
                    self.mime = mime

            return GeminiImageResponse(base64_data, mime)
        except (KeyError, IndexError) as e:
            raise ValueError(f"无法从 Gemini 响应中提取图像数据: {e}")

    async def generate_image_gemini(self, prompt: str,model:str,aspectRatio: str="16:9",imageSize: str="1K", **kwargs: Any):
        """
        Gemini 生成图像（携程异步版本）
        支持 reference_images 参数 (Persona)
        """
        base_url = self.base_url.replace("/v1", "")
        url = f"{base_url}/v1beta/models/{model}:generateContent?key={self.api_key}"
        logger.info(f"Gemini 生成图像 URL: {url}")
        # 构造 prompt 部分
        parts = [{"text": prompt}]
        
        # 处理参考图 (Persona)
        reference_images = kwargs.get("reference_images")
        if reference_images:
            import base64
            from datetime import timedelta
            from src.utils.storage import get_storage_client
            
            logger.info(f"处理 {len(reference_images)} 张参考图")
            
            # 直接使用参考图列表，后续下载逻辑会处理 uploads/ 开头的 Key
            logger.info(f"开启角色一致性参考图处理，共 {len(reference_images)} 张")
            
            # 最大支持 5 张参考图
            for img_url in reference_images[:5]:
                try:
                    img_data = None
                    # 优先检查是否是 MinIO key (如果刚才没转换成功或者还是key形式)
                    if img_url.startswith("uploads/"):
                        storage_client = await get_storage_client()
                        img_data = await storage_client.download_file(img_url)
                        logger.info(f"从存储直接读取参考图: {img_url[:30]}...")
                    else:
                        # 下载参考图并转 Base64
                        async with aiohttp.ClientSession() as session:
                            async with session.get(img_url, timeout=10) as resp:
                                if resp.status == 200:
                                    img_data = await resp.read()
                                else:
                                    logger.warning(f"下载参考图失败 HTTP {resp.status}: {img_url[:50]}...")
                    
                    if img_data:
                        b64_img = base64.b64encode(img_data).decode('utf-8')
                        
                        # 检测MIME类型
                        mime_type = "image/jpeg"
                        if img_data[:4] == b'\x89PNG':
                            mime_type = "image/png"
                        
                        parts.append({
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": b64_img
                            }
                        })
                        logger.info("成功添加参考图数据")
                except Exception as e:
                    logger.warning(f"处理参考图失败 {img_url[:50]}...: {e}")

        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": aspectRatio,"imageSize": imageSize}},
        }   

        async with self.semaphore:  # 控制最大并发
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, json=payload, headers={"Content-Type": "application/json"}
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"Gemini API Error: {error_text}")
                        raise ValueError(f"Gemini API 请求失败: {resp.status} - {error_text}")
                        
                    result = await resp.text()
                    return json.loads(result)

