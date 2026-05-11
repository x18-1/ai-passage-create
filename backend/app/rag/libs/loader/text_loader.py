"""Simple text and Markdown loader."""
from pathlib import Path
from app.rag.core.types import Document
from app.rag.libs.loader.base_loader import BaseLoader
import hashlib


class TextLoader(BaseLoader):
    def load(self, file_path: str | Path) -> Document:
        path = Path(file_path)
        text = path.read_text(encoding="utf-8", errors="replace")
        doc_id = hashlib.sha256(text.encode()).hexdigest()[:16]
        return Document(
            id=doc_id,
            text=text,
            metadata={"source_path": str(path), "file_name": path.name, "images": []},
        )
