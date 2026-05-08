"""热点来源抓取服务"""

import asyncio
import html
import logging
import os
import random
import re
import time as _time
import uuid
from time import perf_counter
from datetime import datetime, timedelta, timezone
from typing import Callable
from urllib.parse import parse_qs, unquote, urlparse

import httpx
from bs4 import BeautifulSoup

from app.schemas.hotspot import HotspotRawItem, HotspotSource, HotspotSourceFailureVO

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]


def get_random_user_agent() -> str:
    return random.choice(USER_AGENTS)


class RateLimiter:
    def __init__(self, min_interval_ms: int):
        self._min_interval = min_interval_ms / 1000.0
        self._last = 0.0

    async def wait(self) -> None:
        elapsed = _time.monotonic() - self._last
        remaining = self._min_interval - elapsed
        if remaining > 0:
            await asyncio.sleep(remaining)
        self._last = _time.monotonic()


# 模块级限速器（跨请求共享，防止同进程内并发触发封禁）
_sogou_limiter = RateLimiter(3000)
_bilibili_limiter = RateLimiter(2000)
_weibo_limiter = RateLimiter(3000)
_bing_limiter = RateLimiter(5000)
_hackernews_limiter = RateLimiter(1000)


class HotspotSourceService:
    """多来源热点抓取"""

    def __init__(self):
        self.timeout = httpx.Timeout(15.0)

    async def search_sources(
        self,
        keyword: str,
        sources: list[HotspotSource],
    ) -> tuple[list[HotspotRawItem], list[str], list[HotspotSourceFailureVO]]:
        """并发搜索多个来源"""
        source_map: dict[str, Callable[[str], object]] = {
            "bing": self.search_bing,
            "hackernews": self.search_hackernews,
            "sogou": self.search_sogou,
            "bilibili": self.search_bilibili,
            "weibo": self.search_weibo,
            "twitter": self.search_twitter,
        }
        tasks = [self._run_source(source, source_map[source](keyword)) for source in sources if source in source_map]
        results = await asyncio.gather(*tasks)

        items: list[HotspotRawItem] = []
        failed_sources: list[str] = []
        failure_details: list[HotspotSourceFailureVO] = []
        for source, result, error in results:
            if error:
                failed_sources.append(source)
                failure_details.append(HotspotSourceFailureVO(source=source, error=error))
                continue
            items.extend(result)
        return items, failed_sources, failure_details

    async def _run_source(
        self,
        source: HotspotSource,
        task,
    ) -> tuple[HotspotSource, list[HotspotRawItem], str | None]:
        start = perf_counter()
        try:
            result = await task
            elapsed_ms = int((perf_counter() - start) * 1000)
            logger.info(
                "热点来源抓取完成 source=%s count=%s elapsedMs=%s",
                source,
                len(result),
                elapsed_ms,
            )
            return source, result, None
        except Exception as error:
            elapsed_ms = int((perf_counter() - start) * 1000)
            logger.exception(
                "热点来源抓取失败 source=%s elapsedMs=%s error=%s",
                source,
                elapsed_ms,
                error,
            )
            return source, [], str(error)

    async def search_bing(self, keyword: str) -> list[HotspotRawItem]:
        await _bing_limiter.wait()
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(
                "https://www.bing.com/search",
                params={"q": keyword, "count": 20},
                headers={"User-Agent": get_random_user_agent(), "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
            )
            response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        items: list[HotspotRawItem] = []
        for element in soup.select("li.b_algo"):
            title_element = element.select_one("h2 a")
            if not title_element:
                continue
            title = title_element.get_text(strip=True)
            url = title_element.get("href", "")
            snippet_element = element.select_one(".b_caption p")
            snippet = snippet_element.get_text(strip=True) if snippet_element else ""
            if title and url.startswith("http"):
                items.append(HotspotRawItem(title=title, content=snippet, url=url, source="bing"))
        return items[:20]

    async def search_hackernews(self, keyword: str) -> list[HotspotRawItem]:
        await _hackernews_limiter.wait()
        one_day_ago = int((datetime.now(timezone.utc) - timedelta(hours=24)).timestamp())
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                "https://hn.algolia.com/api/v1/search",
                params={
                    "query": keyword,
                    "tags": "story",
                    "hitsPerPage": 20,
                    "numericFilters": f"created_at_i>{one_day_ago}",
                },
            )
            response.raise_for_status()
        data = response.json()
        items: list[HotspotRawItem] = []
        for hit in data.get("hits", []):
            url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
            title = hit.get("title") or ""
            if not title or not url:
                continue
            items.append(
                HotspotRawItem(
                    title=title,
                    content=hit.get("story_text") or title,
                    url=url,
                    source="hackernews",
                    sourceId=hit.get("objectID"),
                    publishedAt=self._parse_datetime(hit.get("created_at")),
                    likeCount=hit.get("points") or 0,
                    commentCount=hit.get("num_comments") or 0,
                    authorName=hit.get("author"),
                )
            )
        return items

    async def search_sogou(self, keyword: str) -> list[HotspotRawItem]:
        await _sogou_limiter.wait()
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(
                "https://www.sogou.com/web",
                params={"query": keyword, "ie": "utf-8"},
                headers={"User-Agent": get_random_user_agent(), "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
            )
            response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        items: list[HotspotRawItem] = []
        for element in soup.select(".vrwrap, .rb"):
            title_element = element.select_one("h3 a, .vr-title a, .vrTitle a")
            if not title_element:
                continue
            title = title_element.get_text(strip=True)
            url = title_element.get("href", "")
            if url.startswith("/link?url="):
                url = f"https://www.sogou.com{url}"
            snippet_element = (
                element.select_one(".space-txt")
                or element.select_one(".str-text-info")
                or element.select_one(".str_info")
                or element.select_one(".text-layout")
                or element.select_one("p")
            )
            snippet = snippet_element.get_text(strip=True) if snippet_element else ""
            if title and url and "大家还在搜" not in title:
                items.append(HotspotRawItem(title=title, content=snippet or title, url=url, source="sogou"))
        return items[:20]

    async def search_bilibili(self, keyword: str) -> list[HotspotRawItem]:
        await _bilibili_limiter.wait()
        headers = {
            "User-Agent": get_random_user_agent(),
            "Referer": "https://search.bilibili.com/",
            "Accept": "application/json",
            "Cookie": f"buvid3={uuid.uuid4()}infoc",
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                "https://api.bilibili.com/x/web-interface/search/type",
                params={
                    "keyword": keyword,
                    "search_type": "video",
                    "order": "pubdate",
                    "page": 1,
                    "pagesize": 20,
                },
                headers=headers,
            )
            response.raise_for_status()
        data = response.json()
        if data.get("code") != 0:
            return []
        items: list[HotspotRawItem] = []
        for video in data.get("data", {}).get("result", []) or []:
            title = re.sub(r"</?em[^>]*>", "", html.unescape(video.get("title") or ""))
            bvid = video.get("bvid")
            if not title or not bvid:
                continue
            items.append(
                HotspotRawItem(
                    title=title,
                    content=video.get("description") or title,
                    url=f"https://www.bilibili.com/video/{bvid}",
                    source="bilibili",
                    sourceId=bvid,
                    publishedAt=self._from_timestamp(video.get("pubdate")),
                    viewCount=video.get("play") or 0,
                    likeCount=video.get("like") or 0,
                    commentCount=video.get("review") or 0,
                    danmakuCount=video.get("danmaku") or 0,
                    authorName=video.get("author"),
                    authorUsername=str(video.get("mid") or ""),
                )
            )
        return items

    async def search_weibo(self, keyword: str) -> list[HotspotRawItem]:
        await _weibo_limiter.wait()
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(
                "https://weibo.com/ajax/side/hotSearch",
                headers={"User-Agent": get_random_user_agent(), "Accept": "application/json", "Referer": "https://weibo.com/"},
            )
            response.raise_for_status()
        data = response.json()
        if data.get("ok") != 1:
            return []

        query_lower = keyword.lower()
        query_words = [word for word in re.split(r"\s+", query_lower) if word]
        items: list[HotspotRawItem] = []
        for hot_item in data.get("data", {}).get("realtime", []) or []:
            topic = hot_item.get("note") or hot_item.get("word") or ""
            topic_lower = topic.lower()
            matched = (
                query_lower in topic_lower
                or topic_lower in query_lower
                or any(word in topic_lower or topic_lower in word for word in query_words)
            )
            if not matched:
                continue
            items.append(
                HotspotRawItem(
                    title=f"微博热搜：{topic}",
                    content=f"微博热搜话题「{topic}」，热度 {hot_item.get('num') or hot_item.get('raw_hot') or 0}",
                    url=f"https://s.weibo.com/weibo?q=%23{topic}%23",
                    source="weibo",
                    viewCount=hot_item.get("num") or hot_item.get("raw_hot") or 0,
                    publishedAt=datetime.now(),
                )
            )
        return items

    # Twitter 本地过滤阈值
    _TWITTER_MIN_LIKES = 10
    _TWITTER_MIN_RETWEETS = 5
    _TWITTER_MIN_VIEWS = 500
    _TWITTER_MIN_FOLLOWERS = 100

    def _filter_and_rank_tweets(self, tweets: list[dict]) -> list[dict]:
        """本地质量过滤 + 按质量评分排序（在 AI 分析之前执行，减少无效调用）"""
        filtered = []
        for tweet in tweets:
            text = tweet.get("text") or ""
            tweet_type = (tweet.get("type") or "").lower()
            author = tweet.get("author") or {}
            verified = bool(author.get("isBlueVerified"))
            factor = 0.5 if verified else 1.0

            if "reply" in tweet_type:
                continue
            if re.match(r"^@\w+\s", text.strip()):
                continue
            if (tweet.get("likeCount") or 0) < self._TWITTER_MIN_LIKES * factor:
                continue
            if (tweet.get("retweetCount") or 0) < self._TWITTER_MIN_RETWEETS * factor:
                continue
            if (tweet.get("viewCount") or 0) < self._TWITTER_MIN_VIEWS * factor:
                continue
            if (author.get("followers") or 0) < self._TWITTER_MIN_FOLLOWERS * factor:
                continue
            filtered.append(tweet)

        filtered.sort(
            key=lambda t: (
                (t.get("likeCount") or 0) * 2
                + (t.get("retweetCount") or 0) * 3
                + (t.get("viewCount") or 0) / 100
                + (50 if (t.get("author") or {}).get("isBlueVerified") else 0)
            ),
            reverse=True,
        )
        return filtered

    def _build_twitter_query(self, keyword: str, query_type: str) -> str:
        days_ago = 7 if query_type == "Top" else 3
        parts = [keyword, "-filter:retweets", "-filter:replies", f"since:{self._format_since_date(days_ago)}"]
        if query_type == "Top":
            parts.append("min_faves:10")
        return " ".join(parts)

    async def _fetch_tweet_page(self, query: str, query_type: str, api_key: str, cursor: str | None = None) -> dict:
        params: dict[str, str] = {"query": query, "queryType": query_type}
        if cursor:
            params["cursor"] = cursor
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                "https://api.twitterapi.io/twitter/tweet/advanced_search",
                params=params,
                headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            )
            response.raise_for_status()
        return response.json()

    async def search_twitter(self, keyword: str) -> list[HotspotRawItem]:
        api_key = os.getenv("TWITTER_API_KEY")
        if not api_key:
            return []

        top_query = self._build_twitter_query(keyword, "Top")
        latest_query = self._build_twitter_query(keyword, "Latest")
        logger.info("Twitter 查询 top=%s latest=%s", top_query, latest_query)

        top_page1_coro = self._fetch_tweet_page(top_query, "Top", api_key)
        latest_page1_coro = self._fetch_tweet_page(latest_query, "Latest", api_key)
        top_result, latest_result = await asyncio.gather(top_page1_coro, latest_page1_coro, return_exceptions=True)

        all_tweet_dicts: list[dict] = []
        seen_ids: set[str] = set()

        def add_tweets(tweets: list) -> None:
            for tweet in tweets:
                tid = tweet.get("id")
                if tid and tid not in seen_ids:
                    seen_ids.add(tid)
                    all_tweet_dicts.append(tweet)

        top_next_cursor: str | None = None
        if isinstance(top_result, Exception):
            logger.warning("Twitter Top 第1页失败: %s", top_result)
        else:
            top_data: dict = top_result
            add_tweets(top_data.get("tweets") or [])
            if top_data.get("has_next_page"):
                top_next_cursor = top_data.get("next_cursor")

        if isinstance(latest_result, Exception):
            logger.warning("Twitter Latest 第1页失败: %s", latest_result)
        else:
            add_tweets((latest_result).get("tweets") or [])

        if top_next_cursor:
            try:
                top_page2 = await self._fetch_tweet_page(top_query, "Top", api_key, cursor=top_next_cursor)
                add_tweets(top_page2.get("tweets") or [])
            except Exception as exc:
                logger.warning("Twitter Top 第2页失败: %s", exc)

        logger.info("Twitter: %s 条原始推文，开始本地过滤", len(all_tweet_dicts))
        filtered = self._filter_and_rank_tweets(all_tweet_dicts)
        logger.info(
            "Twitter: %s → %s 条（likes≥%s RT≥%s views≥%s followers≥%s 排除回复）",
            len(all_tweet_dicts), len(filtered),
            self._TWITTER_MIN_LIKES, self._TWITTER_MIN_RETWEETS,
            self._TWITTER_MIN_VIEWS, self._TWITTER_MIN_FOLLOWERS,
        )

        items: list[HotspotRawItem] = []
        for tweet in filtered:
            author = tweet.get("author") or {}
            text = tweet.get("text") or ""
            items.append(HotspotRawItem(
                title=text[:100],
                content=text,
                url=tweet.get("url") or "",
                source="twitter",
                sourceId=tweet.get("id"),
                publishedAt=self._parse_datetime(tweet.get("createdAt")),
                viewCount=tweet.get("viewCount") or 0,
                likeCount=tweet.get("likeCount") or 0,
                retweetCount=tweet.get("retweetCount") or 0,
                replyCount=tweet.get("replyCount") or 0,
                quoteCount=tweet.get("quoteCount") or 0,
                authorName=author.get("name"),
                authorUsername=author.get("userName"),
                authorFollowers=author.get("followers"),
                authorVerified=author.get("isBlueVerified"),
            ))
        return [item for item in items if item.url]

    def _parse_datetime(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None

    def _from_timestamp(self, value) -> datetime | None:
        try:
            return datetime.fromtimestamp(int(value))
        except (TypeError, ValueError):
            return None

    def _format_since_date(self, days: int) -> str:
        date = datetime.utcnow() - timedelta(days=days)
        return date.strftime("%Y-%m-%d")
