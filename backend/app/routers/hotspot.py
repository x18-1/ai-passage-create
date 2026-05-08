"""热点选题路由"""

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.deps import require_login
from app.exceptions import ErrorCode, throw_if
from app.schemas.common import BaseResponse
from app.schemas.hotspot import (
    HotspotRadarRequest,
    HotspotRadarResponse,
    HotspotTopicSuggestionRequest,
    HotspotTopicSuggestionResponse,
)
from app.schemas.user import LoginUserVO
from app.services.hotspot_service import HotspotService

router = APIRouter(prefix="/hotspot", tags=["热点选题"])
logger = logging.getLogger(__name__)


@router.post("/radar", response_model=BaseResponse[HotspotRadarResponse])
async def scan_hotspot_radar(
    request: HotspotRadarRequest,
    current_user: LoginUserVO = Depends(require_login),
):
    """扫描热点雷达"""
    throw_if(not request.keyword or not request.keyword.strip(), ErrorCode.PARAMS_ERROR, "关键词不能为空")
    throw_if(not request.sources, ErrorCode.PARAMS_ERROR, "至少选择一个数据源")

    service = HotspotService()
    try:
        result = await service.scan_radar(request)
        return BaseResponse.success(data=result)
    except Exception as error:
        logger.exception("热点雷达接口失败 keyword=%s sources=%s error=%s", request.keyword, request.sources, error)
        raise


@router.post("/radar/stream")
async def scan_hotspot_radar_stream(
    request: HotspotRadarRequest,
    current_user: LoginUserVO = Depends(require_login),
):
    """流式扫描热点雷达，SSE 逐条推送"""
    throw_if(not request.keyword or not request.keyword.strip(), ErrorCode.PARAMS_ERROR, "关键词不能为空")
    throw_if(not request.sources, ErrorCode.PARAMS_ERROR, "至少选择一个数据源")
    service = HotspotService()
    return StreamingResponse(
        service.stream_radar(request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/topic-suggestions", response_model=BaseResponse[HotspotTopicSuggestionResponse])
async def generate_topic_suggestions(
    request: HotspotTopicSuggestionRequest,
    current_user: LoginUserVO = Depends(require_login),
):
    """根据热点生成选题建议"""
    throw_if(not request.keyword or not request.keyword.strip(), ErrorCode.PARAMS_ERROR, "关键词不能为空")
    throw_if(not request.hotspots, ErrorCode.PARAMS_ERROR, "请至少选择一个热点")

    service = HotspotService()
    try:
        result = await service.generate_topic_suggestions(request)
        return BaseResponse.success(data=result)
    except Exception as error:
        logger.exception(
            "热点选题接口失败 keyword=%s selectedCount=%s error=%s",
            request.keyword,
            len(request.hotspots),
            error,
        )
        raise
