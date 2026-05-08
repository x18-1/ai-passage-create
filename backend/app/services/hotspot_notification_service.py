"""热点站内通知服务"""

import logging
from datetime import datetime
from typing import Optional

from app.schemas.hotspot_monitor import NotificationListResponse, NotificationVO

logger = logging.getLogger(__name__)


class HotspotNotificationService:
    def __init__(self, db):
        self.db = db

    async def create_notification(self, title: str, content: Optional[str], hotspot_record_id: Optional[int]) -> int:
        row_id = await self.db.execute(
            query="""
                INSERT INTO hotspot_notification (type, title, content, isRead, hotspotRecordId, createTime)
                VALUES ('hotspot', :title, :content, 0, :hotspotRecordId, :now)
            """,
            values={
                "title": title[:300],
                "content": (content or "")[:500],
                "hotspotRecordId": hotspot_record_id,
                "now": datetime.now(),
            },
        )
        return row_id

    async def list_notifications(self, limit: int = 20, unread_only: bool = False) -> NotificationListResponse:
        where = "WHERE isRead = 0" if unread_only else ""
        rows = await self.db.fetch_all(
            query=f"""
                SELECT id, type, title, content, isRead, hotspotRecordId, createTime
                FROM hotspot_notification
                {where}
                ORDER BY createTime DESC
                LIMIT :limit
            """,
            values={"limit": limit},
        )
        unread_row = await self.db.fetch_one(
            query="SELECT COUNT(*) AS cnt FROM hotspot_notification WHERE isRead = 0",
            values={},
        )
        notifications = [
            NotificationVO(
                id=row["id"],
                type=row["type"],
                title=row["title"],
                content=row["content"],
                isRead=bool(row["isRead"]),
                hotspotRecordId=row["hotspotRecordId"],
                createTime=row["createTime"],
            )
            for row in rows
        ]
        return NotificationListResponse(
            notifications=notifications,
            unreadCount=unread_row["cnt"] if unread_row else 0,
        )

    async def mark_all_read(self) -> None:
        await self.db.execute(
            query="UPDATE hotspot_notification SET isRead = 1 WHERE isRead = 0",
            values={},
        )
