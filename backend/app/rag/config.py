"""RAG settings bridge for the main backend."""

import os

from app.rag.core.settings import Settings


def _app_setting(name: str, default: str = "") -> str:
    try:
        from app.config import settings as app_settings

        return str(getattr(app_settings, name, default) or default)
    except Exception:
        return os.getenv(name.upper(), default)


def get_rag_settings() -> Settings:
    api_key = _app_setting("dashscope_api_key")
    model = _app_setting("dashscope_model", "qwen-plus")
    return Settings.from_dict(
        {
            "llm": {
                "provider": "openai",
                "model": model,
                "api_key": api_key,
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "temperature": 0.0,
                "max_tokens": 4096,
            },
            "embedding": {
                "provider": "openai",
                "model": "text-embedding-v3",
                "dimensions": 1024,
                "api_key": api_key,
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            },
            "vector_store": {
                "provider": "chroma",
                "persist_directory": "storage/rag/chroma",
                "collection_name": "knowledge_hub",
            },
            "retrieval": {"dense_top_k": 20, "sparse_top_k": 20, "fusion_top_k": 10, "rrf_k": 60},
            "rerank": {"enabled": False, "provider": "none", "model": "none", "top_k": 5},
            "evaluation": {"enabled": False, "provider": "custom", "metrics": ["hit_rate"]},
            "observability": {
                "log_level": "INFO",
                "trace_enabled": True,
                "trace_file": "storage/rag/traces.jsonl",
                "structured_logging": True,
            },
            "ingestion": {
                "chunk_size": 1000,
                "chunk_overlap": 200,
                "splitter": "recursive",
                "batch_size": 100,
                "chunk_refiner": {"use_llm": False},
                "metadata_enricher": {"use_llm": False},
            },
        }
    )
