"""
LLM Factory - Factory Module
"""

import os
import re
from typing import Dict, List, Optional, Any
import yaml
from pathlib import Path

from .base import BaseLLMClient, Message, LLMResponse
from .openai_client import OpenAIClient
from .anthropic_client import AnthropicClient
from .gemini_client import GeminiClient


class LLMFactory:

    _clients: Dict[str, BaseLLMClient] = {}
    _config: Optional[Dict] = None
    _config_path: Optional[str] = None

    @classmethod
    def load_config(cls, config_path: str = "config/llm_providers.yaml"):
        env_var_pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'

        def parse_env_vars(value):
            if isinstance(value, str):
                matches = re.findall(env_var_pattern, value)
                for var_name, default in matches:
                    env_value = os.environ.get(var_name, default)
                    value = value.replace(f'${{{var_name}:{default}}}', env_value)
                    value = value.replace(f'${{{var_name}}}', env_value)
            return value

        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
            for match in re.finditer(env_var_pattern, content):
                var_name, default = match.groups()
                env_value = os.environ.get(var_name, default if default else '')
                content = content.replace(match.group(0), env_value)

        import io
        cls._config = yaml.safe_load(io.StringIO(content))

        cls._config_path = str(Path(config_path).resolve())

    @classmethod
    def get_client(cls,
                   provider: str,
                   model: Optional[str] = None,
                   **kwargs) -> BaseLLMClient:


        if cls._config is None:
            default_config = Path("config/config.yaml")
            if default_config.exists():
                cls.load_config(str(default_config))
            else:
                if 'api_key' not in kwargs:
                    raise ValueError(
                        f"Config file not found and api_key not provided for {provider}. "
                        f"Either load config with LLMFactory.load_config() or provide api_key."
                    )
                cls._config = {'providers': {}}

        if provider not in cls._config.get('providers', {}):
            if 'api_key' in kwargs:
                provider_config = {}
            else:
                raise ValueError(
                    f"Unknown provider: {provider}. "
                    f"Available providers: {list(cls._config.get('providers', {}).keys())}"
                )
        else:
            provider_config = cls._config['providers'][provider]

        api_key = kwargs.pop('api_key', provider_config.get('api_key'))
        if not api_key:
            raise ValueError(f"api_key not provided for {provider}")

        base_url = kwargs.pop('base_url', provider_config.get('base_url'))
        model_name = model or kwargs.pop('model', provider_config.get('default_model'))

        cache_key = f"{provider}_{model_name}"
        if cache_key not in cls._clients:
            if provider in ['openai', 'azure', 'qwen', 'zhipu', 'moonshot',
                           'deepseek', 'baichuan', 'minimax']:
                cls._clients[cache_key] = OpenAIClient(
                    api_key=api_key,
                    base_url=base_url,
                    model=model_name,
                    **{**provider_config.get('options', {}), **kwargs}
                )
            elif provider == 'anthropic':
                cls._clients[cache_key] = AnthropicClient(
                    api_key=api_key,
                    model=model_name,
                    **{**provider_config.get('options', {}), **kwargs}
                )
            elif provider == 'gemini':
                cls._clients[cache_key] = GeminiClient(
                    api_key=api_key,
                    model=model_name,
                    **{**provider_config.get('options', {}), **kwargs}
                )
            else:
                cls._clients[cache_key] = OpenAIClient(
                    api_key=api_key,
                    base_url=base_url or provider_config.get('base_url'),
                    model=model_name,
                    **{**provider_config.get('options', {}), **kwargs}
                )

        return cls._clients[cache_key]

    @classmethod
    async def batch_complete(cls,
                             requests: List[Dict[str, Any]],
                             provider: str = 'openai',
                             model: Optional[str] = None,
                             **kwargs) -> List[LLMResponse]:
        import asyncio

        client = cls.get_client(provider, model, **kwargs)

        async def process_one(req):
            return await client.acomplete(**req)

        tasks = [process_one(req) for req in requests]
        return await asyncio.gather(*tasks)

    @classmethod
    def clear_cache(cls):
        cls._clients.clear()

    @classmethod
    def list_providers(cls) -> List[str]:
        if cls._config is None:
            return []
        return list(cls._config.get('providers', {}).keys())

    @classmethod
    def get_default_model(cls, provider: str) -> Optional[str]:
        if cls._config is None:
            return None
        return cls._config.get('providers', {}).get(provider, {}).get('default_model')

    @classmethod
    def reload_config(cls):
        if cls._config_path:
            cls.load_config(cls._config_path)
            cls.clear_cache()

    @classmethod
    def get_rubric_generator_config(cls, stage: str = 'generic') -> Dict[str, str]:

        if cls._config is None:
            default_config = Path("config/llm_providers.yaml")
            if default_config.exists():
                cls.load_config(str(default_config))
            else:
                return {"provider": "openai", "model": "gpt-4"}

        defaults = cls._config.get('defaults', {})
        stage_config = defaults.get(f'{stage}_rubric', {})

        if isinstance(stage_config, dict):
            return {
                "provider": stage_config.get('provider', 'openai'),
                "model": stage_config.get('model', 'gpt-4')
            }
        else:
            return {
                "provider": stage_config if isinstance(stage_config, str) else 'openai',
                "model": cls.get_default_model(stage_config if isinstance(stage_config, str) else 'openai')
            }

    @classmethod
    def get_simulation_configs(cls) -> List[Dict[str, str]]:
        if cls._config is None:
            default_config = Path("/config/llm_providers.yaml")
            if default_config.exists():
                cls.load_config(str(default_config))
            else:
                return [{"provider": "openai", "model": "gpt-4"}]

        defaults = cls._config.get('defaults', {})
        simulation_config = defaults.get('simulation', [])

        result = []
        for item in simulation_config:
            if isinstance(item, dict):
                result.append({
                    "provider": item.get('provider', 'openai'),
                    "model": item.get('model', 'gpt-4')
                })
            elif isinstance(item, str):
                result.append({
                    "provider": item,
                    "model": cls.get_default_model(item)
                })

        return result

    @classmethod
    def get_rubric_client(cls, stage: str = 'generic'):
        config = cls.get_rubric_generator_config(stage)
        return cls.get_client(**config)
