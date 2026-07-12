"""
FACTORY CLASS TO CREATE EMBEDDING MODELS
"""

import os
from enum import Enum

import torch
from langchain_core.embeddings import Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import OllamaEmbeddings


_DEVICE = "cuda"
_DEFAULT_PROVIDER = "huggingface"
_DEFAULT_MODEL = "AITeamVN/Vietnamese_Embedding"

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_CACHE = os.path.normpath(os.path.join(_BASE_DIR, "..", "model", "embeddings"))


class EmbeddingProvider(str, Enum):
    HUGGINGFACE = "huggingface"
    OLLAMA = "ollama"
    GOOGLE = "google"


def resolve_embedding_config(
    provider: EmbeddingProvider | str | None = None,
    model_name: str | None = None,
) -> tuple[EmbeddingProvider, str]:
    """Get provider/model from explicit arguments or environment variables."""
    if provider is None and model_name is None:
        env_provider = (os.getenv("EMBEDDING_PROVIDER") or "").strip().lower()
        env_model = (os.getenv("EMBEDDING_MODEL") or "").strip()

        if bool(env_provider) != bool(env_model):
            raise ValueError(
                "EMBEDDING_PROVIDER and EMBEDDING_MODEL phai duoc set-up ."
            )

        provider = env_provider or _DEFAULT_PROVIDER
        model_name = env_model or _DEFAULT_MODEL
    else:
        provider = provider or _DEFAULT_PROVIDER
        model_name = (model_name or "").strip()
        if not model_name:
            if str(provider) in {
                EmbeddingProvider.HUGGINGFACE.value,
                str(EmbeddingProvider.HUGGINGFACE),
            }:
                model_name = _DEFAULT_MODEL
            else:
                raise ValueError("embedding provider can model_name .")

    try:
        resolved_provider = (
            provider
            if isinstance(provider, EmbeddingProvider)
            else EmbeddingProvider(str(provider).strip().lower())
        )
    except ValueError as exc:
        supported = ", ".join(item.value for item in EmbeddingProvider)
        raise ValueError(
            f"Khong ho tro embedding provider: {provider}. Supported: {supported}."
        ) from exc

    return resolved_provider, model_name


def get_embedding_model(
    provider: EmbeddingProvider | str | None = None,
    model_name: str | None = None,
    model_kwargs: dict | None = None,
    encode_kwargs: dict | None = None,
    cache_folder: str = _DEFAULT_CACHE,
) -> Embeddings:
    provider, model_name = resolve_embedding_config(provider, model_name)

    print("\n- Embedding Model \n")
    print(f"🔧 Embedding provider: {provider.value}")
    print(f"🔧 Embedding model   : {model_name}")

    if provider == EmbeddingProvider.HUGGINGFACE:
        if not torch.cuda.is_available():
            raise EnvironmentError(
                "Khong tim thay GPU. HuggingFace embedding yeu cau CUDA."
            )

        model_kwargs = model_kwargs or {"device": _DEVICE}
        encode_kwargs = encode_kwargs or {"normalize_embeddings": True}
        print(f"Embedding device  : {model_kwargs.get('device', 'N/A')}")
        print(f"Embedding cache   : {cache_folder}")
        return HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs=model_kwargs,
            encode_kwargs=encode_kwargs,
            cache_folder=cache_folder,
        )

    if provider == EmbeddingProvider.OLLAMA:
        return OllamaEmbeddings(model=model_name)

    if not (os.getenv("GEMINI_API_KEY")):
        raise ValueError("Google embedding yeu cau GEMINI_API_KEY .")
    return GoogleGenerativeAIEmbeddings(model=model_name)
