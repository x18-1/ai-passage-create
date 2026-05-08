"""热点持续监控请求/响应模型"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class KeywordCreateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=200)
    category: Optional[str] = Field(None, max_length=100)


class KeywordVO(BaseModel):
    id: int
    text: str
    category: Optional[str] = None
    is_active: bool = Field(alias="isActive")
    hotspot_count: int = Field(default=0, alias="hotspotCount")
    create_time: Optional[datetime] = Field(None, alias="createTime")

    class Config:
        populate_by_name = True


class RecordVO(BaseModel):
    id: int
    keyword_id: Optional[int] = Field(None, alias="keywordId")
    keyword_text: Optional[str] = Field(None, alias="keywordText")
    title: str
    content: Optional[str] = None
    url: str
    source: str
    is_real: bool = Field(alias="isReal")
    relevance: int
    relevance_reason: Optional[str] = Field(None, alias="relevanceReason")
    keyword_mentioned: bool = Field(alias="keywordMentioned")
    importance: str
    summary: Optional[str] = None
    heat_score: float = Field(alias="heatScore")
    view_count: Optional[int] = Field(None, alias="viewCount")
    like_count: Optional[int] = Field(None, alias="likeCount")
    retweet_count: Optional[int] = Field(None, alias="retweetCount")
    comment_count: Optional[int] = Field(None, alias="commentCount")
    author_name: Optional[str] = Field(None, alias="authorName")
    author_username: Optional[str] = Field(None, alias="authorUsername")
    author_followers: Optional[int] = Field(None, alias="authorFollowers")
    author_verified: Optional[bool] = Field(None, alias="authorVerified")
    published_at: Optional[datetime] = Field(None, alias="publishedAt")
    create_time: datetime = Field(alias="createTime")

    class Config:
        populate_by_name = True


class RecordListRequest(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=50)
    source: Optional[str] = None
    importance: Optional[str] = None
    keyword_id: Optional[int] = Field(None, alias="keywordId")
    is_real: Optional[bool] = Field(None, alias="isReal")
    time_range: Optional[str] = Field(None, alias="timeRange")
    sort_by: str = Field(default="created_at", alias="sortBy")
    sort_order: str = Field(default="desc", alias="sortOrder")

    class Config:
        populate_by_name = True


class RecordListResponse(BaseModel):
    records: List[RecordVO]
    total: int
    page: int
    limit: int
    has_more: bool = Field(alias="hasMore")

    class Config:
        populate_by_name = True


class RecordStatsVO(BaseModel):
    total: int
    today: int
    urgent: int
    active_keywords: int = Field(alias="activeKeywords")

    class Config:
        populate_by_name = True


class NotificationVO(BaseModel):
    id: int
    type: str
    title: str
    content: Optional[str] = None
    is_read: bool = Field(alias="isRead")
    hotspot_record_id: Optional[int] = Field(None, alias="hotspotRecordId")
    create_time: datetime = Field(alias="createTime")

    class Config:
        populate_by_name = True


class NotificationListResponse(BaseModel):
    notifications: List[NotificationVO]
    unread_count: int = Field(alias="unreadCount")

    class Config:
        populate_by_name = True


class MonitorStatusVO(BaseModel):
    is_running: bool = Field(alias="isRunning")
    last_run_at: Optional[datetime] = Field(None, alias="lastRunAt")
    next_run_at: Optional[datetime] = Field(None, alias="nextRunAt")
    active_keyword_count: int = Field(alias="activeKeywordCount")

    class Config:
        populate_by_name = True
