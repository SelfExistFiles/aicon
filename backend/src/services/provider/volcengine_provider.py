# src/services/providers/volcengine_provider.py

import asyncio
from typing import Any, Dict, List
from openai import AsyncOpenAI

from .base import BaseLLMProvider

class VolcengineProvider(BaseLLMProvider):
    """
    火山方舟（Doubao）Provider，兼容 OpenAI SDK。

    使用示例：
        client.chat.completions.create(model=..., messages=[...])

    base_url 使用火山兼容 OpenAI API 的地址：
        https://ark.cn-beijing.volces.com/api/v3
    """

    def __init__(self, api_key: str, max_concurrency: int = 5):
        # 关键：使用 OpenAI SDK，设置 base_url
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://ark.cn-beijing.volces.com/api/v3"
        )
        self.semaphore = asyncio.Semaphore(max_concurrency)

    async def completions(
            self,
            model: str,
            messages: List[Dict[str, Any]],
            **kwargs: Any
    ):
        """
        调用火山方舟兼容 OpenAI 的 completions 接口
        """
        async with self.semaphore:
            return await self.client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs
            )
