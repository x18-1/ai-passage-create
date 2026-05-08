# 热点持续监控功能设计

**日期**: 2026-05-08  
**目标**: 将参考项目（yupi-hot-monitor）的持续监控功能迁移至本项目，实现关键词管理、后台定时扫描、热点持久化、WebSocket 实时推送、站内通知，不含邮件功能。

## 产品需求

### TopicPage 新 Tab 布局
```
[ 关键词 ]  [ 监控热点 ]  [ 搜索 ]  [ 生成选题 ]
```

- **关键词**：创建/激活/删除监控关键词，显示每个关键词的热点数
- **监控热点**：展示数据库里存储的热点，带筛选（来源/重要程度/关键词/时间/真实性）和分页
- **搜索**：保留现有按需搜索（原"热点雷达" Tab 重命名）
- **生成选题**：不变

### 自动扫描
- 每 30 分钟自动扫描所有激活的关键词
- 提供"立即扫描"按钮手动触发

### 实时通知
- WebSocket 广播新热点到所有在线客户端
- GlobalHeader 右上角铃铛 + 未读数角标
- 点击铃铛展开最近 5 条通知，"全部已读"按钮

---

## 数据库设计

### 新增 SQL 文件：`sql/add_hotspot_monitoring.sql`

**hotspot_keyword 表**
```sql
CREATE TABLE hotspot_keyword (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    userId      BIGINT NOT NULL COMMENT '所属用户',
    text        VARCHAR(200) NOT NULL COMMENT '关键词',
    category    VARCHAR(100) NULL COMMENT '分类（可选）',
    isActive    TINYINT DEFAULT 1 NOT NULL COMMENT '是否激活',
    createTime  DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updateTime  DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_userId_text (userId, text)
) COMMENT='热点监控关键词' COLLATE=utf8mb4_unicode_ci;
```

**hotspot_record 表**
```sql
CREATE TABLE hotspot_record (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    keywordId       BIGINT NULL COMMENT '关联关键词 ID（删除时置 NULL）',
    keywordText     VARCHAR(200) NULL COMMENT '关键词快照（关键词删除后保留记录）',
    title           VARCHAR(500) NOT NULL COMMENT '热点标题',
    content         TEXT NULL COMMENT '原始内容',
    url             VARCHAR(1024) NOT NULL COMMENT '链接',
    source          VARCHAR(50) NOT NULL COMMENT '来源',
    sourceId        VARCHAR(200) NULL COMMENT '平台内容 ID',
    isReal          TINYINT DEFAULT 1 NOT NULL COMMENT '是否真实内容',
    relevance       INT DEFAULT 0 NOT NULL COMMENT '相关性 0-100',
    relevanceReason VARCHAR(500) NULL COMMENT '相关性理由',
    keywordMentioned TINYINT DEFAULT 0 NOT NULL COMMENT '是否直接提及关键词',
    importance      VARCHAR(20) DEFAULT 'low' NOT NULL COMMENT 'low/medium/high/urgent',
    summary         VARCHAR(500) NULL COMMENT 'AI 摘要',
    heatScore       FLOAT DEFAULT 0 NOT NULL COMMENT '热度分',
    viewCount       BIGINT NULL,
    likeCount       BIGINT NULL,
    retweetCount    BIGINT NULL,
    commentCount    BIGINT NULL,
    authorName      VARCHAR(200) NULL,
    authorUsername  VARCHAR(200) NULL,
    authorFollowers BIGINT NULL,
    authorVerified  TINYINT NULL,
    publishedAt     DATETIME NULL COMMENT '内容发布时间',
    createTime      DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL COMMENT '发现时间',
    UNIQUE KEY uk_url_source (url(512), source)
) COMMENT='热点记录' COLLATE=utf8mb4_unicode_ci;
```

