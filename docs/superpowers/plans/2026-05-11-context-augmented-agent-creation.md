# Context-Augmented Agent Creation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Memory, Writing Skills, and an internal RAG Kernel to the existing 5-Agent article creation flow so each Agent receives stage-specific context.

**Architecture:** Keep the current article pipeline intact and add a context layer around it. Main app services own user permissions, metadata, and prompt injection; `backend/app/rag` owns document ingestion and retrieval mechanics adapted from `plugin/MODULAR-RAG-MCP-SERVER`.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy models, `databases`, MySQL, Vue 3, TypeScript, Ant Design Vue, Chroma/BM25/RAG code adapted from the local Modular RAG project.

---

## File Structure

### Database and Models

- Create `sql/add_agent_context.sql`: adds new tables and article context columns.
- Create `backend/app/models/user_memory.py`: SQLAlchemy model for memory metadata.
- Create `backend/app/models/knowledge_document.py`: SQLAlchemy model for knowledge document metadata.
- Create `backend/app/models/agent_context_snapshot.py`: SQLAlchemy model for injected context snapshots.
- Modify `backend/app/models/article.py`: add context settings columns.

### Schemas

- Create `backend/app/schemas/memory.py`: request/response models for memory CRUD.
- Create `backend/app/schemas/writing_skill.py`: response models for Markdown-backed Skills.
- Create `backend/app/schemas/knowledge.py`: upload/query/document models.
- Create `backend/app/schemas/agent_context.py`: internal `AgentContext` and snapshot VO.
- Modify `backend/app/schemas/article.py`: add article create context flags and state fields.

### Services

- Create `backend/app/services/memory_service.py`: memory CRUD and stage filtering.
- Create `backend/app/services/writing_skill_service.py`: Markdown Skill loading, parsing, and stage filtering.
- Create `backend/app/services/rag_knowledge_service.py`: business wrapper around RAG ingestion/query.
- Create `backend/app/services/agent_context_builder.py`: builds stage-specific prompt context and snapshots.
- Modify `backend/app/services/article_service.py`: persist article context flags and surface them in state.
- Modify `backend/app/services/article_agent_service.py`: inject context into Agent prompts.
- Modify `backend/app/services/article_async_service.py`: load context flags into `ArticleState`.

### RAG Kernel

- Create `backend/app/rag/`: internal RAG Kernel package.
- Copy/adapt required modules from `plugin/MODULAR-RAG-MCP-SERVER/src`:
  - `core/types.py`
  - `core/settings.py`
  - `core/response/*`
  - `core/query_engine/*`
  - `core/trace/*`
  - `ingestion/*`
  - `libs/embedding/*`
  - `libs/vector_store/*`
  - `libs/splitter/*`
  - `libs/loader/*`
  - `libs/reranker/*`
  - `observability/logger.py`
- Create `backend/app/rag/config.py`: builds RAG settings from main app settings.
- Create `backend/app/rag/kernel.py`: stable facade for `ingest_file()` and `query()`.

### Routers

- Create `backend/app/routers/memory.py`.
- Create `backend/app/routers/writing_skill.py` for listing Markdown Skills.
- Create `backend/app/routers/knowledge.py`.
- Modify `backend/app/routers/article.py`: accept context options.
- Modify `backend/app/routers/__init__.py` and `backend/app/main.py`: register routers.

### Frontend

- Create `frontend/src/api/memoryController.ts`.
- Create `frontend/src/api/writingSkillController.ts` for listing available Skills.
- Create `frontend/src/api/knowledgeController.ts`.
- Create `frontend/src/pages/KnowledgePage.vue`.
- Modify `frontend/src/router/index.ts`: add `/knowledge`.
- Modify `frontend/src/components/GlobalHeader.vue`: add nav item.
- Modify `frontend/src/pages/article/ArticleCreatePage.vue`: add context enhancement controls.
- Modify `frontend/src/pages/article/ArticleListPage.vue` and/or `ArticleDetailPage.vue`: add ingest completed article action.
- Modify `frontend/src/pages/topic/MonitorTab.vue`: add ingest selected hotspots action.
- Modify `frontend/src/api/articleController.ts` and `frontend/src/api/typings.d.ts`: add context request fields if generated typings are not regenerated.

### Tests

- Create backend tests:
  - `backend/app/tests/test_memory_service.py`
  - `backend/app/tests/test_writing_skill_service.py`
  - `backend/app/tests/test_agent_context_builder.py`
  - `backend/app/tests/test_rag_knowledge_service.py`
  - `backend/app/tests/test_article_context_options.py`
- Create frontend tests:
  - `frontend/tests/knowledgePageState.test.mjs`
  - `frontend/tests/articleContextOptions.test.mjs`

---

## Task 1: Database Schema and Article Context Columns

**Files:**
- Create: `sql/add_agent_context.sql`
- Modify: `backend/app/models/article.py`
- Create: `backend/app/models/user_memory.py`
- Create: `backend/app/models/knowledge_document.py`
- Create: `backend/app/models/agent_context_snapshot.py`

- [ ] **Step 1: Write SQL migration**

Create `sql/add_agent_context.sql`:

```sql
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

USE ai_passage_creator;

CREATE TABLE IF NOT EXISTS user_memory (
    id bigint auto_increment primary key,
    userId bigint not null comment '用户ID',
    memoryType varchar(32) not null comment 'style/platform/topic/constraint/visual',
    title varchar(200) not null comment '记忆标题',
    content text not null comment '记忆内容',
    weight int default 50 not null comment '权重 0-100',
    source varchar(32) default 'manual' not null comment 'manual/article/system',
    isActive tinyint default 1 not null comment '是否启用',
    createTime datetime default CURRENT_TIMESTAMP not null,
    updateTime datetime default CURRENT_TIMESTAMP not null on update CURRENT_TIMESTAMP,
    isDelete tinyint default 0 not null,
    index idx_user_active (userId, isActive),
    index idx_user_type (userId, memoryType)
) comment '用户长期记忆' collate = utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS knowledge_document (
    id bigint auto_increment primary key,
    userId bigint not null comment '用户ID',
    title varchar(255) not null comment '文档标题',
    sourceType varchar(32) not null comment 'upload/article/hotspot/system',
    sourceId varchar(64) null comment '来源ID',
    collectionName varchar(128) not null comment 'RAG collection',
    filePath varchar(1024) null comment '源文件路径',
    status varchar(32) not null comment 'pending/processing/ready/failed',
    chunkCount int default 0 not null comment 'chunk数量',
    errorMessage text null comment '错误信息',
    createTime datetime default CURRENT_TIMESTAMP not null,
    updateTime datetime default CURRENT_TIMESTAMP not null on update CURRENT_TIMESTAMP,
    isDelete tinyint default 0 not null,
    index idx_user_status (userId, status),
    index idx_user_source (userId, sourceType, sourceId),
    index idx_collection (collectionName)
) comment '知识库文档元数据' collate = utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS agent_context_snapshot (
    id bigint auto_increment primary key,
    taskId varchar(64) not null comment '文章任务ID',
    userId bigint not null comment '用户ID',
    stage varchar(32) not null comment 'title/outline/content/image',
    memoryContext mediumtext null,
    skillContext mediumtext null,
    ragContext mediumtext null,
    hotspotContext mediumtext null,
    articleExampleContext mediumtext null,
    tokenEstimate int default 0 not null,
    createTime datetime default CURRENT_TIMESTAMP not null,
    index idx_task_stage (taskId, stage),
    index idx_user_time (userId, createTime)
) comment 'Agent上下文快照' collate = utf8mb4_unicode_ci;

ALTER TABLE article
    ADD COLUMN enableMemory tinyint default 1 not null comment '是否启用长期记忆',
    ADD COLUMN enableRag tinyint default 1 not null comment '是否启用RAG',
    ADD COLUMN enabledSkillRefs json null comment '启用的写作Skill引用列表',
    ADD COLUMN ragCollections json null comment '启用的RAG集合';
```

