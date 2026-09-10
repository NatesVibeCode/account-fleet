"""Provider registry decoupling dispatch from route ID string inspection."""
from __future__ import annotations

from typing import Dict, Optional
from .base import BaseProvider
from .opencode import OpenCodeProvider
from .openrouter import OpenRouterProvider
from .openai_compatible import OpenAICompatibleProvider


class ProviderRegistry:
    def __init__(self):
        self._providers: Dict[str, BaseProvider] = {}
        # Default built-in providers
        self.register("opencode", OpenCodeProvider())
        self.register("openrouter", OpenRouterProvider())
        self.register("openai_compatible", OpenAICompatibleProvider(provider_name="openai_compatible"))
        # Aliases for local/generic providers
        self.register("ollama", OpenAICompatibleProvider(provider_name="ollama"))
        self.register("lmstudio", OpenAICompatibleProvider(provider_name="lmstudio"))
        self.register("vllm", OpenAICompatibleProvider(provider_name="vllm"))
        self.register("groq", OpenAICompatibleProvider(provider_name="groq"))
        self.register("cerebras", OpenAICompatibleProvider(provider_name="cerebras"))

    def register(self, name: str, provider: BaseProvider) -> None:
        self._providers[name.lower()] = provider

    def get(self, name: str) -> Optional[BaseProvider]:
        return self._providers.get(name.lower())

    def resolve(self, provider_hint: Optional[str], route_id: str) -> BaseProvider:
        """Resolve the appropriate provider using the explicit provider field or route_id fallback."""
        if provider_hint and provider_hint.lower() in self._providers:
            return self._providers[provider_hint.lower()]

        # Fallback to route_id prefix if provider_hint is absent or unknown
        prefix = route_id.split("/", 1)[0].lower() if "/" in route_id else ""
        if prefix in self._providers:
            return self._providers[prefix]

        if "openrouter" in route_id.lower():
            return self._providers["openrouter"]

        # Default fallback
        return self._providers.get("opencode") or list(self._providers.values())[0]
