"""Knowledge service backed by the internal RAG facade."""

from typing import Any

from app.rag.kernel import RagKernel, format_results_for_prompt
from app.schemas.knowledge import KnowledgeDocumentVO


SOURCE_COLLECTION_SUFFIX = {
    "upload": "knowledge",
    "article": "articles",
    "hotspot": "hotspots",
}


def collection_for(user_id: int, source_type: str) -> str:
    suffix = SOURCE_COLLECTION_SUFFIX[source_type]
    return f"user_{user_id}_{suffix}"


class RagKnowledgeService:
    def __init__(self, db, rag_kernel: RagKernel | None = None):
        self.db = db
        self.rag_kernel = rag_kernel or RagKernel()

    async def ingest_uploaded_file(self, user_id: int, title: str, file_path: str) -> int:
        collection = collection_for(user_id, "upload")
        result = self.rag_kernel.ingest_file(file_path=file_path, collection=collection)
        return await self._insert_document(
            user_id=user_id,
            title=title,
            source_type="upload",
            source_id=None,
            collection_name=collection,
            file_path=file_path,
            status="ready" if result.success else "failed",
            chunk_count=result.chunk_count,
            error_message=result.error,
        )

    async def ingest_text_source(
        self,
        user_id: int,
        title: str,
        source_type: str,
        source_id: str,
        file_path: str,
    ) -> int:
        collection = collection_for(user_id, source_type)
        result = self.rag_kernel.ingest_file(file_path=file_path, collection=collection)
        return await self._insert_document(
            user_id=user_id,
            title=title,
            source_type=source_type,
            source_id=source_id,
            collection_name=collection,
            file_path=file_path,
            status="ready" if result.success else "failed",
            chunk_count=result.chunk_count,
            error_message=result.error,
        )

    async def list_documents(self, user_id: int) -> list[KnowledgeDocumentVO]:
        rows = await self.db.fetch_all(
            query="""
                SELECT id, userId, title, sourceType, sourceId, collectionName, status,
                       chunkCount, errorMessage, createTime, updateTime
                FROM knowledge_document
                WHERE userId = :userId AND isDelete = 0
                ORDER BY updateTime DESC
            """,
            values={"userId": user_id},
        )
        return [self._to_vo(row) for row in rows]

    async def delete_document(self, doc_id: int, user_id: int) -> bool:
        """Delete document from DB and remove its vectors from ChromaDB."""
        row = await self.db.fetch_one(
            query="SELECT filePath, collectionName FROM knowledge_document WHERE id = :id AND userId = :userId AND isDelete = 0",
            values={"id": doc_id, "userId": user_id},
        )
        if not row:
            return False

        # Remove from ChromaDB
        try:
            from app.rag.libs.vector_store.vector_store_factory import VectorStoreFactory
            from app.rag.libs.vector_store.chroma_store import ChromaStore
            from app.rag.config import get_rag_settings
            settings = get_rag_settings()
            store = VectorStoreFactory.create(settings, collection_name=row["collectionName"])
            file_path = row["filePath"] or ""
            if file_path and isinstance(store, ChromaStore):
                store.delete_by_metadata({"source_path": file_path})
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("ChromaDB delete failed: %s", e)

        # Soft-delete in DB
        await self.db.execute(
            query="UPDATE knowledge_document SET isDelete = 1 WHERE id = :id AND userId = :userId",
            values={"id": doc_id, "userId": user_id},
        )
        return True

    async def get_document_chunks(self, doc_id: int, user_id: int) -> list[dict]:
        """Return chunks stored in ChromaDB for a given document."""
        row = await self.db.fetch_one(
            query="SELECT filePath, collectionName FROM knowledge_document WHERE id = :id AND userId = :userId AND isDelete = 0",
            values={"id": doc_id, "userId": user_id},
        )
        if not row:
            return []

        file_path = row["filePath"] or ""
        if not file_path:
            return []

        try:
            from app.rag.libs.vector_store.vector_store_factory import VectorStoreFactory
            from app.rag.libs.vector_store.chroma_store import ChromaStore
            from app.rag.config import get_rag_settings
            settings = get_rag_settings()
            store = VectorStoreFactory.create(settings, collection_name=row["collectionName"])
            if not isinstance(store, ChromaStore):
                return []
            results = store.collection.get(  # type: ignore[union-attr]
                where={"source_path": file_path},
                include=["documents", "metadatas"],
            )
            chunks = []
            for i, (doc, meta) in enumerate(zip(results.get("documents") or [], results.get("metadatas") or [])):
                chunks.append({
                    "index": i,
                    "text": doc,
                    "charCount": len(doc),
                    "title": (meta or {}).get("title", ""),
                    "tags": (meta or {}).get("tags", []),
                })
            return chunks
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("Get chunks failed: %s", e)
            return []

    async def query_prompt_context(self, user_id: int, query: str, collections: list[str], top_k: int = 5) -> str:
        effective_collections = collections or [
            collection_for(user_id, "upload"),
            collection_for(user_id, "article"),
            collection_for(user_id, "hotspot"),
        ]
        all_results = []
        for collection in effective_collections:
            all_results.extend(await self.rag_kernel.query(query=query, collection=collection, top_k=top_k))
        all_results.sort(key=lambda item: item.score, reverse=True)
        return format_results_for_prompt(all_results[:top_k])

    async def _insert_document(
        self,
        user_id: int,
        title: str,
        source_type: str,
        source_id: str | None,
        collection_name: str,
        file_path: str | None,
        status: str,
        chunk_count: int,
        error_message: str | None,
    ) -> int:
        return await self.db.execute(
            query="""
                INSERT INTO knowledge_document (
                    userId, title, sourceType, sourceId, collectionName, filePath,
                    status, chunkCount, errorMessage
                )
                VALUES (
                    :userId, :title, :sourceType, :sourceId, :collectionName, :filePath,
                    :status, :chunkCount, :errorMessage
                )
            """,
            values={
                "userId": user_id,
                "title": title,
                "sourceType": source_type,
                "sourceId": source_id,
                "collectionName": collection_name,
                "filePath": file_path,
                "status": status,
                "chunkCount": chunk_count,
                "errorMessage": error_message,
            },
        )

    def _to_vo(self, row) -> KnowledgeDocumentVO:
        return KnowledgeDocumentVO(
            id=self._get(row, "id"),
            userId=self._get(row, "userId"),
            title=self._get(row, "title"),
            sourceType=self._get(row, "sourceType"),
            sourceId=self._get(row, "sourceId"),
            collectionName=self._get(row, "collectionName"),
            status=self._get(row, "status"),
            chunkCount=self._get(row, "chunkCount"),
            errorMessage=self._get(row, "errorMessage"),
            createTime=self._get(row, "createTime"),
            updateTime=self._get(row, "updateTime"),
        )

    def _get(self, row, key: str) -> Any:
        try:
            return row[key]
        except TypeError:
            return getattr(row, key)
