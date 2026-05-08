# Hotspot Backend Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将热点追踪后端对齐参考项目，提升筛选质量（Twitter预过滤、AI prompt量化锚点）和稳定性（限速器、多页拉取、账号检测、关键词扩展缓存）。

**Architecture:** 改动集中在 3 个服务文件。`hotspot_sources.py` 新增 RateLimiter、UA 随机化、Twitter 多页+预过滤、B站账号检测；`hotspot_analysis_service.py` 加关键词扩展内存缓存和更精确的 AI prompt；`hotspot_service.py` 改为 Twitter 优先配额逻辑。所有改动向下兼容，schema/router/测试结构不变。

**Tech Stack:** Python 3.12, httpx, asyncio, BeautifulSoup4, Dashscope（通过 openai 兼容接口）

---

## File Structure

| 操作 | 文件 | 改动内容 |
|------|------|----------|
| 新建 | `backend/app/tests/test_hotspot_sources.py` | RateLimiter、UA随机化、Twitter预过滤、账号检测测试 |
| 修改 | `backend/app/services/hotspot_sources.py` | 限速器、UA随机化、Twitter多页+预过滤、B站账号检测 |
| 修改 | `backend/app/tests/test_hotspot_analysis_service.py` | 新增关键词扩展缓存测试 |
| 修改 | `backend/app/services/hotspot_analysis_service.py` | 扩展缓存、AI prompt量化锚点 |
| 修改 | `backend/app/tests/test_hotspot_service.py` | 新增 Twitter 配额测试 |
| 修改 | `backend/app/services/hotspot_service.py` | Twitter 优先配额逻辑 |

---

### Task 1: 限速器 + UA 随机化

**Files:**
- Create: `backend/app/tests/test_hotspot_sources.py`
- Modify: `backend/app/services/hotspot_sources.py`

- [ ] **Step 1: 新建测试文件，写 RateLimiter 和 UA 随机化的失败测试**

创建 `backend/app/tests/test_hotspot_sources.py`，内容如下：

```python
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
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd backend && uv run pytest app/tests/test_hotspot_sources.py -v
```

预期：`ImportError` 或 `AttributeError: module 'hotspot_sources' has no attribute 'RateLimiter'`

- [ ] **Step 3: 在 `hotspot_sources.py` 中添加 RateLimiter、UA 随机化，并接入各来源**

在文件顶部，删除旧的 `USER_AGENT = "..."` 单行，替换为以下代码（紧接在 `import` 块结束后）：

```python
import random
import time as _time

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
```

然后在各搜索方法的 `async with httpx.AsyncClient` **之前** 加一行 await，并将 `USER_AGENT` 替换为 `get_random_user_agent()`：

`search_bing`（第一行加）：
```python
await _bing_limiter.wait()
```
将 `"User-Agent": USER_AGENT` 改为 `"User-Agent": get_random_user_agent()`

`search_hackernews`（第一行加）：
```python
await _hackernews_limiter.wait()
```

`search_sogou`（第一行加）：
```python
await _sogou_limiter.wait()
```
将 `"User-Agent": USER_AGENT` 改为 `"User-Agent": get_random_user_agent()`

`search_bilibili`（`headers` 字典定义前加）：
```python
await _bilibili_limiter.wait()
```
将 `"User-Agent": USER_AGENT` 改为 `"User-Agent": get_random_user_agent()`

