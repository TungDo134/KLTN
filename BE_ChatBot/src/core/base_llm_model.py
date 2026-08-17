"""
FACTORY CLASS TO CREATE LLM MODELS

Supported providers:
  - NVIDIA  (ChatNVIDIA via langchain-nvidia-ai-endpoints)
  - GROQ    (ChatGroq via langchain_groq)
  - GEMINI  (ChatGemini via langchain_google_genai)
  - OLLAMA  (ChatOllama via langchain-ollama)
  - HUGGINGFACE (HuggingFaceEndpoint via langchain-huggingface) - Not implemented
"""

import os
from enum import Enum

from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_ollama import ChatOllama

load_dotenv()


# ============================================================
# Abstract base - LangChain-compatible wrapper để chain dùng
# ============================================================
class LLMProvider(str, Enum):
    NVIDIA = "nvidia"
    OLLAMA = "ollama"
    OLLAMA_CLOUD = "ollama_cloud"
    GEMINI = "gemini"
    GROQ = "groq"
    HUGGINGFACE = "huggingface"


# ============================================================
# Concrete adapters — mỗi class wrap 1 provider
# ============================================================


class _NvidiaLLM:
    """
    - Wrap ChatNVIDIA — default provider.
    - Default model: meta/llama-3.3-70b-instruct
    - Expect: user-facing tasks (chat and response generation).
    """

    DEFAULT_MODEL = "meta/llama-3.3-70b-instruct"

    @staticmethod
    def build(
        model_name: str = DEFAULT_MODEL,
        temperature: float = 0.5,
        max_tokens: int = 1024,
    ) -> BaseChatModel:
        api_key = os.getenv("NVIDIA_API_KEY")
        if not api_key:
            raise ValueError("NVIDIA_API_KEY is not set in .env")

        print(f"🔧 Provider : nvidia")
        print(f"🔧 Model    : {model_name}")

        return ChatNVIDIA(
            model=model_name,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )


class _OllamaLLM:
    """Wrap ChatOllama — chạy local, không cần API key."""

    DEFAULT_MODEL = "llama3.1:8b"

    @staticmethod
    def build(
        model_name: str = DEFAULT_MODEL,
        temperature: float = 0.5,
        max_tokens: int = 1024,
    ) -> BaseChatModel:

        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

        print(f"🔧 Provider : ollama")
        print(f"🔧 Model    : {model_name}")
        print(f"🔧 Base URL : {base_url}")

        return ChatOllama(
            model=model_name,
            base_url=base_url,
            temperature=temperature,
            num_predict=max_tokens,
        )


class _OllamaCloudLLM:
    """Wrap ChatOllama via Ollama Cloud API key."""

    DEFAULT_MODEL = "gemma4:cloud"
    BASE_URL = "https://ollama.com"

    @staticmethod
    def build(
        model_name: str = DEFAULT_MODEL,
        temperature: float = 0.5,
        max_tokens: int = 1024,
    ) -> BaseChatModel:

        api_key = os.getenv("OLLAMA_API_KEY")
        if not api_key:
            raise ValueError("OLLAMA_API_KEY is not set in .env")

        print(f"Provider : ollama_cloud")
        print(f"Model    : {model_name}")
        print(f"Base URL : {_OllamaCloudLLM.BASE_URL}")

        return ChatOllama(
            model=model_name,
            base_url=_OllamaCloudLLM.BASE_URL,
            temperature=temperature,
            num_predict=max_tokens,
            client_kwargs={"headers": {"Authorization": f"Bearer {api_key}"}},
        )


class _GeminiLLM:
    """
    - Wrap ChatGoogleGenerativeAI — Google Gemini API.
    - Default model: gemini-2.5-flash
    - Due to rate limits, this model should be used for small tasks
    - Expected: Agentic Chunking
    """

    DEFAULT_MODEL = "gemini-2.5-flash"

    @staticmethod
    def build(
        model_name: str = DEFAULT_MODEL,
        temperature: float = 0.5,
        max_tokens: int = 1024,
    ) -> BaseChatModel:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set in .env")

        print(f"🔧 Provider : gemini")
        print(f"🔧 Model    : {model_name}")

        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )


class _GroqLLM:
    """
    - Wrap ChatGroq — Groq Cloud API.
    - Default model: openai/gpt-oss-20b
    - Expect: Rewrite standalone for history chat - Multi Query
    """

    DEFAULT_MODEL = "openai/gpt-oss-20b"

    @staticmethod
    def build(
        model_name: str = DEFAULT_MODEL,
        temperature: float = 0.5,
        max_tokens: int = 1024,
    ) -> BaseChatModel:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set in .env")

        print(f"🔧 Provider : groq")
        print(f"🔧 Model    : {model_name}")

        return ChatGroq(
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
        )


# ============================================================
# Public factory function — entry point duy nhất
# ============================================================
_PROVIDER_MAP = {
    LLMProvider.NVIDIA: _NvidiaLLM,
    LLMProvider.OLLAMA: _OllamaLLM,
    LLMProvider.OLLAMA_CLOUD: _OllamaCloudLLM,
    LLMProvider.GEMINI: _GeminiLLM,
    LLMProvider.GROQ: _GroqLLM,
    # LLMProvider.HUGGINGFACE: _HuggingFaceLLM,
}


def get_llm_model(
    provider: LLMProvider = LLMProvider.NVIDIA,
    model_name: str | None = None,
    temperature: float = 0.5,
    max_tokens: int = 1024,
) -> BaseChatModel:
    """
    Factory function — tạo LLM object theo provider.

    Usage:
        llm = get_llm_model()                                           # NVIDIA default
        llm = get_llm_model(LLMProvider.GEMINI ||
        os.getenv(LLMProvider(os.getenv("env_value")))       # GEMINI API
        llm = get_llm_model(LLMProvider.OLLAMA, "llama3.1:8b")          # Ollama local
        llm = get_llm_model(LLMProvider.OLLAMA_CLOUD, "gemma4:cloud")   # Ollama Cloud
    """
    builder_cls = _PROVIDER_MAP.get(provider)
    if builder_cls is None:
        raise ValueError(f"Unsupported LLM provider: {provider}")

    kwargs = {"temperature": temperature, "max_tokens": max_tokens}
    if model_name:
        kwargs["model_name"] = model_name

    return builder_cls.build(**kwargs)
