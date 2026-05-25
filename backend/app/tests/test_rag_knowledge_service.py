import asyncio
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


SERVICE_PATH = Path(__file__).resolve().parents[1] / "services" / "rag_knowledge_service.py"
spec = importlib.util.spec_from_file_location("rag_knowledge_service", SERVICE_PATH)
svc_module = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(svc_module)
RagKnowledgeService = svc_module.RagKnowledgeService
collection_for = svc_module.collection_for


def test_collection_for_uses_user_scoped_names():
    assert collection_for(9, "upload") == "user_9_knowledge"
    assert collection_for(9, "article") == "user_9_articles"
    assert collection_for(9, "hotspot") == "user_9_hotspots"


class FakeDb:
    def __init__(self):
        self.executed = []
        self.rows = []

    async def execute(self, query, values=None):
        self.executed.append((str(query), values or {}))
        return 3

    async def fetch_all(self, query, values=None):
        self.executed.append((str(query), values or {}))
        return self.rows


class FakeKernel:
    def ingest_file(self, file_path, collection, force=False):
        return type("Result", (), {"success": True, "chunk_count": 4, "error": None})()

    async def query(self, query, collection, top_k=5):
        return [
            type("Result", (), {"text": f"{collection}: {query}", "source": "doc.md", "score": 0.8, "title": None})()
        ]


def test_create_upload_document_records_ready_status_after_ingest():
    async def run():
        db = FakeDb()
        svc = RagKnowledgeService(db, rag_kernel=FakeKernel())
        doc_id = await svc.ingest_uploaded_file(user_id=5, title="demo.pdf", file_path="/tmp/demo.pdf")
        assert doc_id == 3
        assert db.executed[-1][1]["status"] == "ready"
        assert db.executed[-1][1]["chunkCount"] == 4
        assert db.executed[-1][1]["collectionName"] == "user_5_knowledge"

    asyncio.run(run())


def test_query_prompt_context_uses_default_user_collections_and_sorts_results():
    async def run():
        db = FakeDb()
        svc = RagKnowledgeService(db, rag_kernel=FakeKernel())
        prompt = await svc.query_prompt_context(user_id=5, query="AI 编程", collections=[], top_k=2)

        assert "user_5_knowledge: AI 编程" in prompt
        assert "user_5_articles: AI 编程" in prompt
        assert "来源: doc.md" in prompt

    asyncio.run(run())
