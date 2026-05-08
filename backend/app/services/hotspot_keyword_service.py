"""热点监控关键词服务"""

import logging
from datetime import datetime
from typing import Optional

from app.schemas.hotspot_monitor import KeywordCreateRequest, KeywordVO

logger = logging.getLogger(__name__)


class HotspotKeywordService:
    def __init__(self, db):
        self.db = db

    async def create_keyword(self, request: KeywordCreateRequest, user_id: int) -> int:
        now = datetime.now()
        row_id = await self.db.execute(
            query="""
                INSERT INTO hotspot_keyword (userId, text, category, isActive, createTime, updateTime)
                VALUES (:userId, :text, :category, 1, :now, :now)
            """,
            values={"userId": user_id, "text": request.text.strip(), "category": request.category, "now": now},
        )
        logger.info("关键词创建成功 userId=%s text=%s id=%s", user_id, request.text, row_id)
        return row_id

    async def list_keywords(self, user_id: int) -> list[KeywordVO]:
        rows = await self.db.fetch_all(
            query="""
                SELECT k.id, k.text, k.category, k.isActive,
                       COUNT(r.id) AS hotspotCount,
                       k.createTime
                FROM hotspot_keyword k
                LEFT JOIN hotspot_record r ON r.keywordId = k.id
                WHERE k.userId = :userId
                GROUP BY k.id
                ORDER BY k.createTime DESC
            """,
            values={"userId": user_id},
        )
        return [KeywordVO(
            id=row["id"],
            text=row["text"],
            category=row["category"],
            isActive=bool(row["isActive"]),
            hotspotCount=row["hotspotCount"] or 0,
            createTime=row["createTime"],
        ) for row in rows]

    async def toggle_keyword(self, keyword_id: int, user_id: int) -> bool:
        """切换激活状态，返回新的 isActive 值"""
        row = await self.db.fetch_one(
            query="SELECT id, isActive FROM hotspot_keyword WHERE id = :id AND userId = :userId",
            values={"id": keyword_id, "userId": user_id},
        )
        if not row:
            return False
        new_active = 0 if row["isActive"] else 1
        await self.db.execute(
            query="UPDATE hotspot_keyword SET isActive = :active, updateTime = :now WHERE id = :id",
            values={"active": new_active, "id": keyword_id, "now": datetime.now()},
        )
        return bool(new_active)

    async def delete_keyword(self, keyword_id: int, user_id: int) -> bool:
        row = await self.db.fetch_one(
            query="SELECT id FROM hotspot_keyword WHERE id = :id AND userId = :userId",
            values={"id": keyword_id, "userId": user_id},
        )
        if not row:
            return False
        await self.db.execute(
            query="DELETE FROM hotspot_keyword WHERE id = :id",
            values={"id": keyword_id},
        )
        return True

    async def get_all_active_keywords(self) -> list[dict]:
        """获取所有用户的所有激活关键词（供后台扫描使用）"""
        rows = await self.db.fetch_all(
            query="SELECT id, userId, text FROM hotspot_keyword WHERE isActive = 1",
            values={},
        )
        return [{"id": row["id"], "user_id": row["userId"], "text": row["text"]} for row in rows]
