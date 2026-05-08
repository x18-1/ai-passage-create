"""热点监控服务：定时扫描关键词 → 写入 DB → 广播"""

import logging
from datetime import datetime
from typing import Optional

from app.database import database
from app.managers.hotspot_ws_manager import hotspot_ws_manager
from app.schemas.hotspot import HotspotRadarRequest
from app.services.hotspot_keyword_service import HotspotKeywordService
from app.services.hotspot_notification_service import HotspotNotificationService
from app.services.hotspot_record_service import HotspotRecordService
from app.services.hotspot_service import HotspotService

logger = logging.getLogger(__name__)

DEFAULT_SOURCES = ["weibo", "bilibili", "sogou", "bing", "hackernews", "twitter", "duckduckgo"]

_last_run_at: Optional[datetime] = None
_is_running: bool = False


class HotspotMonitorService:
    """后台扫描调度器，使用全局 database 实例（不依赖请求上下文）"""

    async def scan_all_keywords(self) -> None:
        global _is_running, _last_run_at
        if _is_running:
            logger.info("热点扫描正在进行中，跳过本次触发")
            return

        _is_running = True
        _last_run_at = datetime.now()
        logger.info("热点监控扫描开始 startAt=%s", _last_run_at)

        try:
            kw_service = HotspotKeywordService(database)
            keywords = await kw_service.get_all_active_keywords()
            if not keywords:
                logger.info("无激活关键词，跳过扫描")
                return

            logger.info("激活关键词数=%s", len(keywords))
            for kw in keywords:
                try:
                    await self._scan_one_keyword(kw["id"], kw["user_id"], kw["text"])
                except Exception as exc:
                    logger.exception("关键词扫描失败 keyword=%s error=%s", kw["text"], exc)
        finally:
            _is_running = False
            logger.info("热点监控扫描结束")

    async def _scan_one_keyword(self, keyword_id: int, user_id: int, keyword_text: str) -> None:
        logger.info("扫描关键词 text=%s userId=%s", keyword_text, user_id)

        request = HotspotRadarRequest(
            keyword=keyword_text,
            sources=DEFAULT_SOURCES,
            analyzeLimit=20,
        )
        service = HotspotService()
        result = await service.scan_radar(request)

        record_service = HotspotRecordService(database)
        notification_service = HotspotNotificationService(database)
        new_count = 0

        for vo in result.hotspots:
            record_id = await record_service.save_record(user_id, keyword_id, keyword_text, vo)
            if record_id:
                new_count += 1
                await notification_service.create_notification(
                    title=f"发现新热点：{vo.title[:50]}",
                    content=vo.summary or (vo.content[:100] if vo.content else None),
                    hotspot_record_id=record_id,
                )
                await hotspot_ws_manager.broadcast({
                    "type": "hotspot_new",
                    "importance": vo.importance,
                    "title": vo.title[:80],
                    "source": vo.source,
                    "keywordText": keyword_text,
                })

        logger.info("关键词扫描完成 keyword=%s 新增=%s", keyword_text, new_count)

    @staticmethod
    def get_status() -> dict:
        return {
            "isRunning": _is_running,
            "lastRunAt": _last_run_at.isoformat() if _last_run_at else None,
        }


# 模块级单例（供 APScheduler 调用）
monitor_service = HotspotMonitorService()
