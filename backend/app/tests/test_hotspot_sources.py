import asyncio
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.schemas.hotspot import HotspotRawItem

SOURCE_PATH = Path(__file__).resolve().parents[1] / "services" / "hotspot_sources.py"
spec = __import__("importlib.util").util.spec_from_file_location("hotspot_sources", SOURCE_PATH)
source_module = __import__("importlib.util").util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(source_module)
HotspotSourceService = source_module.HotspotSourceService
RateLimiter = source_module.RateLimiter
get_random_user_agent = source_module.get_random_user_agent
USER_AGENTS = source_module.USER_AGENTS


def test_rate_limiter_waits_min_interval_between_calls():
    async def run():
        limiter = RateLimiter(200)  # 200ms，测试用
        await limiter.wait()        # 第一次，直接通过
        t0 = time.monotonic()
        await limiter.wait()        # 第二次，应等待 ≥180ms
        elapsed_ms = (time.monotonic() - t0) * 1000
        assert elapsed_ms >= 180, f"Expected ≥180ms, got {elapsed_ms:.0f}ms"

    asyncio.run(run())


def test_get_random_user_agent_returns_value_from_list():
    ua = get_random_user_agent()
    assert ua in USER_AGENTS


def test_get_random_user_agent_varies_over_many_calls():
    seen = {get_random_user_agent() for _ in range(60)}
    assert len(seen) > 1, "UA should vary across calls"


def test_twitter_filter_removes_low_engagement_tweets():
    service = HotspotSourceService()
    tweets = [
        {
            "id": "1", "text": "Great tweet about AI",
            "url": "https://twitter.com/x/1",
            "createdAt": "2024-01-01T00:00:00Z",
            "viewCount": 1000, "likeCount": 20, "retweetCount": 10,
            "replyCount": 5, "quoteCount": 2, "type": "tweet",
            "author": {"name": "User", "userName": "user1", "followers": 200, "isBlueVerified": False},
        },
        {
            "id": "2", "text": "Low engagement tweet",
            "url": "https://twitter.com/x/2",
            "createdAt": "2024-01-01T00:00:00Z",
            "viewCount": 50, "likeCount": 1, "retweetCount": 0,
            "replyCount": 0, "quoteCount": 0, "type": "tweet",
            "author": {"name": "Nobody", "userName": "nobody", "followers": 5, "isBlueVerified": False},
        },
    ]
    result = service._filter_and_rank_tweets(tweets)
    assert len(result) == 1
    assert result[0]["id"] == "1"


def test_twitter_filter_halves_thresholds_for_blue_verified():
    service = HotspotSourceService()
    tweets = [
        {
            "id": "1", "text": "Verified user tweet about AI",
            "url": "https://twitter.com/x/1",
            "createdAt": "2024-01-01T00:00:00Z",
            "viewCount": 300, "likeCount": 6, "retweetCount": 3,
            "replyCount": 0, "quoteCount": 0, "type": "tweet",
            "author": {"name": "Verified", "userName": "vuser", "followers": 60, "isBlueVerified": True},
        }
    ]
    result = service._filter_and_rank_tweets(tweets)
    assert len(result) == 1  # 蓝V阈值减半，此条应通过


def test_twitter_filter_removes_reply_tweets():
    service = HotspotSourceService()
    tweets = [
        {
            "id": "1", "text": "@someuser this is a reply",
            "url": "https://twitter.com/x/1",
            "createdAt": "2024-01-01T00:00:00Z",
            "viewCount": 10000, "likeCount": 100, "retweetCount": 50,
            "replyCount": 10, "quoteCount": 5, "type": "tweet",
            "author": {"name": "User", "userName": "user1", "followers": 1000, "isBlueVerified": False},
        },
        {
            "id": "2", "text": "This is a reply tweet",
            "url": "https://twitter.com/x/2",
            "createdAt": "2024-01-01T00:00:00Z",
            "viewCount": 10000, "likeCount": 100, "retweetCount": 50,
            "replyCount": 10, "quoteCount": 5, "type": "reply",
            "author": {"name": "User2", "userName": "user2", "followers": 1000, "isBlueVerified": False},
        },
    ]
    result = service._filter_and_rank_tweets(tweets)
    assert len(result) == 0  # 两条都应被过滤


def test_twitter_filter_sorts_by_quality_score():
    service = HotspotSourceService()
    tweets = [
        {
            "id": "low", "text": "Low quality tweet",
            "url": "https://twitter.com/x/low",
            "createdAt": "2024-01-01T00:00:00Z",
            "viewCount": 600, "likeCount": 15, "retweetCount": 8,
            "replyCount": 2, "quoteCount": 1, "type": "tweet",
            "author": {"name": "Low", "userName": "low", "followers": 150, "isBlueVerified": False},
        },
        {
            "id": "high", "text": "High quality tweet",
            "url": "https://twitter.com/x/high",
            "createdAt": "2024-01-01T00:00:00Z",
            "viewCount": 5000, "likeCount": 500, "retweetCount": 200,
            "replyCount": 30, "quoteCount": 10, "type": "tweet",
            "author": {"name": "High", "userName": "high", "followers": 500, "isBlueVerified": False},
        },
    ]
    result = service._filter_and_rank_tweets(tweets)
    assert result[0]["id"] == "high"


def test_detect_account_returns_empty_when_no_matching_bilibili_user():
    async def run():
        service = HotspotSourceService()
        with patch.object(service, "_search_bilibili_user", new=AsyncMock(return_value=[])):
            items, accounts = await service.detect_and_fetch_account("some random keyword xyz")
        assert items == []
        assert accounts == []

    asyncio.run(run())


def test_detect_account_skips_users_with_too_few_followers():
    async def run():
        service = HotspotSourceService()
        mock_users = [{"uname": "ai编程", "mid": 123, "fans": 500}]
        with patch.object(service, "_search_bilibili_user", new=AsyncMock(return_value=mock_users)):
            items, accounts = await service.detect_and_fetch_account("AI编程")
        assert accounts == []
        assert items == []

    asyncio.run(run())


def test_detect_account_fetches_videos_when_account_matches():
    async def run():
        service = HotspotSourceService()
        mock_users = [{"uname": "AI编程小王子", "mid": 999, "fans": 50000}]
        mock_videos = [
            HotspotRawItem(
                title="AI编程入门教程",
                content="学习AI编程",
                url="https://www.bilibili.com/video/BV1",
                source="bilibili",
            )
        ]
        with (
            patch.object(service, "_search_bilibili_user", new=AsyncMock(return_value=mock_users)),
            patch.object(service, "_fetch_bilibili_user_videos", new=AsyncMock(return_value=mock_videos)),
        ):
            items, accounts = await service.detect_and_fetch_account("AI编程")
        assert len(accounts) == 1
        assert accounts[0]["platform"] == "bilibili"
        assert accounts[0]["followers"] == 50000
        assert len(items) == 1
        assert items[0].title == "AI编程入门教程"

    asyncio.run(run())