- [ ] **Step 2: Write model definitions**

Create `backend/app/models/user_memory.py`:

```python
"""User memory ORM model."""

from sqlalchemy import BigInteger, Column, DateTime, Integer, SmallInteger, String, Text
from sqlalchemy.sql import func

from app.database import Base


class UserMemory(Base):
    __tablename__ = "user_memory"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column("userId", BigInteger, nullable=False)
    memory_type = Column("memoryType", String(32), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    weight = Column(Integer, nullable=False, default=50)
    source = Column(String(32), nullable=False, default="manual")
    is_active = Column("isActive", SmallInteger, nullable=False, default=1)
    create_time = Column("createTime", DateTime, nullable=False, default=func.now())
    update_time = Column("updateTime", DateTime, nullable=False, default=func.now(), onupdate=func.now())
    is_delete = Column("isDelete", SmallInteger, nullable=False, default=0)
```

Create matching models for the other tables using the SQL column names:

```python
# backend/app/models/knowledge_document.py
class KnowledgeDocument(Base):
    __tablename__ = "knowledge_document"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column("userId", BigInteger, nullable=False)
    title = Column(String(255), nullable=False)
    source_type = Column("sourceType", String(32), nullable=False)
    source_id = Column("sourceId", String(64), nullable=True)
    collection_name = Column("collectionName", String(128), nullable=False)
    file_path = Column("filePath", String(1024), nullable=True)
    status = Column(String(32), nullable=False)
    chunk_count = Column("chunkCount", Integer, nullable=False, default=0)
    error_message = Column("errorMessage", Text, nullable=True)
    create_time = Column("createTime", DateTime, nullable=False, default=func.now())
    update_time = Column("updateTime", DateTime, nullable=False, default=func.now(), onupdate=func.now())
    is_delete = Column("isDelete", SmallInteger, nullable=False, default=0)
```

```python
# backend/app/models/agent_context_snapshot.py
class AgentContextSnapshot(Base):
    __tablename__ = "agent_context_snapshot"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column("taskId", String(64), nullable=False)
    user_id = Column("userId", BigInteger, nullable=False)
    stage = Column(String(32), nullable=False)
    memory_context = Column("memoryContext", Text, nullable=True)
    skill_context = Column("skillContext", Text, nullable=True)
    rag_context = Column("ragContext", Text, nullable=True)
    hotspot_context = Column("hotspotContext", Text, nullable=True)
    article_example_context = Column("articleExampleContext", Text, nullable=True)
    token_estimate = Column("tokenEstimate", Integer, nullable=False, default=0)
    create_time = Column("createTime", DateTime, nullable=False, default=func.now())
```

- [ ] **Step 3: Modify Article model**

In `backend/app/models/article.py`, add:

```python
enable_memory = Column("enableMemory", SmallInteger, nullable=False, default=1, comment="是否启用长期记忆")
enable_rag = Column("enableRag", SmallInteger, nullable=False, default=1, comment="是否启用RAG")
enabled_skill_refs = Column("enabledSkillRefs", Text, nullable=True, comment="启用的写作Skill引用列表")
rag_collections = Column("ragCollections", Text, nullable=True, comment="启用的RAG集合")
```

- [ ] **Step 4: Verify syntax**

Run:

```bash
python -m py_compile backend/app/models/article.py backend/app/models/user_memory.py backend/app/models/knowledge_document.py backend/app/models/agent_context_snapshot.py
```

Expected: exit code 0.

- [ ] **Step 5: Commit**

```bash
git add sql/add_agent_context.sql backend/app/models/article.py backend/app/models/user_memory.py backend/app/models/knowledge_document.py backend/app/models/agent_context_snapshot.py
git commit -m "feat: add agent context schema"
```

---

## Task 2: Memory Service and Markdown Writing Skills

**Files:**
- Create: `backend/app/schemas/memory.py`
- Create: `backend/app/schemas/writing_skill.py`
- Create: `backend/app/services/memory_service.py`
- Create: `backend/app/services/writing_skill_service.py`
- Create: `backend/app/routers/memory.py`
- Create: `backend/app/routers/writing_skill.py`
- Modify: `backend/app/main.py`
- Test: `backend/app/tests/test_memory_service.py`
- Test: `backend/app/tests/test_writing_skill_service.py`

- [ ] **Step 1: Write failing MemoryService tests**

Create `backend/app/tests/test_memory_service.py`:

```python
import asyncio
from datetime import datetime

from app.schemas.memory import MemoryCreateRequest
from app.schemas.user import LoginUserVO
from app.services.memory_service import MemoryService


def make_user():
    return LoginUserVO(id=1, userAccount="u", userRole="user", userName="u", createTime="", updateTime="")


class FakeDb:
    def __init__(self):
        self.rows = []
        self.executed = []

    async def execute(self, query, values=None):
        self.executed.append((str(query), values))
        return 7

    async def fetch_all(self, query, values=None):
        return self.rows

    async def fetch_one(self, query, values=None):
        return self.rows[0] if self.rows else None


def test_create_memory_validates_and_inserts_user_memory():
    async def run():
        db = FakeDb()
        svc = MemoryService(db)
        row_id = await svc.create_memory(
            MemoryCreateRequest(memoryType="style", title="科技风", content="结构清晰，少营销语", weight=80),
            make_user(),
        )
        assert row_id == 7
        _, values = db.executed[-1]
        assert values["userId"] == 1
        assert values["memoryType"] == "style"
        assert values["title"] == "科技风"
        assert values["weight"] == 80

    asyncio.run(run())


def test_list_active_by_stage_filters_visual_for_image_stage():
    async def run():
        db = FakeDb()
        now = datetime(2026, 5, 11, 10, 0, 0)
        db.rows = [
            {"id": 1, "userId": 1, "memoryType": "visual", "title": "视觉", "content": "科技感配图", "weight": 90, "source": "manual", "isActive": 1, "createTime": now, "updateTime": now},
            {"id": 2, "userId": 1, "memoryType": "topic", "title": "主题", "content": "AI 编程", "weight": 50, "source": "manual", "isActive": 1, "createTime": now, "updateTime": now},
        ]
        svc = MemoryService(db)
        memories = await svc.list_for_stage(1, "image")
        assert len(memories) == 1
        assert memories[0].memory_type == "visual"

    asyncio.run(run())
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
cd backend && uv run pytest app/tests/test_memory_service.py -q
```

Expected: FAIL because `app.schemas.memory` and `MemoryService` do not exist.

- [ ] **Step 3: Implement memory schema and service**

