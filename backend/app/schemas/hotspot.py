"""热点选题模型"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


HotspotSource = Literal["weibo", "bilibili", "sogou", "bing", "hackernews", "twitter", "google", "duckduckgo"]
HotspotImportance = Literal["low", "medium", "high", "urgent"]


class HotspotPreMatch(BaseModel):
    """关键词预匹配结果"""

    matched: bool
    matched_terms: list[str] = Field(default_factory=list, alias="matchedTerms")

    class Config:
        populate_by_name = True


class HotspotAnalysis(BaseModel):
    """热点 AI 分析结果"""

    is_real: bool = Field(default=True, alias="isReal")
    relevance: int = Field(default=0, ge=0, le=100)
    relevance_reason: str = Field(default="", alias="relevanceReason")
    keyword_mentioned: bool = Field(default=False, alias="keywordMentioned")
    importance: HotspotImportance = "low"
    summary: str = ""

    class Config:
        populate_by_name = True


class HotspotRawItem(BaseModel):
    """热点原始条目和分析中间态"""

    title: str
    content: str = ""
    url: str
    source: HotspotSource
    source_id: Optional[str] = Field(default=None, alias="sourceId")
    published_at: Optional[datetime] = Field(default=None, alias="publishedAt")
    view_count: Optional[int] = Field(default=None, alias="viewCount")
    like_count: Optional[int] = Field(default=None, alias="likeCount")
    retweet_count: Optional[int] = Field(default=None, alias="retweetCount")
    reply_count: Optional[int] = Field(default=None, alias="replyCount")
    comment_count: Optional[int] = Field(default=None, alias="commentCount")
    quote_count: Optional[int] = Field(default=None, alias="quoteCount")
    danmaku_count: Optional[int] = Field(default=None, alias="danmakuCount")
    author_name: Optional[str] = Field(default=None, alias="authorName")
    author_username: Optional[str] = Field(default=None, alias="authorUsername")
    author_followers: Optional[int] = Field(default=None, alias="authorFollowers")
    author_verified: Optional[bool] = Field(default=None, alias="authorVerified")
    analysis: Optional[HotspotAnalysis] = None
    heat_score: float = Field(default=0, alias="heatScore")

    class Config:
        populate_by_name = True


class HotspotVO(BaseModel):
    """前端展示热点"""

    title: str
    content: str
    url: str
    source: HotspotSource
    published_at: Optional[str] = Field(default=None, alias="publishedAt")
    heat_score: float = Field(alias="heatScore")
    is_real: bool = Field(alias="isReal")
    relevance: int
    relevance_reason: str = Field(alias="relevanceReason")
    keyword_mentioned: bool = Field(alias="keywordMentioned")
    importance: HotspotImportance
    summary: str
    view_count: Optional[int] = Field(default=None, alias="viewCount")
    like_count: Optional[int] = Field(default=None, alias="likeCount")
    retweet_count: Optional[int] = Field(default=None, alias="retweetCount")
    comment_count: Optional[int] = Field(default=None, alias="commentCount")
    author_name: Optional[str] = Field(default=None, alias="authorName")

    class Config:
        populate_by_name = True


class TopicSuggestionVO(BaseModel):
    """热点生成的选题建议"""

    title: str
    content_description: str = Field(alias="contentDescription")
    angle: str
    viral_reason: str = Field(alias="viralReason")
    suitable_platforms: list[str] = Field(default_factory=list, alias="suitablePlatforms")
    source_hotspot_titles: list[str] = Field(default_factory=list, alias="sourceHotspotTitles")

    class Config:
        populate_by_name = True


class HotspotTopicSuggestionRequest(BaseModel):
    """生成热点选题请求"""

    keyword: str = Field(..., min_length=1, max_length=100)
    hotspots: list[HotspotVO] = Field(default_factory=list)
    limit: int = Field(default=5, ge=1, le=10)


class HotspotTopicSuggestionResponse(BaseModel):
    """生成热点选题响应"""

    keyword: str
    suggestions: list[TopicSuggestionVO] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class HotspotRadarRequest(BaseModel):
    """热点雷达扫描请求"""

    keyword: str = Field(..., min_length=1, max_length=100)
    sources: list[HotspotSource] = Field(
        default_factory=lambda: ["weibo", "bilibili", "sogou", "bing", "hackernews", "twitter", "google", "duckduckgo"]
    )
    analyze_limit: int = Field(default=20, ge=1, le=30, alias="analyzeLimit")

    class Config:
        populate_by_name = True


class HotspotRadarStatsVO(BaseModel):
    """热点雷达统计"""

    total: int = 0
    today: int = 0
    urgent: int = 0
    high_relevance: int = Field(default=0, alias="highRelevance")
    source_count: int = Field(default=0, alias="sourceCount")

    class Config:
        populate_by_name = True


class HotspotSourceFailureVO(BaseModel):
    """热点来源失败详情"""

    source: HotspotSource
    error: str


class HotspotDiagnosticVO(BaseModel):
    """热点雷达诊断日志"""

    level: Literal["info", "warning", "error"] = "info"
    stage: str
    message: str
    source: Optional[HotspotSource] = None
    count: Optional[int] = None
    elapsed_ms: Optional[int] = Field(default=None, alias="elapsedMs")

    class Config:
        populate_by_name = True


class HotspotRadarResponse(BaseModel):
    """热点雷达响应"""

    keyword: str
    expanded_keywords: list[str] = Field(default_factory=list, alias="expandedKeywords")
    stats: HotspotRadarStatsVO = Field(default_factory=HotspotRadarStatsVO)
    hotspots: list[HotspotVO] = Field(default_factory=list)
    failed_sources: list[str] = Field(default_factory=list, alias="failedSources")
    failed_source_details: list[HotspotSourceFailureVO] = Field(default_factory=list, alias="failedSourceDetails")
    diagnostics: list[HotspotDiagnosticVO] = Field(default_factory=list)

    class Config:
        populate_by_name = True
