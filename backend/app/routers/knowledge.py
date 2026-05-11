"""Knowledge base routes."""

from pathlib import Path
from typing import List

import httpx
from bs4 import BeautifulSoup
from databases import Database
from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel

from app.database import get_db
from app.deps import require_login
from app.schemas.common import BaseResponse
from app.schemas.knowledge import KnowledgeDocumentVO, KnowledgeQueryRequest
from app.schemas.user import LoginUserVO
from app.services.rag_knowledge_service import RagKnowledgeService


router = APIRouter(prefix="/knowledge", tags=["知识库"])


async def _fetch_article_text(url: str) -> str:
    """Fetch and extract main text from a URL. Returns empty string on failure."""
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; RAG-Crawler/1.0)"}
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                return ""
            soup = BeautifulSoup(resp.text, "lxml")
            # Remove script/style/nav/header/footer tags
            for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
                tag.decompose()
            # Try article/main content first
            main = soup.find("article") or soup.find("main") or soup.find(id="content") or soup.body
            if main is None:
                return ""
            text = main.get_text(separator="\n", strip=True)
            # Limit to 8000 chars to avoid too large chunks
            return text[:8000]
    except Exception:
        return ""


class IngestHotspotsRequest(BaseModel):
    recordIds: List[int]


@router.get("/documents", response_model=BaseResponse[list[KnowledgeDocumentVO]])
async def list_knowledge_documents(
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    return BaseResponse.success(data=await RagKnowledgeService(db).list_documents(current_user.id))


@router.post("/upload", response_model=BaseResponse[int])
async def upload_knowledge(
    file: UploadFile = File(...),
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".md", ".txt"}:
        return BaseResponse(code=40000, data=None, message="仅支持 PDF/Markdown/TXT")

    upload_dir = Path("/tmp/ai-passage-uploads") / str(current_user.id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    target = upload_dir / (file.filename or "upload.txt")
    target.write_bytes(await file.read())
    doc_id = await RagKnowledgeService(db).ingest_uploaded_file(current_user.id, target.name, str(target))
    return BaseResponse.success(data=doc_id)


@router.post("/query", response_model=BaseResponse[str])
async def query_knowledge(
    request: KnowledgeQueryRequest,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    context = await RagKnowledgeService(db).query_prompt_context(
        user_id=current_user.id,
        query=request.query,
        collections=request.collections,
        top_k=request.top_k,
    )
    return BaseResponse.success(data=context)


@router.post("/articles/{task_id}/ingest", response_model=BaseResponse[int])
async def ingest_article(
    task_id: str,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    row = await db.fetch_one(
        query="SELECT title, content FROM article WHERE taskId = :taskId AND userId = :userId AND isDelete = 0",
        values={"taskId": task_id, "userId": current_user.id},
    )
    if not row:
        return BaseResponse(code=40004, data=None, message="文章不存在")
    title = row["title"] or task_id
    content = row["content"] or ""
    tmp_dir = Path("/tmp/ai-passage-uploads") / str(current_user.id)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_file = tmp_dir / f"article_{task_id}.md"
    tmp_file.write_text(f"# {title}\n\n{content}", encoding="utf-8")
    doc_id = await RagKnowledgeService(db).ingest_text_source(
        user_id=current_user.id,
        title=title,
        source_type="article",
        source_id=task_id,
        file_path=str(tmp_file),
    )
    return BaseResponse.success(data=doc_id)


@router.post("/hotspots/ingest", response_model=BaseResponse[int])
async def ingest_hotspots(
    request: IngestHotspotsRequest,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    if not request.recordIds:
        return BaseResponse(code=40000, data=None, message="recordIds 不能为空")
    placeholders = ", ".join(f":id{i}" for i in range(len(request.recordIds)))
    values: dict = {"userId": current_user.id}
    values.update({f"id{i}": rid for i, rid in enumerate(request.recordIds)})
    rows = await db.fetch_all(
        query=f"""
            SELECT id, title, content, summary, url
            FROM hotspot_record
            WHERE id IN ({placeholders}) AND userId = :userId
        """,
        values=values,
    )
    if not rows:
        return BaseResponse(code=40004, data=None, message="未找到热点记录")
    tmp_dir = Path("/tmp/ai-passage-uploads") / str(current_user.id)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    svc = RagKnowledgeService(db)
    last_id = 0
    for row in rows:
        rid = row["id"]
        title = row["title"] or f"热点_{rid}"
        full_text = await _fetch_article_text(row["url"] or "")
        body = f"# {title}\n\n来源: {row['url'] or ''}\n\n{row['summary'] or ''}\n\n{row['content'] or ''}"
        if full_text:
            body += f"\n\n## 原文全文\n\n{full_text}"
        tmp_file = tmp_dir / f"hotspot_{rid}.md"
        tmp_file.write_text(body, encoding="utf-8")
        last_id = await svc.ingest_text_source(
            user_id=current_user.id,
            title=title,
            source_type="hotspot",
            source_id=str(rid),
            file_path=str(tmp_file),
        )
    return BaseResponse.success(data=last_id)


@router.delete("/documents/{doc_id}", response_model=BaseResponse[bool])
async def delete_knowledge_document(
    doc_id: int,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    ok = await RagKnowledgeService(db).delete_document(doc_id, current_user.id)
    return BaseResponse.success(data=ok)


@router.get("/documents/{doc_id}/chunks", response_model=BaseResponse[list])
async def get_document_chunks(
    doc_id: int,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    chunks = await RagKnowledgeService(db).get_document_chunks(doc_id, current_user.id)
    return BaseResponse.success(data=chunks)