Create `backend/app/schemas/memory.py`:

```python
from typing import Literal, Optional

from pydantic import BaseModel, Field

MemoryType = Literal["style", "platform", "topic", "constraint", "visual"]


class MemoryCreateRequest(BaseModel):
    memory_type: MemoryType = Field(..., alias="memoryType")
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    weight: int = Field(50, ge=0, le=100)

    class Config:
        populate_by_name = True


class MemoryUpdateRequest(BaseModel):
    memory_type: Optional[MemoryType] = Field(None, alias="memoryType")
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    weight: Optional[int] = Field(None, ge=0, le=100)

    class Config:
        populate_by_name = True


class MemoryVO(BaseModel):
    id: int
    user_id: int = Field(..., alias="userId")
    memory_type: str = Field(..., alias="memoryType")
    title: str
    content: str
    weight: int
    source: str
    is_active: bool = Field(..., alias="isActive")
    create_time: str = Field(..., alias="createTime")
    update_time: str = Field(..., alias="updateTime")

    class Config:
        populate_by_name = True
```

Create `backend/app/services/memory_service.py` with:

```python
from app.schemas.memory import MemoryCreateRequest, MemoryUpdateRequest, MemoryVO


STAGE_MEMORY_TYPES = {
    "title": {"style", "platform", "topic", "constraint"},
    "outline": {"style", "topic", "constraint"},
    "content": {"style", "platform", "topic", "constraint"},
    "image": {"visual", "platform"},
}


class MemoryService:
    def __init__(self, db):
        self.db = db

    async def create_memory(self, request: MemoryCreateRequest, login_user) -> int:
        return await self.db.execute(
            query="""
                INSERT INTO user_memory (userId, memoryType, title, content, weight, source, isActive)
                VALUES (:userId, :memoryType, :title, :content, :weight, 'manual', 1)
            """,
            values={
                "userId": login_user.id,
                "memoryType": request.memory_type,
                "title": request.title,
                "content": request.content,
                "weight": request.weight,
            },
        )

    async def list_memories(self, user_id: int, memory_type: str | None = None) -> list[MemoryVO]:
        extra = "AND memoryType = :memoryType" if memory_type else ""
        values = {"userId": user_id}
        if memory_type:
            values["memoryType"] = memory_type
        rows = await self.db.fetch_all(
            query=f"""
                SELECT id, userId, memoryType, title, content, weight, source, isActive, createTime, updateTime
                FROM user_memory
                WHERE userId = :userId AND isDelete = 0 {extra}
                ORDER BY weight DESC, updateTime DESC
            """,
            values=values,
        )
        return [self._to_vo(row) for row in rows]

    async def list_for_stage(self, user_id: int, stage: str) -> list[MemoryVO]:
        allowed = STAGE_MEMORY_TYPES.get(stage, set())
        memories = await self.list_memories(user_id)
        return [item for item in memories if item.is_active and item.memory_type in allowed]

    async def toggle_memory(self, memory_id: int, user_id: int) -> bool:
        row = await self.db.fetch_one(
            query="SELECT isActive FROM user_memory WHERE id = :id AND userId = :userId AND isDelete = 0",
            values={"id": memory_id, "userId": user_id},
        )
        if not row:
            return False
        next_active = 0 if row["isActive"] else 1
        await self.db.execute(
            query="UPDATE user_memory SET isActive = :isActive WHERE id = :id AND userId = :userId",
            values={"isActive": next_active, "id": memory_id, "userId": user_id},
        )
        return bool(next_active)

    async def delete_memory(self, memory_id: int, user_id: int) -> bool:
        await self.db.execute(
            query="UPDATE user_memory SET isDelete = 1 WHERE id = :id AND userId = :userId",
            values={"id": memory_id, "userId": user_id},
        )
        return True

    def _to_vo(self, row) -> MemoryVO:
        data = dict(row)
        return MemoryVO(
            id=data["id"],
            userId=data["userId"],
            memoryType=data["memoryType"],
            title=data["title"],
            content=data["content"],
            weight=data["weight"],
            source=data["source"],
            isActive=bool(data["isActive"]),
            createTime=data["createTime"].isoformat(),
            updateTime=data["updateTime"].isoformat(),
        )
```

- [ ] **Step 4: Implement Markdown writing skill loader**

Create Markdown Skills under `backend/app/writing_skills/system/`:

```text
backend/app/writing_skills/system/tech-media-analysis.md
backend/app/writing_skills/system/xiaohongshu-seeding.md
```

Each file uses YAML frontmatter followed by Markdown instructions:

```markdown
---
id: tech-media-analysis
name: 科技自媒体深度分析
description: 适合公众号和知乎的科技趋势分析文章
applicableStages:
  - title
  - outline
  - content
---

# 写作要求

- 标题要有趋势感、信息密度或反差感
- 开头用热点事件切入
- 正文包含背景、影响、机会、风险、建议
- 结尾给出可执行建议
- 避免空泛口号和过度营销语
```

Create `backend/app/schemas/writing_skill.py`:

```python
from pydantic import BaseModel, Field


class WritingSkillVO(BaseModel):
    ref: str
    id: str
    name: str
    description: str = ""
    applicable_stages: list[str] = Field(default_factory=list, alias="applicableStages")
    content: str = ""

    class Config:
        populate_by_name = True
```

Create `backend/app/services/writing_skill_service.py` with a small frontmatter parser using `yaml.safe_load`. It must expose:

```python
class WritingSkillService:
    def list_skills(self) -> list[WritingSkillVO]: ...
    async def list_for_stage(self, user_id: int, stage: str, enabled_skill_refs: list[str]) -> list[WritingSkillVO]: ...
```

`ref` format is `system/<skill-id>`, for example `system/tech-media-analysis`.

- [ ] **Step 5: Implement routers and register them**

Create `backend/app/routers/memory.py`:

```python
from fastapi import APIRouter, Depends
from databases import Database

from app.database import get_db
from app.deps import require_login
from app.schemas.common import BaseResponse
from app.schemas.memory import MemoryCreateRequest, MemoryVO
from app.schemas.user import LoginUserVO
from app.services.memory_service import MemoryService

router = APIRouter(prefix="/memories", tags=["长期记忆"])


@router.get("", response_model=BaseResponse[list[MemoryVO]])
async def list_memories(db: Database = Depends(get_db), current_user: LoginUserVO = Depends(require_login)):
    return BaseResponse.success(data=await MemoryService(db).list_memories(current_user.id))


@router.post("", response_model=BaseResponse[int])
async def create_memory(request: MemoryCreateRequest, db: Database = Depends(get_db), current_user: LoginUserVO = Depends(require_login)):
    return BaseResponse.success(data=await MemoryService(db).create_memory(request, current_user))


@router.patch("/{memory_id}/toggle", response_model=BaseResponse[bool])
async def toggle_memory(memory_id: int, db: Database = Depends(get_db), current_user: LoginUserVO = Depends(require_login)):
    return BaseResponse.success(data=await MemoryService(db).toggle_memory(memory_id, current_user.id))


@router.delete("/{memory_id}", response_model=BaseResponse[bool])
async def delete_memory(memory_id: int, db: Database = Depends(get_db), current_user: LoginUserVO = Depends(require_login)):
    return BaseResponse.success(data=await MemoryService(db).delete_memory(memory_id, current_user.id))
```

