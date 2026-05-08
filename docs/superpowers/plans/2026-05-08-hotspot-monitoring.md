# Hotspot Monitoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将热点追踪从"按需搜索"升级为"持续监控"：关键词管理、每30分钟自动扫描、热点持久化、WebSocket实时推送、站内通知、前端4 Tab布局（关键词/监控热点/搜索/生成选题）。

**Architecture:** 后端新增3张MySQL表（keyword/record/notification），使用 APScheduler 后台任务每30分钟扫描全部活跃关键词并将结果写入 `hotspot_record`；FastAPI WebSocket 端点广播新热点；前端通过 WebSocket composable 订阅实时更新，通知铃铛显示未读数。所有新 DB 查询沿用项目现有的 `databases` 库 + 原始 SQL 模式。

**Tech Stack:** FastAPI, databases(MySQL), APScheduler, FastAPI WebSocket, Vue 3, Ant Design Vue

---

## File Structure

**新增后端文件**
| 文件 | 职责 |
|------|------|
| `sql/add_hotspot_monitoring.sql` | 3张新表的 DDL |
| `backend/app/schemas/hotspot_monitor.py` | 所有新的 Pydantic 请求/响应模型 |
| `backend/app/services/hotspot_keyword_service.py` | 关键词 CRUD |
| `backend/app/services/hotspot_record_service.py` | 热点记录查询+过滤+排序 |
| `backend/app/services/hotspot_notification_service.py` | 通知 CRUD |
| `backend/app/managers/hotspot_ws_manager.py` | WebSocket 连接池 + 广播 |
| `backend/app/services/hotspot_monitor_service.py` | 扫描调度核心：遍历关键词→扫描→写DB→广播 |
| `backend/app/routers/hotspot_monitor.py` | 所有新 API 路由 |
| `backend/app/tests/test_hotspot_keyword_service.py` | 关键词服务测试 |
| `backend/app/tests/test_hotspot_record_service.py` | 记录服务测试 |

**修改后端文件**
| 文件 | 改动 |
|------|------|
| `backend/app/routers/__init__.py` | 导出 `hotspot_monitor_router` |
| `backend/app/main.py` | lifespan 注册 APScheduler，注册新路由 |
| `backend/pyproject.toml` | 新增 `apscheduler` 依赖 |

**新增前端文件**
| 文件 | 职责 |
|------|------|
| `frontend/src/api/hotspotMonitorController.ts` | 所有新 API 调用函数 |
| `frontend/src/composables/useHotspotWs.ts` | WebSocket 连接管理 composable |
| `frontend/src/pages/topic/KeywordsTab.vue` | 关键词管理 Tab |
| `frontend/src/pages/topic/MonitorTab.vue` | 监控热点列表+筛选 Tab |

**修改前端文件**
| 文件 | 改动 |
|------|------|
| `frontend/src/api/typings.d.ts` | 新增监控相关类型 |
| `frontend/src/components/GlobalHeader.vue` | 加入通知铃铛 |
| `frontend/src/pages/TopicPage.vue` | 改为4 Tab布局，集成 WebSocket |

---

### Task 1: SQL 建表 + APScheduler 依赖

**Files:**
- Create: `sql/add_hotspot_monitoring.sql`
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: 创建 SQL 文件**

创建 `/home/xcodd/code/ai-passage-creator/sql/add_hotspot_monitoring.sql`：

```sql
-- 热点监控关键词表
CREATE TABLE IF NOT EXISTS hotspot_keyword (
    id         BIGINT AUTO_INCREMENT PRIMARY KEY,
    userId     BIGINT NOT NULL COMMENT '所属用户 ID',
    text       VARCHAR(200) NOT NULL COMMENT '关键词',
    category   VARCHAR(100) NULL COMMENT '分类（可选）',
    isActive   TINYINT DEFAULT 1 NOT NULL COMMENT '是否激活',
    createTime DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updateTime DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_userId_text (userId, text(191)),
    INDEX idx_userId_active (userId, isActive)
) COMMENT='热点监控关键词' COLLATE=utf8mb4_unicode_ci;

-- 热点记录表
CREATE TABLE IF NOT EXISTS hotspot_record (
    id               BIGINT AUTO_INCREMENT PRIMARY KEY,
    userId           BIGINT NOT NULL COMMENT '所属用户 ID',
    keywordId        BIGINT NULL COMMENT '关联关键词（删除时置 NULL）',
    keywordText      VARCHAR(200) NULL COMMENT '关键词快照',
    title            VARCHAR(500) NOT NULL COMMENT '热点标题',
    content          TEXT NULL COMMENT '原始内容',
    url              VARCHAR(1024) NOT NULL COMMENT '链接',
    source           VARCHAR(50) NOT NULL COMMENT '来源',
    sourceId         VARCHAR(200) NULL COMMENT '平台内容 ID',
    isReal           TINYINT DEFAULT 1 NOT NULL COMMENT '是否真实内容',
    relevance        INT DEFAULT 0 NOT NULL COMMENT '相关性 0-100',
    relevanceReason  VARCHAR(500) NULL COMMENT '相关性理由',
    keywordMentioned TINYINT DEFAULT 0 NOT NULL COMMENT '是否直接提及关键词',
    importance       VARCHAR(20) DEFAULT 'low' NOT NULL COMMENT 'low/medium/high/urgent',
    summary          VARCHAR(500) NULL COMMENT 'AI 摘要',
    heatScore        FLOAT DEFAULT 0 NOT NULL COMMENT '热度分',
    viewCount        BIGINT NULL,
    likeCount        BIGINT NULL,
    retweetCount     BIGINT NULL,
    commentCount     BIGINT NULL,
    authorName       VARCHAR(200) NULL,
    authorUsername   VARCHAR(200) NULL,
    authorFollowers  BIGINT NULL,
    authorVerified   TINYINT NULL,
    publishedAt      DATETIME NULL COMMENT '内容发布时间',
    createTime       DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL COMMENT '发现时间',
    INDEX idx_userId_importance (userId, importance),
    INDEX idx_userId_createTime (userId, createTime),
    INDEX idx_keywordId (keywordId),
    UNIQUE KEY uk_url_source (url(512), source)
) COMMENT='热点记录' COLLATE=utf8mb4_unicode_ci;

-- 热点站内通知表
CREATE TABLE IF NOT EXISTS hotspot_notification (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    type            VARCHAR(50) DEFAULT 'hotspot' NOT NULL COMMENT 'hotspot/alert',
    title           VARCHAR(300) NOT NULL,
    content         VARCHAR(500) NULL,
    isRead          TINYINT DEFAULT 0 NOT NULL,
    hotspotRecordId BIGINT NULL COMMENT '关联热点记录 ID',
    createTime      DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    INDEX idx_isRead (isRead),
    INDEX idx_createTime (createTime)
) COMMENT='热点站内通知' COLLATE=utf8mb4_unicode_ci;
```

- [ ] **Step 2: 执行建表 SQL**

```bash
mysql -uroot -p ai_passage_creator < sql/add_hotspot_monitoring.sql
```

预期：无报错，3张表创建成功。

- [ ] **Step 3: 添加 apscheduler 依赖**

```bash
cd backend && uv add "apscheduler>=3.10"
```

预期：`pyproject.toml` 新增 apscheduler，`uv.lock` 更新。

- [ ] **Step 4: Commit**

```bash
git add sql/add_hotspot_monitoring.sql backend/pyproject.toml backend/uv.lock && git commit -m "feat: 热点监控建表，添加 apscheduler 依赖"
```

---

### Task 2: Pydantic 模型

**Files:**
- Create: `backend/app/schemas/hotspot_monitor.py`

- [ ] **Step 1: 创建 schemas 文件**

