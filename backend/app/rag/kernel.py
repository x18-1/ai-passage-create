"""RAG kernel facade used by application services."""

import logging
from dataclasses import dataclass
from typing import Iterable

logger = logging.getLogger(__name__)


@dataclass
class RagIngestResult:
    success: bool
    chunk_count: int = 0
    error: str | None = None


@dataclass
class RagQueryResult:
    text: str
    source: str
    score: float
    title: str | None = None


def format_results_for_prompt(results: Iterable[RagQueryResult]) -> str:
    blocks = []
    for index, item in enumerate(results, start=1):
        title = f"标题: {item.title}\n" if item.title else ""
        blocks.append(
            f"[资料 {index}]\n"
            f"{title}"
            f"内容: {item.text}\n"
            f"来源: {item.source}\n"
            f"相关度: {item.score:.2f}"
        )
    return "\n\n".join(blocks)


class RagKernel:
    def ingest_file(self, file_path: str, collection: str, force: bool = False) -> RagIngestResult:
        try:
            from app.rag.ingestion.pipeline import IngestionPipeline
            from app.rag.config import get_rag_settings
        except ImportError as exc:
            logger.error("RAG import failed: %s", exc, exc_info=True)
            return RagIngestResult(success=False, error=f"RAG ingestion pipeline is unavailable: {exc}")

        try:
            pipeline = IngestionPipeline(get_rag_settings(), collection=collection, force=force)
        except Exception as exc:
            logger.error("IngestionPipeline init failed: %s", exc, exc_info=True)
            return RagIngestResult(success=False, error=f"Pipeline init error: {exc}")

        result = pipeline.run(file_path)
        if not result.success:
            logger.error("RAG ingest failed file=%s error=%s", file_path, result.error)
        else:
            logger.info("RAG ingest OK file=%s chunks=%d", file_path, result.chunk_count)
        return RagIngestResult(
            success=bool(result.success),
            chunk_count=int(result.chunk_count),
            error=result.error,
        )

    async def query(self, query: str, collection: str, top_k: int = 5) -> list[RagQueryResult]:
        try:
            from app.rag.query import QueryKnowledgeHubTool
        except ImportError:
            return []

        tool = QueryKnowledgeHubTool()
        response = await tool.execute(query=query, top_k=top_k, collection=collection)
        chunks = getattr(response, "metadata", {}).get("chunks", [])
        return [
            RagQueryResult(
                text=str(chunk.get("text", "")),
                source=str(chunk.get("source", "")),
                score=float(chunk.get("score", 0)),
                title=chunk.get("title"),
            )
            for chunk in chunks
        ]
