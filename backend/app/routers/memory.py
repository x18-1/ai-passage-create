"""Long-term memory routes."""

from databases import Database
from fastapi import APIRouter, Depends, Query

from app.database import get_db
from app.deps import require_login
from app.exceptions import ErrorCode, throw_if
from app.schemas.common import BaseResponse
from app.schemas.memory import MemoryCreateRequest, MemoryUpdateRequest, MemoryVO
from app.schemas.user import LoginUserVO
from app.services.memory_service import MemoryService


router = APIRouter(prefix="/memories", tags=["长期记忆"])


@router.get("", response_model=BaseResponse[list[MemoryVO]])
async def list_memories(
    memory_type: str | None = Query(None, alias="memoryType"),
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    result = await MemoryService(db).list_memories(current_user.id, memory_type)
    return BaseResponse.success(data=result)


@router.post("", response_model=BaseResponse[int])
async def create_memory(
    request: MemoryCreateRequest,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    result = await MemoryService(db).create_memory(request, current_user)
    return BaseResponse.success(data=result)


@router.patch("/{memory_id}", response_model=BaseResponse[bool])
async def update_memory(
    memory_id: int,
    request: MemoryUpdateRequest,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    ok = await MemoryService(db).update_memory(memory_id, request, current_user.id)
    throw_if(not ok, ErrorCode.NOT_FOUND_ERROR, "记忆不存在")
    return BaseResponse.success(data=True)


@router.patch("/{memory_id}/toggle", response_model=BaseResponse[bool])
async def toggle_memory(
    memory_id: int,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    result = await MemoryService(db).toggle_memory(memory_id, current_user.id)
    return BaseResponse.success(data=result)


@router.delete("/{memory_id}", response_model=BaseResponse[bool])
async def delete_memory(
    memory_id: int,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    result = await MemoryService(db).delete_memory(memory_id, current_user.id)
    return BaseResponse.success(data=result)
