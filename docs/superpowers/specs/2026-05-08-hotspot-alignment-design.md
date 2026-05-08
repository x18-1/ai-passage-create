# 热点追踪后端对齐设计

**日期**: 2026-05-08  
**目标**: 将现有热点追踪后端对齐参考项目（yupi-hot-monitor），提升筛选质量和速度。

## 背景

现有实现与参考项目对比发现以下差距：
- Twitter 无本地预过滤，低质量推文直接进入 AI 分析
- Twitter 只拉 1 次请求，参考项目拉 Top 2页 + Latest 1页
- 各来源无限速，存在被封 IP 风险
- 关键词扩展每次都调 AI，无缓存
- AI prompt 缺少量化评分锚点，AI 判断不一致
- 分析配额平均分配，没有 Twitter 优先
- 无账号检测（B站 UP 主）功能

## 改动范围

涉及文件：
- `backend/app/services/hotspot_sources.py`
- `backend/app/services/hotspot_analysis_service.py`
- `backend/app/services/hotspot_service.py`

不新增文件，不改动 schema、router、测试。

---

## 改动 1 — 限速器（`hotspot_sources.py`）

新增 `RateLimiter` 类，每次请求前等待距上次请求的最小间隔。

```python
class RateLimiter:
    def __init__(self, min_interval_ms: int):
        self.min_interval = min_interval_ms / 1000
        self.last_request_time = 0.0

    async def wait(self):
        elapsed = time.monotonic() - self.last_request_time
        remaining = self.min_interval - elapsed
        if remaining > 0:
            await asyncio.sleep(remaining)
        self.last_request_time = time.monotonic()
```

各来源独立实例：
| 来源 | 间隔 |
|------|------|
| Sogou | 3000ms |
| Bilibili | 2000ms |
| Weibo | 3000ms |
| Bing | 5000ms |
| HackerNews | 1000ms |

限速器挂在 `HotspotSourceService` 实例上（进程级单例），跨请求共享。

## 改动 2 — UA 随机化（`hotspot_sources.py`）

将固定 `USER_AGENT` 替换为 `USER_AGENTS` 列表（3个），每次请求随机选取。

## 改动 3 — Twitter 多页拉取 + 本地预过滤（`hotspot_sources.py`）

### 多页拉取

同时发起两种搜索（并行）：
- Top 搜索：近 7 天，min_faves:10，拉 2 页（有 next_cursor 时拉第 2 页）
- Latest 搜索：近 3 天，拉 1 页

两种结果合并去重后进行本地过滤。

### 本地质量过滤阈值

| 指标 | 普通用户 | 蓝V用户（减半） |
|------|----------|----------------|
| 点赞数 | ≥ 10 | ≥ 5 |
| 转发数 | ≥ 5 | ≥ 2.5 → 取整 ≥ 2 |
| 浏览量 | ≥ 500 | ≥ 250 |
| 粉丝数 | ≥ 100 | ≥ 50 |

额外规则：过滤回复类推文（type 含 "reply" 或文本以 `@用户名 ` 开头）。

### 质量评分排序

过滤后按评分降序排列：
```
score = likes * 2 + retweets * 3 + views / 100 + (50 if blue_verified else 0)
```

## 改动 4 — 账号检测（`hotspot_sources.py`）

新增 `detect_and_fetch_account(keyword)` 方法：

1. 调用 B 站用户搜索接口（`/x/web-interface/search/type?search_type=bili_user`）
2. 如果有匹配账号（粉丝数 > 1000 且用户名或昵称与关键词相近），拉取该 UP 主最新视频
3. 返回账号列表 + 对应内容列表

在 `search_sources` 中，账号检测结果优先放在所有来源结果之前。

账号匹配条件：
- 用户名（username）或昵称（name）小写后包含关键词（小写）
- 粉丝数 > 1000

## 改动 5 — 关键词扩展缓存（`hotspot_analysis_service.py`）

`expand_keyword` 方法加内存字典缓存：
```python
self._expansion_cache: dict[str, list[str]] = {}
```

命中缓存时直接返回，不调 AI。缓存在服务实例生命周期内有效（进程级）。

## 改动 6 — AI Prompt 量化锚点（`hotspot_analysis_service.py`）

`_build_analysis_prompt` 中补充明确的评分规则：

```
评分规则：
- 同领域但未直接提及关键词 → 低于 40 分
- 间接相关（同类产品/同领域不同主题）→ 30-50 分  
- 直接讨论、提及或有实质关联 → 60 分以上
- 仅属于同一领域而无关联 → 低于 40 分

summary 字段要求：说明此内容与关键词的关系，而非内容本身的介绍。
```

## 改动 7 — Twitter 优先配额（`hotspot_service.py`）

`scan_radar` 中，`prioritize_for_analysis` 排序后，不再统一取前 N 条。改为：

```python
TWITTER_QUOTA = 15
OTHER_QUOTA = 10

items_for_analysis = []
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

`analyze_limit` 参数保留兼容，但优先使用配额逻辑。

---

## 数据流变化（scan_radar）

```
原始：expand → fetch(并发) → dedup → prioritize → 取前N → AI分析 → filter_rank

改后：
  账号检测(B站) ┐
  并发fetch 6源 ┘→ 合并(账号优先) → dedup → freshness过滤 → prioritize
  → Twitter配额15 + 其他配额10 → AI分析(semaphore=3) → filter_rank
```

---

## 不改动的部分

- `filter_and_rank`：过滤逻辑（relevance<50、keyword未提及且<65）保持不变
- `_apply_pre_match_floor`：预匹配兜底逻辑保持不变
- `calc_hot_score`：热度计算公式保持不变
- 所有 schema、router、测试文件
- `generate_topic_suggestions`：选题生成逻辑保持不变
