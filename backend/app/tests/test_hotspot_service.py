import asyncio
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
services_package = types.ModuleType("app.services")
services_package.__path__ = [str(Path(__file__).resolve().parents[1] / "services")]
sys.modules.setdefault("app.services", services_package)

from app.schemas.hotspot import (
    HotspotAnalysis,
    HotspotRadarRequest,
    HotspotRawItem,
    HotspotSourceFailureVO,
    HotspotTopicSuggestionRequest,
    HotspotVO,
)

SERVICE_PATH = Path(__file__).resolve().parents[1] / "services" / "hotspot_service.py"
spec = __import__("importlib.util").util.spec_from_file_location("hotspot_service", SERVICE_PATH)
service_module = __import__("importlib.util").util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(service_module)
HotspotService = service_module.HotspotService


class FakeSourceService:
    async def search_sources(self, keyword, sources):
        return [
            HotspotRawItem(
                title="AI 编程热点",
                content="AI 编程正在成为新的内容热点",
                url="https://example.com/ai",
                source="bing",
            )
        ], ["twitter"], [HotspotSourceFailureVO(source="twitter", error="API key missing")]


class FakeAnalysisService:
    def __init__(self):
        self.suggestion_hotspots = None

    async def expand_keyword(self, keyword):
        return [keyword, "AI"]

    def deduplicate_results(self, items):
        return items

    def prioritize_for_analysis(self, items, expanded_keywords):
        return items

    async def analyze_items(self, keyword, expanded_keywords, items):
        for item in items:
            item.analysis = HotspotAnalysis(
                isReal=True,
                relevance=88,
                relevanceReason="直接讨论 AI 编程",
                keywordMentioned=True,
                importance="high",
                summary="AI 编程热点摘要",
            )
        return items

    def filter_and_rank(self, items):
        for item in items:
            item.heat_score = 100
        return items

    def to_vo(self, item):
        from app.services.hotspot_analysis_service import HotspotAnalysisService

        return HotspotAnalysisService(ai_client=None).to_vo(item)

    async def generate_topic_suggestions(self, keyword, hotspots, limit):
        self.suggestion_hotspots = hotspots
        from app.schemas.hotspot import TopicSuggestionVO

        return [
            TopicSuggestionVO(
                title=f"{keyword}选题",
                contentDescription="内容描述",
                angle="趋势解读",
                viralReason="热点强",
                suitablePlatforms=["公众号"],
                sourceHotspotTitles=[hotspots[0].title],
            )
        ]


def test_scan_radar_returns_hotspots_stats_and_failed_sources():
    async def run():
        service = HotspotService(
            ai_client=None,
            source_service=FakeSourceService(),
            analysis_service=FakeAnalysisService(),
        )

        result = await service.scan_radar(HotspotRadarRequest(keyword="AI 编程", sources=["bing", "twitter"]))

        assert result.keyword == "AI 编程"
        assert result.stats.total == 1
        assert result.stats.high_relevance == 1
        assert result.failed_sources == ["twitter"]
        assert result.failed_source_details[0].error == "API key missing"
        assert any(item.stage == "fetch_sources" and item.level == "error" for item in result.diagnostics)
        assert result.hotspots[0].title == "AI 编程热点"

    asyncio.run(run())


def test_generate_topic_suggestions_uses_selected_hotspots_without_searching_sources():
    async def run():
        fake_analysis = FakeAnalysisService()
        service = HotspotService(ai_client=None, source_service=FakeSourceService(), analysis_service=fake_analysis)
        selected = HotspotVO(
            title="已选热点",
            content="热点内容",
            url="https://example.com/selected",
            source="bing",
            heatScore=120,
            isReal=True,
            relevance=90,
            relevanceReason="高度相关",
            keywordMentioned=True,
            importance="high",
            summary="摘要",
            likeCount=10,
            authorName="作者",
        )

        result = await service.generate_topic_suggestions(
            HotspotTopicSuggestionRequest(keyword="AI 编程", hotspots=[selected], limit=3)
        )

        assert result.suggestions[0].source_hotspot_titles == ["已选热点"]
        assert fake_analysis.suggestion_hotspots[0].title == "已选热点"
        assert fake_analysis.suggestion_hotspots[0].analysis.summary == "摘要"
        assert fake_analysis.suggestion_hotspots[0].analysis.relevance == 90
        assert fake_analysis.suggestion_hotspots[0].like_count == 10

    asyncio.run(run())


def test_generate_topic_suggestions_sorts_selected_hotspots_by_heat_and_relevance():
    async def run():
        fake_analysis = FakeAnalysisService()
        service = HotspotService(ai_client=None, source_service=FakeSourceService(), analysis_service=fake_analysis)
        low_heat = HotspotVO(
            title="低热热点",
            content="热点内容",
            url="https://example.com/low",
            source="bing",
            heatScore=20,
            isReal=True,
            relevance=99,
            relevanceReason="相关",
            keywordMentioned=True,
            importance="high",
            summary="低热摘要",
        )
        high_heat = HotspotVO(
            title="高热热点",
            content="热点内容",
            url="https://example.com/high",
            source="weibo",
            heatScore=120,
            isReal=True,
            relevance=80,
            relevanceReason="相关",
            keywordMentioned=True,
            importance="medium",
            summary="高热摘要",
        )

        result = await service.generate_topic_suggestions(
            HotspotTopicSuggestionRequest(keyword="AI 编程", hotspots=[low_heat, high_heat], limit=3)
        )

        assert result.suggestions[0].source_hotspot_titles == ["高热热点"]
        assert fake_analysis.suggestion_hotspots[0].title == "高热热点"

    asyncio.run(run())


def test_scan_radar_applies_twitter_quota_15_and_other_quota_10():
    async def run():
        twitter_items = [
            HotspotRawItem(title=f"twitter_{i}", content="c", url=f"https://t.co/{i}", source="twitter")
            for i in range(16)
        ]
        other_items = [
            HotspotRawItem(title=f"bing_{i}", content="c", url=f"https://bing.com/{i}", source="bing")
            for i in range(12)
        ]
        analyzed_items: list[HotspotRawItem] = []

        class QuotaFakeAnalysis(FakeAnalysisService):
            def prioritize_for_analysis(self, items, expanded_keywords):
                return items  # 保持传入顺序

            async def analyze_items(self, keyword, expanded_keywords, items):
                analyzed_items.extend(items)
                for item in items:
                    item.analysis = HotspotAnalysis(
                        isReal=True,
                        relevance=88,
                        relevanceReason="直接相关",
                        keywordMentioned=True,
                        importance="high",
                        summary="摘要",
                    )
                return items

        class QuotaFakeSource(FakeSourceService):
            async def search_sources(self, keyword, sources):
                return twitter_items + other_items, [], []

        service = HotspotService(
            ai_client=None,
            source_service=QuotaFakeSource(),
            analysis_service=QuotaFakeAnalysis(),
        )
        await service.scan_radar(HotspotRadarRequest(keyword="test", sources=["twitter", "bing"]))

        twitter_analyzed = [i for i in analyzed_items if i.source == "twitter"]
        other_analyzed = [i for i in analyzed_items if i.source != "twitter"]
        assert len(twitter_analyzed) == 15, f"Expected 15 twitter, got {len(twitter_analyzed)}"
        assert len(other_analyzed) == 10, f"Expected 10 other, got {len(other_analyzed)}"

    asyncio.run(run())