`search_weibo`（第一行加）：
```python
await _weibo_limiter.wait()
```
将 `"User-Agent": USER_AGENT` 改为 `"User-Agent": get_random_user_agent()`

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd backend && uv run pytest app/tests/test_hotspot_sources.py::test_rate_limiter_waits_min_interval_between_calls app/tests/test_hotspot_sources.py::test_get_random_user_agent_returns_value_from_list app/tests/test_hotspot_sources.py::test_get_random_user_agent_varies_over_many_calls -v
```

预期：3 tests PASSED

- [ ] **Step 5: 运行全量测试，确认原有测试不受影响**

```bash
cd backend && uv run pytest app/tests/ -v
```

预期：全部 PASSED（task 1 的 3 个新增测试 + 原有测试）

- [ ] **Step 6: Commit**

```bash
cd backend && git add app/tests/test_hotspot_sources.py app/services/hotspot_sources.py && git commit -m "feat: 热点来源添加限速器和 UA 随机化"
```

---

### Task 2: Twitter 多页拉取 + 本地预过滤

**Files:**
- Modify: `backend/app/tests/test_hotspot_sources.py`
- Modify: `backend/app/services/hotspot_sources.py`

- [ ] **Step 1: 在 `test_hotspot_sources.py` 末尾追加 Twitter 过滤测试**

```python
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
```

- [ ] **Step 2: 运行新测试，确认失败**

```bash
cd backend && uv run pytest app/tests/test_hotspot_sources.py::test_twitter_filter_removes_low_engagement_tweets -v
```

预期：`AttributeError: 'HotspotSourceService' object has no attribute '_filter_and_rank_tweets'`

- [ ] **Step 3: 在 `hotspot_sources.py` 中的 `HotspotSourceService` 添加以下方法和常量**

在类定义开头（`__init__` 之前或类级别）添加常量：

```python
_TWITTER_MIN_LIKES = 10
_TWITTER_MIN_RETWEETS = 5
_TWITTER_MIN_VIEWS = 500
_TWITTER_MIN_FOLLOWERS = 100
```

在类内添加 `_filter_and_rank_tweets` 和辅助方法：

```python
def _filter_and_rank_tweets(self, tweets: list[dict]) -> list[dict]:
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
```

然后将现有 `search_twitter` 方法**完整替换**为以下内容：

```python
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
    if not isinstance(top_result, Exception):
        add_tweets(top_result.get("tweets") or [])
        if top_result.get("has_next_page"):
            top_next_cursor = top_result.get("next_cursor")
    else:
        logger.warning("Twitter Top 第1页失败: %s", top_result)

    if not isinstance(latest_result, Exception):
        add_tweets(latest_result.get("tweets") or [])
    else:
        logger.warning("Twitter Latest 第1页失败: %s", latest_result)

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
```

- [ ] **Step 4: 运行 Twitter 过滤测试，确认通过**

```bash
cd backend && uv run pytest app/tests/test_hotspot_sources.py -k "twitter" -v
```

预期：4 tests PASSED

- [ ] **Step 5: 运行全量测试**

```bash
cd backend && uv run pytest app/tests/ -v
```

预期：全部 PASSED

- [ ] **Step 6: Commit**

```bash
cd backend && git add app/tests/test_hotspot_sources.py app/services/hotspot_sources.py && git commit -m "feat: Twitter 多页拉取和本地质量预过滤"
```

---

### Task 3: B站账号检测

**Files:**
- Modify: `backend/app/tests/test_hotspot_sources.py`
- Modify: `backend/app/services/hotspot_sources.py`

- [ ] **Step 1: 在 `test_hotspot_sources.py` 末尾追加账号检测测试**

```python
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
```

- [ ] **Step 2: 运行新测试，确认失败**

```bash
cd backend && uv run pytest app/tests/test_hotspot_sources.py -k "detect_account" -v
```

预期：`AttributeError: 'HotspotSourceService' object has no attribute 'detect_and_fetch_account'`

- [ ] **Step 3: 在 `hotspot_sources.py` 的 `HotspotSourceService` 中添加账号检测方法**

在 `search_weibo` 方法之后添加以下三个方法：

```python
async def detect_and_fetch_account(self, keyword: str) -> tuple[list[HotspotRawItem], list[dict]]:
    """检测关键词是否为 B站 UP 主账号名，若匹配则拉取最新内容（优先于搜索结果）"""
    try:
        users = await self._search_bilibili_user(keyword)
    except Exception as exc:
        logger.warning("B站账号检测失败 keyword=%s error=%s", keyword, exc)
        return [], []

    keyword_lower = keyword.lower()
    matched_accounts: list[dict] = []
    account_items: list[HotspotRawItem] = []

    for user in users:
        uname = (user.get("uname") or "").lower()
        followers = user.get("fans") or 0
        if followers < 1000:
            continue
        if keyword_lower not in uname:
            continue
        mid = str(user.get("mid") or "")
        matched_accounts.append({
            "platform": "bilibili",
            "name": user.get("uname"),
            "followers": followers,
        })
        logger.info("B站账号检测命中 uname=%s followers=%s mid=%s", user.get("uname"), followers, mid)
        try:
            videos = await self._fetch_bilibili_user_videos(mid)
            account_items.extend(videos)
        except Exception as exc:
            logger.warning("B站账号视频拉取失败 mid=%s error=%s", mid, exc)

    return account_items, matched_accounts

