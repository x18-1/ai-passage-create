import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.schemas.hotspot import HotspotAnalysis, HotspotRawItem

SERVICE_PATH = Path(__file__).resolve().parents[1] / "services" / "hotspot_analysis_service.py"
spec = __import__("importlib.util").util.spec_from_file_location("hotspot_analysis_service", SERVICE_PATH)
service_module = __import__("importlib.util").util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(service_module)
HotspotAnalysisService = service_module.HotspotAnalysisService


def test_expand_keyword_extracts_core_terms_without_ai():
    service = HotspotAnalysisService(ai_client=None)

    result = service.expand_keyword_locally("Claude Sonnet 4.6")

    assert "Claude Sonnet 4.6" in result
    assert "Claude" in result
    assert "Sonnet" in result
    assert "Claude Sonnet" in result


def test_pre_match_keyword_matches_variants_case_insensitively():
    service = HotspotAnalysisService(ai_client=None)

    result = service.pre_match_keyword(
        "CLAUDE SONNET 4.6 is now stronger at coding",
        ["claude sonnet 4.6", "Anthropic Sonnet"],
    )

    assert result.matched is True
    assert result.matched_terms == ["claude sonnet 4.6"]


def test_deduplicate_results_uses_normalized_url_and_title():
    service = HotspotAnalysisService(ai_client=None)
    items = [
        HotspotRawItem(title="OpenAI 发布新模型", content="a", url="https://www.example.com/a/", source="bing"),
        HotspotRawItem(title="OpenAI 发布新模型", content="b", url="https://example.com/a", source="sogou"),
        HotspotRawItem(title="Claude 更新", content="c", url="https://example.com/b", source="bing"),
    ]

    result = service.deduplicate_results(items)

    assert [item.title for item in result] == ["OpenAI 发布新模型", "Claude 更新"]


def test_filter_and_rank_prefers_interaction_over_raw_views():
    service = HotspotAnalysisService(ai_client=None)
    now = datetime.now()
    low_likes_high_views = HotspotRawItem(
        title="低互动高浏览",
        content="content",
        url="https://example.com/low",
        source="twitter",
        view_count=10_000_000,
        like_count=561,
        published_at=now,
        analysis=HotspotAnalysis(is_real=True, relevance=90, keyword_mentioned=True, importance="high", summary="summary"),
    )
    high_likes_low_views = HotspotRawItem(
        title="高互动低浏览",
        content="content",
        url="https://example.com/high",
        source="twitter",
        view_count=100_000,
        like_count=11_611,
        published_at=now,
        analysis=HotspotAnalysis(is_real=True, relevance=90, keyword_mentioned=True, importance="high", summary="summary"),
    )

    result = service.filter_and_rank([low_likes_high_views, high_likes_low_views])

    assert result[0].title == "高互动低浏览"


def test_filter_and_rank_removes_stale_and_low_relevance_items():
    service = HotspotAnalysisService(ai_client=None)
    fresh = datetime.now() - timedelta(hours=2)
    stale = datetime.now() - timedelta(days=10)
    items = [
        HotspotRawItem(
            title="fresh",
            content="content",
            url="https://example.com/fresh",
            source="bing",
            published_at=fresh,
            analysis=HotspotAnalysis(is_real=True, relevance=80, keyword_mentioned=True, importance="medium", summary="ok"),
        ),
        HotspotRawItem(
            title="stale",
            content="content",
            url="https://example.com/stale",
            source="bing",
            published_at=stale,
            analysis=HotspotAnalysis(is_real=True, relevance=90, keyword_mentioned=True, importance="high", summary="old"),
        ),
        HotspotRawItem(
            title="low relevance",
            content="content",
            url="https://example.com/low",
            source="bing",
            published_at=fresh,
            analysis=HotspotAnalysis(is_real=True, relevance=40, keyword_mentioned=True, importance="low", summary="low"),
        ),
        HotspotRawItem(
            title="not mentioned below strict threshold",
            content="content",
            url="https://example.com/strict",
            source="bing",
            published_at=fresh,
            analysis=HotspotAnalysis(is_real=True, relevance=60, keyword_mentioned=False, importance="medium", summary="strict"),
        ),
    ]

    result = service.filter_and_rank(items)

    assert [item.title for item in result] == ["fresh"]


def test_generate_fallback_suggestions_returns_copy_ready_topics():
    async def run():
        service = HotspotAnalysisService(ai_client=None)
        items = [
            HotspotRawItem(
                title="Claude Code 发布新能力",
                content="Claude Code 可以自动处理更复杂的工程任务",
                url="https://example.com/claude",
                source="bing",
                analysis=HotspotAnalysis(
                    is_real=True,
                    relevance=90,
                    keyword_mentioned=True,
                    importance="high",
                    summary="Claude Code 工程能力更新",
                ),
            )
        ]

        suggestions = await service.generate_topic_suggestions("AI 编程", items, limit=3)

        assert len(suggestions) == 1
        assert "AI 编程" in suggestions[0].title
        assert suggestions[0].content_description
        assert suggestions[0].source_hotspot_titles == ["Claude Code 发布新能力"]

    asyncio.run(run())


def test_expand_keyword_caches_result_and_calls_ai_only_once():
    async def run():
        call_count = 0

        class FakeChatCompletions:
            async def create(self, **kwargs):
                nonlocal call_count
                call_count += 1

                class Msg:
                    content = '["Claude Sonnet 4.6", "Claude", "Sonnet", "claude-sonnet"]'

                class Choice:
                    message = Msg()

                class Resp:
                    choices = [Choice()]

                return Resp()

        class FakeChat:
            completions = FakeChatCompletions()

        class FakeClient:
            chat = FakeChat()

        service = HotspotAnalysisService(ai_client=FakeClient())
        result1 = await service.expand_keyword("Claude Sonnet 4.6")
        result2 = await service.expand_keyword("Claude Sonnet 4.6")

        assert call_count == 1, f"AI should be called only once, got {call_count}"
        assert result1 == result2
        assert "Claude Sonnet 4.6" in result1
        assert "Claude" in result1

    asyncio.run(run())
