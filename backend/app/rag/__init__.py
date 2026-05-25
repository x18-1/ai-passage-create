"""Internal RAG facade."""

from app.rag.kernel import RagIngestResult, RagKernel, RagQueryResult, format_results_for_prompt

__all__ = [
    "RagIngestResult",
    "RagKernel",
    "RagQueryResult",
    "format_results_for_prompt",
]