创建 `backend/app/schemas/hotspot_monitor.py`：

```python
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
```

- [ ] **Step 2: 验证导入无误**

```bash
cd backend && uv run python -c "from app.schemas.hotspot_monitor import KeywordVO, RecordVO, NotificationVO; print('OK')"
```

预期：`OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/hotspot_monitor.py && git commit -m "feat: 热点监控 Pydantic schemas"
```

---

### Task 3: 关键词服务 + 路由

**Files:**
- Create: `backend/app/services/hotspot_keyword_service.py`
- Create: `backend/app/tests/test_hotspot_keyword_service.py`

- [ ] **Step 1: 写失败测试**

创建 `backend/app/tests/test_hotspot_keyword_service.py`：

```python
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.schemas.hotspot_monitor import KeywordCreateRequest


SERVICE_PATH = Path(__file__).resolve().parents[1] / "services" / "hotspot_keyword_service.py"
spec = __import__("importlib.util").util.spec_from_file_location("hotspot_keyword_service", SERVICE_PATH)
svc_module = __import__("importlib.util").util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(svc_module)
HotspotKeywordService = svc_module.HotspotKeywordService


class FakeDB:
    def __init__(self, rows=None, last_id=1):
        self._rows = rows or []
        self._last_id = last_id
        self.executed = []

    async def execute(self, query, values=None):
        self.executed.append((query, values))
        return self._last_id

    async def fetch_all(self, query, values=None):
        return self._rows

    async def fetch_one(self, query, values=None):
        return self._rows[0] if self._rows else None


def test_create_keyword_returns_id():
    async def run():
        db = FakeDB(last_id=42)
        svc = HotspotKeywordService(db)
        result = await svc.create_keyword(KeywordCreateRequest(text="AI编程"), user_id=1)
        assert result == 42
        assert "INSERT INTO hotspot_keyword" in db.executed[0][0]

    asyncio.run(run())


def test_list_keywords_maps_rows():
    class FakeRow:
        def __getitem__(self, key):
            data = {"id": 1, "text": "AI编程", "category": None, "isActive": 1,
                    "hotspotCount": 5, "createTime": None}
            return data[key]

    async def run():
        db = FakeDB(rows=[FakeRow()])
        svc = HotspotKeywordService(db)
        result = await svc.list_keywords(user_id=1)
        assert len(result) == 1
        assert result[0].text == "AI编程"
        assert result[0].hotspot_count == 5

    asyncio.run(run())
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd backend && uv run python -m pytest app/tests/test_hotspot_keyword_service.py -v 2>&1 | tail -5
```

预期：`AttributeError` — module has no attribute `HotspotKeywordService`

- [ ] **Step 3: 实现服务**

创建 `backend/app/services/hotspot_keyword_service.py`：

```python
"""热点监控关键词服务"""

import logging
from datetime import datetime
from typing import Optional

from app.schemas.hotspot_monitor import KeywordCreateRequest, KeywordVO

logger = logging.getLogger(__name__)


class HotspotKeywordService:
    def __init__(self, db):
        self.db = db

    async def create_keyword(self, request: KeywordCreateRequest, user_id: int) -> int:
        now = datetime.now()
        row_id = await self.db.execute(
            query="""
                INSERT INTO hotspot_keyword (userId, text, category, isActive, createTime, updateTime)
                VALUES (:userId, :text, :category, 1, :now, :now)
            """,
            values={"userId": user_id, "text": request.text.strip(), "category": request.category, "now": now},
        )
        logger.info("关键词创建成功 userId=%s text=%s id=%s", user_id, request.text, row_id)
        return row_id

    async def list_keywords(self, user_id: int) -> list[KeywordVO]:
        rows = await self.db.fetch_all(
            query="""
                SELECT k.id, k.text, k.category, k.isActive,
                       COUNT(r.id) AS hotspotCount,
                       k.createTime
                FROM hotspot_keyword k
                LEFT JOIN hotspot_record r ON r.keywordId = k.id
                WHERE k.userId = :userId
                GROUP BY k.id
                ORDER BY k.createTime DESC
            """,
            values={"userId": user_id},
        )
        return [KeywordVO(
            id=row["id"],
            text=row["text"],
            category=row["category"],
            isActive=bool(row["isActive"]),
            hotspotCount=row["hotspotCount"] or 0,
            createTime=row["createTime"],
        ) for row in rows]

    async def toggle_keyword(self, keyword_id: int, user_id: int) -> bool:
        """切换激活状态，返回新的 isActive 值"""
        row = await self.db.fetch_one(
            query="SELECT id, isActive FROM hotspot_keyword WHERE id = :id AND userId = :userId",
            values={"id": keyword_id, "userId": user_id},
        )
        if not row:
            return False
        new_active = 0 if row["isActive"] else 1
        await self.db.execute(
            query="UPDATE hotspot_keyword SET isActive = :active, updateTime = :now WHERE id = :id",
            values={"active": new_active, "id": keyword_id, "now": datetime.now()},
        )
        return bool(new_active)

    async def delete_keyword(self, keyword_id: int, user_id: int) -> bool:
        row = await self.db.fetch_one(
            query="SELECT id FROM hotspot_keyword WHERE id = :id AND userId = :userId",
            values={"id": keyword_id, "userId": user_id},
        )
        if not row:
            return False
        await self.db.execute(
            query="DELETE FROM hotspot_keyword WHERE id = :id",
            values={"id": keyword_id},
        )
        return True

    async def get_all_active_keywords(self) -> list[dict]:
        """获取所有用户的所有激活关键词（供后台扫描使用）"""
        rows = await self.db.fetch_all(
            query="SELECT id, userId, text FROM hotspot_keyword WHERE isActive = 1",
            values={},
        )
        return [{"id": row["id"], "user_id": row["userId"], "text": row["text"]} for row in rows]
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd backend && uv run python -m pytest app/tests/test_hotspot_keyword_service.py -v 2>&1 | tail -8
```

预期：`2 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/hotspot_keyword_service.py backend/app/tests/test_hotspot_keyword_service.py && git commit -m "feat: 热点关键词 CRUD 服务"
```

---

### Task 4: 热点记录服务 + 测试

**Files:**
- Create: `backend/app/services/hotspot_record_service.py`
- Create: `backend/app/tests/test_hotspot_record_service.py`

- [ ] **Step 1: 写失败测试**

创建 `backend/app/tests/test_hotspot_record_service.py`：

```python
import asyncio
import sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.schemas.hotspot_monitor import RecordListRequest

SERVICE_PATH = Path(__file__).resolve().parents[1] / "services" / "hotspot_record_service.py"
spec = __import__("importlib.util").util.spec_from_file_location("hotspot_record_service", SERVICE_PATH)
svc_module = __import__("importlib.util").util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(svc_module)
HotspotRecordService = svc_module.HotspotRecordService


class FakeDB:
    def __init__(self, rows=None):
        self._rows = rows or []
        self.executed = []

    async def execute(self, query, values=None):
        self.executed.append((query, values))
        return 1

    async def fetch_all(self, query, values=None):
        return self._rows

    async def fetch_one(self, query, values=None):
        return self._rows[0] if self._rows else None


def test_list_records_returns_empty_when_no_rows():
    async def run():
        db = FakeDB(rows=[])
        svc = HotspotRecordService(db)
        req = RecordListRequest()
        result = await svc.list_records(req, user_id=1)
        assert result.records == []
        assert result.total == 0
        assert result.has_more is False

    asyncio.run(run())


def test_url_source_exists_check():
    async def run():
        class FakeRow:
            def __getitem__(self, key):
                return {"cnt": 1}[key]

        db = FakeDB(rows=[FakeRow()])
        svc = HotspotRecordService(db)
        exists = await svc.url_source_exists("https://example.com", "bing")
        assert exists is True

    asyncio.run(run())
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd backend && uv run python -m pytest app/tests/test_hotspot_record_service.py -v 2>&1 | tail -5
```

