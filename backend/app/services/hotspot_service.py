"""热点选题编排服务"""

import asyncio
import json
import logging
from time import perf_counter
from datetime import datetime, timedelta
from typing import AsyncIterator

from openai import AsyncOpenAI

from app.config import settings

from app.schemas.hotspot import (
    HotspotAnalysis,
    HotspotDiagnosticVO,
    HotspotRadarRequest,
    HotspotRadarResponse,
    HotspotRadarStatsVO,
    HotspotRawItem,
    HotspotSource,
    HotspotSourceFailureVO,
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

    async def stream_radar(self, request: HotspotRadarRequest) -> AsyncIterator[str]:
        """流式扫描热点雷达，逐条推送 SSE 事件"""
        keyword = request.keyword.strip()

        def sse(event_type: str, payload: dict) -> str:
            return f"data: {json.dumps({'type': event_type, **payload}, ensure_ascii=False)}\n\n"

        # 1. 关键词扩展
        yield sse("stage", {"message": "关键词扩展中..."})
        expanded_keywords = await self.analysis_service.expand_keyword(keyword)
        yield sse("stage", {"message": f"关键词扩展完成，共 {len(expanded_keywords)} 个"})

        # 2. 账号检测
        account_items, _ = await self.source_service.detect_and_fetch_account(keyword)

        # 3. 并发抓取各来源，每完成一个立即推送
        source_map = {
            "bing": self.source_service.search_bing,
            "hackernews": self.source_service.search_hackernews,
            "sogou": self.source_service.search_sogou,
            "bilibili": self.source_service.search_bilibili,
            "weibo": self.source_service.search_weibo,
            "twitter": self.source_service.search_twitter,
            "duckduckgo": self.source_service.search_duckduckgo,
        }
        done_queue: asyncio.Queue = asyncio.Queue()

        async def fetch_one(source: str) -> None:
            result = await self.source_service._run_source(source, source_map[source](keyword))
            await done_queue.put(result)

        active_sources = [s for s in request.sources if s in source_map]
        tasks = [asyncio.create_task(fetch_one(s)) for s in active_sources]

        all_items: list[HotspotRawItem] = list(account_items)
        failed_sources: list[str] = []
        failure_details: list[HotspotSourceFailureVO] = []

        for _ in range(len(tasks)):
            source, items, error = await done_queue.get()
            if error:
                failed_sources.append(source)
                failure_details.append(HotspotSourceFailureVO(source=source, error=error))
                yield sse("source_error", {"source": source, "error": error})
            else:
                all_items.extend(items)
                yield sse("source_done", {"source": source, "count": len(items)})

        # 4. 去重 + 优先级排序 + 配额
        unique_items = self.analysis_service.deduplicate_results(all_items)
        prioritized = self.analysis_service.prioritize_for_analysis(unique_items, expanded_keywords)

        TWITTER_QUOTA = 15
        OTHER_QUOTA = 10
        items_for_analysis: list[HotspotRawItem] = []
        twitter_count = 0
        other_count = 0
        for item in prioritized:
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

        yield sse("stage", {"message": f"AI 分析中，共 {len(items_for_analysis)} 条..."})

        # 5. AI 分析：每完成一条就 yield（通过 asyncio.Queue 收集）
        analyze_queue: asyncio.Queue = asyncio.Queue()
        semaphore = asyncio.Semaphore(3)
        cutoff = datetime.now() - timedelta(days=7)

        async def analyze_one(item: HotspotRawItem) -> None:
            full_text = f"{item.title}\n{item.content}"
            pre_match = self.analysis_service.pre_match_keyword(full_text, expanded_keywords)
            async with semaphore:
                item.analysis = await self.analysis_service.analyze_content(full_text, keyword, pre_match)
            self.analysis_service._apply_pre_match_floor(item.analysis, pre_match)
            await analyze_queue.put(item)

        analyze_tasks = [asyncio.create_task(analyze_one(item)) for item in items_for_analysis]
        hotspot_vos: list[HotspotVO] = []

        for _ in range(len(analyze_tasks)):
            item = await analyze_queue.get()
            if item.published_at and item.published_at < cutoff:
                continue
            if not item.analysis or not item.analysis.is_real:
                continue
            if item.analysis.relevance < 50:
                continue
            if not item.analysis.keyword_mentioned and item.analysis.relevance < 65:
                continue
            item.heat_score = self.analysis_service.calc_hot_score(item)
            vo = self.analysis_service.to_vo(item)
            hotspot_vos.append(vo)
            yield sse("hotspot", {"hotspot": vo.model_dump(by_alias=True)})

        # 6. 完成
        stats = self._build_stats(hotspot_vos)
        yield sse("complete", {
            "stats": stats.model_dump(by_alias=True),
            "expandedKeywords": expanded_keywords,
            "failedSources": failed_sources,
            "failedSourceDetails": [f.model_dump(by_alias=True) for f in failure_details],
        })

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
