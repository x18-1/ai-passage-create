"""RAG settings adapted from MODULAR-RAG-MCP-SERVER."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any


RAG_ROOT = Path(__file__).resolve().parents[3]  # → backend/


def resolve_path(relative: str | Path) -> Path:
    path = Path(relative)
    if path.is_absolute():
        return path
    return (RAG_ROOT / path).resolve()


class SettingsError(ValueError):
    pass


def _mapping(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise SettingsError(f"Missing settings section: {key}")
    return value


@dataclass(frozen=True)
class LLMSettings:
    provider: str
    model: str
    temperature: float
    max_tokens: int
    api_key: str | None = None
    base_url: str | None = None


@dataclass(frozen=True)
class EmbeddingSettings:
    provider: str
    model: str
    dimensions: int
    api_key: str | None = None
    base_url: str | None = None


@dataclass(frozen=True)
class VectorStoreSettings:
    provider: str
    persist_directory: str
    collection_name: str


@dataclass(frozen=True)
class RetrievalSettings:
    dense_top_k: int
    sparse_top_k: int
    fusion_top_k: int
    rrf_k: int


@dataclass(frozen=True)
class RerankSettings:
    enabled: bool
    provider: str
    model: str
    top_k: int


@dataclass(frozen=True)
class EvaluationSettings:
    enabled: bool
    provider: str
    metrics: list[str]


@dataclass(frozen=True)
class ObservabilitySettings:
    log_level: str
    trace_enabled: bool
    trace_file: str
    structured_logging: bool


@dataclass(frozen=True)
class IngestionSettings:
    chunk_size: int
    chunk_overlap: int
    splitter: str
    batch_size: int
    chunk_refiner: dict[str, Any] | None = None
    metadata_enricher: dict[str, Any] | None = None


@dataclass(frozen=True)
class Settings:
    llm: LLMSettings
    embedding: EmbeddingSettings
    vector_store: VectorStoreSettings
    retrieval: RetrievalSettings
    rerank: RerankSettings
    evaluation: EvaluationSettings
    observability: ObservabilitySettings
    ingestion: IngestionSettings | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Settings":
        llm = _mapping(data, "llm")
        embedding = _mapping(data, "embedding")
        vector_store = _mapping(data, "vector_store")
        retrieval = _mapping(data, "retrieval")
        rerank = _mapping(data, "rerank")
        evaluation = _mapping(data, "evaluation")
        observability = _mapping(data, "observability")
        ingestion = data.get("ingestion") or {}

        return cls(
            llm=LLMSettings(
                provider=str(llm["provider"]),
                model=str(llm["model"]),
                temperature=float(llm["temperature"]),
                max_tokens=int(llm["max_tokens"]),
                api_key=llm.get("api_key"),
                base_url=llm.get("base_url"),
            ),
            embedding=EmbeddingSettings(
                provider=str(embedding["provider"]),
                model=str(embedding["model"]),
                dimensions=int(embedding["dimensions"]),
                api_key=embedding.get("api_key"),
                base_url=embedding.get("base_url"),
            ),
            vector_store=VectorStoreSettings(
                provider=str(vector_store["provider"]),
                persist_directory=str(vector_store["persist_directory"]),
                collection_name=str(vector_store["collection_name"]),
            ),
            retrieval=RetrievalSettings(
                dense_top_k=int(retrieval["dense_top_k"]),
                sparse_top_k=int(retrieval["sparse_top_k"]),
                fusion_top_k=int(retrieval["fusion_top_k"]),
                rrf_k=int(retrieval["rrf_k"]),
            ),
            rerank=RerankSettings(
                enabled=bool(rerank["enabled"]),
                provider=str(rerank["provider"]),
                model=str(rerank["model"]),
                top_k=int(rerank["top_k"]),
            ),
            evaluation=EvaluationSettings(
                enabled=bool(evaluation["enabled"]),
                provider=str(evaluation["provider"]),
                metrics=list(evaluation["metrics"]),
            ),
            observability=ObservabilitySettings(
                log_level=str(observability["log_level"]),
                trace_enabled=bool(observability["trace_enabled"]),
                trace_file=str(observability["trace_file"]),
                structured_logging=bool(observability["structured_logging"]),
            ),
            ingestion=IngestionSettings(
                chunk_size=int(ingestion.get("chunk_size", 1000)),
                chunk_overlap=int(ingestion.get("chunk_overlap", 200)),
                splitter=str(ingestion.get("splitter", "recursive")),
                batch_size=int(ingestion.get("batch_size", 100)),
                chunk_refiner=ingestion.get("chunk_refiner"),
                metadata_enricher=ingestion.get("metadata_enricher"),
            ),
        )


def load_settings(path=None) -> "Settings":
    """Compatibility shim — delegates to get_rag_settings()."""
    from app.rag.config import get_rag_settings
    return get_rag_settings()
