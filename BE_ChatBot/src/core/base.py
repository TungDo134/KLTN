"""
 ============ UNUSED ============
Abstract class -> extend for implement LLM models
- API (Nvidia, HuggingFace)
- Local (Ollama)
"""
from abc import ABC, abstractmethod


class ModelLLMPlatform(ABC):
    # Chat feature
    @abstractmethod
    async def achat(self, prompt: str) -> str:
        pass
