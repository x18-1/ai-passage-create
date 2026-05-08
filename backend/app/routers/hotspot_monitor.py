"""热点持续监控路由"""

import asyncio
import logging

from databases import Database
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query

from app.database import get_db
from app.deps import require_login
from app.exceptions import ErrorCode, throw_if
from app.managers.hotspot_ws_manager import hotspot_ws_manager
from app.schemas.common import BaseResponse
from app.schemas.hotspot_monitor import (
    KeywordCreateRequest,
    KeywordVO,
    MonitorStatusVO,
    NotificationListResponse,
    RecordListResponse,
    RecordStatsVO,
)
from app.schemas.user import LoginUserVO
from app.services.hotspot_keyword_service import HotspotKeywordService
from app.services.hotspot_monitor_service import monitor_service
from app.services.hotspot_notification_service import HotspotNotificationService
from app.services.hotspot_record_service import HotspotRecordService

router = APIRouter(prefix="/hotspot", tags=["热点监控"])
logger = logging.getLogger(__name__)


# ─── 关键词 ─────────────────────────────────────────────────
@router.get("/keywords", response_model=BaseResponse[list[KeywordVO]])
async def list_keywords(
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    svc = HotspotKeywordService(db)
    result = await svc.list_keywords(current_user.id)
    return BaseResponse.success(data=result)


@router.post("/keywords", response_model=BaseResponse[int])
async def create_keyword(
    request: KeywordCreateRequest,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    throw_if(not request.text or not request.text.strip(), ErrorCode.PARAMS_ERROR, "关键词不能为空")
    svc = HotspotKeywordService(db)
    try:
        row_id = await svc.create_keyword(request, current_user.id)
        return BaseResponse.success(data=row_id)
    except Exception as exc:
        if "Duplicate" in str(exc) or "1062" in str(exc):
            throw_if(True, ErrorCode.PARAMS_ERROR, "该关键词已存在")
        raise


@router.patch("/keywords/{keyword_id}/toggle", response_model=BaseResponse[bool])
async def toggle_keyword(
    keyword_id: int,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    svc = HotspotKeywordService(db)
    new_active = await svc.toggle_keyword(keyword_id, current_user.id)
    return BaseResponse.success(data=new_active)


@router.delete("/keywords/{keyword_id}", response_model=BaseResponse[bool])
async def delete_keyword(
    keyword_id: int,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    svc = HotspotKeywordService(db)
    ok = await svc.delete_keyword(keyword_id, current_user.id)
    throw_if(not ok, ErrorCode.NOT_FOUND_ERROR, "关键词不存在")
    return BaseResponse.success(data=True)


# ─── 热点记录 ────────────────────────────────────────────────
@router.get("/records", response_model=BaseResponse[RecordListResponse])
async def list_records(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=50),
    source: str | None = None,
    importance: str | None = None,
    keywordId: int | None = None,
    isReal: bool | None = None,
    timeRange: str | None = None,
    sortBy: str = "created_at",
    sortOrder: str = "desc",
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    from app.schemas.hotspot_monitor import RecordListRequest
    req = RecordListRequest(
        page=page, limit=limit, source=source, importance=importance,
        keywordId=keywordId, isReal=isReal, timeRange=timeRange,
        sortBy=sortBy, sortOrder=sortOrder,
    )
    svc = HotspotRecordService(db)
    result = await svc.list_records(req, current_user.id)
    return BaseResponse.success(data=result)


@router.get("/records/stats", response_model=BaseResponse[RecordStatsVO])
async def get_record_stats(
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    svc = HotspotRecordService(db)
    stats = await svc.get_stats(current_user.id)
    return BaseResponse.success(data=stats)


# ─── 通知 ────────────────────────────────────────────────────
@router.get("/notifications", response_model=BaseResponse[NotificationListResponse])
async def list_notifications(
    limit: int = Query(default=20, ge=1, le=100),
    unreadOnly: bool = False,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    svc = HotspotNotificationService(db)
    result = await svc.list_notifications(limit=limit, unread_only=unreadOnly)
    return BaseResponse.success(data=result)


@router.patch("/notifications/read-all", response_model=BaseResponse[bool])
async def mark_all_notifications_read(
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    svc = HotspotNotificationService(db)
    await svc.mark_all_read()
    return BaseResponse.success(data=True)


# ─── 监控控制 ────────────────────────────────────────────────
@router.post("/monitor/trigger", response_model=BaseResponse[bool])
async def trigger_monitor(
    current_user: LoginUserVO = Depends(require_login),
):
    """立即触发一次全量扫描（异步，不等待完成）"""
    asyncio.create_task(monitor_service.scan_all_keywords())
    return BaseResponse.success(data=True, message="扫描任务已触发")


@router.get("/monitor/status", response_model=BaseResponse[MonitorStatusVO])
async def get_monitor_status(
    current_user: LoginUserVO = Depends(require_login),
):
    status = monitor_service.get_status()
    return BaseResponse.success(data=MonitorStatusVO(
        isRunning=status["isRunning"],
        lastRunAt=status["lastRunAt"],
        nextRunAt=None,
        activeKeywordCount=0,
    ))


# ─── WebSocket ───────────────────────────────────────────────
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await hotspot_ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == '{"type":"ping"}':
                await websocket.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        hotspot_ws_manager.disconnect(websocket)
    except Exception:
        hotspot_ws_manager.disconnect(websocket)