**hotspot_notification 表**
```sql
CREATE TABLE hotspot_notification (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    type            VARCHAR(50) DEFAULT 'hotspot' NOT NULL COMMENT '类型：hotspot/alert',
    title           VARCHAR(300) NOT NULL,
    content         VARCHAR(500) NULL,
    isRead          TINYINT DEFAULT 0 NOT NULL,
    hotspotRecordId BIGINT NULL COMMENT '关联热点记录',
    createTime      DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    INDEX idx_isRead (isRead),
    INDEX idx_createTime (createTime)
) COMMENT='热点站内通知' COLLATE=utf8mb4_unicode_ci;
```

---

## 后端架构

### 新增文件列表

```
backend/app/
├── models/
│   ├── hotspot_keyword.py      # SQLAlchemy ORM
│   ├── hotspot_record.py
│   └── hotspot_notification.py
├── schemas/
│   └── hotspot_monitor.py      # 请求/响应 Pydantic 模型
├── services/
│   ├── hotspot_keyword_service.py     # 关键词 CRUD
│   ├── hotspot_record_service.py      # 热点查询/过滤
│   ├── hotspot_notification_service.py # 通知 CRUD
│   └── hotspot_monitor_service.py     # 扫描调度器（核心）
├── managers/
│   └── hotspot_ws_manager.py          # WebSocket 连接管理
└── routers/
    └── hotspot_monitor.py             # 所有新路由
```

修改文件：
- `backend/app/main.py` — lifespan 里注册 APScheduler
- `backend/app/routers/__init__.py` — 注册新路由

### API 路由（前缀 `/api/hotspot`）

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/keywords` | 列出当前用户所有关键词（含热点数） |
| POST | `/keywords` | 创建关键词 |
| PATCH | `/keywords/{id}/toggle` | 切换激活状态 |
| DELETE | `/keywords/{id}` | 删除关键词 |
| GET | `/records` | 分页查询热点记录（带过滤/排序） |
| GET | `/records/stats` | 统计（总数/今日/紧急/活跃关键词数） |
| GET | `/notifications` | 查询通知（带未读过滤） |
| PATCH | `/notifications/read-all` | 全部标为已读 |
| POST | `/monitor/trigger` | 立即触发一次扫描 |
| WS | `/ws` | WebSocket 连接端点 |

### GET /records 过滤参数

| 参数 | 类型 | 说明 |
|------|------|------|
| page | int | 页码，默认 1 |
| limit | int | 每页条数，默认 20，最大 50 |
| source | str | 来源过滤 |
| importance | str | 重要程度过滤 |
| keyword_id | int | 按关键词过滤 |
| is_real | bool | 真实性过滤 |
| time_range | str | 1h/today/7d/30d |
| sort_by | str | created_at/published_at/relevance/importance/heat（默认 created_at） |
| sort_order | str | desc/asc（默认 desc） |

importance 和 heat 排序在内存中执行（数据量小，分页后处理）；其他排序在 DB 层执行。

### HotspotMonitorService（核心）

```
scan_all_keywords():
  → 从 DB 读所有 is_active=True 的关键词
  → 对每个关键词调用 scan_one_keyword(keyword)
  → 关键词间串行（避免并发过高）

scan_one_keyword(keyword):
  → 复用 HotspotService 的扫描逻辑（expand → fetch → analyze）
  → 每条通过过滤的热点：
      → 检查 url+source 是否已存在（跳过重复）
      → 写入 hotspot_record
      → 写入 hotspot_notification
      → WebSocket 广播 {"type": "hotspot_new", "importance": ..., "title": ...}
