"""热点选题编排服务"""

import logging
from time import perf_counter
from datetime import datetime

from openai import AsyncOpenAI

from app.config import settings

from app.schemas.hotspot import (
    HotspotAnalysis,
    HotspotDiagnosticVO,
    HotspotRadarRequest,
    HotspotRadarResponse,
    HotspotRadarStatsVO,
    HotspotRawItem,
    HotspotTopicSuggestionRequest,
    HotspotTopicSuggestionResponse,
    HotspotVO,
)
from app.services.hotspot_analysis_service import HotspotAnalysisService

logger = logging.getLogger(__name__)


class HotspotService:
    """热点选题服务"""

    def __init__(self, ai_client=None, source_service=None, analysis_service=None):
        resolved_ai_client = ai_client if ai_client is not None else (AsyncOpenAI(
            api_key=settings.dashscope_api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        ) if settings.dashscope_api_key else None)
        self.analysis_service = analysis_service or HotspotAnalysisService(ai_client=resolved_ai_client)
        if source_service is not None:
            self.source_service = source_service
        else:
            from app.services.hotspot_sources import HotspotSourceService

            self.source_service = HotspotSourceService()

    async def generate_topic_suggestions(
        self,
        request: HotspotTopicSuggestionRequest,
    ) -> HotspotTopicSuggestionResponse:
        start = perf_counter()
        keyword = request.keyword.strip()
        logger.info(
            "热点选题生成开始 keyword=%s selectedCount=%s limit=%s",
            keyword,
            len(request.hotspots),
            request.limit,
        )
        selected_items = [self._vo_to_raw_item(item) for item in request.hotspots]
        ranked_items = sorted(
            selected_items,
            key=lambda item: (-(item.heat_score or 0), -(item.analysis.relevance if item.analysis else 0)),
        )
        suggestions = await self.analysis_service.generate_topic_suggestions(keyword, ranked_items, request.limit)
        logger.info(
            "热点选题生成完成 keyword=%s selectedCount=%s suggestionCount=%s elapsedMs=%s",
            keyword,
            len(request.hotspots),
            len(suggestions),
            int((perf_counter() - start) * 1000),
        )

        return HotspotTopicSuggestionResponse(
            keyword=keyword,
            suggestions=suggestions,
        )

    async def scan_radar(self, request: HotspotRadarRequest) -> HotspotRadarResponse:
        """扫描热点雷达，不生成选题"""
        total_start = perf_counter()
        diagnostics: list[HotspotDiagnosticVO] = []
        keyword = request.keyword.strip()
        logger.info(
            "热点雷达扫描开始 keyword=%s sources=%s analyzeLimit=%s",
            keyword,
            request.sources,
            request.analyze_limit,
        )

        stage_start = perf_counter()
        expanded_keywords = await self.analysis_service.expand_keyword(keyword)
        diagnostics.append(
            HotspotDiagnosticVO(
                stage="expand_keyword",
                message=f"关键词扩展完成，共 {len(expanded_keywords)} 个检索词",
                count=len(expanded_keywords),
                elapsedMs=self._elapsed_ms(stage_start),
            )
        )

        stage_start = perf_counter()
        raw_items, failed_sources, failed_source_details = await self.source_service.search_sources(keyword, request.sources)
        diagnostics.append(
            HotspotDiagnosticVO(
                level="warning" if failed_sources else "info",
                stage="fetch_sources",
                message=f"来源抓取完成，原始结果 {len(raw_items)} 条，失败来源 {len(failed_sources)} 个",
                count=len(raw_items),
                elapsedMs=self._elapsed_ms(stage_start),
            )
        )
        for failure in failed_source_details:
            diagnostics.append(
                HotspotDiagnosticVO(
                    level="error",
                    stage="fetch_sources",
                    source=failure.source,
                    message=f"{failure.source} 抓取失败：{failure.error}",
                )
            )

        stage_start = perf_counter()
        unique_items = self.analysis_service.deduplicate_results(raw_items)
        prioritized_items = self.analysis_service.prioritize_for_analysis(unique_items, expanded_keywords)
        diagnostics.append(
            HotspotDiagnosticVO(
                stage="deduplicate",
                message=f"去重和候选排序完成，{len(raw_items)} 条原始结果变为 {len(prioritized_items)} 条",
                count=len(prioritized_items),
                elapsedMs=self._elapsed_ms(stage_start),
            )
        )

        stage_start = perf_counter()
        TWITTER_QUOTA = 15
        OTHER_QUOTA = 10
        items_for_analysis: list[HotspotRawItem] = []
        twitter_count = 0
        other_count = 0
        for item in prioritized_items:
            if item.source == "twitter":
                if twitter_count < TWITTER_QUOTA:
                    items_for_analysis.append(item)
                    twitter_count += 1
            else:
                if other_count < OTHER_QUOTA:
                    items_for_analysis.append(item)
                    other_count += 1
            if twitter_count >= TWITTER_QUOTA and other_count >= OTHER_QUOTA:
                break
        analyzed_items = await self.analysis_service.analyze_items(
            keyword,
            expanded_keywords,
            items_for_analysis,
        )
        diagnostics.append(
            HotspotDiagnosticVO(
                stage="analyze",
                message=f"AI 分析完成，共分析 {len(analyzed_items)} 条",
                count=len(analyzed_items),
                elapsedMs=self._elapsed_ms(stage_start),
            )
        )

        stage_start = perf_counter()
        ranked_items = self.analysis_service.filter_and_rank(analyzed_items)
        hotspot_vos = [self.analysis_service.to_vo(item) for item in ranked_items[:20]]
        diagnostics.append(
            HotspotDiagnosticVO(
                stage="filter_rank",
                message=f"过滤排序完成，命中 {len(hotspot_vos)} 条可用热点",
                count=len(hotspot_vos),
                elapsedMs=self._elapsed_ms(stage_start),
            )
        )
        logger.info(
            "热点雷达扫描完成 keyword=%s raw=%s unique=%s analyzed=%s final=%s failedSources=%s elapsedMs=%s",
            keyword,
            len(raw_items),
            len(unique_items),
            len(analyzed_items),
            len(hotspot_vos),
            failed_sources,
            int((perf_counter() - total_start) * 1000),
        )

        return HotspotRadarResponse(
            keyword=keyword,
            expandedKeywords=expanded_keywords,
            stats=self._build_stats(hotspot_vos),
            hotspots=hotspot_vos,
            failedSources=failed_sources,
            failedSourceDetails=failed_source_details,
            diagnostics=diagnostics,
        )

    def _build_stats(self, hotspots) -> HotspotRadarStatsVO:
        today = datetime.now().date()
        return HotspotRadarStatsVO(
            total=len(hotspots),
            today=sum(1 for item in hotspots if item.published_at and datetime.fromisoformat(item.published_at).date() == today),
            urgent=sum(1 for item in hotspots if item.importance == "urgent"),
            highRelevance=sum(1 for item in hotspots if item.relevance >= 80),
            sourceCount=len({item.source for item in hotspots}),
        )

    def _elapsed_ms(self, start: float) -> int:
        return int((perf_counter() - start) * 1000)

    def _vo_to_raw_item(self, item: HotspotVO) -> HotspotRawItem:
        return HotspotRawItem(
            title=item.title,
            content=item.content,
            url=item.url,
            source=item.source,
            publishedAt=item.published_at,
            viewCount=item.view_count,
            likeCount=item.like_count,
            retweetCount=item.retweet_count,
            commentCount=item.comment_count,
            authorName=item.author_name,
            heatScore=item.heat_score,
            analysis=HotspotAnalysis(
                isReal=item.is_real,
                relevance=item.relevance,
                relevanceReason=item.relevance_reason,
                keywordMentioned=item.keyword_mentioned,
                importance=item.importance,
                summary=item.summary,
            ),
        )