Create `backend/app/routers/writing_skill.py` with only:

```http
GET /api/writing-skills
```

Include both routers in `backend/app/main.py`.

- [ ] **Step 6: Run tests**

Run:

```bash
cd backend && uv run pytest app/tests/test_memory_service.py app/tests/test_writing_skill_service.py -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/memory.py backend/app/schemas/writing_skill.py backend/app/services/memory_service.py backend/app/services/writing_skill_service.py backend/app/routers/memory.py backend/app/routers/writing_skill.py backend/app/main.py backend/app/tests/test_memory_service.py backend/app/tests/test_writing_skill_service.py
git commit -m "feat: add memory and writing skill services"
```

---

## Task 3: Internal RAG Kernel Facade

**Files:**
- Create: `backend/app/rag/`
- Create: `backend/app/rag/kernel.py`
- Create: `backend/app/rag/config.py`
- Copy/adapt: selected files from `plugin/MODULAR-RAG-MCP-SERVER/src`
- Test: `backend/app/tests/test_rag_kernel_facade.py`

- [ ] **Step 1: Write facade tests with fake kernel dependencies**

Create `backend/app/tests/test_rag_kernel_facade.py`:

```python
from app.rag.kernel import RagQueryResult, format_results_for_prompt


def test_format_results_for_prompt_includes_source_and_score():
    results = [
        RagQueryResult(text="AI 编程正在改变 IDE 工作流", source="hotspot.md", score=0.91),
        RagQueryResult(text="开发者工具需要强调效率收益", source="doc.md", score=0.82),
    ]

    prompt = format_results_for_prompt(results)

    assert "AI 编程正在改变 IDE 工作流" in prompt
    assert "来源: hotspot.md" in prompt
    assert "相关度: 0.91" in prompt
    assert "开发者工具需要强调效率收益" in prompt
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
cd backend && uv run pytest app/tests/test_rag_kernel_facade.py -q
```

Expected: FAIL because `app.rag.kernel` does not exist.

- [ ] **Step 3: Create minimal RAG facade**

Create `backend/app/rag/__init__.py` and `backend/app/rag/kernel.py`:

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class RagIngestResult:
    success: bool
    chunk_count: int = 0
    error: str | None = None


@dataclass
class RagQueryResult:
    text: str
    source: str
    score: float
    title: str | None = None


def format_results_for_prompt(results: Iterable[RagQueryResult]) -> str:
    blocks = []
    for index, item in enumerate(results, start=1):
        title = f"标题: {item.title}\n" if item.title else ""
        blocks.append(
            f"[资料 {index}]\n"
            f"{title}"
            f"内容: {item.text}\n"
            f"来源: {item.source}\n"
            f"相关度: {item.score:.2f}"
        )
    return "\n\n".join(blocks)


class RagKernel:
    def ingest_file(self, file_path: str, collection: str, force: bool = False) -> RagIngestResult:
        from app.rag.ingestion.pipeline import IngestionPipeline
        from app.rag.config import get_rag_settings

        pipeline = IngestionPipeline(get_rag_settings(), collection=collection, force=force)
        result = pipeline.run(file_path)
        return RagIngestResult(success=result.success, chunk_count=result.chunk_count, error=result.error)

    async def query(self, query: str, collection: str, top_k: int = 5) -> list[RagQueryResult]:
        from app.rag.query import QueryKnowledgeHubTool

        tool = QueryKnowledgeHubTool()
        response = await tool.execute(query=query, top_k=top_k, collection=collection)
        return [
            RagQueryResult(
                text=c.get("text", ""),
                source=c.get("source", ""),
                score=float(c.get("score", 0)),
                title=c.get("title"),
            )
            for c in response.metadata.get("chunks", [])
        ]
```

- [ ] **Step 4: Copy RAG modules**

Copy only required source modules from `plugin/MODULAR-RAG-MCP-SERVER/src` to `backend/app/rag`, then update imports from `src.` to `app.rag.`. Use a mechanical replacement and then run import smoke tests.

Required initial mapping:

```text
plugin/.../src/core/types.py -> backend/app/rag/core/types.py
plugin/.../src/core/settings.py -> backend/app/rag/core/settings.py
plugin/.../src/core/query_engine/ -> backend/app/rag/core/query_engine/
plugin/.../src/core/response/ -> backend/app/rag/core/response/
plugin/.../src/core/trace/ -> backend/app/rag/core/trace/
plugin/.../src/ingestion/ -> backend/app/rag/ingestion/
plugin/.../src/libs/ -> backend/app/rag/libs/
plugin/.../src/observability/logger.py -> backend/app/rag/observability/logger.py
```

For Phase 1, create `backend/app/rag/query.py` by adapting `query_knowledge_hub.py` without MCP types.

- [ ] **Step 5: Add RAG settings bridge**

Create `backend/app/rag/config.py`:

```python
from app.config import settings as app_settings
from app.rag.core.settings import Settings


def get_rag_settings() -> Settings:
    return Settings.from_dict(
        {
            "llm": {
                "provider": "openai",
                "model": app_settings.dashscope_model,
                "api_key": app_settings.dashscope_api_key,
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "temperature": 0.0,
                "max_tokens": 4096,
            },
            "embedding": {
                "provider": "openai",
                "model": "text-embedding-v3",
                "dimensions": 1024,
                "api_key": app_settings.dashscope_api_key,
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            },
            "vector_store": {
                "provider": "chroma",
                "persist_directory": "./storage/rag/chroma",
                "collection_name": "knowledge_hub",
            },
            "retrieval": {"dense_top_k": 20, "sparse_top_k": 20, "fusion_top_k": 10, "rrf_k": 60},
            "rerank": {"enabled": False, "provider": "none", "model": "none", "top_k": 5},
            "evaluation": {"enabled": False, "provider": "custom", "metrics": ["hit_rate"]},
            "observability": {
                "log_level": "INFO",
                "trace_enabled": True,
                "trace_file": "./storage/rag/traces.jsonl",
                "structured_logging": True,
            },
            "ingestion": {
                "chunk_size": 1000,
                "chunk_overlap": 200,
                "splitter": "recursive",
                "batch_size": 100,
                "chunk_refiner": {"use_llm": False},
                "metadata_enricher": {"use_llm": False},
            },
        }
    )
```

- [ ] **Step 6: Run facade and smoke tests**

Run:

```bash
cd backend && uv run pytest app/tests/test_rag_kernel_facade.py -q
python - <<'PY'
from app.rag.config import get_rag_settings
from app.rag.kernel import RagKernel
settings = get_rag_settings()
print(settings.vector_store.provider)
print(RagKernel)
PY
```

Expected: tests pass and script prints `chroma`.

- [ ] **Step 7: Commit**

```bash
git add backend/app/rag backend/app/tests/test_rag_kernel_facade.py
git commit -m "feat: add internal rag kernel facade"
```

---

## Task 4: Knowledge Service and Knowledge API

**Files:**
- Create: `backend/app/schemas/knowledge.py`
- Create: `backend/app/services/rag_knowledge_service.py`
- Create: `backend/app/routers/knowledge.py`
- Modify: `backend/app/main.py`
- Test: `backend/app/tests/test_rag_knowledge_service.py`

- [ ] **Step 1: Write failing RagKnowledgeService tests**

Create `backend/app/tests/test_rag_knowledge_service.py`:

```python
import asyncio
from datetime import datetime