```

### WebSocket 连接管理

`HotspotWsManager`：
- 维护活跃连接集合
- `broadcast(message: dict)` — 向所有连接广播
- 连接断开时自动移除

WebSocket 端点 `/api/hotspot/ws`：
- 不需要路径参数（广播给所有在线用户）
- 连接后保持心跳（客户端发 `{"type":"ping"}` 服务端回 `{"type":"pong"}`）
- 新热点发现时服务端推送 `{"type":"hotspot_new","importance":"high","title":"..."}`

### APScheduler 集成

在 `main.py` 的 `lifespan` 里注册：
```python
scheduler = AsyncIOScheduler()
scheduler.add_job(monitor_service.scan_all_keywords, "interval", minutes=30, id="hotspot_scan")
scheduler.start()
# shutdown 时 scheduler.shutdown()
```

依赖：`apscheduler>=3.10`

---

## 前端架构

### 新增文件

```
frontend/src/
├── pages/topic/
│   ├── KeywordsTab.vue        # 关键词管理
│   └── MonitorTab.vue         # 监控热点列表+筛选
└── composables/
    └── useHotspotWs.ts        # WebSocket 连接与事件处理
```

修改文件：
- `frontend/src/pages/TopicPage.vue` — 改造为 4 Tab 布局，集成 WebSocket
- `frontend/src/components/GlobalHeader.vue` — 新增通知铃铛
- `frontend/src/api/hotspotController.ts` — 新增 API 调用函数
- `frontend/src/api/typings.d.ts` — 新增类型定义

### KeywordsTab 界面

```
[ 输入关键词 ] [ 分类（可选） ] [ + 添加 ]

┌─ AI 编程 ──────────── 42条 ─ [开关] [删除] ┐
│  分类：技术                                 │
└────────────────────────────────────────────┘
┌─ Claude Code ────────── 18条 ─ [开关] [删除] ┐
│  分类：AI                                    │
└──────────────────────────────────────────────┘
```

- 开关切换 `isActive`，灰色表示未激活
- 删除弹确认框

### MonitorTab 界面

顶部统计卡片：总热点 / 今日新增 / 紧急热点

筛选栏（与参考项目一致）：
```
[ 来源▼ ] [ 重要程度▼ ] [ 关键词▼ ] [ 时间范围▼ ] [ 真实性▼ ] [ 排序▼ ] [立即扫描]
```

热点卡片（与现有风格一致）：
- 标题 + AI摘要 + 标签（重要程度/来源/关键词/真实性）
- 互动数字（点赞/转发/评论/浏览）
- 发现时间 + 发布时间
- 展开/收起「AI 分析理由」和「原始内容」

分页：20条/页，[上一页] [1 2 3...] [下一页]

### useHotspotWs.ts

```typescript
// 连接 WebSocket，处理 hotspot_new 事件
// 收到新热点时：
//   1. 更新通知未读数（notificationCount.value++）
//   2. 如果当前在 MonitorTab，刷新第一页数据
```

### GlobalHeader 通知铃铛

- `GET /api/hotspot/notifications?limit=5` 加载最近通知
- 未读数角标（红点，数量）
- 展开下拉：最近 5 条，"全部已读"按钮
- 通知高亮显示 urgent/high 重要程度

---

## 不改动的部分

- 现有 `scan_radar`（SSE 按需搜索）— 重命名为"搜索" Tab 保留
- 现有 `generate_topic_suggestions`（选题生成）— 不变
- 现有 `HotspotAnalysisService` / `HotspotSourceService` — 直接复用
- 用户认证体系 — 不变（关键词按 userId 隔离）

---

## 筛选条件完整列表

| 筛选项 | 参考项目 | 本项目 |
|--------|---------|--------|
| 来源 | twitter/bing/sogou/bilibili/weibo/hackernews/duckduckgo | 同上 |
| 重要程度 | urgent/high/medium/low | 同上 |
| 关键词 | 按 keyword_id | 按 keyword_id |
| 时间范围 | 1h/today/7d/30d | 同上 |
| 真实性 | is_real true/false | 同上 |

---

## 依赖变更

新增 Python 包：
- `apscheduler>=3.10` — 后台调度器

无需新增前端包（Vue 3 内置 WebSocket 支持）。
