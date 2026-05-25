"""RAG query adapter — wraps HybridSearch without MCP dependencies."""
import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class QueryResponse:
    chunks: list[dict]

    @property
    def metadata(self):
        return {"chunks": self.chunks}


class QueryKnowledgeHubTool:
    def __init__(self, settings=None):
        self._settings = settings
        self._embedding_client = None
        self._reranker = None

    @property
    def settings(self):
        if self._settings is None:
            from app.rag.config import get_rag_settings
            self._settings = get_rag_settings()
        return self._settings

    async def execute(self, query: str, top_k: int = 5, collection: str = "default") -> QueryResponse:
        try:
            results = await asyncio.to_thread(self._search_sync, query, top_k, collection)
            chunks = [
                {
                    "text": r.text or "",
                    "source": r.metadata.get("source_path", r.metadata.get("source", "")),
                    "score": float(r.score),
                    "title": r.metadata.get("title", ""),
                }
                for r in results
            ]
            return QueryResponse(chunks=chunks)
        except Exception as exc:
            logger.warning("RAG query failed collection=%s error=%s", collection, exc)
            return QueryResponse(chunks=[])

    def _search_sync(self, query: str, top_k: int, collection: str):
        from app.rag.core.query_engine.hybrid_search import create_hybrid_search
        from app.rag.core.query_engine.dense_retriever import create_dense_retriever
        from app.rag.core.query_engine.sparse_retriever import create_sparse_retriever
        from app.rag.core.query_engine.query_processor import QueryProcessor
        from app.rag.core.query_engine.reranker import create_core_reranker
        from app.rag.ingestion.storage.bm25_indexer import BM25Indexer
        from app.rag.libs.embedding.embedding_factory import EmbeddingFactory
        from app.rag.libs.vector_store.vector_store_factory import VectorStoreFactory
        from app.rag.core.settings import resolve_path

        settings = self.settings

        if self._embedding_client is None:
            self._embedding_client = EmbeddingFactory.create(settings)
        if self._reranker is None:
            self._reranker = create_core_reranker(settings=settings)

        vector_store = VectorStoreFactory.create(settings, collection_name=collection)
        dense_retriever = create_dense_retriever(
            settings=settings,
            embedding_client=self._embedding_client,
            vector_store=vector_store,
        )
        bm25_indexer = BM25Indexer(index_dir=str(resolve_path(f"storage/rag/bm25/{collection}")))
        sparse_retriever = create_sparse_retriever(
            settings=settings,
            bm25_indexer=bm25_indexer,
            vector_store=vector_store,
        )
        sparse_retriever.default_collection = collection
        hybrid_search = create_hybrid_search(
            settings=settings,
            query_processor=QueryProcessor(),
            dense_retriever=dense_retriever,
            sparse_retriever=sparse_retriever,
        )
        result = hybrid_search.search(query=query, top_k=top_k)
        return result if isinstance(result, list) else result.results