from app.services.rag_knowledge_service import RagKnowledgeService, collection_for


def test_collection_for_uses_user_scoped_names():
    assert collection_for(9, "upload") == "user_9_knowledge"
    assert collection_for(9, "article") == "user_9_articles"
    assert collection_for(9, "hotspot") == "user_9_hotspots"


class FakeDb:
    def __init__(self):
        self.executed = []
        self.rows = []

    async def execute(self, query, values=None):
        self.executed.append((str(query), values))
        return 3

    async def fetch_all(self, query, values=None):
        return self.rows


class FakeKernel:
    def ingest_file(self, file_path, collection, force=False):
        return type("Result", (), {"success": True, "chunk_count": 4, "error": None})()


def test_create_upload_document_records_ready_status_after_ingest():
    async def run():
        db = FakeDb()
        svc = RagKnowledgeService(db, rag_kernel=FakeKernel())
        doc_id = await svc.ingest_uploaded_file(user_id=5, title="demo.pdf", file_path="/tmp/demo.pdf")
        assert doc_id == 3
        assert db.executed[-1][1]["status"] == "ready"
        assert db.executed[-1][1]["chunkCount"] == 4
        assert db.executed[-1][1]["collectionName"] == "user_5_knowledge"

    asyncio.run(run())
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
cd backend && uv run pytest app/tests/test_rag_knowledge_service.py -q
```

Expected: FAIL because service does not exist.

- [ ] **Step 3: Implement knowledge schema**

Create `backend/app/schemas/knowledge.py`:

```python
from typing import Literal, Optional

from pydantic import BaseModel, Field

KnowledgeSourceType = Literal["upload", "article", "hotspot", "system"]


class KnowledgeDocumentVO(BaseModel):
    id: int
    user_id: int = Field(..., alias="userId")
    title: str
    source_type: str = Field(..., alias="sourceType")
    source_id: Optional[str] = Field(None, alias="sourceId")
    collection_name: str = Field(..., alias="collectionName")
    status: str
    chunk_count: int = Field(..., alias="chunkCount")
    error_message: Optional[str] = Field(None, alias="errorMessage")
    create_time: str = Field(..., alias="createTime")
    update_time: str = Field(..., alias="updateTime")

    class Config:
        populate_by_name = True


class KnowledgeQueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    collections: list[str] = Field(default_factory=list)
    top_k: int = Field(5, alias="topK", ge=1, le=20)

    class Config:
        populate_by_name = True


class KnowledgeQueryResultVO(BaseModel):
    text: str
    source: str
    score: float
    title: Optional[str] = None
```

- [ ] **Step 4: Implement RagKnowledgeService**

Create `backend/app/services/rag_knowledge_service.py`:

```python
from pathlib import Path

from app.rag.kernel import RagKernel, format_results_for_prompt
from app.schemas.knowledge import KnowledgeDocumentVO


SOURCE_COLLECTION_SUFFIX = {
    "upload": "knowledge",
    "article": "articles",
    "hotspot": "hotspots",
}


def collection_for(user_id: int, source_type: str) -> str:
    suffix = SOURCE_COLLECTION_SUFFIX[source_type]
    return f"user_{user_id}_{suffix}"


class RagKnowledgeService:
    def __init__(self, db, rag_kernel: RagKernel | None = None):
        self.db = db
        self.rag_kernel = rag_kernel or RagKernel()

    async def ingest_uploaded_file(self, user_id: int, title: str, file_path: str) -> int:
        collection = collection_for(user_id, "upload")
        result = self.rag_kernel.ingest_file(file_path=file_path, collection=collection)
        status = "ready" if result.success else "failed"
        return await self._insert_document(
            user_id=user_id,
            title=title,
            source_type="upload",
            source_id=None,
            collection_name=collection,
            file_path=file_path,
            status=status,
            chunk_count=result.chunk_count,
            error_message=result.error,
        )

    async def query_prompt_context(self, user_id: int, query: str, collections: list[str], top_k: int = 5) -> str:
        effective_collections = collections or [
            collection_for(user_id, "upload"),
            collection_for(user_id, "article"),
            collection_for(user_id, "hotspot"),
        ]
        all_results = []
        for collection in effective_collections:
            all_results.extend(await self.rag_kernel.query(query=query, collection=collection, top_k=top_k))
        all_results.sort(key=lambda item: item.score, reverse=True)
        return format_results_for_prompt(all_results[:top_k])

    async def _insert_document(self, user_id: int, title: str, source_type: str, source_id: str | None,
                               collection_name: str, file_path: str | None, status: str,
                               chunk_count: int, error_message: str | None) -> int:
        return await self.db.execute(
            query="""
                INSERT INTO knowledge_document (
                    userId, title, sourceType, sourceId, collectionName, filePath,
                    status, chunkCount, errorMessage
                )
                VALUES (
                    :userId, :title, :sourceType, :sourceId, :collectionName, :filePath,
                    :status, :chunkCount, :errorMessage
                )
            """,
            values={
                "userId": user_id,
                "title": title,
                "sourceType": source_type,
                "sourceId": source_id,
                "collectionName": collection_name,
                "filePath": file_path,
                "status": status,
                "chunkCount": chunk_count,
                "errorMessage": error_message,
            },
        )
```

- [ ] **Step 5: Implement knowledge router**

Create `backend/app/routers/knowledge.py` with upload and query endpoints. Upload writes files to `/tmp/ai-passage-uploads/{userId}/` first:

```python
from pathlib import Path

from databases import Database
from fastapi import APIRouter, Depends, File, UploadFile

from app.database import get_db
from app.deps import require_login
from app.schemas.common import BaseResponse
from app.schemas.knowledge import KnowledgeQueryRequest
from app.schemas.user import LoginUserVO
from app.services.rag_knowledge_service import RagKnowledgeService

router = APIRouter(prefix="/knowledge", tags=["知识库"])