async def _search_bilibili_user(self, keyword: str) -> list[dict]:
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
            params={"keyword": keyword, "search_type": "bili_user", "page": 1},
            headers=headers,
        )
        response.raise_for_status()
    data = response.json()
    if data.get("code") != 0:
        return []
    return data.get("data", {}).get("result", []) or []

async def _fetch_bilibili_user_videos(self, mid: str) -> list[HotspotRawItem]:
    await _bilibili_limiter.wait()
    headers = {
        "User-Agent": get_random_user_agent(),
        "Referer": f"https://space.bilibili.com/{mid}/",
        "Accept": "application/json",
    }
    async with httpx.AsyncClient(timeout=self.timeout) as client:
        response = await client.get(
            "https://api.bilibili.com/x/space/arc/search",
            params={"mid": mid, "ps": 10, "tid": 0, "order": "pubdate"},
            headers=headers,
        )
        response.raise_for_status()
    data = response.json()
    items: list[HotspotRawItem] = []
    vlist = (data.get("data") or {}).get("list", {}).get("vlist") or []
    for video in vlist:
        title = re.sub(r"</?em[^>]*>", "", html.unescape(video.get("title") or ""))
        bvid = video.get("bvid")
        if not title or not bvid:
            continue
        items.append(HotspotRawItem(
            title=title,
            content=video.get("description") or title,
            url=f"https://www.bilibili.com/video/{bvid}",
            source="bilibili",
            sourceId=bvid,
            publishedAt=self._from_timestamp(video.get("created")),
            viewCount=video.get("play") or 0,
            likeCount=video.get("like") or 0,
            commentCount=video.get("comment") or 0,
            danmakuCount=video.get("danmaku") or 0,
            authorName=video.get("author"),
            authorUsername=mid,
        ))
    return items
```

- [ ] **Step 4: 将账号检测接入 `search_sources` 方法**

找到现有 `search_sources` 方法，将方法体替换为以下内容（保持方法签名不变）：

```python
async def search_sources(
    self,
    keyword: str,
    sources: list[HotspotSource],
) -> tuple[list[HotspotRawItem], list[str], list[HotspotSourceFailureVO]]:
    """并发搜索多个来源，账号检测结果优先"""
    # 账号检测（不算在普通来源内，失败不影响主流程）
    account_items, detected_accounts = await self.detect_and_fetch_account(keyword)
    if detected_accounts:
        logger.info("B站账号检测命中 %s 个账号，获得 %s 条内容", len(detected_accounts), len(account_items))

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

    items: list[HotspotRawItem] = list(account_items)  # 账号内容排在最前
    failed_sources: list[str] = []
    failure_details: list[HotspotSourceFailureVO] = []
    for source, result, error in results:
        if error:
            failed_sources.append(source)
            failure_details.append(HotspotSourceFailureVO(source=source, error=error))
            continue
        items.extend(result)
    return items, failed_sources, failure_details
