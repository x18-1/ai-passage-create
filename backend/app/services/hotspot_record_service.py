"""热点记录查询/写入服务"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from app.schemas.hotspot_monitor import RecordListRequest, RecordListResponse, RecordStatsVO, RecordVO
from app.schemas.hotspot import HotspotVO

logger = logging.getLogger(__name__)

IMPORTANCE_ORDER = {"urgent": 0, "high": 1, "medium": 2, "low": 3}


class HotspotRecordService:
    def __init__(self, db):
        self.db = db

    async def url_source_exists(self, url: str, source: str) -> bool:
        row = await self.db.fetch_one(
            query="SELECT COUNT(*) AS cnt FROM hotspot_record WHERE url = :url AND source = :source",
            values={"url": url[:1024], "source": source},
        )
        return bool(row and row["cnt"] > 0)

    async def save_record(self, user_id: int, keyword_id: Optional[int], keyword_text: Optional[str], vo: HotspotVO) -> int:
        """写入热点记录（INSERT IGNORE 自动去重）。返回记录 ID，0 表示重复跳过。"""
        now = datetime.now()
        published_at: Optional[datetime] = None
        if vo.published_at:
            try:
                published_at = datetime.fromisoformat(vo.published_at)
            except (ValueError, TypeError):
                pass
        try:
            row_id = await self.db.execute(
                query="""
                    INSERT IGNORE INTO hotspot_record (
                        userId, keywordId, keywordText, title, content, url, source, sourceId,
                        isReal, relevance, relevanceReason, keywordMentioned, importance,
                        summary, heatScore, viewCount, likeCount, retweetCount, commentCount,
                        authorName, authorUsername, authorFollowers, authorVerified,
                        publishedAt, createTime
                    ) VALUES (
                        :userId, :keywordId, :keywordText, :title, :content, :url, :source, :sourceId,
                        :isReal, :relevance, :relevanceReason, :keywordMentioned, :importance,
                        :summary, :heatScore, :viewCount, :likeCount, :retweetCount, :commentCount,
                        :authorName, :authorUsername, :authorFollowers, :authorVerified,
                        :publishedAt, :createTime
                    )
                """,
                values={
                    "userId": user_id, "keywordId": keyword_id, "keywordText": keyword_text,
                    "title": vo.title[:500], "content": vo.content, "url": vo.url[:1024],
                    "source": vo.source, "sourceId": None,
                    "isReal": 1 if vo.is_real else 0,
                    "relevance": vo.relevance,
                    "relevanceReason": (vo.relevance_reason or "")[:500],
                    "keywordMentioned": 1 if vo.keyword_mentioned else 0,
                    "importance": vo.importance,
                    "summary": (vo.summary or "")[:500],
                    "heatScore": vo.heat_score or 0.0,
                    "viewCount": vo.view_count, "likeCount": vo.like_count,
                    "retweetCount": vo.retweet_count, "commentCount": vo.comment_count,
                    "authorName": vo.author_name, "authorUsername": None,
                    "authorFollowers": None, "authorVerified": None,
                    "publishedAt": published_at,
                    "createTime": now,
                },
            )
            return row_id or 0
        except Exception as exc:
            logger.warning("热点记录写入失败（可能重复） url=%s error=%s", vo.url, exc)
            return 0

    async def list_records(self, request: RecordListRequest, user_id: int) -> RecordListResponse:
        where, values = self._build_where(request, user_id)
        count_row = await self.db.fetch_one(
            query=f"SELECT COUNT(*) AS cnt FROM hotspot_record WHERE {where}",
            values=values,
        )
        total = count_row["cnt"] if count_row else 0

        db_sort = self._db_sort_clause(request)
        offset = (request.page - 1) * request.limit
        rows = await self.db.fetch_all(
            query=f"""
                SELECT id, keywordId, keywordText, title, content, url, source, isReal,
                       relevance, relevanceReason, keywordMentioned, importance, summary,
                       heatScore, viewCount, likeCount, retweetCount, commentCount,
                       authorName, authorUsername, authorFollowers, authorVerified,
                       publishedAt, createTime
                FROM hotspot_record
                WHERE {where}
                {db_sort}
                LIMIT :limit OFFSET :offset
            """,
            values={**values, "limit": request.limit, "offset": offset},
        )

        records = [self._row_to_vo(row) for row in rows]

        if request.sort_by in ("importance", "heat"):
            records = self._memory_sort(records, request.sort_by, request.sort_order)

        return RecordListResponse(
            records=records,
            total=total,
            page=request.page,
            limit=request.limit,
            hasMore=(offset + len(records)) < total,
        )

    async def get_stats(self, user_id: int) -> RecordStatsVO:
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        row = await self.db.fetch_one(
            query="""
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN createTime >= :todayStart THEN 1 ELSE 0 END) AS today,
                    SUM(CASE WHEN importance = 'urgent' THEN 1 ELSE 0 END) AS urgent
                FROM hotspot_record
                WHERE userId = :userId
            """,
            values={"userId": user_id, "todayStart": today_start},
        )
        kw_row = await self.db.fetch_one(
            query="SELECT COUNT(*) AS cnt FROM hotspot_keyword WHERE userId = :userId AND isActive = 1",
            values={"userId": user_id},
        )
        return RecordStatsVO(
            total=row["total"] or 0 if row else 0,
            today=row["today"] or 0 if row else 0,
            urgent=row["urgent"] or 0 if row else 0,
            activeKeywords=kw_row["cnt"] if kw_row else 0,
        )

    def _build_where(self, req: RecordListRequest, user_id: int):
        conditions = ["userId = :userId"]
        values: dict = {"userId": user_id}

        if req.source:
            conditions.append("source = :source")
            values["source"] = req.source

        if req.importance:
            conditions.append("importance = :importance")
            values["importance"] = req.importance

        if req.keyword_id is not None:
            conditions.append("keywordId = :keywordId")
            values["keywordId"] = req.keyword_id

        if req.is_real is not None:
            conditions.append("isReal = :isReal")
            values["isReal"] = 1 if req.is_real else 0

        if req.time_range:
            cutoff = self._time_range_cutoff(req.time_range)
            if cutoff:
                conditions.append("createTime >= :cutoff")
                values["cutoff"] = cutoff

        return " AND ".join(conditions), values

    def _db_sort_clause(self, req: RecordListRequest) -> str:
        direction = "ASC" if req.sort_order == "asc" else "DESC"
        col_map = {
            "created_at": "createTime",
            "published_at": "COALESCE(publishedAt, createTime)",
            "relevance": "relevance",
        }
        if req.sort_by in ("importance", "heat"):
            return "ORDER BY createTime DESC"
        col = col_map.get(req.sort_by, "createTime")
        return f"ORDER BY {col} {direction}"

    def _memory_sort(self, records: list, sort_by: str, sort_order: str) -> list:
        reverse = sort_order != "asc"
        if sort_by == "importance":
            return sorted(records, key=lambda r: IMPORTANCE_ORDER.get(r.importance, 4), reverse=reverse)
        if sort_by == "heat":
            return sorted(records, key=lambda r: r.heat_score, reverse=reverse)
        return records

    def _time_range_cutoff(self, time_range: str) -> Optional[datetime]:
        now = datetime.now()
        cutoffs = {
            "1h": now - timedelta(hours=1),
            "today": now.replace(hour=0, minute=0, second=0, microsecond=0),
            "7d": now - timedelta(days=7),
            "30d": now - timedelta(days=30),
        }
        return cutoffs.get(time_range)

    def _row_to_vo(self, row) -> RecordVO:
        return RecordVO(
            id=row["id"],
            keywordId=row["keywordId"],
            keywordText=row["keywordText"],
            title=row["title"],
            content=row["content"],
            url=row["url"],
            source=row["source"],
            isReal=bool(row["isReal"]),
            relevance=row["relevance"],
            relevanceReason=row["relevanceReason"],
            keywordMentioned=bool(row["keywordMentioned"]),
            importance=row["importance"],
            summary=row["summary"],
            heatScore=float(row["heatScore"] or 0),
            viewCount=row["viewCount"],
            likeCount=row["likeCount"],
            retweetCount=row["retweetCount"],
            commentCount=row["commentCount"],
            authorName=row["authorName"],
            authorUsername=row["authorUsername"],
            authorFollowers=row["authorFollowers"],
            authorVerified=bool(row["authorVerified"]) if row["authorVerified"] is not None else None,
            publishedAt=row["publishedAt"],
            createTime=row["createTime"],
        )
