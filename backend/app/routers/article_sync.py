"""文章草稿同步记录路由"""

from typing import List

from databases import Database
from fastapi import APIRouter, Depends

from app.database import get_db
from app.deps import require_login
from app.exceptions import ErrorCode, throw_if
from app.schemas.article_sync import ArticleSyncRecordUpsertRequest, ArticleSyncRecordVO
from app.schemas.common import BaseResponse
from app.schemas.user import LoginUserVO
from app.services.article_sync_record_service import ArticleSyncRecordService

router = APIRouter(prefix="/article-sync", tags=["文章草稿同步记录"])


@router.get("/records/{task_id}", response_model=BaseResponse[List[ArticleSyncRecordVO]])
async def list_sync_records(
    task_id: str,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    """获取某篇文章的草稿同步记录"""
    throw_if(not task_id or not task_id.strip(), ErrorCode.PARAMS_ERROR, "任务ID不能为空")
    service = ArticleSyncRecordService(db)
    records = await service.list_records(task_id, current_user)
    return BaseResponse.success(data=records)


@router.post("/record", response_model=BaseResponse[bool])
async def upsert_sync_record(
    request: ArticleSyncRecordUpsertRequest,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    """创建或更新草稿同步记录"""
    service = ArticleSyncRecordService(db)
    result = await service.upsert_record(request, current_user)
    return BaseResponse.success(data=result)
