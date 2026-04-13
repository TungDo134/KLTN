"""
FACTORY CLASS TO CREATE EMBEDDING MODELS
"""

import os
from enum import Enum

import torch
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import OllamaEmbeddings
from langchain_core.embeddings import Embeddings

# --- Auto-detect GPU ---
_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Thư mục chứa file này
_DEFAULT_CACHE = os.path.normpath(os.path.join(_BASE_DIR, "..", "model", "embeddings"))  # Điều chỉnh ../ cho phù hợp
print(f"📁 Cache dir: {_DEFAULT_CACHE}")


class EmbeddingProvider(str, Enum):
    HUGGINGFACE = "huggingface"
    OLLAMA = "ollama"


def get_embedding_model(
        provider: EmbeddingProvider = EmbeddingProvider.HUGGINGFACE,  # Default use HuggingFace
        model_name: str = "AITeamVN/Vietnamese_Embedding",
        model_kwargs: dict = None,
        encode_kwargs: dict = None,
        cache_folder: str = _DEFAULT_CACHE,
) -> Embeddings:
    model_kwargs = model_kwargs or {"device": _DEVICE}
    encode_kwargs = encode_kwargs or {"normalize_embeddings": True}

    print(f"🔧 Provider : {provider.value}")
    print(f"🔧 Model    : {model_name}")
    print(f"🔧 Device   : {model_kwargs.get('device', 'N/A')}")
    print(f"🔧 Cache    : {cache_folder}")

    if provider == EmbeddingProvider.HUGGINGFACE:
        return HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs=model_kwargs,
            encode_kwargs=encode_kwargs,
            cache_folder=cache_folder,
        )

    elif provider == EmbeddingProvider.OLLAMA:
        return OllamaEmbeddings(model=model_name)
    else:
        raise ValueError(f"Unsupported embedding provider: {provider}")
