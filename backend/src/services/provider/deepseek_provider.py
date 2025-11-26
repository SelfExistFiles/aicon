# src/services/providers/deepseek_provider.py

import asyncio
from typing import Any, Dict, List
from openai import AsyncOpenAI

from .base import BaseLLMProvider


class DeepSeekProvider(BaseLLMProvider):
    """
    DeepSeek 官方 API，兼容 OpenAI Protocol
    """

    def __init__(self, api_key: str, max_concurrency: int = 5):
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        self.semaphore = asyncio.Semaphore(max_concurrency)

    async def completions(
            self,
            model: str,
            messages: List[Dict[str, Any]],
            **kwargs: Any
    ):
        async with self.semaphore:
            return await self.client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs
            )