预期：`AttributeError` — module has no attribute `HotspotRecordService`

- [ ] **Step 3: 实现服务**

创建 `backend/app/services/hotspot_record_service.py`：

```python
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
        """写入热点记录，重复时忽略。返回记录 ID（0 表示重复跳过）"""
        now = datetime.now()
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
                    "publishedAt": datetime.fromisoformat(vo.published_at) if vo.published_at else None,
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

        # importance / heat 在内存中排序
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
            total=row["total"] or 0,
            today=row["today"] or 0,
            urgent=row["urgent"] or 0,
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
        col = col_map.get(req.sort_by, "createTime")
        if req.sort_by in ("importance", "heat"):
            return "ORDER BY createTime DESC"
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
        cutoffs = {"1h": now - timedelta(hours=1), "today": now.replace(hour=0, minute=0, second=0, microsecond=0), "7d": now - timedelta(days=7), "30d": now - timedelta(days=30)}
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
            heatScore=row["heatScore"] or 0.0,
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
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd backend && uv run python -m pytest app/tests/test_hotspot_record_service.py -v 2>&1 | tail -8
```

预期：`2 passed`

- [ ] **Step 5: 运行全量测试**

```bash
cd backend && uv run python -m pytest app/tests/ -q 2>&1 | tail -5
```

预期：`25 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/hotspot_record_service.py backend/app/tests/test_hotspot_record_service.py && git commit -m "feat: 热点记录服务（写入/查询/过滤/排序）"
```

---

### Task 5: 通知服务 + WebSocket 管理器

**Files:**
- Create: `backend/app/services/hotspot_notification_service.py`
- Create: `backend/app/managers/hotspot_ws_manager.py`

- [ ] **Step 1: 创建通知服务**

创建 `backend/app/services/hotspot_notification_service.py`：

```python
"""热点站内通知服务"""

import logging
from datetime import datetime
from typing import Optional

from app.schemas.hotspot_monitor import NotificationListResponse, NotificationVO

logger = logging.getLogger(__name__)


class HotspotNotificationService:
    def __init__(self, db):
        self.db = db

    async def create_notification(self, title: str, content: Optional[str], hotspot_record_id: Optional[int]) -> int:
        row_id = await self.db.execute(
            query="""
                INSERT INTO hotspot_notification (type, title, content, isRead, hotspotRecordId, createTime)
                VALUES ('hotspot', :title, :content, 0, :hotspotRecordId, :now)
            """,
            values={"title": title[:300], "content": (content or "")[:500], "hotspotRecordId": hotspot_record_id, "now": datetime.now()},
        )
        return row_id

    async def list_notifications(self, limit: int = 20, unread_only: bool = False) -> NotificationListResponse:
        where = "WHERE isRead = 0" if unread_only else ""
        rows = await self.db.fetch_all(
            query=f"""
                SELECT id, type, title, content, isRead, hotspotRecordId, createTime
                FROM hotspot_notification
                {where}
                ORDER BY createTime DESC
                LIMIT :limit
            """,
            values={"limit": limit},
        )
        unread_row = await self.db.fetch_one(
            query="SELECT COUNT(*) AS cnt FROM hotspot_notification WHERE isRead = 0",
            values={},
        )
        notifications = [NotificationVO(
            id=row["id"], type=row["type"], title=row["title"], content=row["content"],
            isRead=bool(row["isRead"]), hotspotRecordId=row["hotspotRecordId"],
            createTime=row["createTime"],
        ) for row in rows]
        return NotificationListResponse(
            notifications=notifications,
            unreadCount=unread_row["cnt"] if unread_row else 0,
        )

    async def mark_all_read(self) -> None:
        await self.db.execute(
            query="UPDATE hotspot_notification SET isRead = 1 WHERE isRead = 0",
            values={},
        )
```

- [ ] **Step 2: 创建 WebSocket 管理器**

创建 `backend/app/managers/hotspot_ws_manager.py`：

```python
"""热点 WebSocket 连接管理器"""

import json
import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class HotspotWsManager:
    def __init__(self):
        self._connections: set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.add(ws)
        logger.info("WebSocket 连接建立，当前连接数=%s", len(self._connections))

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.discard(ws)
        logger.info("WebSocket 连接断开，当前连接数=%s", len(self._connections))

    async def broadcast(self, message: dict) -> None:
        if not self._connections:
            return
        data = json.dumps(message, ensure_ascii=False, default=str)
        dead: set[WebSocket] = set()
        for ws in list(self._connections):
            try:
                await ws.send_text(data)
            except Exception:
                dead.add(ws)
        self._connections -= dead


# 模块级单例
hotspot_ws_manager = HotspotWsManager()
```

- [ ] **Step 3: 验证导入**

```bash
cd backend && uv run python -c "from app.managers.hotspot_ws_manager import hotspot_ws_manager; from app.services.hotspot_notification_service import HotspotNotificationService; print('OK')"
```

预期：`OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/hotspot_notification_service.py backend/app/managers/hotspot_ws_manager.py && git commit -m "feat: 热点通知服务 + WebSocket 连接管理器"
```

---

### Task 6: 监控服务（扫描核心）

**Files:**
- Create: `backend/app/services/hotspot_monitor_service.py`

- [ ] **Step 1: 创建监控服务**

创建 `backend/app/services/hotspot_monitor_service.py`：

```python
"""热点监控服务：定时扫描关键词 → 写入 DB → 广播"""

import logging
from datetime import datetime
from typing import Optional

from app.database import database
from app.managers.hotspot_ws_manager import hotspot_ws_manager
from app.schemas.hotspot import HotspotRadarRequest
from app.services.hotspot_keyword_service import HotspotKeywordService
from app.services.hotspot_notification_service import HotspotNotificationService
from app.services.hotspot_record_service import HotspotRecordService
from app.services.hotspot_service import HotspotService

logger = logging.getLogger(__name__)

DEFAULT_SOURCES = ["weibo", "bilibili", "sogou", "bing", "hackernews", "twitter", "duckduckgo"]

_last_run_at: Optional[datetime] = None
_is_running: bool = False


class HotspotMonitorService:
    """后台扫描调度器，使用全局 database 实例（不依赖请求上下文）"""

    async def scan_all_keywords(self) -> None:
        global _is_running, _last_run_at
        if _is_running:
            logger.info("热点扫描正在进行中，跳过本次触发")
            return

        _is_running = True
        _last_run_at = datetime.now()
        logger.info("热点监控扫描开始 startAt=%s", _last_run_at)

        try:
            kw_service = HotspotKeywordService(database)
            keywords = await kw_service.get_all_active_keywords()
            if not keywords:
                logger.info("无激活关键词，跳过扫描")
                return

            logger.info("激活关键词数=%s", len(keywords))
            for kw in keywords:
                try:
                    await self._scan_one_keyword(kw["id"], kw["user_id"], kw["text"])
                except Exception as exc:
                    logger.exception("关键词扫描失败 keyword=%s error=%s", kw["text"], exc)
        finally:
            _is_running = False
            logger.info("热点监控扫描结束")

    async def _scan_one_keyword(self, keyword_id: int, user_id: int, keyword_text: str) -> None:
        logger.info("扫描关键词 text=%s userId=%s", keyword_text, user_id)

        request = HotspotRadarRequest(
            keyword=keyword_text,
            sources=DEFAULT_SOURCES,
            analyzeLimit=20,
        )
        service = HotspotService()
        result = await service.scan_radar(request)

        record_service = HotspotRecordService(database)
        notification_service = HotspotNotificationService(database)
        new_count = 0

        for vo in result.hotspots:
            record_id = await record_service.save_record(user_id, keyword_id, keyword_text, vo)
            if record_id:
                new_count += 1
                await notification_service.create_notification(
                    title=f"发现新热点：{vo.title[:50]}",
                    content=vo.summary or vo.content[:100] if vo.content else None,
                    hotspot_record_id=record_id,
                )
                await hotspot_ws_manager.broadcast({
                    "type": "hotspot_new",
                    "importance": vo.importance,
                    "title": vo.title[:80],
                    "source": vo.source,
                    "keywordText": keyword_text,
                })

        logger.info("关键词扫描完成 keyword=%s 新增=%s", keyword_text, new_count)

    @staticmethod
    def get_status() -> dict:
        return {
            "isRunning": _is_running,
            "lastRunAt": _last_run_at.isoformat() if _last_run_at else None,
        }


# 模块级单例（供 APScheduler 调用）
monitor_service = HotspotMonitorService()
```

