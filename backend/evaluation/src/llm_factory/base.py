"""
LLM Factory - Base Module
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, AsyncIterator, Any
from dataclasses import dataclass, field
from enum import Enum


class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    role: str
    content: str

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def __add__(self, other):
        return Usage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens
        )


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: Optional[Usage] = None
    raw_response: Optional[Any] = None
    finish_reason: Optional[str] = None

    def __str__(self) -> str:
        return f"LLMResponse(model={self.model}, content={self.content[:100]}...)"


class BaseLLMClient(ABC):

    def __init__(self,
                 api_key: str,
                 base_url: Optional[str] = None,
                 model: Optional[str] = None,
                 **kwargs):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.kwargs = kwargs

    @abstractmethod
    async def acomplete(self,
                        messages: List[Message],
                        temperature: float = 0.7,
                        max_tokens: int = 2000,
                        **kwargs) -> LLMResponse:
        pass

    @abstractmethod
    def complete(self,
                 messages: List[Message],
                 temperature: float = 0.7,
                 max_tokens: int = 2000,
                 **kwargs) -> LLMResponse:
        pass

    async def astream(self,
                      messages: List[Message],
                      temperature: float = 0.7,
                      max_tokens: int = 2000,
                      **kwargs) -> AsyncIterator[str]:
        raise NotImplementedError("Streaming not implemented for this client")

    @property
    @abstractmethod
    def provider_name(self) -> str:

        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model})"