```

- [ ] **Step 5: 运行账号检测测试，确认通过**

```bash
cd backend && uv run pytest app/tests/test_hotspot_sources.py -k "detect_account" -v
```

预期：3 tests PASSED

- [ ] **Step 6: 运行全量测试**

```bash
cd backend && uv run pytest app/tests/ -v
```

预期：全部 PASSED

- [ ] **Step 7: Commit**

```bash
cd backend && git add app/tests/test_hotspot_sources.py app/services/hotspot_sources.py && git commit -m "feat: B站账号检测，命中时优先拉取 UP 主最新视频"
```

---

### Task 4: 关键词扩展缓存

**Files:**
- Modify: `backend/app/tests/test_hotspot_analysis_service.py`
- Modify: `backend/app/services/hotspot_analysis_service.py`

- [ ] **Step 1: 在 `test_hotspot_analysis_service.py` 末尾追加缓存测试**

```python
def test_expand_keyword_caches_result_and_calls_ai_only_once():
    async def run():
        call_count = 0

        class FakeCompletion:
            class choices:
                pass

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
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd backend && uv run pytest app/tests/test_hotspot_analysis_service.py::test_expand_keyword_caches_result_and_calls_ai_only_once -v
```

预期：FAILED（call_count == 2，缓存不存在）

- [ ] **Step 3: 在 `hotspot_analysis_service.py` 中添加缓存**

在 `HotspotAnalysisService.__init__` 末尾添加一行：

```python
def __init__(self, ai_client: Optional[AsyncOpenAI] = None):
    self.ai_client = ai_client
    self.model = settings.dashscope_model
    self._expansion_cache: dict[str, list[str]] = {}
```

在 `expand_keyword` 方法开头，`local_terms = self.expand_keyword_locally(keyword)` **之前**添加缓存检查：

```python
async def expand_keyword(self, keyword: str) -> list[str]:
    if keyword in self._expansion_cache:
        logger.info("热点关键词扩展命中缓存 keyword=%s", keyword)
        return self._expansion_cache[keyword]

    local_terms = self.expand_keyword_locally(keyword)
    ...