- [ ] **Step 2: 验证导入**

```bash
cd backend && uv run python -c "from app.services.hotspot_monitor_service import monitor_service; print('OK')"
```

预期：`OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/hotspot_monitor_service.py && git commit -m "feat: 热点监控调度服务（扫描→写DB→广播）"
```

---

### Task 7: 路由注册 + APScheduler

**Files:**
- Create: `backend/app/routers/hotspot_monitor.py`
- Modify: `backend/app/routers/__init__.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 创建路由文件**

创建 `backend/app/routers/hotspot_monitor.py`：

```python
"""热点持续监控路由"""

import logging

from databases import Database
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query

from app.database import get_db
from app.deps import require_login
from app.exceptions import ErrorCode, throw_if
from app.managers.hotspot_ws_manager import hotspot_ws_manager
from app.schemas.common import BaseResponse
from app.schemas.hotspot_monitor import (
    KeywordCreateRequest, KeywordVO,
    RecordListRequest, RecordListResponse, RecordStatsVO,
    NotificationListResponse, MonitorStatusVO,
)
from app.schemas.user import LoginUserVO
from app.services.hotspot_keyword_service import HotspotKeywordService
from app.services.hotspot_monitor_service import monitor_service
from app.services.hotspot_notification_service import HotspotNotificationService
from app.services.hotspot_record_service import HotspotRecordService

router = APIRouter(prefix="/hotspot", tags=["热点监控"])
logger = logging.getLogger(__name__)


