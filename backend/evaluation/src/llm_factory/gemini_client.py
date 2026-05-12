"""
LLM Factory - Google Gemini Client
"""

from typing import List, Optional
import asyncio

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from .base import BaseLLMClient, Message, LLMResponse, Usage


class GeminiClient(BaseLLMClient):

    def __init__(self,
                 api_key: str,
                 model: str = "gemini-2.0-flash-exp",
                 thinking_level: Optional[str] = None,
                 **kwargs):

        if not GEMINI_AVAILABLE:
            raise ImportError(
                "google-genai package is required. "
                "Install it with: pip install google-genai"
            )

        super().__init__(api_key, None, model, **kwargs)

        self.client = genai.Client(api_key=api_key)
        self.thinking_level = thinking_level

    async def acomplete(self,
                        messages: List[Message],
                        temperature: float = 0.7,
                        max_tokens: int = 2000,
                        **kwargs) -> LLMResponse:
        try:
            contents = self._convert_messages(messages)

            config_kwargs = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }

            if self.thinking_level:
                config_kwargs["thinking_config"] = types.ThinkingConfig(
                    thinking_level=self.thinking_level
                )

            config_kwargs.update(kwargs)

            config = types.GenerateContentConfig(**config_kwargs)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=config
                )
            )

            content = response.text if hasattr(response, 'text') else ""

            usage = None
            if hasattr(response, 'usage_metadata'):
                meta = response.usage_metadata
                usage = Usage(
                    prompt_tokens=meta.prompt_token_count if hasattr(meta, 'prompt_token_count') else 0,
                    completion_tokens=meta.candidates_token_count if hasattr(meta, 'candidates_token_count') else 0,
                    total_tokens=meta.total_token_count if hasattr(meta, 'total_token_count') else 0
                )

            return LLMResponse(
                content=content,
                model=self.model,
                usage=usage,
                raw_response=response,
                finish_reason=response.candidates[0].finish_reason if response.candidates else None
            )

        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")

    def complete(self,
                 messages: List[Message],
                 temperature: float = 0.7,
                 max_tokens: int = 2000,
                 **kwargs) -> LLMResponse:
        try:
            contents = self._convert_messages(messages)
            config_kwargs = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }
            if self.thinking_level:
                config_kwargs["thinking_config"] = types.ThinkingConfig(
                    thinking_level=self.thinking_level
                )
            config_kwargs.update(kwargs)

            config = types.GenerateContentConfig(**config_kwargs)
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config
            )

            content = response.text if hasattr(response, 'text') else ""

            usage = None
            if hasattr(response, 'usage_metadata'):
                meta = response.usage_metadata
                usage = Usage(
                    prompt_tokens=meta.prompt_token_count if hasattr(meta, 'prompt_token_count') else 0,
                    completion_tokens=meta.candidates_token_count if hasattr(meta, 'candidates_token_count') else 0,
                    total_tokens=meta.total_token_count if hasattr(meta, 'total_token_count') else 0
                )

            return LLMResponse(
                content=content,
                model=self.model,
                usage=usage,
                raw_response=response,
                finish_reason=response.candidates[0].finish_reason if response.candidates else None
            )

        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")

    def _convert_messages(self, messages: List[Message]) -> str:
        parts = []
        for msg in messages:
            if msg.role == "system":
                parts.append(f"[System]: {msg.content}\n")
            elif msg.role == "user":
                parts.append(f"[User]: {msg.content}\n")
            elif msg.role == "assistant":
                parts.append(f"[Assistant]: {msg.content}\n")

        return "".join(parts)

    @property
    def provider_name(self) -> str:
        return "Google"
