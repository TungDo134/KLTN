# src/core/container.py
"""
Singleton Pattern — Khởi tạo 1 lần, dùng ở mọi nơi.
"""
import os
from functools import lru_cache
from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel

from src.core.base_llm_model import get_llm_model, LLMProvider

load_dotenv()


@lru_cache(maxsize=1)
def _load_system_prompt() -> str:
    path = os.getenv("SYSTEM_PROMPT")
    if not path:
        return "You are a Vietnamese travel assistant."
    try:
        with open(path, "r", encoding="utf-8") as f:
            print(f"✅ System prompt loaded from: {path}")
            return f.read()
    except FileNotFoundError:
        print(f"⚠️  System prompt not found: {path}.")
        return "You are a Vietnamese travel assistant."


@lru_cache(maxsize=None)
def get_llm(
        provider: LLMProvider = LLMProvider(os.getenv("LLM_PROVIDER", "nvidia")),
        model_name: str | None = None,
        temperature: float = 0.5,
        max_tokens: int = 1024,
):
    """Default dùng NVIDIA - meta/llama-3.3-70b-instruct"""
    print(f"\n🚀 Initializing LLM [{provider} / {model_name or 'default'}] \n")
    return get_llm_model(provider, model_name, temperature, max_tokens)


def get_system_prompt() -> str:
    """Singleton system prompt."""
    return _load_system_prompt()


def get_model_info(llm: BaseChatModel) -> str:
    """Trả về string 'provider / model_name' từ BaseChatModel object."""
    model = getattr(llm, "model_name", None) or getattr(llm, "model", None) or "unknown"
    provider = type(llm).__name__.replace("Chat", "").lower()  # ChatGroq → groq
    return f"{provider} / {model}"
