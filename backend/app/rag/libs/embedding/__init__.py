"""
Embedding Module.

This package contains embedding service abstractions and implementations:
- Base embedding class
- Embedding factory
- Provider implementations (OpenAI, Azure, Ollama)
"""

from app.rag.libs.embedding.azure_embedding import AzureEmbedding
from app.rag.libs.embedding.base_embedding import BaseEmbedding
from app.rag.libs.embedding.embedding_factory import EmbeddingFactory
from app.rag.libs.embedding.ollama_embedding import OllamaEmbedding
from app.rag.libs.embedding.openai_embedding import OpenAIEmbedding

__all__ = [
    "BaseEmbedding",
    "EmbeddingFactory",
    "OpenAIEmbedding",
    "AzureEmbedding",
    "OllamaEmbedding",
]
