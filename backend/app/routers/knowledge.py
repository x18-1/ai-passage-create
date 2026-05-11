"""Knowledge base routes."""

from pathlib import Path

from databases import Database
from fastapi import APIRouter, Depends, File, UploadFile

from app.database import get_db
from app.deps import require_login
from app.schemas.common import BaseResponse
from app.schemas.knowledge import KnowledgeDocumentVO, KnowledgeQueryRequest
from app.schemas.user import LoginUserVO
from app.services.rag_knowledge_service import RagKnowledgeService


router = APIRouter(prefix="/knowledge", tags=["知识库"])


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
