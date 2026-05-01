# AI 爆款文章创作器 ✍️

<div align="center">

**AI 爆款文章创作器**

基于多智能体协作，自动完成从选题、大纲、正文到配图的全流程图文创作

![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![Vue](https://img.shields.io/badge/Vue-3.5-4FC08D?style=flat-square&logo=vuedotjs&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-Compatible-412991?style=flat-square&logo=openai&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)

</div>

## 🏗 项目简介

AI 爆款文章创作器是一个基于 **FastAPI + OpenAI SDK** 构建的智能图文创作平台，通过 **5 个智能体协作** 完成从选题到图文文章的全自动创作，每个阶段都支持用户介入，实现人机协作的创作体验。

```
阶段1: 选题 → 生成 3-5 个标题方案 → 用户选择
阶段2: 标题 → 生成大纲 → 用户编辑 / AI 优化大纲
阶段3: 大纲 → 生成正文 → 分析配图需求 → 生成配图 → 图文合成
```

## 🎯 核心价值

| 特性 | 说明 | 价值 |
|------|------|------|
| 🤖 多智能体协作 | 5 个 Agent 分工协作，Pipeline 编排 | 专业分工，质量更高 |
| 🎨 多元配图 | 6 种配图策略 + 自动降级 | 图文并茂，永不中断 |
| 📡 实时流式输出 | SSE 推送大纲/正文创作过程 | 所见即所得 |
| 🧑‍💻 人机协作 | 三阶段创作，每步可介入 | 创作可控 |
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

### 其他特性

- ✅ 文章管理（列表、详情、删除）
- ✅ Markdown 导出
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
| Stripe | >=14.3.0 | 支付集成 |
| 腾讯云 COS SDK | 1.9.32 | 对象存储 |
| Google Gen AI SDK | 1.35.0 | Gemini AI 生图 |
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
```

### 2. 配置环境变量

```bash
cd python-backend
cp .env.example .env
```

编辑 `.env` 文件：

```env
# 必填
DASHSCOPE_API_KEY=your-dashscope-api-key
PEXELS_API_KEY=your-pexels-api-key

# 可选
STRIPE_API_KEY=sk_test_xxx
COS_SECRET_ID=xxx
COS_SECRET_KEY=xxx
```

### 3. 启动后端

```bash
cd python-backend

# 使用 uv（推荐）
uv sync
uv run uvicorn app.main:app --reload --port 8123

# 或使用 pip
pip install -e .
uvicorn app.main:app --reload --port 8123
```

接口文档：http://localhost:8123/docs

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
cp .env.example .env

# 2. 编辑 .env 文件，填写必需的 API Key
# 必须配置：DASHSCOPE_API_KEY 和 PEXELS_API_KEY
vim .env

# 3. 一键启动所有服务
docker compose up -d --build

# 或使用启动脚本（自动检查环境）
./start.sh
```

### 国内网络使用（镜像加速）

如果遇到 Docker 镜像拉取失败，使用国内镜像版本：

```bash
docker compose -f docker-compose.china.yml up -d --build
```

### 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端 | 80 | 访问地址：http://localhost |
| 后端 | 8123 | API 接口：http://localhost:8123 |
| 接口文档 | 8123 | http://localhost:8123/docs |
| MySQL | 不暴露 | 仅内部网络访问（可选暴露到 13306） |
| Redis | 不暴露 | 仅内部网络访问（可选暴露到 16379） |

> **安全说明**：MySQL 和 Redis 默认不暴露端口到宿主机，仅通过 Docker 内部网络访问。如需从宿主机连接数据库进行调试，可在 `docker-compose.yml` 中取消相应 `ports` 注释。

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
├── python-backend/                  # Python 后端
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
│   │   ├── services/                # 业务服务
│   │   │   ├── article_agent_service.py
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
│   │   ├── managers/                # 管理器（SSE 等）
│   │   ├── constants/               # 常量（Prompt、枚举）
│   │   ├── config.py                # 配置（pydantic-settings）
│   │   ├── database.py              # 数据库连接
│   │   └── main.py                  # FastAPI 应用入口
│   ├── pyproject.toml               # 依赖管理（uv）
│   └── Dockerfile
├── frontend/                        # 前端项目
│   ├── src/
│   │   ├── pages/                   # 页面组件
│   │   ├── components/              # 公共组件
│   │   ├── api/                     # API 接口
│   │   └── stores/                  # 状态管理
│   └── package.json
├── sql/                             # 数据库脚本
│   ├── create_table.sql             # 建表语句
│   ├── init_database.sql            # 初始化数据
│   └── ...                          # 增量更新脚本
├── docker-compose.yml               # Docker 编排
└── start.sh                         # 启动脚本
```

## 🗄 数据库设计

### 核心表

| 表名 | 说明 |
|------|------|
| user | 用户表（含 VIP 时间、配额） |
| article | 文章表（含状态、阶段、配图方式限制） |
| agent_log | 智能体执行日志 |
| payment_record | 支付记录 |

### 文章表关键字段

```sql
task_id              -- 任务ID（UUID）
phase                -- 当前阶段：TITLE_SELECTION/OUTLINE_EDITING/CONTENT_GENERATION/COMPLETED
style                -- 文章风格
title_options        -- 标题方案列表（JSON）
enabled_image_methods -- 允许的配图方式（JSON 数组）
```

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