```

在方法的 **两个** return 点之前（成功路径和 fallback 路径）各加一行缓存写入：

成功路径（`return result` 前）：
```python
self._expansion_cache[keyword] = result
return result
```

fallback 路径（`return local_terms` 前）：
```python
self._expansion_cache[keyword] = local_terms
return local_terms
```

- [ ] **Step 4: 运行缓存测试，确认通过**

```bash
cd backend && uv run pytest app/tests/test_hotspot_analysis_service.py::test_expand_keyword_caches_result_and_calls_ai_only_once -v
```

预期：PASSED

- [ ] **Step 5: 运行全量测试**

```bash
cd backend && uv run pytest app/tests/ -v
```

预期：全部 PASSED

- [ ] **Step 6: Commit**

```bash
cd backend && git add app/tests/test_hotspot_analysis_service.py app/services/hotspot_analysis_service.py && git commit -m "feat: 关键词扩展结果内存缓存，避免重复 AI 调用"
```

---

### Task 5: AI Prompt 量化锚点

**Files:**
- Modify: `backend/app/services/hotspot_analysis_service.py`

此改动无需新增测试（prompt 是纯字符串，测试其内容价值低；功能正确性在集成时验证）。

- [ ] **Step 1: 将 `_build_analysis_prompt` 完整替换为以下内容**

找到 `hotspot_analysis_service.py` 中的 `_build_analysis_prompt` 方法，整体替换：

```python
def _build_analysis_prompt(self, keyword: str, pre_match: HotspotPreMatch) -> str:
    match_hint = (
        f"文本预匹配命中：{'、'.join(pre_match.matched_terms)}"
        if pre_match.matched
        else f"文本预匹配发现内容中未直接提及关键词「{keyword}」的任何变体，请特别严格审核相关性。"
    )
    return f"""你是热点内容精准匹配专家。请判断内容是否与监控关键词【{keyword}】直接相关。
{match_hint}

评分规则：
1. 判断是否为真实有价值的信息（排除标题党、假新闻、营销软文）
2. 判断内容是否【直接】涉及关键词「{keyword}」：
   - 同领域但未直接提及关键词 → 低于 40 分
   - 间接沾边（同类产品/同领域不同主题）→ 30-50 分
   - 直接讨论、提及或有实质关联 → 60 分以上
   - 仅属于同一领域而无关联 → 低于 40 分
3. keywordMentioned：内容是否直接提及「{keyword}」或其等价表述
4. importance：对关注「{keyword}」的人而言有多重要（low/medium/high/urgent）
5. summary：说明此内容与「{keyword}」的关联是什么（不是介绍内容本身）
6. relevanceReason：相关性打分的理由（一句话）

输出 JSON：
{{
  "isReal": true,
  "relevance": 0,
  "relevanceReason": "打分理由",
  "keywordMentioned": true,
  "importance": "low|medium|high|urgent",
  "summary": "此内容与【{keyword}】的关联：..."
}}

只输出 JSON。"""
```

- [ ] **Step 2: 运行全量测试，确认无回归**

```bash
cd backend && uv run pytest app/tests/ -v
```

预期：全部 PASSED

- [ ] **Step 3: Commit**

```bash
cd backend && git add app/services/hotspot_analysis_service.py && git commit -m "feat: AI 分析 prompt 添加量化评分锚点，提升判断一致性"
```

---

### Task 6: Twitter 优先配额

**Files:**
- Modify: `backend/app/tests/test_hotspot_service.py`
- Modify: `backend/app/services/hotspot_service.py`

- [ ] **Step 1: 在 `test_hotspot_service.py` 末尾追加配额测试**

```python
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
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd backend && uv run pytest app/tests/test_hotspot_service.py::test_scan_radar_applies_twitter_quota_15_and_other_quota_10 -v
```

预期：FAILED（当前是平等取前 N 条，twitter 会是 16 条或受 analyze_limit 限制）

- [ ] **Step 3: 修改 `hotspot_service.py` 中 `scan_radar` 的配额逻辑**

找到 `scan_radar` 方法中以下代码段：

```python
stage_start = perf_counter()
items_for_analysis = prioritized_items[: request.analyze_limit]
analyzed_items = await self.analysis_service.analyze_items(
```

将 `items_for_analysis = prioritized_items[: request.analyze_limit]` 这一行替换为：

```python
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
```

- [ ] **Step 4: 运行配额测试，确认通过**

```bash
cd backend && uv run pytest app/tests/test_hotspot_service.py::test_scan_radar_applies_twitter_quota_15_and_other_quota_10 -v
```

预期：PASSED

- [ ] **Step 5: 运行全量测试**

```bash
cd backend && uv run pytest app/tests/ -v
```

预期：全部 PASSED

- [ ] **Step 6: Commit**

```bash
cd backend && git add app/tests/test_hotspot_service.py app/services/hotspot_service.py && git commit -m "feat: Twitter 优先配额（15条）+ 其他来源配额（10条）"
```

---

## 自检：规格覆盖

| 设计改动 | 对应任务 | 状态 |
|----------|----------|------|
| 限速器（5个来源） | Task 1 | ✓ |
| UA 随机化 | Task 1 | ✓ |
| Twitter Top 2页 + Latest 1页 | Task 2 | ✓ |
| Twitter 本地预过滤（4个阈值 + 蓝V减半） | Task 2 | ✓ |
| Twitter 质量评分排序 | Task 2 | ✓ |
| B站账号检测 + 拉取最新视频 | Task 3 | ✓ |
| 账号内容优先插入 search_sources | Task 3 | ✓ |
| 关键词扩展内存缓存 | Task 4 | ✓ |
| AI Prompt 量化锚点（3档分值说明） | Task 5 | ✓ |
| Twitter 优先配额（15 + 10） | Task 6 | ✓ |
