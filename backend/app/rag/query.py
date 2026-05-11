"""Thin query adapter placeholder for the internal RAG facade."""


class QueryResponse:
    def __init__(self, chunks=None):
        self.metadata = {"chunks": chunks or []}


class QueryKnowledgeHubTool:
    async def execute(self, query: str, top_k: int = 5, collection: str | None = None):
        return QueryResponse([])
