"""
LLM Factory - Anthropic Claude Client
"""

from typing import List, Optional
import asyncio

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from .base import BaseLLMClient, Message, LLMResponse, Usage


class AnthropicClient(BaseLLMClient):

    def __init__(self,
                 api_key: str,
                 model: str = "claude-3-5-sonnet-20241022",
                 timeout: int = 60,
                 max_retries: int = 3,
                 **kwargs):

        if not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "anthropic package is required. "
                "Install it with: pip install anthropic"
            )

        super().__init__(api_key, None, model, **kwargs)
        self.client = anthropic.AsyncAnthropic(
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries
        )
        self.timeout = timeout
        self.max_retries = max_retries

    async def acomplete(self,
                        messages: List[Message],
                        temperature: float = 0.7,
                        max_tokens: int = 2000,
                        **kwargs) -> LLMResponse:

        # Separate system messages and chat messages
        system_msg = ""
        chat_messages = []

        for msg in messages:
            if msg.role == "system":
                system_msg = msg.content
            else:
                chat_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        try:
            response = await self.client.messages.create(
                model=self.model,
                system=system_msg,
                messages=chat_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **{**self.kwargs, **kwargs}
            )


            content = response.content[0].text

            return LLMResponse(
                content=content,
                model=response.model,
                usage=Usage(
                    prompt_tokens=response.usage.input_tokens,
                    completion_tokens=response.usage.output_tokens,
                    total_tokens=response.usage.input_tokens + response.usage.output_tokens
                ),
                raw_response=response,
                finish_reason=response.stop_reason
            )

        except Exception as e:
            raise Exception(f"Anthropic API error: {str(e)}")

    def complete(self,
                 messages: List[Message],
                 temperature: float = 0.7,
                 max_tokens: int = 2000,
                 **kwargs) -> LLMResponse:

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.acomplete(messages, temperature, max_tokens, **kwargs)
        )

    @property
    def provider_name(self) -> str:
        """Provider Name"""
        return "Anthropic"

    async def astream(self,
                      messages: List[Message],
                      temperature: float = 0.7,
                      max_tokens: int = 2000,
                      **kwargs):

        system_msg = ""
        chat_messages = []

        for msg in messages:
            if msg.role == "system":
                system_msg = msg.content
            else:
                chat_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        async with self.client.messages.stream(
            model=self.model,
            system=system_msg,
            messages=chat_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **{**self.kwargs, **kwargs}
        ) as stream:
            async for text in stream.text_stream:
                yield text
