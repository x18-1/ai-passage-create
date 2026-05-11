# AI 爆款文章创作器 ✍️

<div align="center">

**AI 爆款文章创作器**

基于多智能体协作，自动完成热点监控、选题、大纲、正文、配图到一键全平台发布的全流程图文创作

![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![Vue](https://img.shields.io/badge/Vue-3.5-4FC08D?style=flat-square&logo=vuedotjs&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-Compatible-412991?style=flat-square&logo=openai&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)

</div>

## 🏗 项目简介

AI 爆款文章创作器是一个基于 **FastAPI + OpenAI SDK** 构建的智能图文创作与分发平台，通过 **5 个智能体协作** 完成从选题到图文文章的全自动创作，每个阶段都支持用户介入；同时内置热点监控与发布中心，帮助创作者从热点发现、选题生成、文章创作到多平台草稿同步形成闭环。

```
阶段0: 热点监控 / 热点搜索 → AI 分析热点 → 生成选题建议
阶段1: 选题 → 生成 3-5 个标题方案 → 用户选择
阶段2: 标题 → 生成大纲 → 用户编辑 / AI 优化大纲
阶段3: 大纲 → 生成正文 → 分析配图需求 → 生成配图 → 图文合成
阶段4: 完成文章 → 发布中心 → 一键同步到多平台草稿箱
```

## 🎯 核心价值

| 特性 | 说明 | 价值 |
|------|------|------|
| 🤖 多智能体协作 | 5 个 Agent 分工协作，Pipeline 编排 | 专业分工，质量更高 |
| 🎨 多元配图 | 6 种配图策略 + 自动降级 | 图文并茂，永不中断 |
| 📡 实时流式输出 | SSE 推送大纲/正文创作过程 | 所见即所得 |
| 🔥 热点监控 | 关键词持续监控 + WebSocket 通知 | 第一时间捕捉创作机会 |
| 🧑‍💻 人机协作 | 三阶段创作，每步可介入 | 创作可控 |
| 🚀 一键发布 | 对接 Wechatsync，同步多平台草稿 | 分发效率更高 |
| 💎 VIP 会员体系 | Stripe 支付 + 配额管理 | 商业化就绪 |
| 🐳 Docker 一键部署 | docker compose up 即可运行 | 5 分钟上手 |

## ✨ 功能特性

### 智能体协作

| 智能体 | 功能 | 说明 |
|--------|------|------|
| Agent 1 | 标题生成 | 根据选题生成 3-5 个标题方案供用户选择 |
| Agent 2 | 大纲生成 | 根据标题生成文章大纲（流式输出） |
| Agent 3 | 正文生成 | 根据大纲生成 Markdown 正文（流式输出） |
| Agent 4 | 配图分析 | 分析正文内容，生成配图需求 |
| Agent 5 | 配图生成 | 获取图片并上传到 COS |
| 合成 | 合并图文 | 将配图插入正文生成完整图文 |

### 配图方式（策略模式）

系统采用策略模式实现多种配图方式，支持灵活扩展：

| 方式 | 说明 | 数据来源 | 权限 |
|------|------|---------|------|
| Pexels | 高质量图库检索 | 关键词检索 | 全部用户 |
| Mermaid | 流程图/架构图生成 | AI Prompt 生成 | 全部用户 |
| Iconify | 图标库检索 | 关键词检索 | 全部用户 |
| 表情包 | Bing 图片搜索 | 关键词检索 | 全部用户 |
| Nano Banana | Gemini AI 生图 | AI Prompt 生成 | VIP |
| SVG Diagram | AI 概念示意图 | AI Prompt 生成 | VIP |
| Picsum | 随机图片 | 降级方案 | 自动触发 |

> 当主配图方式失败时，系统会自动降级到 Picsum 随机图片，确保文章生成不中断。

### 文章风格

- 🔬 科技风格 - 专业严谨
- 💝 情感风格 - 温暖感人  
- 📚 教育风格 - 通俗易懂
- 😄 轻松幽默 - 诙谐有趣

### 热点监控与选题

选题页升级为 4 个 Tab，支持“持续监控 + 即时搜索 + AI 选题生成”两种热点工作流：

| 模块 | 功能 | 说明 |
|------|------|------|
| 关键词 | 添加、删除、启停监控词，可设置分类 | 每个用户维护自己的监控关键词 |
| 监控热点 | 查看系统持续扫描后沉淀的热点记录 | 支持统计卡片、筛选、排序、分页和批量勾选 |
| 搜索 | 按需扫描指定关键词 | 支持微博、B站、搜狗、Bing、Hacker News、Twitter/X、DuckDuckGo |
| 生成选题 | 基于已选热点生成文章选题建议 | 输出选题、内容描述、切入角度、爆点理由、适合平台和参考热点 |

热点监控能力：

- ⏱ 后端启动后通过 APScheduler 每 30 分钟扫描一次所有激活关键词
- 🔍 支持手动点击“立即扫描”，无需等待下一轮定时任务
- 🧠 对热点进行相关性、重要程度、热度、真实性和摘要分析
- 🔔 新热点写入数据库后通过 WebSocket 实时广播，并在顶部导航通知铃铛展示未读数
- 🧾 热点记录支持按来源、重要程度、关键词、时间范围、真实性过滤，并支持按发现时间、发布时间、重要程度、相关性和热度排序

### 一键全平台发布

发布中心支持将已完成文章同步到多个内容平台草稿箱，发布前仍可在目标平台做最终检查和调整。

### 上下文增强 Agent 创作

系统为 5 个创作 Agent 提供三层上下文注入，使生成内容更贴合用户偏好：

| 上下文层 | 来源 | 说明 |
|--------|------|------|
| 长期记忆 | 用户手动创建/系统自动提炼 | 写作风格、平台偏好、话题倾向、配图风格等个性化记忆 |
| 写作 Skills | Markdown 技能文件 | 可按平台/文体启用的结构化写作规则（科技自媒体、小红书种草等） |
| 知识库 RAG | 用户上传文档/历史文章/热点记录 | Hybrid Search 检索（向量 + BM25 + RRF 融合）后按相关度排序注入 |

每次创作时系统自动构建并保存 `agent_context_snapshot`，记录各阶段注入的 Token 量，方便追踪上下文消耗。知识库管理入口在顶部导航「知识库」页，支持 PDF / Markdown / TXT 文件上传和 RAG 查询测试。

| 能力 | 说明 |
|------|------|
| 文章选择 | 仅展示已完成文章，支持按标题或选题搜索 |
| 内容预览 | 自动带入标题、封面、标签和 Markdown 正文，发布前可编辑 |
| 平台检测 | 通过 Wechatsync Chrome 扩展查询当前浏览器已登录平台 |
| 批量同步 | 勾选多个已登录平台后一键同步到草稿箱 |
| 状态追踪 | 展示同步中、草稿已创建、失败等状态，并保存草稿链接和错误信息 |
| 历史记录 | 同一篇文章再次进入发布中心时自动加载上次同步记录 |

当前预置平台包括：微信公众号、知乎、微博、小红书、掘金、CSDN、简书、今日头条、抖音图文、B站专栏、百家号、语雀、豆瓣、搜狐号、雪球、人人都是产品经理、大鱼号、一点号、51CTO、慕课手记、开源中国、思否、博客园、搜狐焦点、Twitter/X、东方财富、什么值得买、网易号、WordPress、Typecho、Markdown 压缩包。

> 发布中心依赖浏览器侧的 Wechatsync Chrome 扩展能力。需要先安装并启用扩展，在浏览器中登录目标平台账号，再点击“刷新”查询平台登录状态。

### SSE 实时通信

基于 Server-Sent Events 实现实时进度推送：

| 消息类型 | 说明 |
|---------|------|
| `AGENT1_COMPLETE` | 标题方案生成完成 |
| `AGENT2_STREAMING` | 大纲流式输出中 |
| `AGENT2_COMPLETE` | 大纲生成完成 |
| `AGENT3_STREAMING` | 正文流式输出中 |
| `AGENT3_COMPLETE` | 正文生成完成 |
| `AGENT4_COMPLETE` | 配图需求分析完成 |
| `IMAGE_COMPLETE` | 单张配图生成完成 |
| `AGENT5_COMPLETE` | 所有配图生成完成 |
| `MERGE_COMPLETE` | 图文合成完成 |
| `ERROR` | 错误通知 |

### WebSocket 热点通知

热点监控使用 WebSocket 推送新热点事件：

| 事件类型 | 说明 |
|---------|------|
| `hotspot_new` | 发现新热点，包含重要程度、标题、来源和关键词 |
| `pong` | 心跳响应 |

前端会自动重连并每 30 秒发送心跳，收到新热点后刷新监控列表、统计数据和通知铃铛。

### 其他特性

- ✅ 文章管理（列表、详情、删除）
- ✅ Markdown 导出
- ✅ 热点关键词管理与热点记录沉淀
- ✅ 一键同步多平台草稿箱
- ✅ VIP 会员体系（Stripe 支付）
- ✅ 智能体执行日志追踪
- ✅ 管理后台统计分析

## 🛠 技术栈

### 后端

| 技术 | 版本 | 说明 |
|------|------|------|
| FastAPI | 0.115.0 | Web 框架 |
| Python | 3.10+ | 编程语言 |
| OpenAI SDK | 1.58.1 | 大模型调用（兼容通义千问） |
| SQLAlchemy | 2.0.36 | ORM 框架 |
| MySQL | 8.0 | 数据存储 |
| Redis | 5.2.0 | 缓存 / 会话管理 |
| APScheduler | >=3.10 | 热点监控定时调度 |
| httpx + BeautifulSoup | 0.28.1 / 4.12.3 | 多来源热点抓取 |
| Stripe | >=14.3.0 | 支付集成 |
| 腾讯云 COS SDK | 1.9.32 | 对象存储 |
| Google Gen AI SDK | 1.75.0 | Gemini AI 生图 |
| Uvicorn | 0.32.0 | ASGI 服务器 |

### 前端

| 技术 | 版本 | 说明 |
|------|------|------|
| Vue | 3.5 | 前端框架 |
| TypeScript | 5.8 | 类型安全 |
| Ant Design Vue | 4.2 | UI 组件库 |
| Vite | 7.0 | 构建工具 |
| Pinia | 3.0 | 状态管理 |
| Vue Router | 4.5 | 路由管理 |
| ECharts | 6.0 | 数据可视化 |
| Axios | 1.11 | HTTP 客户端 |

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- MySQL 8.0+
- Redis 7.x

### 1. 数据库初始化

```bash
mysql -uroot -p < sql/create_table.sql

# 补充新增功能所需表；脚本使用 IF NOT EXISTS，可重复执行
mysql -uroot -p < sql/add_hotspot_monitoring.sql
mysql -uroot -p < sql/add_article_sync_record.sql
```

### 2. 配置环境变量

```bash
cd backend
cp .env.example .env
```

编辑 `.env` 文件：

```env
# 必填
DASHSCOPE_API_KEY=your-dashscope-api-key
PEXELS_API_KEY=your-pexels-api-key

# 可选
STRIPE_API_KEY=sk_test_xxx
TENCENT_COS_SECRET_ID=xxx
TENCENT_COS_SECRET_KEY=xxx
```

### 3. 启动后端

```bash
cd backend

# 使用 uv（推荐）
uv sync
uv run uvicorn app.main:app --reload --port 8567

# 或使用 pip
pip install -e .
uvicorn app.main:app --reload --port 8567
```

接口文档：http://localhost:8567/docs

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端页面：http://localhost:5173

## 🐳 Docker 一键部署（推荐）

### 前置条件

- Docker 20.10+
- Docker Compose v2+

### 快速启动

```bash
# 1. 复制环境变量配置文件
cd backend
cp .env.example .env

# 2. 编辑 .env 文件，填写必需的 API Key
# 必须配置：DASHSCOPE_API_KEY 和 PEXELS_API_KEY
vim .env

# 3. 一键启动所有服务
docker compose up -d --build

# 4. 首次启动后补充新增功能所需表（可重复执行）
docker compose exec -T mysql mysql -uroot -p你的MySQL密码 ai_passage_creator < ../sql/add_hotspot_monitoring.sql
docker compose exec -T mysql mysql -uroot -p你的MySQL密码 ai_passage_creator < ../sql/add_article_sync_record.sql
```

### 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端 | 80 | 访问地址：http://localhost |
| 后端 | 8123 | API 接口：http://localhost:8123 |
| 接口文档 | 8123 | http://localhost:8123/docs |
| MySQL | 不暴露 | 仅内部网络访问（可选暴露到 13306） |
| Redis | 不暴露 | 仅内部网络访问（可选暴露到 16379） |

> **安全说明**：MySQL 和 Redis 默认不暴露端口到宿主机，仅通过 Docker 内部网络访问。如需从宿主机连接数据库进行调试，可在 `backend/docker-compose.yml` 中取消相应 `ports` 注释。

### 常用命令

```bash
# 查看服务状态
docker compose ps

# 查看服务日志
docker compose logs -f backend    # 后端日志
docker compose logs -f frontend   # 前端日志
docker compose logs -f mysql      # 数据库日志

# 重启单个服务
docker compose restart backend

# 停止所有服务
docker compose down

# 停止并删除数据卷（清空数据）
docker compose down -v
```

### 环境变量说明

| 变量名 | 必需 | 默认值 | 说明 |
|--------|------|--------|------|
| DASHSCOPE_API_KEY | ✅ | - | 通义千问 API Key |
| PEXELS_API_KEY | ✅ | - | Pexels 图片 API Key |
| MYSQL_ROOT_PASSWORD | - | 123456 | MySQL root 密码 |
| MYSQL_DATABASE | - | ai_passage_creator | 数据库名 |
| BACKEND_PORT | - | 8123 | 后端端口 |
| FRONTEND_PORT | - | 80 | 前端端口 |
| NANO_BANANA_API_KEY | - | - | AI 生图（VIP功能） |
| STRIPE_API_KEY | - | - | Stripe 支付（VIP功能） |

详见 `.env.example` 文件获取完整配置说明。

## 📁 项目结构

```
├── backend/                         # Python 后端
│   ├── app/
│   │   ├── agent/                   # 智能体模块
│   │   │   ├── agents/              # 各智能体实现
│   │   │   │   ├── title_generator.py
│   │   │   │   ├── outline_generator.py
│   │   │   │   ├── content_generator.py
│   │   │   │   ├── image_analyzer.py
│   │   │   │   └── content_merger.py
│   │   │   ├── parallel/            # 并行配图生成
│   │   │   ├── context/             # 流式处理上下文
│   │   │   └── orchestrator.py      # 多智能体编排器
│   │   ├── routers/                 # API 路由（FastAPI）
│   │   │   ├── hotspot_monitor.py   # 热点监控 / 关键词 / 通知 / WebSocket
│   │   │   └── article_sync.py      # 文章草稿同步记录
│   │   ├── services/                # 业务服务
│   │   │   ├── article_agent_service.py
│   │   │   ├── hotspot_monitor_service.py
│   │   │   ├── hotspot_record_service.py
│   │   │   ├── hotspot_keyword_service.py
│   │   │   ├── hotspot_sources.py
│   │   │   ├── article_sync_record_service.py
│   │   │   ├── image_service_strategy.py
│   │   │   ├── cos_service.py
│   │   │   ├── pexels_service.py
│   │   │   ├── nano_banana_service.py
│   │   │   ├── mermaid_service.py
│   │   │   ├── iconify_service.py
│   │   │   ├── emoji_pack_service.py
│   │   │   └── svg_diagram_service.py
│   │   ├── models/                  # 数据库模型（SQLAlchemy）
│   │   ├── schemas/                 # 请求/响应 Schema（Pydantic）
│   │   ├── managers/                # 管理器（SSE、热点 WebSocket 等）
│   │   ├── constants/               # 常量（Prompt、枚举）
│   │   ├── config.py                # 配置（pydantic-settings）
│   │   ├── database.py              # 数据库连接
│   │   └── main.py                  # FastAPI 应用入口
│   ├── pyproject.toml               # 依赖管理（uv）
│   └── Dockerfile
├── frontend/                        # 前端项目
│   ├── src/
│   │   ├── pages/                   # 页面组件
│   │   │   ├── topic/               # 热点关键词与监控热点 Tab
│   │   │   └── PublishPage.vue      # 发布中心
│   │   ├── components/              # 公共组件
│   │   ├── api/                     # API 接口
│   │   ├── composables/             # WebSocket 等组合式逻辑
│   │   ├── utils/                   # Wechatsync、Markdown、发布状态等工具
│   │   └── stores/                  # 状态管理
│   └── package.json
├── sql/                             # 数据库脚本
│   ├── create_table.sql             # 建表语句
│   ├── init_database.sql            # 初始化数据
│   └── ...                          # 增量更新脚本
└── backend/docker-compose.yml        # Docker 编排
```

## 🗄 数据库设计

### 核心表

| 表名 | 说明 |
|------|------|
| user | 用户表（含 VIP 时间、配额） |
| article | 文章表（含状态、阶段、配图方式限制） |
| agent_log | 智能体执行日志 |
| payment_record | 支付记录 |
| hotspot_keyword | 热点监控关键词 |
| hotspot_record | 热点记录 |
| hotspot_notification | 热点站内通知 |
| article_sync_record | 文章草稿同步记录 |

### 文章表关键字段

```sql
task_id              -- 任务ID（UUID）
phase                -- 当前阶段：TITLE_SELECTION/OUTLINE_EDITING/CONTENT_GENERATION/COMPLETED
style                -- 文章风格
title_options        -- 标题方案列表（JSON）
enabled_image_methods -- 允许的配图方式（JSON 数组）
```

### 热点监控表关键字段

```sql
hotspot_keyword.text       -- 监控关键词
hotspot_keyword.category   -- 关键词分类
hotspot_keyword.isActive   -- 是否启用监控
hotspot_record.source      -- 热点来源
hotspot_record.importance  -- 重要程度：low/medium/high/urgent
hotspot_record.relevance   -- AI 相关性评分
hotspot_record.heatScore   -- 综合热度分
hotspot_record.summary     -- AI 摘要
hotspot_notification.isRead -- 通知是否已读
```

### 草稿同步表关键字段

```sql
taskId       -- 文章任务 ID
platform     -- 平台 ID
platformName -- 平台名称
status       -- SYNCING/DRAFT_CREATED/FAILED
draftLink    -- 草稿链接
errorMessage -- 同步失败原因
```

## 🔌 主要 API

### 热点监控

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/hotspot/keywords` | 获取当前用户监控关键词 |
| POST | `/api/hotspot/keywords` | 新增监控关键词 |
| PATCH | `/api/hotspot/keywords/{keyword_id}/toggle` | 启停关键词 |
| DELETE | `/api/hotspot/keywords/{keyword_id}` | 删除关键词 |
| GET | `/api/hotspot/records` | 查询热点记录，支持筛选、排序、分页 |
| GET | `/api/hotspot/records/stats` | 获取热点统计 |
| GET | `/api/hotspot/notifications` | 查询热点通知 |
| PATCH | `/api/hotspot/notifications/read-all` | 全部通知标为已读 |
| POST | `/api/hotspot/monitor/trigger` | 立即触发一次后台扫描 |
| GET | `/api/hotspot/monitor/status` | 获取监控状态 |
| WS | `/api/hotspot/ws` | 新热点实时通知 |

### 草稿同步记录

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/article-sync/records/{task_id}` | 获取某篇文章的草稿同步记录 |
| POST | `/api/article-sync/record` | 创建或更新平台草稿同步状态 |

## 🔑 API Key 获取

| 服务 | 获取地址 | 说明 |
|------|---------|------|
| 通义千问 | https://bailian.console.aliyun.com | 必需 |
| Pexels | https://www.pexels.com/api/ | 必需 |
| Stripe | https://dashboard.stripe.com | 支付功能 |
| 腾讯云 COS | https://console.cloud.tencent.com | 图片上传 |
| Nano Banana | - | Gemini AI 生图（VIP 功能） |

## 🧪 测试账号

| 账号 | 密码 | 角色 |
|------|------|------|
| admin | 12345678 | 管理员 |
| user | 12345678 | 普通用户 |
| test | 12345678 | 测试账号 |

## 🏛 架构特点

### 多智能体编排

采用自定义 Pipeline 编排器，按阶段顺序调度各智能体：

```python
class ArticleAgentOrchestrator:
    async def execute_phase3(self, service, state, stream_handler):
        # 正文生成 → 配图分析 → 并行配图生成 → 图文合成
        await self.content_agent.run(service, state, stream_handler)
        await self.image_analyzer_agent.run(service, state, stream_handler)
        await parallel_image_generator.run(service, state, stream_handler)
        await self.content_merger_agent.run(service, state, stream_handler)
```

### 配图策略模式

支持 6 种配图方式，通过策略模式实现灵活扩展：

```python
class ImageMethodEnum(str, Enum):
    PEXELS = "PEXELS"           # Pexels 图库
    NANO_BANANA = "NANO_BANANA" # AI 生图（VIP）
    MERMAID = "MERMAID"         # 流程图
    ICONIFY = "ICONIFY"         # 图标库
    EMOJI_PACK = "EMOJI_PACK"   # 表情包
    SVG_DIAGRAM = "SVG_DIAGRAM" # 示意图（VIP）
```

### 流式输出

基于 SSE（Server-Sent Events）+ FastAPI `StreamingResponse` 实现实时进度推送：

- 大纲生成流式输出
- 正文创作流式输出
- 配图生成实时通知
- 阶段状态实时更新

### 热点监控调度

后端应用生命周期启动时创建 APScheduler 任务，每 30 分钟执行一次 `monitor_service.scan_all_keywords`：

```python
scheduler.add_job(
    monitor_service.scan_all_keywords,
    "interval",
    minutes=30,
    id="hotspot_scan",
    max_instances=1,
)
```

扫描流程：

```
读取激活关键词 → 多来源抓取热点 → AI 分析相关性/重要程度/摘要 → 去重入库 → 创建站内通知 → WebSocket 广播
```

### 发布中心集成

发布中心通过浏览器注入的 Wechatsync 扩展 API 完成平台检测与草稿同步：

```ts
window.$syncer.getAccounts(callback) // 查询已登录平台
window.$syncer.addTask(task, statusHandler, callback) // 同步文章到草稿箱
```

前端会将 Markdown 转为 HTML 后提交给扩展，并把每个平台的同步状态写入后端，便于后续追踪。
