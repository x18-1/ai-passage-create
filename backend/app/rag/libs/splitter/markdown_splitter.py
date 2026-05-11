"""Markdown-aware splitter that splits on heading boundaries."""

from __future__ import annotations

from typing import Any, List, Optional

try:
    from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

from app.rag.libs.splitter.base_splitter import BaseSplitter

_HEADERS = [
    ("#", "h1"),
    ("##", "h2"),
    ("###", "h3"),
    ("####", "h4"),
]


class MarkdownSplitter(BaseSplitter):
    """Split Markdown by heading boundaries, then sub-split oversized sections.

    Each heading section becomes one chunk. If a section exceeds chunk_size,
    it is further split by RecursiveCharacterTextSplitter so no chunk is too large.
    The heading path (e.g. "Overview > Installation") is prepended to every chunk
    so the LLM has context when the chunk is retrieved.
    """

    def __init__(
        self,
        settings: Any,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        if not LANGCHAIN_AVAILABLE:
            raise ImportError(
                "langchain-text-splitters is required for MarkdownSplitter. "
                "Install with: pip install langchain-text-splitters"
            )
        ingestion = getattr(settings, "ingestion", None)
        self.chunk_size = chunk_size or (ingestion.chunk_size if ingestion else 1000)
        self.chunk_overlap = chunk_overlap or (ingestion.chunk_overlap if ingestion else 200)

        self._md_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=_HEADERS,
            strip_headers=False,
        )
        self._char_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )

    def split_text(self, text: str, trace: Any = None, **kwargs: Any) -> List[str]:
        # Step 1: split by Markdown headings
        md_docs = self._md_splitter.split_text(text)

        chunks: List[str] = []
        for doc in md_docs:
            content = doc.page_content.strip()
            if not content:
                continue

            # Build heading breadcrumb from metadata (e.g. "Overview > Install")
            heading_parts = []
            for key in ("h1", "h2", "h3", "h4"):
                val = doc.metadata.get(key)
                if val:
                    heading_parts.append(val)
            breadcrumb = " > ".join(heading_parts)

            # Prefix breadcrumb so retrieval results carry section context
            prefixed = f"[{breadcrumb}]\n{content}" if breadcrumb else content

            # Step 2: if the section is still too long, sub-split it
            if len(prefixed) <= self.chunk_size:
                chunks.append(prefixed)
            else:
                sub_chunks = self._char_splitter.split_text(prefixed)
                chunks.extend(sub_chunks)

        # Fallback: if no headings were found, use recursive splitter
        if not chunks:
            chunks = self._char_splitter.split_text(text)

        return chunks