# ─── 关键词 ─────────────────────────────────────
@router.get("/keywords", response_model=BaseResponse[list[KeywordVO]])
async def list_keywords(
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    svc = HotspotKeywordService(db)
    result = await svc.list_keywords(current_user.id)
    return BaseResponse.success(data=result)


@router.post("/keywords", response_model=BaseResponse[int])
async def create_keyword(
    request: KeywordCreateRequest,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    throw_if(not request.text or not request.text.strip(), ErrorCode.PARAMS_ERROR, "关键词不能为空")
    svc = HotspotKeywordService(db)
    try:
        row_id = await svc.create_keyword(request, current_user.id)
        return BaseResponse.success(data=row_id)
    except Exception as exc:
        if "Duplicate" in str(exc):
            from app.exceptions import throw_if as _throw
            _throw(True, ErrorCode.PARAMS_ERROR, "该关键词已存在")
        raise


@router.patch("/keywords/{keyword_id}/toggle", response_model=BaseResponse[bool])
async def toggle_keyword(
    keyword_id: int,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    svc = HotspotKeywordService(db)
    new_active = await svc.toggle_keyword(keyword_id, current_user.id)
    return BaseResponse.success(data=new_active)


@router.delete("/keywords/{keyword_id}", response_model=BaseResponse[bool])
async def delete_keyword(
    keyword_id: int,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    svc = HotspotKeywordService(db)
    ok = await svc.delete_keyword(keyword_id, current_user.id)
    throw_if(not ok, ErrorCode.NOT_FOUND_ERROR, "关键词不存在")
    return BaseResponse.success(data=True)


# ─── 热点记录 ────────────────────────────────────
@router.get("/records", response_model=BaseResponse[RecordListResponse])
async def list_records(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=50),
    source: str | None = None,
    importance: str | None = None,
    keywordId: int | None = None,
    isReal: bool | None = None,
    timeRange: str | None = None,
    sortBy: str = "created_at",
    sortOrder: str = "desc",
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    req = RecordListRequest(
        page=page, limit=limit, source=source, importance=importance,
        keywordId=keywordId, isReal=isReal, timeRange=timeRange,
        sortBy=sortBy, sortOrder=sortOrder,
    )
    svc = HotspotRecordService(db)
    result = await svc.list_records(req, current_user.id)
    return BaseResponse.success(data=result)


@router.get("/records/stats", response_model=BaseResponse[RecordStatsVO])
async def get_record_stats(
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    svc = HotspotRecordService(db)
    stats = await svc.get_stats(current_user.id)
    return BaseResponse.success(data=stats)


# ─── 通知 ─────────────────────────────────────────
@router.get("/notifications", response_model=BaseResponse[NotificationListResponse])
async def list_notifications(
    limit: int = Query(default=20, ge=1, le=100),
    unreadOnly: bool = False,
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    svc = HotspotNotificationService(db)
    result = await svc.list_notifications(limit=limit, unread_only=unreadOnly)
    return BaseResponse.success(data=result)


@router.patch("/notifications/read-all", response_model=BaseResponse[bool])
async def mark_all_notifications_read(
    db: Database = Depends(get_db),
    current_user: LoginUserVO = Depends(require_login),
):
    svc = HotspotNotificationService(db)
    await svc.mark_all_read()
    return BaseResponse.success(data=True)


# ─── 监控控制 ─────────────────────────────────────
@router.post("/monitor/trigger", response_model=BaseResponse[bool])
async def trigger_monitor(
    current_user: LoginUserVO = Depends(require_login),
):
    """立即触发一次全量扫描（异步，不等待完成）"""
    import asyncio
    asyncio.create_task(monitor_service.scan_all_keywords())
    return BaseResponse.success(data=True, message="扫描任务已触发")


@router.get("/monitor/status", response_model=BaseResponse[MonitorStatusVO])
async def get_monitor_status(
    current_user: LoginUserVO = Depends(require_login),
):
    status = monitor_service.get_status()
    return BaseResponse.success(data=MonitorStatusVO(
        isRunning=status["isRunning"],
        lastRunAt=status["lastRunAt"],
        nextRunAt=None,
        activeKeywordCount=0,
    ))


# ─── WebSocket ────────────────────────────────────
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await hotspot_ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == '{"type":"ping"}':
                await websocket.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        hotspot_ws_manager.disconnect(websocket)
    except Exception:
        hotspot_ws_manager.disconnect(websocket)
```

- [ ] **Step 2: 更新路由 __init__.py**

修改 `backend/app/routers/__init__.py`，添加：

```python
from app.routers.hotspot_monitor import router as hotspot_monitor_router

__all__ = [
    ...现有所有项...,
    "hotspot_monitor_router",
]
```

完整文件内容：

```python
"""API 路由"""

from app.routers.user import router as user_router
from app.routers.health import router as health_router
from app.routers.article import router as article_router
from app.routers.article_sync import router as article_sync_router
from app.routers.hotspot import router as hotspot_router
from app.routers.hotspot_monitor import router as hotspot_monitor_router
from app.routers.payment import payment_router, webhook_router
from app.routers.statistics import router as statistics_router

__all__ = [
    "user_router",
    "health_router",
    "article_router",
    "article_sync_router",
    "hotspot_router",
    "hotspot_monitor_router",
    "payment_router",
    "webhook_router",
    "statistics_router",
]
```

- [ ] **Step 3: 更新 main.py 注册路由 + APScheduler**

修改 `backend/app/main.py` 的 import 区和 lifespan 区：

**import 区新增：**
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.routers import (
    ...,  # 现有
    hotspot_monitor_router,
)
from app.services.hotspot_monitor_service import monitor_service
```

**lifespan 替换为：**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    await database.connect()
    await init_redis()
    print(f"数据库连接成功: {settings.database_url}")
    print(f"Redis 连接成功: {settings.redis_url}")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        monitor_service.scan_all_keywords,
        "interval",
        minutes=30,
        id="hotspot_scan",
        max_instances=1,
    )
    scheduler.start()
    print("热点监控调度器已启动（每30分钟）")

    yield

    scheduler.shutdown(wait=False)
    await database.disconnect()
    await close_redis()
    print("应用已关闭")
```

**路由注册区新增：**
```python
app.include_router(hotspot_monitor_router, prefix="/api")
```

- [ ] **Step 4: 验证启动**

```bash
cd backend && uv run python -c "
from app.main import app
print('路由列表:')
for route in app.routes:
    if hasattr(route, 'path'):
        print(' ', route.path)
" 2>&1 | grep hotspot
```

预期：输出包含 `/api/hotspot/keywords`、`/api/hotspot/records`、`/api/hotspot/ws` 等路由。

- [ ] **Step 5: 全量测试**

```bash
cd backend && uv run python -m pytest app/tests/ -q 2>&1 | tail -5
```

预期：`25 passed`（含之前所有测试）

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/hotspot_monitor.py backend/app/routers/__init__.py backend/app/main.py && git commit -m "feat: 热点监控路由 + APScheduler 30分钟定时扫描"
```

---

### Task 8: 前端 API 类型 + Controller

**Files:**
- Modify: `frontend/src/api/typings.d.ts`
- Create: `frontend/src/api/hotspotMonitorController.ts`

- [ ] **Step 1: 在 typings.d.ts 末尾追加新类型**

在 `frontend/src/api/typings.d.ts` 的 `declare namespace API {` 块内末尾追加：

```typescript
  type HotspotImportance = 'low' | 'medium' | 'high' | 'urgent'

  type KeywordVO = {
    id: number
    text: string
    category?: string
    isActive: boolean
    hotspotCount: number
    createTime?: string
  }

  type RecordVO = {
    id: number
    keywordId?: number
    keywordText?: string
    title: string
    content?: string
    url: string
    source: HotspotSource
    isReal: boolean
    relevance: number
    relevanceReason?: string
    keywordMentioned: boolean
    importance: HotspotImportance
    summary?: string
    heatScore: number
    viewCount?: number
    likeCount?: number
    retweetCount?: number
    commentCount?: number
    authorName?: string
    publishedAt?: string
    createTime: string
  }

  type RecordListResponse = {
    records: RecordVO[]
    total: number
    page: number
    limit: number
    hasMore: boolean
  }

  type RecordStatsVO = {
    total: number
    today: number
    urgent: number
    activeKeywords: number
  }

  type NotificationVO = {
    id: number
    type: string
    title: string
    content?: string
    isRead: boolean
    hotspotRecordId?: number
    createTime: string
  }

  type NotificationListResponse = {
    notifications: NotificationVO[]
    unreadCount: number
  }
```

- [ ] **Step 2: 创建 controller**

创建 `frontend/src/api/hotspotMonitorController.ts`：

```typescript
import request from '@/request'

// ─── 关键词 ───────────────────────────────────────
export function listKeywords() {
  return request.get<{ data: API.KeywordVO[] }>('/hotspot/keywords')
}

export function createKeyword(params: { text: string; category?: string }) {
  return request.post<{ data: number }>('/hotspot/keywords', params)
}

export function toggleKeyword(id: number) {
  return request.patch<{ data: boolean }>(`/hotspot/keywords/${id}/toggle`)
}

export function deleteKeyword(id: number) {
  return request.delete<{ data: boolean }>(`/hotspot/keywords/${id}`)
}

// ─── 热点记录 ─────────────────────────────────────
export function listRecords(params: {
  page?: number
  limit?: number
  source?: string
  importance?: string
  keywordId?: number
  isReal?: boolean
  timeRange?: string
  sortBy?: string
  sortOrder?: string
}) {
  return request.get<{ data: API.RecordListResponse }>('/hotspot/records', { params })
}

export function getRecordStats() {
  return request.get<{ data: API.RecordStatsVO }>('/hotspot/records/stats')
}

// ─── 通知 ─────────────────────────────────────────
export function listNotifications(params?: { limit?: number; unreadOnly?: boolean }) {
  return request.get<{ data: API.NotificationListResponse }>('/hotspot/notifications', { params })
}

export function markAllNotificationsRead() {
  return request.patch<{ data: boolean }>('/hotspot/notifications/read-all')
}

// ─── 监控控制 ─────────────────────────────────────
export function triggerMonitor() {
  return request.post<{ data: boolean }>('/hotspot/monitor/trigger')
}
```

- [ ] **Step 3: 验证前端编译**

```bash
cd frontend && npm run build 2>&1 | grep -E "error|✓ built"
```

预期：`✓ built in ...s`

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/typings.d.ts frontend/src/api/hotspotMonitorController.ts && git commit -m "feat: 热点监控前端 API 类型和调用函数"
```

---

### Task 9: useHotspotWs composable

**Files:**
- Create: `frontend/src/composables/useHotspotWs.ts`

- [ ] **Step 1: 创建 composable**

创建 `frontend/src/composables/useHotspotWs.ts`：

```typescript
import { onMounted, onUnmounted, ref } from 'vue'

export interface HotspotWsEvent {
  type: 'hotspot_new' | 'pong'
  importance?: string
  title?: string
  source?: string
  keywordText?: string
}

export function useHotspotWs(onHotspotNew?: (event: HotspotWsEvent) => void) {
  const isConnected = ref(false)
  let ws: WebSocket | null = null
  let pingInterval: ReturnType<typeof setInterval> | null = null
  let reconnectTimeout: ReturnType<typeof setTimeout> | null = null

  function connect() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = import.meta.env.DEV ? 'localhost:8567' : location.host
    ws = new WebSocket(`${protocol}//${host}/api/hotspot/ws`)

    ws.onopen = () => {
      isConnected.value = true
      pingInterval = setInterval(() => {
        if (ws?.readyState === WebSocket.OPEN) {
          ws.send('{"type":"ping"}')
        }
      }, 30000)
    }

    ws.onmessage = (event) => {
      try {
        const data: HotspotWsEvent = JSON.parse(event.data)
        if (data.type === 'hotspot_new') {
          onHotspotNew?.(data)
        }
      } catch {
        // ignore malformed
      }
    }

    ws.onclose = () => {
      isConnected.value = false
      if (pingInterval) clearInterval(pingInterval)
      // 5秒后重连
      reconnectTimeout = setTimeout(connect, 5000)
    }

    ws.onerror = () => {
      ws?.close()
    }
  }

  function disconnect() {
    if (reconnectTimeout) clearTimeout(reconnectTimeout)
    if (pingInterval) clearInterval(pingInterval)
    ws?.close()
    ws = null
    isConnected.value = false
  }

  onMounted(connect)
  onUnmounted(disconnect)

  return { isConnected }
}
```

- [ ] **Step 2: 验证编译**

```bash
cd frontend && npm run build 2>&1 | grep -E "error|✓ built"
```

预期：`✓ built`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/composables/useHotspotWs.ts && git commit -m "feat: WebSocket composable（自动重连 + 心跳）"
```

---

### Task 10: GlobalHeader 通知铃铛

**Files:**
- Modify: `frontend/src/components/GlobalHeader.vue`

- [ ] **Step 1: 读取当前 GlobalHeader.vue**

文件路径：`frontend/src/components/GlobalHeader.vue`

在 `<script setup lang="ts">` 内已有 imports，在最后追加：

```typescript
import { ref, onMounted } from 'vue'
import { BellOutlined } from '@ant-design/icons-vue'
import { listNotifications, markAllNotificationsRead } from '@/api/hotspotMonitorController'
import { useHotspotWs } from '@/composables/useHotspotWs'

const notifications = ref<API.NotificationVO[]>([])
const unreadCount = ref(0)
const notifVisible = ref(false)

async function loadNotifications() {
  try {
    const res = await listNotifications({ limit: 5 })
    const data = res.data?.data
    if (data) {
      notifications.value = data.notifications
      unreadCount.value = data.unreadCount
    }
  } catch {}
}

async function doMarkAllRead() {
  await markAllNotificationsRead()
  unreadCount.value = 0
  notifications.value = notifications.value.map(n => ({ ...n, isRead: true }))
}

// WebSocket：收到新热点时刷新通知数
useHotspotWs(() => {
  unreadCount.value++
  loadNotifications()
})

onMounted(loadNotifications)
```

- [ ] **Step 2: 在模板 `header-right` 的 `<div v-if="loginUserStore.loginUser.id">` 内，VIP 按钮之前插入铃铛**

在 `<RouterLink v-if="!isVip" ...>升级 VIP</RouterLink>` 之前插入：

```html
<!-- 通知铃铛 -->
<a-popover
  v-model:open="notifVisible"
  trigger="click"
  placement="bottomRight"
  :arrow="false"
>
  <template #content>
    <div class="notif-panel">
      <div class="notif-header">
        <span>通知</span>
        <a-button type="link" size="small" @click="doMarkAllRead">全部已读</a-button>
      </div>
      <div v-if="notifications.length === 0" class="notif-empty">暂无通知</div>
      <div v-for="n in notifications" :key="n.id" :class="['notif-item', { unread: !n.isRead }]">
        <div class="notif-title">{{ n.title }}</div>
        <div v-if="n.content" class="notif-content">{{ n.content }}</div>
      </div>
    </div>
  </template>
  <a-badge :count="unreadCount" :overflow-count="99" class="notif-bell">
    <BellOutlined class="bell-icon" />
  </a-badge>
</a-popover>
```

- [ ] **Step 3: 在 `<style scoped>` 末尾追加铃铛样式**

```scss
.notif-bell {
  cursor: pointer;
  margin-right: 12px;
}

.bell-icon {
  font-size: 18px;
  color: var(--color-text-secondary);
}

.notif-panel {
  width: 300px;
  max-height: 360px;
  overflow-y: auto;
}

.notif-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0 8px;
  font-weight: 600;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: 8px;
}

.notif-empty {
  text-align: center;
  color: var(--color-text-muted);
  padding: 24px 0;
  font-size: 13px;
}

.notif-item {
  padding: 8px 0;
  border-bottom: 1px solid var(--color-border);
  font-size: 13px;
}

.notif-item.unread .notif-title {
  font-weight: 600;
}

.notif-title {
  color: var(--color-text);
  margin-bottom: 4px;
}

.notif-content {
  color: var(--color-text-secondary);
  font-size: 12px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
```

- [ ] **Step 4: 验证编译**

```bash
cd frontend && npm run build 2>&1 | grep -E "error|✓ built"
```

预期：`✓ built`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/GlobalHeader.vue && git commit -m "feat: GlobalHeader 通知铃铛（WebSocket 实时未读数）"
```

---

### Task 11: KeywordsTab.vue

**Files:**
- Create: `frontend/src/pages/topic/KeywordsTab.vue`

- [ ] **Step 1: 创建组件**

确保目录存在：
```bash
mkdir -p frontend/src/pages/topic
```

创建 `frontend/src/pages/topic/KeywordsTab.vue`：

```vue
<template>
  <div class="keywords-tab">
    <div class="add-form">
      <a-input
        v-model:value="newText"
        placeholder="输入关键词，如 AI 编程、Claude Code"
        class="kw-input"
        @press-enter="doCreate"
      />
      <a-input
        v-model:value="newCategory"
        placeholder="分类（可选）"
        class="cat-input"
      />
      <a-button type="primary" :loading="creating" @click="doCreate">
        + 添加
      </a-button>
    </div>

    <div v-if="loading" class="kw-loading"><a-spin /></div>

    <div v-else-if="keywords.length === 0" class="kw-empty">
      <a-empty description="还没有监控关键词，添加一个开始监控热点吧" />
    </div>

    <div v-else class="kw-grid">
      <div
        v-for="kw in keywords"
        :key="kw.id"
        :class="['kw-card', { inactive: !kw.isActive }]"
      >
        <div class="kw-main">
          <span class="kw-text">{{ kw.text }}</span>
          <span v-if="kw.category" class="kw-category">{{ kw.category }}</span>
        </div>
        <div class="kw-meta">
          <span class="kw-count">{{ kw.hotspotCount }} 条热点</span>
        </div>
        <div class="kw-actions">
          <a-switch
            :checked="kw.isActive"
            size="small"
            :loading="togglingId === kw.id"
            @change="doToggle(kw)"
          />
          <a-popconfirm title="确定删除该关键词吗？" @confirm="doDelete(kw.id)">
            <a-button type="text" danger size="small" class="del-btn">删除</a-button>
          </a-popconfirm>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { listKeywords, createKeyword, toggleKeyword, deleteKeyword } from '@/api/hotspotMonitorController'

const keywords = ref<API.KeywordVO[]>([])
const loading = ref(false)
const creating = ref(false)
const togglingId = ref<number | null>(null)
const newText = ref('')
const newCategory = ref('')

async function load() {
  loading.value = true
  try {
    const res = await listKeywords()
    keywords.value = res.data?.data || []
  } catch {
    message.error('加载关键词失败')
  } finally {
    loading.value = false
  }
}

async function doCreate() {
  const text = newText.value.trim()
  if (!text) return message.warning('请输入关键词')
  creating.value = true
  try {
    await createKeyword({ text, category: newCategory.value.trim() || undefined })
    newText.value = ''
    newCategory.value = ''
    message.success('关键词添加成功')
    await load()
  } catch (err: any) {
    message.error(err?.response?.data?.message || '添加失败')
  } finally {
    creating.value = false
  }
}

async function doToggle(kw: API.KeywordVO) {
  togglingId.value = kw.id
  try {
    await toggleKeyword(kw.id)
    kw.isActive = !kw.isActive
  } catch {
    message.error('切换失败')
  } finally {
    togglingId.value = null
  }
}

async function doDelete(id: number) {
  try {
    await deleteKeyword(id)
    keywords.value = keywords.value.filter(k => k.id !== id)
    message.success('删除成功')
  } catch {
    message.error('删除失败')
  }
}

onMounted(load)
</script>

<style scoped lang="scss">
.keywords-tab { padding: 8px 0; }

.add-form {
  display: flex;
  gap: 10px;
  margin-bottom: 24px;
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 16px;
}

.kw-input { flex: 2; }
.cat-input { flex: 1; }

.kw-loading, .kw-empty {
  display: flex;
  justify-content: center;
  padding: 48px 0;
}

.kw-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.kw-card {
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: opacity 0.2s;
}

.kw-card.inactive { opacity: 0.5; }

.kw-main { display: flex; align-items: center; gap: 8px; }

.kw-text { font-size: 16px; font-weight: 600; color: var(--color-text); }

.kw-category {
  font-size: 12px;
  color: var(--color-primary);
  background: rgba(34,197,94,0.1);
  padding: 2px 8px;
  border-radius: 999px;
}

.kw-meta { color: var(--color-text-muted); font-size: 13px; }

.kw-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
```

- [ ] **Step 2: 验证编译**

```bash
cd frontend && npm run build 2>&1 | grep -E "error|✓ built"
```

预期：`✓ built`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/topic/KeywordsTab.vue && git commit -m "feat: 关键词管理 Tab（增删查切换）"
```

---

### Task 12: MonitorTab.vue

**Files:**
- Create: `frontend/src/pages/topic/MonitorTab.vue`

- [ ] **Step 1: 创建组件**

创建 `frontend/src/pages/topic/MonitorTab.vue`：

```vue
<template>
  <div class="monitor-tab">
    <!-- 统计卡片 -->
    <section class="stats-grid">
      <div class="stat-card">
        <span>总热点</span>
        <strong>{{ stats.total }}</strong>
      </div>
      <div class="stat-card accent">
        <span>今日新增</span>
        <strong>{{ stats.today }}</strong>
      </div>
      <div class="stat-card danger">
        <span>紧急热点</span>
        <strong>{{ stats.urgent }}</strong>
      </div>
      <div class="stat-card success">
        <span>活跃关键词</span>
        <strong>{{ stats.activeKeywords }}</strong>
      </div>
    </section>

    <!-- 筛选栏 -->
    <section class="filter-bar">
      <a-select v-model:value="filters.source" allow-clear placeholder="来源" class="filter-item" @change="onFilterChange">
        <a-select-option v-for="s in sourceOptions" :key="s.value" :value="s.value">{{ s.label }}</a-select-option>
      </a-select>
      <a-select v-model:value="filters.importance" allow-clear placeholder="重要程度" class="filter-item" @change="onFilterChange">
        <a-select-option value="urgent">紧急</a-select-option>
        <a-select-option value="high">重要</a-select-option>
        <a-select-option value="medium">中等</a-select-option>
        <a-select-option value="low">一般</a-select-option>
      </a-select>
      <a-select v-model:value="filters.keywordId" allow-clear placeholder="关键词" class="filter-item" @change="onFilterChange">
        <a-select-option v-for="kw in keywords" :key="kw.id" :value="kw.id">{{ kw.text }}</a-select-option>
      </a-select>
      <a-select v-model:value="filters.timeRange" allow-clear placeholder="时间范围" class="filter-item" @change="onFilterChange">
        <a-select-option value="1h">1小时内</a-select-option>
        <a-select-option value="today">今天</a-select-option>
        <a-select-option value="7d">7天内</a-select-option>
        <a-select-option value="30d">30天内</a-select-option>
      </a-select>
      <a-select v-model:value="filters.isReal" allow-clear placeholder="真实性" class="filter-item" @change="onFilterChange">
        <a-select-option :value="true">真实</a-select-option>
        <a-select-option :value="false">存疑</a-select-option>
      </a-select>
      <a-select v-model:value="filters.sortBy" placeholder="排序" class="filter-item" @change="onFilterChange">
        <a-select-option value="created_at">发现时间</a-select-option>
        <a-select-option value="published_at">发布时间</a-select-option>
        <a-select-option value="importance">重要程度</a-select-option>
        <a-select-option value="relevance">相关性</a-select-option>
        <a-select-option value="heat">热度综合</a-select-option>
      </a-select>
      <a-button :loading="triggering" @click="doTrigger">立即扫描</a-button>
    </section>

    <!-- 热点列表 -->
    <div v-if="loading && records.length === 0" class="list-loading"><a-spin /></div>

    <div v-else-if="records.length === 0" class="list-empty">
      <a-empty description="暂无热点记录，请先添加关键词并触发扫描" />
    </div>

    <div v-else class="record-list">
      <article v-for="item in records" :key="item.id" class="record-card">
        <div class="record-tags">
          <a-tag :color="importanceColor(item.importance)">{{ importanceLabel(item.importance) }}</a-tag>
          <a-tag :color="sourceColor(item.source)">{{ sourceLabel(item.source) }}</a-tag>
          <a-tag v-if="item.keywordText" color="purple">{{ item.keywordText }}</a-tag>
          <a-tag v-if="item.keywordMentioned" color="blue">直接提及</a-tag>
          <a-tag :color="item.isReal ? 'green' : 'orange'">{{ item.isReal ? '真实' : '存疑' }}</a-tag>
          <a-tag color="red">热 {{ Math.round(item.heatScore) }}</a-tag>
        </div>
        <h3><a :href="item.url" target="_blank" rel="noreferrer">{{ item.title }}</a></h3>
        <p class="record-summary">
          <span>AI 摘要</span>{{ item.summary || item.content }}
        </p>
        <div class="record-meta">
          <span>相关性 {{ item.relevance }}%</span>
          <span v-if="item.likeCount">👍 {{ fmt(item.likeCount) }}</span>
          <span v-if="item.retweetCount">🔁 {{ fmt(item.retweetCount) }}</span>
          <span v-if="item.commentCount">💬 {{ fmt(item.commentCount) }}</span>
          <span v-if="item.viewCount">👁 {{ fmt(item.viewCount) }}</span>
          <span class="time">发现 {{ formatDate(item.createTime) }}</span>
          <span v-if="item.publishedAt" class="time">发布 {{ formatDate(item.publishedAt) }}</span>
        </div>
        <a-collapse ghost class="reason-collapse">
          <a-collapse-panel key="r" header="AI 分析理由">
            {{ item.relevanceReason || '暂无' }}
          </a-collapse-panel>
        </a-collapse>
      </article>
    </div>

    <!-- 分页 -->
    <div v-if="total > 0" class="pagination">
      <a-pagination
        v-model:current="page"
        :total="total"
        :page-size="limit"
        show-quick-jumper
        @change="loadRecords"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'
import { listKeywords } from '@/api/hotspotMonitorController'
import { getRecordStats, listRecords, triggerMonitor } from '@/api/hotspotMonitorController'
import { useHotspotWs } from '@/composables/useHotspotWs'

const sourceOptions = [
  { label: '微博', value: 'weibo' }, { label: 'B站', value: 'bilibili' },
  { label: '搜狗', value: 'sogou' }, { label: 'Bing', value: 'bing' },
  { label: 'HN', value: 'hackernews' }, { label: 'Twitter/X', value: 'twitter' },
  { label: 'DuckDuckGo', value: 'duckduckgo' },
]

const stats = ref<API.RecordStatsVO>({ total: 0, today: 0, urgent: 0, activeKeywords: 0 })
const records = ref<API.RecordVO[]>([])
const keywords = ref<API.KeywordVO[]>([])
const loading = ref(false)
const triggering = ref(false)
const page = ref(1)
const limit = ref(20)
const total = ref(0)

const filters = reactive({
  source: undefined as string | undefined,
  importance: undefined as string | undefined,
  keywordId: undefined as number | undefined,
  timeRange: undefined as string | undefined,
  isReal: undefined as boolean | undefined,
  sortBy: 'created_at',
})

async function loadStats() {
  try {
    const res = await getRecordStats()
    stats.value = res.data?.data || stats.value
  } catch {}
}

async function loadKeywords() {
  try {
    const res = await listKeywords()
    keywords.value = res.data?.data || []
  } catch {}
}

async function loadRecords() {
  loading.value = true
  try {
    const res = await listRecords({
      page: page.value, limit: limit.value,
      ...filters,
    })
    const data = res.data?.data
    if (data) {
      records.value = data.records
      total.value = data.total
    }
  } catch {
    message.error('加载热点失败')
  } finally {
    loading.value = false
  }
}

function onFilterChange() {
  page.value = 1
  loadRecords()
}

async function doTrigger() {
  triggering.value = true
  try {
    await triggerMonitor()
    message.success('扫描任务已触发，稍后刷新查看新热点')
    setTimeout(() => { loadRecords(); loadStats() }, 3000)
  } catch {
    message.error('触发失败')
  } finally {
    triggering.value = false
  }
}

// 收到 WebSocket 推送时刷新第一页
useHotspotWs(() => {
  loadStats()
  if (page.value === 1) loadRecords()
})

const importanceLabel = (v: string) => ({ urgent: '紧急', high: '重要', medium: '中等', low: '一般' }[v] || v)
const importanceColor = (v: string) => ({ urgent: 'red', high: 'volcano', medium: 'gold', low: 'blue' }[v] || 'default')
const sourceLabel = (v: string) => sourceOptions.find(s => s.value === v)?.label || v
const sourceColor = (v: string): string => ({ weibo: 'red', bilibili: 'pink', sogou: 'blue', bing: 'cyan', hackernews: 'orange', twitter: 'purple', duckduckgo: 'geekblue' }[v] || 'default')
const formatDate = (d: string) => dayjs(d).format('MM-DD HH:mm')
const fmt = (n: number) => n >= 10000 ? `${(n / 10000).toFixed(1)}万` : n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n)

onMounted(() => { loadStats(); loadKeywords(); loadRecords() })
</script>

<style scoped lang="scss">
.monitor-tab { padding: 8px 0; }

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.stat-card {
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 22px;
}
.stat-card span { color: var(--color-text-muted); font-size: 14px; }
.stat-card strong { display: block; font-size: 34px; line-height: 1.2; margin-top: 12px; color: var(--color-text); }
.stat-card.accent strong { color: #06b6d4; }
.stat-card.danger strong { color: #f43f5e; }
.stat-card.success strong { color: #10b981; }

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 12px 16px;
  margin-bottom: 16px;
}

.filter-item { width: 140px; }

.list-loading, .list-empty {
  display: flex;
  justify-content: center;
  padding: 64px 0;
}

.record-list { display: flex; flex-direction: column; gap: 16px; }

.record-card {
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 20px;
}

.record-tags { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }

.record-card h3 { margin: 0 0 12px; font-size: 17px; line-height: 1.5; }
.record-card h3 a { color: var(--color-text); text-decoration: none; }
.record-card h3 a:hover { color: var(--color-primary); }

.record-summary { color: var(--color-text-secondary); font-size: 14px; line-height: 1.7; margin: 0 0 12px; }
.record-summary span { color: var(--color-primary); font-weight: 700; margin-right: 8px; }

.record-meta { display: flex; flex-wrap: wrap; gap: 10px; color: var(--color-text-muted); font-size: 13px; }
.time { margin-left: auto; }

.reason-collapse { margin-top: 8px; }

.pagination { display: flex; justify-content: center; margin-top: 32px; padding-bottom: 16px; }

@media (max-width: 900px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .filter-item { width: 100%; }
}
</style>
```

- [ ] **Step 2: 验证编译**

```bash
cd frontend && npm run build 2>&1 | grep -E "error|✓ built"
```

预期：`✓ built`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/topic/MonitorTab.vue && git commit -m "feat: 监控热点 Tab（筛选/排序/分页/WebSocket刷新）"
```

---

### Task 13: TopicPage 改为 4 Tab 布局

**Files:**
- Modify: `frontend/src/pages/TopicPage.vue`

- [ ] **Step 1: 替换 script 区的 Tab 定义和组件导入**

在 `TopicPage.vue` 的 `<script setup lang="ts">` 内，在现有 import 后追加：

```typescript
import KeywordsTab from './topic/KeywordsTab.vue'
import MonitorTab from './topic/MonitorTab.vue'
```

将 `activeTab` 的 `useSessionRef` 初始值改为 `'monitor'`（原来是 `'radar'`）：

```typescript
const activeTab = useSessionRef('hotspot-active-tab', 'monitor')
```

- [ ] **Step 2: 替换模板中 `<a-tabs>` 区域**

找到 `<a-tabs v-model:activeKey="activeTab" class="topic-tabs">` 标签，将整个 `<a-tabs>` 块替换为：

```html
<a-tabs v-model:activeKey="activeTab" class="topic-tabs">
  <!-- Tab 1: 关键词 -->
  <a-tab-pane key="keywords" tab="关键词">
    <KeywordsTab />
  </a-tab-pane>

  <!-- Tab 2: 监控热点 -->
  <a-tab-pane key="monitor" tab="监控热点">
    <MonitorTab />
  </a-tab-pane>

  <!-- Tab 3: 搜索（原热点雷达） -->
  <a-tab-pane key="radar" tab="搜索">
    <!-- 以下是现有热点雷达完整内容，保持不变 -->
    <section class="stats-grid">
      ... （保留原有内容）
    </section>
    ... （保留原有内容到结束）
  </a-tab-pane>

  <!-- Tab 4: 生成选题（保持不变） -->
  <a-tab-pane key="suggestions" tab="生成选题">
    ... （保留原有内容）
  </a-tab-pane>
</a-tabs>
```

**具体做法**：打开文件，找到第59行的 `<a-tabs v-model:activeKey="activeTab" class="topic-tabs">`，在现有两个 `a-tab-pane` 之前插入两个新的，并把 `key="radar"` 的 tab 标签文本从 `热点雷达` 改为 `搜索`：

将原 `<a-tab-pane key="radar" tab="热点雷达">` 改为：
```html
<a-tab-pane key="radar" tab="搜索">
```

在该 tab-pane 之前（`<a-tabs>` 开始标签之后）插入：
```html
<a-tab-pane key="keywords" tab="关键词">
  <KeywordsTab />
</a-tab-pane>

<a-tab-pane key="monitor" tab="监控热点">
  <MonitorTab />
</a-tab-pane>
```

- [ ] **Step 3: 验证编译（最终全量）**

```bash
cd frontend && npm run build 2>&1 | grep -E "error|✓ built"
```

预期：`✓ built`

- [ ] **Step 4: 验证后端全量测试**

```bash
cd backend && uv run python -m pytest app/tests/ -q 2>&1 | tail -5
```

预期：`25 passed`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/TopicPage.vue && git commit -m "feat: TopicPage 升级为4 Tab布局（关键词/监控热点/搜索/生成选题）"
```

---

## 自检：规格覆盖

| 需求 | 对应 Task |
|------|-----------|
| 3张新 DB 表 | Task 1 |
| Pydantic schemas | Task 2 |
| 关键词 CRUD（增删改查激活） | Task 3, 7 |
| 热点记录写入（去重） | Task 4, 6 |
| 热点记录查询（5个筛选项+5个排序） | Task 4, 7 |
| 通知 CRUD | Task 5 |
| WebSocket 广播 | Task 5, 6 |
| HotspotMonitorService（扫描→写DB→广播） | Task 6 |
| APScheduler 30分钟定时 + 手动触发 | Task 7 |
| 前端 API 类型 + controller | Task 8 |
| WebSocket composable（自动重连+心跳） | Task 9 |
| 通知铃铛（GlobalHeader） | Task 10 |
| KeywordsTab（关键词管理） | Task 11 |
| MonitorTab（筛选/排序/分页/实时刷新） | Task 12 |
| TopicPage 4 Tab 布局 | Task 13 |
| 筛选：来源/重要程度/关键词/时间/真实性 | Task 12 |