@router.post("/upload", response_model=BaseResponse[int])
async def upload_knowledge(file: UploadFile = File(...), db: Database = Depends(get_db), current_user: LoginUserVO = Depends(require_login)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".md", ".txt"}:
        return BaseResponse(code=40000, data=None, message="仅支持 PDF/Markdown/TXT")
    upload_dir = Path("/tmp/ai-passage-uploads") / str(current_user.id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    target = upload_dir / (file.filename or "upload.txt")
    target.write_bytes(await file.read())
    doc_id = await RagKnowledgeService(db).ingest_uploaded_file(current_user.id, target.name, str(target))
    return BaseResponse.success(data=doc_id)


@router.post("/query", response_model=BaseResponse[str])
async def query_knowledge(request: KnowledgeQueryRequest, db: Database = Depends(get_db), current_user: LoginUserVO = Depends(require_login)):
    context = await RagKnowledgeService(db).query_prompt_context(
        user_id=current_user.id,
        query=request.query,
        collections=request.collections,
        top_k=request.top_k,
    )
    return BaseResponse.success(data=context)
```

- [ ] **Step 6: Run tests**

Run:

```bash
cd backend && uv run pytest app/tests/test_rag_knowledge_service.py -q
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/knowledge.py backend/app/services/rag_knowledge_service.py backend/app/routers/knowledge.py backend/app/main.py backend/app/tests/test_rag_knowledge_service.py
git commit -m "feat: add knowledge service and api"
```

---

## Task 5: AgentContextBuilder and Snapshot Persistence

**Files:**
- Create: `backend/app/schemas/agent_context.py`
- Create: `backend/app/services/agent_context_builder.py`
- Test: `backend/app/tests/test_agent_context_builder.py`

- [ ] **Step 1: Write failing tests**

Create `backend/app/tests/test_agent_context_builder.py`:

```python
import asyncio

from app.services.agent_context_builder import AgentContextBuilder


class FakeMemoryService:
    async def list_for_stage(self, user_id, stage):
        return [type("Memory", (), {"title": "风格", "content": "少营销语", "weight": 80})()]


class FakeSkillService:
    async def list_for_stage(self, user_id, stage, enabled_skill_refs):
        return [type("Skill", (), {"name": "科技风", "content": "用热点切入"})()]


class FakeRagService:
    async def query_prompt_context(self, user_id, query, collections, top_k=5):
        return "[资料 1]\\n内容: AI 编程热点\\n来源: hotspot.md\\n相关度: 0.91"


class FakeDb:
    def __init__(self):
        self.executed = []

    async def execute(self, query, values=None):
        self.executed.append((str(query), values))
        return 1


def test_builder_includes_memory_skill_and_rag_context():
    async def run():
        db = FakeDb()
        builder = AgentContextBuilder(
            db,
            memory_service=FakeMemoryService(),
            writing_skill_service=FakeSkillService(),
            rag_knowledge_service=FakeRagService(),
        )
        ctx = await builder.build_context(
            user_id=1,
            task_id="task-1",
            stage="content",
            topic="AI 编程",
            style="tech",
            enabled_skill_refs=["system/tech-media-analysis"],
            enable_memory=True,
            enable_rag=True,
            rag_collections=[],
        )
        assert "少营销语" in ctx.instruction_block
        assert "用热点切入" in ctx.instruction_block
        assert "AI 编程热点" in ctx.instruction_block
        assert db.executed[-1][1]["stage"] == "content"

    asyncio.run(run())
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
cd backend && uv run pytest app/tests/test_agent_context_builder.py -q
```

Expected: FAIL because builder does not exist.

- [ ] **Step 3: Implement schema**

Create `backend/app/schemas/agent_context.py`:

```python
from pydantic import BaseModel


class AgentContext(BaseModel):
    memory_context: str = ""
    skill_context: str = ""
    rag_context: str = ""
    hotspot_context: str = ""
    article_example_context: str = ""
    instruction_block: str = ""
```

- [ ] **Step 4: Implement AgentContextBuilder**

Create `backend/app/services/agent_context_builder.py`:

```python
from app.schemas.agent_context import AgentContext
from app.services.memory_service import MemoryService
from app.services.rag_knowledge_service import RagKnowledgeService
from app.services.writing_skill_service import WritingSkillService


class AgentContextBuilder:
    def __init__(self, db, memory_service=None, writing_skill_service=None, rag_knowledge_service=None):
        self.db = db
        self.memory_service = memory_service or MemoryService(db)
        self.writing_skill_service = writing_skill_service or WritingSkillService(db)
        self.rag_knowledge_service = rag_knowledge_service or RagKnowledgeService(db)

    async def build_context(self, user_id: int, task_id: str, stage: str, topic: str, style: str | None,
                            enabled_skill_refs: list[str], enable_memory: bool, enable_rag: bool,
                            rag_collections: list[str]) -> AgentContext:
        memory_context = ""
        skill_context = ""
        rag_context = ""

        if enable_memory:
            memories = await self.memory_service.list_for_stage(user_id, stage)
            memory_context = "\n".join(f"- {m.title}: {m.content}" for m in memories)

        skills = await self.writing_skill_service.list_for_stage(user_id, stage, enabled_skill_refs)
        skill_context = "\n".join(f"- {s.name}: {s.content}" for s in skills)

        if enable_rag and stage in {"outline", "content", "title"}:
            rag_context = await self.rag_knowledge_service.query_prompt_context(
                user_id=user_id,
                query=topic,
                collections=rag_collections,
                top_k=5,
            )

        instruction_block = self._compose_instruction_block(memory_context, skill_context, rag_context)
        await self._save_snapshot(user_id, task_id, stage, memory_context, skill_context, rag_context, instruction_block)
        return AgentContext(
            memory_context=memory_context,
            skill_context=skill_context,
            rag_context=rag_context,
            instruction_block=instruction_block,
        )

    def _compose_instruction_block(self, memory_context: str, skill_context: str, rag_context: str) -> str:
        sections = []
        if memory_context:
            sections.append(f"【用户长期偏好】\n{memory_context}")
        if skill_context:
            sections.append(f"【启用写作 Skill】\n{skill_context}")
        if rag_context:
            sections.append(f"【相关知识库资料】\n{rag_context}\n请基于资料写作；资料不足时不要编造具体事实。")
        return "\n\n".join(sections)

    async def _save_snapshot(self, user_id: int, task_id: str, stage: str, memory_context: str,
                             skill_context: str, rag_context: str, instruction_block: str) -> None:
        token_estimate = max(1, len(instruction_block) // 4) if instruction_block else 0
        await self.db.execute(
            query="""
                INSERT INTO agent_context_snapshot (
                    taskId, userId, stage, memoryContext, skillContext, ragContext, tokenEstimate
                )
                VALUES (
                    :taskId, :userId, :stage, :memoryContext, :skillContext, :ragContext, :tokenEstimate
                )
            """,
            values={
                "taskId": task_id,
                "userId": user_id,
                "stage": stage,
                "memoryContext": memory_context,
                "skillContext": skill_context,
                "ragContext": rag_context,
                "tokenEstimate": token_estimate,
            },
        )
```

- [ ] **Step 5: Run tests**

Run:

```bash
cd backend && uv run pytest app/tests/test_agent_context_builder.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/agent_context.py backend/app/services/agent_context_builder.py backend/app/tests/test_agent_context_builder.py
git commit -m "feat: build agent context snapshots"
```

---

## Task 6: Persist Article Context Options and Inject Prompts

**Files:**
- Modify: `backend/app/schemas/article.py`
- Modify: `backend/app/services/article_service.py`
- Modify: `backend/app/services/article_async_service.py`
- Modify: `backend/app/services/article_agent_service.py`
- Modify: `backend/app/routers/article.py`
- Test: `backend/app/tests/test_article_context_options.py`

- [ ] **Step 1: Write failing article option test**

Create `backend/app/tests/test_article_context_options.py`:

```python
from app.schemas.article import ArticleCreateRequest, ArticleState


def test_article_create_request_accepts_context_options():
    request = ArticleCreateRequest(
        topic="AI 编程",
        enableMemory=True,
        enableRag=True,
        enabledSkillRefs=["system/tech-media-analysis", "system/xiaohongshu-seeding"],
        ragCollections=["user_1_knowledge"],
    )
    assert request.enable_memory is True
    assert request.enable_rag is True
    assert request.enabled_skill_refs == ["system/tech-media-analysis", "system/xiaohongshu-seeding"]
    assert request.rag_collections == ["user_1_knowledge"]


def test_article_state_has_context_fields():
    state = ArticleState()
    state.user_id = 1
    state.enable_memory = True
    state.enable_rag = True
    state.enabled_skill_refs = ["system/tech-media-analysis"]
    state.rag_collections = ["user_1_knowledge"]
    assert state.user_id == 1
    assert state.enabled_skill_refs == ["system/tech-media-analysis"]
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
cd backend && uv run pytest app/tests/test_article_context_options.py -q
```

Expected: FAIL because request/state fields do not exist.

- [ ] **Step 3: Add schema fields**

Modify `ArticleCreateRequest` in `backend/app/schemas/article.py`:

```python
enable_memory: bool = Field(True, alias="enableMemory", description="是否启用长期记忆")
enable_rag: bool = Field(True, alias="enableRag", description="是否启用RAG")
enabled_skill_refs: List[str] = Field(default_factory=list, alias="enabledSkillRefs")
rag_collections: List[str] = Field(default_factory=list, alias="ragCollections")

class Config:
    populate_by_name = True
```

Add to `ArticleState.__init__`:

```python
self.user_id: Optional[int] = None
self.enable_memory: bool = True
self.enable_rag: bool = True
self.enabled_skill_refs: List[str] = []
self.rag_collections: List[str] = []
```

- [ ] **Step 4: Persist fields in ArticleService**

Update `create_article_task()` signature:

```python
enable_memory: bool = True
enable_rag: bool = True
enabled_skill_refs: Optional[List[str]] = None
rag_collections: Optional[List[str]] = None
```

Extend insert SQL with:

```sql
enableMemory, enableRag, enabledSkillRefs, ragCollections
```

and values:

```python
"enableMemory": 1 if enable_memory else 0,
"enableRag": 1 if enable_rag else 0,
"enabledSkillRefs": json.dumps(enabled_skill_refs or [], ensure_ascii=False),
"ragCollections": json.dumps(rag_collections or [], ensure_ascii=False),
```

Pass the fields through `create_article_task_with_quota_check()` and `article.create` router.

- [ ] **Step 5: Load context fields into async ArticleState**

In `backend/app/services/article_async_service.py`, locate state construction and set:

```python
state.user_id = article["userId"]
state.enable_memory = bool(article.get("enableMemory", 1))
state.enable_rag = bool(article.get("enableRag", 1))
state.enabled_skill_refs = json.loads(article.get("enabledSkillRefs") or "[]")
state.rag_collections = json.loads(article.get("ragCollections") or "[]")
```

- [ ] **Step 6: Inject context into Agent prompts**

In `ArticleAgentService.__init__`, add:

```python
from app.services.agent_context_builder import AgentContextBuilder
self.agent_context_builder = AgentContextBuilder(database)
```

Add helper:

```python
async def _build_context_prompt(self, state: ArticleState, stage: str) -> str:
    if not state.user_id:
        return ""
    try:
        context = await self.agent_context_builder.build_context(
            user_id=state.user_id,
            task_id=state.task_id,
            stage=stage,
            topic=state.topic or "",
            style=state.style,
            enabled_skill_refs=state.enabled_skill_refs or [],
            enable_memory=state.enable_memory,
            enable_rag=state.enable_rag,
            rag_collections=state.rag_collections or [],
        )
        return f"\n\n{context.instruction_block}" if context.instruction_block else ""
    except Exception as exc:
        logger.warning("构建Agent上下文失败 taskId=%s stage=%s error=%s", state.task_id, stage, exc)
        return ""
```

Then append in each Agent method:

```python
prompt += await self._build_context_prompt(state, "title")
prompt += await self._build_context_prompt(state, "outline")
prompt += await self._build_context_prompt(state, "content")
prompt += await self._build_context_prompt(state, "image")
```

Use the appropriate stage in each method.

- [ ] **Step 7: Run backend tests**

Run:

```bash
cd backend && uv run pytest app/tests/test_article_context_options.py app/tests/test_agent_context_builder.py -q
```

Expected: pass.

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/article.py backend/app/services/article_service.py backend/app/services/article_async_service.py backend/app/services/article_agent_service.py backend/app/routers/article.py backend/app/tests/test_article_context_options.py
git commit -m "feat: inject context into article agents"
```

---

## Task 7: Knowledge UI and Article/Hotspot Ingest Controls

**Files:**
- Create: `frontend/src/api/memoryController.ts`
- Create: `frontend/src/api/writingSkillController.ts`
- Create: `frontend/src/api/knowledgeController.ts`
- Create: `frontend/src/pages/KnowledgePage.vue`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/components/GlobalHeader.vue`
- Modify: `frontend/src/pages/article/ArticleCreatePage.vue`
- Modify: `frontend/src/pages/article/ArticleListPage.vue`
- Modify: `frontend/src/pages/topic/MonitorTab.vue`
- Test: `frontend/tests/articleContextOptions.test.mjs`

- [ ] **Step 1: Write frontend state serialization test**

Create `frontend/tests/articleContextOptions.test.mjs`:

```javascript
import assert from 'node:assert/strict'

const buildCreateArticlePayload = (topic, state) => ({
  topic,
  style: state.style,
  enabledImageMethods: state.enabledImageMethods,
  enableMemory: state.enableMemory,
  enableRag: state.enableRag,
  enabledSkillRefs: state.enabledSkillRefs,
  ragCollections: state.ragCollections,
})

const payload = buildCreateArticlePayload('AI 编程', {
  style: 'tech',
  enabledImageMethods: ['PEXELS'],
  enableMemory: true,
  enableRag: true,
  enabledSkillRefs: ["system/tech-media-analysis", "system/xiaohongshu-seeding"],
  ragCollections: ['user_1_knowledge'],
})

assert.equal(payload.topic, 'AI 编程')
assert.equal(payload.enableMemory, true)
assert.equal(payload.enableRag, true)
assert.deepEqual(payload.enabledSkillRefs, ["system/tech-media-analysis", "system/xiaohongshu-seeding"])
assert.deepEqual(payload.ragCollections, ['user_1_knowledge'])
```

- [ ] **Step 2: Run test**

Run:

```bash
cd frontend && node tests/articleContextOptions.test.mjs
```

Expected: pass. This locks the request shape.

- [ ] **Step 3: Create API wrappers**

Create `frontend/src/api/knowledgeController.ts`:

```typescript
import request from '@/request'

export function uploadKnowledge(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/knowledge/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function queryKnowledge(body: { query: string; collections?: string[]; topK?: number }) {
  return request.post('/knowledge/query', body)
}

export function ingestArticle(taskId: string) {
  return request.post(`/knowledge/articles/${taskId}/ingest`)
}

export function ingestHotspots(recordIds: number[]) {
  return request.post('/knowledge/hotspots/ingest', { recordIds })
}
```

Create memory and Skill controllers with `get/post/patch/delete` against `/memories` and `/writing-skills`.

- [ ] **Step 4: Add KnowledgePage**

Create `frontend/src/pages/KnowledgePage.vue` with four tabs:

```vue
<template>
  <div class="knowledge-page">
    <a-tabs v-model:activeKey="activeTab">
      <a-tab-pane key="documents" tab="资料库">
        <a-upload :before-upload="beforeUpload" :show-upload-list="false">
          <a-button>上传资料</a-button>
        </a-upload>
      </a-tab-pane>
      <a-tab-pane key="memories" tab="记忆">
        <a-empty description="记忆管理将在此处展示" />
      </a-tab-pane>
      <a-tab-pane key="skills" tab="写作 Skills">
        <a-empty description="写作 Skills 管理将在此处展示" />
      </a-tab-pane>
      <a-tab-pane key="rag" tab="RAG 测试">
        <a-input-search v-model:value="query" enter-button="查询" @search="doQuery" />
        <pre class="rag-result">{{ result }}</pre>
      </a-tab-pane>
    </a-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { message } from 'ant-design-vue'
import { queryKnowledge, uploadKnowledge } from '@/api/knowledgeController'

const activeTab = ref('documents')
const query = ref('')
const result = ref('')

const beforeUpload = async (file: File) => {
  await uploadKnowledge(file)
  message.success('资料已提交入库')
  return false
}

const doQuery = async () => {
  const res = await queryKnowledge({ query: query.value, topK: 5 })
  result.value = res.data?.data || ''
}
</script>
```

This is the first UI slice. Replace the empty panels with Markdown Skill previews and memory forms as the backend endpoints stabilize.

- [ ] **Step 5: Add route and nav item**

In `frontend/src/router/index.ts`:

```typescript
{
  path: '/knowledge',
  name: '知识库',
  component: () => import('@/pages/KnowledgePage.vue'),
}
```

In `GlobalHeader.vue`, add a nav item:

```typescript
{
  key: '/knowledge',
  icon: DatabaseOutlined,
  label: '知识库',
}
```

Import `DatabaseOutlined` from `@ant-design/icons-vue`.

- [ ] **Step 6: Add article create controls**

In `ArticleCreatePage.vue`, add reactive state:

```typescript
const contextOptions = reactive({
  enableMemory: true,
  enableRag: true,
  enabledSkillRefs: [] as string[],
  ragCollections: [] as string[],
})
```

When calling `createArticle`, include:

```typescript
enableMemory: contextOptions.enableMemory,
enableRag: contextOptions.enableRag,
enabledSkillRefs: contextOptions.enabledSkillRefs,
ragCollections: contextOptions.ragCollections,
```

Add UI in advanced settings:

```vue
<a-collapse-panel key="context" header="上下文增强">
  <a-switch v-model:checked="contextOptions.enableMemory" /> 启用长期记忆
  <a-switch v-model:checked="contextOptions.enableRag" /> 启用知识库 RAG
</a-collapse-panel>
```

- [ ] **Step 7: Add ingest buttons**

In `ArticleListPage.vue`, add an action for completed articles:

```typescript
const doIngestArticle = async (record: API.ArticleVO) => {
  if (!record.taskId) return
  await ingestArticle(record.taskId)
  message.success('已加入写作样例库')
}
```

In `MonitorTab.vue`, add batch action:

```typescript
const doIngestSelectedHotspots = async () => {
  if (selectedIds.value.length === 0) return message.warning('请先选择热点')
  await ingestHotspots(selectedIds.value)
  message.success('已加入热点知识库')
}
```

- [ ] **Step 8: Run frontend checks**

Run:

```bash
cd frontend && node tests/articleContextOptions.test.mjs
npm run build
```

Expected: test passes and build succeeds.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/api/memoryController.ts frontend/src/api/writingSkillController.ts frontend/src/api/knowledgeController.ts frontend/src/pages/KnowledgePage.vue frontend/src/router/index.ts frontend/src/components/GlobalHeader.vue frontend/src/pages/article/ArticleCreatePage.vue frontend/src/pages/article/ArticleListPage.vue frontend/src/pages/topic/MonitorTab.vue frontend/tests/articleContextOptions.test.mjs
git commit -m "feat: add knowledge and context controls"
```

---

## Task 8: End-to-End Verification and Documentation

**Files:**
- Modify: `README.md`
- Modify: `backend/.env.example`
- Optional: `frontend/src/api/typings.d.ts`

- [ ] **Step 1: Update env example**

Add to `backend/.env.example`:

```env
# RAG 配置
RAG_CHROMA_DIR=./storage/rag/chroma
RAG_BM25_DIR=./storage/rag/bm25
RAG_TRACE_FILE=./storage/rag/traces.jsonl
RAG_EMBEDDING_MODEL=text-embedding-v3
```

- [ ] **Step 2: Update README**

Add a short section:

```markdown
### 上下文增强 Agent 创作

系统支持将用户长期记忆、写作 Skills 和知识库 RAG 结果注入 5 个创作 Agent。知识库支持用户上传资料、历史文章样例和热点记录，底层使用内嵌 Modular RAG Kernel 提供 Hybrid Search、BM25、向量检索、RRF 融合和引用溯源。
```

- [ ] **Step 3: Run backend focused tests**

Run:

```bash
cd backend && uv run pytest \
  app/tests/test_memory_service.py \
  app/tests/test_writing_skill_service.py \
  app/tests/test_rag_kernel_facade.py \
  app/tests/test_rag_knowledge_service.py \
  app/tests/test_agent_context_builder.py \
  app/tests/test_article_context_options.py \
  -q
```

Expected: all selected tests pass.

- [ ] **Step 4: Run frontend focused tests**

Run:

```bash
cd frontend && node tests/articleContextOptions.test.mjs
```

Expected: pass.

- [ ] **Step 5: Run build**

Run:

```bash
cd frontend && npm run build
```

Expected: build succeeds.

- [ ] **Step 6: Manual smoke flow**

Start backend and frontend:

```bash
cd backend && uv run uvicorn app.main:app --reload --port 8567
cd frontend && npm run dev
```

Manual checks:

1. Login.
2. Open `/knowledge`.
3. Upload a `.txt` document.
4. Run a RAG query from the RAG 测试 tab.
5. Create a memory.
6. Enable a writing Skill.
7. Create an article with context enhancement enabled.
8. Confirm generated article still completes if RAG query fails.

- [ ] **Step 7: Commit**

```bash
git add README.md backend/.env.example frontend/src/api/typings.d.ts
git commit -m "docs: document context-augmented creation"
```

---

## Self-Review Checklist

Spec coverage:

- Memory system: Tasks 1, 2, 5, 6, 7.
- Writing Skills: Tasks 1, 2, 5, 6, 7.
- RAG Kernel internalization: Task 3.
- Knowledge service and upload/query APIs: Task 4.
- AgentContextBuilder and snapshots: Task 5.
- Prompt injection into 5-Agent flow: Task 6.
- Frontend knowledge page and controls: Task 7.
- Verification and documentation: Task 8.

Known scope choices:

- MCP server code is not migrated in Phase 1.
- Dashboard/evaluation code from the RAG project is not migrated in Phase 1.
- Memory is manually managed; no automatic summarization in Phase 1.
- The first KnowledgePage implementation may start with upload/query and then fill memory forms and Skill previews in the same task if time allows.

Implementation order:

1. Database and models.
2. Memory/Skill services.
3. RAG facade.
4. Knowledge service.
5. AgentContextBuilder.
6. Article prompt injection.
7. Frontend UI.
8. Verification/docs.
